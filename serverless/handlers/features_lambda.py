"""Rebuild the Athena gold feature tables from raw, on a schedule.

For each table, in dependency order:
  1. DROP TABLE IF EXISTS              (Athena)
  2. clear its external_location S3 prefix  (CTAS requires an empty location)
  3. CREATE TABLE AS ...               (re-run the canonical CTAS SQL)

The SQL is the single source of truth in athena/queries/ — shipped in the
Lambda package (see Makefile LAMBDA_MODULES). We never duplicate it here.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import boto3

from serverless.athena import run_ddl
from serverless.metrics import put_metric

DATABASE = os.environ["ATHENA_DATABASE"]
OUTPUT_LOCATION = os.environ["ATHENA_OUTPUT_LOCATION"]

# Repo root inside the package: serverless/handlers/features_lambda.py -> parents[2]
QUERIES_DIR = Path(__file__).resolve().parents[2] / "athena" / "queries"

# (table name, sql filename) — MUST stay in dependency order:
# congestion_target reads feature_vessel_inbound_hourly; port_status reads it too.
TABLES: list[tuple[str, str]] = [
    ("feature_vessel_inbound_hourly", "feature_vessel_inbound_hourly.sql"),
    ("feature_port_status_hourly", "feature_port_status_hourly.sql"),
    ("congestion_target", "congestion_target.sql"),
]

_EXTERNAL_LOCATION = re.compile(r"external_location\s*=\s*'([^']+)'", re.IGNORECASE)


def _read_sql(filename: str) -> str:
    return (QUERIES_DIR / filename).read_text(encoding="utf-8")


def _parse_s3_uri(uri: str) -> tuple[str, str]:
    parsed = urlparse(uri)
    if parsed.scheme != "s3":
        raise ValueError(f"Expected s3:// URI, got {uri}")
    return parsed.netloc, parsed.path.lstrip("/")


def _clear_prefix(s3_uri: str) -> int:
    """Delete every object under an s3:// prefix. Returns count deleted."""
    bucket, prefix = _parse_s3_uri(s3_uri)
    s3 = boto3.client("s3")
    paginator = s3.get_paginator("list_objects_v2")
    deleted = 0
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        objects = [{"Key": obj["Key"]} for obj in page.get("Contents", [])]
        if objects:
            s3.delete_objects(Bucket=bucket, Delete={"Objects": objects})
            deleted += len(objects)
    return deleted


def _rebuild_one(table: str, sql: str) -> dict[str, Any]:
    match = _EXTERNAL_LOCATION.search(sql)
    if not match:
        raise ValueError(f"No external_location found in SQL for {table}")
    location = match.group(1)

    run_ddl(
        f"DROP TABLE IF EXISTS {DATABASE}.{table}",
        database=DATABASE,
        output_location=OUTPUT_LOCATION,
    )
    deleted = _clear_prefix(location)
    run_ddl(sql, database=DATABASE, output_location=OUTPUT_LOCATION)

    return {"table": table, "objects_cleared": deleted, "status": "rebuilt"}


def lambda_handler(_event: dict[str, Any], _context: Any) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    for table, filename in TABLES:
        # No per-table try/except: the tables depend on each other in order, so
        # if one fails the rest cannot be trusted — fail the whole run loudly.
        results.append(_rebuild_one(table, _read_sql(filename)))

    put_metric("FeatureRebuildSuccess", 1)
    return {"status": "ok", "tables": results}
