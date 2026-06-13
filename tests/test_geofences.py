from pathlib import Path

from serverless.geofences import best_geofence_match, load_feature_collection

REFERENCE_DIR = Path(__file__).resolve().parents[1] / "warehouse" / "reference"
REFERENCE_GEOFENCES = REFERENCE_DIR / "noaa_cp7_uslax_anchorages.geojson"


def test_best_geofence_match_finds_uslax_anchorage_b() -> None:
    features = load_feature_collection(REFERENCE_GEOFENCES)

    match = best_geofence_match(
        lat=33.731,
        lon=-118.218,
        features=features,
        port_code="USLAX",
        zone_type="anchorage",
    )

    assert match is not None
    assert match["properties"]["zone_id"] == "uslax_anchorage_b"


def test_best_geofence_match_returns_none_outside_anchorages() -> None:
    features = load_feature_collection(REFERENCE_GEOFENCES)

    match = best_geofence_match(
        lat=33.9,
        lon=-118.5,
        features=features,
        port_code="USLAX",
        zone_type="anchorage",
    )

    assert match is None
