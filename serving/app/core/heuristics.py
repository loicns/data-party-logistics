"""Shared heuristic helpers (zone, ETA, confidence)."""

from __future__ import annotations

import math
from datetime import UTC, datetime


def haversine_nm(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_nm = 3440.065  # Earth radius in nautical miles
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    return radius_nm * 2 * math.asin(math.sqrt(a))


def _nav_status_parts(nav_status: object) -> tuple[str, int | None]:
    status_text = str(nav_status or "").strip().lower()
    if isinstance(nav_status, int):
        return status_text, nav_status
    if status_text.isdigit():
        return status_text, int(status_text)
    return status_text, None


def vessel_zone(distance_nm: float, speed_knots: float, nav_status: object) -> str:
    status, status_code = _nav_status_parts(nav_status)
    if "moored" in status or status_code == 5:
        return "berth"
    if "anchor" in status or status_code == 1:
        return "anchor"
    if speed_knots <= 0.3 and distance_nm <= 2:
        return "anchor"
    if distance_nm <= 50:
        return "approaching"
    return "transit"


def format_eta(distance_nm: float, speed_knots: float, zone: str) -> str:
    if zone == "berth":
        return "Berthed"
    if zone == "anchor":
        return "Waiting"
    if speed_knots <= 1.0:
        return "Unknown"
    hours = distance_nm / speed_knots
    if hours > 72:
        return ">72h"
    whole = int(hours)
    mins = round((hours - whole) * 60)
    if mins == 60:
        whole += 1
        mins = 0
    return f"{whole}h {mins:02d}m"


def confidence_score(distance_nm: float, speed_knots: float, zone: str) -> int:
    if zone in {"berth", "anchor"}:
        return 99
    score = 92
    if distance_nm > 120:
        score -= 18
    elif distance_nm > 60:
        score -= 10
    if speed_knots < 4:
        score -= 18
    elif speed_knots < 8:
        score -= 8
    return max(45, min(99, score))


def minutes_ago_text(ts: datetime | None) -> str:
    if ts is None:
        return "unavailable"
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=UTC)
    delta = int((datetime.now(UTC) - ts).total_seconds() / 60)
    if delta < 2:
        return "just now"
    if delta < 60:
        return f"{delta}m ago"
    if delta < 1440:
        return f"{delta // 60}h ago"
    return f"{delta // 1440}d ago"
