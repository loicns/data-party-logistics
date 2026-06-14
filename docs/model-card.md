# Model Card: Port Congestion 24h Classifier

_Public version. Last updated 2026-06-12._

## Summary

| Field | Value |
|---|---|
| Model | Port congestion 24h classifier |
| Task | Predict whether a selected port will be congested 24 hours after the feature timestamp |
| Output | `P(congested in 24h)` plus a binary flag at probability >= 0.5 |
| Algorithm | LightGBM `LGBMClassifier` |
| Artifact | `models/port_congestion/model.txt` |
| Current scope | 10 selected container ports |
| Public artifact | `predictions.json`, published for the dashboard |

## Intended Use

The model is intended as an early-warning signal for port-level congestion risk.
It is useful for portfolio review, operational triage, and transparent ML
engineering demonstration.

It is not intended to be used as a safety-critical routing system, contractual
ETA guarantee, financial trading signal, or authoritative source for port
closures.

## Inputs

The model uses the feature contract in `models/features.py`:

| Feature | Meaning |
|---|---|
| `vessels_in_10nm` | Vessel count within 10 nautical miles of the port center |
| `vessels_in_50nm` | Vessel count within 50 nautical miles |
| `vessels_in_200nm` | Vessel count within 200 nautical miles |
| `avg_speed_50nm` | Average speed of vessels within 50 nautical miles |
| `vessels_at_anchor` | AIS-derived count of slow or anchored vessels near port |
| `avg_wave_height_m` | Average marine wave height from weather observations |
| `hour_of_day` | Feature timestamp hour |
| `day_of_week` | Feature timestamp day of week |

Political, macroeconomic, labor, sanctions, conflict, trade-flow, and news-event
signals are not in the current deployed model. GDELT event ingestion and hourly
event feature tables now exist for analysis, but they are intentionally outside
`models/features.py` until the model is retrained and evaluated against an
AIS-only baseline.

## Label

`is_congested_24h = 1` when, 24 hours after the feature timestamp,
`vessels_at_anchor` exceeds the port's trailing 90-day 75th percentile and is
greater than 2 vessels.

This label is relative to each port's own recent history. A chronically busy
port is not automatically labelled congested.

## Evaluation

| Metric | Current value |
|---|---|
| Dataset | 2,556 port-hour rows |
| Positive rate | 21.8% |
| Held-out AUC-ROC | 0.953 |
| Positive precision / recall | 0.70 / 0.84 |
| Accuracy | 0.89 |
| Top gain features | `vessels_in_50nm`, `vessels_at_anchor`, `vessels_in_10nm` |

The current evaluation uses a stratified random split. This is useful for a
pipeline milestone, but it is optimistic for a time-series forecasting problem
because adjacent hourly rows are correlated. A time-based backtest is required
before treating the score as a reliable real-world accuracy estimate.

## Limitations

- AIS coverage is source-dependent and weaker in some waters, especially around
  Shanghai (`CNSHA`) in the current AISStream feed.
- The model predicts a port-level congestion label, not vessel-specific delay,
  berth assignment, closure, labor availability, or route disruption.
- The model does not yet use the new GDELT event feature columns.
- The public dashboard should show unavailable predictions as missing, not
  imputed or fabricated values.
- The model should be recalibrated and backtested as more chronological history
  accumulates.

## Operational Contract

Training, serving, and local prediction all import the same feature list from
`models/features.py` to avoid train/serve skew. The predict Lambda reads the
latest feature row per port, scores each port independently, and writes
`predictions.json`.

## Next Improvements

- Add chronological train/test backtesting and per-port metrics.
- Add probability calibration and threshold review.
- Publish model version, dataset snapshot, and metric history as a
  machine-readable artifact.
- Compare AIS/weather-only performance against AIS/weather plus event features
  before adding event columns to the serving feature contract.
