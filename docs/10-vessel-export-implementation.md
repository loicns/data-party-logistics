# Vessel Export Implementation

This artifact shows exactly how to implement the next dashboard step:

1. query real vessel rows from the warehouse
2. convert them into dashboard-ready records
3. regenerate the browser data export
4. make the `Vessels` and `Map` views real

It is written against the **actual database objects** in this project:

- `public_staging.stg_ais_positions`
- `public_marts.mart_port_congestion_daily`

## Why This Is The Right Next Step

Right now the dashboard has:

- real port-level metrics
- real trend and forecast inputs
- real source freshness

But it still has an empty operational core:

- `vessels: []`

That means the product can summarize a port, but it cannot answer the most operator-shaped question:

> Which vessels should I care about right now?

In a real ML or logistics product, this is normal. Teams often build the product in layers:

1. a stable data pipeline
2. a warehouse export or service payload
3. an operator-facing UI
4. baseline rules and heuristics
5. ML on top of those validated workflows

This step is layer 2 moving into layer 3.

## Files You Will Touch

### 1. Backend export script

Edit:

- [dashboard/export_demo_data.py](/Users/loicns/Projects/data-party-logistics/dashboard/export_demo_data.py)

Why:

- this is where the dashboard payload is assembled
- it already exports per-port metrics
- it is the correct place to add vessel rows

### 2. Generated browser data file

Regenerate:

- [dashboard/demo-data.js](/Users/loicns/Projects/data-party-logistics/dashboard/demo-data.js)

Why:

- the dashboard loads this static file directly
- once this file includes vessel rows, the `Map` and `Vessels` views become real

## Step 1. Add The SQL Query

Put this block near the top of [dashboard/export_demo_data.py](/Users/loicns/Projects/data-party-logistics/dashboard/export_demo_data.py), right after `TREND_SQL`.

```python
VESSELS_SQL = """
WITH latest_positions AS (
    SELECT
        mmsi,
        vessel_name,
        latitude,
        longitude,
        speed_knots,
        nav_status,
        observed_at,
        ROW_NUMBER() OVER (
            PARTITION BY mmsi
            ORDER BY observed_at DESC
        ) AS row_num
    FROM public_staging.stg_ais_positions
    WHERE latitude IS NOT NULL
      AND longitude IS NOT NULL
),
current_positions AS (
    SELECT
        mmsi,
        vessel_name,
        latitude,
        longitude,
        speed_knots,
        nav_status,
        observed_at
    FROM latest_positions
    WHERE row_num = 1
),
with_distance AS (
    SELECT
        mmsi,
        vessel_name,
        latitude,
        longitude,
        speed_knots,
        nav_status,
        observed_at,
        3440.065 * 2 * ASIN(
            SQRT(
                POWER(SIN(RADIANS(latitude - %(port_lat)s) / 2), 2)
                + COS(RADIANS(%(port_lat)s))
                * COS(RADIANS(latitude))
                * POWER(SIN(RADIANS(longitude - %(port_lon)s) / 2), 2)
            )
        ) AS distance_nm
    FROM current_positions
)
SELECT
    mmsi,
    vessel_name,
    latitude,
    longitude,
    speed_knots,
    nav_status,
    observed_at,
    distance_nm
FROM with_distance
WHERE distance_nm <= %(max_radius_nm)s
ORDER BY distance_nm ASC
LIMIT %(limit)s
"""
```

### What this block does

#### `latest_positions`

This takes the staging AIS table and ranks rows so we can keep only the most recent position per vessel.

Why:

- AIS produces many rows per vessel
- the dashboard needs a current operational picture, not full history

#### `current_positions`

This filters to one row per `mmsi`, keeping the latest known location.

Why:

- the vessel table should represent the latest state for each ship

#### `with_distance`

This computes nautical-mile distance from the selected port using a haversine-style formula directly in SQL.

Why:

- we need a real distance to sort and classify vessels
- we do not need PostGIS yet for this specific UI export

#### Final `SELECT`

This returns only vessels within the chosen radius, sorted closest-first.

Why:

- close vessels matter most operationally
- limiting rows keeps the payload small and the UI readable

## Step 2. Add Python Helpers

Put these helper functions below `pad()` in [dashboard/export_demo_data.py](/Users/loicns/Projects/data-party-logistics/dashboard/export_demo_data.py).

```python
def vessel_zone(distance_nm: float, speed_knots: float, nav_status: str | None) -> str:
    status = (nav_status or "").lower()
    if "moored" in status:
        return "berth"
    if "anchor" in status or speed_knots <= 1.0:
        return "anchor"
    if distance_nm <= 50:
        return "approaching"
    return "transit"


def format_eta(distance_nm: float, speed_knots: float, zone: str) -> str:
    if zone == "berth":
        return "Berthed"
    if zone == "anchor":
        return "Waiting"
    if speed_knots <= 1.0:
        return "Unknown"

    hours = distance_nm / speed_knots
    if hours > 72:
        return ">72h"

    whole_hours = int(hours)
    minutes = int(round((hours - whole_hours) * 60))
    if minutes == 60:
        whole_hours += 1
        minutes = 0
    return f"{whole_hours}h {minutes:02d}m"


def confidence_score(distance_nm: float, speed_knots: float, zone: str) -> int:
    if zone in {"berth", "anchor"}:
        return 99

    score = 92
    if distance_nm > 120:
        score -= 18
    elif distance_nm > 60:
        score -= 10

    if speed_knots < 4:
        score -= 18
    elif speed_knots < 8:
        score -= 8

    return max(45, min(99, score))
```

### What these helpers do

#### `vessel_zone(...)`

This converts raw AIS state into product-facing categories:

- `berth`
- `anchor`
- `approaching`
- `transit`

Why:

- dashboards need operator language, not raw `nav_status` strings alone
- the map colors and vessel table already expect these categories

#### `format_eta(...)`

This creates a simple fallback ETA from distance and speed.

Why:

- you do not yet have a trained ETA model
- a product can still be useful with a clear baseline ETA
- in real ML systems, baseline heuristics often ship before the model does

#### `confidence_score(...)`

This produces a simple heuristic confidence.

Why:

- users should see uncertainty
- even before ML, confidence can reflect data quality and distance-to-port
- real ML products often start with rule-based confidence before calibrated model confidence exists

## Step 3. Build The Vessel List

Put this function below the helper functions in [dashboard/export_demo_data.py](/Users/loicns/Projects/data-party-logistics/dashboard/export_demo_data.py).

```python
def build_vessels(
    conn: psycopg.Connection[RowDict],
    meta: dict[str, Any],
    max_radius_nm: int = 200,
    limit: int = 12,
) -> list[dict[str, Any]]:
    with conn.cursor() as cur:
        cur.execute(
            VESSELS_SQL,
            {
                "port_lat": meta["lat"],
                "port_lon": meta["lon"],
                "max_radius_nm": max_radius_nm,
                "limit": limit,
            },
        )
        rows = cast(list[RowDict], cur.fetchall())

    vessels: list[dict[str, Any]] = []
    for row in rows:
        distance_nm = round(float(row["distance_nm"] or 0.0), 1)
        speed_knots = round(float(row["speed_knots"] or 0.0), 1)
        zone = vessel_zone(distance_nm, speed_knots, cast(str | None, row["nav_status"]))
        vessels.append(
            {
                "name": row["vessel_name"] or f"MMSI {row['mmsi']}",
                "mmsi": str(row["mmsi"]),
                "lat": round(float(row["latitude"]), 4),
                "lon": round(float(row["longitude"]), 4),
                "sog": speed_knots,
                "zone": zone,
                "dist": distance_nm,
                "eta": format_eta(distance_nm, speed_knots, zone),
                "conf": confidence_score(distance_nm, speed_knots, zone),
            }
        )

    return vessels
```

### What this block does

This is the translation layer between warehouse rows and UI rows.

It turns database rows into the exact object shape your dashboard already expects:

- `name`
- `mmsi`
- `lat`
- `lon`
- `sog`
- `zone`
- `dist`
- `eta`
- `conf`

Why this matters in real projects:

- warehouse schemas are not UI schemas
- product teams almost always need a shaping layer between storage and presentation
- this is the same kind of transformation you would later move into a service or API serializer

## Step 4. Wire Vessels Into The Existing Port Payload

In `build_port_payload(...)`, replace this:

```python
        "vessels": [],
```

with this:

```python
        "vessels": build_vessels(conn, meta),
```

### Why

This is the point where vessel rows become part of the final dashboard payload.

Before:

- ports had metrics and trends only

After:

- each port also includes its live vessel list

## Step 5. Regenerate The Export

Run:

```bash
uv run python dashboard/export_demo_data.py
```

This will rewrite:

- [dashboard/demo-data.js](/Users/loicns/Projects/data-party-logistics/dashboard/demo-data.js)

### What should happen after this

- the `Vessels` tab should stop showing the empty-state for ports with nearby AIS rows
- the `Map` view should get real vessel markers
- the vessel count should reflect actual exported rows
- each row should show a simple operational zone, distance, speed, ETA, and confidence

## How This Matches A Real Machine Learning Project

This step is very realistic.

A real ML product is usually not:

- raw warehouse tables directly into UI
- or model training first, everything else later

It is usually:

1. **Raw ingestion**
   Data lands in storage or raw tables.

2. **Staging and marts**
   dbt or SQL models clean and aggregate the data.

3. **Feature shaping for the product**
   A service or export builds UI-facing payloads from those marts and staging tables.

4. **Rules-based operational value**
   The product becomes useful before ML is fully ready.

5. **ML replaces or improves heuristics**
   ETA, confidence, and ranking become learned outputs later.

That is exactly what this exporter is doing:

- `public_staging.stg_ais_positions` gives current vessel facts
- `public_marts.mart_port_congestion_daily` gives port-level operational state
- `dashboard/export_demo_data.py` shapes them into a product payload

In a mature production system, this code would likely move into:

- a FastAPI endpoint
- a scheduled materialization job
- or a dedicated backend service

But the pattern is the same.

## What This Still Does Not Solve

This is a strong next step, but it is still a baseline:

- ETA is heuristic, not model-based
- confidence is heuristic, not calibrated
- distance is computed from latest AIS point only
- there is no lane history or destination-aware ranking yet

That is okay. In fact, it is the honest and useful sequence.

## Optional Follow-Up After This

Once the vessel export works, the next best step is:

- add a `why_flagged` field per port

Examples:

- `Low congestion and no anchored buildup`
- `Anchored count rising with low in-zone speed`
- `Wave conditions may slow port operations`

That will make the `Overview` view feel much more like a real decision tool.
