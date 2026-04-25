"""Tests for carrier adapter layer — base, Maersk, and CMA-CGM adapters."""

import asyncio
import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from ingestion.clients.carriers.base import (
    CarrierAPIError,
    Confidence,
    NullAdapter,
    VesselETA,
)
from ingestion.clients.carriers.maersk import (
    MaerskAdapter,
    MaerskTrackResponse,
    _eta_cache,
)
from ingestion.config import Settings

# ─── Helpers ──────────────────────────────────────────────────────────────────


def _make_settings() -> Settings:
    """Create a Settings object with fake credentials for tests.

    Real API keys must never appear in test code — this ensures:
    1. Tests can run in CI without secrets configured
    2. Tests never accidentally make real API calls (rate limit / side effects)
    3. Test results are always reproducible
    """
    return Settings(
        aisstream_api_key="fake",
        fred_api_key="fake",
        noaa_api_token="fake",
        s3_bucket_raw="test-bucket",
        maersk_api_key="fake-maersk-key",
        cmacgm_api_key="fake-cmacgm-key",
    )


def _make_maersk_response_json(
    imo: str = "9703291",
    eta: str = "2026-04-20T08:00:00Z",
) -> dict:
    """Return a minimal valid Maersk API response dict for a given vessel."""
    return {
        "imo": imo,
        "estimatedTimeOfArrival": eta,
        "serviceName": "AE7",
        "vesselPosition": {
            "vesselName": "MAERSK EDINBURGH",
            "latitude": 51.9,
            "longitude": 4.1,
        },
    }


# ─── Base / VesselETA tests ───────────────────────────────────────────────────


def test_vessel_eta_creation():
    """VesselETA dataclass creates correctly with all required fields."""
    eta = VesselETA(
        imo="9703291",
        carrier="maersk",
        eta=datetime(2026, 4, 20, 8, 0),
        confidence=Confidence.API,
    )
    assert eta.imo == "9703291"
    assert eta.carrier == "maersk"
    assert eta.confidence == Confidence.API
    assert eta.service_name == ""  # Default — empty string, not None
    assert isinstance(eta.fetched_at, datetime)  # default_factory populated it


def test_vessel_eta_confidence_enum_is_string():
    """Confidence enum members are valid JSON strings (inherits from str)."""
    assert Confidence.API == "api"
    assert Confidence.SCRAPED == "scraped"
    # Verify JSON-serialisable without custom encoder
    assert json.dumps(Confidence.API) == '"api"'


def test_null_adapter_returns_none():
    """NullAdapter.get_vessel_eta() returns None without raising."""
    adapter = NullAdapter(
        carrier_name="hapag-lloyd",
        reason="business account required",
    )
    result = asyncio.run(adapter.get_vessel_eta("9703291"))
    assert result is None


def test_null_adapter_schedule_returns_empty_list():
    """NullAdapter.get_service_schedule() returns empty list without raising."""
    adapter = NullAdapter(carrier_name="evergreen", reason="no public API")
    result = asyncio.run(adapter.get_service_schedule("service-123"))
    assert result == []


# ─── MaerskAdapter tests ──────────────────────────────────────────────────────


def test_maersk_track_response_parsing():
    """MaerskTrackResponse Pydantic model parses aliased fields correctly.

    This tests the SCHEMA CONTRACT — if Maersk renames 'estimatedTimeOfArrival',
    this test fails immediately instead of silently returning None ETAs.
    """
    raw = _make_maersk_response_json()
    parsed = MaerskTrackResponse.model_validate(raw)
    assert parsed.imo == "9703291"
    assert parsed.estimated_time_of_arrival == "2026-04-20T08:00:00Z"
    assert parsed.service_name == "AE7"


@patch("ingestion.clients.carriers.maersk.httpx.AsyncClient")
def test_maersk_adapter_parses_api_response(mock_client_cls):
    """MaerskAdapter.get_vessel_eta() returns a VesselETA with confidence=API.

    Pattern: Arrange → Act → Assert
    Arrange: configure the mock httpx client to return a controlled response
    Act:     call get_vessel_eta()
    Assert:  result is VesselETA with correct fields
    """
    # ── Arrange ──────────────────────────────────────────────────────────────
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = _make_maersk_response_json()
    mock_resp.raise_for_status = MagicMock()  # No-op — simulates 200 OK

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client_cls.return_value = mock_client

    adapter = MaerskAdapter(_make_settings())
    adapter.client = mock_client  # Inject mock directly — bypasses constructor

    # Clear cache to ensure this test doesn't hit a cached value
    _eta_cache.clear()

    # ── Act ───────────────────────────────────────────────────────────────────
    result = asyncio.run(adapter.get_vessel_eta("9703291"))

    # ── Assert ────────────────────────────────────────────────────────────────
    assert result is not None
    assert result.imo == "9703291"
    assert result.carrier == "maersk"
    assert result.confidence == Confidence.API  # Must be API, not CACHED or SCRAPED
    assert result.service_name == "AE7"
    assert isinstance(result.eta, datetime)
    mock_client.get.assert_called_once()  # Exactly one HTTP call was made


@patch("ingestion.clients.carriers.maersk.httpx.AsyncClient")
def test_maersk_adapter_returns_none_on_404(mock_client_cls):
    """MaerskAdapter.get_vessel_eta() returns None when vessel not found (404).

    None is the correct return — 404 means vessel not in Maersk's fleet,
    not an API failure. The caller interprets None as 'try other carriers'.
    """
    import httpx as real_httpx

    mock_resp = MagicMock()
    mock_resp.status_code = 404
    # Construct a real HTTPStatusError so the except block's .status_code check works
    http_error = real_httpx.HTTPStatusError(
        message="Not Found",
        request=MagicMock(),
        response=MagicMock(status_code=404, text="Vessel not found"),
    )
    mock_resp.raise_for_status.side_effect = http_error

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client_cls.return_value = mock_client

    adapter = MaerskAdapter(_make_settings())
    adapter.client = mock_client
    _eta_cache.clear()

    result = asyncio.run(adapter.get_vessel_eta("0000000"))
    assert result is None  # 404 -> None, not CarrierAPIError


@patch("ingestion.clients.carriers.maersk.httpx.AsyncClient")
def test_maersk_adapter_raises_carrier_api_error_on_429(mock_client_cls):
    """MaerskAdapter raises CarrierAPIError after retries are exhausted on 429.

    The @retry decorator will attempt 3 times total, then re-raise.
    We verify the exception type and that it carries the status code.
    """
    import httpx as real_httpx

    http_error = real_httpx.HTTPStatusError(
        message="Too Many Requests",
        request=MagicMock(),
        response=MagicMock(status_code=429, text="Rate limit exceeded"),
    )
    mock_resp = MagicMock()
    mock_resp.raise_for_status.side_effect = http_error

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client_cls.return_value = mock_client

    adapter = MaerskAdapter(_make_settings())
    adapter.client = mock_client
    _eta_cache.clear()

    with pytest.raises(CarrierAPIError) as exc_info:
        asyncio.run(adapter.get_vessel_eta("9703291"))

    assert exc_info.value.carrier == "maersk"
    assert exc_info.value.status_code == 429
    # The @retry decorator will have called mock_client.get 3 times
    assert mock_client.get.call_count == 3


@patch("ingestion.clients.carriers.maersk.httpx.AsyncClient")
def test_maersk_adapter_cache_hit_skips_api(mock_client_cls):
    """Second call within TTL returns cached result without hitting the API.

    This test verifies the cache is working as intended — same IMO, second call,
    zero additional HTTP requests.
    """
    mock_resp = MagicMock()
    mock_resp.json.return_value = _make_maersk_response_json()
    mock_resp.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client_cls.return_value = mock_client

    adapter = MaerskAdapter(_make_settings())
    adapter.client = mock_client
    _eta_cache.clear()

    # First call — should hit the API
    result1 = asyncio.run(adapter.get_vessel_eta("9703291"))
    assert result1 is not None
    assert mock_client.get.call_count == 1  # One real HTTP call

    # Second call — should hit the cache, no additional HTTP call
    result2 = asyncio.run(adapter.get_vessel_eta("9703291"))
    assert result2 is not None
    assert mock_client.get.call_count == 1  # Still exactly one — cache served it
    assert result2.confidence == Confidence.CACHED
