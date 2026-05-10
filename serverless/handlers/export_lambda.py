"""Athena-backed dashboard export for the low-cost pilot."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from typing import Any

import boto3

from serverless.athena import first_row, run_query
from serverless.metrics import put_metric
from serverless.ports import PORTS
from serverless.s3_health import latest_object_for_prefix, object_age_minutes


def _env(name: str, default: str = "") -> str:
    value = os.getenv(name, default)
    if not value:
        raise ValueError(f"Missing required env var: {name}")
    return value


def _sources(bucket: str) -> list[dict[str, Any]]:
    source_defs = [
        (
            "AIS Vessel Positions",
            "raw/source=ais/",
            "Hourly AIS snapshots near selected ports",
            55,
        ),
        (
            "Marine Weather",
            "raw/source=weather/",
            "Wave and marine conditions from Open-Meteo",
            30,
        ),
        (
            "NOAA Tides",
            "raw/source=noaa_tides/",
            "US tidal predictions from NOAA CO-OPS",
            15,
        ),
    ]
    results: list[dict[str, Any]] = []
    for name, prefix, detail, contribution in source_defs:
        obj = latest_object_for_prefix(bucket, prefix)
        age = object_age_minutes(obj)
        if age is None:
            freshness = "unavailable"
            status = "stale"
        elif age < 120:
            freshness = f"{int(age)} min ago"
            status = "active"
        elif age < 1440:
            freshness = f"{int(age // 60)}h ago"
            status = "stale"
        else:
            freshness = f"{int(age // 1440)}d ago"
            status = "stale"
        results.append(
            {
                "name": name,
                "status": status,
                "freshness": freshness,
                "detail": detail,
                "contribution": contribution,
            }
        )
    return results


def _safe_float(value: str | None, default: float = 0.0) -> float:
    try:
        return float(value) if value not in {None, ""} else default
    except ValueError:
        return default


def _pad(values: list[float], size: int, fill: float = 0.0) -> list[float]:
    if not values:
        return [fill] * size
    if len(values) >= size:
        return values[-size:]
    return [values[0]] * (size - len(values)) + values


def _summary_sql(port_code: str, lat: float, lon: float) -> str:
    return f"""
WITH latest AS (
    SELECT mmsi, max(from_iso8601_timestamp(received_at)) AS max_observed
    FROM raw_ais_positions
    WHERE date >= date_format(current_date - INTERVAL '2' DAY, '%Y-%m-%d')
    GROUP BY mmsi
),
current_positions AS (
    SELECT a.*
    FROM raw_ais_positions a
    JOIN latest l
      ON a.mmsi = l.mmsi
     AND from_iso8601_timestamp(a.received_at) = l.max_observed
    WHERE a.date >= date_format(current_date - INTERVAL '2' DAY, '%Y-%m-%d')
),
with_distance AS (
    SELECT
        mmsi,
        ship_name,
        lat,
        lon,
        sog,
        nav_status,
        3440.065 * 2 * asin(
            sqrt(
                power(sin(radians(lat - {lat}) / 2), 2) +
                cos(radians({lat})) * cos(radians(lat)) *
                power(sin(radians(lon - {lon}) / 2), 2)
            )
        ) AS distance_nm
    FROM current_positions
)
SELECT
    count(*) AS total_vessels,
    sum(
        CASE
            WHEN coalesce(nav_status, 15) = 1 OR coalesce(sog, 0) <= 1
                THEN 1
            ELSE 0
        END
    ) AS vessels_at_anchor,
    avg(coalesce(sog, 0)) AS avg_speed_in_zone,
    (
        SELECT max_by(wave_height_m, from_iso8601_timestamp(timestamp))
        FROM raw_weather_observations w
        WHERE w.port_code = '{port_code}'
          AND w.date >= date_format(current_date - INTERVAL '2' DAY, '%Y-%m-%d')
    ) AS max_wave_height_m
FROM with_distance
WHERE distance_nm <= 200
"""


def _trend_sql(port_code: str, lat: float, lon: float) -> str:
    return f"""
WITH daily_positions AS (
    SELECT
        date,
        mmsi,
        max_by(ship_name, from_iso8601_timestamp(received_at)) AS ship_name,
        max_by(lat, from_iso8601_timestamp(received_at)) AS lat,
        max_by(lon, from_iso8601_timestamp(received_at)) AS lon,
        max_by(sog, from_iso8601_timestamp(received_at)) AS sog,
        max_by(nav_status, from_iso8601_timestamp(received_at)) AS nav_status
    FROM raw_ais_positions
    WHERE date >= date_format(current_date - INTERVAL '6' DAY, '%Y-%m-%d')
    GROUP BY date, mmsi
),
scored AS (
    SELECT
        date,
        3440.065 * 2 * asin(
            sqrt(
                power(sin(radians(lat - {lat}) / 2), 2) +
                cos(radians({lat})) * cos(radians(lat)) *
                power(sin(radians(lon - {lon}) / 2), 2)
            )
        ) AS distance_nm,
        sog,
        nav_status
    FROM daily_positions
),
weather_daily AS (
    SELECT date, max(wave_height_m) AS max_wave_height_m
    FROM raw_weather_observations
    WHERE port_code = '{port_code}'
      AND date >= date_format(current_date - INTERVAL '6' DAY, '%Y-%m-%d')
    GROUP BY date
)
SELECT
    s.date AS activity_date,
    count(*) AS total_vessels,
    sum(
        CASE
            WHEN coalesce(nav_status, 15) = 1 OR coalesce(sog, 0) <= 1
                THEN 1
            ELSE 0
        END
    ) AS vessels_at_anchor,
    avg(coalesce(sog, 0)) AS avg_speed_in_zone,
    coalesce(max(w.max_wave_height_m), 0) AS max_wave_height_m
FROM scored s
LEFT JOIN weather_daily w ON s.date = w.date
WHERE distance_nm <= 200
GROUP BY s.date
ORDER BY s.date DESC
LIMIT 6
"""


def _vessels_sql(lat: float, lon: float) -> str:
    return f"""
WITH latest AS (
    SELECT mmsi, max(from_iso8601_timestamp(received_at)) AS max_observed
    FROM raw_ais_positions
    WHERE date >= date_format(current_date - INTERVAL '2' DAY, '%Y-%m-%d')
    GROUP BY mmsi
),
current_positions AS (
    SELECT a.*
    FROM raw_ais_positions a
    JOIN latest l
      ON a.mmsi = l.mmsi
     AND from_iso8601_timestamp(a.received_at) = l.max_observed
    WHERE a.date >= date_format(current_date - INTERVAL '2' DAY, '%Y-%m-%d')
),
with_distance AS (
    SELECT
        mmsi,
        ship_name,
        lat,
        lon,
        sog,
        nav_status,
        3440.065 * 2 * asin(
            sqrt(
                power(sin(radians(lat - {lat}) / 2), 2) +
                cos(radians({lat})) * cos(radians(lat)) *
                power(sin(radians(lon - {lon}) / 2), 2)
            )
        ) AS distance_nm
    FROM current_positions
)
SELECT
    mmsi,
    ship_name,
    lat,
    lon,
    sog,
    nav_status,
    distance_nm
FROM with_distance
WHERE distance_nm <= 200
ORDER BY distance_nm ASC
LIMIT 12
"""


def _zone(distance_nm: float, speed_knots: float, nav_status: Any) -> str:
    status = str(nav_status or "").lower()
    if "5" in status or "moored" in status:
        return "berth"
    if "1" in status or "anchor" in status or speed_knots <= 1.0:
        return "anchor"
    if distance_nm <= 50:
        return "approaching"
    return "transit"


def _eta(distance_nm: float, speed_knots: float, zone: str) -> str:
    if zone == "berth":
        return "Berthed"
    if zone == "anchor":
        return "Waiting"
    if speed_knots <= 1.0:
        return "Unknown"
    hours = distance_nm / speed_knots
    if hours > 72:
        return ">72h"
    whole_hours = int(hours)
    minutes = round((hours - whole_hours) * 60)
    return f"{whole_hours}h {minutes:02d}m"


def _confidence(distance_nm: float, speed_knots: float, zone: str) -> int:
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


def _trend_score(
    total_vessels: float,
    anchored: float,
    avg_speed: float,
    max_wave: float,
) -> float:
    if total_vessels <= 0:
        return 0.0
    anchored_ratio = min(1.0, anchored / total_vessels)
    wave_component = min(1.0, max_wave / 3.0)
    speed_component = min(1.0, max(0.0, 6.0 - avg_speed) / 6.0)
    return round(
        min(
            1.0,
            0.65 * anchored_ratio + 0.25 * wave_component + 0.10 * speed_component,
        ),
        2,
    )


def _build_port_payload(
    database: str,
    output_location: str,
    port_code: str,
    meta: dict[str, Any],
) -> dict[str, Any]:
    summary = (
        first_row(
            _summary_sql(port_code, meta["lat"], meta["lon"]),
            database=database,
            output_location=output_location,
        )
        or {}
    )

    trends_rows = run_query(
        _trend_sql(port_code, meta["lat"], meta["lon"]),
        database=database,
        output_location=output_location,
    )
    trend_values = []
    for row in reversed(trends_rows):
        trend_values.append(
            _trend_score(
                _safe_float(row.get("total_vessels")),
                _safe_float(row.get("vessels_at_anchor")),
                _safe_float(row.get("avg_speed_in_zone")),
                _safe_float(row.get("max_wave_height_m")),
            )
        )
    trend_values = _pad(trend_values, 6, 0.0)

    vessel_rows = run_query(
        _vessels_sql(meta["lat"], meta["lon"]),
        database=database,
        output_location=output_location,
    )
    vessels = []
    for row in vessel_rows:
        distance_nm = round(_safe_float(row.get("distance_nm")), 1)
        speed_knots = round(_safe_float(row.get("sog")), 1)
        zone = _zone(distance_nm, speed_knots, row.get("nav_status"))
        vessels.append(
            {
                "name": row.get("ship_name") or f"MMSI {row.get('mmsi')}",
                "mmsi": str(row.get("mmsi") or ""),
                "lat": round(_safe_float(row.get("lat")), 4),
                "lon": round(_safe_float(row.get("lon")), 4),
                "sog": speed_knots,
                "zone": zone,
                "dist": distance_nm,
                "eta": _eta(distance_nm, speed_knots, zone),
                "conf": _confidence(distance_nm, speed_knots, zone),
            }
        )

    return {
        "name": meta["name"],
        "flag": meta["flag"],
        "code": port_code,
        "lat": meta["lat"],
        "lon": meta["lon"],
        "metrics": {
            "congestionPct": round(
                _trend_score(
                    _safe_float(summary.get("total_vessels")),
                    _safe_float(summary.get("vessels_at_anchor")),
                    _safe_float(summary.get("avg_speed_in_zone")),
                    _safe_float(summary.get("max_wave_height_m")),
                )
                * 100
            ),
            "waiting": int(_safe_float(summary.get("vessels_at_anchor"))),
            "avgSpeed": round(_safe_float(summary.get("avg_speed_in_zone")), 1),
            "maxWave": round(_safe_float(summary.get("max_wave_height_m")), 1),
            "tracked": int(_safe_float(summary.get("total_vessels"))),
        },
        "forecast": trend_values[-5:],
        "trend": trend_values,
        "vessels": vessels,
    }


def lambda_handler(_event: dict[str, Any], _context: Any) -> dict[str, Any]:
    bucket = _env("DATA_BUCKET_NAME")
    database = _env("ATHENA_DATABASE")
    output_location = _env("ATHENA_OUTPUT_LOCATION")
    export_key = os.getenv("DASHBOARD_EXPORT_KEY", "exports/dashboard/demo-data.js")

    payload = {
        "metadata": {
            "generatedAt": datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC"),
            "mode": "athena-export",
        },
        "labels": {
            "outlook": ["D-4", "D-3", "D-2", "D-1", "Now"],
            "trend": ["D-5", "D-4", "D-3", "D-2", "D-1", "Now"],
        },
        "sources": _sources(bucket),
        "ports": {
            code: _build_port_payload(database, output_location, code, meta)
            for code, meta in PORTS.items()
        },
    }

    body = "window.DEMO_DATA = " + json.dumps(payload, indent=2) + ";\n"
    s3 = boto3.client("s3")
    s3.put_object(
        Bucket=bucket,
        Key=export_key,
        Body=body.encode("utf-8"),
        ContentType="application/javascript",
        CacheControl="no-cache",
    )

    date_prefix = datetime.now(UTC).strftime("%Y-%m-%d")
    curated_key = f"curated/port_metrics/date={date_prefix}/latest.json"
    s3.put_object(
        Bucket=bucket,
        Key=curated_key,
        Body=json.dumps(payload, indent=2).encode("utf-8"),
        ContentType="application/json",
        CacheControl="no-cache",
    )

    put_metric("ExportRunSuccess", 1)
    put_metric("ExportArtifactWritten", 1)
    put_metric(
        "TrackedVesselsTotal",
        sum(len(port["vessels"]) for port in payload["ports"].values()),
    )

    return {"status": "ok", "export_key": export_key, "curated_key": curated_key}
