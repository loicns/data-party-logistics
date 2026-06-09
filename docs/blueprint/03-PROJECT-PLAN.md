# 03 — Project Plan & Action List

_Last updated 2026-06-09 · This is the ordered backlog. Tick items as done; log each in 06-CHANGELOG.md._

## Phase 0 — Clean state (do FIRST, blocks everything)

See `05-CLEANUP-PLAN.md` for exact commands.

- [ ] **0.1** Remove dead top-level dirs: `agent/ features/ serving/ orchestration/ dashboard/`
- [ ] **0.2** Remove dead ingestion clients: `cmems.py fred.py carriers/`
- [ ] **0.3** Remove dead deps from `pyproject.toml`: copernicusmarine, playwright, fastapi, uvicorn, xlrd, xlwt, pandera
- [ ] **0.4** Add missing ML deps: `lightgbm, scikit-learn, pandas, awswrangler`
- [ ] **0.5** De-duplicate the two `dev` dependency blocks in `pyproject.toml`
- [ ] **0.6** Fix `packages` + `ruff.src` lists to only `ingestion, models, serverless`
- [ ] **0.7** `infra/` decision (audited 2026-06-09): RDS Postgres confirmed GONE (state is stale).
      CloudTrail `dpl-audit-trail` → **KEEP** (free, good practice). `dpl-raw` bucket → reused for
      backfill (Phase 1.5) then deleted. Remove `infra/` dir + run `terraform`-free afterward.
- [ ] **0.8** `uv sync` + `ruff check` + `pytest` all green
- [ ] **0.9** Commit: `chore: remove dead dbt/prefect/serving artifacts, declare ML deps`

## Phase 1 — Feature contract (DONE ✅)

- [x] **1.1** Reconcile `features.py` ↔ 3 SQL files (avg_speed_50nm, vessels_at_anchor, avg_wave_height_m)
- [x] **1.2** Replace fabricated berth→vessel mapping with honest AIS-derived count
- [x] **1.3** Centralize `PORT_TERMINALS` into `serverless/ports.py`

## Phase 1.5 — Backfill historical data (HIGH VALUE — found 2026-06-09)

The old Terraform-era bucket `dpl-raw-861276086413` holds **~25 days of AIS**
(Apr 16–May 11) + ~12 days weather/tides (Apr 25–May 7), **identical schema** to
the current pilot data. This is ~8× more AIS history than the 168-row v1 set.

- [ ] **1.5.1** Server-side sync old → pilot bucket (same `date=` partition layout):
      `aws s3 sync s3://dpl-raw-861276086413/raw/ s3://dpl-serverless-pilot-861276086413-pilot-data/raw/ --exclude "source=cmems/*" --exclude "source=fred/*" --exclude "*_test/*"`
- [ ] **1.5.2** ⚠️ Widen the `30 DAY` filter → `90 DAY` in all 3 feature SQL files
      (April data is >30 days old now and would be silently excluded otherwise)
- [ ] **1.5.3** Rebuild CTAS tables (depends on Phase 2) over the expanded range
- [ ] **1.5.4** Rebuild dataset (`build_dataset.py`) → retrain (`train.py`)
- [ ] **1.5.5** Record new row count + AUC in `04-PERFORMANCE-EVALUATION.md`
- [ ] **1.5.6** Once absorbed + verified, delete `dpl-raw-861276086413` (Phase 0.7 infra)

## Phase 2 — Make CTAS rebuildable

- [ ] **2.1** `feature_vessel_inbound_hourly.sql`: `CREATE IF NOT EXISTS` → `DROP` + recreate
- [ ] **2.2** `feature_port_status_hourly.sql`: same
- [ ] **2.3** `congestion_target.sql`: same
- [ ] **2.4** Document the S3-clear step each rebuild needs (external_location must be empty)

## Phase 3 — features_lambda (automate gold tables)

- [ ] **3.1** `serverless/handlers/features_lambda.py`: run 3 CTAS in dependency order via `athena.py`
- [ ] **3.2** Clear each table's S3 prefix before its CREATE
- [ ] **3.3** Add to `template.yaml`: function + Athena/S3 policies + `cron :15`
- [ ] **3.4** Deploy, invoke manually, confirm tables refresh

## Phase 4 — predict_lambda (the forecast, in cloud)

- [ ] **4.1** `serverless/handlers/predict_lambda.py`: read settings → load model → loop PORTS → write predictions.json → invalidate CloudFront
- [ ] **4.2** Reuse `models/training/predict.py` (`load_model`, `predict`)
- [ ] **4.3** Per-port try/except (failure isolation, NFR3)
- [ ] **4.4** Add to `template.yaml`: function + S3 read(model)/write(public) + CloudFront + `cron :30`
- [ ] **4.5** Deploy, invoke manually, confirm `predictions.json` lands in public bucket

## Phase 5 — Dashboard reads cloud

- [ ] **5.1** `usePredictions.js`: fetch published CloudFront `predictions.json` URL
- [ ] **5.2** Delete committed `dashboard-v2/public/predictions.json`
- [ ] **5.3** Verify locally + on Vercel

## Phase 6 — Verify the loop ("done when")

- [ ] **6.1** Delete local `predictions.json`, wait 1 hour
- [ ] **6.2** Dashboard 24h forecast still shows fresh numbers with today's timestamp — **no laptop**
- [ ] **6.3** Record cost for the day in `04-PERFORMANCE-EVALUATION.md`

## Deferred backlog (Phase 7+, not scheduled)

- [ ] Point `export_lambda` at gold tables (W3 cost fix)
- [ ] Incremental CTAS rebuild (partition pruning)
- [ ] Retrain on weeks of data; record AUC progression
- [ ] CI: GitHub Actions running ruff + pytest + `sam validate`
