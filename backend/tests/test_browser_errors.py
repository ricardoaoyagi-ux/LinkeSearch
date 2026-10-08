import asyncio

import pytest
from fastapi import HTTPException
from playwright.sync_api import Error as PlaywrightError

from app.api.deps import browser_call
from app.scraping.browser import BrowserUnavailableError


def _raise(exc):
    raise exc


@pytest.mark.parametrize(
    "exc",
    [BrowserUnavailableError(RuntimeError("exit code 21")), PlaywrightError("Target page, context or browser has been closed")],
)
def test_browser_failures_become_readable_503(exc):
    with pytest.raises(HTTPException) as info:
        asyncio.run(browser_call(_raise, exc))
    assert info.value.status_code == 503
    assert "Chrome" in info.value.detail


def test_browser_call_returns_result():
    assert asyncio.run(browser_call(lambda a, b: a + b, 2, 3)) == 5
