"""Shared configuration for all ingestion clients.

Loads settings from environment variables via pydantic-settings.
Actual values live in .env (gitignored); structure is documented in .env.example.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # AWS
    aws_region: str = "eu-west-3"
    aws_profile: str = "dpl"
    s3_bucket_raw: str = "data-party-logistics-raw"

    # AISStream
    aisstream_api_key: str = ""

    # FRED
    fred_api_key: str = ""

    # NOAA
    noaa_api_token: str = ""

    # Anthropic (Week 8)
    anthropic_api_key: str = ""

    # Postgres (Week 3)
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "dpl_dev"
    postgres_user: str = "dpl"
    postgres_password: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()