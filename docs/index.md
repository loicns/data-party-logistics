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
| Dashboard | Built | React/Vite dashboard runs locally from fixtures and in production from CloudFront artifacts. |
| Monitoring | Built for freshness | Freshness checks, CloudWatch metrics, and alarm semantics are documented. |
| Deployment | Built | SAM deploy path and cost-control pause/resume scripts are present. |
| Event-aware intelligence | Planned | Political, economic, labor, and news-event features are not in the current model. |
| Event feature tables | Built for analysis | GDELT event ingestion, attribution, and hourly feature tables exist; model retraining is pending. |

## Reviewer Reading Path

1. Start with the root `README.md` for the 60-second local run path.
2. Read [Secrets And Environments](secrets-and-environments.md) to understand how
   the project runs without committed private keys.
3. Read [System Architecture Overview](14-system-architecture-overview.md) for
   the current runtime design.
4. Read [Data Flow And Storage Contract](15-data-flow-and-storage-contract.md)
   for table/file contracts.
5. Read [Monitoring And Alarm Semantics](17-monitoring-and-alarm-semantics.md)
   for operational behavior.
6. Read the public [Model Card](model-card.md), [Coverage](coverage.md), and
   [Data Dictionary](blueprint/10-DATA-DICTIONARY.md) for ML/dashboard semantics.
7. Read [Event Intelligence Layer](event-intelligence.md) for GDELT ingestion,
   attribution rules, and event feature tables.

## Core Docs

- [Product PRD](07-product-prd.md)
- [Serverless Pilot](12-serverless-pilot.md)
- [Serverless Status And Cost Forecast](13-serverless-status-and-costs.md)
- [Model Card](model-card.md)
- [Coverage](coverage.md)
- [Event-Aware Dashboard Task List](22-event-aware-dashboard-task-list.md)
- [Event Intelligence Layer](event-intelligence.md)
- [IAM And Deployment Identity](18-iam-and-deployment-identity.md)
- [Athena Query Layer Guide](19-athena-query-layer-guide.md)
- [Pipeline Explorer](pipeline-explorer.md)
- [Market Validation And Reach Plan](21-market-validation-and-reach-plan.md)

## Archive And Context

Older planning notes, audits, and implementation session reports remain in the
repository for traceability. They are secondary to the reviewer path above when
there is a status mismatch.
