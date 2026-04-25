-- stg_ais_positions: clean, deduplicated AIS vessel position reports.
--
-- MATERIALIZATION: view (re-computed on every query, no storage cost)
-- Mart models (mart_vessel_daily) read FROM this view and are materialized as tables.

--   Input:  raw.raw_ais_positions (loaded from S3 by dbt_flow.py)
--   Output: staging.stg_ais_positions (consumed by mart models + feature engineering)
--   Used by: mart_vessel_daily.sql, mart_port_congestion_daily.sql,

WITH source AS (
    SELECT * FROM {{ source('raw', 'raw_ais_positions') }}
),
deduplicated AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY mmsi, timestamp
            ORDER BY _loaded_at ASC
        ) AS _row_num
    FROM source
    WHERE mmsi IS NOT NULL
      AND timestamp IS NOT NULL
      AND latitude IS NOT NULL
      AND longitude IS NOT NULL
      AND latitude BETWEEN -90 AND 90
      AND longitude BETWEEN -180 AND 180
),

final AS (
    SELECT
        mmsi,
        vessel_name,
        ship_type,
        latitude,
        longitude,
        speed_knots,
        course_deg,
        heading_deg,
        nav_status,
        timestamp::timestamptz AS observed_at,
        TO_CHAR(timestamp::timestamptz, 'YYYYMMDD')::INT AS date_key,
        _loaded_at
    FROM deduplicated
    WHERE _row_num = 1
)

SELECT * FROM final
