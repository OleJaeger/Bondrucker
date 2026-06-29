"""Data-access layer for print jobs.

All queue/privacy invariants (FIFO ordering across retries, scrubbing
content on success, recovering jobs interrupted by a restart) live here so
the API layer and the queue worker share a single implementation.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.exceptions import InvalidJobStateError, JobNotFoundError
from app.models import JobStatus, PrintJob, utcnow


class JobRepository:
    def __init__(self, session: Session):
        self._session = session

    # --- API-facing ----------------------------------------------------

    def create(self, payload: dict[str, Any]) -> PrintJob:
        job = PrintJob(payload_json=json.dumps(payload))
        self._session.add(job)
        self._session.commit()
        return job

    def get(self, job_id: str) -> PrintJob:
        job = self._session.get(PrintJob, job_id)
        if job is None:
            raise JobNotFoundError(job_id)
        return job

    def list(self, status: str | JobStatus | None = None) -> list[PrintJob]:
        stmt = select(PrintJob).order_by(PrintJob.created_at)
        if status is not None:
            stmt = stmt.where(PrintJob.status == status)
        return list(self._session.scalars(stmt))

    def cancel(self, job_id: str) -> PrintJob:
        job = self.get(job_id)
        if job.status not in JobStatus.active_statuses():
            raise InvalidJobStateError(
                f"Druckauftrag {job_id!r} kann im Status {job.status!r} nicht abgebrochen werden"
            )
        job.status = JobStatus.CANCELLED.value
        job.next_retry_at = None
        self._session.commit()
        return job

    # --- worker-facing ---------------------------------------------------

    def fetch_next_runnable(self, now: datetime) -> PrintJob | None:
        """Return the oldest job eligible for printing, or ``None``.

        Eligible jobs are freshly queued jobs, or failed jobs whose retry
        delay has elapsed - ordered by ``created_at`` so retries do not jump
        ahead of jobs that were queued later (true FIFO).
        """

        stmt = (
            select(PrintJob)
            .where(
                or_(
                    PrintJob.status == JobStatus.QUEUED.value,
                    and_(
                        PrintJob.status == JobStatus.FAILED.value,
                        PrintJob.next_retry_at.isnot(None),
                        PrintJob.next_retry_at <= now,
                    ),
                )
            )
            .order_by(PrintJob.created_at)
            .limit(1)
        )
        return self._session.scalars(stmt).first()

    def mark_printing(self, job: PrintJob) -> None:
        job.status = JobStatus.PRINTING.value
        job.next_retry_at = None
        self._session.commit()

    def mark_completed(self, job: PrintJob) -> None:
        """Mark ``job`` as completed and scrub its content (privacy)."""

        job.status = JobStatus.COMPLETED.value
        job.completed_at = utcnow()
        job.payload_json = None
        job.error_message = None
        job.next_retry_at = None
        self._session.commit()

    def mark_failed(self, job: PrintJob, error_message: str, next_retry_at: datetime) -> None:
        job.status = JobStatus.FAILED.value
        job.error_message = error_message
        job.retry_count += 1
        job.next_retry_at = next_retry_at
        self._session.commit()

    def recover_interrupted(self) -> int:
        """Requeue jobs left in ``printing`` state by an unclean shutdown.

        Returns the number of jobs recovered.
        """

        stmt = select(PrintJob).where(PrintJob.status == JobStatus.PRINTING.value)
        jobs = list(self._session.scalars(stmt))
        for job in jobs:
            job.status = JobStatus.FAILED.value
            job.error_message = "Druckvorgang durch Neustart des Dienstes unterbrochen - wird erneut versucht"
            job.next_retry_at = utcnow()

        if jobs:
            self._session.commit()
        return len(jobs)
