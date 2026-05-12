# Dashboard V2 Readiness Artifact

This artifact is a handoff for engineering. It describes the current state of `dashboard-v2`, what is already compatible with the live serverless data pipeline, and what still needs to be built before `dashboard-v2` can run on real operational data cleanly and automatically.

## Executive Summary

`dashboard-v2` is **partially wired for real data already**, but it is **not yet fully production-ready** as a live frontend for the current serverless export pipeline.

### Already true

- the app is a React + Vite frontend
- it loads `window.DEMO_DATA`
- it selects a real port from the exported payload
- some pages already read real values from the export:
  - operations dashboard
  - vessel traffic map
  - topbar search / port switch

### Not yet true

- most pages are still mock / static shells
- route-level UX is not yet aligned to the current export contract
- the app still assumes richer vessel fields than the current export provides
- there is no explicit runtime strategy for loading the live `demo-data.js` in deployed environments
- there is no clear status/error/fallback handling when the export is missing or stale

## Current Runtime Context

The active backend is the AWS serverless path:

- scheduled Lambda ingestion
- S3 raw landing
- Glue + Athena query layer
- export Lambda generates `demo-data.js`
- `demo-data.js` is published to the dashboard bucket automatically

That means `dashboard-v2` should be treated as an **export-driven static frontend**, not a live API client.

## Current Frontend Architecture

### Entry points

- `dashboard-v2/index.html`
- `dashboard-v2/src/main.jsx`
- `dashboard-v2/src/App.jsx`

### Data loading path

- `dashboard-v2/index.html` includes:
  - `<script src="/demo-data.js"></script>`
- `dashboard-v2/src/context/DataContext.jsx` reads:
  - `window.DEMO_DATA`
- `DataContext` exposes:
  - `data`
  - `ports`
  - `currentPortCode`
  - `setCurrentPortCode`
  - `port`
  - `metadata`
  - `labels`
  - `sources`

### Router structure

`dashboard-v2/src/App.jsx` defines these routes:

- `/` → `OperationsDashboard`
- `/map` → `VesselTrafficMap`
- `/schedule` → `ArrivalDepartureSchedule`
- `/berth` → `BerthSchedulingView`
- `/insights` → `CongestionInsights`
- `/predictive` → `PredictiveAnalysis`

## What Is Already Using Real Data

## 1. `DataContext`

File:
- `dashboard-v2/src/context/DataContext.jsx`

Status:
- **real-data compatible**

What it does:
- loads `window.DEMO_DATA`
- picks the first port in `rawData.ports`
- exposes current port-level data through context

Notes:
- simple and workable
- no fetch logic needed if `demo-data.js` is always present
- currently has only a basic loading state and console error for failure

## 2. `OperationsDashboard`

File:
- `dashboard-v2/src/pages/OperationsDashboard.jsx`

Status:
- **partially real**

Real parts:
- reads `port.metrics`
- reads `metadata.generatedAt`
- reads `port.vessels`
- plots real vessel markers on map
- shows real tracked vessel count
- shows real congestion/waiting/wave metrics

Not yet production-grade:
- metric styling and trend language are still generic
- map markers initialize only once and do not fully re-sync with port changes
- active traffic list is hard-limited to `port.vessels.slice(0, 10)`
- there is no selected-vessel state shared with the rest of the app
- no explicit handling for stale exports or empty vessel lists

## 3. `VesselTrafficMap`

File:
- `dashboard-v2/src/pages/VesselTrafficMap.jsx`

Status:
- **partially real**

Real parts:
- uses `port.vessels`
- filters by zone
- maps real vessel positions
- shows per-vessel detail rail from selected map point

Not yet production-grade:
- assumes vessel fields that the current export does not provide well:
  - `imo`
  - `type`
  - `destination`
  - `cog`
- those values are currently missing from the export contract
- zoom range buttons are visual only and not contract-driven
- there is no cluster or overlap management
- no handling for widened export counts beyond simple marker placement

## 4. `Topbar`

File:
- `dashboard-v2/src/components/Topbar.jsx`

Status:
- **partially real**

Real parts:
- uses `ports`
- switches `currentPortCode`
- filters current `port.vessels`
- displays source health pills

Not yet production-grade:
- search checks `v.imo`, but current export does not reliably provide `imo`
- result click behavior is not wired to route or selected vessel state
- nav icons are still shell-level and not clearly tied to route state

## What Is Still Mock / Static

## 1. `PredictiveAnalysis`

File:
- `dashboard-v2/src/pages/PredictiveAnalysis.jsx`

Status:
- **mostly mock**

Uses real data only for:
- `m.congestionPct`

Still static:
- prediction accuracy `91%`
- alerts text
- SVG forecast shapes
- berth demand chart
- risk narrative

To be real:
- this page must consume:
  - `port.forecast`
  - `port.trend`
  - `sources`
  - freshness metadata

## 2. `CongestionInsights`

File:
- `dashboard-v2/src/pages/CongestionInsights.jsx`

Status:
- **mock**

Current values are hard-coded:
- wait time
- vessels at anchorage
- 48h forecast bars
- berth utilization
- delayed vessels

To be real:
- must map all displayed values to current export fields or a future extended export

## 3. `ArrivalDepartureSchedule`

File:
- `dashboard-v2/src/pages/ArrivalDepartureSchedule.jsx`

Status:
- **mock**

Current rows are static example vessels and berths.

Important constraint:
- the current serverless export does **not** provide a true arrival/departure schedule table

To make this real, engineering must choose one of:

1. derive a lightweight ETA queue from exported vessels
2. extend export Lambda to publish a schedule-oriented payload
3. add a new backend/API/data product for port call schedules

## 4. `BerthSchedulingView`

File:
- `dashboard-v2/src/pages/BerthSchedulingView.jsx`

Status:
- **mock**

Current berth occupancy blocks are fully static.

Important constraint:
- the current export does **not** contain real berth allocation data

This page cannot become truly real without:
- new berth data ingestion
- or derived berth heuristics
- or manual/partner operational data

## Real Data Contract Available Today

Today `dashboard-v2` can safely rely on this export shape:

- `metadata.generatedAt`
- `metadata.mode`
- `labels.outlook`
- `labels.trend`
- `sources[]`
- `ports[PORT_CODE]`
  - `name`
  - `flag`
  - `code`
  - `lat`
  - `lon`
  - `metrics`
    - `congestionPct`
    - `waiting`
    - `avgSpeed`
    - `maxWave`
    - `tracked`
  - `forecast`
  - `trend`
  - `vessels[]`
    - `name`
    - `mmsi`
    - `lat`
    - `lon`
    - `sog`
    - `zone`
    - `dist`
    - `eta`
    - `conf`

## Real Data Contract Not Available Today

These fields/pages are not backed by the current export contract:

- `imo`
- `destination`
- `type`
- `cog`
- true berth allocations
- true arrivals/departures schedule board
- true prediction accuracy metrics
- true delay event objects

If `dashboard-v2` keeps referring to those, it will either:
- show blanks
- show fake defaults
- or silently degrade into a misleading UI

## What Needs To Be Built

## Phase 1. Make `dashboard-v2` honest and live with today’s export

This is the minimum build needed for real data.

### Required changes

1. Replace all hard-coded schedule / berth / analytics examples with:
   - real export-backed components
   - or clearly labeled “not available in current pilot” states

2. Refactor `PredictiveAnalysis` to read:
   - `port.forecast`
   - `port.trend`
   - `sources`
   - `metadata.generatedAt`

3. Refactor `CongestionInsights` to read:
   - `port.metrics`
   - `port.vessels`
   - source freshness

4. Remove assumptions about unsupported vessel fields:
   - `imo`
   - `destination`
   - `type`
   - `cog`
   unless backend export is extended first

5. Add robust empty/stale states:
   - missing `window.DEMO_DATA`
   - empty `port.vessels`
   - stale source freshness
   - export older than threshold

6. Update map logic so it re-renders cleanly when port changes

7. Add selected vessel state at app/context level if multiple routes should share it

### Outcome

After Phase 1, `dashboard-v2` becomes a truthful live frontend for the current pilot export.

## Phase 2. Add export extensions needed by the richer UI

If product wants the richer v2 experience, the backend export should be extended deliberately.

### Useful export additions

1. vessel optional metadata
   - `imo`
   - `cog`
   - maybe `destination`
   - maybe `ship_type`

2. richer port summaries
   - zone counts
   - closest vessels by type/zone
   - stale/coverage flags

3. export status manifest
   - last successful export
   - source freshness by feed
   - record counts
   - coverage note

4. possibly derived queue / arrivals panel
   - if schedule page should survive in pilot form

### Outcome

The UI can stay visually ambitious without relying on fake placeholders.

## Phase 3. Decide what is out of scope for the current pilot

Engineering should explicitly decide whether these routes remain:

- `/schedule`
- `/berth`

If the current pilot has no real berth/schedule backend, then:

- remove them for now
- relabel them as roadmap/demo-only
- or gate them behind mocked/demo mode

This is better than pretending they are operational.

## Recommended Migration Plan

## Recommendation

Treat `dashboard-v2` as a **live export consumer**, not a greenfield product shell.

### Step order

1. keep `demo-data.js` as the runtime contract
2. make `dashboard-v2` consume only fields that exist now
3. strip or downgrade pages that rely on non-existent data
4. add explicit stale/coverage/empty states
5. extend export Lambda only where the UX value justifies it

## Engineering Task Breakdown

## Track A. Runtime integration

- confirm deployed environment serves `demo-data.js` at the same path expected by `index.html`
- verify `window.DEMO_DATA` is present in production
- add loading/error state beyond `console.error`
- define cache/freshness behavior in browser

## Track B. Real-data conversion

- `OperationsDashboard`
  - keep
  - harden
- `VesselTrafficMap`
  - keep
  - harden
- `Topbar`
  - keep
  - make search result selection real
- `PredictiveAnalysis`
  - rebuild on export fields
- `CongestionInsights`
  - rebuild on export fields

## Track C. Scope correction

- `ArrivalDepartureSchedule`
  - either remove, label as roadmap, or back with a new export contract
- `BerthSchedulingView`
  - either remove, label as roadmap, or back with new berth data

## Track D. Backend extensions

- add optional vessel metadata only if used intentionally
- add manifest/status payload if UX needs it
- avoid adding fields with no stable source of truth

## Definition of Ready For Live Real Data

`dashboard-v2` is ready to replace the current dashboard only when:

1. it renders entirely from the real export contract
2. unsupported fields are removed or handled gracefully
3. all major routes are either:
   - real
   - intentionally disabled
   - or explicitly labeled as roadmap/demo-only
4. port switching re-renders map and panels correctly
5. stale and empty states are operator-safe
6. the deployed bucket path for `demo-data.js` is confirmed

## Recommended Acceptance Checklist

- [ ] `window.DEMO_DATA` load works in deployed environment
- [ ] Operations dashboard uses only real fields
- [ ] Vessel map uses only real fields
- [ ] Search does not depend on missing `imo`
- [ ] Predictive page uses real `forecast` and `trend`
- [ ] Insights page uses real `metrics`, `vessels`, and `sources`
- [ ] Schedule page is either real or removed from live nav
- [ ] Berth page is either real or removed from live nav
- [ ] Empty/stale/error states are visible and understandable
- [ ] Port switching updates all route views safely

## Final Recommendation To Engineering

Do **not** treat `dashboard-v2` as “already done except for wiring.”

The right framing is:

- **the shell and design system are promising**
- **the data context pattern is usable**
- **two pages are already partly real**
- **several routes are still mock product theater**

The clean migration path is:

1. stabilize the real-data routes first
2. remove or downgrade the mock routes
3. extend the export contract only where it clearly supports product value

That approach gets `dashboard-v2` to a trustworthy live state faster than trying to make every current screen real at once.
