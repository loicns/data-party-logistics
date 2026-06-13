# Mid-Term Port Prediction Plan

_Last updated 2026-06-13._

This plan extends Data Party Logistics from the current 24-hour congestion
classifier into a 7-day and 14-day selected-port prediction workflow using only
real source data. No mock, synthetic, or assumed records are allowed in
training, validation, published predictions, or dashboard explanations.

## Outcome

Build a mid-term prediction card for the selected dashboard port that shows:

- `P(congested in 7 days)`
- `P(congested in 14 days)`
- the model version, data snapshot time, and source freshness
- the live and historical data sources used
- the top local factors that moved the prediction
- a plain-language explanation of how the 7-day and 14-day prediction was
  calculated

The card should fail closed: if any required real-data input or model artifact
is missing, it shows an unavailable state instead of substituting demo,
estimated, or mock values.

## Current Repo Fit

The current live architecture already has the right shape:

- Lambda ingestion writes raw source data to S3.
- Glue and Athena expose raw and curated tables.
- Athena CTAS queries build feature tables.
- LightGBM trains and serves a model from a shared feature contract.
- `predictions.json` is published beside the dashboard artifact.
- `dashboard-v2/src/pages/PredictiveAnalysis.jsx` already reads predictions for
  the selected `currentPortCode`.

The current model is only a 24-hour classifier. GDELT event ingestion and event
feature tables exist, but the deployed model does not consume them yet. UN
Comtrade and FRED are named in older warehouse docs, but they are not wired into
the active serverless path.

## Source Research

### UN Comtrade

Official source pages:

- [UN Comtrade subscription plans](https://uncomtrade.org/docs/subscriptions/)
- [How to access UN Comtrade data](https://uncomtrade.org/docs/how-to-access/)
- [API subscription keys](https://uncomtrade.org/docs/api-subscription-keys/)
- [UN Comtrade API guide](https://uncomtrade.org/docs/un-comtrade-api/)
- [UN shop Comtrade pricing](https://shop.un.org/databases#Comtrade)

Relevant access facts:

- Free registered accounts can use the basic data API with an API key.
- The free registered tier advertises up to 500 calls/day and 100K records per
  API call.
- Premium API/batch/bulk access is intended for larger workloads.
- The UN shop lists annual Comtrade subscription prices:
  - Premium Individual: USD 2,000/year
  - Premium Institutional Pro 1: USD 6,000/year
  - Premium Institutional Pro 2: USD 12,000/year
- Public/anonymous access exists, but the official help center says rate limits
  are applied more strictly for anonymous access.
- Bulk-file download is premium-only.

How it should be used here:

- Start on the free registered API tier.
- Pull only the country and commodity slices needed for the selected pilot
  ports.
- Cache raw responses by query, reporter, partner, flow, period, and
  classification.
- Use Comtrade as a monthly/structural demand signal, not as a live event feed.

Important limitation:

- Comtrade is not a port-operations feed and does not directly report berth
  queues, anchorages, or live port congestion. It can help explain medium-term
  demand pressure, seasonality, and trade-flow context, but it should not be
  treated as a direct 7-day operational signal without backtest evidence.

### GDELT

Official source pages:

- [The GDELT Project](https://www.gdeltproject.org/)
- [GDELT DOC 2.0 API announcement](https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/)

Relevant access facts:

- GDELT describes the database as free and open.
- The project monitors global news in near real time and updates every 15
  minutes.
- The current repo already ingests GDELT DOC article lists for maritime event
  pressure.

How it should be used here:

- Keep the existing hourly GDELT Lambda.
- Add a bounded historical backfill only for pilot-port maritime queries.
- Keep deterministic attribution rules and audit rows; do not display event
  severity as a verified disruption score.
- Add 7-day and 14-day rolling event-pressure features:
  - event count by category
  - severe-event count
  - average severity
  - recency of latest event
  - source-country and port-term match counts

Important limitation:

- GDELT DOC article metadata is not a structured incident feed. It is useful as
  event pressure, but every model and dashboard explanation must say it is
  news-derived, not confirmed port status.

### FRED

Official source pages:

- [FRED API documentation](https://fred.stlouisfed.org/docs/api/fred/)
- [FRED API keys](https://fred.stlouisfed.org/docs/api/api_key.html)
- [FRED API terms of use](https://fred.stlouisfed.org/docs/api/terms_of_use.html)

Relevant access facts:

- API requests require an API key.
- The key is issued through a logged-in FRED user account.
- The public terms say FRED may impose or adjust bandwidth and transaction
  limits.
- The official docs reviewed here do not publish a stable numeric rate limit.

How it should be used here:

- Use a small allowlist of macro series after validating each series ID via the
  FRED API.
- Cache all raw observations by `series_id` and observation date.
- Refresh daily for daily series and monthly for monthly series.
- Keep release-date awareness so the model never sees data that was not
  available at prediction time.

Candidate series to validate before implementation:

- global supply-chain pressure or similar shipping-relevant stress series
- oil or bunker-cost proxy series
- trade-weighted USD or FX stress series
- industrial production or trade-volume proxy series for major markets

No series enters the model until its ID, license notes, release lag, frequency,
and update cadence are recorded in the source registry.

## Cost Plan

### Data Provider Costs

| Source | Direct data cost | Required account/key | When paid access is needed |
|---|---:|---|---|
| GDELT DOC | USD 0 | No | Not expected for pilot |
| FRED | USD 0 direct API fee found in official docs | Yes, API key | Not expected for pilot |
| UN Comtrade basic | USD 0 | Yes, free API subscription key | Not expected for targeted pilot |
| UN Comtrade Premium Individual | USD 2,000/year | Yes | Only if free limits block required volume |
| UN Comtrade Premium Institutional Pro 1 | USD 6,000/year | Yes | Only for institution-wide/nonprofit-academic access |
| UN Comtrade Premium Institutional Pro 2 | USD 12,000/year | Yes | Only for private-sector institution-wide access |

Decision: do not buy Comtrade premium for v1. Use the free registered tier and
prove whether the limited selected-port query set actually needs more.

### AWS Incremental Costs

The existing pilot cost forecast is USD 5-15/month when kept serverless,
low-scan, and without NAT/RDS/Fargate. This work should add only small scheduled
jobs and curated Parquet tables.

| Increment | Expected monthly cost | Notes |
|---|---:|---|
| FRED daily Lambda | USD 0-1 | Few requests, tiny payloads |
| Comtrade monthly or weekly Lambda | USD 0-1 | Bounded query list; cache responses |
| GDELT backfill/expanded feature windows | USD 0-2 | Depends on backfill size and Athena scans |
| S3 raw + curated storage | USD 0-1 | Small NDJSON/Parquet payloads |
| Athena CTAS/features | USD 0-3 | Keep Parquet and partition filters |
| CloudWatch logs/alarms | USD 0-2 | Control log verbosity |

Expected incremental runtime cost: USD 1-5/month.

Safe planning budget with the existing pilot: USD 6-20/month.

Cost traps to avoid:

- no NAT gateway
- no always-on database
- no always-on Fargate worker
- no full-history Comtrade scans every run
- no unbounded GDELT API loops
- no dashboard query engine in the browser
- no Athena queries over raw JSON when a curated Parquet table can be reused

## Modeling Design

### Target

Create two direct horizon classifiers:

- `is_congested_7d`
- `is_congested_14d`

For each `port_code` and `observation_hour`, label whether the port becomes
congested at the future horizon. The target should stay aligned with the
current model-card definition unless changed deliberately:

```text
is_congested_horizon = 1 when vessels_at_anchor at observation_hour + horizon
exceeds the port's trailing 90-day 75th percentile and is greater than 2.
```

If the product goal is delay minutes instead of congestion risk, create a
separate regression target. Do not mix binary congestion and expected delay in
one model output.

### Feature Groups

Use only features known at the prediction timestamp:

| Group | Examples | Source |
|---|---|---|
| Live port state | vessels within 10/50/200 nm, anchored vessels, average speed | AIS |
| Marine conditions | wave height, wave period, wind/swell components, tide where available | Open-Meteo/NOAA |
| Port seasonality | hour, day, week, month, holiday/release calendar flags | derived |
| Event pressure | 24h/7d/14d GDELT event counts, severe events, labor/security/policy/infrastructure mix | GDELT |
| Trade flow context | monthly import/export value and weight deltas for port-country market proxies | UN Comtrade |
| Macro context | validated macro stress, energy, FX, demand series | FRED |

No feature can be backfilled from a later publication date. Every macro or
trade feature needs an `available_at` timestamp or a conservative publication
lag rule documented in the data contract.

### Evaluation

Required before dashboard release:

- chronological split, not random split
- per-port metrics
- AIS/weather baseline versus enriched model comparison
- 7-day and 14-day metrics separately
- calibration curve or Brier score
- precision/recall at operator-friendly thresholds
- missing-source ablation so the card can explain degraded confidence

Minimum release gate:

- enriched model must beat AIS/weather baseline on time-based validation for at
  least one selected-port horizon, or the dashboard must label the enrichment
  as experimental and keep the baseline model active.

### Explainability

Use LightGBM contribution output at inference time instead of a heavy extra
explainability service:

```text
model.predict(X, pred_contrib=True)
```

Publish top positive and negative feature contributions in
`predictions.json`. The dashboard card should translate feature names into
operator language, for example:

- "More vessels already within 50 nm increased risk."
- "No recent labor/security event pressure reduced risk."
- "Macro/trade features were unavailable or stale and were excluded."

Do not claim causal explanation. The copy should say these are model
contributions for the current prediction.

## Frontend Prediction Card

Add a selected-port card to `PredictiveAnalysis.jsx` or a dedicated component:

```text
Mid-Term Forecast
Selected port: NLRTM - Rotterdam
As of: 2026-06-13T10:00:00Z

7-day risk: 42% Elevated
14-day risk: 58% Elevated

How this was calculated
The model scored the latest real feature row for this port, then applied two
separately trained LightGBM horizon models. Each model was trained only on
historical feature rows and future congestion labels for that horizon. The
current prediction used live AIS/weather features, recent GDELT event pressure,
and the latest available Comtrade/FRED context that was published before the
feature timestamp.

Top factors
1. Vessels within 50 nm increased risk
2. Average speed near the port decreased risk
3. Recent event pressure increased risk
```

Required states:

- `ready`: both 7d and 14d predictions available
- `partial`: one horizon or noncritical source missing
- `stale`: prediction exists but source freshness exceeds threshold
- `unavailable`: no real prediction for selected port

The card must not render a fallback heuristic as if it were the model.

## Executable Delivery Plan

### Phase 0 - Source And Product Gates

Deliverables:

- source registry with provider URL, auth type, license notes, rate limits,
  refresh cadence, and storage prefix
- selected-port mapping table from `port_code` to country, reporter code,
  relevant partner/corridor rules, and supported sources
- open decisions resolved

Manual work:

- create free UN Comtrade account and API subscription key
- create FRED account/API key
- add keys to local `.env`, GitHub Actions secrets, and AWS Parameter Store or
  Secrets Manager
- decide first validation port if not all 10 pilot ports
- confirm whether the public dashboard redistributes any raw Comtrade-derived
  data or only model-derived risk explanations

Cost:

- USD 0 provider cost
- negligible AWS cost

### Phase 1 - Ingestion

Deliverables:

- `ingestion/clients/fred.py`
- `ingestion/clients/un_comtrade.py`
- `serverless/handlers/fred_lambda.py`
- `serverless/handlers/comtrade_lambda.py`
- SAM parameters and schedules
- unit tests using recorded schema fixtures only where source calls are not
  required; no fabricated training rows

Implementation rules:

- raw responses are stored before transformation
- every request stores provider, endpoint, params, fetched_at, record count, and
  query hash
- API clients use retries with exponential backoff and explicit self-throttles
- Comtrade jobs are scheduled monthly or weekly, not hourly
- FRED jobs are scheduled daily

Cost:

- expected incremental AWS cost USD 0-2/month
- provider cost USD 0

### Phase 2 - Warehouse And Features

Deliverables:

- Glue tables:
  - `raw_fred_observations`
  - `raw_comtrade_flows`
- Athena CTAS:
  - `feature_macro_signals_daily`
  - `feature_trade_signals_monthly`
  - `feature_midterm_port_status_hourly`
- data quality tests:
  - no future timestamps
  - no duplicate source observations
  - source freshness thresholds
  - Comtrade/FRED release-lag checks
  - no horizon leakage

Implementation rules:

- curated tables are Parquet
- partition by date/month where useful
- join macro/trade features with as-of logic
- do not interpolate source values unless documented as last-known-valid and
  available before `observation_hour`

Cost:

- expected incremental Athena/S3 cost USD 0-3/month

### Phase 3 - Model Training And Backtest

Deliverables:

- `models/training/build_midterm_dataset.py`
- `models/training/train_midterm.py`
- model artifacts:
  - `models/port_congestion_7d/model.txt`
  - `models/port_congestion_14d/model.txt`
- metrics artifact:
  - dataset snapshot id
  - per-port AUC/PR/Brier
  - calibration bins
  - baseline comparison
  - feature importance
- updated model card section

Implementation rules:

- use time-based splits
- never use random split as the release metric
- compare baseline AIS/weather/time model to enriched model
- keep the current 24h model separate
- if enriched model does not beat baseline, ship the baseline card and keep
  Comtrade/FRED/GDELT enrichment labeled as research

Cost:

- local training: USD 0 if run locally
- AWS-backed training scans: usually USD 0-3/month at pilot scale

### Phase 4 - Prediction Publishing

Deliverables:

- predict Lambda loads both 7d and 14d artifacts
- `predictions.json` schema v2:

```json
{
  "generatedAt": "2026-06-13T10:30:00Z",
  "schemaVersion": 2,
  "predictions": {
    "NLRTM": {
      "as_of": "2026-06-13T10:00:00Z",
      "model_version": "midterm-2026-06-13",
      "horizons": {
        "7d": {
          "probability": 0.42,
          "risk": "Elevated",
          "status": "ready"
        },
        "14d": {
          "probability": 0.58,
          "risk": "Elevated",
          "status": "ready"
        }
      },
      "source_freshness": {
        "ais": "fresh",
        "weather": "fresh",
        "gdelt": "fresh",
        "fred": "fresh",
        "comtrade": "fresh_for_monthly_source"
      },
      "top_factors": [
        {
          "feature": "vessels_in_50nm",
          "direction": "increased_risk",
          "label": "Inbound vessel density"
        }
      ]
    }
  }
}
```

Cost:

- expected incremental Lambda/CloudFront invalidation cost USD 0-1/month

### Phase 5 - Frontend

Deliverables:

- `MidTermPredictionCard.jsx` or scoped update to `PredictiveAnalysis.jsx`
- source freshness subpanel
- top-factor explanation list
- live/historic source labels
- unavailable/stale/partial states
- frontend fixture generated from real exported data only

Implementation rules:

- dashboard copy must distinguish model prediction from observed history
- dashboard must state that Comtrade and FRED context is latest available
  published data, not live port telemetry
- no heuristic fallback if `predictions.json` lacks a selected-port horizon

Cost:

- USD 0 runtime beyond static hosting

### Phase 6 - Release And Monitoring

Deliverables:

- updated docs:
  - data sources
  - storage contract
  - model card
  - serverless cost page
- CloudWatch metrics:
  - `FredRecordsWritten`
  - `ComtradeRecordsWritten`
  - `MidtermPredictionsWritten`
  - `MidtermPredictionFreshnessMinutes`
- release checklist:
  - source records landed
  - feature tables rebuilt
  - time-based backtest passed
  - predictions published
  - dashboard renders selected-port card
  - stale/missing source states verified

Cost:

- included in the safe planning budget of USD 6-20/month unless Comtrade premium
  is purchased.

## Manual Work Summary

| Task | Owner | Estimated effort |
|---|---|---:|
| Create UN Comtrade free account and API key | human | 15-30 min |
| Create FRED account and API key | human | 10-20 min |
| Store keys in local/AWS/GitHub secrets | human | 20-45 min |
| Confirm first selected validation port | human | 5 min |
| Review Comtrade redistribution posture | human | 30-60 min |
| Inspect first Comtrade/FRED/GDELT landed records | engineer | 30-90 min |
| Validate top-factor copy with product intent | human + engineer | 30-60 min |
| Observe first live hourly/daily cycle | engineer | 1-2 hr |

## Open Questions

1. Which port should be the first acceptance port for the 7-day and 14-day
   model? If no single port is chosen, the implementation should run all 10
   pilot ports and let the dashboard filter to the selected port.
2. Should the output be congestion probability only, or do you also need
   expected delay minutes? Delay minutes require a separate label and likely a
   different validation standard.
3. Will the dashboard be public? If yes, avoid redistributing raw Comtrade rows
   and display only derived model context unless legal review says otherwise.
4. Is paid Comtrade premium allowed if the free tier blocks the workload, or
   must the implementation stay strictly free-provider only?

## Recommended First Build

Build the no-premium path first:

1. Add FRED and Comtrade free-tier clients.
2. Backfill a small, real, selected-port feature window.
3. Add leak-safe 7d/14d labels.
4. Train baseline and enriched LightGBM models with chronological validation.
5. Publish schema v2 predictions with local feature contributions.
6. Add the selected-port mid-term card.

This keeps direct provider spend at USD 0 and should keep the total pilot within
the USD 6-20/month operating budget while proving whether the new sources
actually improve the forecast.
