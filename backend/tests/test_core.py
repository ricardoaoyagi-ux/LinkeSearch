from datetime import date, datetime, timedelta, timezone

import pytest

from app.config import Settings
from app.models.job import ScrapedJob
from app.services import week_service
from app.services.memory_service import MemoryService
from app.services.range_service import suggest_range_hours
from app.services.sync_service import SyncService

NOW = datetime(2026, 10, 8, 9, 0, tzinfo=timezone.utc)


@pytest.mark.parametrize(
    "day,expected",
    [
        (date(2026, 10, 8), "20261004"),  # Thursday
        (date(2026, 10, 4), "20261004"),  # Sunday itself
        (date(2026, 10, 10), "20261004"),  # Saturday
        (date(2026, 10, 11), "20261011"),  # next Sunday
        (date(2026, 10, 5), "20261004"),  # Monday
    ],
)
def test_week_key(day, expected):
    assert week_service.week_key(day) == expected


def test_week_key_validation():
    assert week_service.is_valid_week_key("20261004")
    assert not week_service.is_valid_week_key("20261005")  # not a Sunday
    assert not week_service.is_valid_week_key("../../x")
    assert week_service.previous_week_key("20261004") == "20260927"


@pytest.mark.parametrize(
    "hours_ago,expected",
    [(None, 24), (2, 24), (24, 24), (26, 36), (36, 36), (40, 48), (10_000, 720)],
)
def test_suggest_range(hours_ago, expected):
    last = None if hours_ago is None else NOW - timedelta(hours=hours_ago)
    assert suggest_range_hours(last, NOW, 720) == expected


@pytest.fixture
def memory(tmp_path):
    return MemoryService(Settings(_env_file=None, data_dir=tmp_path))


def _job(job_id, **kw):
    return ScrapedJob(job_id=job_id, title=f"Job {job_id}", company="ACME", **kw)


def test_sync_new_and_dedupe(memory):
    sync = SyncService(memory, "20261004")
    r1 = sync.merge([_job("1", about_html="<p>a</p>"), _job("2")], NOW)
    assert (r1.new, r1.updated, r1.unchanged) == (2, 0, 0)

    later = NOW + timedelta(hours=3)
    r2 = sync.merge([_job("1"), _job("2")], later)
    assert (r2.new, r2.updated, r2.unchanged) == (0, 0, 2)
    job1 = memory.repository("20261004").get("1")
    assert job1.found_at == NOW  # unchanged status keeps original date
    assert job1.about_html == "<p>a</p>"  # detail not wiped
    assert job1.last_seen_at == later


def test_sync_status_change_updates_found_at(memory):
    sync = SyncService(memory, "20261004")
    sync.merge([_job("1")], NOW)
    later = NOW + timedelta(hours=1)
    r = sync.merge([_job("1", li_viewed=True)], later)
    assert r.updated == 1
    job = memory.repository("20261004").get("1")
    assert job.li_viewed and job.found_at == later


def test_sync_across_weeks_does_not_duplicate(memory):
    SyncService(memory, "20260927").merge([_job("old")], NOW - timedelta(days=4))
    r = SyncService(memory, "20261004").merge([_job("old", li_applied=True), _job("new")], NOW)
    assert (r.new, r.updated) == (1, 1)
    assert memory.repository("20261004").ids() == {"new"}
    assert memory.repository("20260927").get("old").li_applied


def test_list_and_delete_files(memory):
    assert memory.list_files() == []
    SyncService(memory, "20261004").merge([_job("1")], NOW)
    files = memory.list_files()
    assert [f.week for f in files] == ["20261004"] and files[0].job_count == 1
    assert memory.delete("20261004")
    assert memory.list_files() == []
    with pytest.raises(ValueError):
        memory.delete("../state")


def test_ignore_hides_job_and_survives_rescans(memory):
    sync = SyncService(memory, "20261004")
    sync.merge([_job("1"), _job("2")], NOW)
    repo = memory.repository("20261004")
    assert repo.get("1").ignored_at is None  # incoming jobs are never ignored
    assert repo.set_timestamp("1", "ignored_at", NOW)
    assert [j.job_id for j in repo.list_all(include_ignored=False)] == ["2"]
    assert {j.job_id for j in repo.list_all()} == {"1", "2"}  # not deleted

    # Re-scan with a LinkedIn status change: the user's ignore mark is kept
    sync.merge([_job("1", li_viewed=True), _job("3")], NOW + timedelta(hours=1))
    assert repo.get("1").ignored_at == NOW and repo.get("1").li_viewed
    assert repo.get("3").ignored_at is None

    assert repo.clear_timestamp("1", "ignored_at")
    assert len(repo.list_all(include_ignored=False)) == 3


def test_old_weekly_file_gets_ignored_column(memory, tmp_path):
    import sqlite3

    path = memory.repository("20261004").db_path
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute(
        "CREATE TABLE jobs (job_id TEXT PRIMARY KEY, title TEXT NOT NULL, company TEXT NOT NULL DEFAULT '',"
        " location TEXT NOT NULL DEFAULT '', workplace_type TEXT NOT NULL DEFAULT '', posted_at TEXT,"
        " posted_label TEXT NOT NULL DEFAULT '', job_url TEXT NOT NULL DEFAULT '', li_viewed INTEGER NOT NULL DEFAULT 0,"
        " li_applied INTEGER NOT NULL DEFAULT 0, about_html TEXT, apply_url TEXT, is_easy_apply INTEGER,"
        " found_at TEXT NOT NULL, last_seen_at TEXT NOT NULL, local_viewed_at TEXT, apply_clicked_at TEXT)"
    )
    conn.execute("INSERT INTO jobs (job_id, title, found_at, last_seen_at) VALUES ('9', 'Old', ?, ?)", (NOW.isoformat(),) * 2)
    conn.commit()
    conn.close()
    repo = memory.repository("20261004")
    assert repo.get("9").ignored_at is None and repo.get("9").saved_at is None
    assert repo.set_timestamp("9", "ignored_at", NOW)
    assert repo.set_timestamp("9", "saved_at", NOW)


def test_saved_mark_survives_rescans(memory):
    sync = SyncService(memory, "20261004")
    sync.merge([_job("1")], NOW)
    repo = memory.repository("20261004")
    assert repo.get("1").saved_at is None  # incoming jobs are never saved
    assert repo.set_timestamp("1", "saved_at", NOW)
    sync.merge([_job("1", li_applied=True)], NOW + timedelta(hours=2))
    assert repo.get("1").saved_at == NOW and repo.get("1").li_applied
    assert repo.clear_timestamp("1", "saved_at")
    assert repo.get("1").saved_at is None


def test_local_marks(memory):
    SyncService(memory, "20261004").merge([_job("1")], NOW)
    repo = memory.repository("20261004")
    assert repo.set_timestamp("1", "apply_clicked_at", NOW)
    assert repo.set_timestamp("1", "apply_clicked_at", NOW + timedelta(hours=1))
    assert repo.get("1").apply_clicked_at == NOW  # first click kept
    assert not repo.set_timestamp("missing", "local_viewed_at", NOW)
