"""NOAA CO-OPS tidal predictions ingestion client.

Fetches Hi/Lo tidal predictions for US destination ports from the NOAA
Tides & Currents public API (no API key required). Validates with Pydantic
and writes NDJSON batches to S3.

API: https://api.tidesandcurrents.noaa.gov/api/prod/datagetter
Docs: https://api.tidesandcurrents.noaa.gov/api/prod/

ARCHITECTURE ROLE:
    Only US ports have NOAA stations. Non-US ports produce null for the
    hours_to_next_high_tide feature — handled by LightGBM native null support.
    Output: raw/source=noaa_tides/date=YYYY-MM-DD/batch-TIMESTAMP.ndjson
    Consumer: features/port_features.py (Week 5) → hours_to_next_high_tide

Usage:
    uv run python -m ingestion.clients.noaa_tides
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import httpx
import structlog
from pydantic import BaseModel, field_validator
from tenacity import retry, stop_after_attempt, wait_exponential

from ingestion.s3_writer import write_ndjson_batch

logger = structlog.get_logger(__name__)

NOAA_PORT_STATIONS: dict[str, str] = {
    "USLAX": "9410660",
    "USLGB": "9410660",
    "USNYC": "8518750",
    "USFPG": "8452660",
}

API_BASE = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
SOURCE_NAME = "noaa_tides"


class TidalEvent(BaseModel):
    """A single Hi/Lo tidal event prediction for one port.

    NOAA CO-OPS returns predictions in the form:
        {"t": "2026-04-13 06:23", "v": "1.234", "type": "H"}

    FIELD NOTE ON tide_level_m:
        NOAA returns tide height relative to MLLW (Mean Lower Low Water) datum.
        Positive = above MLLW, negative values are possible during low spring tides.
        We store the raw MLLW-relative value — no datum conversion.
        dbt models in Week 3 document the datum in column metadata.
    """

    port_code: str
    station_id: str
    timestamp: str
    tide_level_m: float
    tide_type: str

    @field_validator("tide_type")
    @classmethod
    def validate_tide_type(cls, v: str) -> str:
        """Ensure tide_type is exactly "H" or "L"."""
        if v not in ("H", "L"):
            raise ValueError(f"tide_type must be 'H' or 'L', got '{v}'")
        return v


class NOAATidesClient:
    """Fetches Hi/Lo tidal predictions from NOAA CO-OPS.

    API product used: `predictions` with `interval=hilo`
        - Returns only High/Low water events (not hourly values)
        - Typically 3-4 events per day per station (semi-diurnal tides)
        - For 7 days, expect 21-28 records per station
    """

    def __init__(self, http_timeout: int = 15) -> None:
        self.client = httpx.Client(timeout=http_timeout)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def fetch_predictions(
        self,
        port_code: str,
        days_ahead: int = 7,
    ) -> list[TidalEvent]:
        """Fetch Hi/Lo tidal predictions for one port.

        Args:
            port_code:  UN LOCODE (e.g., "USNYC"). Must be in NOAA_PORT_STATIONS.
            days_ahead: Number of days to fetch predictions for (default 7).
                        NOAA supports up to ~365 days ahead for predictions.

        Returns:
            List of TidalEvent objects, one per Hi/Lo event.
            Returns empty list if port_code is not in NOAA_PORT_STATIONS.
        """
        station_id = NOAA_PORT_STATIONS.get(port_code)
        if not station_id:
            logger.debug(
                "noaa_station_not_found",
                port_code=port_code,
                note="non-US port — tidal feature will be null in ML model",
            )
            return []

        today = datetime.now(UTC).date()
        end_date = today + timedelta(days=days_ahead)

        params = {
            "station": station_id,
            "product": "predictions",
            "interval": "hilo",
            "datum": "MLLW",
            "time_zone": "GMT",
            "units": "metric",
            "format": "json",
            "begin_date": today.strftime("%Y%m%d"),
            "end_date": end_date.strftime("%Y%m%d"),
        }

        logger.info(
            "noaa_fetch_start",
            port_code=port_code,
            station_id=station_id,
            begin_date=params["begin_date"],
            end_date=params["end_date"],
        )

        resp = self.client.get(API_BASE, params=params)
        resp.raise_for_status()
        data = resp.json()

        if "error" in data:
            raise ValueError(
                f"NOAA API error for station {station_id}: "
                f"{data['error'].get('message', data)}"
            )

        predictions = data.get("predictions", [])

        records: list[TidalEvent] = []
        for pred in predictions:
            try:
                # Parse NOAA datetime format "YYYY-MM-DD HH:MM" → ISO 8601 with seconds
                # NOAA returns a space-separated datetime, not ISO 8601
                ts_raw = pred.get("t", "")
                ts_dt = datetime.strptime(ts_raw, "%Y-%m-%d %H:%M")
                ts_iso = ts_dt.strftime(
                    "%Y-%m-%dT%H:%M:%S"
                )  # e.g., "2026-04-13T06:23:00"

                record = TidalEvent(
                    port_code=port_code,
                    station_id=station_id,
                    timestamp=ts_iso,
                    tide_level_m=float(
                        pred.get("v", 0)
                    ),  # "v" is the water level value
                    tide_type=pred.get("type", ""),  # "H" or "L"
                )
                records.append(record)
            except Exception:
                logger.exception(
                    "noaa_record_parse_error",
                    port_code=port_code,
                    raw_prediction=pred,
                )
                continue

        logger.info(
            "noaa_fetch_complete",
            port_code=port_code,
            station_id=station_id,
            record_count=len(records),
        )
        return records

    def fetch_all_ports(self, days_ahead: int = 7) -> list[TidalEvent]:
        """Fetch tidal predictions for all ports in NOAA_PORT_STATIONS.

        For 4 US ports x 28 events/port = ~112 records per run.
        """
        all_records: list[TidalEvent] = []
        for port_code in NOAA_PORT_STATIONS:
            try:
                records = self.fetch_predictions(port_code, days_ahead)
                all_records.extend(records)
            except Exception:
                logger.exception("noaa_port_fetch_failed", port_code=port_code)
                continue
        logger.info("noaa_all_ports_done", total_records=len(all_records))
        return all_records


class NOAAIngestionClient:
    """Orchestrates NOAA tidal prediction fetch and S3 upload."""

    def __init__(self) -> None:
        self.noaa = NOAATidesClient()

    def run(self, days_ahead: int = 7) -> str:
        """Fetch all US port tidal predictions and write NDJSON to S3.

        Returns the S3 key of the written file, or "" if no records fetched.
        """
        records = self.noaa.fetch_all_ports(days_ahead)

        if not records:
            logger.warning("noaa_no_records", action="skipping_s3_write")
            return ""

        dicts = [r.model_dump() for r in records]
        key = write_ndjson_batch(dicts, source=SOURCE_NAME)
        logger.info("noaa_run_complete", s3_key=key, record_count=len(records))
        return key


# Entrypoint
def main() -> None:
    """Run NOAA tidal predictions ingestion once and exit.

    Usage: uv run python -m ingestion.clients.noaa_tides
    """
    logger.info(
        "noaa_ingestion_starting",
        stations=len(NOAA_PORT_STATIONS),
        ports=list(NOAA_PORT_STATIONS.keys()),
    )
    client = NOAAIngestionClient()
    key = client.run()
    logger.info("noaa_ingestion_done", s3_key=key)


if __name__ == "__main__":
    main()
