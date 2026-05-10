"""Athena query helpers for the pilot export."""

from __future__ import annotations

import csv
import time
from io import StringIO
from urllib.parse import urlparse

import boto3


def _parse_s3_uri(uri: str) -> tuple[str, str]:
    parsed = urlparse(uri)
    if parsed.scheme != "s3":
        raise ValueError(f"Expected s3:// URI, got {uri}")
    return parsed.netloc, parsed.path.lstrip("/")


def run_query(
    sql_text: str,
    *,
    database: str,
    output_location: str,
) -> list[dict[str, str]]:
    athena = boto3.client("athena")
    response = athena.start_query_execution(
        QueryString=sql_text,
        QueryExecutionContext={"Database": database},
        ResultConfiguration={"OutputLocation": output_location},
    )
    execution_id = response["QueryExecutionId"]

    for _ in range(90):
        status = athena.get_query_execution(QueryExecutionId=execution_id)
        state = status["QueryExecution"]["Status"]["State"]
        if state == "SUCCEEDED":
            break
        if state in {"FAILED", "CANCELLED"}:
            reason = status["QueryExecution"]["Status"].get(
                "StateChangeReason",
                "unknown",
            )
            raise RuntimeError(f"Athena query failed: {reason}")
        time.sleep(2)
    else:
        raise TimeoutError("Timed out waiting for Athena query to finish")

    bucket, key = _parse_s3_uri(f"{output_location.rstrip('/')}/{execution_id}.csv")
    s3 = boto3.client("s3")
    body = s3.get_object(Bucket=bucket, Key=key)["Body"].read().decode("utf-8")

    reader = csv.DictReader(StringIO(body))
    return [dict(row) for row in reader]


def first_row(
    sql_text: str,
    *,
    database: str,
    output_location: str,
) -> dict[str, str] | None:
    rows = run_query(sql_text, database=database, output_location=output_location)
    return rows[0] if rows else None
