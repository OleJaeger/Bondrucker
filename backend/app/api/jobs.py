"""Print job endpoints (``/api/jobs``)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_session
from app.models import JobStatus
from app.repositories.jobs import JobRepository
from app.rendering.builder import build_document
from app.schemas import PrintJobCreate, PrintJobResponse
from app.security import require_api_key

router = APIRouter(prefix="/api/jobs", tags=["jobs"], dependencies=[Depends(require_api_key)])


@router.post("", response_model=PrintJobResponse, status_code=status.HTTP_201_CREATED)
def create_job(payload: PrintJobCreate, session: Session = Depends(get_session)) -> PrintJobResponse:
    """Validate and enqueue a new print job.

    The template and markdown are validated eagerly so the client gets an
    immediate ``400`` for an unknown template or unparsable markdown,
    instead of the job silently failing in the queue.
    """

    data = payload.model_dump()
    build_document(data)

    job = JobRepository(session).create(data)
    return PrintJobResponse.from_job(job)


@router.get("", response_model=list[PrintJobResponse])
def list_jobs(
    status_filter: JobStatus | None = Query(default=None, alias="status"),
    session: Session = Depends(get_session),
) -> list[PrintJobResponse]:
    jobs = JobRepository(session).list(status_filter)
    return [PrintJobResponse.from_job(job) for job in jobs]


@router.get("/{job_id}", response_model=PrintJobResponse)
def get_job(job_id: str, session: Session = Depends(get_session)) -> PrintJobResponse:
    job = JobRepository(session).get(job_id)
    return PrintJobResponse.from_job(job)


@router.delete("/{job_id}", response_model=PrintJobResponse)
def cancel_job(job_id: str, session: Session = Depends(get_session)) -> PrintJobResponse:
    """Cancel a queued or failed job.

    Jobs that are already printing, completed or cancelled cannot be
    cancelled and result in ``409 Conflict``.
    """

    job = JobRepository(session).cancel(job_id)
    return PrintJobResponse.from_job(job)
