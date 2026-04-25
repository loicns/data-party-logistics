"""Load NDJSON files from S3 into Postgres raw tables.

Usage:
    uv run python -m ingestion.loaders.s3_to_postgres \
        --table raw_ais_positions --prefix ais/
    uv run python -m ingestion.loaders.s3_to_postgres \
        --table raw_trade_flows --prefix comtrade/

`uv run python -m` runs the module inside the repo's locked environment rather
than whatever global `python3` happens to be on PATH.
"""

from __future__ import annotations

import argparse  # Standard library: parse command-line arguments (--table, --prefix)
import io  # Standard library: in-memory byte/string streams
import json  # Standard library: JSON parsing
import sys
from typing import Any

import boto3  # AWS SDK for Python — reads S3 files
import psycopg  # Postgres driver (psycopg v3) — connects to RDS
import structlog  # Structured logging library (JSON-format logs)
from psycopg import sql  # psycopg's SQL template system — prevents SQL injection

from ingestion.config import settings  # Settings singleton from W1 S02

logger = structlog.get_logger()
# structlog produces structured (JSON) log output by default.
# Example: {"event": "found_s3_keys", "prefix": "ais/", "count": 42, "timestamp": "..."}
# JSON logs are consumed by CloudWatch Logs Insights in production.

# ─── Column mapping: NDJSON key → Postgres column ────────────────────────────
# Each entry: (json_key_in_ndjson_file, postgres_column_name)
# ORDER MATTERS: the COPY command gets columns in this order.
# If the JSON key and Postgres column have the same name, you still list them.
# If they differ (e.g., "timestamp" → "ts"), you map them explicitly here.
TABLE_COLUMNS: dict[str, list[tuple[str, str]]] = {
    "raw_ais_positions": [
        ("mmsi", "mmsi"),
        ("ship_name", "vessel_name"),
        ("msg_type", "ship_type"),  # msg_type mapped to ship_type as best effort
        ("lat", "latitude"),
        ("lon", "longitude"),
        ("sog", "speed_knots"),
        ("cog", "course_deg"),
        ("true_heading", "heading_deg"),
        ("nav_status", "nav_status"),
        ("received_at", "timestamp"),
    ],
    "raw_comtrade_flows": [
        ("reporter", "reporter_code"),
        ("partner", "partner_code"),
        ("hs_code", "cmd_code"),
        ("trade_value", "primary_value"),
        ("weight", "net_wgt"),
        ("period", "period"),
    ],
    "raw_weather_observations": [
        ("port_code", "port_code"),
        ("timestamp", "observation_hour"),
        ("wave_height_m", "wave_height_m"),
        ("wave_period_s", "wave_period_s"),
        ("wave_direction_deg", "wave_direction_deg"),
    ],
    "raw_gdelt_events": [
        ("event_id", "event_id"),
        ("date", "event_date"),
        ("source_url", "source_url"),
        ("event_code", "event_code"),
        ("lat", "lat"),
        ("lon", "lon"),
    ],
    "raw_fred_indicators": [
        ("series_id", "series_id"),
        ("date", "observation_date"),
        ("value", "value"),
    ],
}


def get_s3_client() -> Any:
    """Create a boto3 S3 client using the project AWS profile."""
    session = boto3.Session(
        profile_name=settings.aws_profile,  # "dpl" — reads ~/.aws/credentials [dpl]
        region_name=settings.aws_region,  # "eu-west-3" — from Settings
    )
    return session.client("s3")


def get_pg_connection() -> psycopg.Connection:
    """Open a connection to the Postgres warehouse.

    Returns a psycopg connection object.
    The caller is responsible for closing it (conn.close()).
    In Week 4, the Prefect flow handles connection lifecycle.
    """
    return psycopg.connect(
        host=settings.postgres_host,  # RDS hostname from .env
        port=settings.postgres_port,  # 5432
        dbname=settings.postgres_db,  # "dpl_dev"
        user=settings.postgres_user,  # "dpl"
        password=settings.postgres_password,  # From .env — NEVER printed in logs
    )


def list_ndjson_keys(s3_client: Any, bucket: str, prefix: str) -> list[str]:
    """List all .ndjson keys under a given S3 prefix.

    WHY A PAGINATOR?
    S3 list_objects_v2 returns at most 1,000 keys per API call.
    If your prefix has 2,500 files (weeks of ingestion), you need multiple calls.
    A paginator handles this automatically — you just iterate pages.
    """
    keys: list[str] = []
    paginator = s3_client.get_paginator("list_objects_v2")
    # get_paginator creates a paginator object for the named API method
    # paginate() makes the first API call and returns the first page

    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            # "Contents" key is absent if the prefix returns 0 results → default []
            key = obj["Key"]
            if key.endswith(".ndjson") or key.endswith(".jsonl"):
                # Filter: only load NDJSON files, not directory markers or other files
                keys.append(key)
    logger.info("found_s3_keys", prefix=prefix, count=len(keys))
    return keys


def ndjson_to_tsv_buffer(
    lines: list[str],
    column_map: list[tuple[str, str]],
) -> io.StringIO:
    r"""Convert NDJSON lines to a TSV buffer suitable for COPY FROM.

    WHY TSV (tab-separated values) not CSV?
    Postgres COPY uses tab as the default delimiter. Commas appear in values
    (e.g., actor names, URLs). Tabs are much rarer in natural text.
    Missing values are represented as \\N (backslash-N) in Postgres TSV format.

    This function performs the transformation:
    NDJSON: {"mmsi": 123, "lat": 51.95, "lon": 4.05, "speed": null}
    TSV:    123\t51.95\t4.05\t\N
    """
    # In-memory buffer avoids disk writes and keeps COPY fast.
    buf = io.StringIO()
    json_keys = [jk for jk, _pg in column_map]
    rows_written = 0

    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            logger.warning("skipping_invalid_json", line=line[:80])
            continue

        values: list[str] = []
        for json_key in json_keys:
            val = record.get(json_key)
            if val is None or val == "":
                values.append("\\N")
            else:
                # Escape characters that would break TSV format
                values.append(str(val).replace("\t", " ").replace("\n", " "))
        buf.write("\t".join(values) + "\n")
        rows_written += 1

    buf.seek(0)
    return buf


def load_file(
    s3_client: Any,
    conn: psycopg.Connection,
    bucket: str,
    key: str,
    table: str,
    column_map: list[tuple[str, str]],
) -> int:
    """Download one NDJSON file from S3 and COPY it into Postgres.

    Returns the number of rows loaded.

    WHY COPY vs INSERT?
    INSERT: one network round-trip per row. For 100,000 rows = 100,000 round-trips.
    COPY:   one network connection, stream all data. For 100,000 rows = 1 connection.
    Speed difference: COPY is typically 10-100x faster for bulk loading.
    This is why warehouse bulk loads use COPY-style ingestion.
    """
    logger.info("downloading", bucket=bucket, key=key)
    response = s3_client.get_object(Bucket=bucket, Key=key)
    body = response["Body"].read().decode("utf-8")
    lines = body.splitlines()

    if not lines:
        logger.info("empty_file", key=key)
        return 0

    pg_columns = [pg for _jk, pg in column_map]
    tsv_buf = ndjson_to_tsv_buffer(lines, column_map)

    # Build the COPY query using psycopg's SQL template system
    col_sql = sql.SQL(", ").join(sql.Identifier(c) for c in pg_columns)
    copy_query = sql.SQL("COPY {schema}.{table} ({columns}) FROM STDIN").format(
        schema=sql.Identifier("raw"),
        table=sql.Identifier(table),
        columns=col_sql,
    )
    # WHY sql.Identifier() instead of f-strings?
    # sql.Identifier("raw_ais_positions") → "raw_ais_positions" (safely quoted)
    # If you used an f-string: f"COPY {table} FROM STDIN", a malicious table name
    # like "raw_ais_positions; DROP TABLE users" would be a SQL injection attack.
    # psycopg's sql module prevents this by escaping identifiers correctly.

    with conn.cursor() as cur, cur.copy(copy_query) as copy:
        # Stream the TSV data to Postgres in 8KB chunks so large files
        # do not need to be materialized twice in memory.
        while data := tsv_buf.read(8192):
            copy.write(data)

    conn.commit()
    row_count = len(lines)
    logger.info("loaded", key=key, rows=row_count)
    return row_count


def main() -> None:
    """CLI entry point: parse arguments and run the loader."""
    parser = argparse.ArgumentParser(description="Load NDJSON from S3 into Postgres")
    parser.add_argument(
        "--table",
        required=True,
        choices=list(TABLE_COLUMNS.keys()),
        help="Target Postgres table",
    )
    parser.add_argument(
        "--prefix",
        required=True,
        help="S3 prefix to scan for NDJSON files (e.g. raw/source=ais/)",
    )
    parser.add_argument(
        "--bucket",
        default=settings.s3_bucket_raw,
        help="S3 bucket name (defaults to settings)",
    )
    parser.add_argument(
        "--truncate",
        action="store_true",
        help="TRUNCATE the target table before loading (use for initial backfill)",
    )
    args = parser.parse_args()

    column_map = TABLE_COLUMNS[args.table]
    s3_client = get_s3_client()
    conn = get_pg_connection()

    if args.truncate:
        # TRUNCATE deletes all rows without logging individual row deletions
        # It's much faster than DELETE FROM for full table clears
        # WARNING: this is destructive — use only for initial backfills
        logger.info("truncating", table=args.table)
        with conn.cursor() as cur:
            cur.execute(
                sql.SQL("TRUNCATE {schema}.{table}").format(
                    schema=sql.Identifier("raw"),
                    table=sql.Identifier(args.table),
                )
            )
        conn.commit()

    keys = list_ndjson_keys(s3_client, args.bucket, args.prefix)

    if not keys:
        logger.warning("no_files_found", prefix=args.prefix, bucket=args.bucket)
        sys.exit(1)

    total_rows = 0
    for key in keys:
        total_rows += load_file(
            s3_client,
            conn,
            args.bucket,
            key,
            args.table,
            column_map,
        )

    conn.close()
    logger.info(
        "load_complete",
        table=args.table,
        total_rows=total_rows,
        files=len(keys),
    )


if __name__ == "__main__":
    main()
