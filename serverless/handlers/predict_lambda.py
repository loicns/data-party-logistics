"""Score 24h congestion for all ports and publish predictions.json.

Runs hourly (after features_lambda refreshes the gold tables):
  1. load the trained model from S3 (once)
  2. for each port, read the latest gold-table row and score it
  3. write predictions.json to the public dashboard bucket
  4. invalidate CloudFront so the dashboard sees it immediately

Deps are heavy (lightgbm + scikit-learn to unpickle the model), installed from
requirements-predict.txt via the Makefile `build-PredictFunction` target and
built with `sam build --use-container` for correct Linux binaries.
Querying uses the lightweight boto3 Athena helper (no pandas/awswrangler), so
the package only carries the model libraries.
"""

from __future__ import annotations

import json
import os
import pickle
import tempfile
from datetime import UTC, datetime
from typing import Any

import boto3
from models.features import FEATURES

from serverless.athena import run_query
from serverless.metrics import put_metric
from serverless.ports import PORTS

DATA_BUCKET = os.environ["DATA_BUCKET_NAME"]
DATABASE = os.environ["ATHENA_DATABASE"]
OUTPUT_LOCATION = os.environ["ATHENA_OUTPUT_LOCATION"]
MODEL_KEY = os.getenv("MODEL_OBJECT_KEY", "models/port_congestion/model_lightgbm.pkl")
PUBLIC_BUCKET = os.getenv("PUBLIC_DASHBOARD_BUCKET_NAME", "")
PREDICTIONS_KEY = os.getenv("PREDICTIONS_OBJECT_KEY", "predictions.json")
DISTRIBUTION_ID = os.getenv("PUBLIC_DASHBOARD_DISTRIBUTION_ID", "")


def load_model() -> Any:
    """Download + deserialize the model from S3 (once per invocation)."""
    s3 = boto3.client("s3")
    with tempfile.NamedTemporaryFile(delete=True) as tmp:
        s3.download_fileobj(DATA_BUCKET, MODEL_KEY, tmp)
        tmp.seek(0)
        return pickle.load(tmp)


def _latest_row(port_code: str) -> dict[str, str] | None:
    """Most recent gold-table row for a port, as a dict of strings."""
    feature_cols = ",\n        ".join(FEATURES)
    sql = f"""
    SELECT
        observation_hour,
        {feature_cols}
    FROM feature_port_status_hourly
    WHERE port_code = '{port_code}'
    ORDER BY observation_hour DESC
    LIMIT 1
    """
    rows = run_query(sql, database=DATABASE, output_location=OUTPUT_LOCATION)
    return rows[0] if rows else None


def predict(model: Any, port_code: str) -> dict[str, Any] | None:
    """Score one port. Returns None if there is no data for it."""
    row = _latest_row(port_code)
    if row is None:
        return None

    # Build the feature vector in the EXACT training order; missing -> 0.0.
    features = [[float(row.get(name) or 0.0) for name in FEATURES]]
    prediction = int(model.predict(features)[0])
    probability = float(model.predict_proba(features)[0][1])

    return {
        "port_code": port_code,
        "prediction": prediction,
        "probability": round(probability, 4),
        "as_of": row.get("observation_hour"),
    }


def lambda_handler(_event: dict[str, Any], _context: Any) -> dict[str, Any]:
    model = load_model()

    results: dict[str, Any] = {}
    succeeded, failed = 0, 0
    for port_code in PORTS:
        try:
            results[port_code] = predict(model, port_code)
            succeeded += 1
        except Exception as exc:  # failure isolation (NFR3)
            results[port_code] = None
            failed += 1
            print(f"WARN {port_code} failed: {exc}")

    payload = {
        "generatedAt": datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC"),
        "predictions": results,
    }

    published = False
    if PUBLIC_BUCKET:
        boto3.client("s3").put_object(
            Bucket=PUBLIC_BUCKET,
            Key=PREDICTIONS_KEY,
            Body=json.dumps(payload, indent=2).encode("utf-8"),
            ContentType="application/json",
            CacheControl="no-cache, no-store, must-revalidate",
        )
        published = True
        if DISTRIBUTION_ID:
            boto3.client("cloudfront").create_invalidation(
                DistributionId=DISTRIBUTION_ID,
                InvalidationBatch={
                    "Paths": {"Quantity": 1, "Items": [f"/{PREDICTIONS_KEY}"]},
                    "CallerReference": datetime.now(UTC).strftime("%Y%m%d%H%M%S%f"),
                },
            )

    put_metric("PredictRunSuccess", 1)
    put_metric("PredictPortsScored", succeeded)
    return {
        "status": "ok",
        "scored": succeeded,
        "failed": failed,
        "published": published,
        "predictions_key": PREDICTIONS_KEY if published else None,
    }
