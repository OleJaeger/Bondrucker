"""``/api/jobs``, ``/api/preview`` and ``/api/printer/status`` endpoint tests.

Uses the stubbed queue worker (see ``conftest.py``), so created jobs stay in
``queued`` state - queue processing itself is covered by
``test_worker.py``.
"""

from __future__ import annotations

from pathlib import Path

from app import database
from app.config import get_settings
from app.models import JobStatus
from app.rendering.icons import reset_icon_renderer
from app.repositories.jobs import JobRepository

PROJECT_ROOT = Path(__file__).resolve().parents[1]

TODO_PAYLOAD = {
    "template": "todo",
    "title": "Einkaufsliste",
    "icon": "fa-cart-shopping",
    "markdown": "# Aufgaben\n\n- [ ] Milch\n- [x] Brot",
}


def test_create_job_returns_201_with_full_payload(client, auth_headers):
    response = client.post("/api/jobs", json=TODO_PAYLOAD, headers=auth_headers)
    assert response.status_code == 201

    body = response.json()
    assert body["status"] == "queued"
    assert body["template"] == "todo"
    assert body["title"] == "Einkaufsliste"
    assert body["icon"] == "fa-cart-shopping"
    assert body["markdown"] == TODO_PAYLOAD["markdown"]
    assert body["retry_count"] == 0
    assert body["error_message"] is None
    assert body["completed_at"] is None
    assert "id" in body and "created_at" in body and "updated_at" in body


def test_create_job_with_unknown_template_returns_400(client, auth_headers):
    payload = {**TODO_PAYLOAD, "template": "does-not-exist"}
    response = client.post("/api/jobs", json=payload, headers=auth_headers)
    assert response.status_code == 400
    assert "does-not-exist" in response.json()["detail"]


def test_create_job_with_too_long_markdown_returns_400(client, auth_headers):
    payload = {**TODO_PAYLOAD, "markdown": "x" * 50_001}
    response = client.post("/api/jobs", json=payload, headers=auth_headers)
    assert response.status_code == 400


def test_create_job_minimal_payload_uses_template_defaults(client, auth_headers):
    response = client.post("/api/jobs", json={"template": "freitext", "markdown": "Hallo"}, headers=auth_headers)
    assert response.status_code == 201
    body = response.json()
    assert body["title"] == ""
    assert body["icon"] is None
    assert body["markdown"] == "Hallo"
    assert body["print_timestamp"] is True


def test_create_job_with_empty_title_and_markdown_returns_422(client, auth_headers):
    response = client.post("/api/jobs", json={"template": "freitext"}, headers=auth_headers)
    assert response.status_code == 422


def test_create_job_with_whitespace_only_title_and_markdown_returns_422(client, auth_headers):
    payload = {"template": "freitext", "title": "   ", "markdown": "\n  \t"}
    response = client.post("/api/jobs", json=payload, headers=auth_headers)
    assert response.status_code == 422


def test_create_job_can_disable_print_timestamp(client, auth_headers):
    payload = {**TODO_PAYLOAD, "print_timestamp": False}
    response = client.post("/api/jobs", json=payload, headers=auth_headers)
    assert response.status_code == 201
    assert response.json()["print_timestamp"] is False


def test_get_job_returns_created_job(client, auth_headers):
    created = client.post("/api/jobs", json=TODO_PAYLOAD, headers=auth_headers).json()

    response = client.get(f"/api/jobs/{created['id']}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_get_unknown_job_returns_404(client, auth_headers):
    response = client.get("/api/jobs/does-not-exist", headers=auth_headers)
    assert response.status_code == 404


def test_list_jobs_filters_by_status(client, auth_headers):
    client.post("/api/jobs", json=TODO_PAYLOAD, headers=auth_headers)
    client.post("/api/jobs", json=TODO_PAYLOAD, headers=auth_headers)

    response = client.get("/api/jobs", params={"status": "queued"}, headers=auth_headers)
    assert response.status_code == 200
    jobs = response.json()
    assert len(jobs) == 2
    assert all(job["status"] == "queued" for job in jobs)

    response = client.get("/api/jobs", params={"status": "failed"}, headers=auth_headers)
    assert response.json() == []


def test_list_jobs_rejects_invalid_status(client, auth_headers):
    response = client.get("/api/jobs", params={"status": "bogus"}, headers=auth_headers)
    assert response.status_code == 422


def test_cancel_queued_job(client, auth_headers):
    created = client.post("/api/jobs", json=TODO_PAYLOAD, headers=auth_headers).json()

    response = client.delete(f"/api/jobs/{created['id']}", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "cancelled"
    # Cancelled jobs retain their content (privacy rule for non-completed jobs).
    assert body["markdown"] == TODO_PAYLOAD["markdown"]


def test_cancel_already_cancelled_job_returns_409(client, auth_headers):
    created = client.post("/api/jobs", json=TODO_PAYLOAD, headers=auth_headers).json()
    client.delete(f"/api/jobs/{created['id']}", headers=auth_headers)

    response = client.delete(f"/api/jobs/{created['id']}", headers=auth_headers)
    assert response.status_code == 409


def test_cancel_unknown_job_returns_404(client, auth_headers):
    response = client.delete("/api/jobs/does-not-exist", headers=auth_headers)
    assert response.status_code == 404


def test_completed_job_has_scrubbed_content(client, auth_headers):
    created = client.post("/api/jobs", json=TODO_PAYLOAD, headers=auth_headers).json()

    with database.session_scope() as session:
        repo = JobRepository(session)
        repo.mark_completed(repo.get(created["id"]))

    response = client.get(f"/api/jobs/{created['id']}", headers=auth_headers)
    body = response.json()
    assert body["status"] == "completed"
    assert body["completed_at"] is not None
    for field in ("template", "title", "icon", "markdown", "error_message"):
        assert body[field] is None


def test_preview_returns_png(client, auth_headers):
    response = client.post("/api/preview", json=TODO_PAYLOAD, headers=auth_headers)
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content[:8] == b"\x89PNG\r\n\x1a\n"


def test_preview_with_unknown_template_returns_400(client, auth_headers):
    payload = {**TODO_PAYLOAD, "template": "does-not-exist"}
    response = client.post("/api/preview", json=payload, headers=auth_headers)
    assert response.status_code == 400


def test_preview_with_empty_title_and_markdown_returns_422(client, auth_headers):
    response = client.post("/api/preview", json={"template": "freitext"}, headers=auth_headers)
    assert response.status_code == 422


def test_list_icons_returns_empty_list_without_assets(client, auth_headers):
    response = client.get("/api/icons", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == []


def test_list_icons_returns_known_icon_names_with_real_assets(client, auth_headers, monkeypatch):
    monkeypatch.setenv("FONTAWESOME_FONT_PATH", str(PROJECT_ROOT / "assets" / "fontawesome" / "fa-solid-900.ttf"))
    monkeypatch.setenv("FONTAWESOME_MAP_PATH", str(PROJECT_ROOT / "assets" / "fontawesome" / "icon-map.json"))
    get_settings.cache_clear()
    reset_icon_renderer()

    try:
        response = client.get("/api/icons", headers=auth_headers)
        assert response.status_code == 200
        icons = response.json()
        assert "fa-cart-shopping" in icons
        assert icons == sorted(icons)
    finally:
        get_settings.cache_clear()
        reset_icon_renderer()


def test_list_icons_returns_custom_svg_icons(client, auth_headers, monkeypatch):
    monkeypatch.setenv("CUSTOM_ICONS_DIR", str(PROJECT_ROOT / "assets" / "icons"))
    get_settings.cache_clear()
    reset_icon_renderer()

    try:
        response = client.get("/api/icons", headers=auth_headers)
        assert response.status_code == 200
        assert "svg-logo" in response.json()
    finally:
        get_settings.cache_clear()
        reset_icon_renderer()


def test_get_icon_svg_returns_svg_for_known_custom_icon(client, auth_headers, monkeypatch):
    monkeypatch.setenv("CUSTOM_ICONS_DIR", str(PROJECT_ROOT / "assets" / "icons"))
    get_settings.cache_clear()
    reset_icon_renderer()

    try:
        response = client.get("/api/icons/svg-logo/svg", headers=auth_headers)
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/svg+xml"
        assert response.content.startswith(b"<?xml")
    finally:
        get_settings.cache_clear()
        reset_icon_renderer()


def test_get_icon_svg_returns_404_for_unknown_icon(client, auth_headers):
    response = client.get("/api/icons/svg-does-not-exist/svg", headers=auth_headers)
    assert response.status_code == 404


def test_printer_status_reports_worker_state(client, auth_headers):
    client.post("/api/jobs", json=TODO_PAYLOAD, headers=auth_headers)

    worker = client.app.state.queue_worker
    worker.printer_client.online = False
    worker._current_job_id = "abc123"

    response = client.get("/api/printer/status", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body == {"online": False, "queue_length": 1, "current_job": "abc123"}


def test_printer_status_counts_queued_and_failed_jobs(client, auth_headers):
    created = client.post("/api/jobs", json=TODO_PAYLOAD, headers=auth_headers).json()
    client.post("/api/jobs", json=TODO_PAYLOAD, headers=auth_headers)

    from datetime import datetime

    with database.session_scope() as session:
        repo = JobRepository(session)
        repo.mark_failed(repo.get(created["id"]), "error", datetime.utcnow())

    response = client.get("/api/printer/status", headers=auth_headers)
    body = response.json()
    assert body["queue_length"] == 2  # 1 queued + 1 failed

    jobs = client.get("/api/jobs", params={"status": "failed"}, headers=auth_headers).json()
    assert len(jobs) == 1
    assert jobs[0]["status"] == JobStatus.FAILED.value
