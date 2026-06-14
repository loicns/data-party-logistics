"""Train and evaluate the additive AIS v2 candidate model.

The production model key is never overwritten. This script writes a candidate
model and an evaluation report so promotion stays an explicit later decision.
"""

from __future__ import annotations

import json
import os
from typing import Any

import awswrangler as wr
import boto3
import lightgbm as lgb
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    precision_score,
    recall_score,
    roc_auc_score,
)

from models.features import FEATURES
from models.features_v2 import FEATURES_V2, MODEL_OBJECT_KEY_V2, TARGET_V2

load_dotenv()

BUCKET = os.environ["S3_BUCKET_RAW"]
REGION = os.getenv("AWS_REGION", "eu-west-3")
BASELINE_MODEL_KEY = "models/port_congestion/model.txt"
DATASET_KEY = "features/training/port_congestion/v2/latest.parquet"
REPORT_KEY = "models/port_congestion/evaluation_v2_latest.json"

boto3.setup_default_session(region_name=REGION)


def _chronological_split(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    df = df.sort_values("observation_hour").reset_index(drop=True)
    train_end = int(len(df) * 0.70)
    val_end = int(len(df) * 0.85)
    return df.iloc[:train_end], df.iloc[train_end:val_end], df.iloc[val_end:]


def _metrics(y_true: pd.Series, probabilities: np.ndarray) -> dict[str, float | None]:
    predictions = (probabilities >= 0.5).astype(int)
    has_two_classes = len(set(y_true.astype(int))) == 2
    has_positive = int((y_true > 0).sum()) > 0

    return {
        "roc_auc": (
            float(roc_auc_score(y_true, probabilities)) if has_two_classes else None
        ),
        "pr_auc": (
            float(average_precision_score(y_true, probabilities))
            if has_positive
            else None
        ),
        "precision_at_0_5": float(
            precision_score(y_true, predictions, zero_division=0)
        ),
        "recall_at_0_5": float(recall_score(y_true, predictions, zero_division=0)),
        "brier_score": float(brier_score_loss(y_true, probabilities)),
    }


def _load_booster(s3: Any, key: str) -> lgb.Booster:
    obj = s3.get_object(Bucket=BUCKET, Key=key)
    model_str = obj["Body"].read().decode("utf-8")
    return lgb.Booster(model_str=model_str)


def main() -> None:
    df = wr.s3.read_parquet(path=f"s3://{BUCKET}/{DATASET_KEY}")
    df["observation_hour"] = pd.to_datetime(df["observation_hour"])
    df[FEATURES_V2] = df[FEATURES_V2].fillna(0)
    df[FEATURES] = df[FEATURES].fillna(0)

    train_df, val_df, test_df = _chronological_split(df)
    if train_df.empty or val_df.empty or test_df.empty:
        raise ValueError("Chronological split produced an empty train/val/test slice")

    y_train = train_df[TARGET_V2].astype(int)
    pos_count = int((y_train == 1).sum())
    neg_count = int((y_train == 0).sum())
    if pos_count == 0 or neg_count == 0:
        raise ValueError("Training slice must contain both positive and negative rows")

    model = lgb.LGBMClassifier(
        objective="binary",
        scale_pos_weight=neg_count / pos_count,
        n_estimators=150,
        learning_rate=0.05,
        num_leaves=31,
        subsample=0.8,
        colsample_bytree=0.8,
        min_child_samples=20,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(train_df[FEATURES_V2], y_train)

    s3 = boto3.client("s3")
    baseline = _load_booster(s3, BASELINE_MODEL_KEY)

    val_probs = model.predict_proba(val_df[FEATURES_V2])[:, 1]
    test_probs = model.predict_proba(test_df[FEATURES_V2])[:, 1]
    baseline_probs = baseline.predict(test_df[FEATURES])

    report = {
        "dataset": f"s3://{BUCKET}/{DATASET_KEY}",
        "rows": {
            "total": len(df),
            "train": len(train_df),
            "validation": len(val_df),
            "test": len(test_df),
        },
        "positive_rows": int((df[TARGET_V2] > 0).sum()),
        "candidate_v2": {
            "validation": _metrics(val_df[TARGET_V2].astype(int), val_probs),
            "test": _metrics(test_df[TARGET_V2].astype(int), test_probs),
        },
        "baseline_v1_on_same_test_window": _metrics(
            test_df[TARGET_V2].astype(int),
            np.asarray(baseline_probs),
        ),
        "feature_importance_gain": dict(
            sorted(
                zip(
                    FEATURES_V2,
                    model.booster_.feature_importance(importance_type="gain"),
                    strict=True,
                ),
                key=lambda item: item[1],
                reverse=True,
            )
        ),
        "promotion_note": (
            "Do not update serving automatically. Promote only after reviewing "
            "this report against the v1 baseline."
        ),
    }

    s3.put_object(
        Bucket=BUCKET,
        Key=MODEL_OBJECT_KEY_V2,
        Body=model.booster_.model_to_string().encode("utf-8"),
    )
    s3.put_object(
        Bucket=BUCKET,
        Key=REPORT_KEY,
        Body=json.dumps(report, indent=2, default=float).encode("utf-8"),
        ContentType="application/json",
    )

    print(json.dumps(report, indent=2, default=float))
    print(f"Saved candidate model: s3://{BUCKET}/{MODEL_OBJECT_KEY_V2}")
    print(f"Saved evaluation report: s3://{BUCKET}/{REPORT_KEY}")


if __name__ == "__main__":
    main()
