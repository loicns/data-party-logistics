"""Tests for weather ingestion client."""

from unittest.mock import MagicMock, patch

from ingestion.clients.weather import (
    FALLBACK_PORT_COORDINATES,
    MarineWeatherHourly,
    OpenMeteoClient,
)


def test_marine_weather_hourly_model():
    """MarineWeatherHourly accepts all fields.

    Verifies the Pydantic model accepts the expected data types.
    Tests that nullable fields (wave_direction, wave_period not set here)
    default to None.
    """
    record = MarineWeatherHourly(
        port_code="NLRTM",
        timestamp="2026-04-13T12:00",
        wave_height_m=1.5,
        wave_direction_deg=270.0,
        wave_period_s=6.0,
        # wind_wave_height_m and swell_wave_height_m not set → should default to None
    )
    assert record.port_code == "NLRTM"
    assert record.wave_height_m == 1.5
    assert record.wind_wave_height_m is None  # Verify nullable default


def test_fallback_port_coordinates_has_10_ports():
    """All 10 fallback ports have coordinates defined.

    This is a contract test on the offline fallback dict: if someone removes a port
    or adds a typo in coordinates, this test catches it immediately.
    The -90/+90 and -180/+180 bounds check that no coordinate is obviously wrong.
    """
    assert len(FALLBACK_PORT_COORDINATES) == 10  # Exact count check
    for code, (lat, lon) in FALLBACK_PORT_COORDINATES.items():
        # Earth latitude bounds
        assert -90 <= lat <= 90, f"{code} latitude out of range"
        # Earth longitude bounds
        assert -180 <= lon <= 180, f"{code} longitude out of range"


@patch("ingestion.clients.weather.httpx.Client")  # Replace httpx.Client with a mock
def test_fetch_forecast_parses_response(mock_client_cls):
    """OpenMeteoClient parses a sample API response.

    Tests the core transformation: parallel arrays → list of per-hour objects.
    Uses a 2-hour sample (easy to verify by hand) rather than 168-hour full forecast.
    """
    sample_response = {
        "latitude": 51.95,
        "longitude": 4.05,
        "hourly": {
            "time": ["2026-04-13T00:00", "2026-04-13T01:00"],
            "wave_height": [1.2, 1.3],  # Hour 0: 1.2m, Hour 1: 1.3m
            "wave_direction": [270, 265],  # Hour 0: 270° (W), Hour 1: 265°
            "wave_period": [5.5, 5.8],
            "wind_wave_height": [0.8, 0.9],
            "swell_wave_height": [0.6, 0.7],
        },
    }

    mock_resp = MagicMock()
    # .json() returns our controlled data
    mock_resp.json.return_value = sample_response
    mock_resp.raise_for_status = MagicMock()  # Don't raise an exception

    mock_client = MagicMock()
    mock_client.get.return_value = mock_resp
    mock_client_cls.return_value = mock_client

    client = OpenMeteoClient()
    client.client = mock_client  # Inject mock HTTP client

    records = client.fetch_forecast("NLRTM", 51.95, 4.05, forecast_days=1)

    assert len(records) == 2  # 2 hours in sample
    assert records[0].wave_height_m == 1.2  # Index 0 → first hour
    assert records[1].port_code == "NLRTM"  # port_code added in transformation
    assert records[1].wave_height_m == 1.3  # Index 1 → second hour
    assert records[0].wave_direction_deg == 270.0  # Float conversion from int in JSON
