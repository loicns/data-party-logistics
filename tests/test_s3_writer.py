"""Tests for ingestion.s3_writer using moto to mock S3."""

from __future__ import annotations

import json

import boto3
import pytest
from ingestion.s3_writer import write_ndjson_batch
from moto import mock_aws


@pytest.fixture
def _s3_bucket(monkeypatch: pytest.MonkeyPatch):
    """Create a mocked S3 bucket and patch settings."""
    with mock_aws():
        bucket_name = "dpl-raw-test-123456789012"
        region = "eu-west-3"

        monkeypatch.setenv("S3_BUCKET_RAW", bucket_name)
        monkeypatch.setenv("AWS_REGION", region)
        monkeypatch.setenv("AWS_DEFAULT_REGION", region)

        # Reload settings so monkeypatched env vars take effect
        import ingestion.config as cfg

        monkeypatch.setattr(cfg, "settings", cfg.Settings())

        s3 = boto3.client("s3", region_name=region)
        s3.create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration={"LocationConstraint": region},
        )
        # USE YIELD INSTEAD OF RETURN
        # This keeps the mock alive during the test
        yield bucket_name


# @mock_aws
class TestWriteNdjsonBatch:
    """Tests for write_ndjson_batch."""

    def test_writes_ndjson_to_correct_partition(self, _s3_bucket: str) -> None:
        """Records land in the expected S3 key with correct NDJSON content."""
        records = [
            {"mmsi": 123456789, "lat": 51.95, "lon": 4.05},
            {"mmsi": 987654321, "lat": 1.26, "lon": 103.84},
        ]

        key = write_ndjson_batch(
            records,
            source="ais",
            bucket=_s3_bucket,
            date_str="2026-04-12",
            batch_id="test001",
        )

        assert key == "raw/source=ais/date=2026-04-12/batch-test001.ndjson"

        # Read back and verify content
        s3 = boto3.client("s3", region_name="eu-west-3")
        obj = s3.get_object(Bucket=_s3_bucket, Key=key)
        body = obj["Body"].read().decode("utf-8")
        lines = body.strip().split("\n")

        assert len(lines) == 2
        assert json.loads(lines[0])["mmsi"] == 123456789
        assert json.loads(lines[1])["mmsi"] == 987654321

    def test_empty_records_raises(self, _s3_bucket: str) -> None:
        """Empty list should raise ValueError."""
        with pytest.raises(ValueError, match="empty batch"):
            write_ndjson_batch([], source="ais", bucket=_s3_bucket)

    def test_auto_generates_batch_id(self, _s3_bucket: str) -> None:
        """When no batch_id is given, a UUID-based one is generated."""
        records = [{"value": 42}]
        key = write_ndjson_batch(
            records,
            source="weather",
            bucket=_s3_bucket,
            date_str="2026-04-12",
        )

        assert key.startswith("raw/source=weather/date=2026-04-12/batch-")
        assert key.endswith(".ndjson")

    def test_defaults_to_today_date(self, _s3_bucket: str) -> None:
        """When no date_str is given, today's UTC date is used."""
        from datetime import UTC, datetime

        today = datetime.now(UTC).strftime("%Y-%m-%d")
        records = [{"value": 1}]
        key = write_ndjson_batch(
            records,
            source="fred",
            bucket=_s3_bucket,
        )

        assert f"date={today}" in key
