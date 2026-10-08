from collections.abc import Callable
from typing import TypeVar

from fastapi import HTTPException
from playwright.sync_api import Error as PlaywrightError

from app.config import get_settings
from app.repositories.job_repository import JobRepository
from app.scraping.browser import BrowserUnavailableError, browser_manager, run_in_browser_thread
from app.services.memory_service import MemoryService

T = TypeVar("T")


def get_memory() -> MemoryService:
    return MemoryService(get_settings())


def repository_or_404(memory: MemoryService, week: str) -> JobRepository:
    try:
        repo = memory.repository(week)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not repo.exists():
        raise HTTPException(status_code=404, detail=f"Arquivo da semana {week} não existe")
    return repo


async def browser_call(fn: Callable[..., T], *args) -> T:
    """Runs a browser operation and turns browser failures into a readable 503.

    An HTTPException keeps the CORS headers, so the UI shows the real message instead of
    "backend indisponível". A broken Chrome is discarded so the next call starts a fresh one.
    """
    try:
        return await run_in_browser_thread(fn, *args)
    except BrowserUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except PlaywrightError as exc:
        await run_in_browser_thread(browser_manager.close)
        raise HTTPException(
            status_code=503, detail="O Chrome em segundo plano falhou. Tente abrir a vaga novamente."
        ) from exc
