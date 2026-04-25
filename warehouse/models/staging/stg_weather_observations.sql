-- stg_weather_observations: clean hourly marine weather per port.
--
-- GRAIN: one row per (port_code, observation_hour)
-- Source: ingestion/clients/weather.py fetches Open-Meteo marine API hourly
--
-- ARCHITECTURE ROLE:
--   Input:  raw.raw_weather_observations
--   Output: staging.stg_weather_observations
--   Used by: mart_port_congestion_daily.sql (joins weather to congestion scores)
--             features/port_features.py (Week 5)

WITH source AS (
    SELECT * FROM {{ source('raw', 'raw_weather_observations') }}
),

deduplicated AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY port_code, observation_hour    -- One weather record per port per hour
            ORDER BY _loaded_at ASC
        ) AS _row_num
    FROM source
    WHERE port_code IS NOT NULL
),

final AS (
    SELECT
        port_code,
        observation_hour::timestamptz AS observed_at,
        wave_height_m,
        wave_period_s,
        wave_direction_deg,
        wind_speed_kmh,
        wind_direction_deg,
        visibility_km,
        -- Derived feature: binary flag for operationally significant wave height
        -- Ships delay berthing when waves > 2.5m — this threshold is from IMO guidelines
        CASE WHEN wave_height_m > 2.5 THEN TRUE ELSE FALSE END AS had_severe_waves,
        _loaded_at
    FROM deduplicated
    WHERE _row_num = 1
)

SELECT * FROM final
