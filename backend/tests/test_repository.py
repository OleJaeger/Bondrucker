"""``JobRepository`` - queue ordering, state transitions and privacy scrubbing."""

from __future__ import annotations

from datetime import timedelta

import pytest

from app import database
from app.exceptions import InvalidJobStateError, JobNotFoundError
from app.models import JobStatus, utcnow
from app.repositories.jobs import JobRepository

PAYLOAD = {"template": "freitext", "title": "T", "icon": None, "markdown": "Hallo"}


@pytest.fixture
def repo(settings_env):
    database.init_db()
    with database.session_scope() as session:
        yield JobRepository(session)


def test_create_returns_queued_job_with_payload(repo):
    job = repo.create(PAYLOAD)
    assert job.status == JobStatus.QUEUED.value
    assert job.retry_count == 0
    assert job.payload_json is not None


def test_get_unknown_job_raises(repo):
    with pytest.raises(JobNotFoundError):
        repo.get("does-not-exist")


def test_list_orders_by_created_at_and_filters_by_status(repo):
    first = repo.create(PAYLOAD)
    second = repo.create(PAYLOAD)
    repo.mark_failed(second, "boom", utcnow())

    assert [job.id for job in repo.list()] == [first.id, second.id]
    assert [job.id for job in repo.list(JobStatus.QUEUED)] == [first.id]
    assert [job.id for job in repo.list(JobStatus.FAILED)] == [second.id]


def test_cancel_queued_job_retains_payload(repo):
    job = repo.create(PAYLOAD)
    cancelled = repo.cancel(job.id)
    assert cancelled.status == JobStatus.CANCELLED.value
    assert cancelled.payload_json is not None


def test_cancel_printing_job_raises(repo):
    job = repo.create(PAYLOAD)
    repo.mark_printing(job)
    with pytest.raises(InvalidJobStateError):
        repo.cancel(job.id)


def test_cancel_already_terminal_job_raises(repo):
    job = repo.create(PAYLOAD)
    repo.mark_completed(job)
    with pytest.raises(InvalidJobStateError):
        repo.cancel(job.id)


def test_fetch_next_runnable_returns_queued_jobs_in_fifo_order(repo):
    first = repo.create(PAYLOAD)
    repo.create(PAYLOAD)

    next_job = repo.fetch_next_runnable(utcnow())
    assert next_job.id == first.id


def test_fetch_next_runnable_ignores_failed_jobs_not_yet_due(repo):
    job = repo.create(PAYLOAD)
    repo.mark_failed(job, "boom", utcnow() + timedelta(hours=1))

    assert repo.fetch_next_runnable(utcnow()) is None


def test_fetch_next_runnable_includes_due_failed_jobs_in_creation_order(repo):
    failed = repo.create(PAYLOAD)
    repo.mark_failed(failed, "boom", utcnow() - timedelta(seconds=1))
    queued = repo.create(PAYLOAD)

    # The failed job was created first and is due -> it wins, even though the
    # newly queued job has no retry delay at all.
    next_job = repo.fetch_next_runnable(utcnow())
    assert next_job.id == failed.id

    repo.mark_printing(next_job)
    assert repo.fetch_next_runnable(utcnow()).id == queued.id


def test_mark_printing_clears_retry_timestamp(repo):
    job = repo.create(PAYLOAD)
    repo.mark_failed(job, "boom", utcnow() - timedelta(seconds=1))

    repo.mark_printing(job)
    assert job.status == JobStatus.PRINTING.value
    assert job.next_retry_at is None


def test_mark_completed_scrubs_content(repo):
    job = repo.create(PAYLOAD)
    repo.mark_failed(job, "boom", utcnow())

    repo.mark_completed(job)
    assert job.status == JobStatus.COMPLETED.value
    assert job.payload_json is None
    assert job.error_message is None
    assert job.next_retry_at is None
    assert job.completed_at is not None


def test_mark_failed_increments_retry_count_and_sets_message(repo):
    job = repo.create(PAYLOAD)
    retry_at = utcnow() + timedelta(seconds=5)

    repo.mark_failed(job, "Drucker nicht erreichbar", retry_at)
    assert job.status == JobStatus.FAILED.value
    assert job.retry_count == 1
    assert job.error_message == "Drucker nicht erreichbar"
    assert job.next_retry_at == retry_at

    repo.mark_failed(job, "Drucker nicht erreichbar", retry_at)
    assert job.retry_count == 2


def test_recover_interrupted_requeues_printing_jobs(repo):
    job = repo.create(PAYLOAD)
    repo.mark_printing(job)

    other = repo.create(PAYLOAD)

    recovered = repo.recover_interrupted()
    assert recovered == 1

    assert job.status == JobStatus.FAILED.value
    assert job.next_retry_at is not None
    assert job.next_retry_at <= utcnow()
    assert "Neustart" in job.error_message

    # Jobs that were never printing are left untouched.
    assert other.status == JobStatus.QUEUED.value


def test_recover_interrupted_returns_zero_when_nothing_to_recover(repo):
    repo.create(PAYLOAD)
    assert repo.recover_interrupted() == 0
