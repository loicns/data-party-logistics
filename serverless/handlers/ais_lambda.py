"""Lambda entrypoint for hourly AIS snapshots."""

from __future__ import annotations

import asyncio
import os
from typing import Any

from ingestion.clients.ais_stream import consume

from serverless.metrics import put_metric


def lambda_handler(event: dict[str, Any], _context: Any) -> dict[str, Any]:
    duration_seconds = int(
        event.get("duration_seconds") or os.getenv("AIS_DURATION_SECONDS", "300")
    )
    shutdown_event = asyncio.Event()
    result = asyncio.run(
        consume(
            shutdown_event=shutdown_event,
            max_duration_seconds=duration_seconds,
        )
    )
    summary = result or {}

    put_metric("AisRunSuccess", 1)
    put_metric("AisFilesWritten", float(summary.get("files_written", 0)))
    put_metric("AisRecordsWritten", float(summary.get("records_written", 0)))

    return {
        "status": "ok",
        "duration_seconds": duration_seconds,
        "summary": summary,
    }
