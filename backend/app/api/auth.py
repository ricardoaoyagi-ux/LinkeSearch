from fastapi import APIRouter
from pydantic import BaseModel

from app.api.deps import browser_call
from app.config import get_settings
from app.scraping.browser import browser_manager, submit_to_browser_thread
from app.services import session_service
from app.tasks.task_manager import task_manager

router = APIRouter(prefix="/api/auth", tags=["auth"])


class AuthStatus(BaseModel):
    logged_in: bool


@router.get("/status", response_model=AuthStatus)
async def status() -> AuthStatus:
    if task_manager.running():
        # The profile is busy with a scan, which only runs with a valid session
        return AuthStatus(logged_in=True)
    return AuthStatus(logged_in=await browser_call(session_service.check_session, get_settings()))


@router.post("/login", response_model=AuthStatus)
async def login() -> AuthStatus:
    return AuthStatus(logged_in=await browser_call(session_service.interactive_login, get_settings()))


@router.post("/logout", response_model=AuthStatus)
async def logout() -> AuthStatus:
    """Leaves the app: clears in-memory caches and closes the background browser.

    The LinkedIn cookie stays in the profile, so the next login is a single click.
    """
    task_manager.clear()
    if not task_manager.running():
        submit_to_browser_thread(browser_manager.close)  # no need to wait for Chrome to exit
    return AuthStatus(logged_in=False)
