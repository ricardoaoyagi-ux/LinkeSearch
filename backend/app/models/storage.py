from datetime import datetime

from pydantic import BaseModel


class MemoryFile(BaseModel):
    week: str
    label: str
    job_count: int
    size_bytes: int


class StorageStatus(BaseModel):
    files: list[MemoryFile]
    current_week: str
    last_run_at: datetime | None
    last_range_hours: int | None
    suggested_range_hours: int


class AppState(BaseModel):
    """Global state persisted in .data/state.json (independent of the weekly files)."""

    last_run_at: datetime | None = None
    last_range_hours: int | None = None
    search_keywords: str | None = None
    search_geo_id: str | None = None
