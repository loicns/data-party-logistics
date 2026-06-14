"""Additive AIS v2 model feature contract.

The production serving path keeps importing models.features. This module is
only for candidate v2 training so v1 cannot switch accidentally.
"""

FEATURES_V2 = [
    "vessels_in_10nm",
    "vessels_in_50nm",
    "vessels_in_200nm",
    "avg_speed_50nm",
    "vessels_at_anchor",
    "avg_wave_height_m",
    "hour_of_day",
    "day_of_week",
    "vessels_at_berth",
    "vessels_waiting_anchor",
    "vessels_inbound",
    "vessels_outbound",
    "vessels_transit_unknown",
    "destination_match_48h_count",
    "avg_distance_delta_nm",
    "avg_draught_waiting_anchor",
]

TARGET_V2 = "is_congested_24h"
MODEL_OBJECT_KEY_V2 = "models/port_congestion/model_v2.txt"
