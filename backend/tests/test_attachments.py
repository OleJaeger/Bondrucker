"""Image upload decoding and QR code generation for print-job attachments."""

from __future__ import annotations

import base64
from io import BytesIO

import pytest
from PIL import Image

from app.exceptions import InvalidAttachmentError
from app.rendering.attachments import _MAX_IMAGE_BYTES, decode_uploaded_image, generate_qr_image


def _encode_png(image: Image.Image) -> str:
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()


def test_decode_uploaded_image_converts_to_dithered_bw_and_scales_to_width():
    source = Image.new("RGB", (100, 50), "red")
    result = decode_uploaded_image(_encode_png(source), width_px=576)

    assert result.mode == "1"
    assert result.width == 576
    assert result.height == 288  # 100x50 scaled by 576/100 = 5.76


def test_decode_uploaded_image_accepts_data_url_prefix():
    source = Image.new("RGB", (10, 10), "black")
    data_url = "data:image/png;base64," + _encode_png(source)

    result = decode_uploaded_image(data_url, width_px=100)

    assert result.mode == "1"
    assert result.size == (100, 100)


def test_decode_uploaded_image_caps_height_and_centers_narrow_result():
    source = Image.new("RGB", (10, 10000), "black")
    result = decode_uploaded_image(_encode_png(source), width_px=576)

    assert result.width == 576
    assert result.height == 2000


def test_decode_uploaded_image_rejects_invalid_base64():
    with pytest.raises(InvalidAttachmentError):
        decode_uploaded_image("not-base64!!!", width_px=576)


def test_decode_uploaded_image_rejects_non_image_data():
    with pytest.raises(InvalidAttachmentError):
        decode_uploaded_image(base64.b64encode(b"hello world").decode(), width_px=576)


def test_decode_uploaded_image_rejects_oversized_payload():
    huge = base64.b64encode(b"x" * (_MAX_IMAGE_BYTES + 1)).decode()
    with pytest.raises(InvalidAttachmentError):
        decode_uploaded_image(huge, width_px=576)


def test_generate_qr_image_returns_centered_bw_image():
    image = generate_qr_image("https://example.com", width_px=576)

    assert image.mode == "1"
    assert image.width == 576
    assert 0 < image.height <= 576
    # Not a blank canvas.
    assert image.getextrema()[0] == 0


def test_generate_qr_image_rejects_empty_content():
    with pytest.raises(InvalidAttachmentError):
        generate_qr_image("   ", width_px=576)
