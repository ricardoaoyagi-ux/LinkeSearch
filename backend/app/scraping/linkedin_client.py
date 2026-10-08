"""Talks to LinkedIn through the logged-in browser context.

Search results are read from the rendered page; job details are fetched over plain HTTP with the
same cookies (no page JS runs, so LinkedIn does not record a "Viewed" for them).
"""

import json
import logging
from pathlib import Path
from urllib.parse import urlencode

from playwright.sync_api import BrowserContext, Page
from playwright.sync_api import TimeoutError as PlaywrightTimeout

from app.scraping import dom_scripts, parsers
from app.scraping.rsc import rsc_to_html

logger = logging.getLogger("uvicorn.error")

BASE = "https://www.linkedin.com"
SEARCH_URL = f"{BASE}/jobs/search-results/"
PAGE_SIZE = 25
_ABOUT_COMPONENT = "com.linkedin.sdui.generated.jobseeker.dsl.impl.aboutTheJob"
_LOGGED_OUT_MARKERS = ("/login", "/authwall", "/checkpoint", "/uas/")


class SessionExpiredError(RuntimeError):
    def __init__(self):
        super().__init__("Sessão do LinkedIn expirada. Deslogue e conecte novamente.")


def build_search_url(keywords: str, geo_id: str, range_hours: int, start: int = 0) -> str:
    params = {"keywords": keywords, "f_TPR": f"r{range_hours * 3600}", "sortBy": "DD"}
    if geo_id:
        params["geoId"] = geo_id
    if start:
        params["start"] = str(start)
    return f"{SEARCH_URL}?{urlencode(params)}"


class LinkedInClient:
    def __init__(self, ctx: BrowserContext, debug_dir: Path | None = None):
        self.ctx = ctx
        self.debug_dir = debug_dir
        self.page: Page = ctx.pages[0] if ctx.pages else ctx.new_page()

    def _goto(self, url: str) -> None:
        self.page.goto(url, wait_until="domcontentloaded")
        if any(marker in self.page.url for marker in _LOGGED_OUT_MARKERS):
            raise SessionExpiredError()

    def discover_preferences_search(self) -> tuple[str, str] | None:
        """(keywords, geoId) behind the 'Show all' link of the Jobs tab (built from career preferences)."""
        self._goto(f"{BASE}/jobs/")
        try:
            self.page.wait_for_selector('a[href*="/jobs/search"]', timeout=20_000)
        except PlaywrightTimeout:
            return None
        links: list[str] = self.page.evaluate(dom_scripts.EXTRACT_SEARCH_LINKS)
        preferred = [h for h in links if "PREFERENCES" in h] or links
        for href in preferred:
            if parsed := parsers.parse_search_link(href):
                return parsed
        return None

    def read_search_page(self, url: str) -> list[dict]:
        """Raw cards of one results page ([] when the page has no results)."""
        self._goto(url)
        try:
            self.page.wait_for_selector(dom_scripts.CARD_SELECTOR, timeout=20_000)
        except PlaywrightTimeout:
            return []
        self.page.wait_for_timeout(1_000)  # let the remaining cards hydrate
        return self.page.evaluate(dom_scripts.EXTRACT_CARDS)

    def fetch_job_page(self, job_id: str) -> dict:
        resp = self.ctx.request.get(f"{BASE}/jobs/view/{job_id}/", fail_on_status_code=False)
        if resp.status != 200:
            return {}
        return parsers.parse_job_page(resp.text())

    def fetch_about_html(self, job_id: str) -> str:
        csrf = next(
            (c["value"].strip('"') for c in self.ctx.cookies(BASE) if c["name"] == "JSESSIONID"), None
        )
        if not csrf:
            raise SessionExpiredError()
        body = {
            "componentId": _ABOUT_COMPONENT,
            "clientArguments": {
                "payload": {"jobId": job_id, "renderAsCard": True},
                "states": [],
                "requestMetadata": {"$type": "proto.sdui.common.RequestMetadata"},
                "screenId": "com.linkedin.sdui.flagshipnav.jobs.JobDetails",
                "knownTemplateIds": [],
            },
        }
        resp = self.ctx.request.post(
            f"{BASE}/flagship-web/rsc-action/actions/component?componentId={_ABOUT_COMPONENT}&sduiid={_ABOUT_COMPONENT}",
            data=json.dumps(body),
            headers={
                "content-type": "application/json",
                "csrf-token": csrf,
                "x-li-rsc-stream": "true",
                "referer": f"{BASE}/jobs/view/{job_id}/",
            },
            fail_on_status_code=False,
        )
        raw = resp.body()
        about = rsc_to_html(raw) if resp.status == 200 else ""
        if not about:
            self._keep_debug_dump(job_id, resp.status, raw)
        return about

    def _keep_debug_dump(self, job_id: str, status: int, raw: bytes) -> None:
        """Saves the raw About response that produced no text (.data/debug, never committed)."""
        target = self.debug_dir / f"about_{job_id}.txt" if self.debug_dir else None
        if target:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
        logger.warning(
            "Empty About for job %s (HTTP %s, %d bytes)%s", job_id, status, len(raw), f"; raw saved to {target}" if target else ""
        )
