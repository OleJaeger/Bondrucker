"""Printer endpoints (``/api/printer/…``)."""

from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.config import get_effective_settings
from app.database import get_session
from app.models import JobStatus
from app.repositories.jobs import JobRepository
from app.schemas import PrinterPowerResponse, PrinterStatusResponse
from app.security import require_api_key

router = APIRouter(prefix="/api/printer", tags=["printer"], dependencies=[Depends(require_api_key)])

_HA_TIMEOUT = 5.0


def _require_ha_config():
    settings = get_effective_settings()
    if not settings.homeassistant_url or not settings.homeassistant_token:
        raise HTTPException(
            status_code=503,
            detail="HOMEASSISTANT_URL und HOMEASSISTANT_TOKEN muessen konfiguriert sein.",
        )
    return settings


def _fetch_plug_state(settings) -> bool:
    url = f"{settings.homeassistant_url.rstrip('/')}/api/states/{settings.homeassistant_printer_plug}"
    try:
        resp = httpx.get(
            url,
            headers={"Authorization": f"Bearer {settings.homeassistant_token}"},
            timeout=_HA_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json().get("state") == "on"
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail=f"HomeAssistant nicht erreichbar: {exc}") from exc


@router.get("/status", response_model=PrinterStatusResponse)
def printer_status(request: Request, session: Session = Depends(get_session)) -> PrinterStatusResponse:
    """Report printer connectivity and the current queue state."""

    worker = request.app.state.queue_worker
    repo = JobRepository(session)
    queue_length = len(repo.list(JobStatus.QUEUED)) + len(repo.list(JobStatus.FAILED))

    return PrinterStatusResponse(
        online=worker.printer_client.is_online(),
        queue_length=queue_length,
        current_job=worker.current_job_id,
    )


@router.get("/power", response_model=PrinterPowerResponse)
def printer_power() -> PrinterPowerResponse:
    """Return the current power state of the printer plug (``switch.plug_016`` by default)."""
    settings = _require_ha_config()
    return PrinterPowerResponse(power=_fetch_plug_state(settings))


@router.post("/power/toggle", response_model=PrinterPowerResponse)
def printer_power_toggle() -> PrinterPowerResponse:
    """Toggle the printer plug via Home Assistant and return the new power state."""
    settings = _require_ha_config()
    url = f"{settings.homeassistant_url.rstrip('/')}/api/services/switch/toggle"
    try:
        resp = httpx.post(
            url,
            headers={"Authorization": f"Bearer {settings.homeassistant_token}"},
            json={"entity_id": settings.homeassistant_printer_plug},
            timeout=_HA_TIMEOUT,
        )
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail=f"HomeAssistant nicht erreichbar: {exc}") from exc

    return PrinterPowerResponse(power=_fetch_plug_state(settings))
