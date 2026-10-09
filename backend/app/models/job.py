from datetime import datetime

from pydantic import BaseModel


class ScrapedJob(BaseModel):
    """A job as read from LinkedIn (list card + optional detail)."""

    job_id: str
    title: str
    company: str = ""
    location: str = ""
    workplace_type: str = ""
    posted_at: datetime | None = None
    posted_label: str = ""
    job_url: str = ""
    li_viewed: bool = False
    li_applied: bool = False
    # Detail fields (filled only when the detail is fetched)
    about_html: str | None = None
    apply_url: str | None = None
    is_easy_apply: bool | None = None


class Job(ScrapedJob):
    """A job as stored in the weekly memory file."""

    week: str
    found_at: datetime
    last_seen_at: datetime
    local_viewed_at: datetime | None = None
    apply_clicked_at: datetime | None = None
    # Set only by the user; never filled from LinkedIn data and kept across scans
    ignored_at: datetime | None = None
    saved_at: datetime | None = None
    # Triage results imported from the AI (kept across scans)
    triage_score: int | None = None
    salary_min: int | None = None
    salary_ideal: int | None = None
    salary_max: int | None = None
    salary_currency: str | None = None
    triage_summary: str | None = None
    triaged_at: datetime | None = None
    triage_action: str | None = None  # "ignored" when the import (not the user) ignored the job
