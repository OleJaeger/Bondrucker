"""``QueueWorker`` - job processing, retry/backoff and restart recovery."""

from __future__ import annotations

import time
from datetime import timedelta

import pytest

from app import database
from app.exceptions import PrinterOfflineError
from app.models import JobStatus, utcnow
from app.printing.worker import QueueWorker
from app.repositories.jobs import JobRepository
from tests.fakes import FakePrinterClient

PAYLOAD = {"template": "freitext", "title": "T", "icon": None, "markdown": "Hallo"}


@pytest.fixture(autouse=True)
def _init_db(settings_env):
    database.init_db()
    yield


def _create_job() -> str:
    with database.session_scope() as session:
        return JobRepository(session).create(PAYLOAD).id


def _get_job(job_id: str):
    with database.session_scope() as session:
        return JobRepository(session).get(job_id)


def test_process_next_returns_false_when_queue_empty(settings_env):
    worker = QueueWorker(settings=settings_env, printer_client=FakePrinterClient())
    assert worker._process_next() is False


def test_process_next_completes_job_and_scrubs_content(settings_env):
    job_id = _create_job()
    printer = FakePrinterClient(online=True)
    worker = QueueWorker(settings=settings_env, printer_client=printer)

    assert worker._process_next() is True

    job = _get_job(job_id)
    assert job.status == JobStatus.COMPLETED.value
    assert job.payload_json is None
    assert job.completed_at is not None
    assert printer.calls == 1


def test_process_next_marks_job_failed_with_backoff_and_keeps_payload(settings_env):
    job_id = _create_job()
    printer = FakePrinterClient(fail_times=1, error_cls=PrinterOfflineError)
    worker = QueueWorker(settings=settings_env, printer_client=printer)

    before = utcnow()
    assert worker._process_next() is True

    job = _get_job(job_id)
    assert job.status == JobStatus.FAILED.value
    assert job.retry_count == 1
    assert "simulated failure" in job.error_message
    assert job.payload_json is not None  # retained while non-terminal

    expected_delay = settings_env.retry_base_delay_seconds  # base * 2**0
    assert job.next_retry_at >= before + timedelta(seconds=expected_delay)


def test_current_job_id_set_while_printing(settings_env):
    job_id = _create_job()
    seen: dict[str, str | None] = {}

    class TrackingPrinter(FakePrinterClient):
        def print_document(self, document):
            seen["current"] = worker.current_job_id
            return super().print_document(document)

    worker = QueueWorker(settings=settings_env, printer_client=TrackingPrinter())
    worker._process_next()

    assert seen["current"] == job_id
    assert worker.current_job_id is None


def test_recover_interrupted_jobs_requeues_printing_job(settings_env):
    with database.session_scope() as session:
        repo = JobRepository(session)
        job = repo.create(PAYLOAD)
        repo.mark_printing(job)
        job_id = job.id

    worker = QueueWorker(settings=settings_env, printer_client=FakePrinterClient())
    worker.recover_interrupted_jobs()

    job = _get_job(job_id)
    assert job.status == JobStatus.FAILED.value
    assert job.next_retry_at <= utcnow()
    assert "Neustart" in job.error_message


def test_worker_thread_retries_then_succeeds(settings_env):
    job_id = _create_job()
    printer = FakePrinterClient(fail_times=2, error_cls=PrinterOfflineError)
    worker = QueueWorker(settings=settings_env, printer_client=printer)

    worker.start()
    try:
        deadline = time.monotonic() + 5
        job = _get_job(job_id)
        while time.monotonic() < deadline and job.status != JobStatus.COMPLETED.value:
            time.sleep(0.02)
            job = _get_job(job_id)
    finally:
        worker.stop()

    assert job.status == JobStatus.COMPLETED.value
    assert printer.calls == 3
    assert job.retry_count == 2
    assert job.payload_json is None


def test_worker_thread_processes_jobs_in_fifo_order(settings_env):
    first_id = _create_job()
    second_id = _create_job()

    printer = FakePrinterClient(online=True)
    worker = QueueWorker(settings=settings_env, printer_client=printer)

    worker.start()
    try:
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline and len(printer.documents) < 2:
            time.sleep(0.02)
    finally:
        worker.stop()

    assert _get_job(first_id).status == JobStatus.COMPLETED.value
    assert _get_job(second_id).status == JobStatus.COMPLETED.value
    assert printer.calls == 2
