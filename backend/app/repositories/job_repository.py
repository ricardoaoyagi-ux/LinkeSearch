"""SQLite access for one weekly memory file. All SQL lives here."""

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from app.models.job import Job

_SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    job_id            TEXT PRIMARY KEY,
    title             TEXT NOT NULL,
    company           TEXT NOT NULL DEFAULT '',
    location          TEXT NOT NULL DEFAULT '',
    workplace_type    TEXT NOT NULL DEFAULT '',
    posted_at         TEXT,
    posted_label      TEXT NOT NULL DEFAULT '',
    job_url           TEXT NOT NULL DEFAULT '',
    li_viewed         INTEGER NOT NULL DEFAULT 0,
    li_applied        INTEGER NOT NULL DEFAULT 0,
    about_html        TEXT,
    apply_url         TEXT,
    is_easy_apply     INTEGER,
    found_at          TEXT NOT NULL,
    last_seen_at      TEXT NOT NULL,
    local_viewed_at   TEXT,
    apply_clicked_at  TEXT,
    ignored_at        TEXT,
    saved_at          TEXT
);
CREATE INDEX IF NOT EXISTS idx_jobs_posted_at ON jobs(posted_at DESC);
"""

_COLUMNS = (
    "job_id", "title", "company", "location", "workplace_type", "posted_at", "posted_label",
    "job_url", "li_viewed", "li_applied", "about_html", "apply_url", "is_easy_apply",
    "found_at", "last_seen_at", "local_viewed_at", "apply_clicked_at", "ignored_at", "saved_at",
)
_TIMESTAMP_COLUMNS = (
    "posted_at", "found_at", "last_seen_at", "local_viewed_at", "apply_clicked_at", "ignored_at", "saved_at",
)
_USER_MARK_COLUMNS = ("local_viewed_at", "apply_clicked_at", "ignored_at", "saved_at")
# Columns added after the first release, applied to older weekly files on open
_MIGRATIONS = {
    "ignored_at": "ALTER TABLE jobs ADD COLUMN ignored_at TEXT",
    "saved_at": "ALTER TABLE jobs ADD COLUMN saved_at TEXT",
}


def _dt(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


class JobRepository:
    def __init__(self, db_path: Path, week: str):
        self.db_path = db_path
        self.week = week

    def exists(self) -> bool:
        return self.db_path.exists()

    @contextmanager
    def _connect(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            conn.executescript(_SCHEMA)
            existing = {r["name"] for r in conn.execute("PRAGMA table_info(jobs)")}
            for column, ddl in _MIGRATIONS.items():
                if column not in existing:
                    conn.execute(ddl)
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _row_to_job(self, row: sqlite3.Row) -> Job:
        data = dict(row)
        data["li_viewed"] = bool(data["li_viewed"])
        data["li_applied"] = bool(data["li_applied"])
        if data["is_easy_apply"] is not None:
            data["is_easy_apply"] = bool(data["is_easy_apply"])
        return Job(week=self.week, **data)

    def get(self, job_id: str) -> Job | None:
        if not self.exists():
            return None
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
        return self._row_to_job(row) if row else None

    def list_all(self, include_ignored: bool = True) -> list[Job]:
        if not self.exists():
            return []
        where = "" if include_ignored else "WHERE ignored_at IS NULL"
        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT * FROM jobs {where} ORDER BY posted_at IS NULL, posted_at DESC, found_at DESC"
            ).fetchall()
        return [self._row_to_job(r) for r in rows]

    def ids(self) -> set[str]:
        if not self.exists():
            return set()
        with self._connect() as conn:
            return {r[0] for r in conn.execute("SELECT job_id FROM jobs")}

    def count(self) -> int:
        if not self.exists():
            return 0
        with self._connect() as conn:
            return conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]

    def save(self, job: Job) -> None:
        values = job.model_dump()
        for key in _TIMESTAMP_COLUMNS:
            values[key] = _dt(values[key])
        placeholders = ", ".join("?" for _ in _COLUMNS)
        with self._connect() as conn:
            conn.execute(
                f"INSERT OR REPLACE INTO jobs ({', '.join(_COLUMNS)}) VALUES ({placeholders})",
                [values[c] for c in _COLUMNS],
            )

    def set_timestamp(self, job_id: str, column: str, when: datetime) -> bool:
        """Sets a user mark once (the first timestamp is kept)."""
        if column not in _USER_MARK_COLUMNS:
            raise ValueError(column)
        if not self.exists():
            return False
        with self._connect() as conn:
            cur = conn.execute(
                f"UPDATE jobs SET {column} = COALESCE({column}, ?) WHERE job_id = ?", (_dt(when), job_id)
            )
            return cur.rowcount > 0

    def clear_timestamp(self, job_id: str, column: str) -> bool:
        if column not in _USER_MARK_COLUMNS:
            raise ValueError(column)
        if not self.exists():
            return False
        with self._connect() as conn:
            cur = conn.execute(f"UPDATE jobs SET {column} = NULL WHERE job_id = ?", (job_id,))
            return cur.rowcount > 0
