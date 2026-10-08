"""Checks and establishes the LinkedIn session stored in the dedicated browser profile."""

import re

from playwright.sync_api import BrowserContext

from app.config import Settings
from app.scraping.browser import browser_manager

FEED_URL = "https://www.linkedin.com/feed/"
LOGIN_TIMEOUT_MS = 5 * 60 * 1000


def _has_session_cookie(ctx: BrowserContext) -> bool:
    return any(c["name"] == "li_at" for c in ctx.cookies("https://www.linkedin.com"))


def is_logged_in_ctx(ctx: BrowserContext) -> bool:
    if not _has_session_cookie(ctx):
        return False
    resp = ctx.request.get(FEED_URL, max_redirects=0, fail_on_status_code=False)
    return resp.status == 200


def check_session(settings: Settings) -> bool:
    if not settings.profile_dir.exists():
        return False
    return is_logged_in_ctx(browser_manager.context(settings, headless=settings.headless))


def interactive_login(settings: Settings) -> bool:
    """Opens a visible window so the user signs in on the real LinkedIn page (Google SSO works)."""
    ctx = browser_manager.context(settings, headless=False)
    try:
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(FEED_URL)
        if "/feed" not in page.url:
            page.wait_for_url(re.compile(r"linkedin\.com/feed"), timeout=LOGIN_TIMEOUT_MS)
        return is_logged_in_ctx(ctx)
    except Exception:
        return False
    finally:
        browser_manager.close()  # back to headless for the next operations
