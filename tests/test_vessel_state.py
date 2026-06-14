from models.vessel_state import (
    AT_BERTH,
    INBOUND,
    OUTBOUND,
    TRANSIT_UNKNOWN,
    WAITING_ANCHOR,
    classify_vessel_state,
)


def test_moored_close_to_port_is_at_berth() -> None:
    assert (
        classify_vessel_state(
            distance_nm=5,
            sog=0.1,
            nav_status=5,
            distance_delta_nm=0,
        )
        == AT_BERTH
    )


def test_declared_anchor_close_to_port_is_waiting() -> None:
    assert (
        classify_vessel_state(
            distance_nm=20,
            sog=0.2,
            nav_status=1,
            distance_delta_nm=0,
        )
        == WAITING_ANCHOR
    )


def test_slow_outbound_vessel_is_not_waiting() -> None:
    assert (
        classify_vessel_state(
            distance_nm=12,
            sog=0.2,
            nav_status=15,
            distance_delta_nm=1.2,
        )
        == OUTBOUND
    )


def test_shrinking_distance_is_inbound() -> None:
    assert (
        classify_vessel_state(
            distance_nm=80,
            sog=10,
            nav_status=0,
            distance_delta_nm=-2.5,
        )
        == INBOUND
    )


def test_destination_and_eta_can_mark_inbound() -> None:
    assert (
        classify_vessel_state(
            distance_nm=120,
            sog=8,
            nav_status=0,
            destination_matches_port=True,
            eta_within_48h=True,
        )
        == INBOUND
    )


def test_unclear_nearby_vessel_is_transit_unknown() -> None:
    assert (
        classify_vessel_state(
            distance_nm=45,
            sog=6,
            nav_status=15,
            distance_delta_nm=0.1,
        )
        == TRANSIT_UNKNOWN
    )
