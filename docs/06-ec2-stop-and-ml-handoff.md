# EC2 Shutdown And ML Handoff

This artifact explains how to stop the current EC2 ingestion setup safely after a week of data collection, while preserving the raw data for future machine learning training.

The main goals are:

- stop the EC2 spend cleanly
- keep the raw S3 data intact
- keep the system ready for later ECS Fargate migration
- preserve the exact dataset boundary for training and evaluation later

## How To Open The EC2 Shell

Use your local Mac terminal to SSH into the instance. You need:

- the private key file: `~/.ssh/dpl-ingestion-key.pem`
- the EC2 public IP address
- the username `ubuntu`

If you already know the public IP, connect with:

```bash
ssh -i ~/.ssh/dpl-ingestion-key.pem ubuntu@<YOUR_PUBLIC_IP>
```

If you need to look up the public IP from your local machine:

```bash
aws ec2 describe-instances \
  --filters "Name=instance-state-name,Values=running" "Name=key-name,Values=dpl-ingestion-key" \
  --query 'Reservations[0].Instances[0].PublicIpAddress' \
  --output text \
  --profile dpl \
  --region eu-west-3
```

Then SSH with the value it prints:

```bash
ssh -i ~/.ssh/dpl-ingestion-key.pem ubuntu@$(aws ec2 describe-instances \
  --filters "Name=instance-state-name,Values=running" "Name=key-name,Values=dpl-ingestion-key" \
  --query 'Reservations[0].Instances[0].PublicIpAddress' \
  --output text \
  --profile dpl \
  --region eu-west-3)
```

Once you are inside the EC2 shell, run the `systemctl` commands in the next section there, not on your laptop.

## What To Stop

You currently have three kinds of moving parts:

- one long-running AIS `systemd` service
- two scheduled daily batch timers for weather and NOAA tides
- the EC2 instance itself

Stopping the laptop does nothing. The job is running on EC2, so you must stop the EC2-side services first.

## What To Keep

Keep all raw data already written to S3.

Do not delete:

- `s3://dpl-raw-861276086413/raw/source=ais/...`
- `s3://dpl-raw-861276086413/raw/source=weather/...`
- `s3://dpl-raw-861276086413/raw/source=noaa_tides/...`

That raw zone is your future training source of truth.

## Step-By-Step Shutdown

### 1. Stop The AIS Stream

Run this inside the EC2 shell after you SSH in:

```bash
sudo systemctl stop dpl-ais-stream.service
sudo systemctl disable dpl-ais-stream.service
```

What this does:

- stops the continuous AIS process
- prevents it from restarting on boot

### 2. Stop The Batch Timers

On the EC2 instance:

```bash
sudo systemctl stop dpl-weather.timer
sudo systemctl disable dpl-weather.timer
sudo systemctl stop dpl-noaa-tides.timer
sudo systemctl disable dpl-noaa-tides.timer
```

What this does:

- prevents future daily weather runs
- prevents future daily NOAA tide runs

### 3. Confirm Nothing Is Still Running

```bash
systemctl list-units --type=service --state=running | grep dpl
systemctl list-timers --all | grep dpl
```

You want:

- no `dpl-ais-stream.service`
- no active `dpl-weather.timer`
- no active `dpl-noaa-tides.timer`

### 4. Save A Final Log Snapshot

This is useful if you later want to trace the exact last successful ingest time.

```bash
sudo journalctl -u dpl-ais-stream.service -n 200 --no-pager > /tmp/dpl-ais-final.log
sudo journalctl -u dpl-weather.service -n 200 --no-pager > /tmp/dpl-weather-final.log
sudo journalctl -u dpl-noaa-tides.service -n 200 --no-pager > /tmp/dpl-noaa-final.log
```

You can keep these logs locally on the EC2 box or copy them off-box if you want an audit trail.

### 5. Terminate The Instance

From your local machine:

```bash
INSTANCE_ID=$(aws ec2 describe-instances \
  --filters "Name=instance-state-name,Values=running" "Name=key-name,Values=dpl-ingestion-key" \
  --query 'Reservations[0].Instances[0].InstanceId' \
  --output text \
  --profile dpl \
  --region eu-west-3)

aws ec2 terminate-instances \
  --instance-ids "$INSTANCE_ID" \
  --profile dpl \
  --region eu-west-3
```

If you want to clean up the key pair and security group too:

```bash
aws ec2 delete-security-group --group-name dpl-ingestion-sg --profile dpl --region eu-west-3
aws ec2 delete-key-pair --key-name dpl-ingestion-key --profile dpl --region eu-west-3
rm -f ~/.ssh/dpl-ingestion-key.pem
```

## How To Preserve The Dataset For ML

The raw bucket is now a time-ordered source of truth. Treat it like a frozen dataset boundary.

Recommended next steps after shutdown:

1. record the first and last object dates for each source
2. note the exact EC2 shutdown time
3. keep the raw bucket untouched
4. use dbt or a loader to create a stable training extract later
5. split training and evaluation by time, not random rows

Why this matters:

- time-based splits prevent leakage
- the model should train on the past and evaluate on the future
- raw S3 is the reproducible input for later feature engineering

## Suggested ML Dataset Strategy

For future training, use a staged workflow:

1. raw S3 files
2. warehouse staging tables
3. mart tables with clean features
4. model training dataset snapshot

For time-sensitive shipping data, use a date cutoff:

- training period: older historical data
- validation period: later unseen period
- test period: the newest held-out slice

That is the safest way to evaluate whether your ETA and congestion models actually generalize.

## ECS Fargate Notes

When you later move ingestion to ECS Fargate, keep the same discipline:

- ECS should write to the same raw S3 layout
- the data contract should stay stable
- only the execution layer changes, not the dataset meaning

Think of it this way:

- EC2 was the first execution platform
- ECS Fargate is the next execution platform
- S3 raw data is the stable interface between them

## What To Add To The Week 4 Guide

If you update `guides/week-04/02-ingestion-flows.md`, do not change the main setup path. Add a small note at the end of the guide saying:

- after a week of collection, stop the EC2 service and preserve the S3 raw bucket
- the raw AIS/weather/NOAA data becomes the future training source
- keep the dataset boundary time-stamped for later model splits

Suggested note text:

```markdown
## Week-4 handoff note

If you are stopping the EC2 ingestion environment after gathering data, do not delete the raw S3 prefixes. Treat the raw bucket as the frozen input for later dbt, feature engineering, and model training. Record the shutdown date and use a time-based train/validation/test split when you build the ML dataset.
```

## Final Checklist

- AIS service stopped
- weather timer disabled
- NOAA timer disabled
- EC2 instance terminated
- raw S3 data preserved
- shutdown date recorded
- future training split strategy documented

That leaves you with a clean stop and a reusable dataset for the next phase.
