"""ESC/POS renderer, PNG preview renderer and icon rendering."""

from __future__ import annotations

import re
from io import BytesIO
from pathlib import Path

from escpos.constants import GS, PAPER_FULL_CUT
from escpos.printer import Dummy
from PIL import Image

from app.config import get_settings
from app.rendering.builder import build_document
from app.rendering.document import ImageBlock, ListItem, TextRun
from app.rendering.escpos_renderer import render_document
from app.rendering.icons import IconRenderer, get_icon_renderer, render_icon_canvas
from app.rendering.png_renderer import render_preview
from app.rendering.text_image import MARGIN, base_font_size, line_height_for, load_font, render_checklist_item

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TIMESTAMP_RE = re.compile(rb"\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}")


def _render_to_dummy(payload: dict) -> bytes:
    document = build_document(payload)
    printer = Dummy()
    render_document(printer, document, get_settings())
    return printer.output


def test_escpos_render_cancels_kanji_mode_before_text(settings_env):
    # The V330M boots in Kanji (double-byte GBK) mode, which garbles German
    # umlauts encoded as single CP437 bytes into Chinese glyphs. "FS ."
    # (0x1c 0x2e) must be sent first to switch to single-byte mode.
    output = _render_to_dummy({"template": "freitext", "title": "T", "markdown": "Jäger"})
    assert output.startswith(b"\x1c.")


def test_escpos_render_includes_title_and_content(settings_env):
    output = _render_to_dummy(
        {
            "template": "todo",
            "title": "Einkaufsliste",
            "icon": "fa-cart-shopping",
            "markdown": "# Aufgaben\n\n- [ ] Milch\n- [x] Brot",
        }
    )
    assert b"Einkaufsliste" in output
    assert b"Aufgaben" in output

    # Checklist items are rendered as raster images (fa-square /
    # fa-square-check icon + wrapped text), not as literal text.
    assert b"Milch" not in output
    assert b"Brot" not in output
    assert b"[ ] " not in output
    assert b"[x] " not in output

    # Header icon + one raster image per checklist item ("GS v 0").
    assert output.count(GS + b"v0") == 3


def test_escpos_render_cuts_when_template_requests_it(settings_env):
    output = _render_to_dummy({"template": "freitext", "title": "T", "markdown": "Hallo"})
    assert PAPER_FULL_CUT in output


def test_escpos_render_skips_cut_when_layout_disables_it(settings_env):
    document = build_document({"template": "freitext", "title": "T", "markdown": "Hallo"})
    document.template.layout.cut = False

    printer = Dummy()
    render_document(printer, document, get_settings())

    assert PAPER_FULL_CUT not in printer.output


def test_escpos_render_includes_timestamp_by_default(settings_env):
    output = _render_to_dummy({"template": "freitext", "title": "T", "markdown": "Hallo"})
    assert TIMESTAMP_RE.search(output) is not None


def test_escpos_render_can_disable_timestamp(settings_env):
    output = _render_to_dummy({"template": "freitext", "title": "T", "markdown": "Hallo", "print_timestamp": False})
    assert TIMESTAMP_RE.search(output) is None


def test_png_preview_returns_valid_image_at_configured_width(settings_env):
    document = build_document(
        {
            "template": "todo",
            "title": "Einkaufsliste",
            "icon": "fa-cart-shopping",
            "markdown": "# Aufgaben\n\n- [ ] Milch\n- [x] Brot\n\n| A | B |\n| - | - |\n| 1 | 2 |",
        }
    )
    png_bytes = render_preview(document, get_settings())

    image = Image.open(BytesIO(png_bytes))
    assert image.format == "PNG"
    assert image.width == get_settings().printer_width_px
    assert image.height > 0


def test_png_preview_renders_german_umlauts(settings_env):
    # Pillow's bundled default font (Aileron) lacks glyphs for ä/ö/ü/ß and
    # renders them as ".notdef" boxes. Without an operator-configured
    # PREVIEW_FONT_PATH, the fallback font must cover these characters.
    font = load_font(get_settings().preview_font_path, 26)
    assert font.getname()[0] != "Aileron"
    assert font.getmask("ä", mode="1").getbbox() is not None

    document = build_document({"template": "freitext", "title": "Müsli", "markdown": "Größe: ÄÖÜäöüß"})
    png_bytes = render_preview(document, get_settings())

    image = Image.open(BytesIO(png_bytes))
    assert image.format == "PNG"


def test_png_preview_includes_timestamp_by_default(settings_env):
    document = build_document({"template": "freitext", "title": "T", "markdown": "Hallo"})
    with_timestamp = render_preview(document, get_settings())

    document.show_timestamp = False
    without_timestamp = render_preview(document, get_settings())

    assert Image.open(BytesIO(with_timestamp)).height > Image.open(BytesIO(without_timestamp)).height


def test_base_font_size_keeps_wrapped_lines_within_printer_width(settings_env):
    # Regression test for the overflow bug: wrapping happens in characters
    # (width_chars), so the chosen font size must not let width_chars
    # characters exceed width_px pixels.
    settings = get_settings()
    base_size = base_font_size(settings.preview_font_path, settings.printer_width_px, settings.printer_width_chars)
    font = load_font(settings.preview_font_path, base_size)

    line_px = settings.printer_width_chars * font.getlength("0")
    assert line_px <= settings.printer_width_px


def test_png_heading_sizes_are_smaller_than_title(settings_env):
    settings = get_settings()
    base_size = base_font_size(settings.preview_font_path, settings.printer_width_px, settings.printer_width_chars)

    title_font = load_font(settings.preview_font_path, int(base_size * 2.0))  # double width + double height
    h1_font = load_font(settings.preview_font_path, int(base_size * 1.5))
    h2_font = load_font(settings.preview_font_path, int(base_size * 1.0))

    assert h1_font.size < title_font.size
    assert h2_font.size < h1_font.size


def test_render_checklist_item_produces_icon_and_text_bitmap(settings_env):
    settings = get_settings()
    base_size = base_font_size(settings.preview_font_path, settings.printer_width_px, settings.printer_width_chars)

    item = ListItem(runs=[TextRun(text="Milch")], checked=False)
    image = render_checklist_item(
        item, settings.printer_width_px, settings.printer_width_chars, settings.preview_font_path, base_size
    )

    assert image.mode == "1"
    assert image.width == settings.printer_width_px
    assert image.height > 0
    # Icon + text produce some black pixels, not a blank canvas.
    assert image.getextrema()[0] == 0


def test_render_checklist_item_unchecked_box_is_hollow(settings_env):
    # The bundled Solid-weight Font Awesome font has no hollow "empty
    # checkbox" glyph - "fa-square" there is a filled square. Unchecked
    # items must instead draw an outline box, so the center of the icon is
    # white, not a solid black square.
    settings = get_settings()
    base_size = base_font_size(settings.preview_font_path, settings.printer_width_px, settings.printer_width_chars)
    line_height = line_height_for(load_font(settings.preview_font_path, base_size))

    item = ListItem(runs=[TextRun(text="Milch")], checked=False)
    image = render_checklist_item(
        item, settings.printer_width_px, settings.printer_width_chars, settings.preview_font_path, base_size
    ).convert("L")

    icon_size = max(line_height - 4, 1)
    icon_y = (line_height - icon_size) // 2
    center = image.getpixel((MARGIN + icon_size // 2, icon_y + icon_size // 2))
    assert center == 255


def _uploaded_image_data_url() -> str:
    import base64

    buffer = BytesIO()
    Image.new("RGB", (20, 10), "red").save(buffer, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()


def test_build_document_with_uploaded_image_prepends_image_block(settings_env):
    document = build_document(
        {"template": "freitext", "title": "Foto", "markdown": "Text", "image_base64": _uploaded_image_data_url()}
    )

    assert isinstance(document.blocks[0], ImageBlock)
    assert document.blocks[0].image.mode == "1"
    assert document.blocks[0].image.width == get_settings().printer_width_px


def test_build_document_with_qr_code_prepends_image_block(settings_env):
    document = build_document({"template": "freitext", "title": "QR", "qr_code": "https://example.com"})

    assert isinstance(document.blocks[0], ImageBlock)
    assert document.blocks[0].image.mode == "1"


def test_escpos_render_prints_image_block_as_raster(settings_env):
    output = _render_to_dummy({"template": "freitext", "title": "Foto", "image_base64": _uploaded_image_data_url()})
    assert output.count(GS + b"v0") >= 1


def test_png_preview_includes_uploaded_image(settings_env):
    document = build_document({"template": "freitext", "title": "Foto", "image_base64": _uploaded_image_data_url()})
    png_bytes = render_preview(document, get_settings())

    image = Image.open(BytesIO(png_bytes))
    assert image.format == "PNG"
    assert image.height > 0


def test_render_icon_canvas_returns_none_without_icon(settings_env):
    assert render_icon_canvas(None, 576) is None
    assert render_icon_canvas("  ", 576) is None


def test_render_icon_canvas_returns_image_for_icon(settings_env):
    canvas = render_icon_canvas("fa-cart-shopping", 576)
    assert canvas is not None
    assert canvas.size[0] == 576


def test_icon_renderer_falls_back_to_placeholder_when_assets_missing(settings_env):
    renderer = get_icon_renderer()
    assert renderer._font_available is False
    assert renderer.available_icons() == []

    glyph = renderer.render("fa-cart-shopping", 50)
    assert glyph is not None
    assert glyph.size == (50, 50)


def test_icon_renderer_renders_real_glyph_when_assets_present(settings_env):
    settings = get_settings().model_copy(
        update={
            "fontawesome_font_path": str(PROJECT_ROOT / "assets" / "fontawesome" / "fa-solid-900.ttf"),
            "fontawesome_map_path": str(PROJECT_ROOT / "assets" / "fontawesome" / "icon-map.json"),
        }
    )
    renderer = IconRenderer(settings)

    assert renderer._font_available is True
    assert "fa-cart-shopping" in renderer.available_icons()
    assert renderer.available_icons() == sorted(renderer.available_icons())

    glyph = renderer.render("fa-cart-shopping", 64)
    assert glyph is not None
    assert glyph.size == (64, 64)
    # A real glyph isn't a blank canvas - it must contain some black pixels.
    assert glyph.getextrema()[0] == 0

    # Unknown icon names still degrade to the placeholder, not an error.
    placeholder = renderer.render("fa-does-not-exist", 64)
    assert placeholder is not None


def test_icon_renderer_renders_custom_svg_icon(settings_env):
    settings = get_settings().model_copy(update={"custom_icons_dir": str(PROJECT_ROOT / "assets" / "icons")})
    renderer = IconRenderer(settings)

    assert "svg-logo" in renderer.available_icons()
    assert renderer.available_icons() == sorted(renderer.available_icons())
    assert renderer.custom_icon_path("svg-logo") == PROJECT_ROOT / "assets" / "icons" / "logo.svg"
    assert renderer.custom_icon_path("svg-does-not-exist") is None

    icon = renderer.render("svg-logo", 64)
    assert icon is not None
    assert icon.size == (64, 64)
    # The icon isn't a blank canvas - it must contain both black and white pixels.
    assert icon.getextrema() == (0, 255)


def test_icon_renderer_falls_back_to_placeholder_for_unreadable_custom_svg(tmp_path, settings_env):
    icons_dir = tmp_path / "icons"
    icons_dir.mkdir()
    (icons_dir / "broken.svg").write_text("not valid svg", encoding="utf-8")

    settings = get_settings().model_copy(update={"custom_icons_dir": str(icons_dir)})
    renderer = IconRenderer(settings)

    assert "svg-broken" in renderer.available_icons()
    icon = renderer.render("svg-broken", 32)
    assert icon is not None
    assert icon.size == (32, 32)


def test_icon_renderer_handles_invalid_map_file_gracefully(tmp_path, settings_env):
    font_path = tmp_path / "fake-font.ttf"
    map_path = tmp_path / "icon-map.json"
    font_path.write_bytes(b"not a real font")
    map_path.write_text("not valid json", encoding="utf-8")

    settings = get_settings().model_copy(
        update={"fontawesome_font_path": str(font_path), "fontawesome_map_path": str(map_path)}
    )
    renderer = IconRenderer(settings)

    assert renderer._font_available is False
    assert renderer.render("fa-cart-shopping", 32) is not None


def test_icon_renderer_returns_none_for_empty_icon_name(settings_env):
    renderer = get_icon_renderer()
    assert renderer.render("", 32) is None
    assert renderer.render("   ", 32) is None
