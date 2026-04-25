-- stg_fred_indicators: clean FRED macroeconomic time series.
--
-- GRAIN: one row per (series_id, observation_date)
-- Examples: GSCPI on 2026-04-01, DCOILWTICO on 2026-04-01
--
-- ARCHITECTURE ROLE:
--   Input:  raw.raw_fred_indicators
--   Output: staging.stg_fred_indicators
--   Used by: mart_trade_features.sql, features/macro_features.py (Week 5)
--             add_macro_features() in build_training_set.py (Week 5)

WITH source AS (
    SELECT * FROM {{ source('raw', 'raw_fred_indicators') }}
),

deduplicated AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY series_id, observation_date   -- One value per series per date
            ORDER BY _loaded_at ASC
        ) AS _row_num
    FROM source
    WHERE series_id IS NOT NULL
      AND observation_date IS NOT NULL
      -- FRED uses "." to represent missing values — we filtered these in the client
      -- but add a safety check here
      AND value IS NOT NULL
),

final AS (
    SELECT
        series_id,
        observation_date::date AS observation_date,
        value::float AS value,
        _loaded_at
    FROM deduplicated
    WHERE _row_num = 1
)

SELECT * FROM final
