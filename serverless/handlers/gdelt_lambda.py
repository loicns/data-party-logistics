"""Lambda entrypoint for GDELT maritime event ingestion."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Any

from ingestion.clients.gdelt_events import GdeltEventsClient
from ingestion.s3_writer import write_ndjson_batch

from serverless.metrics import put_metric


def lambda_handler(_event: dict[str, Any], _context: Any) -> dict[str, Any]:
    timespan = os.getenv("GDELT_TIMESPAN", "1d")
    max_records = int(os.getenv("GDELT_MAX_RECORDS_PER_QUERY", "75"))

    client = GdeltEventsClient()
    records = client.fetch_events(
        timespan=timespan,
        max_records_per_query=max_records,
    )
    if not records:
        raise RuntimeError("GDELT ingestion returned zero records")

    payload = [record.model_dump(mode="json") for record in records]
    key = write_ndjson_batch(
        payload,
        source="gdelt_events",
        batch_id=datetime.now(UTC).strftime("%Y%m%dT%H%M%S"),
    )

    attributed_count = sum(1 for record in records if record.port_code)
    put_metric("GdeltRunSuccess", 1)
    put_metric("GdeltRecordsWritten", len(payload))
    put_metric("GdeltAttributedRecords", attributed_count)

    return {
        "status": "ok",
        "record_count": len(payload),
        "attributed_count": attributed_count,
        "s3_key": key,
    }
