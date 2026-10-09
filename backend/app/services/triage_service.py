"""Triagem: prepares job batches for an external AI (ChatGPT) and imports its fit scores back.

Flow: prepare() fetches the About of every *new* job (not saved, ignored, applied or triaged) at a
slow, LinkedIn-friendly pace and writes JSON batches + an instructions prompt to .data/triage/<week>/.
The user runs them through ChatGPT with their skills file and imports the resulting JSON with
import_results(): scores and salary expectations are stored, and jobs scoring at or below the
threshold are ignored — never touching jobs the user already marked by hand.
"""

import html
import json
import math
import random
import re
import time
import unicodedata
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

from app.config import Settings
from app.models.job import Job
from app.repositories.job_repository import JobRepository
from app.scraping.browser import browser_manager
from app.scraping.linkedin_client import LinkedInBlockedError, LinkedInClient, SessionExpiredError
from app.services import week_service
from app.services.memory_service import MemoryService

NL = chr(10)
DEFAULT_TEMPLATE = Path(__file__).resolve().parents[1] / "triage" / "prompt_template.md"
MANIFEST_NAME = "manifest.json"
TRIAGE_ACTION_IGNORED = "ignored"
# Average seconds one About request takes besides the pause (used only for the time estimate)
_REQUEST_SECONDS = 1.5

Progress = Callable[..., None]


# --- naming ----------------------------------------------------------------------------------
def batch_file_name(week: str, number: int) -> str:
    return f"triagem_{week}_lote_{number:02d}.json"


def prompt_file_name(week: str) -> str:
    return f"triagem_{week}_00_LEIA_PRIMEIRO_prompt.md"


def result_file_name(week: str) -> str:
    return f"resultado_triagem_{week}.json"


# --- blocked companies -----------------------------------------------------------------------
BLOCKED_SUMMARY = "Empresa bloqueada na triagem (lista de empresas a ignorar)."


def _normalize(text: str) -> str:
    """Lowercase without accents, so "Líder ACME" matches "lider acme"."""
    decomposed = unicodedata.normalize("NFD", text or "")
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch)).lower().strip()


def blocked_companies(settings: Settings) -> list[str]:
    return [name.strip() for name in settings.triage_blocked_companies.split(",") if name.strip()]


def is_blocked_company(settings: Settings, company: str) -> bool:
    normalized = _normalize(company)
    return any(_normalize(name) in normalized for name in blocked_companies(settings))


# --- selection & text ------------------------------------------------------------------------
def candidates(repo: JobRepository) -> list[Job]:
    """New jobs: no saved / ignored / apply mark and not triaged yet (most recent first)."""
    return [
        job
        for job in repo.list_all()
        if job.saved_at is None and job.ignored_at is None and job.apply_clicked_at is None and job.triaged_at is None
    ]


_BR_RE = re.compile(r"<br\s*/?>", re.I)
_LI_RE = re.compile(r"<li[^>]*>", re.I)
_BLOCK_END_RE = re.compile(r"</(p|div|li|ul|ol|h3|h4)>", re.I)
_TAG_RE = re.compile(r"<[^>]+>")
_EXTRA_BLANK_LINES_RE = re.compile(NL + "{3,}")


def html_to_text(markup: str | None) -> str:
    """Sanitized About HTML -> readable plain text for the AI (lists become "- item" lines)."""
    text = _BR_RE.sub(NL, markup or "")
    text = _LI_RE.sub("- ", text)
    text = _BLOCK_END_RE.sub(NL, text)
    text = html.unescape(_TAG_RE.sub("", text))
    text = NL.join(line.strip() for line in text.split(NL))
    return _EXTRA_BLANK_LINES_RE.sub(NL + NL, text).strip()


def job_entry(job: Job) -> dict:
    return {
        "job_id": job.job_id,
        "titulo": job.title,
        "empresa": job.company,
        "local": job.location,
        "modelo": job.workplace_type,
        "postada": job.posted_at.date().isoformat() if job.posted_at else "",
        "link": job.job_url,
        "about": html_to_text(job.about_html),
    }


def build_batches(jobs: list[Job], size: int, max_chars: int) -> list[list[dict]]:
    """Splits jobs into batches of at most `size` jobs and roughly `max_chars` characters."""
    batches: list[list[dict]] = []
    current: list[dict] = []
    chars = 0
    for job in jobs:
        entry = job_entry(job)
        entry_chars = len(json.dumps(entry, ensure_ascii=False))
        if current and (len(current) >= size or chars + entry_chars > max_chars):
            batches.append(current)
            current, chars = [], 0
        current.append(entry)
        chars += entry_chars
    if current:
        batches.append(current)
    return batches


# --- files -----------------------------------------------------------------------------------
def render_prompt(settings: Settings, week: str, total_batches: int, total_jobs: int) -> str:
    custom = settings.triage_dir / "prompt_template.md"
    template = (custom if custom.exists() else DEFAULT_TEMPLATE).read_text(encoding="utf-8")
    values = {
        "SEMANA_LEGIVEL": week_service.parse_week_key(week).strftime("%d/%m/%Y"),
        "TOTAL_LOTES": str(total_batches),
        "TOTAL_VAGAS": str(total_jobs),
        "PRIMEIRO_LOTE": batch_file_name(week, 1),
        "ULTIMO_LOTE": batch_file_name(week, total_batches),
        "ARQUIVO_RESULTADO": result_file_name(week),
        "LIMIAR": str(settings.triage_ignore_at_or_below),
        "EMPRESAS_BLOQUEADAS": ", ".join(blocked_companies(settings)) or "(nenhuma)",
    }
    for key, value in values.items():
        template = template.replace("{{" + key + "}}", value)
    return template


def batch_document(week: str, number: int, total_batches: int, total_jobs: int, jobs: list[dict]) -> dict:
    return {
        "lote": number,
        "total_lotes": total_batches,
        "total_vagas": total_jobs,
        "lembrete": (
            f"Lote {number} de {total_batches}. Avalie cada vaga contra o arquivo mestre e incremente "
            f"{result_file_name(week)} seguindo o formato_resposta. Copie o job_id exatamente como está. "
            "Pretensão SEMPRE em CLT mensal em BRL, mesmo que a vaga seja PJ. "
            "Uma entrada por vaga, sem texto dentro do JSON."
        ),
        "formato_resposta": [
            {
                "job_id": "texto copiado do lote",
                "aderencia": "inteiro de 0 a 100",
                "salario_min": "inteiro, mensal CLT",
                "salario_ideal": "inteiro, mensal CLT",
                "salario_max": "inteiro, mensal CLT",
                "moeda": "BRL",
                "resumo": "1 a 2 frases",
            }
        ],
        "vagas": jobs,
    }


def triage_folder(settings: Settings, week: str) -> Path:
    return settings.triage_dir / week


def read_manifest(settings: Settings, week: str) -> dict | None:
    try:
        return json.loads((triage_folder(settings, week) / MANIFEST_NAME).read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        return None


def write_batch_files(settings: Settings, week: str, batches: list[list[dict]], now: datetime) -> dict:
    """Replaces the week's triage files with the new batches, prompt and manifest."""
    folder = triage_folder(settings, week)
    folder.mkdir(parents=True, exist_ok=True)
    for old in folder.glob(f"triagem_{week}_*"):
        old.unlink()
    total_jobs = sum(len(b) for b in batches)
    files: list[str] = []
    manifest_batches: dict[str, list[str]] = {}
    if batches:
        prompt_name = prompt_file_name(week)
        (folder / prompt_name).write_text(render_prompt(settings, week, len(batches), total_jobs), encoding="utf-8")
        files.append(prompt_name)
        for number, jobs in enumerate(batches, start=1):
            name = batch_file_name(week, number)
            document = batch_document(week, number, len(batches), total_jobs, jobs)
            (folder / name).write_text(json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8")
            files.append(name)
            manifest_batches[str(number)] = [job["job_id"] for job in jobs]
    manifest = {
        "week": week,
        "generated_at": now.isoformat(),
        "total_vagas": total_jobs,
        "files": files,
        "batches": manifest_batches,
    }
    (folder / MANIFEST_NAME).write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


# --- pacing ----------------------------------------------------------------------------------
@dataclass
class Pacer:
    """Slow, irregular pauses between About requests; waits in 1 s steps so Cancel stays responsive."""

    settings: Settings
    sleep: Callable[[float], None] = time.sleep
    uniform: Callable[[float, float], float] = random.uniform

    def between_jobs(self, progress: Progress, message: str) -> None:
        self._wait(self.uniform(self.settings.triage_min_delay_s, self.settings.triage_max_delay_s), progress, message)

    def between_blocks(self, progress: Progress, message: str) -> None:
        seconds = self.uniform(self.settings.triage_batch_pause_min_s, self.settings.triage_batch_pause_max_s)
        self._wait(seconds, progress, message, show_countdown=True)

    def _wait(self, seconds: float, progress: Progress, message: str, show_countdown: bool = False) -> None:
        remaining = seconds
        while remaining > 0:
            text = f"{message} — retomando em {math.ceil(remaining)} s" if show_countdown else message
            progress(message=text)  # raises TaskCancelled when the user cancels
            step = min(1.0, remaining)
            self.sleep(step)
            remaining -= step


def estimate_minutes(settings: Settings, fetches: int) -> int:
    if fetches <= 0:
        return 0
    per_job = (settings.triage_min_delay_s + settings.triage_max_delay_s) / 2 + _REQUEST_SECONDS
    block_pause = (settings.triage_batch_pause_min_s + settings.triage_batch_pause_max_s) / 2
    pauses = (fetches - 1) // settings.triage_batch_size
    return math.ceil((fetches * per_job + pauses * block_pause) / 60)


# --- prepare ---------------------------------------------------------------------------------
def ignore_blocked_companies(settings: Settings, repo: JobRepository, now: datetime) -> int:
    """Blocked companies never reach the AI: ignored right away, with score 0 (no About fetched)."""
    count = 0
    for job in candidates(repo):
        if is_blocked_company(settings, job.company):
            repo.update_fields(
                job.job_id,
                triage_score=0,
                triage_summary=BLOCKED_SUMMARY,
                triaged_at=now,
                ignored_at=now,
                triage_action=TRIAGE_ACTION_IGNORED,
            )
            count += 1
    return count


def status(settings: Settings, repo: JobRepository) -> dict:
    new_jobs = candidates(repo)
    without_about = sum(1 for job in new_jobs if not job.about_html)
    fetch_now = min(without_about, settings.triage_max_per_run)
    manifest = read_manifest(settings, repo.week) or {}
    return {
        "week": repo.week,
        "candidates": len(new_jobs),
        "without_about": without_about,
        "fetch_now": fetch_now,
        "max_per_run": settings.triage_max_per_run,
        "estimated_minutes": estimate_minutes(settings, fetch_now),
        "threshold": settings.triage_ignore_at_or_below,
        "files": manifest.get("files", []),
        "batch_jobs": manifest.get("total_vagas", 0),
        "generated_at": manifest.get("generated_at"),
    }


def prepare(
    settings: Settings,
    repo: JobRepository,
    progress: Progress,
    client: LinkedInClient | None = None,
    pacer: Pacer | None = None,
) -> dict:
    pacer = pacer or Pacer(settings)
    week = repo.week
    blocked = ignore_blocked_companies(settings, repo, datetime.now().astimezone())
    pending = [job for job in candidates(repo) if not job.about_html]
    to_fetch = pending[: settings.triage_max_per_run]
    progress(week=week, message="Preparando triagem...", jobs_found=0, pages_read=0)

    stop_reason: str | None = None
    if to_fetch:
        client = client or LinkedInClient(
            browser_manager.context(settings, headless=settings.headless), settings.debug_dir
        )
        total = len(to_fetch)
        for index, job in enumerate(to_fetch):
            label = f"Buscando descrições {index + 1}/{total}"
            if index and index % settings.triage_batch_size == 0:
                pacer.between_blocks(progress, f"Pausa de segurança após {index} vagas")
            elif index:
                pacer.between_jobs(progress, label)
            try:
                about = client.fetch_about_html(job.job_id)
            except (LinkedInBlockedError, SessionExpiredError) as exc:
                stop_reason = str(exc)
                break
            if about:
                repo.update_fields(job.job_id, about_html=about)
            progress(message=label, jobs_found=index + 1)

    ready = [job for job in candidates(repo) if job.about_html]
    batches = build_batches(ready, settings.triage_batch_size, settings.triage_batch_max_chars)
    manifest = write_batch_files(settings, week, batches, datetime.now().astimezone())
    still_pending = len(candidates(repo)) - len(ready)

    if not batches:
        message = "Nenhuma vaga nova com descrição para triar."
    else:
        message = f"{len(ready)} vagas em {len(batches)} lotes prontos para o ChatGPT."
    if still_pending:
        message += f" {still_pending} vagas ainda sem descrição: rode 'Preparar triagem' de novo mais tarde."
    if blocked:
        message += f" {blocked} vagas de empresas bloqueadas foram ignoradas direto."
    if stop_reason:
        message = f"Parado por segurança: {stop_reason} {message}"
    return {"message": message, "jobs_found": manifest["total_vagas"], "pages_read": len(batches), "week": week}


# --- import ----------------------------------------------------------------------------------
@dataclass
class ImportReport:
    total_items: int = 0
    imported: int = 0
    ignored: int = 0
    blocked: int = 0
    kept: int = 0
    manual: int = 0
    not_found: list[str] = field(default_factory=list)
    duplicates: list[str] = field(default_factory=list)
    invalid: list[dict] = field(default_factory=list)
    missing: list[dict] = field(default_factory=list)
    threshold: int = 0

    def as_dict(self) -> dict:
        return asdict(self)


_FENCE_RE = re.compile(r"```(?:json)?", re.I)
_CENTS_RE = re.compile(r"[.,]\d{1,2}$")


def parse_result_text(text: str) -> list:
    """Extracts the result array from what ChatGPT returned (code fences and surrounding text tolerated)."""
    cleaned = _FENCE_RE.sub("", text or "").strip()
    candidates_text = [cleaned]
    start, end = cleaned.find("["), cleaned.rfind("]")
    if start != -1 and end > start:
        candidates_text.append(cleaned[start : end + 1])
    for chunk in candidates_text:
        try:
            data = json.loads(chunk)
        except ValueError:
            continue
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            lists = [value for value in data.values() if isinstance(value, list)]
            if lists:
                return lists[0]
    raise ValueError("Não encontrei um array JSON válido no conteúdo importado.")


def _score(value) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return round(value)
    if isinstance(value, str):
        try:
            return round(float(value.replace("%", "").replace(",", ".").strip()))
        except ValueError:
            return None
    return None


def _money(value) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return round(value)
    if isinstance(value, str):
        # Drop cents ("18.000,00", "18000.5"), then keep digits: "R$ 18.000" / "18,000" / "18000" -> 18000
        without_cents = _CENTS_RE.sub("", value.strip())
        digits = re.sub(r"[^0-9]", "", without_cents)
        return int(digits) if digits else None
    return None


def _short_text(value, limit: int) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text[:limit] or None


def _has_manual_mark(job: Job) -> bool:
    manually_ignored = job.ignored_at is not None and job.triage_action != TRIAGE_ACTION_IGNORED
    return job.saved_at is not None or job.apply_clicked_at is not None or manually_ignored


def import_results(settings: Settings, text: str, now: datetime | None = None) -> ImportReport:
    items = parse_result_text(text)
    now = now or datetime.now().astimezone()
    memory = MemoryService(settings)
    threshold = settings.triage_ignore_at_or_below
    report = ImportReport(total_items=len(items), threshold=threshold)

    # job_id -> weekly file that holds it (the import does not need to know the week)
    location: dict[str, JobRepository] = {}
    for week in memory.list_weeks():
        repo = memory.repository(week)
        for job_id in repo.ids():
            location.setdefault(job_id, repo)

    seen: set[str] = set()
    touched_weeks: set[str] = set()
    for position, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            report.invalid.append({"posicao": position, "motivo": "item não é um objeto JSON"})
            continue
        job_id = str(item.get("job_id") or "").strip()
        score = _score(item.get("aderencia"))
        if not job_id:
            report.invalid.append({"posicao": position, "motivo": "job_id ausente"})
            continue
        if score is None or not 0 <= score <= 100:
            report.invalid.append({"posicao": position, "job_id": job_id, "motivo": "aderencia inválida"})
            continue
        if job_id in seen:
            report.duplicates.append(job_id)
            continue
        seen.add(job_id)
        repo = location.get(job_id)
        job = repo.get(job_id) if repo else None
        if job is None:
            report.not_found.append(job_id)
            continue

        blocked = is_blocked_company(settings, job.company)
        if blocked:
            score = 0  # safety net: a blocked company is always ignored, whatever the AI said
            report.blocked += 1
        fields: dict = {
            "triage_score": score,
            "salary_min": _money(item.get("salario_min")),
            "salary_ideal": _money(item.get("salario_ideal")),
            "salary_max": _money(item.get("salario_max")),
            "salary_currency": _short_text(item.get("moeda"), 8),
            "triage_summary": BLOCKED_SUMMARY if blocked else _short_text(item.get("resumo"), 1000),
            "triaged_at": now,
        }
        if _has_manual_mark(job):
            report.manual += 1  # the user's decision always wins
        elif score <= threshold:
            fields["ignored_at"] = job.ignored_at or now
            fields["triage_action"] = TRIAGE_ACTION_IGNORED
            report.ignored += 1
        else:
            if job.triage_action == TRIAGE_ACTION_IGNORED:  # re-import raised the score: undo our ignore
                fields["ignored_at"] = None
                fields["triage_action"] = None
            report.kept += 1
        repo.update_fields(job_id, **fields)
        report.imported += 1
        touched_weeks.add(repo.week)

    report.missing = _missing_from_batches(settings, memory, touched_weeks)
    return report


def _missing_from_batches(settings: Settings, memory: MemoryService, weeks: set[str]) -> list[dict]:
    """Jobs sent in a batch that still have no score (so the user can ask the AI for just those)."""
    missing: list[dict] = []
    for week in sorted(weeks):
        manifest = read_manifest(settings, week)
        if not manifest:
            continue
        triaged = {job.job_id for job in memory.repository(week).list_all() if job.triaged_at is not None}
        for number, job_ids in manifest.get("batches", {}).items():
            absent = [job_id for job_id in job_ids if job_id not in triaged]
            if absent:
                missing.append({"semana": week, "lote": int(number), "job_ids": absent})
    return missing
