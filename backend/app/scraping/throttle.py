import random
import time

from app.config import Settings


def human_pause(settings: Settings) -> None:
    """Random pause between LinkedIn requests to keep the traffic low and irregular."""
    time.sleep(random.uniform(settings.min_delay_s, settings.max_delay_s))
