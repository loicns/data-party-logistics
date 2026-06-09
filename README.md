# Data Party Logistics

Predicts **port congestion 24 hours ahead** for the world's busiest container ports, using
live AIS vessel positions, weather, and tide data — built end-to-end on AWS serverless
infrastructure and a LightGBM model.

**Status:** v1 shipped — live ingestion, trained model, and a deployed dashboard.

---

## What it does

Every hour, the system snapshots vessel positions around 10 major ports, turns them into
features, and a trained classifier predicts whether each port will be congested 24 hours
from now. The forecast renders live on a dashboard.

```
AISStream (live vessels)  ┐
Open-Meteo (weather)      ├─►  Lambda ingestion ──►  S3 (raw NDJSON)
NOAA (tides)              ┘                              │
                                                         ▼
                                          Athena CTAS feature tables (Parquet)
                                                         │
                              ┌──────────────────────────┼───────────────────────────┐
                              ▼                           ▼                           ▼
                     build_dataset.py            congestion_target            feature_*_hourly
                              │  (joins features + 24h label)
                              ▼
                        train.py  ──►  LightGBM model  ──►  S3 (model_latest.pkl)
                              │
                              ▼
                        predict.py / refresh_predictions.py  ──►  predictions.json
                                                         │
                                                         ▼
                                     React + Vite dashboard (Vercel + CloudFront)
```

---

## The ML

- **Target:** `is_congested_24h` — a port is "congested" when its anchored-vessel count
  exceeds its trailing-90-day 75th percentile (and is above a small floor). The label is
  shifted **+24h** so the model predicts the future, not the present.
- **Features:** vessel counts in 10/50/200nm rings, vessels at anchor, average speed,
  max wave height, and cyclical hour-of-day / day-of-week signals.
- **Model:** `LGBMClassifier` with `scale_pos_weight` computed from the training labels to
  handle class imbalance.
- **Validation:** a **time-aware** 80/20 split (chronological, no shuffling) to prevent
  future data leaking into training. Evaluated with AUC-ROC.

> **Honest note on v1:** the first model trained on ~3 days of data (168 labeled rows,
> AUC ≈ 0.82 — a noisy estimate on a small test set). The pipeline is built so that as
> ingestion accumulates weeks of data, retraining is a single re-run — no code changes.

---

## Architecture

| Layer | Tech | Notes |
|-------|------|-------|
| Ingestion | Python Lambdas, EventBridge schedules | AIS via WebSocket, weather + tides via REST; hourly snapshots to S3 |
| Storage | S3 (NDJSON raw, Parquet curated) | partitioned by date |
| Feature store | Athena CTAS tables | SQL-defined, columnar Parquet |
| Training | LightGBM, scikit-learn, pandas | model artifact in S3 |
| Inference | `predict.py` (CLI) + batch refresh | writes `predictions.json` |
| Frontend | React + Vite + Tailwind | deployed on Vercel, data via CloudFront |
| IaC | AWS SAM (`template.yaml`) | all Lambdas, schedules, buckets, dashboard |

---

## Repo layout

```
ingestion/      AIS / weather / tide clients (Lambda + local)
serverless/     Lambda handlers, SAM-deployed
athena/queries/ CTAS SQL: feature tables + congestion label
models/
  features.py        single source of truth for the model's feature contract
  training/          build_dataset.py · train.py · predict.py
scripts/        refresh_predictions.py · pause.sh · resume.sh (cost control)
dashboard-v2/   React dashboard (Vercel)
```

---

## Running it

Requires Python 3.12, [uv](https://docs.astral.sh/uv/), and AWS credentials (`AWS_PROFILE=dpl`).

```bash
# 1. Build the training dataset from Athena → S3 parquet
uv run python models/training/build_dataset.py

# 2. Train the model and upload to S3
uv run python models/training/train.py

# 3. Predict for one port
uv run python models/training/predict.py --port NLRTM

# 4. Refresh all 10 ports for the dashboard
uv run python scripts/refresh_predictions.py

# Dashboard (local dev)
cd dashboard-v2 && npm install && npm run dev
```

**Cost control:** ingestion runs 24/7 on AWS. To pause all Lambdas (and stop spend)
without losing data, run `scripts/pause.sh`; resume with `scripts/resume.sh`.
See [`SHUTDOWN.md`](SHUTDOWN.md).

---

## Tech stack

Python · uv · AWS Lambda · EventBridge · S3 · Athena · AWS SAM · LightGBM · scikit-learn ·
pandas · awswrangler · React · Vite · Tailwind · Vercel · CloudFront

---

## License

MIT — see [LICENSE](LICENSE).
