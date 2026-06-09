# 05 — Cleanup Plan (reach a clean state)

_Last updated 2026-06-09 · Every removal is verified against live-code imports._

Classification:
- **CONFIRMED DEAD** — not imported by any live code (`serverless/ ingestion(live) models/ scripts/`). Safe to remove.
- **VERIFY FIRST** — likely dead but has state or external coupling; check before deleting.

## A. Dead top-level directories — CONFIRMED DEAD

Verified: none imported by `serverless/`, `ingestion` (live clients), `models/`, or `scripts/`.

| Dir | Why dead | Replaced by |
|---|---|---|
| `agent/` | not imported anywhere | — |
| `features/` | not imported; contract lives in `models/features.py` | `models/features.py` |
| `serving/` | FastAPI app on the deleted Postgres DB | Athena + static JSON |
| `orchestration/` | Prefect flows; `prefect` isn't even a declared dep | SAM schedules |
| `dashboard/` | old v1 dashboard | `dashboard-v2/` |

```bash
git rm -r agent features serving orchestration dashboard
```

## B. Dead ingestion clients — CONFIRMED DEAD

Live Lambdas import only: `ais_stream`, `weather`, `noaa_tides`, `s3_writer`.

| Path | Pulls in dep |
|---|---|
| `ingestion/clients/cmems.py` | copernicusmarine |
| `ingestion/clients/fred.py` | xlrd |
| `ingestion/clients/carriers/` | playwright |
| `ingestion/schemas.py` | pandera (only used by the above) |

```bash
git rm -r ingestion/clients/cmems.py ingestion/clients/fred.py ingestion/clients/carriers
# schemas.py: confirm no live import, then:
git rm ingestion/schemas.py
# also remove their tests:
git rm tests/test_cmems.py tests/test_fred.py tests/test_msc_scraper.py
```

## C. Dependencies — `pyproject.toml`

### Remove (CONFIRMED DEAD — only used by code deleted above)
- `copernicusmarine` (cmems)
- `playwright` (carriers)
- `fastapi`, `uvicorn` (serving)
- `xlrd` (fred), `xlwt` (test_fred)
- `pandera` (schemas)

### ADD (used by `models/training/` but currently UNDECLARED)
- `lightgbm`
- `scikit-learn`
- `pandas`
- `awswrangler`

### Fix structure
- De-duplicate: `mkdocs-material`, `moto[s3]`, `xlwt` appear in **both**
  `[project.optional-dependencies].dev` and `[dependency-groups].dev`. Keep one block.
- Update `[tool.hatch.build.targets.wheel].packages` and `[tool.ruff].src`:
  from `["ingestion","features","models","serving","agent","dashboard","orchestration","serverless"]`
  to `["ingestion","models","serverless"]`.

```bash
# after editing pyproject.toml:
uv sync
uv run ruff check .
uv run pytest
```

## D. VERIFY FIRST (do not blind-delete)

| Path | Concern | Action |
|---|---|---|
| `infra/` (Terraform) | `terraform.tfstate` may still reference real AWS resources | Confirm `terraform state list` is empty / all resources are SAM-managed, then `git rm -r infra/`. If unsure, move to `archive/` instead. |
| `roadmap/` | old planning, superseded by this blueprint | Read, salvage anything useful into `docs/blueprint/`, then `git rm -r roadmap/`. |
| `site/` | mkdocs **build output**, already gitignored (line 52) | Local only: `rm -rf site/` (regenerates via `mkdocs build`). Not in git. |
| `logs/` | runtime logs | Ensure gitignored; `rm -rf logs/` locally. |
| `docs/` (architecture, audit, blog, decisions, learning-journal) | historical docs | Keep for now; `docs/blueprint/` supersedes as the authoritative set. Migrate selectively later. |

## E. Order of operations

1. Section A (dirs) → 2. Section B (clients + tests) → 3. Section C (pyproject) →
4. `uv sync && ruff check && pytest` green → 5. Section D verify → 6. one commit.

**Commit message:**
```
chore: remove dead dbt/prefect/serving/scraper code; declare ML deps

Deletes unused agent/, features/, serving/, orchestration/, dashboard/ dirs and
dead ingestion clients (cmems, fred, carriers). Drops their deps; adds the
previously-undeclared ML deps (lightgbm, scikit-learn, pandas, awswrangler).
Fixes duplicated dev-dep blocks and package lists. Repo now matches the
Lambda + Athena + SAM paradigm only.
```

## F. Removal log (append every actual deletion here)

| Date | Removed | By commit |
|---|---|---|
| 2026-06-09 | `agent/`, `features/`, `serving/`, `orchestration/`, `dashboard/` (Section A) | staged, not yet committed |
| 2026-06-09 | `ingestion/clients/cmems.py`, `ingestion/clients/fred.py`, `ingestion/clients/carriers/` (whole dir), `ingestion/schemas.py`, `tests/test_cmems.py`, `tests/test_fred.py`, `tests/test_msc_scraper.py`, `tests/test_carrier_adapters.py` (Section B) — 19 pytest ✓, ruff ✓ | staged, not yet committed |
| 2026-06-09 | `infra/` (Terraform) — **NOT removed**. `terraform state list` shows 14 live resources: `aws_db_instance.dpl_postgres`, `aws_s3_bucket.raw`, `aws_cloudtrail.dpl_audit`, `aws_security_group.rds_postgres`, and 10 others. Must be destroyed/migrated before deleting. | — |
| 2026-06-09 | `roadmap/serverless-pilot/index.html` — salvaged cost forecast + go-live checklist into `docs/blueprint/07-PILOT-GOLIVE-NOTE.md`, then `git rm -r roadmap/` | staged, not yet committed |
| 2026-06-09 | `site/` — mkdocs build output, confirmed gitignored (.gitignore line 52). Removed locally with `rm -rf site/`. Not in git. | local only |
| 2026-06-09 | `logs/` — confirmed gitignored (.gitignore line 45). Removed locally with `rm -rf logs/`. | local only |
