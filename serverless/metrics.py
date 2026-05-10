"""Small helpers for CloudWatch custom metrics."""

from __future__ import annotations

from datetime import UTC, datetime

import boto3

NAMESPACE = "DPL/Pilot"


def put_metric(
    metric_name: str,
    value: float,
    *,
    unit: str = "Count",
    dimensions: list[dict[str, str]] | None = None,
) -> None:
    cloudwatch = boto3.client("cloudwatch")
    cloudwatch.put_metric_data(
        Namespace=NAMESPACE,
        MetricData=[
            {
                "MetricName": metric_name,
                "Timestamp": datetime.now(UTC),
                "Value": value,
                "Unit": unit,
                "Dimensions": dimensions or [],
            }
        ],
    )
