"""Standard print object (preset) endpoints (``/api/presets``)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_session
from app.presets.builder import build_preset_payload
from app.presets.loader import get_preset_registry
from app.repositories.jobs import JobRepository
from app.rendering.builder import build_document
from app.schemas import PresetInfo, PrintJobCreate, PrintJobResponse
from app.security import require_api_key

router = APIRouter(prefix="/api/presets", tags=["presets"], dependencies=[Depends(require_api_key)])


@router.get("", response_model=list[PresetInfo])
def list_presets() -> list[PresetInfo]:
    """List the configured standard print objects (Standarddruckobjekte)."""

    configs = get_preset_registry().list()
    return [PresetInfo.from_config(config) for config in configs]


@router.post("/{key}/print", response_model=PrintJobResponse, status_code=status.HTTP_201_CREATED)
def print_preset(key: str, session: Session = Depends(get_session)) -> PrintJobResponse:
    """Resolve a preset to a print job and enqueue it.

    The preset's content script (if any) runs eagerly, and the resulting
    payload is validated the same way as ``POST /api/jobs`` so an unknown
    template or invalid content never reaches the queue.
    """

    preset = get_preset_registry().get(key)
    data = build_preset_payload(preset)
    data = PrintJobCreate.model_validate(data).model_dump()
    build_document(data)

    job = JobRepository(session).create(data)
    return PrintJobResponse.from_job(job)
