"""``/api/table/parse`` endpoint tests."""

from __future__ import annotations

import io

import pytest


def _csv_file(content: str, filename: str = "data.csv") -> tuple[str, tuple[str, bytes, str]]:
    return ("file", (filename, content.encode(), "text/csv"))


def test_parse_csv_simple(client, auth_headers):
    csv = "Name,Alter,Stadt\nAlice,30,Berlin\nBob,25,Hamburg"
    response = client.post(
        "/api/table/parse",
        files=[_csv_file(csv)],
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["rows"] == 3
    assert body["columns"] == 3
    assert "| Name |" in body["markdown"]
    assert "| Alice |" in body["markdown"]
    assert body["warnings"] == []


def test_parse_csv_semicolon_delimiter(client, auth_headers):
    csv = "A;B;C\n1;2;3"
    response = client.post(
        "/api/table/parse",
        files=[_csv_file(csv)],
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["columns"] == 3


def test_parse_csv_pipe_in_cell_is_escaped(client, auth_headers):
    csv = "Titel,Wert\nA|B,42"
    response = client.post(
        "/api/table/parse",
        files=[_csv_file(csv)],
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert "A\\|B" in response.json()["markdown"]


def test_parse_csv_too_many_columns_returns_400(client, auth_headers):
    header = ",".join(f"Col{i}" for i in range(9))
    csv = header + "\n" + ",".join("x" for _ in range(9))
    response = client.post(
        "/api/table/parse",
        files=[_csv_file(csv)],
        headers=auth_headers,
    )
    assert response.status_code == 400
    assert "Spalten" in response.json()["detail"]


def test_parse_csv_many_columns_triggers_warning(client, auth_headers):
    header = ",".join(f"Col{i}" for i in range(5))
    csv = header + "\n" + ",".join("x" for _ in range(5))
    response = client.post(
        "/api/table/parse",
        files=[_csv_file(csv)],
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert len(response.json()["warnings"]) > 0


def test_parse_csv_empty_returns_400(client, auth_headers):
    response = client.post(
        "/api/table/parse",
        files=[_csv_file("")],
        headers=auth_headers,
    )
    assert response.status_code == 400


def test_parse_unsupported_format_returns_400(client, auth_headers):
    response = client.post(
        "/api/table/parse",
        files=[("file", ("data.txt", b"hello", "text/plain"))],
        headers=auth_headers,
    )
    assert response.status_code == 400
    assert "Dateiformat" in response.json()["detail"]


def test_parse_requires_auth(client):
    csv = "A,B\n1,2"
    response = client.post(
        "/api/table/parse",
        files=[_csv_file(csv)],
    )
    assert response.status_code == 401


def test_parse_csv_row_limit_triggers_warning(client, auth_headers):
    rows = ["A,B"] + [f"r{i},v{i}" for i in range(201)]
    csv = "\n".join(rows)
    response = client.post(
        "/api/table/parse",
        files=[_csv_file(csv)],
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["rows"] == 200
    assert any("200" in w for w in body["warnings"])


def test_parse_xlsx(client, auth_headers):
    openpyxl = pytest.importorskip("openpyxl")
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Name", "Wert"])
    ws.append(["Alice", 42])
    buf = io.BytesIO()
    wb.save(buf)

    response = client.post(
        "/api/table/parse",
        files=[("file", ("data.xlsx", buf.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"))],
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["rows"] == 2
    assert body["columns"] == 2
    assert "| Name |" in body["markdown"]
