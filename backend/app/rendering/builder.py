"""Builds a renderer-agnostic :class:`Document` from a print job payload.

Shared by the job-creation endpoint (eager validation), the preview endpoint
and the queue worker, so all three agree on what a given payload renders to.
"""

from __future__ import annotations

from typing import Any

from app.config import get_settings
from app.exceptions import InvalidAttachmentError
from app.rendering.attachments import decode_uploaded_image, generate_qr_image
from app.rendering.document import Block, Document, ImageBlock
from app.rendering.markdown import parse_markdown
from app.templates.loader import get_template_registry


def build_document(payload: dict[str, Any]) -> Document:
    """Resolve ``payload`` (``template``/``title``/``icon``/``markdown``/
    ``image_base64``/``qr_code``) into a :class:`Document`.

    Raises :class:`~app.exceptions.TemplateNotFoundError`,
    :class:`~app.exceptions.InvalidMarkdownError` or
    :class:`~app.exceptions.InvalidAttachmentError` if the payload is invalid.
    """

    template = get_template_registry().get(payload["template"])
    blocks: list[Block] = parse_markdown(payload.get("markdown") or "")

    image_base64 = payload.get("image_base64")
    qr_code = payload.get("qr_code")
    if image_base64 and qr_code:
        raise InvalidAttachmentError("Bild und QR-Code koennen nicht gleichzeitig gedruckt werden.")

    width_px = get_settings().printer_width_px
    if image_base64:
        blocks = [ImageBlock(image=decode_uploaded_image(image_base64, width_px)), *blocks]
    elif qr_code:
        blocks = [ImageBlock(image=generate_qr_image(qr_code, width_px)), *blocks]

    icon = payload.get("icon")
    if icon is None:
        icon = template.icon

    show_timestamp = payload.get("print_timestamp", True)

    return Document(
        title=payload.get("title") or "",
        icon=icon,
        blocks=blocks,
        template=template,
        show_timestamp=show_timestamp,
    )
