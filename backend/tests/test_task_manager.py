import threading
import time

from app.models.task import TaskStatus
from app.tasks.task_manager import TaskManager


def _wait_finished(manager: TaskManager, task_id: str, timeout: float = 5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        task = manager.get(task_id)
        if task.status != TaskStatus.RUNNING:
            return task
        time.sleep(0.02)
    raise AssertionError("task did not finish")


def test_task_done_with_progress():
    manager = TaskManager()

    def work(progress):
        progress(pages_read=1, jobs_found=25)
        return {"message": "ok", "new_jobs": 3}

    task = _wait_finished(manager, manager.start(work).task_id)
    assert task.status == TaskStatus.DONE
    assert (task.pages_read, task.jobs_found, task.new_jobs, task.message) == (1, 25, 3, "ok")


def test_task_cancel_keeps_progress():
    manager = TaskManager()
    started, release = threading.Event(), threading.Event()

    def work(progress):
        progress(jobs_found=10)
        started.set()
        release.wait(2)
        progress(jobs_found=20)  # raises TaskCancelled
        return {}

    task_id = manager.start(work).task_id
    started.wait(2)
    assert manager.running().task_id == task_id
    assert manager.cancel(task_id)
    release.set()
    task = _wait_finished(manager, task_id)
    assert task.status == TaskStatus.CANCELLED
    assert task.jobs_found == 10 and "10 vagas" in task.message
    assert manager.running() is None


def test_task_error():
    manager = TaskManager()

    def work(progress):
        raise RuntimeError("boom")

    task = _wait_finished(manager, manager.start(work).task_id)
    assert task.status == TaskStatus.ERROR and task.error == "boom"
