import io
import zipfile

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.api.deps import get_memory, repository_or_404
from app.config import get_settings
from app.models.task import TaskState
from app.services import triage_service
from app.services.memory_service import MemoryService
from app.tasks.task_manager import task_manager

router = APIRouter(prefix="/api/triage", tags=["triage"])

# ChatGPT result for a few hundred jobs is well under this
_MAX_IMPORT_CHARS = 5_000_000


class ImportRequest(BaseModel):
    text: str = Field(min_length=1, max_length=_MAX_IMPORT_CHARS)


def _manifest_files(week: str) -> list[str]:
    manifest = triage_service.read_manifest(get_settings(), week) or {}
    return manifest.get("files", [])


@router.get("/{week}")
def triage_status(week: str, memory: MemoryService = Depends(get_memory)) -> dict:
    """New jobs to triage, how many still need their About, time estimate and generated files."""
    return triage_service.status(get_settings(), repository_or_404(memory, week))


@router.post("/{week}/prepare", response_model=TaskState)
def prepare(week: str, memory: MemoryService = Depends(get_memory)) -> TaskState:
    repo = repository_or_404(memory, week)
    if running := task_manager.running():
        if running.kind == "triage":
            return running
        raise HTTPException(status_code=409, detail="Há uma busca de vagas em andamento. Aguarde terminar.")
    settings = get_settings()
    return task_manager.start(lambda progress: triage_service.prepare(settings, repo, progress), kind="triage")


@router.get("/{week}/files/{name}")
def download_file(week: str, name: str) -> FileResponse:
    # Only files listed in the week's manifest can be served (no path traversal)
    if name not in _manifest_files(week):
        raise HTTPException(status_code=404, detail="Arquivo de triagem não encontrado")
    path = triage_service.triage_folder(get_settings(), week) / name
    media_type = "application/json" if name.endswith(".json") else "text/markdown"
    return FileResponse(path, media_type=media_type, filename=name)


@router.get("/{week}/zip")
def download_zip(week: str) -> Response:
    files = _manifest_files(week)
    if not files:
        raise HTTPException(status_code=404, detail="Nenhum lote gerado para esta semana")
    folder = triage_service.triage_folder(get_settings(), week)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in files:
            archive.write(folder / name, arcname=name)
    filename = f"triagem_{week}.zip"
    return Response(
        buffer.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/import")
def import_results(req: ImportRequest) -> dict:
    """Stores the AI scores; jobs at or below the threshold are ignored (manual marks are never touched)."""
    if task_manager.running():
        raise HTTPException(status_code=409, detail="Há uma busca ou triagem em andamento. Aguarde terminar.")
    try:
        report = triage_service.import_results(get_settings(), req.text)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return report.as_dict()
