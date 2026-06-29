"""Background worker thread that processes the persistent print queue.

The worker runs in its own thread with its own database session(s), picking
the oldest runnable job (FIFO across retries), rendering it and handing it to
the :class:`~app.printing.client.PrinterClient`. On success the job's content
is scrubbed (privacy); on failure it is requeued with an exponential backoff
delay and retried indefinitely.
"""

from __future__ import annotations

import json
import logging
import threading
from datetime import timedelta

from app.config import Settings, get_settings
from app.database import session_scope
from app.models import utcnow
from app.printing.client import PrinterClient
from app.repositories.jobs import JobRepository
from app.rendering.builder import build_document

logger = logging.getLogger(__name__)


class QueueWorker:
    """Polls the database for runnable jobs and prints them one at a time."""

    def __init__(self, settings: Settings | None = None, printer_client: PrinterClient | None = None):
        self.settings = settings or get_settings()
        self.printer_client = printer_client or PrinterClient(self.settings)

        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._current_job_id: str | None = None

    @property
    def current_job_id(self) -> str | None:
        with self._lock:
            return self._current_job_id

    def recover_interrupted_jobs(self) -> None:
        """Requeue jobs left in ``printing`` state by an unclean shutdown.

        Must be called once at startup, before :meth:`start`.
        """

        with session_scope() as session:
            recovered = JobRepository(session).recover_interrupted()
        if recovered:
            logger.warning("Recovered %d job(s) interrupted by a restart", recovered)

    def start(self) -> None:
        if self._thread is not None:
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, name="queue-worker", daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 10.0) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=timeout)
            self._thread = None

    # --- worker loop -----------------------------------------------------

    def _run(self) -> None:
        while not self._stop_event.is_set():
            processed = self._process_next()
            if not processed:
                self._stop_event.wait(self.settings.queue_poll_interval_seconds)

    def _process_next(self) -> bool:
        """Pick up and print one job, if any is runnable.

        Returns ``True`` if a job was processed (so the caller should poll
        again immediately), ``False`` if the queue is currently empty.
        """

        with session_scope() as session:
            repo = JobRepository(session)
            job = repo.fetch_next_runnable(utcnow())
            if job is None:
                return False
            repo.mark_printing(job)
            job_id = job.id
            payload_json = job.payload_json
            retry_count = job.retry_count

        with self._lock:
            self._current_job_id = job_id

        try:
            self._print_job(job_id, payload_json, retry_count)
        finally:
            with self._lock:
                self._current_job_id = None

        return True

    def _print_job(self, job_id: str, payload_json: str | None, retry_count: int) -> None:
        try:
            payload = json.loads(payload_json) if payload_json else {}
            document = build_document(payload)
            self.printer_client.print_document(document)
        except Exception as exc:
            message = str(exc) or exc.__class__.__name__
            logger.warning("Job %s failed (attempt %d): %s", job_id, retry_count + 1, message)
            self._mark_failed(job_id, retry_count, message)
            return

        self._mark_completed(job_id)
        logger.info("Job %s printed successfully", job_id)

    def _mark_completed(self, job_id: str) -> None:
        with session_scope() as session:
            repo = JobRepository(session)
            repo.mark_completed(repo.get(job_id))

    def _mark_failed(self, job_id: str, retry_count: int, message: str) -> None:
        delay = min(
            self.settings.retry_base_delay_seconds * (2**retry_count),
            self.settings.retry_max_delay_seconds,
        )
        next_retry_at = utcnow() + timedelta(seconds=delay)

        with session_scope() as session:
            repo = JobRepository(session)
            repo.mark_failed(repo.get(job_id), message, next_retry_at)
