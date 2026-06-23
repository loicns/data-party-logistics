"""AIS stream ingestion client.

Connects to AISStream.io via WebSocket, subscribes to vessel position
reports for configured pilot ports, validates with Pydantic,
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
from serverless.ports import PORTS

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
VOYAGE_SOURCE_NAME = "ais_voyage"

# AISStream message labels are string names, not raw AIS numeric types. Keep the
# parsers broad so v2 can normalize Class B/static payloads if they arrive, but
# keep the live subscription on the known-good v1 PositionReport feed. Requesting
# the broader static/voyage list caused AISStream to close the socket before data
# arrived, producing zero-file hourly runs.
POSITION_MESSAGE_TYPES = {
    "PositionReport",
    "StandardClassBPositionReport",
    "ExtendedClassBPositionReport",
}
VOYAGE_MESSAGE_TYPES = {
    "ShipStaticData",
    "StaticDataReport",
    "ShipStaticAndVoyageData",
    "ShipStaticAndVoyageRelatedData",
    "VoyageData",
}
SUBSCRIBED_MESSAGE_TYPES = ["PositionReport"]

_LOCODE_PATH = (
    Path(__file__).parent.parent.parent / "warehouse" / "seeds" / "un_locode.csv"
)
BOUNDING_BOXES = load_port_bboxes(_LOCODE_PATH, include_locodes=set(PORTS))


# ---------------------------------------------------------------------------
# Normalization helpers
# ---------------------------------------------------------------------------


def _coalesce_value(data: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = data.get(key)
        if value is not None and value != "":
            return value
    return None


def _coalesce_str(
    data: dict[str, Any],
    *keys: str,
    default: str | None = "",
) -> str | None:
    value = _coalesce_value(data, *keys)
    return str(value).strip() if value is not None and value != "" else default


def _coalesce_float(
    data: dict[str, Any],
    *keys: str,
    default: float | None = 0.0,
) -> float | None:
    value = _coalesce_value(data, *keys)
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _coalesce_int(
    data: dict[str, Any],
    *keys: str,
    default: int | None = 0,
) -> int | None:
    value = _coalesce_value(data, *keys)
    if value is None or value == "":
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _parse_eta_timestamp(eta_raw: Any, received_at: datetime) -> str | None:
    """Best-effort AIS ETA normalization.

    AIS static messages usually carry month/day/hour/minute without a year.
    We infer the next plausible UTC occurrence relative to the receive time.
    """
    if eta_raw is None or eta_raw == "":
        return None

    if isinstance(eta_raw, str):
        raw = eta_raw.strip()
        if not raw:
            return None
        try:
            return (
                datetime.fromisoformat(raw.replace("Z", "+00:00"))
                .astimezone(UTC)
                .isoformat()
            )
        except ValueError:
            return None

    if not isinstance(eta_raw, dict):
        return None

    month = _coalesce_int(eta_raw, "Month", "month", default=None)
    day = _coalesce_int(eta_raw, "Day", "day", default=None)
    hour = _coalesce_int(eta_raw, "Hour", "hour", default=0)
    minute = _coalesce_int(eta_raw, "Minute", "minute", default=0)

    if month is None or day is None or hour is None or minute is None:
        return None
    if month == 0 or day == 0 or hour >= 24 or minute >= 60:
        return None

    try:
        candidate = datetime(received_at.year, month, day, hour, minute, tzinfo=UTC)
    except ValueError:
        return None

    if candidate < received_at:
        try:
            candidate = datetime(
                received_at.year + 1,
                month,
                day,
                hour,
                minute,
                tzinfo=UTC,
            )
        except ValueError:
            return None

    return candidate.isoformat()


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

    MessageType: str | int  # e.g., "PositionReport", "VoyageData", 18, 5
    MetaData: AISMetaData  # Always present — has MMSI, ship name, lat/lon
    Message: dict[str, Any] = Field(default_factory=dict)  # Inner message — type varies

    @property
    def message_type_name(self) -> str:
        return str(self.MessageType)

    def _payload(self, names: set[str]) -> dict[str, Any]:
        """Return the nested AISStream payload for any accepted message name."""
        for name in names:
            value = self.Message.get(name)
            if isinstance(value, dict):
                return value
        return self.Message if isinstance(self.Message, dict) else {}

    def to_position_record(self) -> dict[str, Any] | None:
        """Flatten into a dict suitable for NDJSON storage.

        WHY FLATTEN: Raw AISStream JSON is nested ({MetaData: {MMSI: ...}}).
        The S3 NDJSON and downstream Postgres staging tables (Week 3) expect
        flat rows — one key per column. Flattening happens once at ingestion.
        """
        if (
            self.message_type_name not in POSITION_MESSAGE_TYPES
            and self.message_type_name
            not in {
                "1",
                "2",
                "3",
                "18",
            }
        ):
            return None

        pos = self._payload(POSITION_MESSAGE_TYPES)
        return {
            "mmsi": self.MetaData.MMSI,  # Primary key for vessel tracking
            # .strip() removes trailing spaces
            "ship_name": self.MetaData.ShipName.strip(),
            "lat": _coalesce_float(pos, "Latitude", default=self.MetaData.latitude),
            "lon": _coalesce_float(pos, "Longitude", default=self.MetaData.longitude),
            "sog": _coalesce_float(
                pos,
                "Sog",
                "SpeedOverGround",
                default=0.0,
            ),
            "cog": _coalesce_float(pos, "Cog", "CourseOverGround", default=0.0),
            "true_heading": _coalesce_int(pos, "TrueHeading", default=511),
            "nav_status": _coalesce_int(
                pos,
                "NavigationalStatus",
                "NavigationStatus",
                default=15,
            ),
            "msg_type": self.MessageType,
            "received_at": datetime.now(
                UTC
            ).isoformat(),  # ARRIVAL TIME, not event time
            # NOTE: received_at is when WE got the msg, not when vessel broadcast it.
            # This handles S3 partitions by arrival time for reproducible increments.
        }

    def to_record(self) -> dict[str, Any]:
        """Backward-compatible alias for existing tests/callers."""
        record = self.to_position_record()
        if record is None:
            raise ValueError(f"MessageType {self.MessageType} is not a position report")
        return record

    def to_voyage_record(
        self,
        received_at: datetime | None = None,
    ) -> dict[str, Any] | None:
        """Flatten static/voyage messages into the additive v2 raw source."""
        if (
            self.message_type_name not in VOYAGE_MESSAGE_TYPES
            and self.message_type_name != "5"
        ):
            return None

        received_at = received_at or datetime.now(UTC)
        payload = self._payload(VOYAGE_MESSAGE_TYPES)
        dimension_raw = payload.get("Dimension")
        dimension: dict[str, Any] = (
            dimension_raw if isinstance(dimension_raw, dict) else {}
        )
        eta_raw = _coalesce_value(payload, "Eta", "ETA", "EstimatedTimeOfArrival")
        eta_raw_value = (
            json.dumps(eta_raw, default=str) if isinstance(eta_raw, dict) else eta_raw
        )
        dimension_to_bow = _coalesce_int(dimension, "A", default=None)
        dimension_to_stern = _coalesce_int(dimension, "B", default=None)
        dimension_to_port = _coalesce_int(dimension, "C", default=None)
        dimension_to_starboard = _coalesce_int(dimension, "D", default=None)

        return {
            "mmsi": self.MetaData.MMSI,
            "ship_name": _coalesce_str(
                payload,
                "Name",
                "ShipName",
                default=self.MetaData.ShipName.strip(),
            ),
            "call_sign": _coalesce_str(payload, "CallSign", "Callsign", default=None),
            "imo_number": _coalesce_str(
                payload,
                "ImoNumber",
                "IMONumber",
                "IMO",
                default=None,
            ),
            "ship_type": _coalesce_str(payload, "Type", "ShipType", default=None),
            "destination": _coalesce_str(payload, "Destination", default=None),
            "eta_raw": eta_raw_value,
            "eta_timestamp_utc": _parse_eta_timestamp(eta_raw, received_at),
            "draught_m": _coalesce_float(
                payload,
                "MaximumStaticDraught",
                "MaximumDraught",
                "Draught",
                default=None,
            ),
            "dimension_to_bow_m": _coalesce_int(
                payload,
                "DimensionToBow",
                default=dimension_to_bow,
            ),
            "dimension_to_stern_m": _coalesce_int(
                payload,
                "DimensionToStern",
                default=dimension_to_stern,
            ),
            "dimension_to_port_m": _coalesce_int(
                payload,
                "DimensionToPort",
                default=dimension_to_port,
            ),
            "dimension_to_starboard_m": _coalesce_int(
                payload,
                "DimensionToStarboard",
                default=dimension_to_starboard,
            ),
            "msg_type": self.MessageType,
            "received_at": received_at.isoformat(),
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
        self._files_written = 0

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
            self._files_written += 1
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

    @property
    def total_flushed(self) -> int:
        return self._total_flushed

    @property
    def files_written(self) -> int:
        return self._files_written


# ---------------------------------------------------------------------------
# Main consumer loop
# ---------------------------------------------------------------------------


async def consume(
    shutdown_event: asyncio.Event, max_duration_seconds: int = 300
) -> dict[str, int]:
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
        return {"records_written": 0, "files_written": 0}

    # AISStream subscription message — tells the server what to send
    subscribe_msg = json.dumps(
        {
            "APIKey": api_key,  # Authentication
            # Geographic filter — keep the live subscription small and focused.
            # Sending every UN/LOCODE box makes AISStream close the socket.
            "BoundingBoxes": BOUNDING_BOXES,
            # Keep v1 position reports and add low-risk AIS v2 payloads in parallel.
            "FilterMessageTypes": SUBSCRIBED_MESSAGE_TYPES,
        }
    )

    position_buffer = RecordBuffer(source=SOURCE_NAME)
    voyage_buffer = RecordBuffer(source=VOYAGE_SOURCE_NAME)
    records_received = 0
    position_records_received = 0
    voyage_records_received = 0
    result = {
        "records_received": 0,
        "records_written": 0,
        "files_written": 0,
        "voyage_records_written": 0,
        "voyage_files_written": 0,
    }

    async def periodic_flush() -> None:
        """Flush buffer to S3 every FLUSH_INTERVAL_SEC seconds.

        WHY A SEPARATE TASK:
        The WebSocket message loop blocks on `async for raw_msg in ws`.
        A separate task handles the timer-based flush independently.
        asyncio.sleep() yields control to the event loop — the WebSocket loop continues.
        """
        while not shutdown_event.is_set():  # Loop until SIGINT/SIGTERM received
            await asyncio.sleep(FLUSH_INTERVAL_SEC)  # Yield for 60 seconds
            position_buffer.flush()  # Then flush what's accumulated
            voyage_buffer.flush()

    async def watchdog_timer() -> None:
        """Gracefully shuts down the stream after max duration."""
        if max_duration_seconds > 0:
            await asyncio.sleep(max_duration_seconds)
            logger.info("batch_duration_reached", duration_seconds=max_duration_seconds)
            shutdown_event.set()

    # Create the flush task — runs concurrently with the WebSocket loop below
    flush_task = asyncio.create_task(periodic_flush())
    watchdog_task = asyncio.create_task(watchdog_timer())

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
                        received_at = datetime.now(UTC)
                        position_record = msg.to_position_record()
                        voyage_record = msg.to_voyage_record(received_at)

                        if position_record is not None:
                            position_buffer.add(position_record)
                            position_records_received += 1
                        if voyage_record is not None:
                            voyage_buffer.add(voyage_record)
                            voyage_records_received += 1

                        records_received += 1

                        # Log every 500 records to avoid log spam in production
                        if records_received % 500 == 0:
                            logger.debug(
                                "buffer_status",
                                position_size=position_buffer.size,
                                voyage_size=voyage_buffer.size,
                            )

                    except Exception:
                        logger.exception("message_parse_error")
                        continue

            except websockets.ConnectionClosed as exc:
                if shutdown_event.is_set():
                    # Intentional shutdown — watchdog closed the connection.
                    # Don't reconnect; exit the outer loop cleanly.
                    break
                logger.warning(
                    "websocket_disconnected",
                    action="reconnecting",
                    code=exc.code,
                    reason=exc.reason,
                )
                continue

            if shutdown_event.is_set():
                break

    except asyncio.CancelledError:
        logger.info("consume_cancelled")
        raise
    finally:
        flush_task.cancel()
        watchdog_task.cancel()
        position_flushed = position_buffer.flush()
        voyage_flushed = voyage_buffer.flush()
        logger.info(
            "final_flush",
            position_records_flushed=position_flushed,
            voyage_records_flushed=voyage_flushed,
        )
        result = {
            "records_received": records_received,
            "position_records_received": position_records_received,
            "voyage_records_received": voyage_records_received,
            # Backward-compatible v1 summary keys for existing metrics/runbooks.
            "records_written": position_buffer.total_flushed,
            "files_written": position_buffer.files_written,
            "voyage_records_written": voyage_buffer.total_flushed,
            "voyage_files_written": voyage_buffer.files_written,
            "total_records_written": (
                position_buffer.total_flushed + voyage_buffer.total_flushed
            ),
            "total_files_written": (
                position_buffer.files_written + voyage_buffer.files_written
            ),
        }
    return result


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
