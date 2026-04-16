"""AIS stream ingestion client.

Connects to AISStream.io via WebSocket, subscribes to vessel position
reports for all maritime ports in UN LOCODE, validates with Pydantic,
and writes NDJSON batches to S3 every FLUSH_INTERVAL_SEC seconds.

ARCHITECTURE ROLE:
    This is the highest-frequency data source in the pipeline.
    Output: raw/source=ais/date=YYYY-MM-DD/<batch>.ndjson in S3
    Consumer: warehouse/models/staging/stg_ais.sql (Week 3)
              features/definitions/vessel_features.py (Week 5)

Usage:
    uv run python -m ingestion.clients.ais_stream
"""

from __future__ import (
    annotations,  # Allows type hints to reference classes defined later in the file
)

import asyncio
import json
import signal
from datetime import (
    UTC,
    datetime,
)
from pathlib import Path
from typing import Any

import structlog
import websockets
from pydantic import (
    BaseModel,
    Field,
)

from ingestion.config import settings
from ingestion.port_loader import load_port_bboxes
from ingestion.s3_writer import write_ndjson_batch

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# AISStream's WebSocket endpoint (WSS = secure WebSocket)
WS_URL = "wss://stream.aisstream.io/v0/stream"
FLUSH_INTERVAL_SEC = (
    60  # Write to S3 every 60 seconds — balances latency vs S3 write cost
)
SOURCE_NAME = "ais"  # S3 partition key: raw/source=ais/date=.../...

_LOCODE_PATH = (
    Path(__file__).parent.parent.parent / "warehouse" / "seeds" / "un_locode.csv"
)
BOUNDING_BOXES = load_port_bboxes(_LOCODE_PATH)


# ---------------------------------------------------------------------------
# Pydantic models — Schema validation layer
# ---------------------------------------------------------------------------


class AISMetaData(BaseModel):
    """Metadata envelope from AISStream.

    Maps to the 'MetaData' key in every AISStream WebSocket message.
    Uses Python snake_case names — Pydantic handles alias mapping.
    """

    MMSI: int
    MMSI_String: int | str = ""
    ShipName: str = ""
    latitude: float = Field(default=0.0)
    longitude: float = Field(default=0.0)
    time_utc: str = Field(default="", alias="time_utc")


class PositionReport(BaseModel):
    """Decoded AIS position report (message types 1, 2, 3).

    These are the most common AIS messages — sent every 2-10 seconds
    by vessels underway, every 3 minutes at anchor.
    """

    Sog: float = Field(default=0.0, description="Speed over ground (knots)")
    # Sog = Speed Over Ground
    # Key feature: Sog ≈ 0 means anchored/stopped → congestion signal

    Cog: float = Field(default=0.0, description="Course over ground (degrees)")
    # Cog = Course Over Ground: direction of movement (0-360°)
    # Combined with Sog, gives velocity vector

    TrueHeading: int = Field(default=511, description="True heading (degrees)")
    # Where the bow points (vs Cog which is where the vessel is moving)
    # 511 = "not available" — common default when sensor not working

    NavigationalStatus: int = Field(default=15)
    # 0=Under way (engine), 1=Anchored, 5=Moored, 15=Undefined
    # NavigationalStatus=1 (Anchored) in the port bounding box = congestion signal

    Timestamp: int = Field(
        default=0
    )  # Seconds within the minute (0-59) of the broadcast


class AISMessage(BaseModel):
    """Top-level AIS message from AISStream WebSocket.

    AISStream wraps every message in this envelope regardless of message type.
    The inner Message key varies by MessageType — we only process PositionReport.
    """

    MessageType: str  # e.g., "PositionReport", "VoyageData", "SafetyMessage"
    MetaData: AISMetaData  # Always present — has MMSI, ship name, lat/lon
    Message: dict[str, Any] = Field(default_factory=dict)  # Inner message — type varies

    def to_record(self) -> dict[str, Any]:
        """Flatten into a dict suitable for NDJSON storage.

        WHY FLATTEN: Raw AISStream JSON is nested ({MetaData: {MMSI: ...}}).
        The S3 NDJSON and downstream Postgres staging tables (Week 3) expect
        flat rows — one key per column. Flattening happens once at ingestion.
        """
        pos = self.Message.get(
            "PositionReport", {}
        )  # Inner position report dict; {} if missing
        return {
            "mmsi": self.MetaData.MMSI,  # Primary key for vessel tracking
            # .strip() removes trailing spaces
            "ship_name": self.MetaData.ShipName.strip(),
            "lat": self.MetaData.latitude,
            "lon": self.MetaData.longitude,
            "sog": pos.get(
                "Sog", 0.0
            ),  # Speed; 0.0 default if position report is empty
            "cog": pos.get("Cog", 0.0),
            "true_heading": pos.get("TrueHeading", 511),  # 511 = unavailable
            "nav_status": pos.get("NavigationalStatus", 15),  # 15 = undefined
            "msg_type": self.MessageType,
            "received_at": datetime.now(
                UTC
            ).isoformat(),  # ARRIVAL TIME, not event time
            # NOTE: received_at is when WE got the msg, not when vessel broadcast it.
            # This handles S3 partitions by arrival time for reproducible increments.
        }


# ---------------------------------------------------------------------------
# Buffer and flush logic
# ---------------------------------------------------------------------------

# WHY A BUFFER: Writing to S3 per message (1000s/hour) would be expensive and slow.


class RecordBuffer:
    """Thread-safe-ish buffer that accumulates records and flushes to S3.

    'Thread-safe-ish': we're in an async context (single event loop),
    so true thread safety isn't needed. The "ish" caveat is for clarity.
    """

    def __init__(self, source: str = SOURCE_NAME) -> None:
        self._records: list[dict[str, Any]] = []  # In-memory list of flat record dicts
        self._source = source  # S3 partition: raw/source={source}/...
        self._total_flushed = 0  # Cumulative counter for monitoring

    def add(self, record: dict[str, Any]) -> None:
        """Append a record to the buffer."""
        self._records.append(record)

    @property
    def size(self) -> int:
        return len(
            self._records
        )  # Lets callers check `if buffer.size > 0` without accessing _records

    def flush(self) -> int:
        """Write buffered records to S3 and reset. Returns count written.

        IDEMPOTENCY NOTE: If flush fails (S3 unavailable), records go back
        into the buffer — they'll be included in the next flush attempt.
        This means records could be duplicated on S3 if S3 comes back up.
        Week 3's dbt dedup (ROW_NUMBER OVER PARTITION BY mmsi, received_at)
        handles this deduplication at the warehouse layer.
        """
        if not self._records:
            logger.debug("flush_skipped", reason="buffer_empty")
            return 0

        batch = self._records.copy()  # Copy first — so we can restore on failure
        self._records.clear()  # Clear immediately — don't wait for S3 success

        try:
            key = write_ndjson_batch(batch, source=self._source)  # Write to S3
            self._total_flushed += len(batch)
            logger.info(
                "batch_flushed",
                key=key,
                batch_size=len(batch),
                total_flushed=self._total_flushed,
            )
            return len(batch)
        except Exception:
            # S3 write failed — restore records so they're not lost
            self._records = (
                batch + self._records
            )  # Prepend (not append) to preserve order
            logger.exception("flush_failed", batch_size=len(batch))
            return 0


# ---------------------------------------------------------------------------
# Main consumer loop
# ---------------------------------------------------------------------------


async def consume(shutdown_event: asyncio.Event) -> None:
    """Connect to AISStream and consume messages until shutdown.

    ASYNC ARCHITECTURE:
        Two concurrent tasks run inside this function:
        1. WebSocket message loop: reads AIS messages as they arrive
        2. periodic_flush task: wakes every 60s and flushes buffer to S3

        asyncio.create_task() runs both concurrently on the same event loop
        without threads — no shared memory race conditions.
    """
    api_key = settings.aisstream_api_key  # Read from Settings (loaded from .env)
    if not api_key:
        logger.error("missing_api_key", hint="Set AISSTREAM_API_KEY in .env")
        return

    # AISStream subscription message — tells the server what to send
    subscribe_msg = json.dumps(
        {
            "APIKey": api_key,  # Authentication
            # Geographic filter — all maritime ports in UN LOCODE
            "BoundingBoxes": BOUNDING_BOXES,
            "FilterMessageTypes": [
                "PositionReport"
            ],  # Only position reports (not voyage data, etc.)
        }
    )

    buffer = RecordBuffer()  # Single buffer shared between message loop and flush task

    async def periodic_flush() -> None:
        """Flush buffer to S3 every FLUSH_INTERVAL_SEC seconds.

        WHY A SEPARATE TASK:
        The WebSocket message loop blocks on `async for raw_msg in ws`.
        A separate task handles the timer-based flush independently.
        asyncio.sleep() yields control to the event loop — the WebSocket loop continues.
        """
        while not shutdown_event.is_set():  # Loop until SIGINT/SIGTERM received
            await asyncio.sleep(FLUSH_INTERVAL_SEC)  # Yield for 60 seconds
            buffer.flush()  # Then flush what's accumulated

    # Create the flush task — runs concurrently with the WebSocket loop below
    flush_task = asyncio.create_task(periodic_flush())

    try:
        async for ws in websockets.connect(WS_URL, ping_interval=20, ping_timeout=10):
            try:
                # Send subscription message — tells AISStream which ports/types to send
                await ws.send(subscribe_msg)
                logger.info(
                    "websocket_connected",
                    url=WS_URL,
                    num_bboxes=len(BOUNDING_BOXES),
                )

                async for raw_msg in ws:
                    if shutdown_event.is_set():  # SIGINT received — stop processing
                        break

                    try:
                        data = json.loads(raw_msg)  # Parse JSON string → dict
                        msg = AISMessage.model_validate(
                            data
                        )  # Validate schema with Pydantic
                        record = msg.to_record()  # Flatten to dict
                        buffer.add(record)  # Add to in-memory buffer

                        # Log every 100 records — too frequent logging wastes I/O
                        if buffer.size % 100 == 0:
                            logger.debug("buffer_status", size=buffer.size)

                    except Exception:
                        logger.exception("message_parse_error")
                        continue

            except websockets.ConnectionClosed:
                logger.warning("websocket_disconnected", action="reconnecting")
                continue

            if shutdown_event.is_set():
                break

    except asyncio.CancelledError:
        pass
    finally:
        flush_task.cancel()
        flushed = buffer.flush()
        logger.info("final_flush", records_flushed=flushed)


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------


def main() -> None:
    """Run the AIS consumer with graceful SIGINT handling.

    SIGNAL HANDLING ARCHITECTURE:
        Without this, Ctrl+C raises KeyboardInterrupt mid-operation,
        potentially losing buffered records. Instead:
        1. SIGINT/SIGTERM sets shutdown_event
        2. The consume() loop checks shutdown_event after each message
        3. When set, it breaks cleanly and runs the final flush in `finally`

        This same pattern applies to the Prefect flows in Week 4
        and the FastAPI lifespan shutdown in Week 7.
    """
    shutdown_event = asyncio.Event()  # Shared flag between signal handler and consume()

    def handle_signal(sig: int, _frame: Any) -> None:
        """Called by OS when Ctrl+C (SIGINT=2) or docker stop (SIGTERM=15) received."""
        logger.info("shutdown_signal_received", signal=sig)
        shutdown_event.set()  # Signal the consumer loop to stop after current message

    # Register our handler for these two signals
    signal.signal(signal.SIGINT, handle_signal)  # Ctrl+C in terminal
    signal.signal(
        signal.SIGTERM, handle_signal
    )  # Docker stop / Kubernetes pod termination

    logger.info(
        "ais_consumer_starting",
        ports=len(BOUNDING_BOXES),
        locode_path=str(_LOCODE_PATH),
    )
    asyncio.run(consume(shutdown_event))  # Start the async event loop
    logger.info("ais_consumer_stopped")


if __name__ == "__main__":
    main()
