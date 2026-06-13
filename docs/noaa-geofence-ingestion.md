# NOAA Geofence Ingestion

## What We Added

The first trusted geofence artifact is stored here:

`warehouse/reference/noaa_cp7_uslax_anchorages.geojson`

It contains Los Angeles/Long Beach anchorage polygons converted from NOAA U.S. Coast Pilot 7.

This file is intentionally conservative. It includes only anchorage areas where the PDF gives enough coordinate data to create a closed polygon safely.

## What Is Trustworthy Now

The current GeoJSON is usable for:

- checking whether a vessel is inside a real Los Angeles/Long Beach anchorage
- counting vessels waiting in official anchorage areas
- improving `vessels_at_anchor` model features
- replacing simple "slow and near the port" logic for USLAX anchorage detection

The current GeoJSON should not be used for:

- exact berth assignment
- terminal occupancy
- saying a vessel is at a specific terminal
- shoreline-dependent anchorages that were not fully converted

## Why Some Areas Are Excluded

Some NOAA descriptions say things like "shoreward of a line" or "along the shoreline."

Those are real legal boundaries, but they are not safe to convert from the PDF alone. We need a shoreline or harbor-boundary geometry layer to close those shapes correctly.

For Los Angeles/Long Beach, the excluded areas are recorded in the GeoJSON metadata:

- Anchorage N
- Anchorage P
- Anchorage Q

These can be added later after we include a trusted shoreline layer.

## How To Check A Vessel Position

Use the helper in:

`serverless/geofences.py`

Example:

```python
from serverless.geofences import best_geofence_match, load_feature_collection

features = load_feature_collection(
    "warehouse/reference/noaa_cp7_uslax_anchorages.geojson"
)

match = best_geofence_match(
    lat=33.731,
    lon=-118.218,
    features=features,
    port_code="USLAX",
    zone_type="anchorage",
)

if match:
    zone_id = match["properties"]["zone_id"]
    zone_name = match["properties"]["zone_name"]
```

If `match` is not empty, the vessel is inside a trusted anchorage polygon.

In plain English: pass in the vessel latitude and longitude, and the helper tells us which official anchorage area contains that point.

## How To Use This In The Pipeline

The cleanest next step is to create a prepared table called:

`vessel_state_hourly`

That table should be created before dashboard export and before model scoring.

For each vessel position, calculate:

- vessel id
- timestamp
- port code
- latitude and longitude
- matched geofence id
- matched geofence name
- derived state, for example `likely_waiting_at_anchor`
- confidence, for example `high`
- dwell time in minutes

Then:

- the dashboard reads vessel state from `vessel_state_hourly`
- the model features count vessels from `vessel_state_hourly`
- the old distance-based anchor count becomes a fallback only

## Simple State Rule

For the first version:

- if a vessel is inside an anchorage polygon, mark it `in_anchorage_area`
- if it stays there for at least 30 minutes, mark it `likely_waiting_at_anchor`
- if it is not inside a geofence, fall back to the old distance and speed logic with lower confidence

This avoids treating one accidental position point as a real waiting event.

## Other Ports With Similar NOAA Data

From the same Coast Pilot 7 PDF, similar anchorage coordinate data appears available for several U.S. West Coast ports and areas, including:

- San Diego Harbor, CA
- Mission Bay, CA
- Dana Point Harbor, CA
- Newport Bay Harbor, CA
- Los Angeles/Long Beach Harbors, CA
- Marina del Rey Harbor, CA
- Santa Barbara Harbor, CA
- San Luis Obispo Bay, CA
- Morro Bay Harbor, CA
- Monterey Harbor, CA
- San Francisco Bay, CA
- San Pablo Bay, CA
- Trinidad Bay, CA
- Anaheim Bay Harbor, CA
- Santa Catalina Island, CA

For this project’s current tracked port list, the direct Coast Pilot 7 match is:

- `USLAX` Los Angeles

Other current project ports need different sources:

- `USNYC` should use the relevant NOAA Coast Pilot for New York/New Jersey.
- Non-U.S. ports such as Rotterdam, Singapore, Shanghai, Hamburg, Antwerp, Felixstowe, Dubai, and Kaohsiung need port authority GIS, nautical chart data, or commercial maritime geofence data.

## Terminal Data

The Coast Pilot includes useful terminal and berth reference information, but mostly as tables and point locations, not full terminal polygons.

That means it can help us name terminals and sanity-check locations, but it is not enough by itself for trusted terminal geofences.

For terminal geofences, use:

- official port authority GIS files
- terminal operator maps
- manually drawn polygons reviewed against official maps
- commercial port facility datasets

Until then, terminal status should stay as:

`likely inside terminal area`

not:

`confirmed at exact berth`
