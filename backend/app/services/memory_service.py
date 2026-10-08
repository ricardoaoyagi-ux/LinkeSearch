"""Weekly memory files (.data/memory/vagas_YYYYMMDD.db) and the global state.json."""

import json
from datetime import datetime

from app.config import Settings
from app.models.storage import AppState, MemoryFile, StorageStatus
from app.repositories.job_repository import JobRepository
from app.services import range_service, week_service

FILE_PREFIX = "vagas_"


class MemoryService:
    def __init__(self, settings: Settings):
        self.settings = settings

    # --- weekly files -------------------------------------------------------
    def repository(self, week: str) -> JobRepository:
        if not week_service.is_valid_week_key(week):
            raise ValueError(f"Semana inválida: {week}")
        return JobRepository(self.settings.memory_dir / f"{FILE_PREFIX}{week}.db", week)

    def list_weeks(self) -> list[str]:
        if not self.settings.memory_dir.exists():
            return []
        weeks = []
        for path in self.settings.memory_dir.glob(f"{FILE_PREFIX}*.db"):
            key = path.stem.removeprefix(FILE_PREFIX)
            if week_service.is_valid_week_key(key):
                weeks.append(key)
        return sorted(weeks, reverse=True)

    def list_files(self) -> list[MemoryFile]:
        files = []
        for week in self.list_weeks():
            repo = self.repository(week)
            files.append(
                MemoryFile(
                    week=week,
                    label=week_service.week_label(week),
                    job_count=repo.count(),
                    size_bytes=repo.db_path.stat().st_size,
                )
            )
        return files

    def delete(self, week: str) -> bool:
        repo = self.repository(week)
        if not repo.exists():
            return False
        repo.db_path.unlink()
        return True

    # --- global state -------------------------------------------------------
    def load_state(self) -> AppState:
        try:
            return AppState.model_validate_json(self.settings.state_file.read_text(encoding="utf-8"))
        except (FileNotFoundError, ValueError):
            return AppState()

    def save_state(self, state: AppState) -> None:
        self.settings.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.settings.state_file.write_text(json.dumps(state.model_dump(mode="json"), indent=2), encoding="utf-8")

    def status(self) -> StorageStatus:
        state = self.load_state()
        return StorageStatus(
            files=self.list_files(),
            current_week=week_service.current_week_key(),
            last_run_at=state.last_run_at,
            last_range_hours=state.last_range_hours,
            suggested_range_hours=range_service.suggest_range_hours(
                state.last_run_at, datetime.now().astimezone(), self.settings.max_range_hours
            ),
        )
