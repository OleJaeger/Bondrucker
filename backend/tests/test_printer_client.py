"""``PrinterClient`` against real TCP sockets (no escpos hardware required)."""

from __future__ import annotations

import socket
import struct
import threading

import pytest

from app.exceptions import PrinterOfflineError
from app.printing.client import PrinterClient
from app.rendering.builder import build_document

PAYLOAD = {"template": "freitext", "title": "T", "markdown": "Hallo"}


class FakePrinterServer:
    """Minimal TCP server standing in for the V330M.

    By default it accepts connections and silently discards everything sent
    to it. With ``reset_on_accept=True`` it immediately tears down the
    connection with a TCP RST, simulating a printer that drops the
    connection mid-print.
    """

    def __init__(self, reset_on_accept: bool = False):
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._socket.bind(("127.0.0.1", 0))
        self._socket.listen(1)
        self._socket.settimeout(0.2)
        self.port: int = self._socket.getsockname()[1]

        self._reset_on_accept = reset_on_accept
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()

    def _serve(self) -> None:
        while not self._stop.is_set():
            try:
                conn, _ = self._socket.accept()
            except socket.timeout:
                continue

            if self._reset_on_accept:
                conn.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("ii", 1, 0))
                conn.close()
                continue

            conn.settimeout(0.2)
            with conn:
                while not self._stop.is_set():
                    try:
                        if not conn.recv(4096):
                            break
                    except socket.timeout:
                        continue

    def stop(self) -> None:
        self._stop.set()
        self._socket.close()
        self._thread.join(timeout=1)


@pytest.fixture
def fake_printer_server():
    server = FakePrinterServer()
    yield server
    server.stop()


def _client_for_port(settings_env, port: int) -> PrinterClient:
    settings = settings_env.model_copy(update={"printer_port": port, "printer_timeout": 1.0})
    return PrinterClient(settings)


def test_is_online_false_when_nothing_listening(settings_env):
    client = PrinterClient(settings_env)  # settings_env points at port 19999
    assert client.is_online() is False


def test_is_online_true_when_printer_reachable(settings_env, fake_printer_server):
    client = _client_for_port(settings_env, fake_printer_server.port)
    assert client.is_online() is True


def test_print_document_raises_printer_offline_error_when_unreachable(settings_env):
    client = PrinterClient(settings_env)
    document = build_document(PAYLOAD)

    with pytest.raises(PrinterOfflineError, match="nicht erreichbar"):
        client.print_document(document)


def test_print_document_succeeds_against_reachable_printer(settings_env, fake_printer_server):
    client = _client_for_port(settings_env, fake_printer_server.port)
    document = build_document(PAYLOAD)

    client.print_document(document)  # must not raise


def test_print_document_raises_printer_offline_error_when_connection_drops(settings_env):
    server = FakePrinterServer(reset_on_accept=True)
    try:
        client = _client_for_port(settings_env, server.port)
        document = build_document(PAYLOAD)

        with pytest.raises(PrinterOfflineError, match="Verbindung"):
            client.print_document(document)
    finally:
        server.stop()
