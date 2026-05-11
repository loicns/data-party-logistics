"""API routes for the Data Party Logistics serving layer."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, TypedDict

from fastapi import APIRouter, HTTPException, Query

from ..core.db import get_conn
from ..core.heuristics import (
    confidence_score,
    format_eta,
    vessel_zone,
)
from ..core.ports import PORTS, TERMINAL_NAMES, PortMeta
from ..core.queries import VESSELS_SQL, WEATHER_SQL, ZONE_COUNTS_SQL

router = APIRouter()

MAX_RADIUS_NM = 200


class PredictiveVessel(TypedDict):
    name: str
    mmsi: str
    eta: str
    distance_nm: float
    confidence: int
    ship_type: str


def _get_port_or_404(port_code: str) -> PortMeta:
    meta = PORTS.get(port_code.upper())
    if not meta:
        raise HTTPException(status_code=404, detail=f"Unknown port code: {port_code}")
    return meta


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/ports  — list all available ports
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/ports")
async def list_ports():
    return {
        code: {"name": m["name"], "flag": m["flag"], "lat": m["lat"], "lon": m["lon"]}
        for code, m in PORTS.items()
    }


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/ports/{port_code}  — full port payload (vessels + metrics + berths)
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/ports/{port_code}")
async def get_port(
    port_code: str,
    zone: Annotated[str | None, Query(description="Filter vessels by zone")] = None,
    radius_nm: Annotated[int, Query(ge=10, le=500)] = MAX_RADIUS_NM,
):
    meta = _get_port_or_404(port_code)
    port_code = port_code.upper()

    async with get_conn() as conn:
        # ── Vessels ──────────────────────────────────────────────────────────
        async with conn.cursor() as cur:
            await cur.execute(
                VESSELS_SQL,
                {
                    "port_lat": meta["lat"],
                    "port_lon": meta["lon"],
                    "max_radius_nm": radius_nm,
                },
            )
            vessel_rows = await cur.fetchall()

        # ── Weather ───────────────────────────────────────────────────────────
        async with conn.cursor() as cur:
            await cur.execute(WEATHER_SQL, {"port_code": port_code})
            wx_row = await cur.fetchone()

    # ── Build vessel list ──────────────────────────────────────────────────
    vessels: list[dict] = []
    for row in vessel_rows:
        dist = round(float(row["distance_nm"] or 0.0), 1)
        sog = round(float(row["speed_knots"] or 0.0), 1)
        z = vessel_zone(dist, sog, row.get("nav_status"))
        if zone and z != zone:
            continue
        vessels.append(
            {
                "name": row["vessel_name"] or f"MMSI {row['mmsi']}",
                "mmsi": str(row["mmsi"]),
                "lat": round(float(row["latitude"]), 4),
                "lon": round(float(row["longitude"]), 4),
                "sog": sog,
                "zone": z,
                "dist": dist,
                "eta": format_eta(dist, sog, z),
                "conf": confidence_score(dist, sog, z),
                "ship_type": row.get("ship_type") or "Unknown",
                "observed_at": (
                    row["observed_at"].isoformat() if row.get("observed_at") else None
                ),
            }
        )

    # ── Derive metrics ─────────────────────────────────────────────────────
    berthed = [v for v in vessels if v["zone"] == "berth"]
    waiting = [v for v in vessels if v["zone"] == "anchor"]
    approaching = [v for v in vessels if v["zone"] in ("approaching", "transit")]

    congestion_pct = round(len(waiting) / max(len(berthed) + len(waiting), 1) * 100)
    max_wave = round(float(wx_row["max_wave_height_m"] or 0.0), 1) if wx_row else 0.0

    metrics = {
        "tracked": len(vessels),
        "congestionPct": congestion_pct,
        "waiting": len(waiting),
        "maxWave": max_wave,
    }

    # ── Virtual berths ────────────────────────────────────────────────────
    terminal_names = TERMINAL_NAMES.get(
        port_code, [f"Terminal {i}" for i in range(1, 7)]
    )
    berth_allocations = []
    for i, terminal in enumerate(terminal_names):
        if i < len(berthed):
            v = berthed[i]
            berth_allocations.append(
                {
                    "id": f"berth-{i + 1}",
                    "name": terminal,
                    "status": "occupied",
                    "vessel": v["name"],
                    "mmsi": v["mmsi"],
                    "eta": "Berthed",
                }
            )
        else:
            berth_allocations.append(
                {
                    "id": f"berth-{i + 1}",
                    "name": terminal,
                    "status": "available",
                    "vessel": None,
                    "mmsi": None,
                    "eta": None,
                }
            )

    # ── Arrival schedule ──────────────────────────────────────────────────
    schedule = sorted(
        [
            {
                "vessel": v["name"],
                "mmsi": v["mmsi"],
                "type": "Arrival",
                "status": "In Transit",
                "eta": v["eta"],
                "distance_nm": v["dist"],
            }
            for v in approaching
        ],
        key=lambda x: x["distance_nm"],
    )

    return {
        "name": meta["name"],
        "flag": meta["flag"],
        "code": port_code,
        "lat": meta["lat"],
        "lon": meta["lon"],
        "metrics": metrics,
        "vessels": vessels,
        "berthAllocations": berth_allocations,
        "schedule": schedule,
    }


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/ports/{port_code}/insights  — aggregated analytics data
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/ports/{port_code}/insights")
async def get_insights(
    port_code: str,
    radius_nm: Annotated[int, Query(ge=10, le=500)] = MAX_RADIUS_NM,
):
    meta = _get_port_or_404(port_code)

    async with get_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                ZONE_COUNTS_SQL,
                {
                    "port_lat": meta["lat"],
                    "port_lon": meta["lon"],
                    "max_radius_nm": radius_nm,
                },
            )
            type_rows = await cur.fetchall()

        async with conn.cursor() as cur:
            await cur.execute(
                VESSELS_SQL,
                {
                    "port_lat": meta["lat"],
                    "port_lon": meta["lon"],
                    "max_radius_nm": radius_nm,
                },
            )
            all_vessels = await cur.fetchall()

    # Zone breakdown for charts
    zone_counts: dict[str, int] = {
        "berth": 0,
        "anchor": 0,
        "approaching": 0,
        "transit": 0,
    }
    for row in all_vessels:
        dist = float(row["distance_nm"] or 0)
        sog = float(row["speed_knots"] or 0)
        z = vessel_zone(dist, sog, row.get("nav_status"))
        zone_counts[z] = zone_counts.get(z, 0) + 1

    vessel_type_breakdown = [
        {"type": r["ship_type"], "count": int(r["count"])} for r in type_rows
    ]

    return {
        "port": port_code.upper(),
        "portName": meta["name"],
        "totalVessels": len(all_vessels),
        "zoneBreakdown": zone_counts,
        "vesselTypeBreakdown": vessel_type_breakdown,
        "generatedAt": datetime.now(UTC).isoformat(),
    }


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/ports/{port_code}/predictive  — heuristic-based forecasts
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/ports/{port_code}/predictive")
async def get_predictive(
    port_code: str,
    radius_nm: Annotated[int, Query(ge=10, le=500)] = MAX_RADIUS_NM,
):
    meta = _get_port_or_404(port_code)

    async with get_conn() as conn, conn.cursor() as cur:
        await cur.execute(
            VESSELS_SQL,
            {
                "port_lat": meta["lat"],
                "port_lon": meta["lon"],
                "max_radius_nm": radius_nm,
            },
        )
        vessel_rows = await cur.fetchall()

    approaching: list[PredictiveVessel] = []
    for row in vessel_rows:
        dist = float(row["distance_nm"] or 0)
        sog = float(row["speed_knots"] or 0)
        z = vessel_zone(dist, sog, row.get("nav_status"))
        if z not in ("approaching", "transit"):
            continue
        conf = confidence_score(dist, sog, z)
        approaching.append(
            {
                "name": row["vessel_name"] or f"MMSI {row['mmsi']}",
                "mmsi": str(row["mmsi"]),
                "eta": format_eta(dist, sog, z),
                "distance_nm": round(dist, 1),
                "confidence": conf,
                "ship_type": row.get("ship_type") or "Unknown",
            }
        )

    # Overall risk heuristic: proportion of low-confidence arrivals
    if approaching:
        avg_conf = sum(v["confidence"] for v in approaching) / len(approaching)
        risk = "High" if avg_conf < 65 else "Elevated" if avg_conf < 80 else "Nominal"
    else:
        avg_conf = 99.0
        risk = "Nominal"

    return {
        "port": port_code.upper(),
        "portName": meta["name"],
        "incomingVessels": sorted(approaching, key=lambda x: x["distance_nm"]),
        "overallRisk": risk,
        "fluidityConfidence": round(avg_conf),
        "generatedAt": datetime.now(UTC).isoformat(),
    }
