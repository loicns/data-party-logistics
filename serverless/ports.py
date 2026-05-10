"""Shared port metadata for the serverless pilot."""

from __future__ import annotations

from typing import TypedDict


class PortMeta(TypedDict):
    name: str
    flag: str
    lat: float
    lon: float


PORTS: dict[str, PortMeta] = {
    "NLRTM": {"name": "Rotterdam", "flag": "NL", "lat": 51.9225, "lon": 4.4792},
    "SGSIN": {"name": "Singapore", "flag": "SG", "lat": 1.2644, "lon": 103.8198},
    "USLAX": {"name": "Los Angeles", "flag": "US", "lat": 33.7405, "lon": -118.2728},
}
