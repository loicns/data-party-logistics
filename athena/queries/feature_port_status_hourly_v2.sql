-- feature_port_status_hourly_v2
-- Additive AIS v2 gold table for candidate training. Production serving stays
-- on feature_port_status_hourly until v2 evaluation passes.

CREATE TABLE dpl_pilot.feature_port_status_hourly_v2
WITH (
    format = 'PARQUET',
    partitioned_by = ARRAY['date_partition'],
    external_location =
      's3://dpl-serverless-pilot-861276086413-pilot-data/curated/feature_port_status_hourly_v2/'
)
AS
WITH weather_hourly AS (
    SELECT
        port_code,
        date_trunc('hour', CAST(from_iso8601_timestamp(timestamp) AS timestamp))
            AS observation_hour,
        avg(wave_height_m) AS avg_wave_height,
        avg(wind_wave_height_m) AS avg_wind_kn,
        max(date) AS date_partition
    FROM raw_weather_observations
    WHERE date >= date_format(current_date - INTERVAL '90' DAY, '%Y-%m-%d')
    GROUP BY
        port_code,
        date_trunc('hour', CAST(from_iso8601_timestamp(timestamp) AS timestamp))
),
event_hourly AS (
    SELECT
        port_code,
        observation_hour,
        event_count_6h,
        event_count_24h,
        severe_event_count_24h,
        avg_event_severity_24h,
        labor_event_count_24h,
        conflict_event_count_24h,
        policy_event_count_24h,
        infrastructure_event_count_24h
    FROM dpl_pilot.feature_event_signals_hourly
)
SELECT
    s.port_code,
    s.observation_hour,
    sum(CASE WHEN distance_nm <= 10  THEN 1 ELSE 0 END) AS vessels_in_10nm,
    sum(CASE WHEN distance_nm <= 50  THEN 1 ELSE 0 END) AS vessels_in_50nm,
    sum(CASE WHEN distance_nm <= 200 THEN 1 ELSE 0 END) AS vessels_in_200nm,
    sum(CASE WHEN vessel_state = 'waiting_anchor' THEN 1 ELSE 0 END)
        AS vessels_at_anchor,
    sum(CASE WHEN vessel_state = 'at_berth' THEN 1 ELSE 0 END)
        AS vessels_at_berth,
    sum(CASE WHEN vessel_state = 'waiting_anchor' THEN 1 ELSE 0 END)
        AS vessels_waiting_anchor,
    sum(CASE WHEN vessel_state = 'inbound' THEN 1 ELSE 0 END)
        AS vessels_inbound,
    sum(CASE WHEN vessel_state = 'outbound' THEN 1 ELSE 0 END)
        AS vessels_outbound,
    sum(CASE WHEN vessel_state = 'transit_unknown' THEN 1 ELSE 0 END)
        AS vessels_transit_unknown,
    sum(
        CASE
            WHEN destination_matches_port AND eta_within_48h THEN 1
            ELSE 0
        END
    ) AS destination_match_48h_count,
    avg(CASE WHEN distance_nm <= 50 THEN sog END) AS avg_speed_50nm,
    avg(distance_delta_nm) AS avg_distance_delta_nm,
    avg(CASE WHEN vessel_state = 'waiting_anchor' THEN draught_m END)
        AS avg_draught_waiting_anchor,
    coalesce(w.avg_wave_height, 0) AS avg_wave_height_m,
    coalesce(w.avg_wind_kn, 0) AS avg_wind_kn,
    coalesce(e.event_count_6h, 0) AS event_count_6h,
    coalesce(e.event_count_24h, 0) AS event_count_24h,
    coalesce(e.severe_event_count_24h, 0) AS severe_event_count_24h,
    coalesce(e.avg_event_severity_24h, 0) AS avg_event_severity_24h,
    coalesce(e.labor_event_count_24h, 0) AS labor_event_count_24h,
    coalesce(e.conflict_event_count_24h, 0) AS conflict_event_count_24h,
    coalesce(e.policy_event_count_24h, 0) AS policy_event_count_24h,
    coalesce(e.infrastructure_event_count_24h, 0)
        AS infrastructure_event_count_24h,
    hour(s.observation_hour) AS hour_of_day,
    day_of_week(s.observation_hour) AS day_of_week,
    s.date_partition
FROM dpl_pilot.feature_vessel_state_hourly s
LEFT JOIN weather_hourly w
    ON s.port_code = w.port_code
   AND s.observation_hour = w.observation_hour
LEFT JOIN event_hourly e
    ON s.port_code = e.port_code
   AND s.observation_hour = e.observation_hour
GROUP BY
    s.port_code,
    s.observation_hour,
    w.avg_wave_height,
    w.avg_wind_kn,
    e.event_count_6h,
    e.event_count_24h,
    e.severe_event_count_24h,
    e.avg_event_severity_24h,
    e.labor_event_count_24h,
    e.conflict_event_count_24h,
    e.policy_event_count_24h,
    e.infrastructure_event_count_24h,
    s.date_partition
