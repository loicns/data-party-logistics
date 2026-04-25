"""Carrier adapter registry.

Usage:
    from ingestion.clients.carriers import get_adapter
    adapter = get_adapter("maersk")
    eta = await adapter.get_vessel_eta("9703291")
"""

from ingestion.clients.carriers.base import (
    CarrierAdapter,  # Abstract base class — all adapters implement this
    NullAdapter,  # Placeholder adapter for carriers with no integration yet
)
from ingestion.clients.carriers.maersk import MaerskAdapter
from ingestion.clients.carriers.msc_scraper import MSCScrapingAdapter
from ingestion.config import settings  # Singleton settings object — reads from .env


def get_all_adapters() -> dict[str, CarrierAdapter]:
    """Return one adapter per carrier, configured from settings.

    The FastAPI handler calls this once at startup and stores the dict.
    Order matters only for display — Maersk first (highest API reliability).

    WHY A DICT INSTEAD OF if/elif?
    The dict-based registry means adding a new carrier = one line here.
    No handler code changes. No routing logic changes. The new carrier just appears
    in the dict and every downstream consumer sees it automatically.
    With if/elif, you'd need to update at least 3 files per new carrier.
    This is the Open/Closed Principle: open for extension, closed for modification.
    """
    return {
        "maersk": MaerskAdapter(settings),
        # Maersk: official API, highest confidence, highest rate limit
        "cma-cgm": NullAdapter("cma-cgm", reason="business_account_required"),
        # CMA CGM: official API, high confidence
        "msc": MSCScrapingAdapter(),
        # MSC: no public API — Playwright scraping, confidence='scraped'
        # No api_key argument — scraping needs no credentials
        "hapag-lloyd": NullAdapter("hapag-lloyd", reason="business_account_required"),
        # Hapag-Lloyd has an API but requires a paid business account.
        # NullAdapter logs a warning and returns None — tracked in data audit.
        "cosco": NullAdapter("cosco", reason="no_public_api"),
        # COSCO has no public API and their tracking page uses aggressive bot detection.
        # Scraping not attempted — would require CAPTCHA bypass (unethical).
        "evergreen": NullAdapter("evergreen", reason="no_public_api"),
        # Evergreen: same situation as COSCO.
        # Future work: monitor for API announcements.
    }


def get_adapter(carrier: str) -> CarrierAdapter:
    """Get a single adapter by carrier name.

    Raises KeyError if carrier is not in the registry — fail fast.
    Use get_all_adapters() if you need to iterate over all carriers.
    """
    adapters = get_all_adapters()
    if carrier not in adapters:
        raise KeyError(
            f"Unknown carrier '{carrier}'. "
            f"Registered carriers: {sorted(adapters.keys())}"
        )
    return adapters[carrier]
