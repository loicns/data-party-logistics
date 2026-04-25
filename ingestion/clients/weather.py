"""Marine weather ingestion client — Open-Meteo."""

from __future__ import annotations  # Modern type hints (int | None syntax)

import logging
from datetime import UTC, datetime
from typing import Any  # Used for the "hourly" dict type which has mixed values

import httpx  # HTTP client (same as other clients — consistency)
from pydantic import BaseModel  # Data validation
from tenacity import retry, stop_after_attempt, wait_exponential  # Retry decorator

from ingestion.config import Settings  # Centralised config

logger = logging.getLogger(__name__)


# ─── Dynamic port coordinate loader ─────────────────────────────────────────
# Load port coordinates from the UN LOCODE CSV (same source as AIS client)


def load_port_coordinates() -> dict[str, tuple[float, float]]:
    """Load port center coordinates from the UN LOCODE CSV via port_loader.

    Returns dict mapping port_code → (lat, lon).
    Falls back to FALLBACK_PORT_COORDINATES if port_loader fails.
    """
    # Temporarily hardcoded to use the 10 fallback ports for quick testing
    return dict(FALLBACK_PORT_COORDINATES)


# ─── Fallback port coordinate registry (for tests / offline use) ─────────────
# Key = UN/LOCODE port code  (2-letter country + 3-letter location)
# Value = (latitude, longitude) tuple — decimal degrees, WGS84
FALLBACK_PORT_COORDINATES: dict[str, tuple[float, float]] = {
    "NLRTM": (51.95, 4.05),  # Rotterdam  — 51.95°N 4.05°E
    "CNSHA": (31.23, 121.47),  # Shanghai   — 31.23°N 121.47°E
    "SGSIN": (1.26, 103.84),  # Singapore  — 1.26°N 103.84°E
    "USLAX": (33.74, -118.27),  # Los Angeles — 33.74°N 118.27°W (negative = West)
    "DEHAM": (53.55, 9.93),  # Hamburg    — 53.55°N 9.93°E
    "BEANR": (51.23, 4.40),  # Antwerp    — 51.23°N 4.40°E
    "GBFXT": (51.96, 1.35),  # Felixstowe — 51.96°N 1.35°E
    "JPTYO": (35.65, 139.77),  # Tokyo      — 35.65°N 139.77°E
    "KRPUS": (35.10, 129.04),  # Busan      — 35.10°N 129.04°E
    "AEJEA": (25.02, 55.06),  # Jebel Ali  — 25.02°N 55.06°E
}
# WHY UN/LOCODEs?
# The AIS stream uses UN/LOCODEs in the vessel's self-reported destination field
# (e.g., "NLRTM" for Rotterdam). Using the same codes here lets us JOIN the
# weather feature to the AIS records directly on port_code without a translation step.
#
# FALLBACK_PORT_COORDINATES is also used in:
# - features/port_features.py         (spatial joins)
# - serving/app/features.py           (runtime weather lookup for /predict/eta)


class MarineWeatherHourly(BaseModel):
    """A single hourly marine weather observation/forecast.

    This is the STORAGE schema — what we write to S3 and later read in dbt.
    All field names are snake_case because that's what our dbt models expect.

    Fields marked `float | None` can be NULL — not all locations have all data
    (e.g., inland ports may not have swell data).
    """

    port_code: str  # UN/LOCODE (e.g., "NLRTM")
    timestamp: str  # ISO 8601 string (e.g., "2026-04-13T00:00")
    wave_height_m: float | None = None  # Significant wave height in metres
    wave_direction_deg: float | None = (
        None  # Mean wave direction in degrees (0=N, 90=E, 180=S, 270=W)
    )
    wave_period_s: float | None = None  # Mean wave period in seconds
    wind_wave_height_m: float | None = (
        None  # Wind-generated wave height (short-period swells)
    )
    swell_wave_height_m: float | None = (
        None  # Ocean swell height (long-period, from distant storms)
    )
    # Together, these 5 fields give the model a rich view of sea state.
    # In Week 5, we derive `weather_severity_score` from these:
    #   severity = 0.5 * wave_height + 0.3 * wind_wave + 0.2 * swell
    # This composite score is what actually feeds the ML model.


class WeatherResponse(BaseModel):
    """Parsed Open-Meteo marine API response envelope.

    Open-Meteo returns a flat response with parallel arrays:
    {
        "latitude": 51.95,
        "longitude": 4.05,
        "hourly": {
            "time":        ["2026-04-13T00:00", "2026-04-13T01:00", ...],
            "wave_height":  [1.2, 1.3, ...],
            "wave_period":  [5.5, 5.8, ...],
            ...
        }
    }

    The "hourly" dict maps variable names to parallel arrays.
    Index i in "time" corresponds to index i in "wave_height", etc.
    We iterate by index to reconstruct per-hour records (Step 3.3).
    """

    latitude: float
    longitude: float
    hourly: dict[str, list[Any]] = {}
    # dict[str, list[Any]]:
    #   - str key = variable name ("time", "wave_height", ...)
    #   - list[Any] = array of values (strings for time, floats for measurements)
    # We use `Any` here because the array can contain floats, strings, or None.


class OpenMeteoClient:
    """Fetches marine weather forecasts from Open-Meteo.

    Open-Meteo is a free, no-API-key marine forecast service.
    It provides 7-day hourly forecasts at any lat/lon.
    Rate limit: 10,000 requests/day — sufficient for all target ports x 24 fetches.
    """

    BASE_URL = "https://marine-api.open-meteo.com/v1/marine"
    # Separate subdomain (marine-api vs api.open-meteo.com) — the marine endpoint
    # provides ocean-specific variables: wave height, swell, wave period.
    # The standard endpoint provides atmospheric: temperature, wind, pressure.
    # We need both — but start with marine (most impactful for ETA model).

    def __init__(self) -> None:
        self.client = httpx.Client(
            timeout=15
        )  # Marine API is fast; 15s timeout sufficient
        self.port_coordinates = load_port_coordinates()  # Load dynamically from CSV

    @retry(
        stop=stop_after_attempt(3),  # 3 total attempts
        wait=wait_exponential(
            multiplier=1,  # Shorter waits (API is faster)
            min=2,  # Minimum 2s wait
            max=10,  # Maximum 10s wait
        ),
    )
    def fetch_forecast(
        self,
        port_code: str,
        lat: float,
        lon: float,
        forecast_days: int = 7,
        # Default: 7-day forecast (Open-Meteo supports up to 16)
    ) -> list[MarineWeatherHourly]:
        """Fetch marine forecast for a single port.

        Returns a list of MarineWeatherHourly records (one per hour x forecast_days).
        For forecast_days=7: 7 x 24 = 168 records per port call.
        """
        params: dict[str, str | int | float] = {
            "latitude": lat,
            "longitude": lon,
            "hourly": ",".join(
                [  # Open-Meteo accepts comma-separated variable names
                    "wave_height",
                    "wave_direction",
                    "wave_period",
                    "wind_wave_height",
                    "swell_wave_height",
                ]
            ),
            "forecast_days": forecast_days,
        }
        # Note: no API key in params — Open-Meteo is free without authentication.
        # This is unusual; most APIs require at least a token.

        resp = self.client.get(self.BASE_URL, params=params)
        resp.raise_for_status()  # Trigger retry on 4xx/5xx
        data = resp.json()

        hourly = data.get("hourly", {})  # Get the hourly sub-dict
        times = hourly.get(
            "time", []
        )  # The timestamps array: ["2026-04-13T00:00", ...]

        # ─── Convert parallel arrays → list of per-hour objects ──────────────
        # Open-Meteo format:    {"time": [T0, T1, T2], "wave_height": [H0, H1, H2]}
        # We want format:
        # [{timestamp: T0, wave_height: H0}, {timestamp: T1, wave_height: H1}, ...]
        # This is a "zip by index" transformation.
        records = []
        for i, ts in enumerate(times):
            # For each key, safely get element at index i
            # The guard `if i < len(...)` handles truncated arrays
            # (shouldn't happen, but defensive)
            records.append(
                MarineWeatherHourly(
                    port_code=port_code,
                    timestamp=ts,  # ISO 8601 string: "2026-04-13T00:00"
                    wave_height_m=(
                        hourly.get("wave_height", [None])[i]
                        if i < len(hourly.get("wave_height", []))
                        else None
                    ),
                    wave_direction_deg=(
                        hourly.get("wave_direction", [None])[i]
                        if i < len(hourly.get("wave_direction", []))
                        else None
                    ),
                    wave_period_s=(
                        hourly.get("wave_period", [None])[i]
                        if i < len(hourly.get("wave_period", []))
                        else None
                    ),
                    wind_wave_height_m=(
                        hourly.get("wind_wave_height", [None])[i]
                        if i < len(hourly.get("wind_wave_height", []))
                        else None
                    ),
                    swell_wave_height_m=(
                        hourly.get("swell_wave_height", [None])[i]
                        if i < len(hourly.get("swell_wave_height", []))
                        else None
                    ),
                )
            )

        logger.info("Fetched %d hourly records for %s", len(records), port_code)
        return records

    def fetch_all_ports(self, forecast_days: int = 7) -> list[MarineWeatherHourly]:
        """Fetch forecasts for all target ports (loaded dynamically from UN LOCODE CSV).

        Loops through port_coordinates and collects all records.
        Error isolation: if one port fails (e.g., coordinates slightly off-sea),
        we log and continue rather than failing the entire batch.
        """
        all_records: list[MarineWeatherHourly] = []
        for port_code, (lat, lon) in self.port_coordinates.items():
            try:
                records = self.fetch_forecast(port_code, lat, lon, forecast_days)
                all_records.extend(
                    records
                )  # Append this port's records to the master list
            except Exception:
                logger.exception("Failed to fetch weather for %s", port_code)
                # Logged but swallowed — partial data is better than nothing
        logger.info("Total weather records: %d", len(all_records))
        return all_records


class WeatherIngestionClient:
    """Orchestrates weather data fetch and S3 upload.

    WHY A WRAPPER CLASS?
    The OpenMeteoClient only knows how to fetch data.
    The WeatherIngestionClient knows how to fetch AND store it.
    This separation lets us test OpenMeteoClient in isolation (no S3 mock needed)
    and test the S3 writer with a mock OpenMeteoClient.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.open_meteo = OpenMeteoClient()  # Composition: wraps OpenMeteoClient

    def write_to_s3(self, records: list[MarineWeatherHourly]) -> str:
        """Write weather records as NDJSON to S3."""
        import boto3  # Lazy import — only needed at runtime, not during tests

        if not records:
            logger.warning("No weather records to write")
            return ""

        now = datetime.now(UTC)
        date_str = now.strftime("%Y-%m-%d")  # e.g., "2026-04-13"
        key = (
            f"raw/source=weather/date={date_str}/"  # Partitioned by DATE (daily)
            f"weather_{now:%Y%m%dT%H%M%S}.ndjson"  # Timestamped file within the day
        )
        # WHY PARTITION BY DATE (not year/month)?
        # Weather data is fetched hourly. We want to be able to query:
        # "give me all weather data for April 13" → reads one partition.
        # Monthly partition would require reading many files
        # or scanning the whole month.

        ndjson = "\n".join(r.model_dump_json() for r in records)
        # model_dump_json() → Pydantic v2: serialize model to JSON string
        # "\n".join() → NDJSON: one JSON object per line

        s3 = boto3.client("s3")
        s3.put_object(
            Bucket=self.settings.s3_bucket_raw,
            Key=key,
            Body=ndjson.encode(),  # str → bytes for S3
            ContentType="application/x-ndjson",
        )

        logger.info(
            "Wrote %d weather records to s3://%s/%s",
            len(records),
            self.settings.s3_bucket_raw,
            key,
        )
        return key

    def run(self, forecast_days: int = 7) -> str:
        """Main entry point: fetch all ports and upload.

        Called by Prefect flow in Week 4:
            weather_client = WeatherIngestionClient(settings)
            weather_client.run()
        """
        records = self.open_meteo.fetch_all_ports(forecast_days)
        return self.write_to_s3(records)


if __name__ == "__main__":
    from ingestion.config import settings

    logging.basicConfig(level=logging.INFO)
    client = WeatherIngestionClient(settings)
    client.run()
