from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import browser_call, get_memory, repository_or_404
from app.config import get_settings
from app.models.job import Job
from app.services import job_detail_service
from app.services.memory_service import MemoryService
from app.tasks.task_manager import task_manager

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.get("/{week}", response_model=list[Job])
def list_jobs(week: str, include_ignored: bool = False, memory: MemoryService = Depends(get_memory)) -> list[Job]:
    """Jobs of a weekly file, most recently posted first. Ignored jobs are left out unless asked for."""
    return repository_or_404(memory, week).list_all(include_ignored=include_ignored)


@router.post("/{week}/{job_id}/detail", response_model=Job)
async def load_detail(week: str, job_id: str, memory: MemoryService = Depends(get_memory)) -> Job:
    """Fetches About + Apply link from LinkedIn the first time a job is opened, then serves it from memory."""
    repo = repository_or_404(memory, week)
    job = repo.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Vaga não encontrada")
    if job_detail_service.has_detail(job):
        return job
    if task_manager.running():
        raise HTTPException(status_code=409, detail="Aguarde a busca em andamento terminar")
    return await browser_call(job_detail_service.fetch_and_store, get_settings(), repo, job_id)


def _mark(memory: MemoryService, week: str, job_id: str, column: str) -> Job:
    repo = repository_or_404(memory, week)
    if not repo.set_timestamp(job_id, column, datetime.now().astimezone()):
        raise HTTPException(status_code=404, detail="Vaga não encontrada")
    return repo.get(job_id)


@router.post("/{week}/{job_id}/viewed", response_model=Job)
def mark_viewed(week: str, job_id: str, memory: MemoryService = Depends(get_memory)) -> Job:
    return _mark(memory, week, job_id, "local_viewed_at")


@router.post("/{week}/{job_id}/apply-click", response_model=Job)
def mark_apply_click(week: str, job_id: str, memory: MemoryService = Depends(get_memory)) -> Job:
    return _mark(memory, week, job_id, "apply_clicked_at")


def _unmark(memory: MemoryService, week: str, job_id: str, column: str) -> Job:
    repo = repository_or_404(memory, week)
    if not repo.clear_timestamp(job_id, column):
        raise HTTPException(status_code=404, detail="Vaga não encontrada")
    return repo.get(job_id)


@router.post("/{week}/{job_id}/ignore", response_model=Job)
def ignore_job(week: str, job_id: str, memory: MemoryService = Depends(get_memory)) -> Job:
    """Hides the job from the default listing (kept in the file)."""
    return _mark(memory, week, job_id, "ignored_at")


@router.delete("/{week}/{job_id}/ignore", response_model=Job)
def unignore_job(week: str, job_id: str, memory: MemoryService = Depends(get_memory)) -> Job:
    return _unmark(memory, week, job_id, "ignored_at")


@router.post("/{week}/{job_id}/save", response_model=Job)
def save_job(week: str, job_id: str, memory: MemoryService = Depends(get_memory)) -> Job:
    """Bookmarks the job in this system (independent of LinkedIn's own "Saved")."""
    return _mark(memory, week, job_id, "saved_at")


@router.delete("/{week}/{job_id}/save", response_model=Job)
def unsave_job(week: str, job_id: str, memory: MemoryService = Depends(get_memory)) -> Job:
    return _unmark(memory, week, job_id, "saved_at")
