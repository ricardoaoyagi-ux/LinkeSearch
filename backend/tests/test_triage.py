import json
import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

from app.config import Settings
from app.models.job import ScrapedJob
from app.scraping.linkedin_client import LinkedInBlockedError
from app.services import triage_service as triage
from app.services.memory_service import MemoryService
from app.services.sync_service import SyncService
from app.tasks.task_manager import TaskCancelled

WEEK = "20261004"
PREV_WEEK = "20260927"
NOW = datetime(2026, 10, 9, 10, 0, tzinfo=timezone.utc)


@pytest.fixture
def settings(tmp_path):
    return Settings(_env_file=None, data_dir=tmp_path, triage_batch_size=2, triage_max_per_run=10)


@pytest.fixture
def memory(settings):
    return MemoryService(settings)


def seed(memory, week, *jobs: ScrapedJob):
    SyncService(memory, week).merge(list(jobs), NOW)
    return memory.repository(week)


def job(job_id, about=None, hours_ago=1):
    return ScrapedJob(
        job_id=job_id,
        title=f"Tech Lead {job_id}",
        company="ACME",
        posted_at=NOW - timedelta(hours=hours_ago),
        job_url=f"https://www.linkedin.com/jobs/view/{job_id}/",
        about_html=about,
    )


class FakeClient:
    def __init__(self, fail_on: str | None = None):
        self.calls: list[str] = []
        self.fail_on = fail_on

    def fetch_about_html(self, job_id: str) -> str:
        self.calls.append(job_id)
        if job_id == self.fail_on:
            raise LinkedInBlockedError(429)
        return f"<p>About {job_id}</p><ul><li>Java</li></ul>"


class FakeClock:
    def __init__(self):
        self.slept = 0.0

    def sleep(self, seconds: float) -> None:
        self.slept += seconds


def pacer(settings, clock):
    return triage.Pacer(settings, sleep=clock.sleep, uniform=lambda low, high: low)


def noop_progress(**_):
    pass


# --- selection ---------------------------------------------------------------------------------
def test_candidates_are_only_new_jobs(memory):
    repo = seed(memory, WEEK, job("1"), job("2"), job("3"), job("4"), job("5"))
    repo.set_timestamp("2", "saved_at", NOW)
    repo.set_timestamp("3", "ignored_at", NOW)
    repo.set_timestamp("4", "apply_clicked_at", NOW)
    repo.update_fields("5", triaged_at=NOW, triage_score=80)
    assert [j.job_id for j in triage.candidates(repo)] == ["1"]


def test_html_to_text():
    text = triage.html_to_text("<p>Sobre</p><ul><li>Java</li><li>AWS &amp; GCP</li></ul>Fim<br>linha")
    assert text.split(chr(10)) == ["Sobre", "- Java", "- AWS & GCP", "", "Fim", "linha"]


def test_batches_respect_size_and_characters(memory):
    repo = seed(memory, WEEK, *(job(str(i), about="<p>x</p>") for i in range(5)))
    jobs = repo.list_all()
    assert [len(b) for b in triage.build_batches(jobs, size=2, max_chars=100_000)] == [2, 2, 1]
    one_char_budget = triage.build_batches(jobs, size=25, max_chars=1)
    assert [len(b) for b in one_char_budget] == [1, 1, 1, 1, 1]  # never an empty batch


# --- prepare -----------------------------------------------------------------------------------
def test_prepare_fetches_missing_about_paced_and_writes_files(settings, memory):
    repo = seed(memory, WEEK, job("1"), job("2", about="<p>já tinha</p>"), job("3"), job("4"))
    client, clock = FakeClient(), FakeClock()

    result = triage.prepare(settings, repo, noop_progress, client=client, pacer=pacer(settings, clock))

    assert sorted(client.calls) == ["1", "3", "4"]  # job 2 already had its About
    # 3 fetches: one 4 s pause between jobs and one 60 s safety pause after the first block of 2
    assert clock.slept == pytest.approx(4 + 60)
    assert result["jobs_found"] == 4 and result["pages_read"] == 2

    folder = triage.triage_folder(settings, WEEK)
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["files"] == [
        "triagem_20261004_00_LEIA_PRIMEIRO_prompt.md",
        "triagem_20261004_lote_01.json",
        "triagem_20261004_lote_02.json",
    ]
    assert sum(len(ids) for ids in manifest["batches"].values()) == 4

    prompt = (folder / manifest["files"][0]).read_text(encoding="utf-8")
    assert "{{" not in prompt
    assert "2 arquivos de lote" in prompt and "4 vagas no total" in prompt
    assert "resultado_triagem_20261004.json" in prompt and "59 ou menos" in prompt

    batch = json.loads((folder / "triagem_20261004_lote_01.json").read_text(encoding="utf-8"))
    assert batch["lote"] == 1 and batch["total_lotes"] == 2 and batch["total_vagas"] == 4
    assert "<" not in batch["vagas"][0]["about"]  # plain text for the AI


def test_prepare_respects_max_per_run(settings, memory):
    settings = settings.model_copy(update={"triage_max_per_run": 2})
    repo = seed(memory, WEEK, job("1"), job("2"), job("3"))
    client = FakeClient()
    result = triage.prepare(settings, repo, noop_progress, client=client, pacer=pacer(settings, FakeClock()))
    assert len(client.calls) == 2
    assert "1 vagas ainda sem descrição" in result["message"]
    assert result["jobs_found"] == 2  # only jobs with About go to the batches


def test_prepare_stops_when_linkedin_blocks(settings, memory):
    repo = seed(memory, WEEK, job("1", hours_ago=1), job("2", hours_ago=2), job("3", hours_ago=3))
    client = FakeClient(fail_on="2")
    result = triage.prepare(settings, repo, noop_progress, client=client, pacer=pacer(settings, FakeClock()))
    assert client.calls == ["1", "2"]  # stopped right away, job 3 never requested
    assert result["message"].startswith("Parado por segurança")
    assert repo.get("1").about_html  # what was fetched is kept
    assert result["jobs_found"] == 1


def test_cancel_during_pause_stops_prepare(settings, memory):
    repo = seed(memory, WEEK, job("1"), job("2"))
    calls = {"n": 0}

    def progress(**_):
        calls["n"] += 1
        if calls["n"] > 3:
            raise TaskCancelled()

    with pytest.raises(TaskCancelled):
        triage.prepare(settings, repo, progress, client=FakeClient(), pacer=pacer(settings, FakeClock()))


def test_status_estimates_time(settings, memory):
    repo = seed(memory, WEEK, *(job(str(i)) for i in range(5)))
    info = triage.status(settings, repo)
    assert info["candidates"] == 5 and info["without_about"] == 5 and info["fetch_now"] == 5
    assert info["estimated_minutes"] >= 1 and info["files"] == []


# --- import ------------------------------------------------------------------------------------
def result_text(*items) -> str:
    return "Aqui está o arquivo:" + chr(10) + "```json" + chr(10) + json.dumps(list(items)) + chr(10) + "```"


def item(job_id, score, **extra):
    return {"job_id": job_id, "aderencia": score, "salario_min": 15000, "salario_ideal": 18000,
            "salario_max": 21000, "moeda": "BRL", "resumo": "ok", **extra}


def test_import_applies_threshold_and_stores_salary(settings, memory):
    repo = seed(memory, WEEK, job("low"), job("edge"), job("ok"))
    report = triage.import_results(settings, result_text(item("low", 30), item("edge", 59), item("ok", 60)), NOW)

    assert (report.imported, report.ignored, report.kept, report.manual) == (3, 2, 1, 0)
    assert repo.get("low").ignored_at == NOW and repo.get("low").triage_action == "ignored"
    assert repo.get("edge").ignored_at is not None  # 59 is ignored
    ok = repo.get("ok")
    assert ok.ignored_at is None and ok.saved_at is None  # above the threshold: nothing is marked
    assert (ok.triage_score, ok.salary_min, ok.salary_ideal, ok.salary_max) == (60, 15000, 18000, 21000)
    assert ok.salary_currency == "BRL" and ok.triage_summary == "ok" and ok.triaged_at == NOW


def test_import_never_overrides_manual_marks(settings, memory):
    repo = seed(memory, WEEK, job("saved"), job("applied"), job("ignored"))
    repo.set_timestamp("saved", "saved_at", NOW)
    repo.set_timestamp("applied", "apply_clicked_at", NOW)
    repo.set_timestamp("ignored", "ignored_at", NOW)
    report = triage.import_results(settings, result_text(item("saved", 10), item("applied", 10), item("ignored", 95)), NOW)

    assert report.manual == 3 and report.ignored == 0
    assert repo.get("saved").saved_at == NOW and repo.get("saved").ignored_at is None
    assert repo.get("applied").ignored_at is None
    assert repo.get("ignored").ignored_at == NOW and repo.get("ignored").triage_action is None
    assert repo.get("saved").triage_score == 10  # the score is stored anyway


def test_import_finds_jobs_in_any_week_and_reports_problems(settings, memory):
    seed(memory, PREV_WEEK, job("old"))
    seed(memory, WEEK, job("new"))
    text = json.dumps({"resultado": [item("old", 80), item("new", 70), item("new", 75), item("ghost", 80),
                                     {"job_id": "x", "aderencia": "muito"}, "lixo"]})
    report = triage.import_results(settings, text, NOW)

    assert report.imported == 2 and report.total_items == 6
    assert report.duplicates == ["new"] and report.not_found == ["ghost"]
    assert [i["motivo"] for i in report.invalid] == ["aderencia inválida", "item não é um objeto JSON"]
    assert memory.repository(PREV_WEEK).get("old").triage_score == 80


def test_reimport_updates_and_can_undo_our_ignore(settings, memory):
    repo = seed(memory, WEEK, job("1"))
    triage.import_results(settings, result_text(item("1", 40)), NOW)
    assert repo.get("1").ignored_at is not None
    later = NOW + timedelta(hours=1)
    triage.import_results(settings, result_text(item("1", "85%", salario_min="R$ 20.000,00")), later)
    again = repo.get("1")
    assert again.ignored_at is None and again.triage_action is None
    assert again.triage_score == 85 and again.salary_min == 20000 and again.triaged_at == later


def test_import_reports_jobs_missing_from_batches(settings, memory):
    repo = seed(memory, WEEK, job("1"), job("2"), job("3"))
    triage.prepare(settings, repo, noop_progress, client=FakeClient(), pacer=pacer(settings, FakeClock()))
    report = triage.import_results(settings, result_text(item("1", 80)), NOW)
    absent = {jid for entry in report.missing for jid in entry["job_ids"]}
    assert absent == {"2", "3"} and all(entry["semana"] == WEEK for entry in report.missing)


def test_import_rejects_text_without_json(settings):
    with pytest.raises(ValueError):
        triage.import_results(settings, "não consegui gerar o arquivo")


# --- persistence -------------------------------------------------------------------------------
def test_new_scan_keeps_triage_fields(settings, memory):
    repo = seed(memory, WEEK, job("1"))
    triage.import_results(settings, result_text(item("1", 90)), NOW)
    SyncService(memory, WEEK).merge([job("1")], NOW + timedelta(hours=5))
    kept = repo.get("1")
    assert kept.triage_score == 90 and kept.salary_ideal == 18000 and kept.triaged_at == NOW


def test_old_weekly_file_gets_triage_columns(memory):
    path = memory.repository(WEEK).db_path
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute(
        "CREATE TABLE jobs (job_id TEXT PRIMARY KEY, title TEXT NOT NULL, company TEXT NOT NULL DEFAULT '',"
        " location TEXT NOT NULL DEFAULT '', workplace_type TEXT NOT NULL DEFAULT '', posted_at TEXT,"
        " posted_label TEXT NOT NULL DEFAULT '', job_url TEXT NOT NULL DEFAULT '', li_viewed INTEGER NOT NULL DEFAULT 0,"
        " li_applied INTEGER NOT NULL DEFAULT 0, about_html TEXT, apply_url TEXT, is_easy_apply INTEGER,"
        " found_at TEXT NOT NULL, last_seen_at TEXT NOT NULL, local_viewed_at TEXT, apply_clicked_at TEXT,"
        " ignored_at TEXT, saved_at TEXT)"
    )
    conn.execute("INSERT INTO jobs (job_id, title, found_at, last_seen_at) VALUES ('9', 'Old', ?, ?)", (NOW.isoformat(),) * 2)
    conn.commit()
    conn.close()
    repo = memory.repository(WEEK)
    assert repo.get("9").triage_score is None
    assert repo.update_fields("9", triage_score=70, triaged_at=NOW)
    assert repo.get("9").triage_score == 70


# --- blocked companies -------------------------------------------------------------------------
def company_job(job_id, company, about="<p>x</p>"):
    return ScrapedJob(job_id=job_id, title="Tech Lead", company=company, posted_at=NOW, about_html=about)


def test_blocked_company_is_ignored_on_prepare_without_fetch_or_batch(settings, memory):
    settings = settings.model_copy(update={"triage_blocked_companies": "Zeta, Acme Corp"})
    repo = seed(memory, WEEK, company_job("1", "Zeta Technologies", about=None), company_job("2", "zeta"),
                company_job("3", "Other"), company_job("4", "Other", about=None))
    client = FakeClient()
    result = triage.prepare(settings, repo, noop_progress, client=client, pacer=pacer(settings, FakeClock()))

    assert client.calls == ["4"]  # no About fetched for the blocked company
    for job_id in ("1", "2"):
        blocked = repo.get(job_id)
        assert blocked.ignored_at is not None and blocked.triage_action == "ignored" and blocked.triage_score == 0
    assert result["jobs_found"] == 2  # only jobs 3 and 4 go to the AI
    assert "2 vagas de empresas bloqueadas" in result["message"]
    prompt = (triage.triage_folder(settings, WEEK) / triage.prompt_file_name(WEEK)).read_text(encoding="utf-8")
    assert "Zeta, Acme Corp" in prompt and "SEMPRE em regime CLT" in prompt


def test_import_forces_zero_for_blocked_company_but_respects_manual_save(settings, memory):
    settings = settings.model_copy(update={"triage_blocked_companies": "Zeta"})
    repo = seed(memory, WEEK, company_job("1", "Zeta"), company_job("2", "Zeta"))
    repo.set_timestamp("2", "saved_at", NOW)
    report = triage.import_results(settings, result_text(item("1", 95), item("2", 95)), NOW)

    assert report.blocked == 2
    assert repo.get("1").triage_score == 0 and repo.get("1").ignored_at is not None
    assert repo.get("2").saved_at == NOW and repo.get("2").ignored_at is None  # your decision wins


def test_prompt_without_blocked_companies(settings, memory):
    repo = seed(memory, WEEK, company_job("1", "Other"))
    triage.prepare(settings, repo, noop_progress, client=FakeClient(), pacer=pacer(settings, FakeClock()))
    prompt = (triage.triage_folder(settings, WEEK) / triage.prompt_file_name(WEEK)).read_text(encoding="utf-8")
    assert "(nenhuma)" in prompt
