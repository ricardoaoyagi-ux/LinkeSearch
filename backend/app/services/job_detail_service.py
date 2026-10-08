"""On-demand job detail (About + external Apply link), fetched when the job is opened in the UI.

Uses plain HTTP requests with the session cookies, so LinkedIn does not mark the job as "Viewed".
"""

from datetime import datetime

from app.config import Settings
from app.models.job import Job
from app.repositories.job_repository import JobRepository
from app.scraping import parsers
from app.scraping.browser import browser_manager
from app.scraping.linkedin_client import LinkedInClient

_DETAIL_FIELDS = ("about_html", "apply_url", "is_easy_apply", "posted_at", "posted_label")


def has_detail(job: Job) -> bool:
    return job.about_html is not None and job.apply_url is not None


def fetch_and_store(settings: Settings, repo: JobRepository, job_id: str) -> Job | None:
    job = repo.get(job_id)
    if job is None or has_detail(job):
        return job
    client = LinkedInClient(browser_manager.context(settings, headless=settings.headless))
    detail = client.fetch_job_page(job_id)
    detail["about_html"] = client.fetch_about_html(job_id)
    filled = parsers.apply_detail(job, detail, datetime.now().astimezone())
    fields = {f: getattr(filled, f) for f in _DETAIL_FIELDS}
    fields["about_html"] = fields["about_html"] or ""  # nothing came back: do not retry on every open
    # Re-read: local marks (viewed/apply) may have changed while LinkedIn was being queried
    current = repo.get(job_id) or job
    updated = current.model_copy(update=fields)
    repo.save(updated)
    return updated
