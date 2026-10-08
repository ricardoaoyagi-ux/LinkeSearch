from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class TaskStatus(str, Enum):
    RUNNING = "running"
    DONE = "done"
    CANCELLED = "cancelled"
    ERROR = "error"


class TaskState(BaseModel):
    task_id: str
    status: TaskStatus = TaskStatus.RUNNING
    message: str = "Iniciando..."
    pages_read: int = 0
    jobs_found: int = 0
    new_jobs: int = 0
    updated_jobs: int = 0
    week: str | None = None
    error: str | None = None
    started_at: datetime
    finished_at: datetime | None = None
