# 07 — Pilot Go-Live Checklist (salvaged from roadmap/)

_Salvaged 2026-06-09 from `roadmap/serverless-pilot/index.html` before that directory was removed._

## Per-service cost forecast (eu-west-3, serverless-only)

| Service | Forecast |
|---|---|
| EventBridge Scheduler | ~$0 |
| Lambda (AIS + weather + NOAA + export) | $0–4/month |
| S3 (raw, curated, export, Athena results) | $0–2/month |
| Athena (low-frequency SQL over raw NDJSON) | $0–4/month |
| CloudWatch + SNS (metrics, logs, alarms) | $1–4/month |
| **Total (serverless-only)** | **$5–15/month** |

**Cost-killing additions to avoid:**
- NAT Gateway: +$30–40/month (dominates the whole budget)
- RDS PostgreSQL: +$15–25/month (reintroduces always-on cost)

## Pre-go-live operator checklist

**AWS / IAM**
- [ ] Deploy role exists (GitHub OIDC, least-privilege, scoped to CF/Lambda/S3/Glue/Athena/CW/SNS)
- [ ] No NAT Gateway introduced anywhere
- [ ] Region locked to `eu-west-3`
- [ ] SNS topic policy allows email alerts

**GitHub secrets**
- [ ] `AWS_DEPLOY_ROLE_ARN` set
- [ ] `AISSTREAM_API_KEY` set
- [ ] `DPL_ALERT_EMAIL` set (optional)
- [ ] `.github/workflows/deploy-serverless.yml` reviewed

**Runtime validation**
- [ ] CloudFormation template validates; SAM stack deploys clean
- [ ] AIS Lambda duration stays in the 300–420 s window
- [ ] Athena export writes `exports/dashboard/demo-data.js` with acceptable scan cost
- [ ] CloudWatch dashboard panels populate after one full cycle

## Definition of done for pilot go-live

The pilot is live when:
1. Stack is deployed via GitHub Actions
2. One full hourly cycle succeeds end-to-end (AIS writes ≥ 1 file, weather lands, export refreshes)
3. CloudWatch dashboard shows real data and alarms can notify through SNS
4. Measured cost after a few days still fits inside the $5–15/month envelope
