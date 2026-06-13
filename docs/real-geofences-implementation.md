# Add Real Geofences

## What This Means

Right now, the system guesses whether a vessel is berthed or waiting at anchor by looking at two simple things:

- how close the vessel is to the port center
- whether the vessel is moving slowly or reporting a status like "moored" or "at anchor"

That is useful for a demo, but it is not accurate enough for real port operations.

A geofence is a drawn area on the map. Instead of saying "this vessel is within 10 nautical miles of the port, so maybe it is waiting," we draw the actual areas that matter:

- the real port boundary
- the real anchorage area where vessels wait
- the real terminal or berth areas where vessels load and unload
- the approach area where vessels are inbound but not yet waiting

Then we classify the vessel based on which area it is actually inside.

In simple words: stop guessing from a circle around the port center, and start checking whether the vessel is inside the real operational area.

## Why This Matters

The current logic can be wrong because ports are not perfect circles.

A vessel may be:

- slow but not waiting
- marked as "moored" in AIS but not actually at a berth
- near the port center but still outside the terminal
- at a known anchorage that is far from the port center
- berthed at a terminal even if its AIS status is stale or wrong

Real geofences make the prediction system more trustworthy because the model can learn from better vessel states.

## What To Build

Create a small reference dataset that stores map areas for each port.

Each area should have:

- `port_code`: the port, for example `USLAX`
- `zone_id`: a stable id, for example `uslax_anchor_1`
- `zone_name`: a human-readable name, for example `Los Angeles Anchorage`
- `zone_type`: one of `port`, `anchorage`, `terminal`, `berth`, or `approach`
- `geometry`: the drawn polygon coordinates
- `source`: where the shape came from
- `confidence`: how trusted the shape is

The geometry should use GeoJSON, which is a common plain-text format for map shapes.

## First Version

Do not try to map every berth perfectly on day one.

Start with:

1. Port boundary
2. Anchorage areas
3. Terminal areas

This is enough to improve the most important labels:

- `likely_waiting_at_anchor`
- `likely_berthed`
- `approaching`
- `near_port`
- `transit`

Exact berth-level assignment can come later.

## How Vessel Classification Should Work

For every vessel position:

1. Check if the vessel is inside a terminal or berth geofence.
2. If yes, mark it as `likely_berthed`.
3. If not, check if it is inside an anchorage geofence.
4. If yes, mark it as `likely_waiting_at_anchor`.
5. If not, check if it is inside the port boundary.
6. If yes, mark it as `near_port`.
7. If not, check if it is inside the approach area.
8. If yes, mark it as `approaching`.
9. Otherwise, mark it as `transit`.

This should replace the current "distance from port center" shortcut as the main method.

Distance can still be kept as a backup signal.

## Add A Time Rule

One vessel position is not enough.

A vessel may briefly pass through an anchorage or terminal area. That does not mean it is waiting or berthed.

Use a dwell-time rule:

- mark as `likely_waiting_at_anchor` only after the vessel stays in an anchorage area for at least 30 minutes
- mark as `likely_berthed` only after the vessel stays in a terminal or berth area for at least 20-30 minutes
- if the vessel leaves the area, end that state

In simple words: do not trust one dot on the map; trust a pattern over time.

## Keep Confidence Clear

Every classified vessel state should include a confidence level.

Example:

- `confirmed`: verified from a port-call or terminal source
- `high`: inside a real geofence and stayed there long enough
- `medium`: inside a real geofence but not long enough yet
- `low`: based only on speed, AIS status, or distance

This prevents the dashboard from presenting guesses as facts.

## How This Fits The Existing System

The current dashboard code can keep showing vessels as berthed, waiting, approaching, or in transit.

But the source of those labels should change.

Instead of calculating vessel state directly inside the export handler, create a new prepared table first:

`vessel_state_hourly`

That table should contain one row per vessel per hour:

- vessel id
- port code
- timestamp
- latitude and longitude
- matched geofence
- derived vessel state
- confidence
- dwell time in minutes

Then the dashboard and prediction model both read from this cleaner table.

## Suggested Rollout

Start small and prove it works for one port first.

Recommended first port: `USLAX`, because anchorage and terminal behavior is operationally important and easy to inspect visually.

Rollout steps:

1. Create geofence polygons for `USLAX`.
2. Store them as GeoJSON.
3. Add a job that checks vessel positions against those polygons.
4. Add dwell-time logic.
5. Produce `vessel_state_hourly`.
6. Update the dashboard to read the new vessel state.
7. Update model features to use better counts from `vessel_state_hourly`.
8. Compare old counts against new counts for a week.
9. Expand to the next port after the labels look sensible.

## What Better Model Features Look Like

After geofences are added, the model should use features like:

- number of vessels waiting in real anchorage areas
- average anchorage dwell time
- number of vessels newly arriving at anchorage
- number of vessels leaving anchorage
- number of vessels inside terminal areas
- number of inbound vessels in approach zones
- weather and wave conditions

These are more meaningful than "vessels within 10 nautical miles moving slowly."

## Best Data Sources

Good sources for geofences include:

- official port maps
- official anchorage charts
- port authority GIS files
- nautical chart data
- manually drawn polygons from verified maps
- commercial maritime datasets if budget allows

For the first version, manually drawn polygons are acceptable if the source is documented and the confidence is marked honestly.

## Important Rule

Do not claim exact berth assignment unless the data proves it.

It is fine to say:

`Vessel is likely berthed somewhere in the terminal area.`

It is risky to say:

`Vessel is at Berth 4.`

Berth-level accuracy usually requires terminal schedules, port-call events, or very precise verified geofences.

## Definition Of Done

This step is done when:

- each pilot port has at least port, anchorage, terminal, and approach geofences
- vessel positions can be matched to those geofences
- vessel state uses geofence plus dwell time
- every state has a confidence level
- the dashboard no longer relies mainly on distance from port center
- the model features use real anchorage and terminal counts
