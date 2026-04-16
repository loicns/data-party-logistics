"""Load cargo-capable ports from UN LOCODE and generate AIS bounding boxes.

UN LOCODE CSV columns (cleaned version):
    LOCODE, Name, NameWoDiacritics, SubDiv, Function, Status, Date, IATA, Latitude,
    Longitude, Remarks

Function codes relevant to us:
    1 = Port (maritime)
    We filter for rows where Function contains "1" and coordinates are not empty.

Usage:
    from ingestion.port_loader import load_port_bboxes
    bboxes = load_port_bboxes("warehouse/seeds/un_locode.csv")
"""

from __future__ import annotations

import csv
from pathlib import Path

APPROACH_NM = 50.0  # nautical miles radius around each port
NM_TO_DEG = 1 / 60  # 1 nautical mile ≈ 1/60 degree latitude


def load_port_bboxes(csv_path: str | Path) -> list[list[list[float]]]:
    """Load all maritime ports from UN LOCODE and return bounding boxes.

    Returns a list of [[south_lat, west_lon], [north_lat, east_lon]] boxes,
    one per port with valid coordinates and a maritime function code.

    AISStream accepts this list directly in the BoundingBoxes subscription field.
    """
    path = Path(csv_path)
    bboxes: list[list[list[float]]] = []

    with path.open(encoding="utf-8-sig") as f:  # utf-8-sig strips BOM if present
        # The file is the raw UN LOCODE CSV without headers and combined coordinates
        fieldnames = [
            "Chg",
            "Country",
            "Location",
            "Name",
            "NameWoDiacritics",
            "SubDiv",
            "Function",
            "Status",
            "Date",
            "IATA",
            "Coordinates",
            "Remarks",
        ]
        reader = csv.DictReader(f, fieldnames=fieldnames)
        for row in reader:
            # Filter: must have maritime function (Function contains "1")
            # and non-empty coordinates
            if "1" not in (row.get("Function") or ""):
                continue
            coords = row.get("Coordinates", "").strip()
            if not coords:
                continue

            try:
                parts = coords.split()
                if len(parts) != 2:
                    continue
                lat_str, lon_str = parts

                lat_deg, lat_min = float(lat_str[:2]), float(lat_str[2:4])
                lat = lat_deg + lat_min / 60.0
                if lat_str[-1].upper() == "S":
                    lat = -lat

                lon_deg, lon_min = float(lon_str[:3]), float(lon_str[3:5])
                lon = lon_deg + lon_min / 60.0
                if lon_str[-1].upper() == "W":
                    lon = -lon
            except (ValueError, IndexError):
                continue  # Skip malformed coordinates

            # Generate a square bounding box ±APPROACH_NM around the port
            # Using simple degree approximation (accurate enough for 50nm boxes)
            # Longitude degree size varies with latitude: divide by cos(lat)
            import math

            lon_deg = APPROACH_NM * NM_TO_DEG / max(math.cos(math.radians(lat)), 0.1)
            lat_deg = APPROACH_NM * NM_TO_DEG

            bboxes.append(
                [
                    [round(lat - lat_deg, 4), round(lon - lon_deg, 4)],  # [south, west]
                    [round(lat + lat_deg, 4), round(lon + lon_deg, 4)],  # [north, east]
                ]
            )

    return bboxes


def load_port_centers(csv_path: str | Path) -> dict[str, tuple[float, float]]:
    """Load all maritime ports from UN LOCODE and return their center coordinates.

    Returns a dict mapping UN LOCODE (e.g., 'NLRTM') to
    (latitude, longitude) center point.
    """
    path = Path(csv_path)
    centers: dict[str, tuple[float, float]] = {}

    with path.open(encoding="utf-8-sig") as f:
        fieldnames = [
            "Chg",
            "Country",
            "Location",
            "Name",
            "NameWoDiacritics",
            "SubDiv",
            "Function",
            "Status",
            "Date",
            "IATA",
            "Coordinates",
            "Remarks",
        ]
        reader = csv.DictReader(f, fieldnames=fieldnames)
        for row in reader:
            if "1" not in (row.get("Function") or ""):
                continue
            coords = row.get("Coordinates", "").strip()
            if not coords:
                continue
            country = (row.get("Country") or "").strip()
            loc = (row.get("Location") or "").strip()
            if not country or not loc:
                continue
            locode = f"{country}{loc}"

            try:
                parts = coords.split()
                if len(parts) != 2:
                    continue
                lat_str, lon_str = parts

                lat_deg, lat_min = float(lat_str[:2]), float(lat_str[2:4])
                lat = lat_deg + lat_min / 60.0
                if lat_str[-1].upper() == "S":
                    lat = -lat

                lon_deg, lon_min = float(lon_str[:3]), float(lon_str[3:5])
                lon = lon_deg + lon_min / 60.0
                if lon_str[-1].upper() == "W":
                    lon = -lon

                centers[locode] = (round(lat, 4), round(lon, 4))
            except (ValueError, IndexError):
                continue

    return centers
