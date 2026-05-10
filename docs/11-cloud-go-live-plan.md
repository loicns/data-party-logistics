# Cloud Go-Live Plan

This artifact is a deployment planning document for making the pipeline live on AWS with Prefect orchestration.

It assumes the following target operating model:

- AIS ingestion runs **hourly**
- the WebSocket stays open for **5 to 7 minutes per hour**
- lower-frequency sources run as regular batch jobs
- Prefect runs the orchestration automatically
- AWS ECS Fargate is used as the compute runtime for flow execution
- Prefect UI and CloudWatch provide monitoring visibility

This document intentionally avoids code changes. It is a planning and readiness artifact only.

## Disclaimer Before Implementation

Before implementing the cloud pipeline, adjust these decisions first:

1. **Confirm the AIS operating model**

   The current repo still contains two AIS patterns:

   - a continuous stream flow in `orchestration/flows/ingest_ais.py`
   - a short AIS snapshot task inside `orchestration/flows/ingest_batch.py`

   Looking at `orchestration/flows/ingest_batch.py`, the batch flow is already designed as the operational orchestrator:

   - it submits AIS, weather, NOAA tides, and CMEMS concurrently
   - it already has Prefect task retries
   - it already creates a Prefect markdown artifact summary
   - it already sends partial or total failure alerts

   That means the go-live path should treat `ingest_batch.py` as the primary hourly ingestion flow unless you intentionally retire that pattern.

   If your real operating decision is:

   - open WebSocket hourly
   - collect for 5 to 7 minutes
   - close to save resources

   then that decision should become the single official ingestion mode.

2. **Decide whether Prefect Cloud or self-hosted Prefect will be the control plane**

   This affects:

   - authentication
   - work pool setup
   - secret storage
   - deployment commands
   - monitoring experience

   For simplicity and speed, Prefect Cloud is the better first production path.

3. **Decide whether Fargate will run flows directly or host a long-lived Prefect worker**

   Two valid patterns exist:

   - ECS task per flow run
   - long-lived Prefect worker running in Fargate and polling a work pool

   For this repo, the better starting pattern is:

   - one long-lived Prefect worker in Fargate
   - scheduled deployments handled by Prefect

   It is simpler to reason about and easier to monitor at first.

4. **Fix raw loading strategy before scale**

   The current S3-to-Postgres loader still works like a learning-stage bulk loader.
   It scans prefixes and is not yet a production-grade incremental manifest loader.

   Before go-live, confirm:

   - whether reloading a whole prefix is acceptable for the next week
   - or whether a `load_manifest` / watermark table must be added first

   For a true live pipeline, incremental loading is strongly preferred.

5. **Choose the first production scope**

   Do not launch “global maritime intelligence” on day one.
   Launch the narrow version:

   - 3 ports
   - AIS
   - weather
   - NOAA tides where relevant
   - dbt transforms
   - dashboard export

   This is the only scope that is honest, supportable, and monitorable right now.

## Recommended Target Architecture

The production-like version of this project should behave like this:

1. **AIS hourly ingestion**

   - Prefect scheduled deployment runs `ingest_batch` every hour
   - Fargate worker picks up the flow
   - inside that batch flow, the AIS task opens the WebSocket
   - AIS messages are collected for 5 to 7 minutes
   - records are flushed to S3
   - the AIS task exits cleanly while the other ingestion tasks run in parallel

2. **Batch side-source ingestion**

   - weather runs as part of the same hourly `ingest_batch` flow
   - NOAA tides currently run as part of the same batch flow, though you may later reduce that cadence
   - CMEMS also runs in the same batch flow if retained

3. **Warehouse refresh**

   - raw S3 files load into Postgres raw tables
   - dbt build produces staging and mart tables
   - freshness checks and tests run afterward

4. **Serving/export**

   - dashboard export regenerates a browser-facing artifact
   - later this can become an API or service endpoint

5. **Monitoring**

   - Prefect UI tracks flow runs, retries, artifacts, and failures
   - CloudWatch tracks ECS task health, logs, runtime, and errors
   - alerting notifies you when ingestion freshness or run health degrades

## Honest Recommendation On AIS Scheduling

Your updated decision makes sense:

- **hourly 5 to 7 minute AIS capture is more resource-efficient than 24/7 streaming**
- it fits your current demo and warehouse goals
- it is easier to deploy and explain
- it is cheaper to operate on Fargate

The tradeoff is also real:

- you lose some between-window vessel motion detail
- you should not claim continuous real-time coverage
- your product language should be “hourly operational snapshots” rather than “live tracking”

That tradeoff is acceptable for this stage.

Looking specifically at `orchestration/flows/ingest_batch.py`, there is one important readiness note:

- the current batch flow still uses `ingest_ais_batch.submit(duration_sec=60)` for testing

Before go-live, that should be treated as an operational parameter decision:

- `300` seconds for a 5-minute hourly capture
- `420` seconds for a 7-minute hourly capture

Also note that the flow timeout comment currently describes a 15-minute envelope with a testing-oriented AIS duration. That timeout should be re-evaluated before live scheduling so it reflects the true production AIS duration and the slowest expected side-source runtime.

## What To Provision

You will need these cloud components:

### 1. Existing pieces already in repo

- S3 raw bucket
- RDS Postgres
- Terraform base in `infra/`

### 2. New pieces to add before go-live

- ECS cluster
- ECS task definition for Prefect worker
- ECS service for the long-lived Prefect worker
- CloudWatch log groups
- IAM task execution role
- IAM task role with access to:
  - S3
  - CloudWatch logs
  - Secrets Manager or environment secrets
  - optionally RDS access by network path
- VPC/subnets/security groups for ECS-to-RDS connectivity
- Prefect work pool targeting ECS/Fargate or a worker polling model
- secrets store for:
  - `AISSTREAM_API_KEY`
  - database credentials if not IAM-auth based
  - Prefect API key

## Proposed Deployment Model

Use this simple operating model first:

### A. One Prefect worker running in Fargate

Purpose:

- stays up
- polls Prefect for work
- executes scheduled flows

Why this is the best first step:

- easiest mental model
- easier log inspection
- easier to control retries and schedules centrally
- no need to build a more complex event-triggered ECS execution pattern first

### B. Prefect deployments for each pipeline

Create three core production deployments first:

1. `ingest-batch-hourly`
2. `dbt-refresh-hourly`
3. `freshness-check-hourly`

Optional later:

4. `dashboard-export-hourly`
5. a legacy or diagnostic `ingest-ais` deployment only if you still want a standalone AIS test flow

Why this correction matters:

- the repo already treats `ingest_batch` as the flow that owns hourly ingestion
- creating both `ingest-ais-hourly` and `ingest-batch-hourly` as active production schedules would duplicate AIS work
- duplication would create overlapping S3 landings, harder debugging, and misleading monitoring

## Recommended Schedules

These schedules fit your current product shape:

1. **AIS hourly**

   - every hour at minute `00`
   - AIS duration inside `ingest_batch`: `300` to `420` seconds

2. **Weather / batch ingestion**

   - same `ingest-batch-hourly` run, not a separate schedule

3. **dbt refresh**

   - every hour at minute `20` or `25`, after `ingest_batch` finishes or has had enough time to land files

4. **freshness and tests**

   - every hour at minute `35`

5. **dashboard export**

   - every hour at minute `40`

Why stagger them:

- avoids overlap
- reduces load spikes
- gives AIS files time to land in S3 before warehouse loads

## Step-By-Step Go-Live Process

## Phase 1: Finalize The Operating Decisions

Before touching cloud infrastructure, write down and lock:

- AIS is hourly for 5 to 7 minutes
- `ingest_batch` is the single official hourly ingestion flow
- demo scope is 3 ports
- Prefect Cloud or self-hosted Prefect
- Fargate worker pattern
- target schedules
- expected freshness SLA

Output of this phase:

- one approved operating note
- no ambiguity about “continuous vs hourly AIS”

## Phase 2: Prepare The Runtime Contract

Define what every flow needs at runtime:

- Python environment
- repo checkout or image contents
- `.env` equivalents
- AWS credentials model
- database connectivity path
- S3 bucket names
- Prefect authentication

Decide whether you will:

- build a Docker image for the repo
- or mount and run code another way

For Fargate, a Docker image is the right answer.

Output of this phase:

- one container image plan
- one secrets/env var inventory

## Phase 3: Provision AWS Execution Infrastructure

Provision:

- ECS cluster
- Fargate-compatible task definition
- task roles
- security groups
- log groups
- secrets wiring

Critical network requirement:

- ECS tasks must reach RDS
- ECS tasks must reach S3
- ECS tasks must reach Prefect API
- ECS tasks must reach AISStream WebSocket endpoint

This is a common hidden failure point.
If networking is wrong, flows will appear “healthy” at container boot but fail at runtime.

Output of this phase:

- one running Fargate task that can start successfully
- visible CloudWatch logs

## Phase 4: Bring Up Prefect Control Plane

Create:

- work pool
- worker authentication
- deployments
- schedules

Validation goals:

- the worker registers and shows as online
- a test flow can be scheduled and run remotely
- logs appear in both Prefect and CloudWatch

Output of this phase:

- working orchestration control plane

## Phase 5: Enable One Flow At A Time

Do not activate everything together.

Enable in this order:

1. `ingest-batch-hourly`
2. `dbt-refresh-hourly`
3. `freshness-check-hourly`
4. optional `dashboard-export-hourly`

Why:

- `ingest_batch` is already the real integration point for AIS plus side sources
- dbt and freshness only matter after raw landing works

Each flow should first run manually, then on a schedule.

Output of this phase:

- controlled rollout
- easier debugging

## Phase 6: Build Monitoring Views

You asked for a monitoring dashboard for each flow and each ingestion pipeline.

Use two layers of visibility:

### Prefect UI should answer

- Did the flow run?
- Did it fail?
- How long did it take?
- Which task failed?
- What artifact summary was created?

### CloudWatch should answer

- Did the ECS task start?
- Did it crash?
- What logs were emitted?
- How much CPU and memory did it use?
- Are runs getting slower?

## Recommended Monitoring Dashboard Layout

Create one operational view with these sections:

### 1. Flow Health

Panels:

- batch ingestion success rate
- per-task success breakdown inside the batch flow:
  - AIS
  - weather
  - NOAA tides
  - CMEMS
- dbt flow success rate
- freshness check success rate

### 2. Runtime Health

Panels:

- ECS task restarts
- task exit codes
- CPU usage
- memory usage
- run duration by flow

### 3. Data Landing Health

Panels:

- count of new S3 AIS files per hour
- count of weather files per hour
- count of NOAA files per day
- count of CMEMS files per run if that source stays enabled
- last successful raw load timestamp

### 4. Warehouse Freshness

Panels:

- latest `_loaded_at` by source table
- dbt freshness status
- count of stale sources

### 5. Product Readiness

Panels:

- latest dashboard export timestamp
- count of vessels exported per demo port
- latest mart rows for each port

## Alerts You Should Have Before Calling It Live

At minimum, set alerts for:

1. AIS flow did not run in the last 90 minutes
2. `ingest_batch` ran but the AIS task produced zero landed files
3. `ingest_batch` failed twice in a row
4. any critical subtask inside `ingest_batch` fails repeatedly
5. dbt build failed
6. freshness check reports stale AIS or weather data
7. ECS worker task stopped unexpectedly
8. repeated WebSocket reconnect or auth failures

## What To Reconsider Before Real Production

These are the biggest reasons not to overstate production readiness yet:

1. **AIS coverage limitations**

   AISStream is useful, but your system is still closer to coastal and port-adjacent visibility than full ocean certainty.

2. **Loader maturity**

   The current raw loading pattern should become incremental before scale.

3. **Truth in product language**

   With hourly 5 to 7 minute snapshots, do not describe the product as continuous real-time tracking.

4. **Small-scope first launch**

   Three ports is a valid pilot.
   Global claims are not.

5. **Monitoring depth**

   Prefect flow visibility is good, but production maturity also needs:

   - infrastructure alerts
   - data volume anomaly checks
   - schema drift awareness
   - raw-to-mart latency tracking

## Recommended Go-Live Definition

I would call the pipeline “go-live ready” only when all of the following are true:

1. hourly AIS flow runs automatically for 48 hours without manual intervention
   via the hourly `ingest_batch` deployment
2. raw files appear in S3 every hour as expected
3. warehouse refresh succeeds on schedule
4. freshness checks stay green or alert correctly
5. Prefect shows stable scheduled run history
6. CloudWatch logs make failures explainable
7. dashboard export updates from real warehouse data

If any of those are missing, the system is still a pilot, not a production pipeline.

## Recommended Immediate Next Actions

Without changing code yet, the next best actions are:

1. choose Prefect Cloud versus self-hosted Prefect
2. confirm the AIS hourly 5 to 7 minute policy as final
3. confirm that `ingest_batch` is the sole scheduled hourly ingestion deployment
4. choose the Fargate worker execution model
5. write the secrets and environment inventory
6. draft the ECS, IAM, and networking Terraform additions
7. define the production deployments and schedules
8. define the CloudWatch dashboard and alert list before launch

## Final Honest Take

Yes, this can be made live in a disciplined way.
But the honest version is:

- **pilot-grade live pipeline first**
- not “full production maritime intelligence platform”

That is still very credible.
In fact, it is more credible because the scope, cadence, and monitoring claims match what the system can actually support.
