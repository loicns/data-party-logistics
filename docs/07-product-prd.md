# Product Requirements Document

## 1. Document Information

- **Product:** Data Party Logistics
- **Document Type:** Product Requirements Document
- **Status:** Draft
- **Last Updated:** 2026-05-08
- **Stakeholders:** Product, ML engineering, data engineering, UX/design, design-partner users in logistics operations
- **Target Release Date:** V1 candidate 8-12 weeks after discovery sign-off

## 2. Executive Summary & Objectives

### Product Decision Up Front

This project should **not** be treated as a new end-to-end replacement for project44, FourKites, Shippeo, Oracle Transportation Management, or similar platforms.

The more realistic and defensible V1 is:

> **A port-centric early-warning tool for teams that do not already have strong ocean visibility software, and who currently rely on carrier portals, spreadsheets, and manual tracking.**

If user discovery shows that the target users already have a performant internal visibility stack or an enterprise control tower, this product should be narrowed further or not built as a standalone product at all.

### Problem Statement

Smaller import/export teams, freight forwarders, and analysts often need earlier warning that a vessel or port is at risk of delay, but they do not always have access to enterprise-grade ocean visibility platforms. They end up checking multiple carrier sites, AIS maps, and spreadsheets to understand what is happening.

### Goal

Deliver a narrow, useful ML-assisted workflow that helps users:

- spot elevated port congestion risk
- identify inbound vessels likely to arrive late versus schedule
- understand confidence, freshness, and fallback behavior clearly

### Non-Goal

V1 is **not** a multimodal transportation management system, a booking platform, or a full supply-chain control tower.

### Target Audience

- Small and mid-market freight forwarders without premium visibility tooling
- Importers/exporters that track a limited set of lanes or ports manually
- Analysts and researchers who want transparent, reproducible port signals from public data

## 3. User Stories & Functional Requirements

### User Stories

- As a logistics coordinator, I want to see which watched vessels or ports are most at risk so that I can prioritize follow-up work.
- As a supply-chain analyst, I want a daily congestion score and trend for selected ports so that I can spot deterioration before it becomes operationally painful.
- As an operations manager, I want to know when the system is uncertain or missing data so that I do not trust a weak prediction blindly.
- As a user, I want a clear fallback when no model prediction is available so that the product remains useful even with incomplete data.

### Functional Requirements

- **FR1:** Users must be able to define a watchlist of ports and, when available, a watchlist of vessels or vessel identifiers.
- **FR2:** The system must provide a daily congestion risk score for each tracked port in scope.
- **FR3:** The system must provide a delay-risk or ETA-risk view for watched inbound vessels when enough data is available.
- **FR4:** Each prediction must show freshness, confidence, and the core inputs used to generate it.
- **FR5:** If the model cannot produce a prediction, the product must fall back to a rules-based view such as latest position, speed, destination, and recent port congestion trend.
- **FR6:** Users must be able to mark a prediction as useful, not useful, or incorrect.
- **FR7:** Users must be able to inspect why a port or vessel is flagged, using simple reason codes such as anchorage buildup, low vessel speeds near port, severe waves, stale data, or destination ambiguity.
- **FR8:** The system must make the supported scope explicit, including covered ports, data freshness expectations, and coverage gaps offshore.

## 4. Success Metrics (KPIs)

### Product Validation Metrics

- At least 5 target users interviewed before build commitment
- At least 3 design partners confirm they do **not** already have a sufficient internal or vendor system for this use case
- At least 2 design partners use the product weekly during pilot

### Primary Metric

- Reduction in manual tracking time for design-partner users by at least 30% on watched shipments or ports

### Secondary Metrics

- Data freshness SLA met for 95% of scheduled runs
- Users open flagged alerts at least 50% of the time
- Fewer than 10% of surfaced alerts are judged clearly non-actionable by pilot users

### ML Performance Targets

- ETA-risk model improves over a naive speed-and-distance baseline by at least 15% on held-out data
- Congestion model beats persistence baseline by at least 10 percentage points on the chosen classification metric
- Confidence calibration is good enough that low-confidence predictions can be filtered without collapsing coverage

## 5. User Experience (UX) & Interface

### Placement

The ML output should live in a simple operational dashboard with:

- a watched ports view
- a watched vessels view
- a “why this is flagged” explanation area
- a visible freshness and confidence panel

### Feedback Loop

Capture lightweight user feedback:

- useful
- not useful
- incorrect
- manually resolved

This feedback should be stored for later evaluation, even if it is not used in the first model training loop.

### Transparency / Explainability

The product must explain:

- whether a result is a model prediction or a fallback
- when the underlying data was last updated
- what major signals influenced the result
- what the user should be cautious about

## 6. Constraints & Assumptions

### Technical Constraints

- Public and low-cost data sources only for V1
- Initial scope limited to a small number of ports with acceptable data quality
- No assumption of direct carrier, terminal, or EDI integrations in V1

### Data Availability Assumptions

- We can collect enough historical AIS-adjacent and weather data to evaluate whether the signal is predictive
- Public data is strong enough for near-port visibility, but not for complete ocean-wide coverage

### Privacy, Ethics, and Reliability

- No personal data is central to V1
- The system must not imply certainty where the source data is incomplete
- The product must not market itself as “real-time global visibility” if the actual coverage is near-coast and source-dependent

## 7. Out of Scope

- Full global end-to-end shipment visibility
- Carrier booking or order management
- Multimodal orchestration across truck, rail, and air
- Automated customer messaging
- Direct replacement of enterprise TMS or control-tower platforms
- LLM-generated disruption narratives as a launch-critical dependency

## 8. Milestones & Roadmap

### Phase 0: Discovery Gate

- Interview target users
- Validate current workflows
- Confirm whether the pain is unsolved for the intended segment
- Decide go / no-go on standalone product positioning

### Phase 1: Reliable Data Foundation

- Stabilize ingestion and warehouse flows
- Define exact in-scope ports and freshness expectations
- Produce a truthful source coverage matrix

### Phase 2: Baseline Product

- Launch dashboard backed by real data, not mock data
- Ship congestion scoring and non-ML fallback views
- Add freshness, confidence, and explanation panels

### Phase 3: ML Pilot

- Train and evaluate first ETA-risk and congestion models
- Compare against rules-based baselines
- Pilot with design partners

### Phase 4: Go / Pivot Decision

- Expand if users get real operational value
- Narrow or reposition if the product is only interesting as a technical demo

## 9. ML-Specific Failure Handling

- If no model prediction is available, show the fallback view and label it clearly.
- If source freshness is outside tolerance, suppress predictions or mark them degraded.
- If prediction confidence is below threshold, prefer “unknown” over a confident-looking weak answer.
- If public AIS coverage is insufficient offshore, say so explicitly instead of implying continuous tracking.

## 10. Go / No-Go Criteria

Proceed only if all of the following are true:

- discovery confirms a real user segment without adequate existing tooling
- baseline product can outperform manual tracking on speed or clarity
- public-data coverage is good enough for the selected use case
- the team is willing to position this as a focused visibility layer, not an enterprise control tower clone

If those criteria are not met, the better outcome is to reposition the project as:

- an open port-intelligence research platform
- a portfolio-grade ML engineering project
- a niche analytics tool for selected ports and lanes

## References

- [project44 Ocean Visibility](https://www.project44.com/platform/visibility/ocean/)
- [Shippeo Ocean](https://www.shippeo.com/platform/multimodal-network/ocean-sea-barge-roro)
- [Oracle Transportation Management](https://www.oracle.com/scm/logistics/transportation-management/)
- [AIS Stream Coverage](https://aisstream.io/coverage)
- [AIS Stream Documentation](https://aisstream.io/documentation)
