from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_memory, repository_or_404
from app.models.storage import StorageStatus
from app.services.memory_service import MemoryService
from app.tasks.task_manager import task_manager

router = APIRouter(prefix="/api/storage", tags=["storage"])


@router.get("", response_model=StorageStatus)
def storage_status(memory: MemoryService = Depends(get_memory)) -> StorageStatus:
    return memory.status()


@router.delete("/files/{week}", response_model=StorageStatus)
def delete_file(week: str, memory: MemoryService = Depends(get_memory)) -> StorageStatus:
    if task_manager.running():
        raise HTTPException(status_code=409, detail="Há uma busca em andamento")
    repository_or_404(memory, week)
    memory.delete(week)
    return memory.status()
