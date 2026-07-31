"""Print template listing (``/api/templates``)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.schemas import TemplateInfo
from app.security import require_api_key
from app.templates.loader import get_template_registry

router = APIRouter(prefix="/api/templates", tags=["templates"], dependencies=[Depends(require_api_key)])


@router.get("", response_model=list[TemplateInfo])
def list_templates() -> list[TemplateInfo]:
    """List the configured print templates (key, display name, type, icon).

    Used by the frontend to populate the template selector when creating a
    new print job, without hardcoding the set of available templates.
    """

    configs = get_template_registry().list()
    return [TemplateInfo.from_config(config) for config in configs]
