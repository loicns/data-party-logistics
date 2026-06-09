# 01 — Product Requirements Document (PRD)

_Status: v1.1 shipped · v1.2 in planning · Last updated 2026-06-09_

## 1. Problem

Ports congest unpredictably. Vessels arrive, anchor, and wait — costing operators
fuel, demurrage, and schedule reliability. Today that risk is visible only *after*
it happens. There is no cheap, open signal that says "this port will be congested
tomorrow."

## 2. Product

**DPL predicts port congestion 24 hours ahead** for the world's busiest container
ports, using live vessel-tracking (AIS), weather, and tide data, and shows the
forecast on a public dashboard.

## 3. Users

| User | Need | What DPL gives them |
|---|---|---|
| Aspiring ML/data engineer (owner) | A portfolio-grade, production-shaped system | End-to-end pipeline + this blueprint |
| Recruiter / reviewer | Evidence of systems thinking, not scripts | Self-updating cloud pipeline, IaC, evaluation |
| Curious operator/analyst | A read on near-term port risk | 24h forecast + live vessel context |

## 4. Goals (what success means)

- **G1 — Self-updating:** the 24h forecast refreshes in the cloud, hourly, with no
  laptop involved.
- **G2 — Honest:** every number shown is real or clearly labelled as derived. No
  fabricated data anywhere.
- **G3 — Cheap:** idle cost ≈ $0; running cost dominated only by Athena scans, which
  we actively minimise.
- **G4 — Reproducible:** anyone can deploy the whole system from this repo with
  declared dependencies and `sam deploy`.
- **G5 — Open source:** MIT, no proprietary services beyond commodity AWS primitives.

## 5. Non-goals (explicitly out of scope)

- Real-time (sub-hour) streaming predictions — batch hourly is sufficient and cheaper.
- A live query API — predictions are published as a static file behind CDN.
- Per-terminal berth assignment — AIS cannot observe it; we never claim it.
- Heavy data infra (Spark/Kafka/EMR) — wrong scale, wrong cost.

## 6. Functional requirements

- **FR1** Ingest AIS, weather, and tide data for 10 ports on a schedule.
- **FR2** Transform raw data into hourly feature tables (the "gold" layer).
- **FR3** Train a binary classifier for `is_congested_24h` with a time-aware split.
- **FR4** Score all 10 ports hourly and publish `predictions.json`.
- **FR5** Render forecast + live vessel context on a public dashboard.
- **FR6** Forecast must use the **exact** feature columns the model trained on.

## 7. Non-functional requirements

- **NFR1 — Freshness:** dashboard forecast timestamp ≤ 2 hours old.
- **NFR2 — Cost:** running cost target < $10/month at current data volume.
- **NFR3 — Failure isolation:** one port failing must not break the batch.
- **NFR4 — No train/serve skew:** features defined once (`models/features.py`).
- **NFR5 — Lint/test clean:** `ruff` + `pytest` green before any merge.

## 8. The 10 ports

NLRTM (Rotterdam) · SGSIN (Singapore) · USLAX (Los Angeles) · CNSHA (Shanghai) ·
DEHAM (Hamburg) · BEANR (Antwerp) · GBFXT (Felixstowe) · AEDXB (Dubai) ·
USNYC (New York) · TWKHH (Kaohsiung).

Source of truth: `serverless/ports.py`. Adding a port = one edit there.

## 9. Honesty constraints (hard requirements)

- The v1 model trained on ~168 labelled rows (3 days). It is a **noisy estimate**,
  stated as such everywhere it appears.
- Vessel-to-berth mapping is **not tracked** and is never implied.
- "Vessels at anchor" is derived from AIS speed + distance, not authoritative.
