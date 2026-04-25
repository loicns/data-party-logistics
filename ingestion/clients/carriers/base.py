"""Carrier adapter base — defines the contract every carrier adapter must honor.

ARCHITECTURE ROLE:
    The adapter pattern isolates carrier-specific logic (auth, response format,
    error codes) behind a single interface. The FastAPI handler (Week 7) calls
    adapter.get_vessel_eta(imo) without knowing which carrier it's talking to.
    Adding a new carrier = one new file in this package. No other file changes.

    Carrier landscape:
        Maersk      — Free REST API (api.maersk.com), confidence='api'
        CMA-CGM     — Free REST API (developer portal), confidence='api'
        MSC         — No API, Playwright scraping (see 05-scraping-layer.md)
        Hapag-Lloyd — API requires business account (NullAdapter until granted)
        COSCO       — No public API (NullAdapter + scraping)
        Evergreen   — No public API (NullAdapter)
"""

from __future__ import annotations  # Enables `int | None` syntax on Python 3.9

from abc import ABC, abstractmethod  # ABC = Abstract Base Class machinery
from dataclasses import dataclass, field  # Lightweight data containers
from datetime import UTC, datetime
from enum import StrEnum  # Enum enforces a closed set of allowed values

import structlog


class Confidence(StrEnum):
    """How trustworthy is this ETA estimate?

    Inheriting from str makes the enum JSON-serialisable without extra steps:
        json.dumps({"confidence": Confidence.API})   → '{"confidence": "api"}'
    Without `str`, json.dumps would raise TypeError on the enum member.
    """

    API = "api"  # Authoritative — from a carrier's official REST API
    SCRAPED = "scraped"  # Fragile — from Playwright browser scraping
    CACHED = "cached"  # Stale — from cache; source may be api or scraped
    ERROR = "error"  # Adapter failed — no data available


@dataclass
class VesselETA:
    """A carrier's ETA estimate for a vessel.

    The `confidence` field is the single most important field for downstream use:
    - The delay predictor model weights 'api' ETAs more heavily than 'scraped'
    - The dashboard shows "MSC ETA: Apr 18 (⚠ scraped — lower confidence)"
    - The reliability scorer only uses 'api' and 'scraped' ETAs, not 'cached'

    WHY DATACLASS OVER PYDANTIC HERE?
    VesselETA is an internal result object, not an API boundary.
    Pydantic's validation cost (field coercion, schema generation) is wasted
    when the data was already validated by the adapter's own Pydantic response model
    (MaerskTrackResponse, CMACGMTrackResponse). Dataclass is faster and simpler
    for pure data containers that don't cross an untrusted boundary.
    """

    # IMO number — globally unique vessel identifier (e.g. "9703291")
    imo: str
    # Carrier name — matches the adapter (e.g. "maersk", "cma-cgm")
    carrier: str
    # Carrier's published ETA at the next port
    eta: datetime
    # How trustworthy is this estimate (see enum above)
    confidence: Confidence
    fetched_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    # default_factory means each VesselETA gets its own creation timestamp.
    # Without default_factory, all instances would share the same frozen datetime.
    # e.g. "AE7" — carrier's internal service/route name
    service_name: str = ""
    # Original API response for audit trails
    raw_response: dict = field(default_factory=dict)


class CarrierAPIError(Exception):
    """Raised by all adapters on unrecoverable API failure.

    Using a single exception type means callers do:
        except CarrierAPIError as e: log_and_degrade(e)
    instead of catching 5 different carrier-specific exceptions.

    WHY STRUCTURED ATTRIBUTES (not just a message string)?
    The reliability logger (Week 5) needs `status_code` to distinguish
    rate-limit failures (429 → slow down) from auth failures (401 → alert).
    Storing structured data on the exception makes that possible without
    parsing a string message.
    """

    def __init__(
        self,
        carrier: str,
        status_code: int | None = None,
        message: str = "",
    ) -> None:
        self.carrier = carrier  # Which adapter raised this (for log correlation)
        # HTTP status code, if available; None for connection errors
        self.status_code = status_code
        self.message = message  # Human-readable description
        super().__init__(f"[{carrier}] HTTP {status_code}: {message}")
        # NOTE: We still call super().__init__() with a formatted string so that
        # str(exception) and repr(exception) produce readable output in logs.


class CarrierAdapter(ABC):
    """Abstract base for all carrier ETA adapters.

    INTERFACE CONTRACT:
        Every adapter must implement get_vessel_eta() and get_service_schedule().
        The return type `VesselETA | None` means: vessel not found in carrier's system.
        None is NOT an error — it's expected for vessels not in that carrier's fleet.
        CarrierAPIError is an error — it means the API itself failed.

    WHY TWO ABSTRACT METHODS?
        get_vessel_eta() is for the delay prediction use case (Week 5 features).
        get_service_schedule() is for the port congestion use case.
        Every adapter must implement both methods because the Week 4 Prefect
        flow will call get_service_schedule() on all registered adapters.
        The ABC forces you to implement it now, not discover the gap in Week 4.
    """

    @abstractmethod
    async def get_vessel_eta(self, imo: str) -> VesselETA | None:
        """Fetch the carrier's published ETA for a vessel by IMO number.

        Returns None if the vessel is not found in this carrier's system.
        Raises CarrierAPIError if the API itself fails after retries.
        """
        ...

    @abstractmethod
    async def get_service_schedule(self, service_id: str) -> list[dict]:
        """Fetch the published schedule for a named service (e.g. Maersk AE7).

        Returns a list of port calls with ETD/ETA per port.
        Returns empty list if service not found.
        """
        ...


class NullAdapter(CarrierAdapter):
    """Placeholder for carriers without API access.

    Used for: Hapag-Lloyd (business account required), Evergreen (no API).
    Always returns None — signals 'no data' without raising errors.
    Logs the reason so the dashboard can show 'Carrier data unavailable'.

    WHY NOT JUST RAISE NotImplementedError?
        NotImplementedError would crash the Week 7 fan-out loop for every vessel lookup.
        NullAdapter fails softly — the loop continues with data from the other carriers.
        This is the "fail small, continue big" principle: one missing carrier
        should not prevent the system from returning data from the other four.
    """

    def __init__(self, carrier_name: str, reason: str) -> None:
        self.carrier_name = carrier_name  # e.g. "hapag-lloyd"
        self.reason = reason  # e.g. "business account required — pending approval"

    async def get_vessel_eta(self, imo: str) -> VesselETA | None:
        structlog.get_logger(__name__).info(
            "null_adapter_called",
            carrier=self.carrier_name,
            reason=self.reason,
            imo=imo,
        )
        # NOTE: structlog's key=value style produces machine-parseable logs that
        # Datadog / CloudWatch Insights can filter on:  carrier="hapag-lloyd"
        # compared to f"Hapag-Lloyd null adapter called for IMO {imo}" — unqueryable.
        return None

    async def get_service_schedule(self, service_id: str) -> list[dict]:
        # Empty list means "no schedule data for this carrier."
        return []
