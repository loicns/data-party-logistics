"""GeoJSON geofence matching helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

GeoJsonFeature = dict[str, Any]


def load_feature_collection(path: str | Path) -> list[GeoJsonFeature]:
    """Load GeoJSON features from a FeatureCollection file."""
    with Path(path).open(encoding="utf-8") as file:
        collection = json.load(file)

    if collection.get("type") != "FeatureCollection":
        raise ValueError("Expected a GeoJSON FeatureCollection")
    return list(collection.get("features", []))


def matching_geofences(
    *,
    lat: float,
    lon: float,
    features: list[GeoJsonFeature],
    port_code: str | None = None,
    zone_type: str | None = None,
) -> list[GeoJsonFeature]:
    """Return GeoJSON features containing a vessel position."""
    matches = []
    for feature in features:
        properties = feature.get("properties", {})
        if port_code and properties.get("port_code") != port_code:
            continue
        if zone_type and properties.get("zone_type") != zone_type:
            continue
        geometry = feature.get("geometry", {})
        if geometry.get("type") != "Polygon":
            continue
        if _point_in_polygon(lon, lat, geometry.get("coordinates", [])):
            matches.append(feature)
    return matches


def best_geofence_match(
    *,
    lat: float,
    lon: float,
    features: list[GeoJsonFeature],
    port_code: str | None = None,
    zone_type: str | None = None,
) -> GeoJsonFeature | None:
    """Return the first matching geofence for a vessel position."""
    matches = matching_geofences(
        lat=lat,
        lon=lon,
        features=features,
        port_code=port_code,
        zone_type=zone_type,
    )
    return matches[0] if matches else None


def _point_in_polygon(
    lon: float,
    lat: float,
    coordinates: list[list[list[float]]],
) -> bool:
    if not coordinates:
        return False

    outer_ring = coordinates[0]
    if not _point_in_ring(lon, lat, outer_ring):
        return False

    holes = coordinates[1:]
    return not any(_point_in_ring(lon, lat, hole) for hole in holes)


def _point_in_ring(lon: float, lat: float, ring: list[list[float]]) -> bool:
    inside = False
    if len(ring) < 4:
        return False

    previous_lon, previous_lat = ring[-1]
    for current_lon, current_lat in ring:
        crosses_lat = (current_lat > lat) != (previous_lat > lat)
        if crosses_lat:
            slope_lon = (previous_lon - current_lon) * (lat - current_lat)
            slope_lon /= previous_lat - current_lat
            intersect_lon = slope_lon + current_lon
            if lon < intersect_lon:
                inside = not inside
        previous_lon, previous_lat = current_lon, current_lat
    return inside
