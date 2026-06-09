# 06 — Changelog

_Running, dated log of every notable change. Newest first. Each entry: what changed, why, and the commit._

Format:
```
## YYYY-MM-DD — short title
- **What:** …
- **Why:** …
- **Commit:** <hash or "pending">
```

---

## 2026-06-09 — v1.2 cloud self-updating loop (CODE COMPLETE, not yet deployed)
- **What:**
  - Backfilled ~54 days of historical AIS (Apr 16–Jun 9) + weather/tides from the
    old `dpl-raw` bucket into the pilot bucket (identical schema, verified).
  - Made the 3 CTAS SQL files rebuildable (`CREATE TABLE`, no `IF NOT EXISTS`) and
    widened the data window 30→90 days (incl. the label percentile — README updated).
  - Added `serverless/handlers/features_lambda.py` (DROP → clear S3 → CREATE per
    table, in dependency order) + `run_ddl()` helper in `serverless/athena.py`.
  - Added `serverless/handlers/predict_lambda.py` (loads model once, scores 10 ports
    via the lightweight boto3 Athena helper, publishes `predictions.json`, invalidates
    CloudFront). Packaged as a zip with `requirements-predict.txt`.
  - `template.yaml`: new `FeaturesFunction` (cron :15) + `PredictFunction` (cron :30)
    + `PredictionsObjectKey` param. `Makefile`: ships `athena/` SQL + predict build.
  - Dashboard `usePredictions.js` now derives the predictions URL from the CloudFront
    base (cloud), with backward-compat for the old flat file shape.
- **Verify:** ruff clean, 19 pytest pass, `sam validate --lint` passes.
- **Pending (user):** `sam build --use-container && sam deploy`, then rebuild tables +
  retrain on backfill, then delete committed `predictions.json` and verify the loop.
- **Commit:** pending

## 2026-06-09 — Establish blueprint governance folder
- **What:** Created `docs/blueprint/` with PRD, architecture, project plan, performance
  evaluation, cleanup plan, and this changelog. This folder is now the single source
  of governance; all future changes are documented here.
- **Why:** Move from ad-hoc scripts toward a documented, production-shaped system.
- **Commit:** pending

## 2026-06-09 — Centralize PORT_TERMINALS
- **What:** Moved `PORT_TERMINALS` from `export_lambda.py` into `serverless/ports.py`.
- **Why:** All port reference data in one module; adding a port is a single-file change.
- **Commit:** pending

## 2026-06-09 — Remove fabricated vessel-to-berth mapping
- **What:** Berth view no longer claims a specific vessel is at a specific terminal.
  Shows real terminal names + AIS-derived berthed count; states mapping isn't tracked.
- **Why:** Honesty (PRD G2). AIS cannot observe terminal-level berth assignment.
- **Commit:** pending

## 2026-06-09 — Reconcile feature contract (Gap 3)
- **What:** Aligned `models/features.py` with the 3 Athena SQL files —
  `avg_speed_50nm`, real `vessels_at_anchor` (SOG < 2kn within 10nm), `avg_wave_height_m`.
- **Why:** The model must read the exact columns it trained on (FR6, NFR4).
- **Commit:** pending

---

_Earlier history predates this changelog; see `git log` and commit `60d2f78`
("drop dbt/Postgres warehouse, adopt Athena CTAS feature store") for the pivot
to the current Lambda + Athena + SAM paradigm._
