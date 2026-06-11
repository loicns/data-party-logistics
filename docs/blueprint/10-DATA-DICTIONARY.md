# 10 — Data Dictionary & Provenance Contract

_What every field shown on the dashboard means, where it comes from, and how
much to trust it. This is PRD goal **G2 ("honest")** written down._

Provenance legend:
- **REAL** — directly observed (AIS / weather APIs)
- **DERIVED** — computed deterministically from real data; method stated
- **HEURISTIC** — a rough estimate; always labelled `est.` in the UI
- **MODEL** — output of the trained LightGBM classifier

## `demo-data.js` (published hourly by the export Lambda)

| Field | Provenance | Meaning |
|---|---|---|
| `metadata.generatedAt` | REAL | UTC time the export ran. Drives the staleness banner (SLA ≤ 2h). |
| `sources[]` | DERIVED | Per-source freshness from S3 object ages. |
| `ports.{code}.vessels[]` | REAL | Latest position per vessel seen in the last **6 h** within 200 nm. Capped at **250 per port** (`vesselsTotal` holds the full count); metrics are computed from the *full* set before capping. |
| `vessels[].zone` | DERIVED | From nav status + speed + distance: `berth` / `anchor` / `approaching` / `transit`. |
| `vessels[].eta` | HEURISTIC | distance ÷ speed. **Not** a model output — labelled `est.` everywhere. |
| `vessels[].conf` | HEURISTIC | Legacy field; no longer rendered as a confidence bar. |
| `metrics.tracked / waiting / berthed` | DERIVED | Counts over the full vessel set. |
| `metrics.congestionPct` | DERIVED | Anchored share of (anchored + berthed). |
| `metrics.maxWave` | REAL | Max wave height from marine weather. |
| `forecast` / `trend` | DERIVED (history!) | Trailing daily congestion values. **This is observed history, not a forecast** — the UI labels it "Congestion Trend — last 5 days". |
| `berthAllocations[]` | DERIVED (aggregate) | Real terminal names; occupancy = count of vessels in the berth zone. **Which** berth is occupied is not observable from AIS — card positions are illustrative and the UI says so. |
| `schedule[]` | DERIVED | Approaching/transit vessels sorted by distance, with HEURISTIC ETAs. |

## `predictions.json` (published hourly by the predict Lambda)

| Field | Provenance | Meaning |
|---|---|---|
| `generatedAt` | REAL | UTC scoring time. |
| `predictions.{code}.probability` | **MODEL** | LightGBM P(congested in 24 h). The only forward-looking number in the product. |
| `predictions.{code}.prediction` | **MODEL** | probability ≥ 0.5. |
| `predictions.{code}.as_of` | REAL | Timestamp of the feature row that was scored. |
| `predictions.{code} = null` | — | No recent feature row for that port (e.g. sparse AIS coverage). UI shows "—", never fabricates. |

## Where each appears

- **Dashboard / Traffic / Schedule tabs** → `demo-data.js`
- **Insights "24h Forecast" card & Predictive "Model 24h Forecast" card** → `predictions.json`

## Known coverage caveats

- **CNSHA (Shanghai):** aisstream.io terrestrial AIS coverage of Chinese waters
  is sparse (~56 messages / 2 days vs thousands for Rotterdam). The port now
  has its own bounding box, but expect thin vessel lists regardless. This is an
  upstream data-source limitation, not a pipeline bug.
