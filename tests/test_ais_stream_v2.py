from datetime import UTC, datetime

from ingestion.clients.ais_stream import (
    BOUNDING_BOXES,
    SUBSCRIBED_MESSAGE_TYPES,
    AISMessage,
)
from serverless.ports import PORTS


def _message(message_type, payload):
    return AISMessage.model_validate(
        {
            "MessageType": message_type,
            "MetaData": {
                "MMSI": 123456789,
                "ShipName": " TEST VESSEL ",
                "latitude": 33.7,
                "longitude": -118.2,
                "time_utc": "2026-06-14T10:00:00Z",
            },
            "Message": payload,
        }
    )


def test_position_report_keeps_v1_shape() -> None:
    msg = _message(
        "PositionReport",
        {
            "PositionReport": {
                "Sog": 8.2,
                "Cog": 120.5,
                "TrueHeading": 121,
                "NavigationalStatus": 0,
            }
        },
    )

    record = msg.to_position_record()

    assert record is not None
    assert record["mmsi"] == 123456789
    assert record["ship_name"] == "TEST VESSEL"
    assert record["lat"] == 33.7
    assert record["lon"] == -118.2
    assert record["sog"] == 8.2
    assert record["msg_type"] == "PositionReport"


def test_ais_subscription_is_scoped_to_pilot_ports() -> None:
    assert len(BOUNDING_BOXES) == len(PORTS)


def test_live_subscription_uses_known_good_position_feed() -> None:
    assert SUBSCRIBED_MESSAGE_TYPES == ["PositionReport"]


def test_class_b_position_report_normalizes_to_position_shape() -> None:
    msg = _message(
        "StandardClassBPositionReport",
        {
            "StandardClassBPositionReport": {
                "Latitude": 1.24,
                "Longitude": 103.81,
                "Sog": 5.5,
                "Cog": 88,
                "TrueHeading": 90,
                "NavigationalStatus": 15,
            }
        },
    )

    record = msg.to_position_record()

    assert record is not None
    assert record["lat"] == 1.24
    assert record["lon"] == 103.81
    assert record["sog"] == 5.5
    assert record["msg_type"] == "StandardClassBPositionReport"


def test_voyage_static_record_writes_additive_shape() -> None:
    received_at = datetime(2026, 6, 14, 10, 0, tzinfo=UTC)
    msg = _message(
        "ShipStaticData",
        {
            "ShipStaticData": {
                "Name": "BOX RUNNER",
                "CallSign": "CALL9",
                "ImoNumber": "IMO1234567",
                "Type": "Cargo",
                "Destination": "USLAX",
                "Eta": {"Month": 6, "Day": 15, "Hour": 8, "Minute": 30},
                "MaximumStaticDraught": 12.4,
                "Dimension": {"A": 100, "B": 20, "C": 8, "D": 9},
            }
        },
    )

    record = msg.to_voyage_record(received_at)

    assert record is not None
    assert record["mmsi"] == 123456789
    assert record["ship_name"] == "BOX RUNNER"
    assert record["destination"] == "USLAX"
    assert record["eta_timestamp_utc"] == "2026-06-15T08:30:00+00:00"
    assert record["draught_m"] == 12.4
    assert record["dimension_to_bow_m"] == 100


def test_voyage_static_missing_optional_fields_are_null() -> None:
    msg = _message("ShipStaticData", {"ShipStaticData": {"Name": "BOX RUNNER"}})

    record = msg.to_voyage_record(datetime(2026, 6, 14, 10, 0, tzinfo=UTC))

    assert record is not None
    assert record["destination"] is None
    assert record["eta_timestamp_utc"] is None
    assert record["draught_m"] is None
    assert record["dimension_to_bow_m"] is None
