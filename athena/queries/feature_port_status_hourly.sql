-- feature_port_status_hourly
-- Joins vessel-ring counts with weather observations.
-- One row per (port_code, observation_hour) — this is the row shape the ML
-- model trains on.

-- REBUILDABLE: features_lambda drops + clears S3 before this CREATE.
CREATE TABLE dpl_pilot.feature_port_status_hourly
WITH (
    format = 'PARQUET',
    partitioned_by = ARRAY['date_partition'],
    external_location =
      's3://dpl-serverless-pilot-861276086413-pilot-data/curated/feature_port_status_hourly/'
)
AS
WITH weather_hourly AS (
    SELECT
        port_code,
        date_trunc('hour', CAST(from_iso8601_timestamp(timestamp) AS timestamp)) AS observation_hour,
        avg(wave_height_m) AS avg_wave_height,
        avg(wind_wave_height_m) AS avg_wind_kn,
        max(date) AS date_partition
    FROM raw_weather_observations
    WHERE date >= date_format(current_date - INTERVAL '90' DAY, '%Y-%m-%d')
    GROUP BY port_code, date_trunc('hour', CAST(from_iso8601_timestamp(timestamp) AS timestamp))
)
SELECT
    v.port_code,
    v.observation_hour,
    v.vessels_at_anchor,
    v.vessels_in_10nm,
    v.vessels_in_50nm,
    v.vessels_in_200nm,
    v.avg_speed_50nm,
    coalesce(w.avg_wave_height, 0) AS avg_wave_height_m,
    coalesce(w.avg_wind_kn, 0)     AS avg_wind_kn,
    hour(v.observation_hour)        AS hour_of_day,
    day_of_week(v.observation_hour) AS day_of_week,
    v.date_partition
FROM dpl_pilot.feature_vessel_inbound_hourly v
LEFT JOIN weather_hourly w
    ON v.port_code        = w.port_code
   AND v.observation_hour = w.observation_hour
