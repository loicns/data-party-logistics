--   Input:  raw.raw_comtrade_flows
--   Output: staging.stg_comtrade_flows
--   Used by: mart_trade_features.sql → features/macro_features.py (Week 5)

WITH source AS (
    SELECT * FROM {{ source('raw', 'raw_comtrade_flows') }}
),

deduplicated AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY reporter_code, partner_code, cmd_code, period, flow_code
            ORDER BY _loaded_at ASC
        ) AS _row_num
    FROM source
),

final AS (
    SELECT
        reporter_code,
        reporter_desc,
        partner_code,
        partner_desc,
        flow_code AS flow_direction,   -- "M" = imports, "X" = exports
        flow_desc,
        cmd_code AS hs_code,           -- Harmonized System commodity code
        cmd_desc AS commodity_description,
        period,                         -- "202404" = April 2024 (YYYYMM format)

        -- These columns may be NULL for some country/commodity combinations
        -- Downstream models handle NULLs with COALESCE or feature imputation (Week 5/6)
        primary_value AS trade_value_usd,
        net_wgt AS net_weight_kg,
        qty AS quantity,
        _loaded_at
    FROM deduplicated
    WHERE _row_num = 1
)

SELECT * FROM final