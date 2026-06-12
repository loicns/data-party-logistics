"""S3 health helpers used by serverless handlers."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any

import boto3


def latest_object_for_prefix(bucket: str, prefix: str) -> dict[str, Any] | None:
    """Find the most-recent object under a date-partitioned prefix.

    Probes today's and yesterday's Hive partitions (date=YYYY-MM-DD/) so the
    scan is bounded (~24 objects max) regardless of how many historical
    partitions exist. The old approach listed the first 1000 keys
    alphabetically and would return a weeks-old object once the partition count
    exceeded 1000.
    """
    s3 = boto3.client("s3")
    for delta in (0, 1):
        day = (date.today() - timedelta(days=delta)).strftime("%Y-%m-%d")
        resp = s3.list_objects_v2(Bucket=bucket, Prefix=f"{prefix}date={day}/")
        contents = resp.get("Contents", [])
        if contents:
            return max(contents, key=lambda obj: obj["LastModified"])
    return None


def object_age_minutes(obj: dict[str, Any] | None) -> float | None:
    if not obj:
        return None
    modified = obj["LastModified"]
    if modified.tzinfo is None:
        modified = modified.replace(tzinfo=UTC)
    return max(0.0, (datetime.now(UTC) - modified).total_seconds() / 60.0)
