"""Network ESC/POS printer client (V330M, port 9100).

Wraps :class:`escpos.printer.Network`. Connectivity failures - including a
connection that drops mid-print - raise :class:`PrinterOfflineError` so the
queue worker retries the job; failures while encoding/sending ESC/POS
commands raise :class:`PrinterCommandError`.
"""

from __future__ import annotations

import socket

from escpos.exceptions import Error as EscposError
from escpos.printer import Network

from app.config import Settings
from app.exceptions import PrinterCommandError, PrinterOfflineError
from app.rendering.document import Document
from app.rendering.escpos_renderer import render_document

# Connection-level failures - the printer is unreachable or the connection
# was dropped while writing to it. Both are treated as "offline" (retryable).
_CONNECTION_ERRORS = (OSError, socket.timeout)

# escpos.printer.Network.open() wraps a failed connect() in DeviceNotFoundError
# (an EscposError, not an OSError) - also treated as "offline".
_CONNECT_ERRORS = (EscposError,) + _CONNECTION_ERRORS


class PrinterClient:
    """Sends rendered :class:`Document`\\ s to the configured network printer."""

    def __init__(self, settings: Settings):
        self._settings = settings

    def _connect(self) -> Network:
        printer = Network(
            host=self._settings.printer_host,
            port=self._settings.printer_port,
            timeout=self._settings.printer_timeout,
        )
        try:
            printer.open()
        except _CONNECT_ERRORS as exc:
            raise PrinterOfflineError(
                f"Drucker unter {self._settings.printer_host}:{self._settings.printer_port} "
                f"nicht erreichbar: {exc}"
            ) from exc
        return printer

    def print_document(self, document: Document) -> None:
        """Render and send ``document``, then close the connection.

        :raises PrinterOfflineError: the printer could not be reached, or the
            connection was lost while sending the job.
        :raises PrinterCommandError: the printer rejected an ESC/POS command
            (e.g. an oversized image).
        """

        printer = self._connect()
        try:
            render_document(printer, document, self._settings)
        except _CONNECTION_ERRORS as exc:
            raise PrinterOfflineError(f"Verbindung zum Drucker verloren: {exc}") from exc
        except EscposError as exc:
            raise PrinterCommandError(str(exc)) from exc
        finally:
            printer.close()

    def is_online(self) -> bool:
        """Best-effort connectivity check for ``GET /api/printer/status``."""

        try:
            printer = Network(
                host=self._settings.printer_host,
                port=self._settings.printer_port,
                timeout=min(self._settings.printer_timeout, 2.0),
            )
            printer.open()
        except Exception:
            return False

        printer.close()
        return True
