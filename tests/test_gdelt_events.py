"""Tests for GDELT maritime event ingestion and attribution."""

from __future__ import annotations

from unittest.mock import MagicMock

from ingestion.clients.gdelt_events import (
    GdeltEventsClient,
    attribute_event_to_ports,
    normalize_article,
    parse_gdelt_seen_date,
)


def test_parse_gdelt_seen_date_common_formats() -> None:
    assert parse_gdelt_seen_date("20260612T104500Z") == "2026-06-12T10:45:00+00:00"
    assert parse_gdelt_seen_date("20260612104500") == "2026-06-12T10:45:00+00:00"


def test_port_name_attribution_is_direct() -> None:
    matches = attribute_event_to_ports(
        "Dockworker strike disrupts operations at Port of Rotterdam"
    )

    assert [match.port_code for match in matches] == ["NLRTM"]
    assert matches[0].attribution_reason == "port_term:rotterdam"


def test_country_maritime_attribution_expands_to_country_ports() -> None:
    matches = attribute_event_to_ports("US port terminals face customs outage")

    assert {match.port_code for match in matches} == {"USLAX", "USNYC"}
    assert all(
        match.attribution_reason.startswith("country_maritime") for match in matches
    )


def test_non_maritime_country_story_is_not_attributed() -> None:
    matches = attribute_event_to_ports("US election polling shows a close race")

    assert matches == []


def test_country_terms_do_not_match_inside_other_words() -> None:
    matches = attribute_event_to_ports("Customs outage affects port terminals")

    assert matches == []


def test_normalize_article_keeps_unattributed_for_audit() -> None:
    records = normalize_article(
        {
            "title": "Global shipping rates rise after container delays",
            "url": "https://example.com/story",
            "seendate": "20260612T104500Z",
            "domain": "example.com",
            "language": "English",
            "sourcecountry": "US",
        },
        query_name="infrastructure",
        query="shipping delays",
        fetched_at="2026-06-12T11:00:00+00:00",
    )

    assert len(records) == 1
    assert records[0].port_code is None
    assert records[0].attribution_reason == "unattributed"
    assert records[0].event_category == "infrastructure"
    assert records[0].severity_score == 0.65


def test_normalize_article_fans_out_to_multiple_ports() -> None:
    records = normalize_article(
        {
            "title": "American port terminals brace for labor strike",
            "url": "https://example.com/us-port-strike",
            "seendate": "20260612T104500Z",
        },
        query_name="labor",
        query="port strike",
        fetched_at="2026-06-12T11:00:00+00:00",
    )

    assert {record.port_code for record in records} == {"USLAX", "USNYC"}
    assert {record.event_category for record in records} == {"labor"}
    assert all(record.severity_score == 0.9 for record in records)


def test_gdelt_client_fetches_and_deduplicates() -> None:
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "articles": [
            {
                "title": "Shanghai port congestion follows terminal outage",
                "url": "https://example.com/shanghai-port",
                "seendate": "20260612T104500Z",
            },
            {
                "title": "Shanghai port congestion follows terminal outage",
                "url": "https://example.com/shanghai-port",
                "seendate": "20260612T104500Z",
            },
        ]
    }
    mock_response.raise_for_status = MagicMock()

    mock_http = MagicMock()
    mock_http.get.return_value = mock_response

    client = GdeltEventsClient(http_client=mock_http)
    records = client.fetch_events(
        queries={"infrastructure": "port congestion"},
        max_records_per_query=2,
    )

    assert len(records) == 1
    assert records[0].port_code == "CNSHA"
    assert records[0].event_category == "infrastructure"
    mock_http.get.assert_called_once()
