from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field

from app.config import get_settings
from app.models.task import TaskState
from app.services.scan_service import run_scan
from app.tasks.task_manager import task_manager

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


class ScanRequest(BaseModel):
    range_hours: int = Field(default=24, ge=1)


@router.post("/scan", response_model=TaskState)
def start_scan(req: ScanRequest) -> TaskState:
    if running := task_manager.running():
        return running
    settings = get_settings()
    hours = min(req.range_hours, settings.max_range_hours)
    return task_manager.start(lambda progress: run_scan(settings, hours, progress))


@router.get("/running", response_model=TaskState | None)
def get_running() -> TaskState | Response:
    """The scan in progress, if any (lets the UI resume its loading screen after a refresh)."""
    return task_manager.running() or Response(status_code=204)


@router.get("/{task_id}", response_model=TaskState)
def get_task(task_id: str) -> TaskState:
    task = task_manager.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")
    return task


@router.post("/{task_id}/cancel", response_model=TaskState)
def cancel_task(task_id: str) -> TaskState:
    if not task_manager.cancel(task_id):
        raise HTTPException(status_code=409, detail="Nenhuma busca em andamento com esse id")
    return task_manager.get(task_id)
