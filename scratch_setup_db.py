import psycopg
from ingestion.config import settings

conn = psycopg.connect(
    host=settings.postgres_host,
    port=settings.postgres_port,
    dbname=settings.postgres_db,
    user=settings.postgres_user,
    password=settings.postgres_password,
    autocommit=True,
)

with conn.cursor() as cur:
    cur.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
    print("PostGIS extension created.")

    queries = [
        "CREATE SCHEMA IF NOT EXISTS raw;",
        """
        CREATE TABLE IF NOT EXISTS raw.raw_ais_positions (
            mmsi        BIGINT NOT NULL,
            vessel_name TEXT,
            ship_type   TEXT,
            latitude    DOUBLE PRECISION,
            longitude   DOUBLE PRECISION,
            speed_knots DOUBLE PRECISION,
            course_deg  DOUBLE PRECISION,
            heading_deg DOUBLE PRECISION,
            nav_status  TEXT,
            timestamp   TIMESTAMPTZ NOT NULL,
            _loaded_at  TIMESTAMPTZ DEFAULT now()
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS raw.raw_comtrade_flows (
            reporter_code  TEXT,
            reporter_desc  TEXT,
            partner_code   TEXT,
            partner_desc   TEXT,
            flow_code      TEXT,
            flow_desc      TEXT,
            cmd_code       TEXT,
            cmd_desc       TEXT,
            period         TEXT,
            primary_value  DOUBLE PRECISION,
            net_wgt        DOUBLE PRECISION,
            qty            DOUBLE PRECISION,
            _loaded_at     TIMESTAMPTZ DEFAULT now()
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS raw.raw_weather_observations (
            port_code           TEXT NOT NULL,
            observation_hour    TIMESTAMPTZ NOT NULL,
            wave_height_m       DOUBLE PRECISION,
            wave_period_s       DOUBLE PRECISION,
            wave_direction_deg  DOUBLE PRECISION,
            wind_speed_kmh      DOUBLE PRECISION,
            wind_direction_deg  DOUBLE PRECISION,
            visibility_km       DOUBLE PRECISION,
            _loaded_at          TIMESTAMPTZ DEFAULT now()
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS raw.raw_gdelt_events (
            event_id   TEXT NOT NULL,
            event_date DATE NOT NULL,
            source_url TEXT,
            event_code TEXT,
            lat        DOUBLE PRECISION,
            lon        DOUBLE PRECISION,
            _loaded_at TIMESTAMPTZ DEFAULT now()
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS raw.raw_fred_indicators (
            series_id        TEXT NOT NULL,
            observation_date DATE NOT NULL,
            value            DOUBLE PRECISION,
            _loaded_at       TIMESTAMPTZ DEFAULT now()
        );
        """,
    ]
    for q in queries:
        cur.execute(q)
    print("Tables created.")
conn.close()
