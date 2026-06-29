"""SQLAlchemy ORM models for the print job queue."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    """Current time in UTC, stored as a naive datetime (convention: all
    timestamps in the DB are UTC)."""

    return datetime.now(timezone.utc).replace(tzinfo=None)


class JobStatus(str, enum.Enum):
    QUEUED = "queued"
    PRINTING = "printing"
    FAILED = "failed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

    @classmethod
    def active_statuses(cls) -> tuple["JobStatus", ...]:
        """Statuses for which the queue worker may still attempt a print."""

        return (cls.QUEUED, cls.FAILED)

    @classmethod
    def terminal_statuses(cls) -> tuple["JobStatus", ...]:
        """Statuses that will never be picked up by the worker again."""

        return (cls.COMPLETED, cls.CANCELLED)


class Base(DeclarativeBase):
    pass


class PrintJob(Base):
    """A single print job.

    ``payload_json`` holds the job content (template, title, icon, markdown)
    as a JSON blob. It is deliberately the *only* place content is stored so
    that the privacy-driven scrub-on-success only has to clear one column.
    """

    __tablename__ = "print_jobs"

    id: Mapped[str] = mapped_column(
        String(32), primary_key=True, default=lambda: uuid.uuid4().hex
    )
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default=JobStatus.QUEUED.value, index=True
    )
    payload_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow, onupdate=utcnow
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Earliest time the worker should retry this job again (NULL = eligible
    # immediately, used for queued jobs and jobs due for retry now).
    next_retry_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, index=True
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<PrintJob id={self.id!r} status={self.status!r} retries={self.retry_count}>"


class AppSetting(Base):
    """A single web-configured override for a Settings field (``app/config.py``).

    Only fields listed in ``app.config.WEB_SETTINGS_FIELDS`` may have a row
    here, and only while not locked by an environment variable / ``.env``
    entry of the same name - see ``app.config.get_effective_settings()``.
    """

    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value_json: Mapped[str] = mapped_column(Text, nullable=False)
