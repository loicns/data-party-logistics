"""CMA-CGM carrier adapter — fetches vessel ETAs from apis.cma-cgm.com.

API OVERVIEW:
    Product:  CMA-CGM Vessel Tracking API
    Base URL: https://apis.cma-cgm.com/operational/vesseltracking/v2
    Auth:     OAuth2 Bearer token — POST /oauth/token to get a short-lived token,
              then pass it as: Authorization: Bearer {token}
    Rate limit: generous on the free developer tier (as of 2026)
    Docs:     https://developer.cma-cgm.com

    Endpoint used:
        GET /vessels/{imo}/tracking
        Returns the ETA and voyage details for a vessel by IMO number.

NOTE ON KEEPING THIS SEPARATE FROM MaerskAdapter:
    Even though this adapter looks very similar to MaerskAdapter, do NOT
    refactor them into a shared RestCarrierAdapter base class. The response
    schemas and auth patterns will diverge as the APIs evolve — CMA-CGM's
    OAuth token refresh logic and Maersk's Consumer-Key rotation are already
    different operational concerns. Keeping them in separate files means
    Maersk changes don't risk breaking CMA-CGM and vice versa. The duplication
    is deliberate. Prefer duplication over the wrong abstraction.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
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

logger = logging.getLogger(__name__)  # "ingestion.clients.carriers.cma_cgm"


# ─── Response schema ─────────────────────────────────────────────────────────


class CMACGMPortCall(BaseModel):
    """Nested model for the vessel's next port call within the tracking response."""

    port_code: str | None = Field(alias="portCode", default=None)
    port_name: str | None = Field(alias="portName", default=None)
    estimated_arrival: str | None = Field(alias="estimatedArrival", default=None)
    # CMA-CGM uses "estimatedArrival" where Maersk uses
    # "estimatedTimeOfArrival".
    # This naming difference is exactly why each adapter has its own Pydantic model —
    # a shared model would otherwise need carrier-specific optional fields.

    model_config = {"populate_by_name": True}


class CMACGMTrackResponse(BaseModel):
    """Top-level response from GET /vessels/{imo}/tracking."""

    imo_number: str | None = Field(alias="imoNumber", default=None)
    vessel_name: str | None = Field(alias="vesselName", default=None)
    service_code: str | None = Field(alias="serviceCode", default=None)
    next_port_call: CMACGMPortCall | None = Field(alias="nextPortCall", default=None)
    # CMA-CGM nests the ETA one level deeper (nextPortCall.estimatedArrival)
    # compared to Maersk's flat estimatedTimeOfArrival.
    # Neither structure is "better" — they just require different parsing logic.

    model_config = {"populate_by_name": True}


# ─── Cache (same pattern as MaerskAdapter) ────────────────────────────────────
_eta_cache: dict[str, tuple[VesselETA, datetime]] = {}
CACHE_TTL_SEC = 900  # 15 minutes — same TTL as Maersk for consistency


class CMACGMAdapter(CarrierAdapter):
    """Carrier adapter for CMA-CGM's Vessel Tracking API.

    KEY DIFFERENCE FROM MaerskAdapter — OAuth token lifecycle:
        CMA-CGM uses OAuth2 client credentials flow. The token is short-lived
        (expires_in is returned in the token response — typically 3600s = 1 hour).
        We store the token and its expiry time on the instance and refresh only
        when it has expired. This avoids requesting a new token on every API call,
        which would be wasteful and would quickly exhaust rate limits.

    Usage:
        adapter = CMACGMAdapter(settings)
        eta = await adapter.get_vessel_eta("9780700")
    """

    BASE_URL = "https://apis.cma-cgm.com/operational/vesseltracking/v2"
    TOKEN_URL = "https://apis.cma-cgm.com/oauth/token"
    CARRIER = "cma-cgm"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._access_token: str | None = None
        self._token_expires_at: datetime = datetime.now(UTC)
        # Initialise to utcnow() so the first call always triggers a token fetch.
        self.client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            timeout=20,
            # NOTE: No static headers here — the Authorization header is added
            # dynamically in _get_auth_headers() after token refresh.
        )

    async def _refresh_token(self) -> None:
        """Fetch a new OAuth2 access token using client credentials flow.

        Raises CarrierAPIError if the token endpoint itself fails.
        This is called lazily — only when the current token is expired.
        """
        async with httpx.AsyncClient() as token_client:
            # WHY a separate AsyncClient (not self.client)?
            # The token endpoint URL (TOKEN_URL) is different from the BASE_URL.
            # Using a separate short-lived client avoids messing with the base_url
            # of the main client, which is scoped to the tracking API.
            resp = await token_client.post(
                self.TOKEN_URL,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.settings.cmacgm_api_key,
                    "client_secret": "",  # CMA-CGM free tier uses key-only auth
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            if resp.status_code != 200:
                raise CarrierAPIError(
                    carrier=self.CARRIER,
                    status_code=resp.status_code,
                    message=f"OAuth token refresh failed: {resp.text[:200]}",
                )

        token_data = resp.json()
        self._access_token = token_data["access_token"]
        expires_in = token_data.get("expires_in", 3600)
        # Default to 1 hour if the provider omits an expiry.
        self._token_expires_at = datetime.now(UTC) + timedelta(seconds=expires_in - 60)
        # NOTE: We subtract 60 seconds from the TTL as a safety buffer.
        # Refreshing 60 seconds early ensures we never hit the API with an
        # expired token due to clock skew or network latency.

    async def _get_auth_headers(self) -> dict[str, str]:
        """Return the Authorization header with a valid (non-expired) token."""
        if self._access_token is None or datetime.now(UTC) >= self._token_expires_at:
            await self._refresh_token()  # Lazy refresh — only when needed
        return {"Authorization": f"Bearer {self._access_token}"}

    def _get_cached(self, imo: str) -> VesselETA | None:
        """Return cached VesselETA if it exists and is not expired. Otherwise None."""
        if imo not in _eta_cache:
            return None
        cached_eta, cached_at = _eta_cache[imo]
        age_seconds = (datetime.now(UTC) - cached_at).total_seconds()
        if age_seconds > CACHE_TTL_SEC:
            del _eta_cache[imo]
            return None
        return cached_eta

    def _set_cached(self, imo: str, eta: VesselETA) -> None:
        """Store a VesselETA in the cache with the current timestamp."""
        _eta_cache[imo] = (eta, datetime.now(UTC))

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=2, max=30),
        retry=retry_if_exception_type(httpx.HTTPStatusError),
        reraise=True,
    )
    async def _fetch_raw(self, imo: str) -> httpx.Response:
        """Make the raw HTTP request to CMA-CGM's tracking endpoint."""
        auth_headers = await self._get_auth_headers()
        # NOTE: We refresh the token inside _fetch_raw (which is wrapped by @retry)
        # so that if a 401 triggers a retry, the next attempt gets a fresh token.
        # If we fetched the token outside the retry loop, we might retry 3 times
        # with the same expired token.
        resp = await self.client.get(
            f"/vessels/{imo}/tracking",
            headers=auth_headers,
        )
        resp.raise_for_status()
        return resp

    async def get_vessel_eta(self, imo: str) -> VesselETA | None:
        """Fetch CMA-CGM's published ETA for a vessel.

        Returns None if the vessel is not in CMA-CGM's system (404).
        Returns cached result if called within 15 minutes of a previous call.
        Raises CarrierAPIError if the API fails after 3 retry attempts.
        """
        # ── Cache check ──────────────────────────────────────────────────────
        cached = self._get_cached(imo)
        if cached is not None:
            cached.confidence = Confidence.CACHED
            logger.debug("cmacgm_cache_hit", extra={"imo": imo})
            return cached

        # ── API call ──────────────────────────────────────────────────────────
        try:
            resp = await self._fetch_raw(imo)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                logger.info("cmacgm_vessel_not_found", extra={"imo": imo})
                return None
            raise CarrierAPIError(
                carrier=self.CARRIER,
                status_code=exc.response.status_code,
                message=exc.response.text[:200],
            ) from exc

        # ── Parse and validate ────────────────────────────────────────────────
        parsed = CMACGMTrackResponse.model_validate(resp.json())

        if (
            parsed.next_port_call is None
            or parsed.next_port_call.estimated_arrival is None
        ):
            # CMA-CGM found the vessel but no ETA is published yet.
            logger.info("cmacgm_no_eta_published", extra={"imo": imo})
            return None

        eta_dt = datetime.fromisoformat(
            parsed.next_port_call.estimated_arrival.replace("Z", "+00:00")
        )

        vessel_eta = VesselETA(
            imo=imo,
            carrier=self.CARRIER,
            eta=eta_dt,
            confidence=Confidence.API,
            service_name=parsed.service_code or "",
            raw_response=resp.json(),
        )

        # ── Cache result ──────────────────────────────────────────────────────
        self._set_cached(imo, vessel_eta)
        logger.info(
            "cmacgm_fetch_success",
            extra={"imo": imo, "eta": eta_dt.isoformat()},
        )
        return vessel_eta

    async def get_service_schedule(self, service_id: str) -> list[dict]:
        """Fetch CMA-CGM's published schedule for a named service."""
        try:
            auth_headers = await self._get_auth_headers()
            resp = await self.client.get(
                f"/services/{service_id}/schedule",
                headers=auth_headers,
            )
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return []
            raise CarrierAPIError(
                carrier=self.CARRIER,
                status_code=exc.response.status_code,
                message=exc.response.text[:200],
            ) from exc

        return cast(list[dict], resp.json().get("schedule", []))
