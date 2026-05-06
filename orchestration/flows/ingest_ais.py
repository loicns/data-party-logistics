"""AIS streaming flow — continuous WebSocket ingestion.

This flow runs indefinitely, reconnecting on failure.
It's designed to be deployed as a long-running flow, not scheduled.

ARCHITECTURE NOTE:
    The actual WebSocket logic lives in ingestion/clients/ais_stream.py.
    This flow is the Prefect orchestration wrapper around that client.
    The separation keeps business logic (what to ingest) out of orchestration
    (how and when to run it). This is the standard "clean architecture" pattern.
"""

import asyncio
from datetime import UTC, datetime

from prefect import flow, get_run_logger, task
from prefect.artifacts import create_markdown_artifact


@task(
    retries=5,
    retry_delay_seconds=[10, 30, 60, 120, 300],  # up to 5 min backoff
    tags=["ingestion", "ais"],
)
def stream_ais_messages(duration_seconds: int = 0) -> dict:
    """Connect to AIS WebSocket and stream position reports.

    Args:
        duration_seconds: How long to run, in seconds.
                          0 = run forever (continuous mode).
                          300 = run for 5 minutes (batch mode for ingest_batch.py).

    Runs the async `consume()` loop inside a fresh asyncio event loop.

    WHY asyncio.run() HERE:
        Prefect tasks run in worker threads. A thread does not have an event
        loop, so we must create one with asyncio.run(). This is the correct
        pattern for calling async code from inside a synchronous Prefect task.
    """
    logger = get_run_logger()
    dur = "∞" if duration_seconds == 0 else f"{duration_seconds}s"
    logger.info(f"Starting AIS stream (duration={dur})")

    # Import here (not at top of file) to avoid loading heavy modules at
    # collection time — keeps Prefect's flow registration fast.
    from ingestion.clients.ais_stream import consume

    shutdown_event = asyncio.Event()
    start = datetime.now(UTC)

    try:
        # asyncio.run() creates a brand-new event loop, runs consume() to
        # completion, then destroys the loop. Safe to call from a thread.
        asyncio.run(
            consume(
                shutdown_event=shutdown_event,
                max_duration_seconds=duration_seconds,
            )
        )
    except Exception as e:
        logger.error(f"AIS stream error: {e}")
        raise  # Re-raise so Prefect can handle retries

    duration = (datetime.now(UTC) - start).total_seconds()
    logger.info(f"AIS stream ended after {duration:.0f}s")

    return {
        "status": "ok",
        "duration_seconds": duration,
        "s3_key": "raw/source=ais/latest",
    }


@flow(
    name="ingest-ais",
    log_prints=True,
    timeout_seconds=86400,  # 24-hour max runtime for continuous mode
)
def ingest_ais(duration_seconds: int = 0) -> dict:
    """Long-running AIS streaming flow.

    Connects to the AIS WebSocket and continuously ingests vessel
    position reports. Reconnects automatically on failure via task retries.

    Args:
        duration_seconds: 0 = run forever, N = stop after N seconds.
    """
    logger = get_run_logger()
    logger.info("Starting AIS streaming flow")

    start = datetime.now(UTC)

    result = stream_ais_messages(duration_seconds=duration_seconds)

    end = datetime.now(UTC)
    duration = (end - start).total_seconds()

    summary = f"""# AIS Streaming Summary

| Metric | Value |
|---|---|
| **Start** | {start.isoformat()} |
| **End** | {end.isoformat()} |
| **Duration** | {duration:.0f}s ({duration / 3600:.1f}h) |
| **Status** | {result.get("status", "unknown")} |
"""

    create_markdown_artifact(
        key="ais-streaming-summary",
        markdown=summary,
        description="AIS streaming session results",
    )

    logger.info(f"AIS stream ended after {duration:.0f}s")
    return result


if __name__ == "__main__":
    ingest_ais()
