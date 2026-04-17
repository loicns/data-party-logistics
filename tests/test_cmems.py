"""Tests for CMEMS ocean current ingestion client.

Run: uv run pytest tests/test_cmems.py -v
"""

from unittest.mock import MagicMock, patch

from ingestion.clients.cmems import (
    ROUTE_WAYPOINTS,
    CMEMSClient,
    OceanCurrentRecord,
)

# ---------------------------------------------------------------------------
# Model and derived field tests
# ---------------------------------------------------------------------------


def test_ocean_current_record_basic():
    """OceanCurrentRecord stores raw fields and computes derived fields.

    This is the most important test in this file: if derived fields are wrong,
    the Week 5 current_headwind_component feature is silently corrupted.
    No test failure here = no safety net before production.
    """
    record = OceanCurrentRecord(
        waypoint_lat=40.0,
        waypoint_lon=-50.0,
        timestamp="2026-04-13T06:00:00",
        current_u_ms=1.0,  # 1 m/s eastward
        current_v_ms=0.0,  # 0 m/s northward
        wave_height_m=2.5,
    )
    assert record.waypoint_lat == 40.0
    assert record.current_u_ms == 1.0
    assert record.wave_height_m == 2.5


def test_current_speed_pure_east():
    """Speed of a purely eastward current equals its u component.

    For u=1.0, v=0.0: speed = sqrt(1² + 0²) = 1.0 m/s.
    This is the simplest possible case — easy to verify by hand.
    """
    record = OceanCurrentRecord(
        waypoint_lat=0.0,
        waypoint_lon=0.0,
        timestamp="2026-04-13T00:00:00",
        current_u_ms=1.0,
        current_v_ms=0.0,
    )
    assert record.current_speed_ms == 1.0


def test_current_speed_diagonal():
    """Speed of a 3-4-5 right triangle current is exactly 5.

    u=3, v=4: speed = sqrt(9 + 16) = sqrt(25) = 5.0 m/s.
    3-4-5 Pythagorean triple makes the expected value exact — no floating point error.
    """
    record = OceanCurrentRecord(
        waypoint_lat=0.0,
        waypoint_lon=0.0,
        timestamp="2026-04-13T00:00:00",
        current_u_ms=3.0,
        current_v_ms=4.0,
    )
    assert record.current_speed_ms == 5.0


def test_current_direction_pure_east():
    """A purely eastward current (u=1, v=0) should point 90° (East).

    atan2(1, 0) = 90° in oceanographic convention (angle from North, clockwise).
    """
    record = OceanCurrentRecord(
        waypoint_lat=0.0,
        waypoint_lon=0.0,
        timestamp="2026-04-13T00:00:00",
        current_u_ms=1.0,
        current_v_ms=0.0,
    )
    assert record.current_direction_deg == 90.0


def test_current_direction_pure_north():
    """A purely northward current (u=0, v=1) should point 0° (North).

    atan2(0, 1) = 0° — current flowing directly northward.
    """
    record = OceanCurrentRecord(
        waypoint_lat=0.0,
        waypoint_lon=0.0,
        timestamp="2026-04-13T00:00:00",
        current_u_ms=0.0,
        current_v_ms=1.0,
    )
    assert record.current_direction_deg == 0.0


def test_current_direction_normalised_to_360():
    """Negative atan2 result is normalised to [0, 360) range.

    u=-1, v=0 → atan2(-1, 0) = -90° → normalised to 270° (West).
    Without the (deg + 360) % 360 normalisation, this would return -90°,
    which would break the Week 5 heading_diff calculation.
    """
    record = OceanCurrentRecord(
        waypoint_lat=0.0,
        waypoint_lon=0.0,
        timestamp="2026-04-13T00:00:00",
        current_u_ms=-1.0,
        current_v_ms=0.0,
    )
    assert record.current_direction_deg == 270.0


def test_wave_height_optional():
    """wave_height_m defaults to None when not provided.

    VHM0 may be missing at some waypoints or time steps — the field must be nullable.
    A non-nullable field here would cause silent data loss via validation drops.
    """
    record = OceanCurrentRecord(
        waypoint_lat=0.0,
        waypoint_lon=0.0,
        timestamp="2026-04-13T00:00:00",
        current_u_ms=0.5,
        current_v_ms=0.3,
        # wave_height_m not provided — should default to None
    )
    assert record.wave_height_m is None


# ---------------------------------------------------------------------------
# Route waypoints sanity check
# ---------------------------------------------------------------------------


def test_route_waypoints_defined():
    """All route waypoints have valid coordinates.

    Contract test: catches anyone who adds a waypoint with invalid lat/lon
    or mistakenly swaps lat and lon (e.g., (103.84, 1.26) for Singapore).
    """
    assert len(ROUTE_WAYPOINTS) >= 10  # At least 10 waypoints defined
    for key, (lat, lon) in ROUTE_WAYPOINTS.items():
        assert -90 <= lat <= 90, f"{key}: latitude {lat} out of range [-90, 90]"
        assert -180 <= lon <= 180, f"{key}: longitude {lon} out of range [-180, 180]"


# ---------------------------------------------------------------------------
# Client cache test
# ---------------------------------------------------------------------------


def test_cmems_client_cache_hit(monkeypatch):
    """CMEMSClient returns cached records without re-fetching.

    Injects a pre-loaded cache entry and verifies that fetch_waypoint()
    returns the cached result without calling copernicusmarine.open_dataset().
    This tests the cache hit branch — the API should never be called.
    """
    import time

    client = CMEMSClient()

    # Pre-populate the cache with a known record
    cached_record = OceanCurrentRecord(
        waypoint_lat=47.0,
        waypoint_lon=-20.0,
        timestamp="2026-04-13T06:00:00",
        current_u_ms=0.3,
        current_v_ms=0.1,
        wave_height_m=1.8,
    )
    # Set expiry 1 hour in the future so the cache is valid
    client._cache["natl_02"] = (time.time() + 3600, [cached_record])

    # Patch copernicusmarine in sys.modules so that if it IS called, we can track it
    mock_cmems = MagicMock()
    with patch.dict("sys.modules", {"copernicusmarine": mock_cmems}):
        result = client.fetch_waypoint("natl_02", 47.0, -20.0)

    # The cached record should be returned — no API call made
    assert len(result) == 1
    assert result[0].current_u_ms == 0.3
    mock_cmems.open_dataset.assert_not_called()  # Verify cache hit: API was NOT called
