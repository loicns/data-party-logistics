# Data Flow And Storage Contract

This page defines the storage and data contract for the serverless pilot.

## Raw Data Prefixes

The live system writes raw data under date-partitioned prefixes:

- `raw/source=ais/date=YYYY-MM-DD/`
- `raw/source=weather/date=YYYY-MM-DD/`
- `raw/source=noaa_tides/date=YYYY-MM-DD/`

Why this matters:

- Lambda writes stay simple
- Glue external tables can point at stable locations
- Athena queries can filter by `date`

## Curated And Export Prefixes

- Athena query results:
  - `athena-results/`
- dashboard artifact:
  - `exports/dashboard/demo-data.js`
- curated payload snapshot:
  - `curated/port_metrics/date=YYYY-MM-DD/latest.json`

## Glue And Athena Contract

### Database

- `dpl_pilot`

### Tables

- `raw_ais_positions`
  - includes `ship_name`, not `vessel_name`
- `raw_weather_observations`
- `raw_noaa_tides`

This column naming matters because the export Lambda queries Athena directly and must match the Glue schema exactly.

## Lambda Write Responsibilities

### AIS snapshot

Writes:

- raw AIS NDJSON objects

Expected output signal:

- at least one file for a healthy run

### Weather

Writes:

- raw weather NDJSON objects

### NOAA

Writes:

- raw NOAA NDJSON objects

### Export

Writes:

- `demo-data.js`
- curated JSON snapshot

### Freshness

Writes:

- no data files
- only CloudWatch custom metrics

## Dashboard Contract

The dashboard expects:

- one browser-readable JavaScript file named `demo-data.js`
- a top-level `window.DEMO_DATA`
- port-level metrics
- source freshness information
- trend arrays
- optional vessel arrays

This is a static export contract, not a live API contract.

## Naming And Partition Assumptions

- date partitions use `YYYY-MM-DD`
- export artifact path is stable
- the pilot remains scoped to three ports
- Athena output stays under the same bucket unless the workgroup is deliberately changed

## Common Failure Modes

- raw data lands but Glue schema does not match query assumptions
- Athena reads old data because the expected prefix did not refresh
- export code expects a column alias that the raw table does not expose
- manual dashboard publication uses stale `demo-data.js`
