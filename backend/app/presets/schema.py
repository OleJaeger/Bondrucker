"""Pydantic schema for standard print object (preset) configuration files (YAML)."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, field_validator, model_validator

from app.config import WEB_SETTINGS_FIELDS

AttachmentType = Literal["qr_code", "image"]

# content_script names are dotted into "app.presets.scripts.<name>" via
# importlib - restrict to safe Python module names.
_SCRIPT_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")


class PresetAttachment(BaseModel):
    """Static or dynamic attachment (QR code or image) printed after the title."""

    type: AttachmentType
    # Required for type "qr_code": the content to encode.
    content: str | None = None
    # For type "image": exactly one of "path" (static, relative to the
    # presets directory, settings.presets_dir) or "script" (dynamic, name of
    # a module in app.presets.scripts providing generate_image() -> bytes,
    # called to produce the image when the preset is printed).
    path: str | None = None
    script: str | None = None

    @field_validator("script")
    @classmethod
    def _valid_script_name(cls, value: str | None) -> str | None:
        if value is not None and not _SCRIPT_NAME_RE.match(value):
            raise ValueError("attachment.script muss ein gueltiger Python-Modulname sein (^[a-z][a-z0-9_]*$)")
        return value

    @model_validator(mode="after")
    def _check_fields(self) -> "PresetAttachment":
        if self.type == "qr_code" and not (self.content and self.content.strip()):
            raise ValueError("attachment.content ist fuer type 'qr_code' erforderlich")
        if self.type == "image" and bool(self.path) == bool(self.script):
            raise ValueError("attachment.path und attachment.script sind fuer type 'image' exklusiv (genau eines)")
        return self


class PresetConfig(BaseModel):
    """A fully validated standard print object (preset) configuration.

    ``key`` is derived from the YAML filename (without extension) and is the
    identifier used in ``GET /api/presets`` and
    ``POST /api/presets/{key}/print``.
    """

    key: str
    name: str
    description: str
    icon: str
    template: str
    # Groups presets in the UI listing (GET /api/presets is rendered as one
    # section per distinct category, in first-seen order).
    category: str = "Sonstige"
    title: str = ""
    # Static markdown content. Mutually exclusive with content_script.
    content: str | None = None
    # Name of a module in app.presets.scripts providing generate() -> str,
    # called to produce the markdown content when the preset is printed.
    content_script: str | None = None
    attachment: PresetAttachment | None = None
    print_timestamp: bool = True
    # Registers this preset's use of web-configurable Settings fields (see
    # app.config.WEB_SETTINGS_FIELDS) - e.g. a preset whose content_script
    # calls Mealie lists "mealie_base_url" here, so GET /api/settings can show
    # which presets a given setting affects.
    config_keys: list[str] = []

    @field_validator("name", "description", "icon", "template", "category")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("must not be empty")
        return value

    @field_validator("config_keys")
    @classmethod
    def _valid_config_keys(cls, value: list[str]) -> list[str]:
        unknown = [key for key in value if key not in WEB_SETTINGS_FIELDS]
        if unknown:
            raise ValueError(f"config_keys enthaelt unbekannte Settings-Felder: {', '.join(unknown)}")
        return value

    @field_validator("content_script")
    @classmethod
    def _valid_script_name(cls, value: str | None) -> str | None:
        if value is not None and not _SCRIPT_NAME_RE.match(value):
            raise ValueError("content_script muss ein gueltiger Python-Modulname sein (^[a-z][a-z0-9_]*$)")
        return value

    @model_validator(mode="after")
    def _exclusive_content(self) -> "PresetConfig":
        if self.content and self.content_script:
            raise ValueError("content und content_script sind exklusiv")
        return self
