"""In-memory registry of background tasks (one scan at a time)."""

import threading
import uuid
from collections.abc import Callable
from datetime import datetime

from app.models.task import TaskState, TaskStatus
from app.scraping.browser import submit_to_browser_thread


class TaskCancelled(Exception):
    """Raised from the progress callback when the user cancels the task."""


class Progress:
    """Handed to the work function: reports progress and raises TaskCancelled when asked to stop."""

    def __init__(self, manager: "TaskManager", task_id: str):
        self._manager = manager
        self._task_id = task_id

    def __call__(self, **fields) -> None:
        if self._manager.is_cancel_requested(self._task_id):
            raise TaskCancelled()
        self._manager.update(self._task_id, **fields)


class TaskManager:
    def __init__(self):
        self._tasks: dict[str, TaskState] = {}
        self._cancel_requested: set[str] = set()
        self._lock = threading.Lock()

    def get(self, task_id: str) -> TaskState | None:
        with self._lock:
            task = self._tasks.get(task_id)
            return task.model_copy() if task else None

    def running(self) -> TaskState | None:
        with self._lock:
            return next((t.model_copy() for t in self._tasks.values() if t.status == TaskStatus.RUNNING), None)

    def clear(self) -> None:
        with self._lock:
            self._tasks = {k: v for k, v in self._tasks.items() if v.status == TaskStatus.RUNNING}

    def cancel(self, task_id: str) -> bool:
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None or task.status != TaskStatus.RUNNING:
                return False
            self._cancel_requested.add(task_id)
            return True

    def is_cancel_requested(self, task_id: str) -> bool:
        with self._lock:
            return task_id in self._cancel_requested

    def update(self, task_id: str, **fields) -> None:
        with self._lock:
            self._tasks[task_id] = self._tasks[task_id].model_copy(update=fields)

    def start(self, work: Callable[[Progress], dict], kind: str = "scan") -> TaskState:
        """`work` runs on the browser thread, receives a Progress callback and returns final fields."""
        task = TaskState(task_id=uuid.uuid4().hex, kind=kind, started_at=datetime.now().astimezone())
        with self._lock:
            self._tasks[task.task_id] = task

        def finish(status: TaskStatus, **fields):
            self.update(task.task_id, status=status, finished_at=datetime.now().astimezone(), **fields)
            with self._lock:
                self._cancel_requested.discard(task.task_id)

        def run():
            try:
                finish(TaskStatus.DONE, **work(Progress(self, task.task_id)))
            except TaskCancelled:
                current = self.get(task.task_id)
                finish(TaskStatus.CANCELLED, message=f"Busca cancelada — {current.jobs_found} vagas gravadas")
            except Exception as exc:  # surfaced to the UI
                finish(TaskStatus.ERROR, error=str(exc) or exc.__class__.__name__, message="Falha na busca")

        submit_to_browser_thread(run)
        return task


task_manager = TaskManager()
