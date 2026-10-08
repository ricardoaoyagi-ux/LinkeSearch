"""Merges scraped jobs into the weekly memory without duplicates.

Rules:
- New job -> stored in the current week's file with found_at = now.
- Known job (current or previous week's file) -> stays in the file where it already lives;
  LinkedIn status is refreshed and found_at moves to now only when a status changed.
"""

from dataclasses import dataclass, field
from datetime import datetime

from app.models.job import Job, ScrapedJob
from app.repositories.job_repository import JobRepository
from app.services import week_service
from app.services.memory_service import MemoryService

_STATUS_FIELDS = ("li_viewed", "li_applied")
_DETAIL_FIELDS = ("about_html", "apply_url", "is_easy_apply")


@dataclass
class SyncResult:
    new: int = 0
    updated: int = 0
    unchanged: int = 0
    new_ids: list[str] = field(default_factory=list)


class SyncService:
    def __init__(self, memory: MemoryService, week: str):
        self.current = memory.repository(week)
        self.previous = memory.repository(week_service.previous_week_key(week))

    def _locate(self, job_id: str) -> tuple[JobRepository, Job] | None:
        for repo in (self.current, self.previous):
            existing = repo.get(job_id)
            if existing:
                return repo, existing
        return None

    def known_ids_with_posted_at(self) -> set[str]:
        """Ids whose posting date is already stored, so the scanner does not fetch it again."""
        return {
            job.job_id
            for repo in (self.current, self.previous)
            for job in repo.list_all()
            if job.posted_at is not None
        }

    def merge(self, scraped: list[ScrapedJob], now: datetime) -> SyncResult:
        result = SyncResult()
        for item in scraped:
            located = self._locate(item.job_id)
            if located is None:
                self.current.save(
                    Job(**item.model_dump(), week=self.current.week, found_at=now, last_seen_at=now)
                )
                result.new += 1
                result.new_ids.append(item.job_id)
                continue

            repo, existing = located
            status_changed = any(getattr(item, f) != getattr(existing, f) for f in _STATUS_FIELDS)
            updates = item.model_dump(exclude={*(_DETAIL_FIELDS)})
            # Never wipe stored detail with an empty scrape
            for f in _DETAIL_FIELDS:
                if getattr(item, f) is not None:
                    updates[f] = getattr(item, f)
            # posted_at from the first time is the most accurate (labels like "1 week ago" get coarser)
            if existing.posted_at is not None:
                updates["posted_at"] = existing.posted_at
            merged = existing.model_copy(update=updates)
            merged.last_seen_at = now
            if status_changed:
                merged.found_at = now
                result.updated += 1
            else:
                result.unchanged += 1
            repo.save(merged)
        return result
