"""Tests for the partition-aware S3 freshness probe."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from unittest.mock import MagicMock, patch

from serverless.s3_health import latest_object_for_prefix, object_age_minutes


def _obj(age_minutes: float) -> dict:
    return {"LastModified": datetime.now(UTC) - timedelta(minutes=age_minutes)}


def _make_s3(today_contents=(), yesterday_contents=()):
    """Return a mock boto3 S3 client whose list_objects_v2 honours date= partitions."""

    def _list(**kwargs):
        prefix = kwargs.get("Prefix", "")
        today_str = date.today().strftime("%Y-%m-%d")
        yesterday_str = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
        if f"date={today_str}/" in prefix:
            return {"Contents": list(today_contents)}
        if f"date={yesterday_str}/" in prefix:
            return {"Contents": list(yesterday_contents)}
        return {}

    s3 = MagicMock()
    s3.list_objects_v2.side_effect = _list
    return s3


@patch("serverless.s3_health.boto3")
def test_returns_today_partition(mock_boto3):
    recent = _obj(15)
    older = _obj(60)
    mock_boto3.client.return_value = _make_s3(today_contents=[older, recent])

    result = latest_object_for_prefix("my-bucket", "raw/source=ais/")

    assert result is recent


@patch("serverless.s3_health.boto3")
def test_falls_back_to_yesterday(mock_boto3):
    yesterday_obj = _obj(90)
    mock_boto3.client.return_value = _make_s3(
        today_contents=[],
        yesterday_contents=[yesterday_obj],
    )

    result = latest_object_for_prefix("my-bucket", "raw/source=ais/")

    assert result is yesterday_obj


@patch("serverless.s3_health.boto3")
def test_returns_none_when_both_empty(mock_boto3):
    mock_boto3.client.return_value = _make_s3()

    result = latest_object_for_prefix("my-bucket", "raw/source=ais/")

    assert result is None


def test_object_age_minutes_none():
    assert object_age_minutes(None) is None


def test_object_age_minutes_recent():
    obj = _obj(30)
    age = object_age_minutes(obj)
    assert 29 < age < 31
