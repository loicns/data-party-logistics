"""Tests for MSCScrapingAdapter.

We do NOT write integration tests that actually launch Chromium and hit MSC's website.
Integration tests that depend on a third-party website's availability and structure
are not reliable in CI. The website could be down, MSC could have changed their HTML,
or the test could take 30+ seconds per run. Instead, test the logic with mocked Playwright.

WHAT WE TEST:
    - _parse_msc_date() correctly parses all expected date formats
    - _parse_msc_date() returns None for unrecognised formats (doesn't raise)
    - MSCScrapingAdapter.get_vessel_eta() returns None when PlaywrightTimeoutError is raised
    - MSCScrapingAdapter.get_service_schedule() always returns an empty list
"""

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
from ingestion.clients.carriers.msc_scraper import (
    MSCScrapingAdapter,
    _parse_msc_date,
)

# ─── _parse_msc_date tests ────────────────────────────────────────────────────


def test_parse_msc_date_dd_mmm_yyyy():
    """Parses 'DD MMM YYYY' format (most common MSC format)."""
    result = _parse_msc_date("18 Apr 2026")
    assert result == datetime(2026, 4, 18)


def test_parse_msc_date_dd_slash_mm_slash_yyyy():
    """Parses 'DD/MM/YYYY' format (European numeric format)."""
    result = _parse_msc_date("18/04/2026")
    assert result == datetime(2026, 4, 18)


def test_parse_msc_date_strips_whitespace():
    """Leading/trailing whitespace from scraped text is handled."""
    result = _parse_msc_date("  18 Apr 2026  ")
    assert result == datetime(2026, 4, 18)


def test_parse_msc_date_unrecognised_format_returns_none():
    """Returns None (does not raise) for unrecognised date strings."""
    result = _parse_msc_date("April 18, 2026")  # US long format — not in our parser
    assert result is None


def test_parse_msc_date_empty_string_returns_none():
    """Empty string (e.g., missing ETA) returns None gracefully."""
    result = _parse_msc_date("")
    assert result is None


# ─── MSCScrapingAdapter.get_service_schedule tests ───────────────────────────


@pytest.mark.asyncio
async def test_get_service_schedule_always_empty():
    """Service schedule always returns empty list — scraping not supported for MSC schedules."""
    adapter = MSCScrapingAdapter()
    result = await adapter.get_service_schedule("AE-1")
    assert result == []


# ─── MSCScrapingAdapter.get_vessel_eta tests (mocked Playwright) ─────────────


@pytest.mark.asyncio
@patch("ingestion.clients.carriers.msc_scraper.async_playwright")
@patch("ingestion.clients.carriers.msc_scraper.asyncio.sleep", new_callable=AsyncMock)
async def test_get_vessel_eta_returns_none_on_selector_timeout(
    mock_sleep, mock_playwright_ctx
):
    """Returns None (does not raise) when Playwright times out waiting for ETA selector.

    This simulates the most common failure mode: MSC updated their frontend
    and ETA_SELECTOR no longer exists in the DOM.

    Mocking strategy:
    - mock_sleep: skip the 3-second delay so the test runs instantly
    - mock_playwright_ctx: replace async_playwright() with a controlled mock
      that raises PlaywrightTimeoutError when wait_for_selector is called
    """
    from playwright.async_api import TimeoutError as PTE

    # Build the mock chain: async_playwright().__aenter__().chromium.launch() → browser
    mock_page = AsyncMock()
    mock_page.goto = AsyncMock()
    mock_page.set_extra_http_headers = AsyncMock()
    mock_page.wait_for_selector = AsyncMock(side_effect=PTE("selector timeout"))
    # side_effect=PTE(...) means wait_for_selector() raises PlaywrightTimeoutError
    # This is exactly what happens when MSC's HTML changes and the selector disappears.

    mock_browser = AsyncMock()
    mock_browser.new_page = AsyncMock(return_value=mock_page)
    mock_browser.close = AsyncMock()

    mock_chromium = AsyncMock()
    mock_chromium.launch = AsyncMock(return_value=mock_browser)

    mock_playwright_instance = AsyncMock()
    mock_playwright_instance.chromium = mock_chromium

    mock_playwright_ctx.return_value.__aenter__ = AsyncMock(
        return_value=mock_playwright_instance
    )
    mock_playwright_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

    adapter = MSCScrapingAdapter()
    result = await adapter.get_vessel_eta("9703291")

    assert result is None  # Must return None, not raise
    mock_browser.close.assert_called_once()  # Browser must be closed even on failure


@pytest.mark.asyncio
@patch("ingestion.clients.carriers.msc_scraper.async_playwright")
@patch("ingestion.clients.carriers.msc_scraper.asyncio.sleep", new_callable=AsyncMock)
async def test_get_vessel_eta_returns_vessel_eta_on_success(
    mock_sleep, mock_playwright_ctx
):
    """Returns VesselETA with confidence=SCRAPED when page loads and selector is found."""
    from ingestion.clients.carriers.base import Confidence

    mock_page = AsyncMock()
    mock_page.goto = AsyncMock()
    mock_page.set_extra_http_headers = AsyncMock()
    mock_page.wait_for_selector = AsyncMock()  # No exception = selector found
    mock_page.inner_text = AsyncMock(return_value="18 Apr 2026")  # Simulated ETA text

    mock_browser = AsyncMock()
    mock_browser.new_page = AsyncMock(return_value=mock_page)
    mock_browser.close = AsyncMock()

    mock_chromium = AsyncMock()
    mock_chromium.launch = AsyncMock(return_value=mock_browser)

    mock_playwright_instance = AsyncMock()
    mock_playwright_instance.chromium = mock_chromium

    mock_playwright_ctx.return_value.__aenter__ = AsyncMock(
        return_value=mock_playwright_instance
    )
    mock_playwright_ctx.return_value.__aexit__ = AsyncMock(return_value=False)

    adapter = MSCScrapingAdapter()
    result = await adapter.get_vessel_eta("9703291")

    assert result is not None
    assert result.imo == "9703291"
    assert result.carrier == "msc"
    assert result.confidence == Confidence.SCRAPED  # Must always be SCRAPED
    assert result.eta == datetime(2026, 4, 18)
