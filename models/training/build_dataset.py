import os

import awswrangler as wr
import boto3
from dotenv import load_dotenv

load_dotenv()

BUCKET = os.environ["S3_BUCKET_RAW"]  # fails loud if missing — good
DATABASE = os.getenv("ATHENA_DATABASE", "dpl_pilot")
REGION = os.getenv("AWS_REGION", "eu-west-3")
boto3.setup_default_session(region_name=REGION)


SQL = """
SELECT
  f.port_code,
  f.observation_hour,
  f.vessels_in_10nm,
  f.vessels_in_50nm,
  f.vessels_in_200nm,
  f.vessels_at_anchor,
  f.avg_speed_50nm,
  f.avg_wave_height_m,
  f.hour_of_day,
  f.day_of_week,
  t.is_congested_24h
FROM feature_port_status_hourly AS f
INNER JOIN congestion_target AS t
    ON f.port_code = t.port_code
    and f.observation_hour = t.observation_hour
ORDER BY f.port_code, f.observation_hour
"""

df = wr.athena.read_sql_query(
    SQL, database=DATABASE, s3_output=f"s3://{BUCKET}/athena-results/"
)

assert not df.empty, "DataFrame is empty!"
print(f"Shape: {df.shape}")
positive_rate = (df["is_congested_24h"] > 0).mean()
print(f"Positive Rate: {positive_rate:.4f}")

wr.s3.to_parquet(
    df=df, path=f"s3://{BUCKET}/features/training/port_congestion/latest.parquet"
)

print(f"S3 PATH: 's3://{BUCKET}/features/training/port_congestion/latest.parquet'")
