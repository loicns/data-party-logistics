"""Conservative vessel-state rules for AIS v2 feature engineering."""

from __future__ import annotations

from typing import Any

AT_BERTH = "at_berth"
WAITING_ANCHOR = "waiting_anchor"
INBOUND = "inbound"
OUTBOUND = "outbound"
TRANSIT_UNKNOWN = "transit_unknown"


def _nav_status_code(nav_status: Any) -> int | None:
    if isinstance(nav_status, int):
        return nav_status
    try:
        return int(str(nav_status).strip())
    except (TypeError, ValueError):
        return None


def classify_vessel_state(
    *,
    distance_nm: float,
    sog: float | None,
    nav_status: Any,
    distance_delta_nm: float | None = None,
    destination_matches_port: bool = False,
    eta_within_48h: bool = False,
) -> str:
    """Classify a vessel without treating every slow departure as waiting.

    Positive distance_delta_nm means the vessel is moving away from the port.
    Negative distance_delta_nm means the vessel is moving toward the port.
    """
    speed = 0.0 if sog is None else float(sog)
    status = _nav_status_code(nav_status)

    if distance_nm <= 15 and status == 5:
        return AT_BERTH

    if distance_delta_nm is not None and distance_delta_nm > 0.5:
        return OUTBOUND

    is_stationary_near_port = speed <= 0.5 and distance_nm <= 30
    is_declared_anchor = status == 1 and distance_nm <= 30
    is_not_moving_away = distance_delta_nm is None or distance_delta_nm <= 0.25
    if is_declared_anchor or (is_stationary_near_port and is_not_moving_away):
        return WAITING_ANCHOR

    is_moving_toward_port = distance_delta_nm is not None and distance_delta_nm < -0.5
    has_matching_voyage_eta = destination_matches_port and eta_within_48h
    if is_moving_toward_port or has_matching_voyage_eta:
        return INBOUND

    return TRANSIT_UNKNOWN
