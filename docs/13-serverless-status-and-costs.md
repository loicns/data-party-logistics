# Serverless Status And Cost Forecast

This page is the detailed implementation status for the **near-zero-cost AWS-only pilot**.

It answers three questions:

1. what has already been implemented in the repo
2. what still remains before the pilot is truly live
3. what the expected monthly cost should be

All cost statements below are **forecast estimates as of May 10, 2026**, not a billed invoice.

## Executive Summary

The repo now contains a real **serverless pilot path** that replaces the earlier:

- Prefect control plane
- Fargate worker idea
- always-on Postgres warehouse for the pilot runtime

with:

- EventBridge Scheduler
- AWS Lambda
- S3
- Glue + Athena
- CloudWatch + SNS
- GitHub Actions deployment

This is now a **real runtime fork** in the repository, not just a written plan.

The implementation is best described as:

- **repo-complete enough to deploy**
- **cloud-not-yet-live until AWS secrets and stack deployment are done**

## What Has Been Implemented

## 1. Deployable serverless infrastructure template

Implemented:

- [template.yaml](/Users/loicns/Projects/data-party-logistics/template.yaml)

What it now defines:

- one pilot S3 data bucket
- one SNS alerts topic
- Glue database
- Glue external tables for:
  - `raw_ais_positions`
  - `raw_weather_observations`
  - `raw_noaa_tides`
- Athena workgroup
- Lambda functions for:
  - hourly AIS snapshots
  - hourly weather ingestion
  - daily NOAA ingestion
  - hourly dashboard export
  - 30-minute freshness checks
- CloudWatch dashboard
- CloudWatch alarms

Validation status:

- the CloudFormation/SAM template validates successfully

## 2. Lambda runtime package

Implemented:

- [serverless/handlers/ais_lambda.py](/Users/loicns/Projects/data-party-logistics/serverless/handlers/ais_lambda.py)
- [serverless/handlers/weather_lambda.py](/Users/loicns/Projects/data-party-logistics/serverless/handlers/weather_lambda.py)
- [serverless/handlers/noaa_lambda.py](/Users/loicns/Projects/data-party-logistics/serverless/handlers/noaa_lambda.py)
- [serverless/handlers/export_lambda.py](/Users/loicns/Projects/data-party-logistics/serverless/handlers/export_lambda.py)
- [serverless/handlers/freshness_lambda.py](/Users/loicns/Projects/data-party-logistics/serverless/handlers/freshness_lambda.py)
- [serverless/athena.py](/Users/loicns/Projects/data-party-logistics/serverless/athena.py)
- [serverless/metrics.py](/Users/loicns/Projects/data-party-logistics/serverless/metrics.py)
- [serverless/s3_health.py](/Users/loicns/Projects/data-party-logistics/serverless/s3_health.py)
- [serverless/ports.py](/Users/loicns/Projects/data-party-logistics/serverless/ports.py)

What this means:

- the pilot now has dedicated Lambda entrypoints
- the existing Python ingestion clients are reused instead of rewritten
- CloudWatch custom metrics can be emitted
- Athena queries can be executed from Lambda
- export freshness can be checked without RDS

## 3. AIS client adapted for serverless observability

Updated:

- [ingestion/clients/ais_stream.py](/Users/loicns/Projects/data-party-logistics/ingestion/clients/ais_stream.py)

What changed:

- the AIS consumer now returns:
  - `records_received`
  - `records_written`
  - `files_written`

Why this matters:

- the AIS Lambda can now emit operational metrics
- CloudWatch alarms can detect “ran but wrote nothing”
- the pilot monitoring layer is more honest than a binary success flag

## 4. Athena-backed dashboard export

Implemented:

- [serverless/handlers/export_lambda.py](/Users/loicns/Projects/data-party-logistics/serverless/handlers/export_lambda.py)

What it does:

- queries Athena over S3-backed raw tables
- derives port-level summary metrics for:
  - Rotterdam
  - Singapore
  - Los Angeles
- builds the dashboard payload
- writes:
  - `exports/dashboard/demo-data.js`
  - `curated/port_metrics/date=YYYY-MM-DD/latest.json`

This replaces the always-on Postgres dependency for the pilot export path.

## 5. Browser-first deployment path

Implemented:

- [.github/workflows/deploy-serverless.yml](/Users/loicns/Projects/data-party-logistics/.github/workflows/deploy-serverless.yml)
- [requirements.txt](/Users/loicns/Projects/data-party-logistics/requirements.txt)

What it does:

- builds the SAM app in GitHub Actions
- deploys the stack to AWS
- uses GitHub secrets instead of a local machine

This is the intended “no local machine required” deploy path after initial setup.

## 6. Docs site integration

Implemented:

- [docs/12-serverless-pilot.md](/Users/loicns/Projects/data-party-logistics/docs/12-serverless-pilot.md)
- this page
- links added in [docs/index.md](/Users/loicns/Projects/data-party-logistics/docs/index.md)
- navigation added in [mkdocs.yml](/Users/loicns/Projects/data-party-logistics/mkdocs.yml)

This means the serverless pilot is now represented as a documented product direction inside the docs site, not hidden in code only.

## What Has Been Verified

Verified in the repo:

- Python modules compile
- `ruff` passes on the new serverless code
- the CloudFormation template validates
- docs build successfully
- the repo test suite still passes

Most recent checks:

- `aws cloudformation validate-template --template-body file://template.yaml ...`
- `uv run python -m py_compile ...`
- `uv run ruff check ...`
- `uv run pytest --tb=short -q`
- `uv run mkdocs build -q`

## What Still Remains To Do

## 1. AWS account setup

Still required:

- create the deployment IAM role used by GitHub Actions
- grant that role permission to:
  - deploy CloudFormation/SAM
  - manage Lambda
  - manage Glue
  - manage Athena
  - manage S3
  - manage CloudWatch
  - manage SNS

Status:

- **not yet done in the repo**
- this is an AWS account task

## 2. GitHub secrets

Still required:

- `AWS_DEPLOY_ROLE_ARN`
- `AISSTREAM_API_KEY`
- optional `DPL_ALERT_EMAIL`

Status:

- **not yet configured**

## 3. First deployment

Still required:

- run the `Deploy Serverless Pilot` GitHub Actions workflow
- confirm stack creation in AWS
- confirm SNS email subscription if alert email is used

Status:

- **not yet live**

## 4. First production-like validation cycle

Still required after deployment:

- confirm hourly AIS Lambda runs for 5 minutes
- confirm weather Lambda writes S3 files
- confirm NOAA Lambda writes S3 files
- confirm Athena reads the raw lake
- confirm export Lambda writes `demo-data.js`
- confirm CloudWatch dashboard populates
- confirm alarms can fire correctly

Status:

- **infrastructure is prepared, but runtime behavior is not yet observed in AWS**

## 5. Dashboard hosting decision

Still required:

- decide where the dashboard static files are served from

Good low-cost options:

- S3 static website hosting
- CloudFront in front of S3
- GitHub Pages for docs, with dashboard artifact sync if desired

Current status:

- the export artifact path is implemented
- the final hosting target is **not yet finalized**

## 6. Data quality hardening

Still recommended before calling it truly live:

- add more explicit Athena query failure handling visibility
- validate Glue table field compatibility with real landed JSON
- consider Parquet conversion later if Athena scan costs rise
- add stricter freshness and zero-record alarms by source

Current status:

- **good enough for pilot**
- **not yet fully hardened for production**

## Remaining Work Checklist

### Ready in code

- serverless stack template
- Lambda handlers
- export path
- monitoring scaffolding
- GitHub Actions deploy path
- docs site integration

### Still manual

- AWS IAM deployment role
- GitHub secrets
- first stack deployment
- alert email confirmation
- live run verification
- final dashboard hosting choice

### Still future improvements

- Parquet/curated data optimization
- deeper data quality alarms
- more robust export health and retry logic
- CI checks for SAM template and Lambda packaging

## Cost Forecast

## Target monthly cost

The intended pilot target remains:

- **roughly $0 to $10 per month**

That is realistic **if usage stays small** and you avoid the expensive traps:

- no NAT gateway
- no RDS instance
- no always-on Fargate worker
- low Athena scan volume
- small CloudWatch logs

## Cost breakdown by service

### 1. EventBridge Scheduler

Expected cost:

- effectively **$0** at this pilot scale

Why:

- EventBridge Scheduler includes a **14 million invocation free tier per month**

For this pilot:

- 5 recurring schedules
- roughly hourly or daily cadence
- far below the free tier

Source:

- Amazon EventBridge Scheduler overview says the free tier includes **14 million invocations per month**
- Amazon EventBridge pricing page shows the same free-tier framing

References:

- [Amazon EventBridge Scheduler](https://aws.amazon.com/eventbridge/scheduler/)
- [Amazon EventBridge Pricing](https://aws.amazon.com/fr/eventbridge/pricing/)

### 2. Lambda

Expected cost:

- usually **$0 to low single digits**

Why:

- the pilot has small scheduled jobs
- AIS runs hourly for 5 minutes, but still only one Lambda execution per hour
- weather, export, and freshness jobs are short

Actual billed cost depends on:

- memory size
- duration
- number of requests

Reference:

- [AWS Lambda Pricing](https://aws.amazon.com/lambda/pricing/)

### 3. S3

Expected cost:

- usually **pennies to a few dollars**

Why:

- the pilot stores raw NDJSON and a small export artifact
- the bucket has lifecycle rules already baked into the stack

Reference:

- [Amazon S3 Pricing](https://aws.amazon.com/s3/pricing/)

### 4. Athena

Expected cost:

- usually **pennies to low dollars**

Why:

- Athena charges by data scanned
- the pilot is only reading a small 3-port raw lake
- query frequency is low

Risk factor:

- if the raw JSON lake grows and queries are not optimized, Athena can become the first service that needs tuning

Reference:

- [Amazon Athena Pricing](https://aws.amazon.com/athena/pricing/)

### 5. CloudWatch + SNS

Expected cost:

- usually **low single digits**

Why:

- Lambda logs are cheap at low volume
- CloudWatch dashboard/alarms are small
- SNS email notifications are light

Largest variable:

- log volume from AIS and export jobs

## Total forecast scenarios

### Scenario A: very disciplined pilot

- EventBridge Scheduler: ~$0
- Lambda: ~$0 to $2
- S3: ~$0 to $1
- Athena: ~$0 to $2
- CloudWatch + SNS: ~$1 to $3

**Estimated total: ~$1 to $8 per month**

### Scenario B: normal pilot drift

- EventBridge Scheduler: ~$0
- Lambda: ~$1 to $4
- S3: ~$1 to $2
- Athena: ~$1 to $4
- CloudWatch + SNS: ~$2 to $4

**Estimated total: ~$5 to $14 per month**

### Scenario C: cost mistake version

This is what breaks the low-cost promise:

- adding RDS back
- adding Fargate back
- adding NAT gateway
- running high-scan Athena queries carelessly

At that point, the pilot is no longer near-zero-cost.

## Total forecast to use in planning

The honest planning number to use is:

- **best-case operating target:** `$1–8/month`
- **safe planning budget:** `$5–15/month`

That is the number I would use for stakeholder discussions.

## Why Prefect Cloud Is No Longer In The Cost Model

This pilot page intentionally excludes Prefect Cloud from the final cost model.

Why:

- the implemented stack no longer depends on Prefect for orchestration
- the scheduled runtime is now EventBridge + Lambda

That was the whole economic reason for the architecture fork.

## Recommended Next Move

The next best action is not more repo code.

It is:

1. create the AWS deploy role
2. add the GitHub secrets
3. run the serverless deployment workflow
4. observe one full hourly cycle in AWS
5. update this page with real observed costs after a few days

At that point, this page can shift from **forecast** to **measured operating cost**.
