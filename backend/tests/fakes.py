"""Test doubles for the printer client and queue worker."""

from __future__ import annotations

from app.exceptions import PrinterOfflineError
from app.rendering.document import Document


class FakePrinterClient:
    """Stand-in for :class:`app.printing.client.PrinterClient`.

    Records every document it was asked to print. ``fail_times`` lets a test
    simulate the first N print attempts failing (e.g. printer offline)
    before subsequent attempts succeed.
    """

    def __init__(self, online: bool = True, fail_times: int = 0, error_cls: type[Exception] = PrinterOfflineError):
        self.online = online
        self.fail_times = fail_times
        self.error_cls = error_cls
        self.calls = 0
        self.documents: list[Document] = []

    def print_document(self, document: Document) -> None:
        self.calls += 1
        self.documents.append(document)
        if self.calls <= self.fail_times:
            raise self.error_cls(f"simulated failure #{self.calls}")

    def is_online(self) -> bool:
        return self.online


class StubWorker:
    """Stand-in for :class:`app.printing.worker.QueueWorker` used by the API tests.

    Avoids starting a real background thread so job-status assertions in API
    tests are not racy; queue-processing behaviour itself is covered by the
    worker tests, which exercise :class:`~app.printing.worker.QueueWorker`
    directly.
    """

    def __init__(self, *args, **kwargs):
        self.printer_client = FakePrinterClient()
        self._current_job_id: str | None = None

    @property
    def current_job_id(self) -> str | None:
        return self._current_job_id

    def recover_interrupted_jobs(self) -> None:
        pass

    def start(self) -> None:
        pass

    def stop(self, timeout: float = 10.0) -> None:
        pass
