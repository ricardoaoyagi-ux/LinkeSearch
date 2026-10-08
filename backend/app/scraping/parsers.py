"""Pure parsing of the raw data extracted from LinkedIn's jobs search UI (no browser here).

The page JS (see dom_scripts.py) returns plain dicts; these functions turn them into ScrapedJob.
"""

import html
import re
from datetime import datetime, timedelta
from urllib.parse import parse_qs, urlparse

from app.models.job import ScrapedJob

_RELATIVE_RE = re.compile(r"(\d+)\s+(minute|hour|day|week|month|year)s?\s+ago", re.I)
_UNIT_DELTA = {
    "minute": timedelta(minutes=1),
    "hour": timedelta(hours=1),
    "day": timedelta(days=1),
    "week": timedelta(weeks=1),
    "month": timedelta(days=30),
    "year": timedelta(days=365),
}
_WORKPLACE_RE = re.compile(r"\s*\((On-site|Hybrid|Remote)\)\s*$", re.I)
_VERIFIED_SUFFIX = " (Verified job)"
JOB_VIEW_URL = "https://www.linkedin.com/jobs/view/{job_id}/"


def parse_relative(text: str, now: datetime) -> datetime | None:
    """'Posted 26 minutes ago' / 'Reposted 1 hour ago' -> absolute datetime."""
    if not text:
        return None
    if re.search(r"\bjust now\b|\bmoments? ago\b", text, re.I):
        return now
    match = _RELATIVE_RE.search(text)
    if not match:
        return None
    amount, unit = int(match.group(1)), match.group(2).lower()
    return now - amount * _UNIT_DELTA[unit]


def relative_label(text: str) -> str:
    match = _RELATIVE_RE.search(text or "")
    if not match:
        return ""
    prefix = "Reposted " if re.search(r"\bReposted\b", text, re.I) else ""
    return prefix + match.group(0)


def _first_line(text: str) -> str:
    return (text or "").split("\n")[0].strip()


def parse_card(raw: dict, now: datetime) -> ScrapedJob:
    """raw = {id, ps: [paragraph texts], hidden_title} from a job card."""
    ps: list[str] = [p for p in raw.get("ps", []) if p and p != "·"]
    title = (raw.get("hidden_title") or "").strip() or _first_line(ps[0] if ps else "")
    title = title.removesuffix(_VERIFIED_SUFFIX).removeprefix("Selected, ").strip()

    company = _first_line(ps[1]) if len(ps) > 1 else ""
    location = _first_line(ps[2]) if len(ps) > 2 else ""
    workplace = ""
    if m := _WORKPLACE_RE.search(location):
        workplace = m.group(1)
        location = location[: m.start()].strip()

    footer = [_first_line(p) for p in ps[3:]]
    li_applied = "Applied" in footer
    li_viewed = li_applied or "Viewed" in footer
    posted_text = next((p for p in footer if _RELATIVE_RE.search(p)), "")

    return ScrapedJob(
        job_id=str(raw["id"]),
        title=title,
        company=company,
        location=location,
        workplace_type=workplace,
        posted_at=parse_relative(posted_text, now),
        posted_label=relative_label(posted_text),
        job_url=JOB_VIEW_URL.format(job_id=raw["id"]),
        li_viewed=li_viewed,
        li_applied=li_applied,
        is_easy_apply=True if "Easy Apply" in footer else None,
    )


def unwrap_safety_url(href: str | None) -> str | None:
    """LinkedIn wraps external links in /safety/go/?url=<real>; return the real http(s) URL."""
    if not href:
        return None
    parsed = urlparse(href)
    if parsed.netloc.endswith("linkedin.com") and parsed.path.startswith("/safety/go"):
        inner = parse_qs(parsed.query).get("url", [None])[0]
        href = inner
    if not href or urlparse(href).scheme not in ("http", "https"):
        return None
    return href


_APPLY_TAG_RE = re.compile(r'<a\b[^>]*aria-label="Apply on company website"[^>]*>', re.I)
_HREF_RE = re.compile(r'href="([^"]+)"')


def parse_job_page(page_html: str) -> dict:
    """Server-rendered /jobs/view/<id>/ page -> {apply_href, posted_text}.

    The external Apply link is rendered on the server; Easy Apply buttons are not (client-side only).
    """
    apply_href = None
    if tag := _APPLY_TAG_RE.search(page_html):
        if href := _HREF_RE.search(tag.group(0)):
            apply_href = html.unescape(href.group(1))
    posted = re.search(r"(?:Reposted |Posted )?\d+\s+(?:minute|hour|day|week|month|year)s?\s+ago", page_html)
    return {"apply_href": apply_href, "posted_text": posted.group(0) if posted else ""}


def apply_detail(job: ScrapedJob, raw: dict, now: datetime) -> ScrapedJob:
    """raw = {about_html, apply_href, posted_text} gathered for one job."""
    updates: dict = {}
    about = (raw.get("about_html") or "").strip()
    if about:
        updates["about_html"] = about
    external = unwrap_safety_url(raw.get("apply_href"))
    if external:
        updates["apply_url"] = external
        updates["is_easy_apply"] = False
    else:
        # No external link: Easy Apply (or apply on LinkedIn) -> open the job on LinkedIn
        updates["apply_url"] = job.job_url
        updates["is_easy_apply"] = True
    posted_text = raw.get("posted_text") or ""
    if job.posted_at is None and (posted := parse_relative(posted_text, now)):
        updates["posted_at"] = posted
        updates["posted_label"] = relative_label(posted_text)
    return job.model_copy(update=updates)


def parse_search_link(href: str) -> tuple[str, str] | None:
    """Extracts (keywords, geoId) from the preferences 'Show all' link of /jobs/."""
    query = parse_qs(urlparse(href).query)
    keywords = (query.get("keywords") or [""])[0].strip()
    if not keywords:
        return None
    return keywords, (query.get("geoId") or [""])[0].strip()
