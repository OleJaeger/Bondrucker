"""Application configuration via environment variables (.env)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Literal

from dotenv import dotenv_values
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Security ---------------------------------------------------
    api_key: str
    docs_enabled: bool = True

    # --- Printer ------------------------------------------------------
    printer_host: str = "127.0.0.1"
    printer_port: int = 9100
    printer_timeout: float = 5.0
    printer_cut_after_print: bool = True
    printer_feed_lines: int = 3

    # --- Layout ---------------------------------------------------------
    printer_width_chars: int = 48
    printer_width_px: int = 576

    # --- Storage -----------------------------------------------------------
    db_path: str = "data/app.db"
    templates_dir: str = "config/templates"
    presets_dir: str = "config/presets"
    log_dir: str = "logs"
    log_level: str = "INFO"

    # --- Icons --------------------------------------------------------------
    fontawesome_font_path: str = "assets/fontawesome/fa-solid-900.ttf"
    fontawesome_map_path: str = "assets/fontawesome/icon-map.json"

    # Directory of custom SVG icons (one file per icon, e.g. "logo.svg" ->
    # icon name "svg-logo"). See backend/assets/icons/README.md.
    custom_icons_dir: str = "assets/icons"

    # Directory of image assets used by preset image scripts (e.g. sheets of
    # motifs with a red grid, see app/presets/grid_images.py).
    images_dir: str = "assets/images"

    # Optional TTF/OTF used for the PNG preview. If unset (or unreadable),
    # Pillow's bundled default font is used, which is proportional rather
    # than monospace - a monospace font (e.g. DejaVu Sans Mono) gives a more
    # faithful preview of the character-grid ESC/POS output.
    preview_font_path: str | None = None

    # --- Queue / retry ---------------------------------------------------------
    retry_base_delay_seconds: float = 5.0
    retry_max_delay_seconds: float = 300.0
    queue_poll_interval_seconds: float = 1.0

    # --- Standarddruckobjekte (Presets) ---------------------------------------
    mealie_base_url: str | None = None
    mealie_api_token: str | None = None
    mealie_shopping_list_id: str | None = None

    weather_latitude: float = 52.52
    weather_longitude: float = 13.405
    weather_location_name: str = "Berlin"

    homeassistant_url: str | None = None
    homeassistant_token: str | None = None
    homeassistant_printer_plug: str = "switch.plug_016"

    sp_webdav_url: str | None = None
    sp_webdav_username: str | None = None
    sp_webdav_password: str | None = None
    sp_sync_path: str = "super-productivity"

    jagd_db_host: str | None = None
    jagd_db_port: int = 5000
    jagd_db_name: str | None = None
    jagd_db_user: str | None = None
    jagd_db_password: str | None = None

    # --- CORS -----------------------------------------------------------------
    cors_origins: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance.

    Cached so the .env file is only parsed once; tests can call
    ``get_settings.cache_clear()`` after monkeypatching environment variables.
    """

    return Settings()


@dataclass(frozen=True)
class SettingFieldSpec:
    """Metadata for a ``Settings`` field that may be configured via the web app."""

    key: str
    group: str
    label: str
    type: Literal["str", "int"] = "str"
    secret: bool = False


# Settings fields editable via the web app (``GET``/``PUT /api/settings``).
# These are exactly the fields preset content scripts use to talk to external
# services (Mealie, HomeAssistant, Super Productivity, the Jagdzeiten DB) -
# everything else (printer, storage paths, security, ...) stays .env-only.
# Field whose name (uppercased) is set via the environment or .env is locked
# and cannot be overridden here - see ``env_locked_fields()``.
WEB_SETTINGS_FIELDS: dict[str, SettingFieldSpec] = {
    spec.key: spec
    for spec in (
        SettingFieldSpec("mealie_base_url", "Mealie (Einkaufsliste)", "Basis-URL"),
        SettingFieldSpec("mealie_api_token", "Mealie (Einkaufsliste)", "API-Token", secret=True),
        SettingFieldSpec("mealie_shopping_list_id", "Mealie (Einkaufsliste)", "Einkaufslisten-ID (optional)"),
        SettingFieldSpec("weather_location_name", "Wetter / HomeAssistant", "Ortsname"),
        SettingFieldSpec("homeassistant_url", "Wetter / HomeAssistant", "HomeAssistant-URL"),
        SettingFieldSpec("homeassistant_token", "Wetter / HomeAssistant", "HomeAssistant-Token", secret=True),
        SettingFieldSpec("homeassistant_printer_plug", "Wetter / HomeAssistant", "Steckdosen-Entity (Drucker)"),
        SettingFieldSpec("sp_webdav_url", "Super Productivity", "WebDAV-URL"),
        SettingFieldSpec("sp_webdav_username", "Super Productivity", "WebDAV-Benutzername"),
        SettingFieldSpec("sp_webdav_password", "Super Productivity", "WebDAV-Passwort", secret=True),
        SettingFieldSpec("sp_sync_path", "Super Productivity", "Sync-Pfad"),
        SettingFieldSpec("jagd_db_host", "Jagdtag", "Datenbank-Host"),
        SettingFieldSpec("jagd_db_port", "Jagdtag", "Datenbank-Port", type="int"),
        SettingFieldSpec("jagd_db_name", "Jagdtag", "Datenbank-Name"),
        SettingFieldSpec("jagd_db_user", "Jagdtag", "Datenbank-Benutzer"),
        SettingFieldSpec("jagd_db_password", "Jagdtag", "Datenbank-Passwort", secret=True),
    )
}


def env_locked_fields() -> set[str]:
    """Names of ``Settings`` fields explicitly set via the environment or .env.

    These win over any web-configured override and cannot be changed through
    the web app - ".env always wins" is the whole point of "gesperrte Felder".
    """

    raw_keys = set(os.environ.keys())
    dotenv_path = Path(Settings.model_config.get("env_file") or ".env")
    if dotenv_path.exists():
        raw_keys |= {key for key, value in dotenv_values(dotenv_path).items() if value is not None}
    return {key.lower() for key in raw_keys}


def get_effective_settings() -> Settings:
    """``Settings`` with web-configured overrides applied.

    Layers, from lowest to highest precedence: field defaults < web-configured
    overrides (``app_settings`` table, only for unlocked ``WEB_SETTINGS_FIELDS``)
    < environment/.env. Used by preset content scripts and the settings API so
    changes made in the web app take effect immediately, without restarting
    the container.
    """

    base = get_settings()

    from app.database import init_db, session_scope
    from app.repositories.settings import SettingsRepository

    init_db()
    with session_scope() as session:
        stored = SettingsRepository(session).get_all()

    locked = env_locked_fields()
    overrides = {key: value for key, value in stored.items() if key in WEB_SETTINGS_FIELDS and key not in locked}
    if not overrides:
        return base
    return base.model_copy(update=overrides)
