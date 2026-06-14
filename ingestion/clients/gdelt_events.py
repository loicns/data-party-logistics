"""GDELT DOC event ingestion for maritime disruption signals."""

from __future__ import annotations

import hashlib
import logging
import re
from datetime import UTC, datetime
from typing import Any

import httpx
from pydantic import BaseModel, Field
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

GDELT_DOC_URL = "https://api.gdeltproject.org/api/v2/doc/doc"

DEFAULT_EVENT_QUERIES: dict[str, str] = {
    "labor": (
        "(port OR shipping OR maritime OR dockworker OR longshore OR terminal) "
        "(strike OR protest OR blockade OR labor)"
    ),
    "conflict_security": (
        "(port OR shipping OR maritime OR vessel OR container) "
        "(war OR conflict OR attack OR sanction OR blockade)"
    ),
    "infrastructure": (
        "(port OR terminal OR shipping) "
        "(closure OR congestion OR accident OR explosion OR outage)"
    ),
    "trade_policy": (
        "(shipping OR container OR freight OR port) "
        "(tariff OR customs OR embargo OR sanctions)"
    ),
}

MARITIME_TERMS = {
    "anchorage",
    "berth",
    "cargo",
    "container",
    "dock",
    "freight",
    "harbor",
    "harbour",
    "maritime",
    "port",
    "shipping",
    "terminal",
    "vessel",
}

CATEGORY_TERMS: dict[str, set[str]] = {
    "labor": {"strike", "labor", "labour", "dockworker", "longshore", "protest"},
    "conflict_security": {
        "attack",
        "blockade",
        "conflict",
        "embargo",
        "sanction",
        "sanctions",
        "war",
    },
    "infrastructure": {
        "accident",
        "closure",
        "congestion",
        "explosion",
        "outage",
        "shutdown",
    },
    "trade_policy": {"customs", "tariff", "tariffs", "trade", "policy"},
}

HIGH_SEVERITY_TERMS = {
    "attack",
    "blockade",
    "closure",
    "embargo",
    "explosion",
    "sanction",
    "sanctions",
    "shutdown",
    "strike",
    "war",
}
MEDIUM_SEVERITY_TERMS = {
    "accident",
    "congestion",
    "customs",
    "delay",
    "delays",
    "labor",
    "labour",
    "outage",
    "protest",
    "tariff",
}

PORT_RULES: dict[str, dict[str, Any]] = {
    "NLRTM": {
        "name": "Rotterdam",
        "country_code": "NL",
        "port_terms": ["rotterdam", "maasvlakte"],
        "country_terms": ["netherlands", "dutch"],
    },
    "SGSIN": {
        "name": "Singapore",
        "country_code": "SG",
        "port_terms": ["singapore", "tuas", "pasir panjang"],
        "country_terms": ["singapore"],
    },
    "USLAX": {
        "name": "Los Angeles",
        "country_code": "US",
        "port_terms": ["los angeles", "port of la", "san pedro"],
        "country_terms": ["united states", "u.s.", "us ", "american"],
    },
    "CNSHA": {
        "name": "Shanghai",
        "country_code": "CN",
        "port_terms": ["shanghai", "yangshan"],
        "country_terms": ["china", "chinese"],
    },
    "DEHAM": {
        "name": "Hamburg",
        "country_code": "DE",
        "port_terms": ["hamburg"],
        "country_terms": ["germany", "german"],
    },
    "BEANR": {
        "name": "Antwerp",
        "country_code": "BE",
        "port_terms": ["antwerp", "antwerpen"],
        "country_terms": ["belgium", "belgian"],
    },
    "GBFXT": {
        "name": "Felixstowe",
        "country_code": "GB",
        "port_terms": ["felixstowe"],
        "country_terms": ["united kingdom", "uk ", "britain", "british"],
    },
    "AEDXB": {
        "name": "Dubai",
        "country_code": "AE",
        "port_terms": ["dubai", "jebel ali"],
        "country_terms": ["united arab emirates", "uae", "emirati"],
    },
    "USNYC": {
        "name": "New York",
        "country_code": "US",
        "port_terms": ["new york", "new jersey", "port of ny", "port of nj"],
        "country_terms": ["united states", "u.s.", "us ", "american"],
    },
    "TWKHH": {
        "name": "Kaohsiung",
        "country_code": "TW",
        "port_terms": ["kaohsiung"],
        "country_terms": ["taiwan", "taiwanese"],
    },
}


class PortAttribution(BaseModel):
    """One event-to-port attribution decision."""

    port_code: str
    port_name: str
    attribution_reason: str


class MaritimeEventRecord(BaseModel):
    """Normalized raw event record written to S3."""

    event_id: str
    source: str = "gdelt_doc"
    query_name: str
    query: str
    fetched_at: str
    seen_at: str | None = None
    title: str
    url: str
    domain: str | None = None
    language: str | None = None
    source_country: str | None = None
    port_code: str | None = None
    port_name: str | None = None
    attribution_reason: str = "unattributed"
    event_category: str
    severity_score: float = Field(ge=0.0, le=1.0)
    matched_terms: list[str] = Field(default_factory=list)


def _normalize_text(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[^a-z0-9.]+", " ", value)
    compact = re.sub(r"\s+", " ", value).strip()
    return f" {compact} "


def _term_in_text(term: str, text: str) -> bool:
    return _normalize_text(term) in text


def _matched_terms(text: str, terms: set[str]) -> list[str]:
    return sorted(term for term in terms if _term_in_text(term, text))


def parse_gdelt_seen_date(value: str | None) -> str | None:
    """Parse the common GDELT seendate formats into ISO-8601 UTC."""

    if not value:
        return None

    raw = value.strip()
    formats = [
        "%Y%m%dT%H%M%SZ",
        "%Y%m%d%H%M%S",
        "%Y-%m-%dT%H:%M:%SZ",
    ]
    for fmt in formats:
        try:
            parsed = datetime.strptime(raw, fmt).replace(tzinfo=UTC)
            return parsed.isoformat()
        except ValueError:
            continue
    return raw


def categorize_event(text: str, query_name: str) -> tuple[str, list[str]]:
    """Return the most likely event category and matched trigger terms."""

    category_matches = {
        category: _matched_terms(text, terms)
        for category, terms in CATEGORY_TERMS.items()
    }
    best_category, matches = max(
        category_matches.items(),
        key=lambda item: (len(item[1]), item[0] == query_name),
    )
    if matches:
        return best_category, matches
    if query_name in CATEGORY_TERMS:
        return query_name, []
    return "other", []


def severity_score(text: str) -> float:
    """Coarse, inspectable severity score for event feature aggregation."""

    high_matches = _matched_terms(text, HIGH_SEVERITY_TERMS)
    if high_matches:
        return 0.9

    medium_matches = _matched_terms(text, MEDIUM_SEVERITY_TERMS)
    if medium_matches:
        return 0.65

    if _matched_terms(text, MARITIME_TERMS):
        return 0.35
    return 0.2


def attribute_event_to_ports(title: str, url: str = "") -> list[PortAttribution]:
    """Attribute an article to pilot ports with explicit, conservative rules.

    Port-name matches win first. Country-only attribution is allowed only when
    the text also contains a maritime term, and expands to all pilot ports in
    that country.
    """

    text = _normalize_text(f"{title} {url}")
    maritime_match = any(_term_in_text(term, text) for term in MARITIME_TERMS)

    direct_matches: list[PortAttribution] = []
    for port_code, rule in PORT_RULES.items():
        for term in rule["port_terms"]:
            if _term_in_text(term, text):
                direct_matches.append(
                    PortAttribution(
                        port_code=port_code,
                        port_name=rule["name"],
                        attribution_reason=f"port_term:{term}",
                    )
                )
                break

    if direct_matches:
        return direct_matches

    if not maritime_match:
        return []

    country_matches: list[PortAttribution] = []
    for port_code, rule in PORT_RULES.items():
        for term in rule["country_terms"]:
            if _term_in_text(term, text):
                country_matches.append(
                    PortAttribution(
                        port_code=port_code,
                        port_name=rule["name"],
                        attribution_reason=f"country_maritime:{term}",
                    )
                )
                break
    return country_matches


def _article_value(article: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = article.get(key)
        if value not in {None, ""}:
            return str(value)
    return None


def _event_base_id(url: str, title: str, seen_at: str | None) -> str:
    raw = "|".join([url, title, seen_at or ""])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]


def normalize_article(
    article: dict[str, Any],
    *,
    query_name: str,
    query: str,
    fetched_at: str,
    include_unattributed: bool = True,
) -> list[MaritimeEventRecord]:
    """Normalize one GDELT article into zero, one, or many port event rows."""

    title = _article_value(article, "title") or ""
    url = _article_value(article, "url", "url_mobile") or ""
    if not title and not url:
        return []

    seen_at = parse_gdelt_seen_date(
        _article_value(article, "seendate", "seenDate", "seen_date")
    )
    text = _normalize_text(f"{title} {url}")
    category, terms = categorize_event(text, query_name)
    event_severity = severity_score(text)
    base_id = _event_base_id(url, title, seen_at)

    attributions = attribute_event_to_ports(title, url)
    if not attributions and include_unattributed:
        attributions = [
            PortAttribution(
                port_code="",
                port_name="",
                attribution_reason="unattributed",
            )
        ]

    records: list[MaritimeEventRecord] = []
    for attribution in attributions:
        suffix = attribution.port_code or "unattributed"
        records.append(
            MaritimeEventRecord(
                event_id=f"{base_id}-{suffix}",
                query_name=query_name,
                query=query,
                fetched_at=fetched_at,
                seen_at=seen_at,
                title=title,
                url=url,
                domain=_article_value(article, "domain"),
                language=_article_value(article, "language"),
                source_country=_article_value(
                    article,
                    "sourcecountry",
                    "sourceCountry",
                    "source_country",
                ),
                port_code=attribution.port_code or None,
                port_name=attribution.port_name or None,
                attribution_reason=attribution.attribution_reason,
                event_category=category,
                severity_score=event_severity,
                matched_terms=terms,
            )
        )
    return records


class GdeltEventsClient:
    """Fetch and normalize GDELT DOC articles for maritime disruption queries."""

    def __init__(self, http_client: httpx.Client | None = None) -> None:
        self.client = http_client or httpx.Client(timeout=20)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    def fetch_query(
        self,
        query_name: str,
        query: str,
        *,
        timespan: str = "1d",
        max_records: int = 75,
    ) -> list[dict[str, Any]]:
        """Fetch raw article dictionaries from GDELT DOC."""

        params: dict[str, str | int] = {
            "query": query,
            "mode": "ArtList",
            "format": "json",
            "timespan": timespan,
            "maxrecords": max_records,
            "sort": "HybridRel",
        }
        response = self.client.get(GDELT_DOC_URL, params=params)
        response.raise_for_status()
        data = response.json()
        articles = data.get("articles", [])
        if not isinstance(articles, list):
            raise ValueError(f"GDELT returned non-list articles for {query_name}")
        return articles

    def fetch_events(
        self,
        *,
        queries: dict[str, str] | None = None,
        timespan: str = "1d",
        max_records_per_query: int = 75,
    ) -> list[MaritimeEventRecord]:
        """Fetch all configured maritime event queries and normalize records."""

        fetched_at = datetime.now(UTC).isoformat()
        event_queries = queries or DEFAULT_EVENT_QUERIES
        records: list[MaritimeEventRecord] = []
        seen_event_ids: set[str] = set()

        for query_name, query in event_queries.items():
            try:
                articles = self.fetch_query(
                    query_name,
                    query,
                    timespan=timespan,
                    max_records=max_records_per_query,
                )
            except Exception:
                logger.exception("gdelt_query_failed query_name=%s", query_name)
                continue

            for article in articles:
                for record in normalize_article(
                    article,
                    query_name=query_name,
                    query=query,
                    fetched_at=fetched_at,
                ):
                    if record.event_id in seen_event_ids:
                        continue
                    seen_event_ids.add(record.event_id)
                    records.append(record)

        logger.info("Fetched %d normalized GDELT event records", len(records))
        return records
