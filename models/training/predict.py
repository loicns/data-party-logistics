import argparse
import os
import pickle
import tempfile

import awswrangler as wr
import boto3
from dotenv import load_dotenv

load_dotenv()

BUCKET = os.environ["S3_BUCKET_RAW"]  # fails loud if missing — good
DATABASE = os.getenv("ATHENA_DATABASE", "dpl_pilot")
REGION = os.getenv("AWS_REGION", "eu-west-3")
boto3.setup_default_session(region_name=REGION)
S3_OBJECT_KEY = "models/port_congestion/model_lightgbm.pkl"

parser = argparse.ArgumentParser(description="Get predictions on specified port.")

parser.add_argument(
    "--port", type=str, required=True, help="UN LOCODE's 5-characters port code."
)

args = parser.parse_args()

SQL = f"""
SELECT
  observation_hour,
  vessels_in_10nm,
  vessels_in_50nm,
  vessels_in_200nm,
  vessels_at_anchor,
  avg_speed_50nm,
  max_wave_height_m,
  hour_of_day,
  day_of_week
FROM feature_port_status_hourly
WHERE port_code = '{args.port}'
ORDER BY observation_hour DESC
LIMIT 1
"""

df = wr.athena.read_sql_query(
    SQL, database=DATABASE, s3_output=f"s3://{BUCKET}/athena-results/"
)
df.fillna(0, inplace=True)

assert df.shape[0] == 1, f"Assertion query results: shape = 1 failed, results: {df}"


print(f"== Successfully queried latest result for port: {args.port}")
print(f"Results:\n{df}")

s3_client = boto3.client("s3")

with tempfile.NamedTemporaryFile(delete=True) as tmp_file:
    print(f"Downloading model to temporary file: {tmp_file.name}")

    s3_client.download_fileobj(BUCKET, S3_OBJECT_KEY, tmp_file)

    tmp_file.seek(0)

    model = pickle.load(tmp_file)
print("Model loaded successfully into memory. Temp file cleaned up.")

FEATURES = [
    "vessels_in_10nm",
    "vessels_in_50nm",
    "vessels_in_200nm",
    "avg_speed_50nm",
    "vessels_at_anchor",
    "max_wave_height_m",
    "hour_of_day",
    "day_of_week",
]
X = df[FEATURES]

prediction = int(model.predict(X)[0])  # 0 or 1
probability = float(model.predict_proba(X)[0][1])  # P(congested)

as_of = str(df["observation_hour"].iloc[0])  # when this snapshot is from

result = {
    "port_code": args.port,
    "prediction": prediction,
    "probability": round(probability, 4),
    "as_of": as_of,
}
print(result)
