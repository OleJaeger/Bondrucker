"""Decoding/processing for user-supplied print-job attachments: an uploaded
image (converted to dithered black & white) or a generated QR code.

Both produce a single :class:`PIL.Image.Image` (mode "1", centered on a
``width_px``-wide canvas) for use as an
:class:`app.rendering.document.ImageBlock`, printed via
:meth:`escpos.escpos.Escpos.image` and pasted into the PNG preview.
"""

from __future__ import annotations

import base64
import binascii
from io import BytesIO

import qrcode
from PIL import Image, UnidentifiedImageError

from app.exceptions import InvalidAttachmentError

# Generous limit on the *decoded* image size - large enough for any photo a
# user would reasonably print on an 80mm thermal printer, small enough to
# bound memory/CPU use of the resize/dither step.
_MAX_IMAGE_BYTES = 5 * 1024 * 1024

# Caps the resized image height so a very tall/narrow image cannot produce an
# enormous canvas (and PNG preview / print job).
_MAX_IMAGE_HEIGHT_PX = 2000

# QR codes are square; printing them as wide as the full receipt looks
# oversized, so they are capped well below ``width_px``.
_MAX_QR_SIZE_PX = 384


def decode_uploaded_image(data: str, width_px: int) -> Image.Image:
    """Decode a base64 (optionally ``data:`` URL) encoded image and convert
    it to a dithered black & white image, scaled to fit ``width_px`` and
    centered on a ``width_px``-wide canvas (mode "1").

    Raises :class:`InvalidAttachmentError` if ``data`` is not a valid,
    reasonably sized image.
    """

    raw = _decode_base64(data)
    if len(raw) > _MAX_IMAGE_BYTES:
        raise InvalidAttachmentError(
            f"Bild ist zu gross ({len(raw)} Bytes, Limit {_MAX_IMAGE_BYTES} Bytes)"
        )

    try:
        image = Image.open(BytesIO(raw))
        image.load()
    except (UnidentifiedImageError, OSError) as exc:
        raise InvalidAttachmentError("Datei ist kein gueltiges Bild") from exc

    image = image.convert("L")

    scale = min(width_px / image.width, _MAX_IMAGE_HEIGHT_PX / image.height)
    new_size = (max(round(image.width * scale), 1), max(round(image.height * scale), 1))
    if new_size != image.size:
        image = image.resize(new_size, Image.LANCZOS)

    return _center_on_canvas(image.convert("1"), width_px)


def generate_qr_image(content: str, width_px: int) -> Image.Image:
    """Generate a QR code for ``content``, centered on a ``width_px``-wide
    canvas (mode "1").

    Raises :class:`InvalidAttachmentError` if ``content`` is empty.
    """

    if not content.strip():
        raise InvalidAttachmentError("QR-Code-Inhalt darf nicht leer sein")

    target_px = min(width_px, _MAX_QR_SIZE_PX)

    # Two-pass: determine the module count for this content at the default
    # box size, then pick a box size that fills target_px as closely as
    # possible. Avoids resizing the generated image, which would blur the
    # crisp black/white modules.
    probe = qrcode.QRCode(border=2)
    probe.add_data(content)
    probe.make(fit=True)
    modules = probe.modules_count + 2 * probe.border
    box_size = max(target_px // modules, 1)

    qr = qrcode.QRCode(border=2, box_size=box_size)
    qr.add_data(content)
    qr.make(fit=True)
    image = qr.make_image(fill_color="black", back_color="white").get_image().convert("1")

    return _center_on_canvas(image, width_px)


def _center_on_canvas(image: Image.Image, width_px: int) -> Image.Image:
    if image.width >= width_px:
        return image

    canvas = Image.new("1", (width_px, image.height), "white")
    x = (width_px - image.width) // 2
    canvas.paste(image, (x, 0))
    return canvas


def _decode_base64(data: str) -> bytes:
    if data.startswith("data:"):
        _, _, data = data.partition(",")

    try:
        return base64.b64decode(data)
    except (binascii.Error, ValueError) as exc:
        raise InvalidAttachmentError("Bilddaten konnten nicht decodiert werden (ungueltiges Base64)") from exc
