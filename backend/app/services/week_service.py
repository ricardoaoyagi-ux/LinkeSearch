"""Weekly memory files are keyed by the Sunday that starts the week (YYYYMMDD)."""

import re
from datetime import date, datetime, timedelta

WEEK_KEY_RE = re.compile(r"^\d{8}$")


def week_key(day: date) -> str:
    """Most recent Sunday (the day itself when it is a Sunday)."""
    sunday = day - timedelta(days=(day.weekday() + 1) % 7)
    return sunday.strftime("%Y%m%d")


def current_week_key() -> str:
    return week_key(datetime.now().date())


def previous_week_key(key: str) -> str:
    return (parse_week_key(key) - timedelta(days=7)).strftime("%Y%m%d")


def parse_week_key(key: str) -> date:
    if not is_valid_week_key(key):
        raise ValueError(f"Invalid week key: {key!r}")
    return datetime.strptime(key, "%Y%m%d").date()


def is_valid_week_key(key: str) -> bool:
    if not WEEK_KEY_RE.match(key):
        return False
    try:
        day = datetime.strptime(key, "%Y%m%d").date()
    except ValueError:
        return False
    return day.weekday() == 6


def week_label(key: str) -> str:
    return f"Semana de {parse_week_key(key).strftime('%d/%m/%Y')}"
