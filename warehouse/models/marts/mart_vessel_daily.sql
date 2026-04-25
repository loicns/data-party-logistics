-- mart_vessel_daily: daily vessel behavior aggregations.
--
-- GRAIN: one row per (mmsi, calendar_date)
-- Example: "On 2026-04-12, vessel 636019825 had average speed 14.2 knots, ..."
-- MATERIALIZATION: table (physical storage, fast reads)

--   Input:  staging.stg_ais_positions (clean AIS data)
--   Output: marts.mart_vessel_daily
--   Read by: features/vessel_features.py (Week 5) — computes ML features

{{ config(materialized='table') }}  -- Override the default 'view' from dbt_project.yml

WITH positions AS (
    SELECT * FROM {{ ref('stg_ais_positions') }}
),

-- Aggregate: one row per vessel per day
daily_stats AS (
    SELECT
        mmsi,
        -- DATE_TRUNC truncates timestamp to the day boundary
        -- "2026-04-12 14:30:00" → "2026-04-12 00:00:00"
        DATE_TRUNC('day', observed_at) AS activity_date,

        -- Position count: proxy for AIS transponder activity level
        COUNT(*) AS position_count,

        -- Speed statistics: key ETA prediction features
        -- AVG: typical speed on this day
        AVG(speed_knots) AS avg_speed_knots,
        -- STDDEV: speed variability — high variability means stops/starts = congestion
        STDDEV(speed_knots) AS speed_stddev_knots,
        MAX(speed_knots) AS max_speed_knots,
        MIN(speed_knots) AS min_speed_knots,

        -- Navigation status proportions
        -- "% time at anchor" is a strong congestion signal
        -- SUM(CASE WHEN...) / COUNT(*) = proportion (between 0 and 1)
        SUM(CASE WHEN nav_status = 'At anchor' THEN 1.0 ELSE 0.0 END) / NULLIF(COUNT(*), 0)
            AS pct_time_at_anchor,

        SUM(CASE WHEN nav_status = 'Moored' THEN 1.0 ELSE 0.0 END) / NULLIF(COUNT(*), 0)
            AS pct_time_moored,

        -- Last known position (for distance calculations in feature engineering)
        -- ARRAY_AGG + [1] is a PostgreSQL idiom for "last value ordered by timestamp"
        -- Alternative: a window function subquery, but this is more readable here
        (ARRAY_AGG(latitude ORDER BY observed_at DESC))[1] AS last_latitude,
        (ARRAY_AGG(longitude ORDER BY observed_at DESC))[1] AS last_longitude,

        -- Join key for dim_date: integer YYYYMMDD
        (ARRAY_AGG(date_key ORDER BY observed_at DESC))[1] AS date_key
    FROM positions
    GROUP BY mmsi, DATE_TRUNC('day', observed_at)
)

SELECT
    mmsi,
    activity_date,
    position_count,
    avg_speed_knots,
    speed_stddev_knots,
    max_speed_knots,
    min_speed_knots,
    pct_time_at_anchor,
    pct_time_moored,
    last_latitude,
    last_longitude,
    date_key
FROM daily_stats
WHERE position_count >= 2
