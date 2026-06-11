# Athena Query Layer Guide

This guide explains how to validate the live query layer manually.

## Workgroup And Database

Use:

- workgroup: `dpl-serverless-pilot-pilot`
- database: `dpl_pilot`

Expected tables:

- `raw_ais_positions`
- `raw_weather_observations`
- `raw_noaa_tides`

## Query Result Location

For manual console queries, Athena needs a result location.

Recommended location:

- `s3://<pilot-bucket>/athena-results/`

If the console says no output location is configured:

- open the workgroup settings
- set the query result S3 location
- save

## First Validation Queries

```sql
SELECT * FROM raw_weather_observations LIMIT 10;
```

```sql
SELECT * FROM raw_ais_positions LIMIT 10;
```

```sql
SELECT * FROM raw_noaa_tides LIMIT 10;
```

## Recency Checks

```sql
SELECT date, mmsi, ship_name, received_at
FROM raw_ais_positions
ORDER BY received_at DESC
LIMIT 20;
```

```sql
SELECT date, port_code, timestamp
FROM raw_weather_observations
ORDER BY timestamp DESC
LIMIT 20;
```

## What Healthy Looks Like

- all three raw tables are queryable
- recent timestamps look believable
- row counts are greater than zero
- schema matches what the export Lambda expects

## Common Failure Modes

### `No output location provided`

Meaning:

- Athena console query results location is not configured

Fix:

- configure the workgroup result path

### `COLUMN_NOT_FOUND`

Meaning:

- SQL expects a column that Glue does not expose

Example already seen in this project:

- `vessel_name` was wrong
- `ship_name` is the real raw column

### Query succeeds but data looks stale

Meaning:

- ingestion may not be refreshing
- or the expected prefix was not updated recently

Operator next step:

- inspect S3 timestamps and Lambda logs
