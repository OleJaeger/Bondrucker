"""Print preview endpoint (``/api/preview``)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response

from app.config import get_settings
from app.rendering.builder import build_document
from app.rendering.png_renderer import render_preview
from app.schemas import PrintJobCreate
from app.security import require_api_key

router = APIRouter(prefix="/api", tags=["preview"], dependencies=[Depends(require_api_key)])


@router.post(
    "/preview",
    responses={200: {"content": {"image/png": {}}}},
    response_class=Response,
)
def preview(payload: PrintJobCreate) -> Response:
    """Render a print job payload to a PNG preview without enqueueing it.

    Uses the same layout engine as the ESC/POS renderer, so the preview
    matches the printed receipt.
    """

    document = build_document(payload.model_dump())
    png_bytes = render_preview(document, get_settings())
    return Response(content=png_bytes, media_type="image/png")
