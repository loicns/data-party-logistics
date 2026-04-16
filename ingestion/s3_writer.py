"""Reusable S3 writer for NDJSON batches.

All ingestion clients write through this module to ensure consistent
partition layout: raw/source={name}/date={YYYY-MM-DD}/{batch_id}.ndjson
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any

import boto3
import structlog

from ingestion.config import settings

logger = structlog.get_logger(__name__)


def _make_partition_key(source: str, date_str: str | None = None) -> str:
    """Build the S3 partition prefix.

    Args:
        source: Data source name (e.g., "ais", "comtrade", "weather").
        date_str: Optional date override in YYYY-MM-DD format.
                  Defaults to today (UTC).

    Returns:
        Partition prefix like "raw/source=ais/date=2026-04-12/".
    """
    if date_str is None:
        date_str = datetime.now(UTC).strftime("%Y-%m-%d")
    return f"raw/source={source}/date={date_str}/"


def write_ndjson_batch(
    records: list[dict[str, Any]],
    source: str,
    *,
    bucket: str | None = None,
    date_str: str | None = None,
    batch_id: str | None = None,
) -> str:
    """Write a list of dicts as an NDJSON file to S3.

    Args:
        records: List of dictionaries to serialize as NDJSON.
        source: Data source name for the partition path.
        bucket: S3 bucket name. Defaults to settings.s3_bucket_raw.
        date_str: Optional date override (YYYY-MM-DD). Defaults to today UTC.
        batch_id: Optional batch identifier. Defaults to a short UUID.

    Returns:
        The full S3 key that was written.

    Raises:
        ValueError: If records is empty or bucket is not configured.
    """
    if not records:
        msg = "Cannot write an empty batch"
        raise ValueError(msg)

    bucket = bucket or settings.s3_bucket_raw
    if not bucket:
        msg = "S3 bucket not configured — set S3_BUCKET_RAW in .env"
        raise ValueError(msg)

    if batch_id is None:
        batch_id = uuid.uuid4().hex[:12]

    partition = _make_partition_key(source, date_str)
    key = f"{partition}batch-{batch_id}.ndjson"

    # Serialize records to NDJSON (one JSON object per line)
    body = "\n".join(json.dumps(r, default=str) for r in records) + "\n"

    s3 = boto3.client("s3", region_name=settings.aws_region)
    s3.put_object(
        Bucket=bucket,
        Key=key,
        Body=body.encode("utf-8"),
        ContentType="application/x-ndjson",
    )

    logger.info(
        "s3_batch_written",
        bucket=bucket,
        key=key,
        record_count=len(records),
        bytes=len(body),
    )

    return key
