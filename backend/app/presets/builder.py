"""Builds a print-job payload (for ``app.rendering.builder.build_document``) from a preset."""

from __future__ import annotations

import base64
import mimetypes
from pathlib import Path
from typing import Any

from app.config import get_settings
from app.exceptions import InvalidAttachmentError
from app.presets.schema import PresetConfig
from app.presets.script_runner import run_content_script, run_image_script


def build_preset_payload(preset: PresetConfig) -> dict[str, Any]:
    """Resolve ``preset`` into a ``PrintJobCreate``-shaped payload dict.

    Runs ``preset.content_script`` (if set) to obtain the markdown content,
    and resolves a static ``attachment`` (QR code or image) into
    ``qr_code``/``image_base64``.
    """

    if preset.content_script:
        markdown = run_content_script(preset.content_script)
    else:
        markdown = preset.content or ""

    payload: dict[str, Any] = {
        "template": preset.template,
        "title": preset.title,
        "icon": preset.icon,
        "markdown": markdown,
        "print_timestamp": preset.print_timestamp,
    }

    if preset.attachment is not None:
        if preset.attachment.type == "qr_code":
            payload["qr_code"] = preset.attachment.content
        elif preset.attachment.path:
            payload["image_base64"] = _encode_image(preset.attachment.path)
        else:
            image = run_image_script(preset.attachment.script)
            payload["image_base64"] = _encode_image_bytes(image, "image/png")

    return payload


def _encode_image(path: str) -> str:
    settings = get_settings()
    image_path = Path(settings.presets_dir) / path
    try:
        data = image_path.read_bytes()
    except OSError as exc:
        raise InvalidAttachmentError(f"Anhangsdatei {path!r} konnte nicht gelesen werden") from exc

    mime_type, _ = mimetypes.guess_type(image_path.name)
    mime_type = mime_type or "application/octet-stream"
    return _encode_image_bytes(data, mime_type)


def _encode_image_bytes(data: bytes, mime_type: str) -> str:
    return f"data:{mime_type};base64,{base64.b64encode(data).decode('ascii')}"
