"""Batch ingestion flow — runs all API clients concurrently.

Scheduled hourly. Each client is a separate task with retries.
"""

import asyncio
from datetime import UTC, datetime

from ingestion.config import Settings
from prefect import flow, get_run_logger, task
from prefect.artifacts import create_markdown_artifact

# ---------------------------------------------------------------------------
# Tasks — one per ingestion client
# ---------------------------------------------------------------------------


@task(
    retries=3,
    retry_delay_seconds=[10, 30, 60],
    tags=["ingestion", "cmems"],
)
def ingest_cmems() -> dict:
    """Fetch latest ocean currents and wave data from CMEMS."""
    logger = get_run_logger()
    logger.info("Starting CMEMS ingestion")

    from ingestion.clients.cmems import CMEMSIngestionClient

    client = CMEMSIngestionClient()
    s3_key = client.run()

    logger.info(f"CMEMS: {s3_key}")
    return {"s3_key": s3_key, "records": "Unknown"}


@task(
    retries=3,
    retry_delay_seconds=[10, 30, 60],
    tags=["ingestion", "weather"],
)
def ingest_weather() -> dict:
    """Fetch latest marine weather observations from Open-Meteo."""
    logger = get_run_logger()
    logger.info("Starting Marine Weather ingestion")

    from ingestion.clients.weather import WeatherIngestionClient

    settings = Settings()
    client = WeatherIngestionClient(settings)
    s3_key = client.run()

    logger.info(f"Weather: {s3_key}")
    return {"s3_key": s3_key, "records": "Unknown"}


@task(
    retries=3,
    retry_delay_seconds=[10, 30, 60],
    tags=["ingestion", "noaa_tides"],
)
def ingest_noaa_tides() -> dict:
    """Fetch latest tidal predictions from NOAA."""
    logger = get_run_logger()
    logger.info("Starting NOAA Tides ingestion")

    from ingestion.clients.noaa_tides import NOAAIngestionClient

    client = NOAAIngestionClient()
    s3_key = client.run()

    logger.info(f"NOAA Tides: {s3_key}")
    return {"s3_key": s3_key, "records": "Unknown"}


@task(
    retries=2,
    retry_delay_seconds=[30, 60],
    tags=["ingestion", "ais"],
)
def ingest_ais_batch(duration_sec: int = 300) -> dict:
    """Fetch a 5-minute snapshot of AIS vessel positions.

    Runs the async AIS consumer for exactly `duration_sec` seconds, then
    stops cleanly. The watchdog timer inside consume() handles the timeout.

    WHY SYNC TASK WITH asyncio.run():
        Prefect tasks run in worker threads; threads have no event loop.
        asyncio.run() creates a fresh loop, runs the coroutine, then disposes
        the loop. This is the correct way to call async code from a sync task.
        We keep this task sync so the rest of ingest_batch() stays sync too,
        avoiding Prefect async/sync mixing issues.
    """
    logger = get_run_logger()
    logger.info(f"Starting AIS {duration_sec}s batch snapshot")

    from ingestion.clients.ais_stream import consume

    shutdown_event = asyncio.Event()
    # asyncio.run() blocks until consume() finishes (after duration_sec seconds)
    asyncio.run(
        consume(
            shutdown_event=shutdown_event,
            max_duration_seconds=duration_sec,
        )
    )

    return {"s3_key": "raw/source=ais/latest", "records": "Unknown"}


# ---------------------------------------------------------------------------
# Flow
# ---------------------------------------------------------------------------


@flow(
    name="ingest-batch",
    log_prints=True,
    timeout_seconds=1200,  # 15 minute hard timeout (AIS=60s + CMEMS=~6min + buffer)
)
def ingest_batch() -> dict:
    """Run all ingestion clients concurrently.

    Each task retries independently up to 3 times with backoff.
    If one client fails after all retries, the others still complete.
    """
    logger = get_run_logger()
    start = datetime.now(UTC)
    logger.info(f"Batch ingestion starting at {start.isoformat()}")

    # Submit all tasks concurrently.
    # .submit() is non-blocking — all four tasks start immediately in parallel.
    # AIS duration: 60s for testing, change to 300 for production
    ais_future = ingest_ais_batch.submit(duration_sec=60)
    cmems_future = ingest_cmems.submit()
    weather_future = ingest_weather.submit()
    noaa_tides_future = ingest_noaa_tides.submit()

    # Collect results — .result() blocks until the task completes
    results = {}
    failures = []

    for name, future in [
        ("ais", ais_future),
        ("cmems", cmems_future),
        ("weather", weather_future),
        ("noaa_tides", noaa_tides_future),
    ]:
        try:
            results[name] = future.result()
        except Exception as e:
            logger.error(f"{name} failed after all retries: {e}")
            failures.append(name)
            results[name] = {"status": "failed", "error": str(e)}

    # Build summary
    end = datetime.now(UTC)
    duration = (end - start).total_seconds()

    total_records = sum(
        r.get("records", 0)
        for r in results.values()
        if isinstance(r.get("records"), int)
    )

    summary = f"""# Batch Ingestion Summary

| Metric | Value |
|---|---|
| **Timestamp** | {end.isoformat()} |
| **Duration** | {duration:.1f}s |
| **Sources OK** | {4 - len(failures)}/4 |
| **Sources Failed** | {len(failures)} ({", ".join(failures) if failures else "none"}) |
| **Total Records** | N/A |

## Per-Source Results

| Source | Status | Records | S3 Key |
|---|---|---|---|
"""
    for name, r in results.items():
        status = "FAIL" if name in failures else "OK"
        records = r.get("records", "N/A")
        s3_key = r.get("s3_key", "N/A")
        summary += f"| {name} | {status} | {records} | `{s3_key}` |\n"

    # Create a Prefect artifact for the dashboard
    create_markdown_artifact(
        key="batch-ingestion-summary",
        markdown=summary,
        description="Latest batch ingestion run results",
    )

    logger.info(f"Batch complete: {4 - len(failures)}/4 OK in {duration:.1f}s")

    if failures:
        logger.warning(f"Failed sources: {failures}")

    return {
        "results": results,
        "failures": failures,
        "total_records": total_records,
        "duration_seconds": duration,
    }


if __name__ == "__main__":
    ingest_batch()
