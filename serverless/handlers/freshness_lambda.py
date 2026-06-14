"""Checks S3 freshness and emits metrics for alarms/dashboarding."""

from __future__ import annotations

import os
from typing import Any

from serverless.metrics import put_metric
from serverless.s3_health import latest_object_for_prefix, object_age_minutes


def lambda_handler(_event: dict[str, Any], _context: Any) -> dict[str, Any]:
    bucket = os.getenv("DATA_BUCKET_NAME", "")
    if not bucket:
        raise ValueError("DATA_BUCKET_NAME is required")

    checks = {
        "AisFreshnessMinutes": "raw/source=ais/",
        "AisVoyageFreshnessMinutes": "raw/source=ais_voyage/",
        "WeatherFreshnessMinutes": "raw/source=weather/",
        "NoaaFreshnessMinutes": "raw/source=noaa_tides/",
        "GdeltFreshnessMinutes": "raw/source=gdelt_events/",
        "ExportFreshnessMinutes": os.getenv(
            "DASHBOARD_EXPORT_PREFIX",
            "exports/dashboard/",
        ),
    }

    results: dict[str, float | None] = {}
    for metric_name, prefix in checks.items():
        obj = latest_object_for_prefix(bucket, prefix)
        age = object_age_minutes(obj)
        results[metric_name] = age
        if age is not None:
            put_metric(metric_name, age, unit="Count")

    put_metric("FreshnessRunSuccess", 1)
    return {"status": "ok", "ages_minutes": results}
