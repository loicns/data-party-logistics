"""Maersk carrier adapter — fetches vessel ETAs from api.maersk.com.

API OVERVIEW:
    Product:  Maersk Track & Trace (Synergy)
    Base URL: https://api.maersk.com/synergy/tracking/v1
    Auth:     Consumer-Key header (from api.maersk.com developer dashboard)
    Rate limit: ~100 req/day on the free tier (as of 2026)
    Docs:     https://developer.maersk.com/api-catalogue

    Endpoint used:
        GET /track/{imo}
        Returns the ETA and current position for a vessel by IMO number.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import cast

import httpx
from pydantic import BaseModel, Field
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from ingestion.config import Settings

from .base import CarrierAdapter, CarrierAPIError, Confidence, VesselETA

# NOTE: Relative import (from .base) keeps this file portable.

logger = logging.getLogger(__name__)  # "ingestion.clients.carriers.maersk"


# ─── Response schema ─────────────────────────────────────────────────────────


class MaerskVesselPosition(BaseModel):
    """Nested model for the vessel's current position within the tracking response."""

    latitude: float | None = None
    longitude: float | None = None
    vessel_name: str | None = Field(alias="vesselName", default=None)

    model_config = {"populate_by_name": True}
    # populate_by_name=True: allows using both Python names and aliases when
    # constructing the model. Without this, only the alias works in model_validate().


class MaerskTrackResponse(BaseModel):
    """Top-level response from GET /track/{imo}.

    Only the fields we use are declared here. Pydantic ignores extra fields
    in the response by default — we don't need to model every field Maersk returns.
    """

    # IMO number, echoed back by the API
    imo: str
    estimated_time_of_arrival: str | None = Field(
        alias="estimatedTimeOfArrival", default=None
    )
    # NOTE: Maersk returns datetime as an ISO 8601 string, not a Python datetime.
    # We parse it manually in the adapter rather than using Pydantic's datetime type
    # because Maersk sometimes omits timezone info — and Pydantic would raise on that.
    service_name: str | None = Field(alias="serviceName", default=None)
    # e.g. "AE7/AEX" — the liner service this vessel is operating on
    vessel_position: MaerskVesselPosition | None = Field(
        alias="vesselPosition", default=None
    )

    model_config = {"populate_by_name": True}


# ─── Cache ────────────────────────────────────────────────────────────────────
# Simple in-memory cache — keyed by IMO number.
# TTL 15 minutes: Maersk ETAs don't change minute-to-minute but the free-tier
# rate limit is 100 req/day (~4/hour). Without caching, a busy development
# session (re-running tests, trying the live endpoint) eats the daily quota.
# In production Week 7 this would be Redis, but a dict works for development.

_eta_cache: dict[str, tuple[VesselETA, datetime]] = {}
# Key:   IMO number (str)
# Value: (VesselETA result, datetime when it was cached)
# dict is module-level so it persists across adapter instances within one process.

CACHE_TTL_SEC = 900  # 15 minutes — matches the granularity of Maersk's ETA updates


class MaerskAdapter(CarrierAdapter):
    """Carrier adapter for Maersk's Synergy Track & Trace API.

    Usage:
        adapter = MaerskAdapter(settings)
        eta = await adapter.get_vessel_eta("9703291")
        if eta:
            print(eta.eta, eta.confidence)   # datetime, Confidence.API
    """

    BASE_URL = "https://api.maersk.com/synergy/tracking/v1"
    CARRIER = "maersk"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers={
                "Consumer-Key": settings.maersk_api_key,
                # NOTE: Header name is "Consumer-Key" not "Authorization" — Maersk's
                # developer portal uses a non-standard header. Exact name matters;
                # "consumer-key" (lowercase) will be rejected with 401.
                "Accept": "application/json",
            },
            timeout=20,  # 20s: Maersk's API is fast; 20s is generous for CI
        )

    def _get_cached(self, imo: str) -> VesselETA | None:
        """Return cached VesselETA if it exists and is not expired. Otherwise None."""
        if imo not in _eta_cache:
            return None
        cached_eta, cached_at = _eta_cache[imo]
        age_seconds = (datetime.now(UTC) - cached_at).total_seconds()
        if age_seconds > CACHE_TTL_SEC:
            del _eta_cache[imo]  # Evict expired entry — prevents unbounded dict growth
            return None
        return cached_eta

    def _set_cached(self, imo: str, eta: VesselETA) -> None:
        """Store a VesselETA in the cache with the current timestamp."""
        _eta_cache[imo] = (eta, datetime.now(UTC))

    @retry(
        # Max 3 total attempts (1 original + 2 retries)
        stop=stop_after_attempt(3),
        wait=wait_exponential(
            multiplier=2,  # Wait = 2 * 2^attempt seconds
            min=2,  # Minimum wait: 2 seconds
            max=30,  # Maximum wait: 30 seconds cap
        ),
        retry=retry_if_exception_type(httpx.HTTPStatusError),
        reraise=True,
        # WHY ONLY HTTPStatusError?
        # We only retry transient failures (429 rate limit, 503 server busy).
        # We do NOT retry on httpx.ConnectError — if DNS/network is broken,
        # retrying immediately won't help and wastes the rate limit budget.
        # 401/403 auth failures will also be retried, which is slightly wasteful,
        # but they always exhaust all 3 attempts and raise CarrierAPIError clearly.
    )
    async def _fetch_raw(self, imo: str) -> httpx.Response:
        """Make the raw HTTP request to Maersk's tracking endpoint.

        Separated from get_vessel_eta() so the @retry decorator only wraps
        the network call — not the response parsing. A ValidationError in parsing
        should NOT be retried; only HTTP failures should.
        """
        logger.info("maersk_fetch_start", extra={"imo": imo})
        resp = await self.client.get(f"/track/{imo}")
        resp.raise_for_status()
        # raise_for_status() is what makes @retry trigger on 429/503.
        # Without it, a 429 response would be returned silently and parsed as
        # if it were valid data — producing a confusing ValidationError.
        return resp

    async def get_vessel_eta(self, imo: str) -> VesselETA | None:
        """Fetch Maersk's published ETA for a vessel.

        Returns None if the vessel is not in Maersk's fleet tracking system (404).
        Returns cached VesselETA if called within 15 minutes of a
        previous successful call.
        Raises CarrierAPIError if the API fails after 3 retry attempts.
        """
        # ── Cache check ──────────────────────────────────────────────────────
        cached = self._get_cached(imo)
        if cached is not None:
            logger.debug(
                "maersk_cache_hit",
                extra={"imo": imo, "confidence": Confidence.CACHED.value},
            )
            cached.confidence = Confidence.CACHED
            # NOTE: We downgrade confidence to CACHED on a cache hit.
            # The underlying data came from the API, but it is now stale.
            # Downstream consumers (the reliability scorer) only use CACHED
            # ETAs for dashboard display — not for model training features.
            return cached

        # ── API call ──────────────────────────────────────────────────────────
        try:
            resp = await self._fetch_raw(imo)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                # 404 = vessel not in Maersk's tracking system.
                # This is expected for vessels operated by other carriers.
                # Return None rather than raising — None means "no data", not "error".
                logger.info("maersk_vessel_not_found", extra={"imo": imo})
                return None
            # All other status codes become CarrierAPIError.
            raise CarrierAPIError(
                carrier=self.CARRIER,
                status_code=exc.response.status_code,
                # Truncate because error bodies can be verbose.
                message=exc.response.text[:200],
            ) from exc

        # ── Parse and validate ────────────────────────────────────────────────
        parsed = MaerskTrackResponse.model_validate(resp.json())
        # model_validate() raises ValidationError if the response shape has changed.
        # This surfaces immediately as a noisy failure in CI — far better than
        # silently producing None ETAs because a field was renamed.

        if parsed.estimated_time_of_arrival is None:
            # Vessel found in Maersk's system, but no ETA published yet.
            # This happens for vessels in port or far from their next port call.
            logger.info("maersk_no_eta_published", extra={"imo": imo})
            return None

        eta_dt = datetime.fromisoformat(
            parsed.estimated_time_of_arrival.replace("Z", "+00:00")
        )
        # NOTE: Python's fromisoformat() does not parse "Z" as UTC before 3.11.
        # The replace() call is the standard compatibility shim — it costs nothing.

        vessel_eta = VesselETA(
            imo=imo,
            carrier=self.CARRIER,
            eta=eta_dt,
            confidence=Confidence.API,  # Official REST API response
            service_name=parsed.service_name or "",
            raw_response=resp.json(),  # Full response stored for audit
        )

        # ── Cache result ──────────────────────────────────────────────────────
        self._set_cached(imo, vessel_eta)

        logger.info(
            "maersk_fetch_success",
            extra={
                "imo": imo,
                "eta": eta_dt.isoformat(),
                "service": vessel_eta.service_name,
            },
        )
        return vessel_eta

    async def get_service_schedule(self, service_id: str) -> list[dict]:
        """Fetch Maersk's published port-call schedule for a named service.

        service_id: Maersk service code, e.g. "AE7" or "AEX"
        Returns a list of port-call dicts with keys: port, eta, etd, terminal.
        Returns empty list if the service is not found.
        """
        try:
            resp = await self.client.get(f"/schedules/{service_id}")
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return []  # Unknown service — not an error
            raise CarrierAPIError(
                carrier=self.CARRIER,
                status_code=exc.response.status_code,
                message=exc.response.text[:200],
            ) from exc

        return cast(list[dict], resp.json().get("portCalls", []))
        # WHY .get("portCalls", [])?
        # If the key is missing (schema change), we return an empty list rather
        # than raising KeyError. The caller interprets empty list as "no schedule"
        # and moves on. A KeyError here would crash the Week 4 Prefect flow for
        # an entire service loop — empty list keeps the flow running.
