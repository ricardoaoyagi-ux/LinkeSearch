"""Single-threaded owner of the persistent Chrome profile.

The profile directory can only be opened by one browser at a time, so every browser operation
runs on one dedicated worker thread (Playwright sync API). The context is kept open between
operations (fast on-demand job details) and closed after some idle time.
The LinkedIn session cookie never leaves this profile directory.
"""

import asyncio
import logging
import threading
import time
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from typing import TypeVar

from playwright.sync_api import BrowserContext, Playwright, sync_playwright
from playwright.sync_api import Error as PlaywrightError

from app.config import Settings

T = TypeVar("T")

logger = logging.getLogger("uvicorn.error")

IDLE_CLOSE_S = 10 * 60
# A Chrome that is still shutting down keeps the profile locked for a few seconds (exit code 21)
LAUNCH_ATTEMPTS = 3
LAUNCH_RETRY_DELAY_S = 3.0


class BrowserUnavailableError(RuntimeError):
    def __init__(self, cause: Exception):
        super().__init__(
            "Não foi possível abrir o Chrome em segundo plano (o perfil pode estar em uso). "
            "Tente novamente em alguns segundos."
        )
        self.__cause__ = cause

_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="browser")


class BrowserManager:
    """Must only be used from the browser thread (see run_in_browser_thread)."""

    def __init__(self):
        self._pw: Playwright | None = None
        self._ctx: BrowserContext | None = None
        self._headless: bool | None = None
        self._last_used = 0.0
        self._idle_timer: threading.Timer | None = None

    def context(self, settings: Settings, headless: bool) -> BrowserContext:
        if self._ctx is not None and self._headless != headless:
            self.close()
        if self._ctx is None:
            ctx = self._launch(settings, headless)
            ctx.on("close", lambda _: self._forget(ctx))
            self._ctx, self._headless = ctx, headless
        self._touch()
        return self._ctx

    def _launch(self, settings: Settings, headless: bool) -> BrowserContext:
        settings.profile_dir.mkdir(parents=True, exist_ok=True)
        if self._pw is None:
            self._pw = sync_playwright().start()
        for attempt in range(1, LAUNCH_ATTEMPTS + 1):
            try:
                return self._pw.chromium.launch_persistent_context(
                    str(settings.profile_dir),
                    channel=settings.browser_channel or None,
                    headless=headless,
                    viewport={"width": 1400, "height": 900},
                    locale="en-US",
                    args=["--disable-blink-features=AutomationControlled"],
                )
            except PlaywrightError as exc:
                logger.warning("Chrome launch failed (attempt %d/%d): %s", attempt, LAUNCH_ATTEMPTS, str(exc).splitlines()[0])
                if attempt == LAUNCH_ATTEMPTS:
                    raise BrowserUnavailableError(exc) from exc
                time.sleep(LAUNCH_RETRY_DELAY_S * attempt)
        raise AssertionError("unreachable")

    def _forget(self, ctx: BrowserContext) -> None:
        if self._ctx is ctx:  # close() clears the reference first, so this is an unexpected exit
            logger.warning("Background Chrome closed unexpectedly; it will be reopened on the next request")
            self._ctx, self._headless = None, None

    def _touch(self) -> None:
        self._last_used = time.monotonic()
        if self._idle_timer:
            self._idle_timer.cancel()
        self._idle_timer = threading.Timer(IDLE_CLOSE_S + 1, lambda: _executor.submit(self._close_if_idle))
        self._idle_timer.daemon = True
        self._idle_timer.start()

    def _close_if_idle(self) -> None:
        if time.monotonic() - self._last_used >= IDLE_CLOSE_S:
            self.close()

    def close(self) -> None:
        ctx, self._ctx, self._headless = self._ctx, None, None
        if ctx is not None:
            try:
                ctx.close()
            except Exception:
                pass  # already closed (e.g. the user closed the login window)


browser_manager = BrowserManager()


async def run_in_browser_thread(fn: Callable[..., T], *args) -> T:
    """Runs a blocking browser function on the dedicated thread without blocking the API."""
    return await asyncio.get_running_loop().run_in_executor(_executor, fn, *args)


def submit_to_browser_thread(fn: Callable[..., T], *args) -> Future:
    return _executor.submit(fn, *args)
