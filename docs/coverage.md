# Coverage

_Public version. Last updated 2026-06-12._

Data Party Logistics currently covers 10 selected container ports. The product
is a near-port early-warning system, not satellite-grade global vessel tracking.

## Covered Ports

| Code | Port | Country/Region | AIS vessel context | Weather | Tides | Events | Terminal names | Known caveat |
|---|---|---|---|---|---|---|---|---|
| `NLRTM` | Rotterdam | Netherlands | Supported | Supported | Not covered by NOAA | GDELT rules | Listed | Strong current pilot signal |
| `SGSIN` | Singapore | Singapore | Supported | Supported | Not covered by NOAA | GDELT rules | Listed | Dense traffic can make attribution noisy |
| `USLAX` | Los Angeles | United States | Supported | Supported | NOAA-supported | GDELT rules | Listed | Anchorage geometry is being refined |
| `CNSHA` | Shanghai | China | Sparse | Supported | Not covered by NOAA | GDELT rules | Not listed | AISStream coverage is thin in Chinese waters |
| `DEHAM` | Hamburg | Germany | Supported | Supported | Not covered by NOAA | GDELT rules | Not listed | Terminal-level detail not yet modeled |
| `BEANR` | Antwerp | Belgium | Supported | Supported | Not covered by NOAA | GDELT rules | Not listed | Terminal-level detail not yet modeled |
| `GBFXT` | Felixstowe | United Kingdom | Supported | Supported | Not covered by NOAA | GDELT rules | Not listed | Terminal-level detail not yet modeled |
| `AEDXB` | Dubai | United Arab Emirates | Supported | Supported | Not covered by NOAA | GDELT rules | Not listed | Terminal-level detail not yet modeled |
| `USNYC` | New York | United States | Supported | Supported | NOAA-supported | GDELT rules | Not listed | Terminal-level detail not yet modeled |
| `TWKHH` | Kaohsiung | Taiwan | Supported | Supported | Not covered by NOAA | GDELT rules | Not listed | Terminal-level detail not yet modeled |

## What "Supported" Means

| Layer | Current meaning |
|---|---|
| AIS vessel context | Latest vessel positions seen within 200 nautical miles of a selected port, source permitting |
| Weather | Marine weather from Open-Meteo for the selected port |
| Tides | NOAA tide predictions for supported US stations only |
| Events | GDELT article metadata matched to ports through conservative port/country maritime rules |
| Model forecast | A LightGBM port-level congestion probability when a recent feature row exists |
| Terminal names | Static terminal names for a few verified ports; no vessel-to-terminal assignment |

## What Is Not Covered Yet

- Continuous offshore or ocean-wide tracking.
- Guaranteed vessel-specific ETA accuracy.
- Authoritative berth assignment.
- Verified port closure, labor action, customs slowdown, sanction, conflict,
  tariff, or election-event prediction. The new event layer captures article
  pressure, not confirmed operational impact.
- Public confidence intervals or calibrated uncertainty bands.
- Automated per-port coverage quality scores.

## Coverage Rules For The Dashboard

- If a port has no recent feature row, show the model forecast as unavailable.
- If a source is stale, show the stale state instead of hiding it.
- If AIS coverage is sparse, mark the affected port as coverage-limited.
- If a value is heuristic, label it as estimated.
- Do not imply global maritime visibility from a near-port AIS feed.

## Next Coverage Improvements

- Publish a generated `coverage.json` beside `demo-data.js` and
  `predictions.json`.
- Track per-port AIS message counts, latest observation age, and prediction
  availability.
- Add per-source freshness to the public coverage page automatically.
- Evaluate a satellite AIS supplement for sparse regions.
- Add richer event-source coverage once geocoding, source diversity, and
  route/chokepoint attribution are active.
