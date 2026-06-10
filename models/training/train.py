import os

import awswrangler as wr
import boto3
import lightgbm as lgb
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from sklearn.metrics import classification_report, roc_auc_score
from sklearn.model_selection import train_test_split

from models.features import FEATURES, TARGET

load_dotenv()

BUCKET = os.environ["S3_BUCKET_RAW"]
REGION = os.getenv("AWS_REGION", "eu-west-3")
S3_OBJECT_KEY = "models/port_congestion/model.txt"

boto3.setup_default_session(region_name=REGION)

df = wr.s3.read_parquet(
    path=f"s3://{BUCKET}/features/training/port_congestion/latest.parquet"
)

df["observation_hour"] = pd.to_datetime(df["observation_hour"])
df = df.sort_values(by="observation_hour").reset_index(drop=True)

X = df[FEATURES]
y = df[TARGET]

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.20, random_state=42, stratify=y
)

print(f"TRAIN SAMPLE SIZE: X: {X_train.shape}; y: {y_train.shape}")
print(f"TEST SAMPLE SIZE: X: {X_test.shape}; y: {y_test.shape}")

neg_count = np.sum(y_train == 0)
pos_count = np.sum(y_train == 1)

scale_pos_weight = neg_count / pos_count

print(f"scale_pos_weight: {scale_pos_weight:.2f}  (neg={neg_count}, pos={pos_count})")

model = lgb.LGBMClassifier(
    objective="binary",
    scale_pos_weight=scale_pos_weight,
    n_estimators=100,
    learning_rate=0.05,
    num_leaves=31,
    max_depth=-1,
    subsample=0.8,
    colsample_bytree=0.8,
    min_child_samples=20,
    random_state=42,
    n_jobs=-1,
)

print("--- Fitting Model ---")
model.fit(X_train, y_train)

# ==========================================
# 1. EVALUATE ON TEST SET & ASSERT AUC
# ==========================================
print("--- Evaluating Model Performance ---")

# Extract probabilities for the positive class (Class 1)
y_probs = model.predict_proba(X_test)[:, 1]
y_preds = model.predict(X_test)

# Calculate metrics
auc_score = roc_auc_score(y_test, y_probs)
class_report = classification_report(y_test, y_preds)

# Print results
print(f"Test Set AUC-ROC: {auc_score:.4f}\n")
print("Classification Report:")
print(class_report)

# Assert performance threshold
assert auc_score >= 0.65, f"Assertion Failed: AUC-ROC is {auc_score:.4f}"
print("✅ Performance verification passed: AUC is >= 0.65.")


# ==========================================
# 2. EXTRACT FEATURE IMPORTANCES
# ==========================================
print("\n--- Feature Importance Analysis ---")

# Get feature importance (gain determines which signals matter most for split quality)
importance_gain = model.booster_.feature_importance(importance_type="gain")
feature_names = X_test.columns

# Structure into a readable DataFrame
importance_df = (
    pd.DataFrame({"Feature": feature_names, "Gain_Importance": importance_gain})
    .sort_values(by="Gain_Importance", ascending=False)
    .reset_index(drop=True)
)

# Print top 10 contributing signals
print("Top 10 Most Important Features (by Gain):")
print(importance_df.head(10).to_string(index=False))

# ==========================================
# 4. SAVING MODEL TO S3
# ==========================================

# Serialize the native LightGBM booster as text — the portable, version-stable
# format. Loading it at serving time needs only lightgbm (no scikit-learn/scipy),
# which keeps the predict Lambda package under Lambda's 250 MB unzipped limit.
s3_client = boto3.client("s3")
booster_text = model.booster_.model_to_string()

try:
    s3_client.put_object(
        Bucket=BUCKET, Key=S3_OBJECT_KEY, Body=booster_text.encode("utf-8")
    )
    print(f"🚀 Successfully uploaded model to s3://{BUCKET}/{S3_OBJECT_KEY}")
except Exception as e:
    print(f"❌ Failed to upload model to S3. Error: {e}")
    raise
