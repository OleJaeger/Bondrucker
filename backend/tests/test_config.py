"""Web-configured settings overrides (``app_settings`` table, see app/config.py)."""

from __future__ import annotations

from app import database
from app.config import WEB_SETTINGS_FIELDS, env_locked_fields, get_effective_settings, get_settings
from app.repositories.settings import SettingsRepository


def test_get_effective_settings_without_overrides_matches_base(settings_env):
    assert get_effective_settings() == get_settings()


def test_get_effective_settings_applies_stored_override(settings_env):
    with database.session_scope() as session:
        SettingsRepository(session).set("mealie_base_url", "https://mealie.example.com")

    effective = get_effective_settings()
    assert effective.mealie_base_url == "https://mealie.example.com"
    # Unrelated fields are untouched.
    assert effective.mealie_api_token is None


def test_get_effective_settings_ignores_unknown_or_non_configurable_keys(settings_env):
    with database.session_scope() as session:
        repo = SettingsRepository(session)
        repo.set("not_a_real_field", "irrelevant")
        repo.set("api_key", "should-not-override-the-real-api-key")

    effective = get_effective_settings()
    assert effective.api_key == settings_env.api_key
    assert not hasattr(effective, "not_a_real_field")


def test_get_effective_settings_env_locked_field_wins_over_override(settings_env, monkeypatch):
    monkeypatch.setenv("MEALIE_BASE_URL", "https://from-env.example.com")
    get_settings.cache_clear()

    with database.session_scope() as session:
        SettingsRepository(session).set("mealie_base_url", "https://from-web-app.example.com")

    assert "mealie_base_url" in env_locked_fields()
    assert get_effective_settings().mealie_base_url == "https://from-env.example.com"


def test_get_effective_settings_deleted_override_reverts_to_default(settings_env):
    with database.session_scope() as session:
        repo = SettingsRepository(session)
        repo.set("sp_sync_path", "custom-path")
        assert get_effective_settings().sp_sync_path == "custom-path"

        repo.delete("sp_sync_path")

    assert get_effective_settings().sp_sync_path == "super-productivity"


def test_web_settings_fields_cover_only_preset_integration_settings():
    # A sanity check that nothing security/printer/storage-related slipped in.
    assert "api_key" not in WEB_SETTINGS_FIELDS
    assert "printer_host" not in WEB_SETTINGS_FIELDS
    assert "db_path" not in WEB_SETTINGS_FIELDS
