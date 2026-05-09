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
from datetime import UTC, datetime
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

MANIFEST_SCHEMA = "raw"
MANIFEST_TABLE = "load_manifest"


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


def ensure_load_manifest(conn: psycopg.Connection) -> None:
    """Create the raw load manifest table if it does not exist yet.

    WHY A MANIFEST?
    We want to load each S3 object once in normal operation. The manifest is a
    tiny bookkeeping table keyed by (table_name, s3_key) that lets the loader
    skip files it has already copied into Postgres.
    """
    create_query = sql.SQL(
        """
        CREATE TABLE IF NOT EXISTS {schema}.{table} (
            table_name TEXT NOT NULL,
            s3_key TEXT NOT NULL,
            bucket TEXT NOT NULL,
            loaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            row_count INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'loaded',
            PRIMARY KEY (table_name, s3_key)
        )
        """
    ).format(
        schema=sql.Identifier(MANIFEST_SCHEMA),
        table=sql.Identifier(MANIFEST_TABLE),
    )

    with conn.cursor() as cur:
        cur.execute(create_query)
    conn.commit()


def list_loaded_keys(
    conn: psycopg.Connection,
    table_name: str,
    bucket: str,
) -> set[str]:
    """Return the set of S3 keys already loaded for a given raw table."""
    query = sql.SQL(
        """
        SELECT s3_key
        FROM {schema}.{table}
        WHERE table_name = %s
          AND bucket = %s
          AND status = 'loaded'
        """
    ).format(
        schema=sql.Identifier(MANIFEST_SCHEMA),
        table=sql.Identifier(MANIFEST_TABLE),
    )

    with conn.cursor() as cur:
        cur.execute(query, (table_name, bucket))
        return {row[0] for row in cur.fetchall()}


def filter_new_keys(
    keys: list[str],
    loaded_keys: set[str],
) -> list[str]:
    """Keep only keys that are not already present in the load manifest."""
    return [key for key in keys if key not in loaded_keys]


def record_loaded_file(
    conn: psycopg.Connection,
    *,
    table_name: str,
    bucket: str,
    key: str,
    row_count: int,
) -> None:
    """Insert or update the manifest row for a successfully loaded S3 object."""
    query = sql.SQL(
        """
        INSERT INTO {schema}.{table} (
            table_name,
            s3_key,
            bucket,
            loaded_at,
            row_count,
            status
        )
        VALUES (%s, %s, %s, %s, %s, 'loaded')
        ON CONFLICT (table_name, s3_key)
        DO UPDATE SET
            bucket = EXCLUDED.bucket,
            loaded_at = EXCLUDED.loaded_at,
            row_count = EXCLUDED.row_count,
            status = EXCLUDED.status
        """
    ).format(
        schema=sql.Identifier(MANIFEST_SCHEMA),
        table=sql.Identifier(MANIFEST_TABLE),
    )

    with conn.cursor() as cur:
        cur.execute(
            query,
            (table_name, key, bucket, datetime.now(UTC), row_count),
        )
    conn.commit()


def clear_manifest_for_table(
    conn: psycopg.Connection,
    *,
    table_name: str,
    bucket: str,
) -> None:
    """Remove manifest rows for a table when doing a destructive reload."""
    query = sql.SQL(
        """
        DELETE FROM {schema}.{table}
        WHERE table_name = %s
          AND bucket = %s
        """
    ).format(
        schema=sql.Identifier(MANIFEST_SCHEMA),
        table=sql.Identifier(MANIFEST_TABLE),
    )

    with conn.cursor() as cur:
        cur.execute(query, (table_name, bucket))
    conn.commit()


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
    sample_minutes: int = 0,
) -> tuple[io.StringIO, int]:
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

        if sample_minutes > 0:
            # Quickly parse the minute out of the ISO timestamp string
            # e.g., "2026-04-16T19:05:33Z" -> index 14 & 15 is "05"
            ts_str = (
                record.get("received_at")
                or record.get("timestamp")
                or record.get("time_utc")
            )
            if isinstance(ts_str, str) and len(ts_str) >= 16:
                minute_str = ts_str[14:16]
                if minute_str.isdigit() and int(minute_str) >= sample_minutes:
                    continue  # Skip this record! It is outside the first N minutes.

        values: list[str] = []
        for json_key in json_keys:
            val = record.get(json_key)
            if val is None or val == "":
                values.append("\\N")
            else:
                # Escape characters that would break TSV format
                safe_str = (
                    str(val).replace("\\", "\\\\").replace("\t", " ").replace("\n", " ")
                )
                values.append(safe_str)
        buf.write("\t".join(values) + "\n")
        rows_written += 1

    buf.seek(0)
    return buf, rows_written


def load_file(
    s3_client: Any,
    conn: psycopg.Connection,
    bucket: str,
    key: str,
    table: str,
    column_map: list[tuple[str, str]],
    sample_minutes: int = 0,
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
    tsv_buf, rows_written = ndjson_to_tsv_buffer(lines, column_map, sample_minutes)

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
    row_count = rows_written
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
    parser.add_argument(
        "--sample-minutes",
        type=int,
        default=0,
        help="If set > 0, only loads records from the first N minutes of every hour.",
    )
    parser.add_argument(
        "--reload-existing",
        action="store_true",
        help="Load matching files even if they already exist in the manifest.",
    )
    args = parser.parse_args()

    column_map = TABLE_COLUMNS[args.table]
    s3_client = get_s3_client()
    conn = get_pg_connection()
    ensure_load_manifest(conn)

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
        clear_manifest_for_table(
            conn,
            table_name=args.table,
            bucket=args.bucket,
        )

    keys = list_ndjson_keys(s3_client, args.bucket, args.prefix)
    loaded_keys = set()
    if not args.reload_existing:
        loaded_keys = list_loaded_keys(conn, args.table, args.bucket)
        keys = filter_new_keys(keys, loaded_keys)
        logger.info(
            "filtered_loaded_keys",
            table=args.table,
            already_loaded=len(loaded_keys),
            remaining=len(keys),
        )

    if not keys:
        if args.reload_existing:
            logger.warning("no_files_found", prefix=args.prefix, bucket=args.bucket)
            sys.exit(1)

        logger.info(
            "no_new_files_found",
            prefix=args.prefix,
            bucket=args.bucket,
            table=args.table,
        )
        conn.close()
        return

    total_rows = 0
    for key in keys:
        row_count = load_file(
            s3_client,
            conn,
            args.bucket,
            key,
            args.table,
            column_map,
            args.sample_minutes,
        )
        record_loaded_file(
            conn,
            table_name=args.table,
            bucket=args.bucket,
            key=key,
            row_count=row_count,
        )
        total_rows += row_count

    conn.close()
    logger.info(
        "load_complete",
        table=args.table,
        total_rows=total_rows,
        files=len(keys),
    )


if __name__ == "__main__":
    main()
