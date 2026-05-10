"""S3 health helpers used by serverless handlers."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import boto3


def latest_object_for_prefix(bucket: str, prefix: str) -> dict[str, Any] | None:
    s3 = boto3.client("s3")
    response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix, MaxKeys=1000)
    contents = response.get("Contents", [])
    if not contents:
        return None
    return max(contents, key=lambda obj: obj["LastModified"])


def object_age_minutes(obj: dict[str, Any] | None) -> float | None:
    if not obj:
        return None
    modified = obj["LastModified"]
    if modified.tzinfo is None:
        modified = modified.replace(tzinfo=UTC)
    return max(0.0, (datetime.now(UTC) - modified).total_seconds() / 60.0)
