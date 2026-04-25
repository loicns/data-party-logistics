-- mart_port_congestion_daily: daily port congestion metrics.
--
-- GRAIN: one row per (port_code, calendar_date)
-- Congestion score: continuous 0-1 metric. >0.5 = "congested" for the classifier.
--
-- MATERIALIZATION: table
--   Input:  stg_ais_positions + seeds.wpi_ports (port reference data)
--   Output: marts.mart_port_congestion_daily

{{ config(materialized='table') }}

WITH positions AS (
    SELECT * FROM {{ ref('stg_ais_positions') }}
),

ports AS (
    -- wpi_ports is a dbt seed: a static CSV file committed to the repo
    -- It contains the 10 target ports with coordinates and metadata
    SELECT * FROM {{ ref('wpi_ports') }}
),

weather AS (
    SELECT * FROM {{ ref('stg_weather_observations') }}
),

-- Identify which vessels are "near" each port on each day
-- "Near" = within ~0.3 degrees latitude/longitude of port center
-- 0.3 degrees ≈ 33km — covers the port approach and anchorage area
vessel_port_presence AS (
    SELECT
        p.port_code,
        DATE_TRUNC('day', a.observed_at) AS activity_date,
        a.mmsi,
        a.speed_knots,
        a.nav_status,
        a.observed_at
    FROM positions a
    -- CROSS JOIN: pair every vessel position with every port
    -- Then filter by proximity — this is the "spatial join" pattern for flat-earth approximation
    CROSS JOIN ports p
    WHERE ABS(a.latitude - p.latitude) < 0.3      -- Within ~33km north/south
      AND ABS(a.longitude - p.longitude) < 0.3    -- Within ~33km east/west
),

-- Aggregate to daily statistics per port
daily_port_stats AS (
    SELECT
        port_code,
        activity_date,
        COUNT(DISTINCT mmsi) AS total_vessels,     -- Unique vessels in the port zone today
        -- "At anchor" = waiting for berth = the definition of congestion
        COUNT(DISTINCT CASE WHEN nav_status = 'At anchor' THEN mmsi END) AS vessels_at_anchor,
        COUNT(DISTINCT CASE WHEN nav_status = 'Moored' THEN mmsi END) AS vessels_moored,
        AVG(speed_knots) AS avg_speed_in_zone     -- Very low average = vessels mostly waiting
    FROM vessel_port_presence
    GROUP BY port_code, activity_date
),

-- Join daily weather to port stats
with_weather AS (
    SELECT
        d.*,
        w.wave_height_m AS avg_wave_height_m,
        w.max_wave_height_m,
        w.had_severe_waves,
        -- "Disruption score" from GDELT news would go here (added in marts/mart_port_features.sql)
        0.0 AS disruption_score  -- Placeholder — joined in a higher-level mart
    FROM daily_port_stats d
    LEFT JOIN (
        -- Aggregate hourly weather to daily (one weather row per port per day)
        SELECT
            port_code,
            DATE_TRUNC('day', observed_at) AS weather_date,
            AVG(wave_height_m) AS wave_height_m,
            MAX(wave_height_m) AS max_wave_height_m,
            BOOL_OR(had_severe_waves) AS had_severe_waves  -- TRUE if ANY hour had severe waves
        FROM weather
        GROUP BY port_code, DATE_TRUNC('day', observed_at)
    ) w ON d.port_code = w.port_code AND d.activity_date = w.weather_date
)

SELECT
    port_code,
    activity_date,
    total_vessels,
    vessels_at_anchor,
    vessels_moored,
    avg_speed_in_zone,
    -- CONGESTION SCORE: 0 = no congestion, 1 = maximum congestion
    -- Formula: ratio of waiting vessels to total vessels
    -- Clamped to [0, 1] in case of data anomalies (LEAST/GREATEST)
    GREATEST(0.0, LEAST(1.0,
        CASE
            WHEN total_vessels = 0 THEN 0.0  -- No vessels = no congestion to measure
            ELSE vessels_at_anchor::float / total_vessels::float
        END
    )) AS congestion_score,
    avg_wave_height_m,
    max_wave_height_m,
    had_severe_waves,
    disruption_score
FROM with_weather