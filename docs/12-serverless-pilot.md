# Serverless Pilot

This repo now includes a near-zero-cost AWS-only pilot deployment path based on:

- AWS SAM
- Lambda
- EventBridge Scheduler
- S3
- Glue + Athena
- CloudWatch + SNS

## Files

- `template.yaml`: deployable serverless stack
- `serverless/handlers/`: Lambda entrypoints
- `.github/workflows/deploy-serverless.yml`: GitHub Actions deployment workflow
- `requirements.txt`: Lambda packaging dependencies for SAM

## What It Replaces

This pilot path is a deliberate runtime fork from the earlier:

- Prefect orchestration
- always-on Postgres querying
- Fargate worker idea

It keeps the product behavior, but changes the runtime model to be cheaper.

## What It Deploys

- hourly AIS snapshot Lambda
- hourly weather Lambda
- daily NOAA Lambda
- hourly dashboard export Lambda
- 30-minute freshness Lambda
- one S3 data bucket
- Glue catalog tables for raw AIS, weather, and NOAA data
- Athena workgroup
- CloudWatch dashboard
- CloudWatch alarms
- SNS topic for alerts

## Browser-First Deployment

The intended deploy path is:

1. create the `AWS_DEPLOY_ROLE_ARN`, `AISSTREAM_API_KEY`, and optional `DPL_ALERT_EMAIL` GitHub secrets
2. trigger the `Deploy Serverless Pilot` workflow from GitHub Actions
3. inspect the stack in the AWS Console
4. use CloudWatch Dashboard and the S3 outputs to verify the pilot

## Important Notes

- The export path is Athena-backed and reads raw JSON directly from S3.
- The dashboard artifact is written to:
  - `s3://<bucket>/exports/dashboard/demo-data.js`
- The pilot is intentionally scoped to:
  - Rotterdam
  - Singapore
  - Los Angeles
