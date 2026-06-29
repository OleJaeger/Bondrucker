"""Shared bitmap-rendering helpers used by both the PNG preview renderer and
the ESC/POS renderer.

Two concerns live here:

* Font loading and a *dynamic* base font size, so that word-wrapped lines
  (computed in characters via :mod:`app.rendering.layout`) actually fit
  within ``width_px`` pixels in the PNG preview - independent of the
  configured ``PREVIEW_FONT_PATH`` and any per-template ``width_chars``
  override.
* Rendering a checklist item (``- [ ]`` / ``- [x]``) as a small bitmap that
  combines a Font Awesome ``fa-square`` / ``fa-square-check`` icon with the
  wrapped item text. ESC/POS printers cannot mix an inline icon bitmap with
  text on the same line, so checklist items are sent as a single raster
  image (via :meth:`escpos.escpos.Escpos.image`) by both renderers - this
  keeps the preview and the printout identical.
"""

from __future__ import annotations

import os
from functools import lru_cache

import barcode
from PIL import Image, ImageDraw, ImageFont

from app.rendering.document import ListItem
from app.rendering.icons import get_icon_renderer
from app.rendering.layout import LIST_INDENT, wrap_runs

MARGIN = 12
LINE_HEIGHT_FACTOR = 1.35

# Width (in characters) reserved for the checkbox icon, matching the
# previous "[ ] " / "[x] " text prefix so word-wrapping stays unchanged.
CHECKLIST_PREFIX_CHARS = 4

_FONT_SIZE_REFERENCE = 100

# Pillow's bundled default font (Aileron) has a limited character set that
# does not cover German umlauts (ä/ö/ü/ß), rendering them as ".notdef" boxes.
# DejaVu Sans Mono, bundled with python-barcode (a python-escpos dependency),
# covers the full Latin-1 range and is used as the fallback before
# ``ImageFont.load_default()``.
_FALLBACK_FONT_PATH = os.path.join(os.path.dirname(barcode.__file__), "fonts", "DejaVuSansMono.ttf")


@lru_cache(maxsize=16)
def load_font(path: str | None, size: int) -> ImageFont.FreeTypeFont:
    for candidate in (path, _FALLBACK_FONT_PATH):
        if candidate:
            try:
                return ImageFont.truetype(candidate, size=size)
            except OSError:
                continue
    return ImageFont.load_default(size=size)


@lru_cache(maxsize=8)
def base_font_size(font_path: str | None, width_px: int, width_chars: int) -> int:
    """Largest font size whose monospace character width still fits
    ``width_chars`` columns into ``width_px`` pixels.

    Word-wrapping happens in characters (:func:`app.rendering.layout.wrap_runs`),
    so the font used to draw those lines must be sized such that
    ``width_chars`` characters do not exceed ``width_px`` - otherwise long
    lines extend past the right edge of the preview image.
    """

    reference = load_font(font_path, _FONT_SIZE_REFERENCE)
    char_width = reference.getlength("0")
    if char_width <= 0:
        return _FONT_SIZE_REFERENCE // 4

    px_per_char = width_px / max(width_chars, 1)
    return max(int(_FONT_SIZE_REFERENCE * px_per_char / char_width), 8)


def line_height_for(font: ImageFont.FreeTypeFont) -> int:
    return int(font.size * LINE_HEIGHT_FACTOR)


def render_checklist_item(
    item: ListItem,
    width_px: int,
    width_chars: int,
    font_path: str | None,
    font_size: int,
) -> Image.Image:
    """Render one checklist item (icon + wrapped text) onto a
    ``width_px``-wide 1-bit canvas.

    The result is used as a raster image by both renderers so a checklist
    looks identical in the PNG preview and on the printout.
    """

    font = load_font(font_path, font_size)
    line_height = line_height_for(font)

    indent_chars = LIST_INDENT * item.level
    avail = max(width_chars - indent_chars - CHECKLIST_PREFIX_CHARS, 1)
    lines = wrap_runs(item.runs, avail)
    if not lines:
        lines = [[]]

    image = Image.new("L", (width_px, len(lines) * line_height), color=255)
    draw = ImageDraw.Draw(image)

    indent_px = draw.textlength(" " * indent_chars, font=font)
    prefix_px = draw.textlength(" " * CHECKLIST_PREFIX_CHARS, font=font)
    text_x = MARGIN + indent_px + prefix_px

    icon_size = max(line_height - 4, 1)
    icon_x = int(MARGIN + indent_px)
    icon_y = (line_height - icon_size) // 2
    if item.checked:
        icon = get_icon_renderer().render("fa-square-check", icon_size)
        if icon is not None:
            image.paste(icon, (icon_x, (line_height - icon.height) // 2))
    else:
        # The bundled Solid-weight Font Awesome font has no hollow "empty
        # checkbox" glyph - "fa-square" there is a filled square, which next
        # to "fa-square-check" reads as reversed (filled = open, outline =
        # done). Draw a plain rounded outline so unchecked items look like
        # an empty box.
        border = max(icon_size // 10, 1)
        radius = max(icon_size // 8, 1)
        draw.rounded_rectangle(
            [icon_x, icon_y, icon_x + icon_size - 1, icon_y + icon_size - 1],
            radius=radius,
            outline=0,
            width=border,
        )

    y = 0
    for line in lines:
        cx = text_x
        for frag in line:
            stroke = 1 if frag.bold else 0
            draw.text((cx, y), frag.text, font=font, fill=0, stroke_width=stroke, stroke_fill=0)
            w = draw.textlength(frag.text, font=font)
            if frag.underline or frag.italic:
                draw.line([(cx, y + line_height - 4), (cx + w, y + line_height - 4)], fill=0, width=1)
            cx += w
        y += line_height

    return image.convert("1")
