# DPL — Cost Shutdown Guide

How to stop AWS costs when you're done collecting data. Pick the option that
matches how long you want to stay off.

All commands assume:
```bash
cd /Users/loicns/Projects/data-party-logistics
export AWS_PROFILE=dpl   # already the default in the scripts
```

The 5 things that cost recurring money in this stack:
- 5 scheduled Lambdas firing hourly/half-hourly (compute)
- The hourly **export** Lambda runs Athena queries (the main variable cost)
- 1 CloudWatch dashboard (~$3/month)
- S3 storage (pennies — grows slowly)

There is **no** always-on server, NAT gateway, or database, so there is no big
hidden cost. Pausing the Lambdas removes almost all of it.

---

## Option A — PAUSE (recommended)

**Keeps everything + all data. Stops ~95% of cost. Reversible in one command.**

Pins every Lambda to reserved concurrency = 0, so scheduled invocations are
throttled instantly (throttled invocations are free). No data is touched.

```bash
scripts/pause.sh
```

Resume whenever you want more data:
```bash
scripts/resume.sh
```

Residual cost after pausing: ~$3/month (the CloudWatch dashboard) + pennies of
S3 storage. Good enough for most budgets.

---

## Option B — PAUSE + drop the dashboard (near $0)

Do Option A, then delete the CloudWatch dashboard to remove the last ~$3/month:

```bash
scripts/pause.sh
aws cloudwatch delete-dashboards \
  --dashboard-names dpl-serverless-pilot-pilot \
  --region eu-west-3
```

The dashboard is recreated automatically next time you run `sam deploy`, so
this is safe and reversible. After this, recurring cost is effectively $0
(just S3 storage pennies).

---

## Option C — FULL TEARDOWN (deletes the data too)

Only if you want the project gone entirely. This DELETES your S3 data —
download anything you want to keep first.

```bash
# 1. Back up data you want to keep (optional)
aws s3 sync s3://dpl-serverless-pilot-861276086413-pilot-data/ ./backup/ --region eu-west-3

# 2. Empty the versioned buckets (CloudFormation can't delete non-empty buckets)
aws s3 rm s3://dpl-serverless-pilot-861276086413-pilot-data/ --recursive --region eu-west-3

# 3. Delete the stack
aws cloudformation delete-stack --stack-name dpl-serverless-pilot --region eu-west-3
aws cloudformation wait stack-delete-complete --stack-name dpl-serverless-pilot --region eu-west-3
```

Note: the data bucket has versioning enabled, so step 2 may need the versioned
delete (delete-markers + old versions) before the bucket will drop. If the
stack delete stalls on the bucket, empty all versions via the S3 console, then
re-run step 3.

---

## How to verify costs actually stopped

After pausing, confirm no Lambda has run recently:
```bash
aws logs tail /aws/lambda/dpl-serverless-pilot-ais-snapshot \
  --region eu-west-3 --since 2h --format short
```
You should see nothing new after the pause time.

Check your actual spend anytime in the AWS Billing console → Cost Explorer,
filtered to this region (eu-west-3).

---

## Quick reference

| Goal | Command |
|------|---------|
| Stop cost, keep data, resume later | `scripts/pause.sh` |
| Start collecting again | `scripts/resume.sh` |
| Remove last $3/mo too | Option B above |
| Delete everything | Option C above |
