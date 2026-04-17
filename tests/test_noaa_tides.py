"""Tests for NOAA tidal predictions ingestion client.

Run: uv run pytest tests/test_noaa_tides.py -v
"""

from unittest.mock import MagicMock

import pytest
from ingestion.clients.noaa_tides import (
    NOAA_PORT_STATIONS,
    NOAATidesClient,
    TidalEvent,
)
from pydantic import ValidationError


def test_tidal_event_high_water():
    """TidalEvent stores a High water event correctly."""
    event = TidalEvent(
        port_code="USNYC",
        station_id="8518750",
        timestamp="2026-04-13T06:23:00",
        tide_level_m=1.45,
        tide_type="H",
    )
    assert event.port_code == "USNYC"
    assert event.tide_level_m == 1.45
    assert event.tide_type == "H"


def test_tidal_event_low_water():
    """TidalEvent stores a Low water event correctly."""
    event = TidalEvent(
        port_code="USLAX",
        station_id="9410660",
        timestamp="2026-04-13T12:45:00",
        tide_level_m=0.12,
        tide_type="L",
    )
    assert event.tide_type == "L"
    assert event.tide_level_m == 0.12


def test_tidal_event_negative_tide_level():
    """TidalEvent accepts negative tide levels (below MLLW datum)."""
    event = TidalEvent(
        port_code="USNYC",
        station_id="8518750",
        timestamp="2026-04-13T00:00:00",
        tide_level_m=-0.08,  # Negative: valid below-MLLW reading
        tide_type="L",
    )
    assert event.tide_level_m == -0.08


def test_tidal_event_invalid_tide_type():
    """TidalEvent rejects invalid tide_type values."""
    with pytest.raises(ValidationError):
        TidalEvent(
            port_code="USNYC",
            station_id="8518750",
            timestamp="2026-04-13T00:00:00",
            tide_level_m=1.2,
            tide_type="HH",  # Invalid — only "H" or "L" allowed
        )


def test_tidal_event_empty_tide_type():
    """TidalEvent rejects an empty tide_type string."""
    with pytest.raises(ValidationError):
        TidalEvent(
            port_code="USNYC",
            station_id="8518750",
            timestamp="2026-04-13T00:00:00",
            tide_level_m=1.2,
            tide_type="",  # Invalid — empty string
        )


def test_noaa_port_stations_defined():
    """NOAA_PORT_STATIONS has the expected US ports."""
    assert "USLAX" in NOAA_PORT_STATIONS
    assert "USNYC" in NOAA_PORT_STATIONS
    assert "USLGB" in NOAA_PORT_STATIONS
    assert "USFPG" in NOAA_PORT_STATIONS
    # Verify international ports are NOT in the map — intentional exclusion
    assert "NLRTM" not in NOAA_PORT_STATIONS
    assert "CNSHA" not in NOAA_PORT_STATIONS


def test_station_ids_are_numeric_strings():
    """All NOAA station IDs are non-empty numeric strings."""
    for port, station_id in NOAA_PORT_STATIONS.items():
        assert station_id.isdigit(), f"{port}: station ID '{station_id}' is not numeric"
        assert len(station_id) >= 6, f"{port}: station ID '{station_id}' is too short"


def test_fetch_predictions_parses_noaa_response():
    """NOAATidesClient parses a sample NOAA JSON response correctly."""
    sample_response = {
        "predictions": [
            {"t": "2026-04-13 06:23", "v": "1.456", "type": "H"},  # High water
            {"t": "2026-04-13 12:45", "v": "0.089", "type": "L"},  # Low water
            {"t": "2026-04-13 18:52", "v": "1.312", "type": "H"},  # High water
        ]
    }

    mock_resp = MagicMock()
    mock_resp.json.return_value = sample_response
    mock_resp.raise_for_status = MagicMock()  # Don't raise; simulate HTTP 200

    mock_http_client = MagicMock()
    mock_http_client.get.return_value = mock_resp

    client = NOAATidesClient()
    client.client = mock_http_client  # Inject mock — no real HTTP call made

    events = client.fetch_predictions("USNYC", days_ahead=7)

    assert len(events) == 3  # All 3 predictions parsed

    assert events[0].tide_type == "H"
    assert events[0].tide_level_m == 1.456
    assert events[0].timestamp == "2026-04-13T06:23:00"  # Normalised to ISO 8601
    assert events[0].port_code == "USNYC"
    assert events[0].station_id == "8518750"

    assert events[1].tide_type == "L"
    assert events[1].tide_level_m == 0.089

    assert events[2].tide_type == "H"
    assert events[2].tide_level_m == 1.312


def test_fetch_predictions_returns_empty_for_unknown_port():
    """NOAATidesClient returns [] for ports not in NOAA_PORT_STATIONS."""
    client = NOAATidesClient()
    events = client.fetch_predictions("NLRTM", days_ahead=7)

    assert events == []  # Non-US port → empty list, not an error


def test_fetch_predictions_handles_noaa_error_envelope():
    """NOAATidesClient raises ValueError on NOAA error body (HTTP 200 + error JSON)."""
    error_response = {
        "error": {
            "message": (
                "No data was found. This product may not be offered at this station."
            )
        }
    }

    mock_resp = MagicMock()
    mock_resp.json.return_value = error_response
    mock_resp.raise_for_status = MagicMock()

    mock_http_client = MagicMock()
    mock_http_client.get.return_value = mock_resp

    client = NOAATidesClient()
    client.client = mock_http_client

    with pytest.raises(ValueError, match="NOAA API error"):
        client.fetch_predictions("USNYC", days_ahead=7)
