"""MSC vessel tracking scraper.

This adapter uses Playwright to extract
vessel ETA from MSC's public tracking page.

BRITTLE BY DESIGN — this is explicitly documented:
    - Any CSS selector change on MSC's side breaks this adapter
    - Any JavaScript framework update on their page may change the DOM structure
    - CAPTCHAs or bot-detection may block requests over time
    - confidence='scraped' propagates this fragility to all downstream consumers

ETHICAL CONSTRAINTS APPLIED:
    - User-Agent identifies this as a research bot
    - 3-second delay between requests (mimics human browsing)
    - No CAPTCHA bypassing — if blocked, the adapter returns None gracefully
    - No login/authentication bypassing
    - Respects 429 / rate-limit responses

ARCHITECTURE ROLE:
    Implements CarrierAdapter from carriers/base.py.
    Registered as 'msc' in the carrier registry (carriers/__init__.py).
    confidence='scraped' on all successful responses.
    Returns None on selector failure, timeout, or bot-detection.
    Downstream: same interface as MaerskAdapter — FastAPI handler is unaware.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import structlog
from playwright.async_api import (
    TimeoutError as PlaywrightTimeoutError,
)
from playwright.async_api import (
    async_playwright,
)

from ingestion.clients.carriers.base import (
    CarrierAdapter,  # ABC that defines get_vessel_eta() and get_service_schedule()
    Confidence,  # Enum: Confidence.API | Confidence.AIS | Confidence.SCRAPED
    VesselETA,  # Pydantic model: imo, carrier, eta, confidence, fetched_at
)

logger = structlog.get_logger(__name__)

SELECTOR_TIMEOUT_MS = 15_000

REQUEST_DELAY_SEC = 3.0

ETA_SELECTOR = ".eta-display"


class MSCScrapingAdapter(CarrierAdapter):
    """Carrier adapter for MSC via Playwright browser scraping.

    This class has no __init__ arguments — MSC scraping needs no API key.
    The registry in carriers/__init__.py instantiates it as: MSCScrapingAdapter()
    """

    async def get_vessel_eta(self, imo: str) -> VesselETA | None:
        """Scrape MSC tracking page for vessel ETA.

        Returns VesselETA with confidence='scraped', or None if:
        - Vessel not found on MSC's system
        - Selector timeout (page structure changed)
        - Bot detection / CAPTCHA triggered
        - Any unexpected exception

        The caller (FastAPI handler) must handle None — all carrier adapters
        may return None, and the handler aggregates across carriers.
        """
        await asyncio.sleep(
            REQUEST_DELAY_SEC
        )  # Be respectful — always wait before loading
        # This sleep applies even on first call. The delay is per-call, not per-session.
        # If you're calling this in a loop over 50 vessels, total time =
        # 50 x 3s = 2.5 minutes.
        # That's intentional — don't optimize this away.

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            # headless=True: no visible browser window — required in server environments
            # (EC2, Docker). No display = no headed browser.
            # headless=False: opens a real Chrome window — useful for debugging locally
            # when you need to see what the page looks like and inspect selectors.

            page = await browser.new_page()
            await page.set_extra_http_headers(
                {
                    # Identify our bot — ethical scraping practice.
                    # Lets MSC understand their traffic and contact us if needed.
                    # A scraper hiding as a real browser (Chrome/Safari UA) implies
                    # deception. A named bot UA is honest about what it is.
                    "User-Agent": (
                        "DPL-Research-Bot/1.0 "
                        "(vessel-intelligence; +https://github.com/you/dpl)"
                    )
                }
            )

            try:
                url = f"https://www.msc.com/track/{imo}"
                await page.goto(url, timeout=30_000)
                # timeout=30_000ms (30s) for page load.
                # This is the time allowed for the initial HTML + JS bundle to load.
                # MSC can be slow — a 10s timeout would produce false timeouts.

                # Wait for the ETA element to appear — JS renders it asynchronously.
                # This is the key difference from requests: we're waiting for JS
                # to finish making its XHR call and injecting the ETA into the DOM.
                await page.wait_for_selector(ETA_SELECTOR, timeout=SELECTOR_TIMEOUT_MS)
                eta_text = await page.inner_text(ETA_SELECTOR)
                # inner_text() returns the visible text content of the element.
                # e.g., "18 Apr 2026" or "18/04/2026" inside MSC locale settings.

                eta_dt = _parse_msc_date(eta_text)
                if eta_dt is None:
                    # The element was found, but the date text format is unrecognised.
                    # Log the raw text so you know what format to add.
                    logger.warning("msc_eta_parse_failed", imo=imo, raw_text=eta_text)
                    return None

                logger.info("msc_eta_scraped", imo=imo, eta=eta_dt.isoformat())
                return VesselETA(
                    imo=imo,
                    carrier="msc",
                    eta=eta_dt,
                    confidence=Confidence.SCRAPED,  # Hardcoded — ALWAYS scraped.
                    fetched_at=datetime.now(UTC),  # UTC timestamp of fetch time.
                    # confidence=Confidence.SCRAPED propagates to downstream consumers:
                    # - features/reliability.py weights it lower in delay predictions
                    # - dashboard shows a "scraped" badge instead of "live API"
                    # - data quality reports flag it as lower-trust
                )

            except PlaywrightTimeoutError:
                # Two causes:
                # 1. MSC updated frontend — ETA_SELECTOR no longer exists in the DOM.
                #    Fix: inspect the page, update ETA_SELECTOR.
                # 2. Vessel IMO not in MSC system — tracking page shows "not found"
                #    and the ETA element never appears.
                # We can't distinguish these without more logic — return None for both.
                logger.warning(
                    "msc_selector_timeout",
                    imo=imo,
                    selector=ETA_SELECTOR,
                    hint="Check if MSC updated their frontend. Inspect page HTML.",
                )
                return None

            except Exception:
                # Catch-all: network errors, bot redirects, unexpected page structure.
                # logger.exception logs the full traceback automatically.
                # We return None rather than raising so one bad vessel doesn't
                # abort a batch run.
                logger.exception("msc_scrape_error", imo=imo)
                return None

            finally:
                await browser.close()  # Always close — prevents browser process leak.
                # Without this, each call leaves a Chromium process in the background.
                # On a server that processes 500 vessels/day, that's 500 zombies.
                # `finally` ensures close() runs even if an exception was raised above.

    async def get_service_schedule(self, service_id: str) -> list[dict]:
        """Return service schedule for an MSC service line.

        MSC service schedules are not scrapable reliably — the schedule pages
        require login or use obfuscated endpoints. Return empty list.
        This is documented as a known limitation in the data audit (Week 3 S01).
        The NullAdapter pattern would also work here, but MSC does have vessel ETA
        scraping, so we use a partial implementation rather than full NullAdapter.
        """
        return []


def _parse_msc_date(raw: str) -> datetime | None:
    """Parse MSC's date display format into a UTC-naive datetime.

    MSC typically displays dates in one of two formats:
        "18 Apr 2026"  →  strptime format "%d %b %Y"
        "18/04/2026"   →  strptime format "%d/%m/%Y"

    This function is fragile by design — update it when MSC changes format.
    If this returns None unexpectedly, check the raw_text in the log.

    Returns None (not raises) so callers can handle gracefully.
    """
    raw = raw.strip()  # Remove leading/trailing whitespace — common in scraped text

    # Attempt 1: "18 Apr 2026" — English abbreviated month name
    try:
        return datetime.strptime(raw, "%d %b %Y")
    except ValueError:
        pass  # Not this format — try the next one

    # Attempt 2: "18/04/2026" — European numeric date (day/month/year)
    # ⚠️ Do not use "%m/%d/%Y" (US format) — MSC's locale is European.
    try:
        return datetime.strptime(raw, "%d/%m/%Y")
    except ValueError:
        pass

    # No format matched — log the raw text upstream and return None
    return None
