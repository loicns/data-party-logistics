# 02 — Architecture & Design

_Last updated 2026-06-09 · Paradigm: **Lambda + Athena + SAM only**_

## 1. Principles

1. **Match architecture to scale.** Data is MBs/hour. Athena + Lambda is correct;
   Spark/Kafka/EMR would cost more and signal poor judgment.
2. **Medallion data flow.** Raw (bronze) → curated features (gold). The hot path
   (prediction, dashboard) reads gold, never raw.
3. **One definition per concept.** Ports in `ports.py`, features in `features.py`,
   feature SQL in `athena/queries/`. No duplicates.
4. **Serverless, no idle cost.** No always-on server, DB, or NAT.
5. **Publish to static + CDN.** Serving cost ≈ $0, infinitely scalable.

## 2. Current state (v1.1 — shipped)

```
AISStream ─┐
Open-Meteo ─┤ 5 SAM Lambdas (EventBridge schedules)
NOAA       ─┘        │
                     ▼
        S3 raw NDJSON  (bronze, partitioned by date)
                     │
        Athena CTAS feature tables  ← BUILT MANUALLY (gap)
                     │
        train.py / predict.py  ← RUN ON LAPTOP (gap)
                     │
        predictions.json  ← COMMITTED FILE (gap)
                     │
        React dashboard → Vercel / CloudFront
```

### Live Lambdas (SAM, `template.yaml`)

| Function | Schedule | Role |
|---|---|---|
| `ais-snapshot` | `rate(1 hour)` | AIS positions → S3 raw |
| `weather` | `cron :10` | Open-Meteo → S3 raw |
| `noaa` | `cron 1:20 daily` | NOAA tides → S3 raw |
| `export` | `cron :25` | Athena (RAW) → `demo-data.json` → CloudFront |
| `freshness` | `rate(30 min)` | Health metric |

### Feature tables (Athena CTAS, `athena/queries/`)

- `feature_vessel_inbound_hourly` — vessel ring counts, avg speed, vessels at anchor
- `feature_port_status_hourly` — joins vessel features + weather (the **gold** table the model reads)
- `congestion_target` — the `is_congested_24h` label, shifted +24h

### Model

- `LGBMClassifier`, `scale_pos_weight` from training labels, time-aware 80/20 split.
- Feature contract: `models/features.py` (single source, prevents train/serve skew).
- Artifact: `model_lightgbm.pkl` (latest alias) + timestamped copies in S3.

## 3. Known weaknesses in v1.1

| # | Weakness | Impact |
|---|---|---|
| W1 | Feature tables rebuilt **manually** | Forecast goes stale without a human |
| W2 | Predictions generated **on laptop**, committed to git | Not self-updating |
| W3 | `export_lambda` queries **raw NDJSON** hourly | Main Athena cost driver |
| W4 | ML deps **undeclared** in `pyproject.toml` | Not reproducible |
| W5 | Large amount of **dead code/deps** (see 05) | Confuses reviewers, bloats builds |

## 4. Target state (v1.2)

Close the loop entirely in the cloud. Two new Lambdas + a schedule chain.

```
:00 ais-snapshot   (ingest raw)
:10 weather        (ingest raw)
:15 features_lambda  ← NEW: rebuild gold CTAS tables from raw
:25 export         (existing)
:30 predict_lambda   ← NEW: score 10 ports from gold → predictions.json → CloudFront
```

- **`features_lambda`** runs the 3 CTAS queries (now rebuildable: DROP + clear S3 +
  CREATE) in dependency order via `serverless/athena.py`.
- **`predict_lambda`** loads the model once, loops `PORTS`, scores each from the fresh
  `feature_port_status_hourly`, writes `predictions.json` to the public bucket, and
  invalidates CloudFront — mirroring `export_lambda`'s publish pattern.
- **Dashboard** `usePredictions.js` reads the published CloudFront URL, not a committed file.

## 5. Deferred (Phase 2+, documented, not now)

- **W3 fix:** point `export_lambda` at gold tables instead of raw (cost win, bigger change).
- **Incremental CTAS:** partition-pruned rebuild instead of full 30-day re-scan.
- **Model registry / drift monitoring:** only once data volume justifies it.

## 6. Repo layout (target, after cleanup)

```
ingestion/      live AIS / weather / tide clients only
serverless/     Lambda handlers (incl. new features_lambda, predict_lambda) + SAM helpers
athena/queries/ rebuildable CTAS SQL
models/         features.py (contract) + training/ (build_dataset, train, predict)
scripts/        local helpers + cost control (pause/resume)
dashboard-v2/   React dashboard
docs/blueprint/ THIS governance folder
template.yaml   SAM IaC
```
