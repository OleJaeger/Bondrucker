"""Table file conversion endpoint (``/api/table/parse``).

Accepts a CSV or XLSX upload, validates that it is printable on an 80mm
thermal printer (column count, row count, file size) and returns a Markdown
table string.
"""

from __future__ import annotations

import csv
import io

from fastapi import APIRouter, Depends, File, UploadFile, status
from fastapi.responses import JSONResponse

from app.exceptions import InvalidAttachmentError
from app.security import require_api_key

router = APIRouter(prefix="/api/table", tags=["table"], dependencies=[Depends(require_api_key)])

_MAX_FILE_BYTES = 1 * 1024 * 1024  # 1 MB
_MAX_COLUMNS = 8
_WARN_COLUMNS = 5
_MAX_ROWS = 200


@router.post("/parse", status_code=status.HTTP_200_OK)
async def parse_table(file: UploadFile = File(...)) -> JSONResponse:
    """Parse an uploaded CSV or XLSX file and convert it to a Markdown table.

    Returns ``{ markdown, rows, columns, warnings }``.  Raises 400 if the
    file format is unsupported, the file is too large, empty, or has too many
    columns to fit on an 80 mm thermal printer.
    """

    content = await file.read()
    if len(content) > _MAX_FILE_BYTES:
        raise InvalidAttachmentError(
            f"Datei zu groß ({len(content) // 1024} KB, Limit 1 MB)."
        )

    filename = (file.filename or "").lower()
    if filename.endswith(".csv"):
        rows = _parse_csv(content)
    elif filename.endswith(".xlsx"):
        rows = _parse_xlsx(content)
    else:
        raise InvalidAttachmentError(
            "Nicht unterstütztes Dateiformat. Bitte eine CSV- oder XLSX-Datei hochladen."
        )

    if not rows:
        raise InvalidAttachmentError("Die Tabelle ist leer.")

    columns = max(len(row) for row in rows)
    if columns > _MAX_COLUMNS:
        raise InvalidAttachmentError(
            f"Die Tabelle hat {columns} Spalten. "
            f"Für den 80-mm-Thermodrucker werden maximal {_MAX_COLUMNS} Spalten unterstützt."
        )

    warnings: list[str] = []
    if columns >= _WARN_COLUMNS:
        warnings.append(
            f"{columns} Spalten können auf dem Thermodrucker sehr eng werden. "
            "Prüfe die Vorschau sorgfältig."
        )

    if len(rows) > _MAX_ROWS:
        warnings.append(
            f"Die Tabelle hat {len(rows)} Zeilen. "
            f"Nur die ersten {_MAX_ROWS} Zeilen werden berücksichtigt."
        )
        rows = rows[:_MAX_ROWS]

    return JSONResponse({
        "markdown": _to_markdown(rows),
        "rows": len(rows),
        "columns": columns,
        "warnings": warnings,
    })


def _parse_csv(content: bytes) -> list[list[str]]:
    text = content.decode("utf-8-sig", errors="replace")
    try:
        dialect = csv.Sniffer().sniff(text[:2048], delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel
    reader = csv.reader(io.StringIO(text), dialect)
    return [row for row in reader if any(cell.strip() for cell in row)]


def _parse_xlsx(content: bytes) -> list[list[str]]:
    try:
        import openpyxl
    except ImportError as exc:
        raise InvalidAttachmentError(
            "XLSX-Unterstützung nicht verfügbar (openpyxl nicht installiert)."
        ) from exc

    try:
        wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
        ws = wb.active
        rows: list[list[str]] = []
        for row in ws.iter_rows(values_only=True):  # type: ignore[union-attr]
            cells = [str(cell) if cell is not None else "" for cell in row]
            if any(c.strip() for c in cells):
                rows.append(cells)
        return rows
    except Exception as exc:
        raise InvalidAttachmentError(
            f"XLSX-Datei konnte nicht gelesen werden: {exc}"
        ) from exc


def _to_markdown(rows: list[list[str]]) -> str:
    max_cols = max(len(row) for row in rows)
    padded = [row + [""] * (max_cols - len(row)) for row in rows]

    def escape(cell: str) -> str:
        return cell.replace("|", "\\|").replace("\n", " ").strip()

    header = padded[0]
    body = padded[1:]

    lines = [
        "| " + " | ".join(escape(c) for c in header) + " |",
        "| " + " | ".join("---" for _ in header) + " |",
        *("| " + " | ".join(escape(c) for c in row) + " |" for row in body),
    ]
    return "\n".join(lines)
