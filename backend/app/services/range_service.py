"""Suggests a search window that covers the gap since the last run, in 12-hour steps."""

import math
from datetime import datetime

DEFAULT_RANGE_HOURS = 24
STEP_HOURS = 12


def suggest_range_hours(last_run_at: datetime | None, now: datetime, max_hours: int) -> int:
    if last_run_at is None:
        return DEFAULT_RANGE_HOURS
    elapsed_hours = (now - last_run_at).total_seconds() / 3600
    if elapsed_hours <= DEFAULT_RANGE_HOURS:
        return DEFAULT_RANGE_HOURS
    return min(math.ceil(elapsed_hours / STEP_HOURS) * STEP_HOURS, max_hours)
