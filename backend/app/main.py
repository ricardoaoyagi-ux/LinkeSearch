"""FastAPI entry point. Run with: python -m app (binds to 127.0.0.1 only)."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, jobs, storage, tasks
from app.config import get_settings
from app.scraping.browser import browser_manager, run_in_browser_thread


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    await run_in_browser_thread(browser_manager.close)


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="LinkeSearch", version="1.0.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_origin],
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["Content-Type"],
    )
    for module in (auth, storage, jobs, tasks):
        app.include_router(module.router)
    return app


app = create_app()
