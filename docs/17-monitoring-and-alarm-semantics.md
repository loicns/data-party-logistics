# Monitoring And Alarm Semantics

This page explains what the current CloudWatch alarms mean and what operators should do when they fire.

## Current Alarm Set

- `dpl-serverless-pilot-export-freshness`
- `dpl-serverless-pilot-ais-freshness`
- `dpl-serverless-pilot-export-errors`
- `dpl-serverless-pilot-ais-zero-files`

## Alarm Meanings

### Export freshness

Condition:

- `ExportFreshnessMinutes > 120`

Meaning:

- the export artifact is older than expected

Operator action:

- inspect `dpl-serverless-pilot-export`
- verify Athena query success
- verify `demo-data.js` write time in S3

### AIS freshness

Condition:

- `AisFreshnessMinutes > 90`

Meaning:

- no recent AIS object landed

Operator action:

- inspect `dpl-serverless-pilot-ais-snapshot`
- verify recent invocation and write counts

### Export errors

Condition:

- Lambda `Errors > 0`

Meaning:

- the export Lambda raised an exception in the evaluation window

Operator action:

- inspect the latest export Lambda log stream
- check for Athena schema mismatches or missing raw inputs

### AIS zero files

Condition:

- `AisFilesWritten < 1`

Meaning:

- the AIS job ran but wrote no file

Operator action:

- confirm run duration
- confirm connection success
- confirm whether this was only a short smoke test or a real scheduled run

## How To Read `In alarm`

`In alarm` does not always mean the system is currently broken.

It can also mean:

- a recent manual smoke test failed earlier
- the evaluation window still contains older bad datapoints
- the latest successful run has not yet replaced the alarm window

So operators should always compare:

- latest Lambda success
- latest S3 artifact time
- current alarm state

## How To Read `OK`

`OK` means:

- the recent datapoints are within the configured threshold

It does **not** mean:

- the whole product is production-grade
- all user-facing semantics are correct

It only means the monitored metric is currently healthy.

## Alarm Hygiene Principles

The alarm set should stay small and actionable.

If an alarm fires frequently but never leads to action, it should be:

- re-thresholded
- rewritten
- or removed

The goal is operator clarity, not alarm volume.
