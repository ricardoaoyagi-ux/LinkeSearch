"""Application settings. Override any value with an env var prefixed LINKESEARCH_ or a backend/.env file."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="LINKESEARCH_", env_file=".env", extra="ignore")

    data_dir: Path = PROJECT_ROOT / ".data"

    frontend_origin: str = "http://localhost:3000"

    # Scraping behaviour
    # "chrome" = installed Google Chrome with a separate profile; "" = Playwright's bundled Chromium
    browser_channel: str = "chrome"
    headless: bool = True
    max_pages: int = 40  # 25 jobs per page -> up to 1000 jobs per run
    min_delay_s: float = 1.5
    max_delay_s: float = 4.0
    max_range_hours: int = 24 * 30

    # Fallback search when the preferences "Show all" link cannot be found on /jobs/
    fallback_keywords: str = ""
    fallback_geo_id: str = ""

    @property
    def profile_dir(self) -> Path:
        return self.data_dir / "browser-profile"

    @property
    def memory_dir(self) -> Path:
        return self.data_dir / "memory"

    @property
    def state_file(self) -> Path:
        return self.data_dir / "state.json"


@lru_cache
def get_settings() -> Settings:
    return Settings()
