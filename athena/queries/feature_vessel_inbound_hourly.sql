-- feature_vessel_inbound_hourly
-- One row per (port_code, observation_hour).
-- Counts vessels in 10nm / 50nm / 200nm rings and reports avg SOG per ring.
--
-- Replace YOUR_DATA_BUCKET below before running.
-- Example:
--   aws athena start-query-execution \
--     --query-string file://athena/queries/feature_vessel_inbound_hourly.sql \
--     --query-execution-context Database=dpl_pilot \
--     --result-configuration OutputLocation=s3://.../athena/query-results/

-- REBUILDABLE: features_lambda runs DROP TABLE + clears the S3 prefix before
-- this CREATE, so a re-run refreshes data instead of silently skipping. Run
-- manually only after dropping the table and emptying its external_location.
CREATE TABLE dpl_pilot.feature_vessel_inbound_hourly
WITH (
    format = 'PARQUET',
    partitioned_by = ARRAY['date_partition'],
    external_location =
      's3://dpl-serverless-pilot-861276086413-pilot-data/curated/feature_vessel_inbound_hourly/'
)
AS
WITH port_coords AS (
    SELECT port_code, lat, lon
    FROM (VALUES
        ('NLRTM',  51.9225,    4.4792),
        ('SGSIN',   1.2644,  103.8198),
        ('USLAX',  33.7405, -118.2728),
        ('CNSHA',  30.6267,  121.9851),
        ('DEHAM',  53.5425,    9.9663),
        ('BEANR',  51.2194,    4.4025),
        ('GBFXT',  51.9500,    1.3500),
        ('AEDXB',  24.9857,   55.0272),
        ('USNYC',  40.6892,  -74.0445),
        ('TWKHH',  22.6163,  120.2650)
    ) AS t(port_code, lat, lon)
),
hourly_positions AS (
    SELECT
        mmsi,
        date_trunc('hour', from_iso8601_timestamp(received_at)) AS observation_hour,
        max_by(lat,    from_iso8601_timestamp(received_at)) AS lat,
        max_by(lon,    from_iso8601_timestamp(received_at)) AS lon,
        max_by(sog,    from_iso8601_timestamp(received_at)) AS sog,
        max(date) AS date_partition
    FROM raw_ais_positions
    WHERE date >= date_format(current_date - INTERVAL '90' DAY, '%Y-%m-%d')
    GROUP BY mmsi, date_trunc('hour', from_iso8601_timestamp(received_at))
),
scored AS (
    SELECT
        p.port_code,
        h.observation_hour,
        h.sog,
        3440.065 * 2 * asin(sqrt(
            power(sin(radians(h.lat - p.lat) / 2), 2) +
            cos(radians(p.lat)) * cos(radians(h.lat)) *
            power(sin(radians(h.lon - p.lon) / 2), 2)
        )) AS distance_nm,
        h.date_partition
    FROM hourly_positions h
    CROSS JOIN port_coords p
)
SELECT
    port_code,
    observation_hour,
    sum(CASE WHEN distance_nm <= 10  THEN 1 ELSE 0 END) AS vessels_in_10nm,
    sum(CASE WHEN distance_nm <= 50  THEN 1 ELSE 0 END) AS vessels_in_50nm,
    sum(CASE WHEN distance_nm <= 200 THEN 1 ELSE 0 END) AS vessels_in_200nm,
    sum(CASE WHEN distance_nm <= 10 AND sog < 2 THEN 1 ELSE 0 END) AS vessels_at_anchor,
    avg(CASE WHEN distance_nm <= 50  THEN sog END) AS avg_speed_50nm,
    date_partition
FROM scored
WHERE distance_nm <= 200
GROUP BY port_code, observation_hour, date_partition
