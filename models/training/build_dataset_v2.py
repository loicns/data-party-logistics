"""Build the additive AIS v2 training dataset.

This script intentionally requires a v2 start hour. That keeps the first v2
experiment on post-deploy data instead of silently mixing old v1-only history.
"""

from __future__ import annotations

import argparse
import os

import awswrangler as wr
import boto3
from dotenv import load_dotenv

from models.features_v2 import FEATURES_V2, TARGET_V2

load_dotenv()

BUCKET = os.environ["S3_BUCKET_RAW"]
DATABASE = os.getenv("ATHENA_DATABASE", "dpl_pilot")
REGION = os.getenv("AWS_REGION", "eu-west-3")
boto3.setup_default_session(region_name=REGION)


def _query(start_hour: str) -> str:
    feature_cols = ",\n  ".join(f"f.{name}" for name in FEATURES_V2)
    return f"""
SELECT
  f.port_code,
  f.observation_hour,
  {feature_cols},
  t.{TARGET_V2}
FROM feature_port_status_hourly_v2 AS f
INNER JOIN congestion_target AS t
    ON f.port_code = t.port_code
   AND f.observation_hour = t.observation_hour
WHERE f.observation_hour >= timestamp '{start_hour}'
ORDER BY f.port_code, f.observation_hour
"""


def build_dataset(start_hour: str, min_rows: int, min_positive_rows: int) -> str:
    df = wr.athena.read_sql_query(
        _query(start_hour),
        database=DATABASE,
        s3_output=f"s3://{BUCKET}/athena-results/",
    )

    if len(df) < min_rows:
        raise ValueError(f"v2 dataset has {len(df)} rows; need at least {min_rows}")

    positive_rows = int((df[TARGET_V2] > 0).sum())
    if positive_rows < min_positive_rows:
        raise ValueError(
            f"v2 dataset has {positive_rows} positive rows; "
            f"need at least {min_positive_rows}"
        )

    output_path = f"s3://{BUCKET}/features/training/port_congestion/v2/latest.parquet"
    wr.s3.to_parquet(df=df, path=output_path)
    print(f"Shape: {df.shape}")
    print(f"Positive rows: {positive_rows}")
    print(f"S3 PATH: '{output_path}'")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Build AIS v2 training dataset.")
    parser.add_argument(
        "--start-hour",
        default=os.getenv("AIS_V2_TRAINING_START_HOUR"),
        help="UTC start hour for post-v2 training rows, e.g. 2026-06-14 15:00:00.",
    )
    parser.add_argument("--min-rows", type=int, default=1000)
    parser.add_argument("--min-positive-rows", type=int, default=20)
    args = parser.parse_args()

    if not args.start_hour:
        raise SystemExit(
            "Provide --start-hour or AIS_V2_TRAINING_START_HOUR so v2 training "
            "does not mix pre-v2 historical rows."
        )

    build_dataset(args.start_hour, args.min_rows, args.min_positive_rows)


if __name__ == "__main__":
    main()
