-- feature_vessel_state_hourly
-- Additive AIS v2 table: one row per (port_code, observation_hour, mmsi).
-- This keeps v1 tables unchanged while adding conservative vessel state,
-- trajectory direction, and optional voyage/static context.

CREATE TABLE dpl_pilot.feature_vessel_state_hourly
WITH (
    format = 'PARQUET',
    partitioned_by = ARRAY['date_partition'],
    external_location =
      's3://dpl-serverless-pilot-861276086413-pilot-data/curated/feature_vessel_state_hourly/'
)
AS
WITH port_coords AS (
    SELECT port_code, port_name, lat, lon
    FROM (VALUES
        ('NLRTM', 'Rotterdam',   51.9225,    4.4792),
        ('SGSIN', 'Singapore',    1.2644,  103.8198),
        ('USLAX', 'Los Angeles', 33.7405, -118.2728),
        ('CNSHA', 'Shanghai',    30.6267,  121.9851),
        ('DEHAM', 'Hamburg',     53.5425,    9.9663),
        ('BEANR', 'Antwerp',     51.2194,    4.4025),
        ('GBFXT', 'Felixstowe',  51.9500,    1.3500),
        ('AEDXB', 'Dubai',       24.9857,   55.0272),
        ('USNYC', 'New York',    40.6892,  -74.0445),
        ('TWKHH', 'Kaohsiung',   22.6163,  120.2650)
    ) AS t(port_code, port_name, lat, lon)
),
hourly_positions AS (
    SELECT
        mmsi,
        date_trunc(
            'hour',
            CAST(from_iso8601_timestamp(received_at) AS timestamp)
        ) AS observation_hour,
        max_by(ship_name, from_iso8601_timestamp(received_at)) AS ship_name,
        max_by(lat, from_iso8601_timestamp(received_at)) AS lat,
        max_by(lon, from_iso8601_timestamp(received_at)) AS lon,
        max_by(sog, from_iso8601_timestamp(received_at)) AS sog,
        max_by(cog, from_iso8601_timestamp(received_at)) AS cog,
        max_by(true_heading, from_iso8601_timestamp(received_at)) AS true_heading,
        max_by(nav_status, from_iso8601_timestamp(received_at)) AS nav_status,
        max(date) AS date_partition
    FROM raw_ais_positions
    WHERE date >= date_format(current_date - INTERVAL '90' DAY, '%Y-%m-%d')
    GROUP BY
        mmsi,
        date_trunc('hour', CAST(from_iso8601_timestamp(received_at) AS timestamp))
),
scored AS (
    SELECT
        p.port_code,
        p.port_name,
        h.observation_hour,
        h.mmsi,
        h.ship_name,
        h.lat,
        h.lon,
        h.sog,
        h.cog,
        h.true_heading,
        h.nav_status,
        3440.065 * 2 * asin(sqrt(
            power(sin(radians(h.lat - p.lat) / 2), 2) +
            cos(radians(p.lat)) * cos(radians(h.lat)) *
            power(sin(radians(h.lon - p.lon) / 2), 2)
        )) AS distance_nm,
        h.date_partition
    FROM hourly_positions h
    CROSS JOIN port_coords p
),
with_trajectory AS (
    SELECT
        *,
        distance_nm - lag(distance_nm) OVER (
            PARTITION BY port_code, mmsi
            ORDER BY observation_hour
        ) AS distance_delta_nm
    FROM scored
    WHERE distance_nm <= 200
),
voyage_records AS (
    SELECT
        mmsi,
        destination,
        eta_timestamp_utc,
        draught_m,
        ship_type,
        CAST(from_iso8601_timestamp(received_at) AS timestamp) AS received_ts
    FROM raw_ais_voyage
    WHERE date >= date_format(current_date - INTERVAL '90' DAY, '%Y-%m-%d')
),
joined_voyage AS (
    SELECT
        t.*,
        v.destination,
        v.eta_timestamp_utc,
        v.draught_m,
        v.ship_type,
        row_number() OVER (
            PARTITION BY t.port_code, t.observation_hour, t.mmsi
            ORDER BY v.received_ts DESC NULLS LAST
        ) AS voyage_rank
    FROM with_trajectory t
    LEFT JOIN voyage_records v
        ON t.mmsi = v.mmsi
       AND v.received_ts < t.observation_hour + INTERVAL '1' HOUR
),
enriched AS (
    SELECT
        *,
        CASE
            WHEN destination IS NULL THEN false
            WHEN lower(destination) LIKE concat('%', lower(port_code), '%')
              OR lower(destination) LIKE concat('%', lower(port_name), '%')
              OR lower(destination) LIKE concat('%', lower(substr(port_code, 3)), '%')
            THEN true
            ELSE false
        END AS destination_matches_port,
        CASE
            WHEN eta_timestamp_utc IS NULL THEN false
            WHEN CAST(from_iso8601_timestamp(eta_timestamp_utc) AS timestamp)
              BETWEEN observation_hour AND observation_hour + INTERVAL '48' HOUR
            THEN true
            ELSE false
        END AS eta_within_48h
    FROM joined_voyage
    WHERE voyage_rank = 1
)
SELECT
    port_code,
    observation_hour,
    mmsi,
    ship_name,
    lat,
    lon,
    sog,
    cog,
    true_heading,
    nav_status,
    distance_nm,
    distance_delta_nm,
    destination,
    eta_timestamp_utc,
    draught_m,
    ship_type,
    destination_matches_port,
    eta_within_48h,
    CASE
        WHEN distance_nm <= 15 AND coalesce(nav_status, 15) = 5
            THEN 'at_berth'
        WHEN distance_delta_nm > 0.5
            THEN 'outbound'
        WHEN distance_nm <= 30
         AND (
            coalesce(nav_status, 15) = 1
            OR (
                coalesce(sog, 0) <= 0.5
                AND (distance_delta_nm IS NULL OR distance_delta_nm <= 0.25)
            )
         )
            THEN 'waiting_anchor'
        WHEN distance_delta_nm < -0.5
          OR (destination_matches_port AND eta_within_48h)
            THEN 'inbound'
        ELSE 'transit_unknown'
    END AS vessel_state,
    date_partition
FROM enriched
