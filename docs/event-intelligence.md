# Event Intelligence Layer

_Last updated 2026-06-12._

This page documents the first event-aware layer for the maritime disruption
dashboard. It adds real-world event ingestion, conservative event-to-port
attribution, and hourly event-pressure feature tables.

The current production congestion model does not consume these event features
yet. They are available for analysis and future retraining.

## Source

The first implemented source is GDELT DOC.

| Property | Value |
|---|---|
| Client | `ingestion/clients/gdelt_events.py` |
| Lambda | `serverless/handlers/gdelt_lambda.py` |
| Raw prefix | `raw/source=gdelt_events/date=YYYY-MM-DD/` |
| Glue table | `raw_gdelt_events` |
| Schedule | Hourly at `:12`, before feature rebuild at `:15` |
| Auth | None |

The client fetches four query families:

| Query family | Purpose |
|---|---|
| `labor` | Strikes, dockworker actions, protests, blockades |
| `conflict_security` | Conflict, attacks, sanctions, embargoes, blockades |
| `infrastructure` | Closures, outages, accidents, congestion, explosions |
| `trade_policy` | Tariffs, customs, trade policy, sanctions |

## Raw Event Contract

Each raw record represents one article-to-port attribution row. If an article
mentions multiple pilot ports, it can produce multiple rows with the same base
article hash and different `port_code` suffixes. If no port can be attributed,
the row is retained with `port_code = null` for auditability but excluded from
port-level feature tables.

| Field | Meaning |
|---|---|
| `event_id` | Stable hash of URL/title/seen time plus attribution suffix |
| `source` | `gdelt_doc` |
| `query_name` | Query family that surfaced the article |
| `query` | Exact query string sent to GDELT |
| `fetched_at` | UTC ingestion time |
| `seen_at` | GDELT article seen time when available |
| `title` | Article title |
| `url` | Article URL |
| `domain` | Source domain when supplied by GDELT |
| `language` | Article language when supplied by GDELT |
| `source_country` | GDELT source-country metadata, not assumed to be event location |
| `port_code` | Attributed pilot port, or null if unattributed |
| `port_name` | Attributed port name |
| `attribution_reason` | Rule that produced the port match |
| `event_category` | `labor`, `conflict_security`, `infrastructure`, `trade_policy`, or `other` |
| `severity_score` | Inspectable heuristic score from 0.0 to 1.0 |
| `matched_terms` | Trigger terms found in the normalized title/URL text |

## Attribution Rules

Attribution is intentionally conservative:

- Direct port-name terms win first, such as `rotterdam`, `shanghai`, `jebel ali`,
  or `felixstowe`.
- Country-level attribution only applies when the text also contains a maritime
  term such as `port`, `shipping`, `terminal`, `vessel`, or `container`.
- Country-level attribution expands to pilot ports in that country. For example,
  a US maritime event can map to both `USLAX` and `USNYC`.
- `source_country` is stored but not used as event location.
- Unmatched rows remain in raw data but do not become model features.

These rules favor lower recall and better auditability. A future version can add
geocoding, named-entity extraction, and lane/chokepoint attribution.

## Feature Tables

Two Athena CTAS tables expose the event layer:

| Table | Grain | Purpose |
|---|---|---|
| `event_port_attribution_hourly` | One attributed event per port | Audit table for port attribution decisions |
| `feature_event_signals_hourly` | One port-hour where events exist | Rolling event-pressure features |

`feature_event_signals_hourly` includes:

| Feature | Meaning |
|---|---|
| `event_count_6h` | Attributed event count in the last 6 hours |
| `event_count_24h` | Attributed event count in the last 24 hours |
| `severe_event_count_24h` | Count of events with `severity_score >= 0.8` |
| `avg_event_severity_24h` | Average severity in the 24-hour window |
| `labor_event_count_24h` | Labor-event count in the 24-hour window |
| `conflict_event_count_24h` | Conflict/security count in the 24-hour window |
| `policy_event_count_24h` | Trade-policy count in the 24-hour window |
| `infrastructure_event_count_24h` | Infrastructure-event count in the 24-hour window |
| `last_event_seen_at` | Latest event hour contributing to the row |

`feature_port_status_hourly` now left-joins these event features and fills
missing event windows with zero. This makes the event layer available for
offline analysis without changing the currently deployed model inputs.

## Model Boundary

The deployed model still uses the AIS/weather/time feature contract in
`models/features.py`. Event features should not be added to that contract until
there is:

- enough chronological history,
- an AIS-only versus AIS-plus-events comparison,
- a time-based backtest,
- per-port metrics, and
- a model-card update describing the new inputs.

## Known Limitations

- GDELT article-list metadata is not a structured incident feed.
- The first attribution layer uses title and URL text, not full article body.
- Severity is heuristic and designed for feature aggregation, not direct display
  as a verified impact score.
- Country-level attribution can over-broaden events in countries with multiple
  pilot ports.
- This layer detects event pressure, not confirmed port disruption.
