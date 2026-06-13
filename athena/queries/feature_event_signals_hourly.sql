-- feature_event_signals_hourly
-- Rolling event-pressure features by (port_code, observation_hour).
-- These features are exposed for analysis and future retraining; the current
-- production model does not consume them yet.

CREATE TABLE dpl_pilot.feature_event_signals_hourly
WITH (
    format = 'PARQUET',
    partitioned_by = ARRAY['date_partition'],
    external_location =
      's3://dpl-serverless-pilot-861276086413-pilot-data/curated/feature_event_signals_hourly/'
)
AS
WITH anchors AS (
    SELECT DISTINCT
        port_code,
        event_hour AS observation_hour
    FROM dpl_pilot.event_port_attribution_hourly
),
windowed AS (
    SELECT
        a.port_code,
        a.observation_hour,
        e.event_hour,
        e.event_category,
        e.severity_score
    FROM anchors a
    LEFT JOIN dpl_pilot.event_port_attribution_hourly e
        ON e.port_code = a.port_code
       AND e.event_hour > a.observation_hour - INTERVAL '24' HOUR
       AND e.event_hour <= a.observation_hour
)
SELECT
    port_code,
    observation_hour,
    count_if(event_hour > observation_hour - INTERVAL '6' HOUR) AS event_count_6h,
    count(event_hour) AS event_count_24h,
    count_if(severity_score >= 0.8) AS severe_event_count_24h,
    coalesce(avg(severity_score), 0) AS avg_event_severity_24h,
    count_if(event_category = 'labor') AS labor_event_count_24h,
    count_if(event_category = 'conflict_security') AS conflict_event_count_24h,
    count_if(event_category = 'trade_policy') AS policy_event_count_24h,
    count_if(event_category = 'infrastructure') AS infrastructure_event_count_24h,
    CAST(max(event_hour) AS varchar) AS last_event_seen_at,
    date_format(observation_hour, '%Y-%m-%d') AS date_partition
FROM windowed
GROUP BY port_code, observation_hour
