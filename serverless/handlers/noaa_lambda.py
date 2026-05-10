"""Lambda entrypoint for NOAA tidal predictions."""

from __future__ import annotations

from typing import Any

from ingestion.clients.noaa_tides import NOAAIngestionClient

from serverless.metrics import put_metric


def lambda_handler(_event: dict[str, Any], _context: Any) -> dict[str, Any]:
    client = NOAAIngestionClient()
    key = client.run(days_ahead=2)

    put_metric("NoaaRunSuccess", 1)
    put_metric("NoaaFilesWritten", 1 if key else 0)

    return {"status": "ok", "s3_key": key}
