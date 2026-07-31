"""Icon listing endpoints (``/api/icons``)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse

from app.rendering.icons import get_icon_renderer
from app.security import require_api_key

router = APIRouter(prefix="/api/icons", tags=["icons"], dependencies=[Depends(require_api_key)])


@router.get("", response_model=list[str])
def list_icons() -> list[str]:
    """List the icon names available for print jobs.

    Includes both Font Awesome icon names (e.g. ``fa-cart-shopping``) and
    custom SVG icons (e.g. ``svg-logo``). Used by the frontend to populate a
    searchable icon picker. Font Awesome names are empty if the Font Awesome
    assets are not configured (see ``backend/assets/fontawesome/README.md``).
    """

    return get_icon_renderer().available_icons()


@router.get("/{name}/svg")
def get_icon_svg(name: str) -> FileResponse:
    """Return the raw SVG file for a custom icon (e.g. ``svg-logo``).

    Used by the frontend icon picker to render a preview of custom icons,
    which (unlike Font Awesome icons) have no CSS glyph to display. 404 if
    ``name`` is not a known custom icon (see
    ``backend/assets/icons/README.md``).
    """

    path = get_icon_renderer().custom_icon_path(name)
    if path is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Icon nicht gefunden")

    return FileResponse(path, media_type="image/svg+xml")
