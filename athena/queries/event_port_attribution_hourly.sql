-- event_port_attribution_hourly
-- One row per attributed GDELT event and port.
-- Raw records are article-port rows from raw_gdelt_events. Unattributed rows
-- remain in raw S3 for auditability but are excluded here.

CREATE TABLE dpl_pilot.event_port_attribution_hourly
WITH (
    format = 'PARQUET',
    partitioned_by = ARRAY['date_partition'],
    external_location =
      's3://dpl-serverless-pilot-861276086413-pilot-data/curated/event_port_attribution_hourly/'
)
AS
SELECT DISTINCT
    event_id,
    port_code,
    port_name,
    date_trunc(
        'hour',
        CAST(from_iso8601_timestamp(coalesce(seen_at, fetched_at)) AS timestamp)
    ) AS event_hour,
    seen_at,
    fetched_at,
    source,
    query_name,
    event_category,
    severity_score,
    attribution_reason,
    title,
    url,
    domain,
    language,
    source_country,
    date_format(
        date_trunc(
            'hour',
            CAST(from_iso8601_timestamp(coalesce(seen_at, fetched_at)) AS timestamp)
        ),
        '%Y-%m-%d'
    ) AS date_partition
FROM raw_gdelt_events
WHERE port_code IS NOT NULL
  AND trim(port_code) <> ''
  AND coalesce(seen_at, fetched_at) IS NOT NULL
