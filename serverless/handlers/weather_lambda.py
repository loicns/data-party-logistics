"""Lambda entrypoint for weather ingestion."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from ingestion.clients.weather import OpenMeteoClient
from ingestion.s3_writer import write_ndjson_batch

from serverless.metrics import put_metric


def lambda_handler(_event: dict[str, Any], _context: Any) -> dict[str, Any]:
    client = OpenMeteoClient()
    records = client.fetch_all_ports(forecast_days=2)
    payload = [record.model_dump() for record in records]
    if not payload:
        raise RuntimeError("Weather ingestion returned zero records")
    key = write_ndjson_batch(
        payload,
        source="weather",
        batch_id=datetime.now(UTC).strftime("%Y%m%dT%H%M%S"),
    )

    put_metric("WeatherRunSuccess", 1)
    put_metric("WeatherRecordsWritten", len(payload))

    return {"status": "ok", "record_count": len(payload), "s3_key": key}
