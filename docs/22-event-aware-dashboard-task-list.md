# Event-Aware Dashboard Task List

_Last updated 2026-06-12._

This is the implementation backlog for moving from a port congestion dashboard
to an event-aware maritime disruption dashboard.

## Priority 1: Public Trust Surface

- [x] Create a public model card.
- [x] Create a public coverage page.
- [x] Add both pages to the documentation navigation.
- [x] Fix public docs that still describe ML prediction as only planned.
- [x] Fix validation wording so it matches the current random-split caveat.

## Priority 2: Event Data Foundation

- [x] Select first event source: GDELT DOC for news-derived event pressure.
- [x] Add active GDELT ingestion client and Lambda.
- [x] Store raw event records in S3 with source, timestamp, topic, severity,
  URL, and attribution metadata.
- [x] Add freshness and source-health checks for the GDELT feed.
- [x] Document redistribution and display constraints for the first event layer.
- [ ] Add a second source for macroeconomic or labor-specific validation.

## Priority 3: Event Attribution

- [ ] Geocode event locations to countries, ports, chokepoints, and maritime regions.
- [x] Build first-pass port/country exposure rules for the 10 pilot ports.
- [ ] Add lane/chokepoint references for route-level disruption signals.
- [x] Deduplicate repeated article rows within a run by stable event id.
- [x] Assign first-pass severity fields.

## Priority 4: Event Features

- [x] Create hourly event feature tables by port.
- [x] Add 6h and 24h event-count windows.
- [ ] Add event categories such as strike, conflict, sanction, weather disruption,
  policy change, tariff, accident, and infrastructure outage.
- [x] Add first-pass event intensity features using count and severity.
- [ ] Add source count, tone, proximity, and recency decay.
- [ ] Decide which event features enter the ML feature contract.

## Priority 5: Better Labels And Evaluation

- [ ] Keep `is_congested_24h` as the first target, but add event-aware analysis.
- [ ] Add chronological backtesting with per-port metrics.
- [ ] Track calibration, precision/recall by threshold, and false-alert rate.
- [ ] Compare AIS-only versus AIS plus event features.
- [ ] Add 72h or 7d horizon experiments only after enough labels exist.

## Priority 6: Dashboard Event Layer

- [ ] Add an event timeline per selected port.
- [ ] Add event markers to the global map.
- [ ] Add reason codes: vessel buildup, low speed, wave conditions, stale source,
  sparse coverage, and external event pressure.
- [ ] Link each event reason to its source where licensing permits.
- [ ] Show confidence and freshness for each event-derived warning.

## Priority 7: Automation And Public Artifacts

- [ ] Generate `coverage.json` hourly.
- [ ] Generate `model-card.json` or `metrics.json` after training.
- [ ] Publish event-source freshness in the dashboard data artifact.
- [ ] Add tests for feature-contract consistency and artifact shape.
- [ ] Add documentation checks so public claims stay aligned with code.
