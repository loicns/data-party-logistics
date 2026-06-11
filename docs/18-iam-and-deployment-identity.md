# IAM And Deployment Identity

This page documents how deployment identity works for the serverless pilot and why the IAM policy took iterative refinement.

## Deployment Identity Model

The intended deploy path is:

- GitHub Actions
- GitHub OIDC
- AWS IAM role assumption
- SAM deploy into `eu-west-3`

This avoids:

- long-lived AWS keys in GitHub
- local-machine-only deployment

## Core Pieces

### GitHub secret

- `AWS_DEPLOY_ROLE_ARN`

### Trust model

- GitHub OIDC provider
- trust relationship restricted to the repo and branch

### Deploy workflow

- `.github/workflows/deploy-serverless.yml`

## Why The Policy Needed Iterative Widening

The role was intentionally kept tight, so real deployment exposed missing permissions step by step.

Notable permission gaps that had to be learned from real failures included:

- CloudFormation access to the SAM transform ARN
- CloudFormation access to the `aws-sam-cli-managed-default` helper stack
- S3 bootstrap bucket permissions for:
  - encryption configuration
  - public access block
- IAM readback of generated role inline policies
- Glue delete scope during rollback

This is expected when using a narrowly scoped deploy role with SAM rather than broad admin access.

## What The Deploy Role Must Cover

At a minimum:

- CloudFormation stack lifecycle
- SAM helper stack lifecycle
- S3 deployment/bootstrap bucket management
- Lambda create/update/delete
- IAM role create/read/pass/delete for SAM-generated roles
- Glue database and table lifecycle
- Athena workgroup lifecycle
- SNS topic/subscription lifecycle
- CloudWatch dashboard and alarm lifecycle
- EventBridge Scheduler lifecycle

## Operational Advice

- when SAM fails, inspect CloudFormation first
- treat the first `CREATE_FAILED` or `DELETE_FAILED` event as the source of truth
- if a versioned bucket blocks stack deletion, empty object versions before retrying
- keep the policy honest and scoped, but expect one-time friction during initial bring-up
