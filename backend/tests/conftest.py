"""Shared pytest fixtures.

Each test gets its own temporary SQLite database and a fresh
:class:`~app.config.Settings` (env vars via ``monkeypatch`` +
``get_settings.cache_clear()``). API-level tests use a stubbed queue worker
(:class:`tests.fakes.StubWorker`) so job-status assertions are not racy;
queue-processing itself is covered by the dedicated worker tests.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import database
from app.config import get_settings
from app.presets.loader import reset_preset_registry
from app.rendering.icons import reset_icon_renderer
from app.templates.loader import reset_template_registry
from tests.fakes import StubWorker

PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def settings_env(tmp_path, monkeypatch):
    """Point the app at a temporary DB/log dir and the real template configs."""

    monkeypatch.setenv("API_KEY", "test-api-key")
    monkeypatch.setenv("DB_PATH", str(tmp_path / "app.db"))
    monkeypatch.setenv("TEMPLATES_DIR", str(PROJECT_ROOT / "config" / "templates"))
    monkeypatch.setenv("PRESETS_DIR", str(PROJECT_ROOT / "config" / "presets"))
    monkeypatch.setenv("LOG_DIR", str(tmp_path / "logs"))
    monkeypatch.setenv("PRINTER_HOST", "127.0.0.1")
    monkeypatch.setenv("PRINTER_PORT", "19999")
    monkeypatch.setenv("RETRY_BASE_DELAY_SECONDS", "0.05")
    monkeypatch.setenv("RETRY_MAX_DELAY_SECONDS", "0.2")
    monkeypatch.setenv("QUEUE_POLL_INTERVAL_SECONDS", "0.02")
    monkeypatch.setenv("CORS_ORIGINS", "")
    monkeypatch.setenv("FONTAWESOME_FONT_PATH", str(tmp_path / "missing-font.ttf"))
    monkeypatch.setenv("FONTAWESOME_MAP_PATH", str(tmp_path / "missing-map.json"))
    monkeypatch.setenv("CUSTOM_ICONS_DIR", str(tmp_path / "missing-icons"))

    get_settings.cache_clear()
    reset_template_registry()
    reset_preset_registry()
    reset_icon_renderer()
    database.reset_engine()
    database.init_db()

    yield get_settings()

    database.reset_engine()
    get_settings.cache_clear()
    reset_template_registry()
    reset_preset_registry()
    reset_icon_renderer()


@pytest.fixture
def auth_headers(settings_env):
    return {"X-API-Key": settings_env.api_key}


@pytest.fixture
def client(settings_env, monkeypatch):
    """``TestClient`` with a stubbed queue worker (no background thread)."""

    monkeypatch.setattr("app.main.QueueWorker", StubWorker)

    import app.main as main

    with TestClient(main.app) as test_client:
        yield test_client
