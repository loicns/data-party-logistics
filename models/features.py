"""Single source of truth for the model's feature contract.

Both training (train.py) and serving (predict.py) import from here so
they can never disagree on which columns the model expects. This is the
contract that prevents train/serve skew.
"""

FEATURES = [
    "vessels_in_10nm",
    "vessels_in_50nm",
    "vessels_in_200nm",
    "avg_speed_50nm",
    "vessels_at_anchor",
    "avg_wave_height_m",
    "hour_of_day",
    "day_of_week",
]

TARGET = "is_congested_24h"
