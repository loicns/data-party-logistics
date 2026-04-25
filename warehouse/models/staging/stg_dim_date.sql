-- stg_dim_date: calendar date dimension.
-- Shipping patterns have strong weekly, monthly, and seasonal cycles:
-- - Vessels slow down before Chinese New Year (factories shut, no urgency)
-- - Holiday weeks see reduced port operations (reduced staffing)
-- - Year-end sees inventory restocking rushes
--
-- Without a date dimension, you'd compute day_of_week, is_holiday, etc.
-- in every single query. With this table, one JOIN gives you all temporal attributes.
--
-- MATERIALIZATION: table (not a view — this reference data changes rarely)
-- ARCHITECTURE ROLE: Used by all mart models that need temporal context.

WITH date_series AS (
    -- generate_series: PostgreSQL function that generates a sequence of values
    -- Here: one date per day from 2020-01-01 to 2030-12-31
    -- This is the PostgreSQL alternative to CROSS JOIN date_spine tricks used in other databases
    SELECT generate_series(
        '2020-01-01'::date,   -- Start date: before our project began
        '2030-12-31'::date,   -- End date: future-proofs the dimension
        '1 day'::interval     -- Step: one day at a time
    )::date AS full_date
)

SELECT
    -- date_key: integer YYYYMMDD — used as the foreign key in fact tables
    -- Integer comparisons are faster than timestamp comparisons
    TO_CHAR(full_date, 'YYYYMMDD')::INT AS date_key,
    full_date,
    EXTRACT(YEAR FROM full_date)::INT AS year,
    EXTRACT(MONTH FROM full_date)::INT AS month,
    EXTRACT(DAY FROM full_date)::INT AS day,
    -- DOW: 0 = Sunday, 1 = Monday, ..., 6 = Saturday (PostgreSQL convention)
    EXTRACT(DOW FROM full_date)::INT AS day_of_week,
    TO_CHAR(full_date, 'Day') AS day_name,     -- "Monday", "Tuesday", etc.
    EXTRACT(WEEK FROM full_date)::INT AS week_of_year,
    EXTRACT(QUARTER FROM full_date)::INT AS quarter,
    -- is_weekday: vessels and ports operate differently on weekends
    CASE WHEN EXTRACT(DOW FROM full_date) IN (0, 6) THEN FALSE ELSE TRUE END AS is_weekday,
    TO_CHAR(full_date, 'YYYY-MM') AS year_month   -- "2026-04" for monthly aggregations
FROM date_series