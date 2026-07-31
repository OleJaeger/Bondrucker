#!/usr/bin/env python3
"""Client (Bibliothek + CLI) fuer die Bondrucker REST-API.

Siehe ``docs/openapi.yaml`` fuer die vollstaendige API-Spezifikation.

Konfiguration von Basis-URL und API-Key (in dieser Reihenfolge):

1. Explizite Parameter (``BondruckerClient(base_url=..., api_key=...)``)
   bzw. die CLI-Optionen ``--url`` / ``--api-key``.
2. Umgebungsvariablen ``BONDRUCKER_API_URL`` / ``BONDRUCKER_API_KEY``.
3. ``.env`` im Projekt-Wurzelverzeichnis (ein Verzeichnis ueber ``scripts/``):
   ``BONDRUCKER_API_URL`` bzw. ``BONDRUCKER_API_KEY``, fuer den API-Key
   alternativ das dort bereits vorhandene ``API_KEY`` (derselbe Wert, den
   der Server von Clients im Header ``X-API-Key`` erwartet).
4. Default fuer die Basis-URL: ``https://backend-bondrucker.bondrucker-app.de``. Fuer den API-Key
   gibt es keinen Default - er muss ueber eine der obigen Quellen gesetzt
   werden (ausser fuer ``GET /health``, das keine Authentifizierung
   benoetigt).

Bibliotheks-Beispiel
---------------------
    from bondrucker_api import BondruckerClient

    client = BondruckerClient()
    print(client.list_templates())
    job = client.create_job(
        template="todo",
        title="Einkaufsliste",
        icon="fa-cart-shopping",
        markdown="- [ ] Milch\\n- [x] Brot",
    )
    print(job["id"], job["status"])

CLI-Beispiele
-------------
    python bondrucker_api.py health
    python bondrucker_api.py templates
    python bondrucker_api.py icons
    python bondrucker_api.py printer-status
    python bondrucker_api.py printer-power
    python bondrucker_api.py printer-toggle
    python bondrucker_api.py presets list
    python bondrucker_api.py presets print wlan-qrcode
    python bondrucker_api.py jobs list --status queued
    python bondrucker_api.py jobs get <job_id>
    python bondrucker_api.py jobs create --template todo --title Einkaufsliste \\
        --markdown "- [ ] Milch\\n- [x] Brot" --icon fa-cart-shopping
    python bondrucker_api.py jobs cancel <job_id>
    python bondrucker_api.py preview --template freitext --markdown "# Test" -o preview.png
"""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import sys
from pathlib import Path
from typing import Any

import requests

__all__ = [
    "BondruckerApiError",
    "BondruckerClient",
    "DEFAULT_BASE_URL",
    "encode_image_file",
]

DEFAULT_BASE_URL = "https://backend-bondrucker.bondrucker-app.de"

JOB_STATUSES = ("queued", "printing", "failed", "completed", "cancelled")


def _load_dotenv(path: Path) -> dict[str, str]:
    """Read simple ``KEY=VALUE`` lines from a ``.env`` file.

    Lines that are empty, start with ``#`` or contain no ``=`` are ignored.
    Surrounding single or double quotes around the value are stripped.
    """
    values: dict[str, str] = {}
    if not path.is_file():
        return values

    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        values[key] = value

    return values


def _resolve_config(base_url: str | None, api_key: str | None) -> tuple[str, str | None]:
    env_file = _load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

    if base_url is None:
        base_url = os.environ.get("BONDRUCKER_API_URL") or env_file.get("BONDRUCKER_API_URL") or DEFAULT_BASE_URL

    if api_key is None:
        api_key = (
            os.environ.get("BONDRUCKER_API_KEY")
            or env_file.get("BONDRUCKER_API_KEY")
            or env_file.get("API_KEY")
        )

    return base_url.rstrip("/"), api_key


class BondruckerApiError(RuntimeError):
    """Raised for failed HTTP requests against the Bondrucker API.

    ``status_code`` is ``0`` for connection-level errors (no response
    received at all), otherwise the HTTP status code returned by the server.
    """

    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail if status_code == 0 else f"HTTP {status_code}: {detail}")
        self.status_code = status_code
        self.detail = detail


def _extract_error_detail(response: requests.Response) -> str:
    try:
        data = response.json()
    except ValueError:
        return response.text or response.reason or f"HTTP {response.status_code}"

    detail = data.get("detail") if isinstance(data, dict) else None
    if isinstance(detail, str):
        return detail
    if detail is not None:
        return json.dumps(detail, ensure_ascii=False)
    return json.dumps(data, ensure_ascii=False)


def encode_image_file(path: str | Path) -> str:
    """Read an image file and return a base64 ``data:`` URL for ``image_base64``.

    The MIME type is guessed from the file extension (falls back to
    ``application/octet-stream``). The result respects the API's
    ``image_base64`` size limit of 7,000,000 characters (~5 MB binary).
    """
    file_path = Path(path)
    data = file_path.read_bytes()
    mime_type, _ = mimetypes.guess_type(file_path.name)
    mime_type = mime_type or "application/octet-stream"
    encoded = base64.b64encode(data).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def _build_job_payload(
    template: str,
    *,
    title: str = "",
    icon: str | None = None,
    markdown: str = "",
    print_timestamp: bool = True,
    image_base64: str | None = None,
    qr_code: str | None = None,
) -> dict[str, Any]:
    if image_base64 is not None and qr_code is not None:
        raise ValueError("image_base64 und qr_code sind exklusiv - nur eines von beiden angeben.")

    payload: dict[str, Any] = {"template": template, "print_timestamp": print_timestamp}
    if title:
        payload["title"] = title
    if icon is not None:
        payload["icon"] = icon
    if markdown:
        payload["markdown"] = markdown
    if image_base64 is not None:
        payload["image_base64"] = image_base64
    if qr_code is not None:
        payload["qr_code"] = qr_code
    return payload


class BondruckerClient:
    """Thin wrapper around the Bondrucker REST API (``docs/openapi.yaml``)."""

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.base_url, self.api_key = _resolve_config(base_url, api_key)
        self.timeout = timeout
        self._session = requests.Session()

    def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        auth: bool = True,
        expect_json: bool = True,
    ) -> Any:
        headers = {}
        if auth:
            if not self.api_key:
                raise BondruckerApiError(
                    0,
                    "Kein API-Key konfiguriert. Setze BONDRUCKER_API_KEY oder API_KEY "
                    "(z.B. in der .env im Projekt-Wurzelverzeichnis) oder uebergib "
                    "--api-key / api_key=...",
                )
            headers["X-API-Key"] = self.api_key

        try:
            response = self._session.request(
                method,
                f"{self.base_url}{path}",
                json=json_body,
                params=params,
                headers=headers,
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise BondruckerApiError(0, str(exc)) from exc

        if not response.ok:
            raise BondruckerApiError(response.status_code, _extract_error_detail(response))

        if not expect_json:
            return response.content
        if not response.content:
            return None
        return response.json()

    # --- health ---------------------------------------------------------

    def health(self) -> dict[str, Any]:
        """``GET /health`` - liveness check, ohne API-Key."""
        return self._request("GET", "/health", auth=False)

    # --- templates / icons -----------------------------------------------

    def list_templates(self) -> list[dict[str, Any]]:
        """``GET /api/templates`` - konfigurierte Druckvorlagen."""
        return self._request("GET", "/api/templates")

    def list_icons(self) -> list[str]:
        """``GET /api/icons`` - verfuegbare Font-Awesome-Icon-Namen."""
        return self._request("GET", "/api/icons")

    # --- presets (Standarddruckobjekte) ------------------------------------

    def list_presets(self) -> list[dict[str, Any]]:
        """``GET /api/presets`` - konfigurierte Standarddruckobjekte."""
        return self._request("GET", "/api/presets")

    def print_preset(self, key: str) -> dict[str, Any]:
        """``POST /api/presets/{key}/print`` - Standarddruckobjekt drucken und einreihen."""
        return self._request("POST", f"/api/presets/{key}/print")

    # --- printer ----------------------------------------------------------

    def printer_status(self) -> dict[str, Any]:
        """``GET /api/printer/status`` - Konnektivitaet und Warteschlangenstatus."""
        return self._request("GET", "/api/printer/status")

    def printer_power(self) -> dict[str, Any]:
        """``GET /api/printer/power`` - Aktuellen Steckdosen-Zustand abrufen."""
        return self._request("GET", "/api/printer/power")

    def toggle_printer_power(self) -> dict[str, Any]:
        """``POST /api/printer/power/toggle`` - Steckdose umschalten, neuen Zustand zurueckgeben."""
        return self._request("POST", "/api/printer/power/toggle")

    # --- jobs ---------------------------------------------------------------

    def list_jobs(self, status: str | None = None) -> list[dict[str, Any]]:
        """``GET /api/jobs`` - Druckauftraege auflisten, optional nach Status gefiltert."""
        params = {"status": status} if status else None
        return self._request("GET", "/api/jobs", params=params)

    def get_job(self, job_id: str) -> dict[str, Any]:
        """``GET /api/jobs/{job_id}`` - einzelnen Druckauftrag abrufen."""
        return self._request("GET", f"/api/jobs/{job_id}")

    def create_job(
        self,
        template: str,
        *,
        title: str = "",
        icon: str | None = None,
        markdown: str = "",
        print_timestamp: bool = True,
        image_base64: str | None = None,
        qr_code: str | None = None,
    ) -> dict[str, Any]:
        """``POST /api/jobs`` - neuen Druckauftrag anlegen und einreihen.

        ``image_base64`` und ``qr_code`` sind exklusiv. Fuer ``image_base64``
        kann :func:`encode_image_file` genutzt werden, um eine Bilddatei zu
        kodieren.
        """
        payload = _build_job_payload(
            template,
            title=title,
            icon=icon,
            markdown=markdown,
            print_timestamp=print_timestamp,
            image_base64=image_base64,
            qr_code=qr_code,
        )
        return self._request("POST", "/api/jobs", json_body=payload)

    def cancel_job(self, job_id: str) -> dict[str, Any]:
        """``DELETE /api/jobs/{job_id}`` - Auftrag abbrechen (nur ``queued``/``failed``)."""
        return self._request("DELETE", f"/api/jobs/{job_id}")

    # --- preview --------------------------------------------------------------

    def preview(
        self,
        template: str,
        *,
        title: str = "",
        icon: str | None = None,
        markdown: str = "",
        print_timestamp: bool = True,
        image_base64: str | None = None,
        qr_code: str | None = None,
    ) -> bytes:
        """``POST /api/preview`` - PNG-Vorschau rendern, ohne Auftrag anzulegen.

        Gibt die rohen PNG-Bytes zurueck.
        """
        payload = _build_job_payload(
            template,
            title=title,
            icon=icon,
            markdown=markdown,
            print_timestamp=print_timestamp,
            image_base64=image_base64,
            qr_code=qr_code,
        )
        return self._request("POST", "/api/preview", json_body=payload, expect_json=False)


# --- CLI ------------------------------------------------------------------------


def _add_job_payload_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--template", required=True, help="Key einer konfigurierten Vorlage, z.B. 'todo'")
    parser.add_argument("--title", default="", help="Titel des Druckauftrags")
    parser.add_argument("--icon", help="Font-Awesome-Icon-Name, z.B. 'fa-cart-shopping'")

    markdown_group = parser.add_mutually_exclusive_group()
    markdown_group.add_argument("--markdown", help="Markdown-Inhalt als Text")
    markdown_group.add_argument(
        "--markdown-file", type=Path, metavar="PATH", help="Datei, deren Inhalt als Markdown gesendet wird"
    )

    parser.add_argument(
        "--no-timestamp",
        action="store_true",
        help="Zeitstempel unten rechts NICHT drucken (Default: drucken)",
    )

    content_group = parser.add_mutually_exclusive_group()
    content_group.add_argument(
        "--image", type=Path, metavar="PATH", help="Bilddatei, wird base64-kodiert als image_base64 gesendet"
    )
    content_group.add_argument("--qr-code", help="Inhalt fuer QR-Code (URL, WLAN, vCard, geo:..., ...)")


def _job_payload_kwargs(args: argparse.Namespace) -> dict[str, Any]:
    markdown = args.markdown or ""
    if args.markdown_file is not None:
        markdown = args.markdown_file.read_text(encoding="utf-8")

    image_base64 = encode_image_file(args.image) if args.image is not None else None

    return {
        "template": args.template,
        "title": args.title,
        "icon": args.icon,
        "markdown": markdown,
        "print_timestamp": not args.no_timestamp,
        "image_base64": image_base64,
        "qr_code": args.qr_code,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bondrucker_api.py",
        description="CLI fuer die Bondrucker REST-API (siehe docs/openapi.yaml).",
    )
    parser.add_argument(
        "--url",
        help=f"Basis-URL der API (Default: BONDRUCKER_API_URL / .env / {DEFAULT_BASE_URL})",
    )
    parser.add_argument(
        "--api-key",
        help="API-Key (Default: BONDRUCKER_API_KEY / API_KEY aus der .env)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="Timeout in Sekunden fuer HTTP-Requests (Default: 30)",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("health", help="Liveness-Check (/health, kein API-Key notwendig)")
    subparsers.add_parser("templates", help="Konfigurierte Druckvorlagen auflisten")
    subparsers.add_parser("icons", help="Verfuegbare Font-Awesome-Icon-Namen auflisten")
    subparsers.add_parser("printer-status", help="Drucker-Konnektivitaet und Warteschlange anzeigen")
    subparsers.add_parser("printer-power", help="Aktuellen Steckdosen-Zustand anzeigen (Ein/Aus)")
    subparsers.add_parser("printer-toggle", help="Steckdose umschalten und neuen Zustand anzeigen")

    presets_parser = subparsers.add_parser("presets", help="Standarddruckobjekte verwalten")
    presets_sub = presets_parser.add_subparsers(dest="presets_command", required=True)

    presets_sub.add_parser("list", help="Konfigurierte Standarddruckobjekte auflisten")

    presets_print_parser = presets_sub.add_parser("print", help="Standarddruckobjekt drucken und einreihen")
    presets_print_parser.add_argument("key", help="Key des Standarddruckobjekts, z.B. 'wlan-qrcode'")

    jobs_parser = subparsers.add_parser("jobs", help="Druckauftraege verwalten")
    jobs_sub = jobs_parser.add_subparsers(dest="jobs_command", required=True)

    list_parser = jobs_sub.add_parser("list", help="Druckauftraege auflisten")
    list_parser.add_argument("--status", choices=JOB_STATUSES, help="Nach Status filtern")

    get_parser = jobs_sub.add_parser("get", help="Einzelnen Druckauftrag abrufen")
    get_parser.add_argument("job_id")

    create_parser = jobs_sub.add_parser("create", help="Neuen Druckauftrag anlegen und einreihen")
    _add_job_payload_arguments(create_parser)

    cancel_parser = jobs_sub.add_parser(
        "cancel", help="Druckauftrag abbrechen (nur Status 'queued' oder 'failed')"
    )
    cancel_parser.add_argument("job_id")

    preview_parser = subparsers.add_parser(
        "preview", help="PNG-Vorschau rendern, ohne einen Druckauftrag anzulegen"
    )
    _add_job_payload_arguments(preview_parser)
    preview_parser.add_argument(
        "-o", "--output", default="preview.png", metavar="PATH", help="Zieldatei fuer die PNG-Vorschau (Default: preview.png)"
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    client = BondruckerClient(base_url=args.url, api_key=args.api_key, timeout=args.timeout)

    try:
        if args.command == "health":
            result: Any = client.health()
        elif args.command == "templates":
            result = client.list_templates()
        elif args.command == "icons":
            result = client.list_icons()
        elif args.command == "printer-status":
            result = client.printer_status()
        elif args.command == "printer-power":
            result = client.printer_power()
        elif args.command == "printer-toggle":
            result = client.toggle_printer_power()
        elif args.command == "presets":
            if args.presets_command == "list":
                result = client.list_presets()
            elif args.presets_command == "print":
                result = client.print_preset(args.key)
            else:  # pragma: no cover - argparse erzwingt gueltige Subcommands
                parser.error(f"Unbekannter presets-Befehl: {args.presets_command}")
                return 2
        elif args.command == "jobs":
            if args.jobs_command == "list":
                result = client.list_jobs(status=args.status)
            elif args.jobs_command == "get":
                result = client.get_job(args.job_id)
            elif args.jobs_command == "create":
                result = client.create_job(**_job_payload_kwargs(args))
            elif args.jobs_command == "cancel":
                result = client.cancel_job(args.job_id)
            else:  # pragma: no cover - argparse erzwingt gueltige Subcommands
                parser.error(f"Unbekannter jobs-Befehl: {args.jobs_command}")
                return 2
        elif args.command == "preview":
            png_bytes = client.preview(**_job_payload_kwargs(args))
            output_path = Path(args.output)
            output_path.write_bytes(png_bytes)
            print(f"Vorschau gespeichert: {output_path} ({len(png_bytes)} Bytes)")
            return 0
        else:  # pragma: no cover - argparse erzwingt gueltige Subcommands
            parser.error(f"Unbekannter Befehl: {args.command}")
            return 2
    except (BondruckerApiError, ValueError, OSError) as exc:
        print(f"Fehler: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
