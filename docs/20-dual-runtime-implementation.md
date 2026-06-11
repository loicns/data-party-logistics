# Dual Runtime Implementation

This artifact explains the current truth of the repo:

- the **live deployed pilot runtime** is the AWS serverless path
- the **Prefect runtime still exists in code**, but it is not the active deployed control plane

The goal of this page is to make the relationship between the two paths clear, compare what changed, and outline how each could run automatically without constant human intervention.

## Short Answer

**Was Prefect decommissioned?**

Not fully from the codebase, but effectively **yes for the live pilot runtime**.

What that means in practice:

- Prefect flows still exist under `orchestration/flows/`
- `pyproject.toml` still includes `prefect`
- the repo still contains the older warehouse-first and Postgres/dbt orchestration path
- the **currently deployed system** uses:
  - SAM
  - Lambda
  - EventBridge schedules
  - S3
  - Glue/Athena
  - CloudWatch

So the answer is:

- **Prefect is not gone from the repo**
- **Prefect is not the active deployed scheduler for the current pilot**

## Current Runtime Split

### Active deployed runtime

- `template.yaml`
- `.github/workflows/deploy-serverless.yml`
- `serverless/handlers/*.py`

This path owns:

- hourly AIS snapshot scheduling
- hourly weather scheduling
- daily NOAA scheduling
- dashboard export scheduling
- freshness checks
- S3 landing and export writing
- CloudWatch metrics and alarms

### Legacy / alternate runtime still present

- `orchestration/flows/ingest_batch.py`
- `orchestration/flows/ingest_ais.py`
- `orchestration/flows/dbt_flow.py`
- `orchestration/flows/freshness_flow.py`
- `orchestration/alerts.py`

This path was designed to own:

- Prefect flow scheduling
- concurrent ingestion task orchestration
- long-running AIS streaming
- S3-to-Postgres loading
- dbt builds and dbt freshness checks
- Prefect artifacts and run UI

## What Was Replaced

### 1. Scheduler and orchestration control plane

**Former implementation**

- Prefect `@flow` orchestration
- likely Fargate/worker or other hosted runtime assumptions
- flow state tracked in Prefect UI

**Replacement**

- EventBridge schedules
- Lambda invocation per pipeline
- CloudWatch logs, metrics, dashboards, and alarms

### 2. AIS runtime shape

**Former implementation**

- `orchestration/flows/ingest_ais.py`
- long-running AIS streaming flow
- reconnecting control loop managed by Prefect task retries

**Replacement**

- scheduled Lambda snapshot window
- 300 to 420 second bounded run
- clean stop every hour

### 3. Batch ingestion orchestration

**Former implementation**

- `orchestration/flows/ingest_batch.py`
- Prefect tasks submitted concurrently:
  - AIS
  - weather
  - NOAA
  - FRED
  - CMEMS

**Replacement**

- separate Lambda functions per source
- each source scheduled independently
- no shared flow-run wrapper required

### 4. Query and transform layer

**Former implementation**

- raw S3 files loaded into Postgres
- `orchestration/flows/dbt_flow.py`
- dbt build over Postgres models
- dbt freshness checks

**Replacement**

- raw JSON remains in S3
- Glue tables define schema
- Athena queries raw S3 directly
- export Lambda generates dashboard artifacts directly from Athena

### 5. Operator visibility

**Former implementation**

- Prefect flow runs
- Prefect artifacts
- Prefect retry history

**Replacement**

- CloudWatch dashboards
- CloudWatch alarms
- Lambda logs
- SNS alerts

## Comparison Table

| Area | Prefect Runtime | Serverless Runtime |
|---|---|---|
| Scheduler | Prefect deployments / worker model | EventBridge schedules |
| Compute | Worker / container / long-running task assumptions | Lambda |
| AIS | Continuous or batch flow | Hourly bounded snapshot |
| Storage | S3 raw + Postgres warehouse path | S3 raw + S3 export path |
| Query layer | Postgres + dbt | Glue + Athena |
| Dashboard feed | Warehouse-backed transform path | `demo-data.js` export artifact |
| Monitoring | Prefect UI + logs | CloudWatch + SNS |
| Cost shape | higher steady-state baseline | near-zero / low variable |
| Best use case | richer orchestration and warehouse workflows | cheap pilot ingestion and serving |

## How Each Path Can Work Well

## A. Serverless runtime

This is the best fit for the current 3-port pilot.

### Strengths

- cheapest path to stay live
- simple deploy model
- no always-on worker
- no RDS baseline
- clean browser-first GitHub deployment story

### What it needs to work well automatically

1. EventBridge schedules remain enabled
2. all Lambda env vars are correct
3. export Lambda publishes to both:
   - pilot data bucket
   - public dashboard bucket
4. CloudFront invalidation works after public artifact publish
5. alarms are tuned so they are useful, not noisy
6. log retention and Athena scan discipline are kept under control

### Automation completeness target

To make the serverless path fully hands-off:

- ingestion Lambdas run on schedule
- export Lambda publishes `demo-data.js` automatically
- dashboard bucket updates automatically
- CloudFront refreshes automatically
- CloudWatch alarms notify on stale or failed runs

That path is now very close.

## B. Prefect runtime

This path still makes sense if you want:

- richer DAG orchestration
- one place to coordinate many heterogeneous sources
- Postgres/dbt as a real warehouse-first platform
- a future broader internal data platform rather than only a cheap pilot

### Strengths

- stronger orchestration semantics
- cleaner task grouping and retry behavior
- richer flow-level observability
- better fit for mixed cadence and mixed dependency workflows
- more natural home for dbt-first and warehouse-first operations

### What it needs to work well automatically

1. a real Prefect deployment target
   - Prefect Cloud or Prefect server
   - plus worker runtime
2. a stable compute plane
   - likely ECS Fargate or another long-running worker host
3. durable secrets and runtime env configuration
4. a decision on AIS mode:
   - continuous `ingest_ais`
   - or bounded hourly AIS inside `ingest_batch`
5. Postgres infrastructure if `dbt_flow.py` stays active
6. monitoring and alerting that does not depend on manual UI checks

### Important current gaps in the Prefect path

These are visible in the current code:

- `ingest_batch.py` still uses `duration_sec=60` for AIS testing, not production 300 seconds
- `ingest_batch.py` includes sources that the live pilot does not currently deploy
  - CMEMS
  - FRED
- `dbt_flow.py` still assumes S3-to-Postgres loading
- `freshness_flow.py` still assumes native dbt freshness commands and dbt artifacts
- there is no evidence in the live deployed stack that Prefect workers are currently running

So the Prefect code is real, but the runtime is not currently activated as a production-like service.

## How To Make Each Path Fully Automatic

## Option 1. Serverless-only pilot

This is the current recommended operating model.

### Required automation

- GitHub Actions deploys SAM
- EventBridge schedules Lambdas
- export Lambda writes:
  - `s3://pilot-bucket/exports/dashboard/demo-data.js`
  - `s3://dashboard-bucket/demo-data.js`
- CloudFront invalidation runs automatically
- CloudWatch alarms notify on:
  - stale AIS
  - stale export
  - Lambda errors
  - zero AIS files

### Result

- no human needed for normal ingestion
- no human needed for normal dashboard refresh
- human only needed for alarms, code changes, or upstream failures

## Option 2. Prefect-first data platform

This is the right direction if the real goal is a broader orchestration and warehouse platform.

### Required automation

1. deploy Prefect control plane
2. deploy worker runtime
3. promote `ingest_batch` to the official batch orchestrator
4. change AIS duration in `ingest_batch.py` from `60` to production `300`
5. decide whether `ingest_ais.py` remains:
   - operational
   - diagnostic
   - retired
6. provision Postgres and networking for `dbt_flow.py`
7. schedule:
   - hourly `ingest_batch`
   - hourly or offset `dbt_flow`
   - daily `freshness_flow`
8. make alerting and runbooks work without opening Prefect manually every hour

### Result

- stronger orchestration platform
- more moving parts
- higher steady-state cost
- better future fit for broader transformation and ML work

## Option 3. Dual implementation

This is the most flexible path, but it only works if the responsibilities are kept clean.

### Recommended dual split

Use **serverless as the live pilot runtime** and **Prefect as the experimental / warehouse platform**.

#### Serverless owns

- demo-serving runtime
- public dashboard artifact
- 3-port pilot ingestion
- low-cost operational monitoring

#### Prefect owns

- exploratory broader-source ingestion
- warehouse-first transformations
- Postgres/dbt experimentation
- future ML feature generation workflows

### Critical rule

Do **not** let both runtimes write the same production dashboard artifact blindly.

If you keep both:

- serverless should publish the live dashboard artifact
- Prefect should publish separate experimental outputs
  - separate S3 prefixes
  - separate tables
  - separate dashboards

Otherwise you create:

- hidden race conditions
- conflicting definitions of “latest”
- unclear alert ownership

## Recommended Dual Contract

### Serverless contract

- raw landing for the active pilot
- Athena/Glue query layer for the pilot
- exported dashboard artifact for the pilot
- CloudWatch alarms for the pilot

### Prefect contract

- alternative or expanded ingest sources
- S3 raw experimental prefixes
- Postgres/dbt warehouse branch
- research-grade or internal-only artifacts

### Naming discipline

Keep the outputs separate:

- `raw/source=.../` for serverless pilot
- `raw-experimental/source=.../` or separate bucket for Prefect expansion
- separate export prefixes
- separate dashboards
- separate alarm namespaces if both stay active

## Recommended Direction

For the current state of this repo, the cleanest direction is:

1. keep the serverless stack as the live pilot runtime
2. treat Prefect as an alternate implementation path, not the currently deployed one
3. only reactivate Prefect operationally if you intentionally choose:
   - warehouse-first runtime
   - richer orchestration
   - higher cost tolerance

## Decision Summary

If your question is:

**“Can I still run Prefect?”**

Yes, from the codebase point of view.

If your question is:

**“Is Prefect the active deployed pilot control plane?”**

No.

If your question is:

**“Can both exist without constant human intervention?”**

Yes, but only if:

- ownership is separated
- outputs do not collide
- monitoring is explicit
- the serverless path remains the source of truth for the live pilot unless you intentionally switch it

## Next Practical Move

If you want a true dual runtime in practice, the next work should be:

1. declare one runtime as **live serving**
2. declare the other as **experimental / warehouse**
3. separate their S3 output contracts
4. separate their monitoring contracts
5. automate each on its own deploy path

Without that discipline, dual runtime quickly becomes double ambiguity instead of double capability.
