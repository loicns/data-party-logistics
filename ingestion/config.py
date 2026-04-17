"""Central configuration for the ingestion layer."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    """Immutable settings loaded from environment variables."""

    # AWS
    aws_region: str = os.getenv("AWS_REGION", "eu-west-3")
    aws_profile: str = os.getenv("AWS_PROFILE", "dpl")
    s3_bucket_raw: str = os.getenv("S3_BUCKET_RAW", "")

    # API keys
    aisstream_api_key: str = os.getenv("AISSTREAM_API_KEY", "")
    fred_api_key: str = os.getenv("FRED_API_KEY", "")
    noaa_api_token: str = os.getenv("NOAA_API_TOKEN", "")
    cmems_username: str = os.getenv("CMEMS_USERNAME", "")
    cmems_password: str = os.getenv("CMEMS_PASSWORD", "")

    def validate(self) -> None:
        """Raise if critical settings are missing."""
        if not self.s3_bucket_raw:
            msg = "S3_BUCKET_RAW is not set in .env"
            raise ValueError(msg)


settings = Settings()
