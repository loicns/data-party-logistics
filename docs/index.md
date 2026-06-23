# Data Party Logistics Documentation

Data Party Logistics is an end-to-end ML engineering pilot for short-term port
congestion intelligence. It ingests AIS vessel positions, weather, and NOAA tide
signals; stores raw data in S3; builds Athena feature tables; scores a LightGBM
model; and publishes a React dashboard for operators and reviewers.

## Current Capability Status

| Capability | Status | Description |
|---|---|---|
| Data ingestion | Built | AIS, weather, and NOAA Lambda ingestion jobs write partitioned raw data to S3. |
| Query layer | Built | Glue/Athena tables and CTAS queries define the pilot warehouse surface. |
| ML prediction | Built, early data | Training and prediction commands exist; model maturity improves as more data accumulates. |
| Dashboard | Built | React/Vite dashboard runs locally from fixtures and in production on Vercel, backed by CloudFront data artifacts. |
| Monitoring | Built for freshness | Freshness checks, CloudWatch metrics, and alarm semantics are documented. |
| Deployment | Built | SAM deploy path and cost-control pause/resume scripts are present. |
| Event-aware intelligence | Planned | Political, economic, labor, and news-event features are not in the current model. |
| Event feature tables | Built for analysis | GDELT event ingestion, attribution, and hourly feature tables exist; model retraining is pending. |

## Reviewer Reading Path

1. Start with the root `README.md` for the 60-second local run path.
2. Read [Secrets And Environments](operations/secrets-and-environments.md) to understand how
   the project runs without committed private keys.
3. Read [System Architecture Overview](architecture/system-overview.md) for
   the current runtime design.
4. Read [Data Flow And Storage Contract](architecture/data-flow.md)
   for table/file contracts.
5. Read [Monitoring And Alarm Semantics](operations/monitoring-and-alarms.md)
   for operational behavior.
6. Read the public [Model Card](ml/model-card.md), [Coverage](product/coverage.md), and
   [Data Dictionary](data/data-dictionary.md) for ML/dashboard semantics.
7. Read [Event Intelligence Layer](ml/event-intelligence.md) for GDELT ingestion,
   attribution rules, and event feature tables.

## Core Docs

- [Product PRD](product/prd.md)
- [Serverless Status And Cost Forecast](operations/serverless-status-and-costs.md)
- [Model Card](ml/model-card.md)
- [Coverage](product/coverage.md)
- [Event Intelligence Layer](ml/event-intelligence.md)
- [IAM And Deployment Identity](operations/iam-and-identity.md)
- [Athena Query Layer Guide](architecture/athena-query-layer.md)
- [Pipeline Explorer](data/pipeline-explorer.md)
- [Market Validation And Reach Plan](product/market-validation.md)

## Archive And Context

Older planning notes, audits, and implementation session reports remain in the
repository for traceability. They are secondary to the reviewer path above when
there is a status mismatch.
