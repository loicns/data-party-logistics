# 09 — Model Card: Port Congestion 24h Classifier

_Last updated 2026-06-11 · artifact `models/port_congestion/model.txt`_

## Summary

| | |
|---|---|
| Task | Binary classification — will the port be congested 24 hours from now? |
| Algorithm | LightGBM (`LGBMClassifier`, 100 trees, lr 0.05, `scale_pos_weight` for imbalance) |
| Serving artifact | Native LightGBM booster, text format (`model.txt`) — loads with `lgb.Booster(model_str=...)`, no scikit-learn at inference |
| Trained | 2026-06-10, on ~54 days of AIS history (2026-04-16 → 2026-06-09) |
| Dataset | 2,556 rows (port × hour), 10 ports, 21.8% positive rate |

## Label definition

`is_congested_24h = 1` when, 24 hours after the feature timestamp,
`vessels_at_anchor` exceeds the port's **trailing-90-day 75th percentile** AND
is greater than 2. Defined in `athena/queries/congestion_target.sql`.

## Features (the contract — `models/features.py`)

`vessels_in_10nm`, `vessels_in_50nm`, `vessels_in_200nm`, `avg_speed_50nm`,
`vessels_at_anchor`, `avg_wave_height_m`, `hour_of_day`, `day_of_week`

Training (`build_dataset.py`), serving (`predict_lambda.py`), and the local CLI
(`predict.py`) all import this list — the train/serve-skew guard (NFR4).

## Evaluation

| Metric | Value |
|---|---|
| AUC-ROC (held-out 20%) | **0.953** |
| Precision / recall (positive class) | 0.70 / 0.84 |
| Accuracy | 0.89 |
| Top features by gain | `vessels_in_50nm`, `vessels_at_anchor`, `vessels_in_10nm` |

## Known limitations — read before trusting the number

1. **Split caveat (material):** the split is **stratified random**, not
   time-based, because the chronological tail of the dataset had zero positive
   labels. Random splitting of overlapping hourly windows leaks temporal
   correlation, so 0.953 is **optimistic**. Re-evaluate with a time-based split
   once more balanced history accumulates (v1.3).
2. **Label is relative:** "congested" is defined against each port's own
   trailing distribution — a chronically busy port is not automatically
   "congested".
3. **Coverage skew:** Chinese waters (CNSHA) have sparse terrestrial AIS
   coverage on aisstream.io; features there are built from thin data.
4. **Weather feature:** `avg_wave_height_m` aggregates marine wave state; wind
   speed is proxied by `wind_wave_height_m` upstream (the raw feed has no
   direct wind-speed column).

## Retraining

See `08-RUNBOOK.md` § Retrain. `train.py` asserts AUC ≥ 0.65 before uploading —
a failed assertion blocks the artifact from shipping.
