# Secrets And Environments

This project is designed so reviewers can run the dashboard without private
credentials, while the live pipeline can still run from a properly configured
operator environment.

## Rule Of Thumb

Commit the shape of configuration, never the values.

- Commit `.env.example` with variable names, comments, and fake placeholders.
- Keep real local values in `.env`.
- Keep cloud deployment values in the secret store of the platform that uses
  them.
- Rotate any key immediately if it is accidentally committed or pasted into a
  public artifact.

## Local Demo Mode

The fastest reviewer path is the dashboard demo:

```bash
cd dashboard-v2
npm ci
npm run dev
```

This mode reads `dashboard-v2/public/demo-data.js`. It does not need AWS,
AISStream, Vercel, or any `.env` file.

## Local Live Mode

Use this when you want local commands to call AWS or third-party services:

```bash
cp .env.example .env
```

Then edit `.env` locally. Required live values are:

```text
AWS_REGION
AWS_PROFILE
S3_BUCKET_RAW
AISSTREAM_API_KEY
```

Model and feature commands may also use:

```text
ATHENA_DATABASE
ATHENA_OUTPUT_LOCATION
```

## CI/CD

Use repository or environment secrets for CI/CD:

- `AWS_DEPLOY_ROLE_ARN` for GitHub Actions OIDC deployment.
- `AISSTREAM_API_KEY` for SAM deploys.
- `DPL_ALERT_EMAIL` only if alert subscription should be created.

GitHub Actions should consume these through `${{ secrets.NAME }}`. Do not echo
secret values in logs.

## Vercel Dashboard

Use Vercel project environment variables for dashboard deployment:

```text
VITE_DATA_URL=https://your-cloudfront-domain/demo-data.js
```

The local dashboard intentionally works without `VITE_DATA_URL`; it falls back
to the committed fixture.

## AWS Runtime

Current SAM deploy passes `AISSTREAM_API_KEY` as a `NoEcho` CloudFormation
parameter. For a longer-lived production stack, move secrets to AWS Systems
Manager Parameter Store or AWS Secrets Manager and grant Lambdas read access to
only the parameters they need.

## Interview Demo Guidance

Before a technical interview:

1. Verify the no-secret dashboard path works from a fresh shell.
2. Keep `.env` present only on your machine.
3. If demonstrating live AWS, set credentials before the call and show commands,
   not secret values.
4. Keep `.env.example` open as the contract for what another operator would
   need to provide.
