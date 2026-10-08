"""'Buscar NOVAS vagas': runs the preferences search for the last N hours and merges into this week's file.

Only the result pages are read here (fast). About/Apply are fetched on demand when the job is
opened (job_detail_service), except for jobs whose card hides the posting time ("Viewed",
"Promoted"...): for those the job page is fetched now so the list can be sorted by date.
Each page is saved as soon as it is read, so a cancelled scan keeps what it already found.
"""

from datetime import datetime, timedelta

from app.config import Settings
from app.models.job import ScrapedJob
from app.scraping import parsers
from app.scraping.browser import browser_manager
from app.scraping.linkedin_client import PAGE_SIZE, LinkedInClient, build_search_url
from app.scraping.throttle import human_pause
from app.services import week_service
from app.services.memory_service import MemoryService
from app.services.sync_service import SyncResult, SyncService
from app.tasks.task_manager import Progress

# LinkedIn rounds "posted X ago"; keep jobs slightly beyond the window
_RANGE_TOLERANCE = timedelta(hours=1)


class NoSearchConfiguredError(RuntimeError):
    def __init__(self):
        super().__init__(
            "Não encontrei a busca das suas preferências na aba Jobs. "
            "Defina LINKESEARCH_FALLBACK_KEYWORDS (e LINKESEARCH_FALLBACK_GEO_ID) em backend/.env."
        )


def _resolve_search(client: LinkedInClient, memory: MemoryService, settings: Settings) -> tuple[str, str]:
    state = memory.load_state()
    search = client.discover_preferences_search()
    if search is None and state.search_keywords:
        search = (state.search_keywords, state.search_geo_id or "")
    if search is None and settings.fallback_keywords:
        search = (settings.fallback_keywords, settings.fallback_geo_id)
    if search is None:
        raise NoSearchConfiguredError()
    state.search_keywords, state.search_geo_id = search
    memory.save_state(state)
    return search


def _fill_missing_date(client: LinkedInClient, job: ScrapedJob, settings: Settings) -> ScrapedJob:
    human_pause(settings)
    return parsers.apply_detail(job, client.fetch_job_page(job.job_id), datetime.now().astimezone())


def run_scan(settings: Settings, range_hours: int, progress: Progress) -> dict:
    memory = MemoryService(settings)
    week = week_service.current_week_key()
    sync = SyncService(memory, week)
    dated_ids = sync.known_ids_with_posted_at()
    started = datetime.now().astimezone()
    oldest_allowed = started - timedelta(hours=range_hours) - _RANGE_TOLERANCE
    progress(week=week, message="Abrindo o LinkedIn...")

    client = LinkedInClient(browser_manager.context(settings, headless=settings.headless))
    progress(message="Lendo as preferências da aba Jobs...")
    keywords, geo_id = _resolve_search(client, memory, settings)

    seen: set[str] = set()
    total = SyncResult()
    for page_index in range(settings.max_pages):
        progress(message=f"Lendo página {page_index + 1} de resultados...")
        raw_cards = client.read_search_page(build_search_url(keywords, geo_id, range_hours, start=page_index * PAGE_SIZE))
        fresh = [c for c in raw_cards if str(c["id"]) not in seen]
        if not fresh:
            break

        now = datetime.now().astimezone()
        page_jobs: list[ScrapedJob] = []
        for raw in fresh:
            job = parsers.parse_card(raw, now)
            seen.add(job.job_id)
            if job.posted_at is None and job.job_id not in dated_ids:
                progress(message=f"Página {page_index + 1}: buscando data de “{job.title[:50]}”")
                job = _fill_missing_date(client, job, settings)
            if job.posted_at is not None and job.posted_at < oldest_allowed:
                continue
            page_jobs.append(job)

        result = sync.merge(page_jobs, datetime.now().astimezone())
        total.new += result.new
        total.updated += result.updated
        progress(pages_read=page_index + 1, jobs_found=len(seen), new_jobs=total.new, updated_jobs=total.updated)
        if len(raw_cards) < PAGE_SIZE:
            break
        human_pause(settings)

    state = memory.load_state()
    state.last_run_at = started
    state.last_range_hours = range_hours
    memory.save_state(state)
    return {
        "message": f"{len(seen)} vagas lidas: {total.new} novas, {total.updated} com status atualizado",
        "jobs_found": len(seen),
        "new_jobs": total.new,
        "updated_jobs": total.updated,
    }
