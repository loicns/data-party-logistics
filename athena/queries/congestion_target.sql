-- congestion_target
-- Binary label: is the port congested 24h from now?
--
-- A port is "congested" when vessels_at_anchor > the trailing-90-day
-- 75th percentile of that port's anchor count, AND > 2 vessels.
-- The label is shifted +24h so the model predicts the future.

-- REBUILDABLE: features_lambda drops + clears S3 before this CREATE.
CREATE TABLE dpl_pilot.congestion_target
WITH (
    format = 'PARQUET',
    partitioned_by = ARRAY['date_partition'],
    external_location =
      's3://dpl-serverless-pilot-861276086413-pilot-data/curated/congestion_target/'
)
AS
WITH anchor_counts AS (
    -- Reuse the export Lambda's anchor definition (slow + close in)
    SELECT
        port_code,
        observation_hour,
        vessels_at_anchor,
        date_partition
    FROM dpl_pilot.feature_vessel_inbound_hourly
),
trailing_p75 AS (
    SELECT
        port_code,
        approx_percentile(vessels_at_anchor, 0.75) AS p75_anchor
    FROM anchor_counts
    WHERE observation_hour >= CAST(current_timestamp AS timestamp) - INTERVAL '90' DAY
    GROUP BY port_code
),
labeled AS (
    SELECT
        a.port_code,
        -- The feature row at time T predicts the congestion state at T+24h.
        -- We label the feature by looking 24h FORWARD.
        a.observation_hour - INTERVAL '24' HOUR AS feature_hour,
        future.vessels_at_anchor AS future_anchor,
        t.p75_anchor,
        CASE
            WHEN future.vessels_at_anchor > t.p75_anchor
             AND future.vessels_at_anchor > 2
            THEN 1 ELSE 0
        END AS is_congested_24h,
        a.date_partition
    FROM anchor_counts a
    JOIN anchor_counts future
      ON future.port_code        = a.port_code
     AND future.observation_hour = a.observation_hour
    JOIN trailing_p75 t
      ON t.port_code = a.port_code
)
SELECT
    port_code,
    feature_hour AS observation_hour,
    future_anchor,
    p75_anchor,
    is_congested_24h,
    date_partition
FROM labeled
WHERE feature_hour IS NOT NULL
