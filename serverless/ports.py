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
    "CNSHA": {"name": "Shanghai", "flag": "CN", "lat": 30.6267, "lon": 121.9851},
    "DEHAM": {"name": "Hamburg", "flag": "DE", "lat": 53.5425, "lon": 9.9663},
    "BEANR": {"name": "Antwerp", "flag": "BE", "lat": 51.2194, "lon": 4.4025},
    "GBFXT": {"name": "Felixstowe", "flag": "GB", "lat": 51.9500, "lon": 1.3500},
    "AEDXB": {"name": "Dubai", "flag": "AE", "lat": 24.9857, "lon": 55.0272},
    "USNYC": {"name": "New York", "flag": "US", "lat": 40.6892, "lon": -74.0445},
    "TWKHH": {"name": "Kaohsiung", "flag": "TW", "lat": 22.6163, "lon": 120.2650},
}
