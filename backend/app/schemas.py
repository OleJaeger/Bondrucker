"""Pydantic request/response models for the public API."""

from __future__ import annotations

import json
from datetime import datetime

from pydantic import BaseModel, Field, model_validator

from app.models import JobStatus, PrintJob
from app.presets.schema import PresetConfig
from app.templates.schema import TemplateConfig


class PrintJobCreate(BaseModel):
    """Request body for ``POST /api/jobs`` and ``POST /api/preview``."""

    template: str = Field(..., min_length=1, description="Key of a configured template, e.g. 'todo'")
    title: str = Field(default="", description="Title printed above the content")
    icon: str | None = Field(
        default=None, description="Icon name, e.g. 'fa-cart-shopping' (Font Awesome) or 'svg-logo' (custom SVG)"
    )
    markdown: str = Field(default="", description="Markdown content of the print job")
    print_timestamp: bool = Field(
        default=True,
        description="Whether to print the current date/time in the bottom-right corner",
    )
    image_base64: str | None = Field(
        default=None,
        max_length=7_000_000,
        description=(
            "Base64-encoded image (optionally a 'data:' URL), printed after the title as "
            "black & white. Mutually exclusive with qr_code."
        ),
    )
    qr_code: str | None = Field(
        default=None,
        max_length=2000,
        description=(
            "Content to encode as a QR code (URL, WLAN, vCard, geo-location, ...), printed "
            "after the title. Mutually exclusive with image_base64."
        ),
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "template": "todo",
                    "title": "Einkaufsliste",
                    "icon": "fa-cart-shopping",
                    "markdown": "# Aufgaben\n\n- [ ] Milch\n- [x] Brot",
                    "print_timestamp": True,
                }
            ]
        }
    }

    @model_validator(mode="after")
    def _require_content(self) -> "PrintJobCreate":
        if (
            not self.title.strip()
            and not self.markdown.strip()
            and not self.image_base64
            and not self.qr_code
        ):
            raise ValueError("Titel, Inhalt (Markdown), Bild oder QR-Code darf nicht leer sein.")
        return self

    @model_validator(mode="after")
    def _exclusive_attachment(self) -> "PrintJobCreate":
        if self.image_base64 and self.qr_code:
            raise ValueError("Bild und QR-Code koennen nicht gleichzeitig gedruckt werden.")
        return self


class PrintJobResponse(BaseModel):
    """Response body for job endpoints.

    For jobs in a terminal ``completed`` state, ``template``/``title``/
    ``icon``/``markdown``/``error_message`` are always ``null`` - their
    content is scrubbed from the database on success (privacy by design).
    """

    id: str
    status: JobStatus
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None
    retry_count: int
    error_message: str | None = None
    template: str | None = None
    title: str | None = None
    icon: str | None = None
    markdown: str | None = None
    print_timestamp: bool | None = None
    image_base64: str | None = None
    qr_code: str | None = None

    @classmethod
    def from_job(cls, job: PrintJob) -> "PrintJobResponse":
        payload: dict = {}
        if job.payload_json:
            try:
                payload = json.loads(job.payload_json)
            except ValueError:
                payload = {}

        return cls(
            id=job.id,
            status=JobStatus(job.status),
            created_at=job.created_at,
            updated_at=job.updated_at,
            completed_at=job.completed_at,
            retry_count=job.retry_count,
            error_message=job.error_message,
            template=payload.get("template"),
            title=payload.get("title"),
            icon=payload.get("icon"),
            markdown=payload.get("markdown"),
            print_timestamp=payload.get("print_timestamp"),
            image_base64=payload.get("image_base64"),
            qr_code=payload.get("qr_code"),
        )


class PrinterStatusResponse(BaseModel):
    """Response body for ``GET /api/printer/status``."""

    online: bool
    queue_length: int
    current_job: str | None = None


class PrinterPowerResponse(BaseModel):
    """Response body for ``GET /api/printer/power`` and ``POST /api/printer/power/toggle``."""

    power: bool


class TemplateInfo(BaseModel):
    """Response body item for ``GET /api/templates``.

    Lets the frontend populate the "create job" form without hardcoding
    the set of available templates.
    """

    key: str
    name: str
    type: str
    icon: str | None = None
    allow_markdown: bool = True
    allow_attachment: bool = True
    default_markdown: str | None = None

    @classmethod
    def from_config(cls, config: TemplateConfig) -> "TemplateInfo":
        return cls(
            key=config.key,
            name=config.name,
            type=config.type,
            icon=config.icon,
            allow_markdown=config.fields.markdown,
            allow_attachment=config.fields.attachment,
            default_markdown=config.default_markdown,
        )


class PresetInfo(BaseModel):
    """Response body item for ``GET /api/presets``."""

    key: str
    name: str
    description: str
    icon: str | None = None
    template: str
    category: str

    @classmethod
    def from_config(cls, config: PresetConfig) -> "PresetInfo":
        return cls(
            key=config.key,
            name=config.name,
            description=config.description,
            icon=config.icon,
            template=config.template,
            category=config.category,
        )


class SettingFieldInfo(BaseModel):
    """Response body item for ``GET``/``PUT /api/settings``.

    One entry per ``app.config.WEB_SETTINGS_FIELDS`` field. Secret fields
    never carry their actual value - ``is_set`` indicates whether one is
    configured, and a new value can be written without ever reading the old
    one back.
    """

    key: str
    group: str
    label: str
    type: str
    secret: bool
    locked: bool
    value: str | int | None
    is_set: bool
    default: str | int | None
    used_by_presets: list[str]
