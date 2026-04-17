"""CMEMS ocean current and wave ingestion client.

Fetches ocean current velocity (u/v components) and significant wave height
from the Copernicus Marine Service GLOBAL_ANALYSISFORECAST_PHY_001_024 dataset
for a set of route waypoints, validates with Pydantic, and writes NDJSON to S3.

Architecture:
    Source: CMEMS GLOBAL_ANALYSISFORECAST_PHY_001_024
    Variables: uo, vo, VHM0
    Output: raw/source=cmems/date=YYYY-MM-DD/batch-TIMESTAMP.ndjson in S3

Usage:
    uv run python -m ingestion.clients.cmems
"""

from __future__ import annotations

import math
import time
from datetime import datetime
from typing import Any

import structlog
from pydantic import BaseModel, computed_field

from ingestion.config import settings
from ingestion.s3_writer import write_ndjson_batch

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Route waypoints
# ---------------------------------------------------------------------------

# Define sparse waypoints along key corridors (e.g., Gulf Stream, Kuroshio).
# Naming convention: ROUTE_DESCRIPTION_INDEX

ROUTE_WAYPOINTS: dict[str, tuple[float, float]] = {
    # ── North Atlantic corridor (Rotterdam ↔ New York) ────────────────────
    "natl_01": (51.0, -10.0),  # Western approaches, UK/Ireland
    "natl_02": (47.0, -20.0),  # Mid-Atlantic ridge, eastern side
    "natl_03": (43.0, -35.0),  # Central North Atlantic
    "natl_04": (40.0, -50.0),  # Gulf Stream influence zone — highest ETA variance
    "natl_05": (38.0, -65.0),  # Western North Atlantic, approaching US shelf
    # ── Pacific corridor (Shanghai/Busan ↔ Los Angeles) ──────────────────
    "npac_01": (32.0, 140.0),  # East of Japan — Kuroshio current starts here
    "npac_02": (35.0, 160.0),  # North Pacific, post-Kuroshio
    "npac_03": (38.0, -175.0),  # Central North Pacific (international date line area)
    "npac_04": (40.0, -155.0),  # Eastern North Pacific
    "npac_05": (35.0, -135.0),  # Approaching US West Coast
    # ── Indian Ocean / Malacca Strait corridor (Singapore ↔ Middle East) ─
    "iocn_01": (1.0, 104.0),  # Malacca Strait exit
    "iocn_02": (5.0, 80.0),  # Central Indian Ocean
    "iocn_03": (12.0, 60.0),  # Arabian Sea, monsoon-driven currents
    "iocn_04": (24.0, 56.0),  # Strait of Hormuz approach
    # ── English Channel / North Sea (Rotterdam ↔ UK ports) ───────────────
    "echn_01": (51.5, 2.0),  # Southern North Sea — strong tidal currents
    "echn_02": (50.5, -1.0),  # Eastern English Channel
}
# Cache waypoint data to prevent redundant API calls during hourly runs.
# Forecasts update 12-hourly; a 6-hour TTL is sufficient.
CACHE_TTL_SECONDS = 6 * 3600

# ---------------------------------------------------------------------------
# Pydantic model
# ---------------------------------------------------------------------------


class OceanCurrentRecord(BaseModel):
    """One ocean current + wave observation at a specific waypoint and time.

    Fields use CMEMS scientific names; derived fields use snake_case.
    Serialized to S3 NDJSON with derived fields pre-computed for downstream use.
    """

    waypoint_lat: float  # Waypoint center latitude
    waypoint_lon: float  # Waypoint center longitude
    timestamp: str  # ISO 8601 forecast timestamp

    current_u_ms: float
    current_v_ms: float

    wave_height_m: float | None = None

    @computed_field  # type: ignore[prop-decorator]  # Auto-computed and serialized to JSON
    @property
    def current_speed_ms(self) -> float:
        """Magnitude of the current vector (m/s) (Euclidean norm)."""
        return round(math.sqrt(self.current_u_ms**2 + self.current_v_ms**2), 3)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def current_direction_deg(self) -> float:
        """Direction the current flows TOWARD (0=N, 90=E, 180=S, 270=W).
        Angle from true north, clockwise.
        """
        deg = math.degrees(math.atan2(self.current_u_ms, self.current_v_ms))
        return round((deg + 360) % 360, 1)  # Normalise negative angles to [0, 360)


# ---------------------------------------------------------------------------
# CMEMS client
# ---------------------------------------------------------------------------


class CMEMSClient:
    """Fetches ocean current and wave data from Copernicus Marine Service.

    Uses the official `copernicusmarine` library to subset the global physical
    ocean forecast (GLOBAL_ANALYSISFORECAST_PHY_001_024) around each route waypoint.

    DATASET VARIABLES FETCHED:
        uo  — eastward current velocity (m/s)
        vo  — northward current velocity (m/s)
        VHM0 — significant wave height (m)

    CACHING:
        Results are cached per waypoint for CACHE_TTL_SECONDS (6 hours).
        Cache is an in-process dict — it resets on process restart.
        Good enough for hourly Prefect flows; would need Redis for multi-process.
    """

    DATASET_ID = "cmems_mod_glo_phy-cur_anfc_0.083deg_PT6H-i"
    # WHY THIS DATASET:
    # GLOBAL_ANALYSISFORECAST_PHY_001_024 is CMEMS's primary global physical ocean
    # forecast. The _PT6H-i suffix means 6-hourly time resolution — matches our
    # CACHE_TTL_SECONDS. The 0.083deg spatial resolution (~9km) is sufficient for
    # shipping-corridor-scale ETA features.

    BBOX_HALF_DEG = 0.5
    # Half-size of the bounding box around each waypoint (degrees).
    # ±0.5° ≈ ±55km — captures the local current at the waypoint without
    # fetching a large region. We average all grid points in the box (Step 4.4).

    def __init__(self) -> None:
        self._cache: dict[str, tuple[float, list[OceanCurrentRecord]]] = {}
        # Cache structure: {waypoint_key: (expiry_timestamp, records_list)}
        # expiry_timestamp: Unix time after which the cache entry is stale
        # records_list: the fetched OceanCurrentRecord objects for this waypoint

    def _is_cache_valid(self, waypoint_key: str) -> bool:
        """Return True if the cache entry for this waypoint is still fresh."""
        if waypoint_key not in self._cache:
            return False  # No entry at all
        expiry, _ = self._cache[waypoint_key]
        return time.time() < expiry  # Current time is before expiry → still fresh

    def fetch_waypoint(
        self,
        waypoint_key: str,
        lat: float,
        lon: float,
    ) -> list[OceanCurrentRecord]:
        """Fetch current + wave forecast for a single waypoint.

        Returns a list of OceanCurrentRecord objects, one per forecast time step.
        For the 6-hourly dataset and a 7-day lookahead: 28 records per waypoint call.

        Uses the cache to avoid redundant CMEMS calls within CACHE_TTL_SECONDS.
        """
        if self._is_cache_valid(waypoint_key):
            _, cached = self._cache[waypoint_key]
            logger.debug("cmems_cache_hit", waypoint=waypoint_key, records=len(cached))
            return cached  # Return cached result — no API call

        logger.info("cmems_fetch_start", waypoint=waypoint_key, lat=lat, lon=lon)

        # copernicusmarine.open_dataset() downloads a subset of the global CMEMS dataset
        # as an xarray.Dataset. We specify:
        #   - minimum|maximum latitude|longitude: bounding box limits
        #   - variables: only fetch required fields to save bandwidth
        import copernicusmarine  # Lazy import — only needed when this method is called

        try:
            ds = copernicusmarine.open_dataset(
                dataset_id=self.DATASET_ID,
                username=settings.cmems_username,
                password=settings.cmems_password,
                minimum_latitude=lat - self.BBOX_HALF_DEG,
                maximum_latitude=lat + self.BBOX_HALF_DEG,
                minimum_longitude=lon - self.BBOX_HALF_DEG,
                maximum_longitude=lon + self.BBOX_HALF_DEG,
                variables=["uo", "vo"],
            )
        except Exception:
            logger.exception("cmems_fetch_failed", waypoint=waypoint_key)
            return []  # Return empty — partial data is better than crashing the run

        records = self._dataset_to_records(ds, lat, lon)

        # Store in cache with expiry
        expiry = time.time() + CACHE_TTL_SECONDS
        self._cache[waypoint_key] = (expiry, records)
        logger.info(
            "cmems_fetch_complete",
            waypoint=waypoint_key,
            records=len(records),
            cache_expires_in_h=CACHE_TTL_SECONDS / 3600,
        )
        return records

    def _dataset_to_records(
        self,
        ds: Any,  # xarray.Dataset — typed as Any to avoid import dependency
        waypoint_lat: float,
        waypoint_lon: float,
    ) -> list[OceanCurrentRecord]:
        """Convert an xarray Dataset subset into a list of OceanCurrentRecord objects.

        Strategy: spatial average over the bounding box, then one record per time step.

        Averages bounding box (e.g., 12x12 grid) for a representative waypoint value,
        reducing dataset size. Spatial variance is low here vs temporal variance.
        """
        records: list[OceanCurrentRecord] = []

        # spatial average leaves 1D series; compute evaluates dask array into memory
        ds_mean = ds.mean(dim=["latitude", "longitude"]).compute()

        for t in ds_mean.time.values:
            # ds_mean.sel(time=t) selects one time step from the averaged dataset
            step = ds_mean.sel(time=t)

            # Convert 0-dim DataArray to float; default 0.0 if missing
            uo = float(step["uo"].item()) if "uo" in step else 0.0
            vo = float(step["vo"].item()) if "vo" in step else 0.0
            vhm0 = float(step["VHM0"].item()) if "VHM0" in step else None

            # Ensure JSON-serializable ISO 8601 string
            ts_dt = datetime.utcfromtimestamp(
                (t - 0) / 1e9  # numpy datetime64 in nanoseconds → seconds
                if hasattr(t, "__float__")
                else t.astype("datetime64[s]").astype(float)
            )
            ts_str = ts_dt.strftime("%Y-%m-%dT%H:%M:%S")

            try:
                record = OceanCurrentRecord(
                    waypoint_lat=waypoint_lat,
                    waypoint_lon=waypoint_lon,
                    timestamp=ts_str,
                    current_u_ms=uo,
                    current_v_ms=vo,
                    wave_height_m=vhm0,
                )
                records.append(record)
            except Exception:
                # One bad time step doesn't abort the whole waypoint
                logger.exception("cmems_record_validation_error", timestamp=ts_str)
                continue

        return records

    def fetch_all_waypoints(self) -> list[OceanCurrentRecord]:
        """Fetch current + wave forecasts for all defined route waypoints.

        Iterates over ROUTE_WAYPOINTS, fetching each one with error isolation.
        If one waypoint fails (e.g., ocean API hiccup), others still succeed.
        """
        all_records: list[OceanCurrentRecord] = []
        for key, (lat, lon) in ROUTE_WAYPOINTS.items():
            records = self.fetch_waypoint(key, lat, lon)
            all_records.extend(records)
        logger.info("cmems_all_waypoints_done", total_records=len(all_records))
        return all_records


# ---------------------------------------------------------------------------
# Ingestion wrapper
# ---------------------------------------------------------------------------

SOURCE_NAME = "cmems"  # S3 partition: raw/source=cmems/date=YYYY-MM-DD/...


class CMEMSIngestionClient:
    """Orchestrates CMEMS fetch and S3 upload.

    Template Method Pattern:
        run()
          ↓
          _fetch() → CMEMSClient.fetch_all_waypoints()
          ↓
          _write() → write_ndjson_batch() → S3

    WHY A WRAPPER:
        CMEMSClient knows about the CMEMS API and caching.
        CMEMSIngestionClient knows about S3 partitioning and batch writing.
        Separating these concerns means you can test CMEMSClient with a mock dataset
        and test the S3 writer with a mock client — each in isolation.
    """

    def __init__(self) -> None:
        self.cmems = CMEMSClient()  # Composition: HAS-A CMEMSClient

    def run(self) -> str:
        """Fetch all waypoints and write NDJSON batch to S3.

        Returns the S3 key of the written file.
        Called by Prefect flow in Week 4:
            cmems_client = CMEMSIngestionClient()
            cmems_client.run()   # ~16 waypoints x 28 time steps = ~448 records
        """
        records = self.cmems.fetch_all_waypoints()

        if not records:
            logger.warning("cmems_no_records", action="skipping_s3_write")
            return ""

        # Serialise Pydantic models to dicts for NDJSON writer
        # model_dump() returns a plain dict; computed fields (current_speed_ms,
        # current_direction_deg) are included automatically — Pydantic v2 behaviour.
        dicts = [r.model_dump() for r in records]
        key = write_ndjson_batch(dicts, source=SOURCE_NAME)
        logger.info("cmems_run_complete", s3_key=key, record_count=len(records))
        return key


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------


def main() -> None:
    """Run CMEMS ingestion once and exit.

    Usage: uv run python -m ingestion.clients.cmems
    """
    logger.info("cmems_ingestion_starting", waypoints=len(ROUTE_WAYPOINTS))
    client = CMEMSIngestionClient()
    key = client.run()
    logger.info("cmems_ingestion_done", s3_key=key)


if __name__ == "__main__":
    main()
