# Data Party Logistics

Data Party Logistics predicts short-term port congestion from live maritime
signals. The pilot ingests AIS vessel positions, marine weather, and NOAA tide
data; builds hourly feature tables in S3/Athena; scores a LightGBM model; and
publishes an operator dashboard for selected major container ports.

The repository is intentionally runnable in two modes:

- **Local demo mode:** runs the dashboard from committed demo data with no
  secrets and no AWS account.
- **Live AWS mode:** runs ingestion, feature generation, model refresh, and
  dashboard publishing against your own AWS account and API keys.

## Current Status

v1 is shipped as a portfolio-grade pilot:

- Serverless ingestion for AIS, weather, NOAA tides, dashboard export, freshness
  checks, GDELT maritime events, feature rebuilds, and prediction refresh.
- S3 raw storage and Athena/Glue query layer.
- LightGBM training and inference pipeline, with a time-based backtest still to add.
- Event-pressure feature tables are built for analysis, but the deployed model
  still uses the AIS/weather/time feature contract until retrained.
- React/Vite dashboard with bundled demo data for local review.
- CI with Ruff, mypy, pytest, frontend linting, and secret scanning.

The first model was trained on a small early dataset, so the model metric is a
pipeline validation signal rather than a mature production benchmark. The
system is designed so retraining with more accumulated data is a repeatable
command, not a rewrite.

## Architecture At A Glance

```text
AISStream / Open-Meteo / NOAA
          |
          v
AWS Lambda ingestion jobs
          |
          v
S3 raw NDJSON partitions
          |
          v
Athena CTAS feature tables
          |
          v
LightGBM training and prediction
          |
          v
dashboard data artifacts in S3/CloudFront
          |
          v
React + Vite operations dashboard on Vercel
```

## Repository Layout

```text
athena/          CTAS SQL for target and feature tables
dashboard-v2/    React/Vite dashboard; local demo runs from public fixtures
docs/            architecture, runbooks, data contracts, and reviewer notes
infra/           Terraform support files for surrounding AWS infrastructure
ingestion/       AIS, weather, tide, and S3 writer clients
models/          feature contract, training, dataset build, and prediction CLIs
scripts/         operational helpers for prediction refresh and cost control
serverless/      Lambda handlers, Athena helpers, ports, metrics, geofences
tests/           unit and smoke tests
warehouse/       seed/reference data used by ingestion and tests
template.yaml    AWS SAM serverless stack
```

## Prerequisites

For the 60-second local dashboard demo:

- Node.js 20 or newer
- npm 10 or newer

For Python checks and model commands:

- Python 3.12
- uv

For live AWS ingestion/deploy:

- AWS CLI configured with a profile or role
- AWS SAM CLI
- An AISStream API key
- An S3 bucket/stack created by this project or equivalent permissions

## Run Locally In 60 Seconds

This path does **not** require secrets. It uses the committed dashboard fixture
at `dashboard-v2/public/demo-data.js`.

```bash
git clone https://github.com/loicns/data-party-logistics.git
cd data-party-logistics/dashboard-v2
npm ci
npm run dev
```

Open the URL printed by Vite, normally:

```text
http://localhost:5173
```

Useful dashboard commands:

```bash
npm run lint
npm run build
npm run preview
```

## Backend Setup

Install Python dependencies from the repository root:

```bash
uv sync --all-extras
cp .env.example .env
```

For local checks that do not call AWS:

```bash
uv run ruff check .
uv run ruff format --check .
uv run pytest
```

For AWS-backed model/data commands, fill `.env` with your own bucket, region,
profile, and API keys first:

```bash
uv run python models/training/build_dataset.py
uv run python models/training/train.py
uv run python models/training/predict.py --port NLRTM
uv run python scripts/refresh_predictions.py
```

For the additive AIS v2 experiment, keep serving on the current model and write
candidate artifacts separately:

```bash
uv run python models/training/build_dataset_v2.py --start-hour "2026-06-14 15:00:00"
uv run python models/training/train_v2.py
```

## Live Deploy

Copy the template and add only your own local values:

```bash
cp .env.example .env
```

Then deploy the SAM stack:

```bash
./deploy.sh
```

`deploy.sh` reads non-secret deployment parameters from `.env` and passes the
AISStream key to SAM as a `NoEcho` parameter. Real keys stay out of git.

Cost-control helpers:

```bash
scripts/pause.sh
scripts/resume.sh
```

See `SHUTDOWN.md` for the full pause/resume runbook.

## Secrets Policy

Handle secrets with a template-plus-runtime pattern:

- Commit `.env.example` with variable names, comments, and fake placeholders.
- Never commit `.env`, cloud credentials, private keys, API tokens, or generated
  files containing credentials.
- Use local `.env` only on your machine.
- Use GitHub Actions secrets for CI/CD values.
- Use Vercel project environment variables for dashboard deployment values such
  as `VITE_DATA_URL`.
- Treat CloudFront as the public data-artifact CDN only; the public dashboard UI
  is the Vercel production app.
- Use AWS Systems Manager Parameter Store or AWS Secrets Manager for long-lived
  production secrets when the stack grows beyond the current pilot.

For an interview demo, keep the dashboard in local demo mode unless you are
explicitly demonstrating the live AWS pipeline. The reviewer can run the UI
without receiving any private keys, and you can still show live mode from your
own preconfigured environment.

More detail: `docs/secrets-and-environments.md`.

## Environment Variables

Common values are documented in `.env.example`.

Required only for live AWS ingestion/deploy:

```text
AWS_REGION
AWS_PROFILE
S3_BUCKET_RAW
AISSTREAM_API_KEY
```

Optional, depending on workflow:

```text
ATHENA_DATABASE
ATHENA_OUTPUT_LOCATION
PUBLIC_DASHBOARD_BUCKET_NAME
PUBLIC_DASHBOARD_DISTRIBUTION_ID
VITE_DATA_URL
POSTGRES_*
FRED_API_KEY
NOAA_API_TOKEN
CMEMS_*
MAERSK_API_KEY
CMACGM_API_KEY
```

## Documentation Map

- `docs/index.md` - curated reviewer documentation hub
- `docs/model-card.md` - public model card
- `docs/coverage.md` - current source and port coverage
- `docs/14-system-architecture-overview.md` - current system architecture
- `docs/15-data-flow-and-storage-contract.md` - storage and data contracts
- `docs/17-monitoring-and-alarm-semantics.md` - freshness and alert semantics
- `docs/18-iam-and-deployment-identity.md` - IAM and deployment identity
- `docs/19-athena-query-layer-guide.md` - Athena query layer
- `docs/blueprint/10-DATA-DICTIONARY.md` - dashboard/data dictionary
- `dashboard-v2/README.md` - dashboard-specific operations

## Production Readiness Notes

- No committed real secrets; `.gitignore` blocks `.env`, keys, state, cache, and
  local data artifacts.
- AWS deploy secrets are injected at deploy time, not stored in `samconfig.toml`.
- Dashboard has a no-secret local fixture path for reviewers.
- Lambda handlers isolate per-port failures where partial data is safer than a
  failed batch.
- Python and frontend lint/test commands are listed above and run in CI.

## License

MIT. See `LICENSE`.
