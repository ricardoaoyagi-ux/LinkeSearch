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
