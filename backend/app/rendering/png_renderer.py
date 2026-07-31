"""Renders a :class:`Document` to a PNG preview image.

Uses the same word-wrapping / table-layout logic
(:mod:`app.rendering.layout`) as the ESC/POS renderer so the preview's line
breaks match the printed output. Pixel-perfect fidelity is not guaranteed
(Pillow's bundled default font is proportional, not monospace, unless an
operator provides ``PREVIEW_FONT_PATH``), but the layout structure is
identical.
"""

from __future__ import annotations

from datetime import datetime
from io import BytesIO

from PIL import Image, ImageDraw, ImageFont

from app.config import Settings
from app.rendering.document import (
    Document,
    Heading,
    ImageBlock,
    ListItem,
    Paragraph,
    TableBlock,
    TextRun,
    ThematicBreak,
)
from app.rendering.icons import render_icon_canvas
from app.rendering.layout import (
    LIST_INDENT,
    TextFragment,
    fragments_to_text,
    layout_table,
    list_item_prefix,
    wrap_runs,
)
from app.rendering.text_image import MARGIN, base_font_size, line_height_for, load_font, render_checklist_item
from app.templates.schema import TextStyle

CELL_PADDING = 4
MAX_CANVAS_HEIGHT = 8000


def render_preview(document: Document, settings: Settings) -> bytes:
    """Render ``document`` to a PNG image and return the raw bytes."""

    width_px = settings.printer_width_px
    width_chars = settings.printer_width_chars
    if document.template is not None and document.template.layout.width_chars:
        width_chars = document.template.layout.width_chars

    base_size = base_font_size(settings.preview_font_path, width_px, width_chars)

    image = Image.new("RGB", (width_px, MAX_CANVAS_HEIGHT), "white")
    draw = ImageDraw.Draw(image)
    y = MARGIN

    icon_image = render_icon_canvas(document.icon, width_px)
    if icon_image is not None:
        image.paste(icon_image.convert("RGB"), (0, y))
        y += icon_image.height + MARGIN

    if document.title:
        title_style = (
            document.template.default_formatting.title
            if document.template is not None
            else TextStyle(align="center", bold=True, double_width=True, double_height=True)
        )
        y = _draw_title(draw, settings, document.title, title_style, width_chars, width_px, base_size, y)
        y += MARGIN // 2

    body_align = (
        document.template.default_formatting.body.align if document.template is not None else "left"
    )

    for block in document.blocks:
        if isinstance(block, Heading):
            y = _draw_heading(draw, settings, block, width_chars, width_px, base_size, y)
        elif isinstance(block, Paragraph):
            y = _draw_paragraph(draw, settings, block, width_chars, width_px, base_size, y, body_align)
        elif isinstance(block, ListItem):
            y = _draw_list_item(image, draw, settings, block, width_chars, width_px, base_size, y)
        elif isinstance(block, TableBlock):
            y = _draw_table(draw, settings, block, width_chars, width_px, base_size, y)
        elif isinstance(block, ThematicBreak):
            y = _draw_thematic_break(draw, width_px, y)
        elif isinstance(block, ImageBlock):
            image.paste(block.image.convert("RGB"), (0, y))
            y += block.image.height + MARGIN

    if document.show_timestamp:
        y = _draw_timestamp(draw, settings, width_px, base_size, y)

    y += MARGIN
    image = image.crop((0, 0, width_px, min(y, MAX_CANVAS_HEIGHT)))

    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


# ---------------------------------------------------------------------------
# Drawing helpers
# ---------------------------------------------------------------------------


def _size_factor(style: TextStyle) -> float:
    factor = 1.0
    if style.double_height:
        factor += 0.5
    if style.double_width:
        factor += 0.5
    return factor


def _draw_lines(
    draw: ImageDraw.ImageDraw,
    lines: list[list[TextFragment]],
    y: int,
    width_px: int,
    font: ImageFont.FreeTypeFont,
    line_height: int,
    align: str = "left",
    indent_px: int = 0,
) -> int:
    for line in lines:
        total_w = sum(draw.textlength(f.text, font=font) for f in line)
        if align == "center":
            x = (width_px - total_w) / 2
        elif align == "right":
            x = width_px - MARGIN - total_w
        else:
            x = MARGIN + indent_px

        cx = x
        for frag in line:
            stroke = 1 if frag.bold else 0
            draw.text((cx, y), frag.text, font=font, fill="black", stroke_width=stroke, stroke_fill="black")
            w = draw.textlength(frag.text, font=font)
            if frag.underline or frag.italic:
                draw.line([(cx, y + line_height - 4), (cx + w, y + line_height - 4)], fill="black", width=1)
            cx += w
        y += line_height

    return y


def _draw_title(
    draw: ImageDraw.ImageDraw,
    settings: Settings,
    title: str,
    style: TextStyle,
    width_chars: int,
    width_px: int,
    base_size: int,
    y: int,
) -> int:
    factor = _size_factor(style)
    font = load_font(settings.preview_font_path, int(base_size * factor))
    line_height = line_height_for(font)

    avail_chars = max(width_chars // (2 if style.double_width else 1), 1)
    lines = wrap_runs([TextRun(text=title, bold=style.bold, underline=style.underline)], avail_chars)
    return _draw_lines(draw, lines, y, width_px, font, line_height, align=style.align)


# Heading sizes must stay smaller than the title (which renders at factor
# 2.0, i.e. double width + double height). Only level 1 gets a size bump
# (matching the ESC/POS double-height-only size); levels >= 2 use the
# default factor of 1.0 (normal size, bold, centered).
_HEADING_FACTOR = {1: 1.5}


def _draw_heading(
    draw: ImageDraw.ImageDraw,
    settings: Settings,
    block: Heading,
    width_chars: int,
    width_px: int,
    base_size: int,
    y: int,
) -> int:
    factor = _HEADING_FACTOR.get(block.level, 1.0)
    font = load_font(settings.preview_font_path, int(base_size * factor))
    line_height = line_height_for(font)

    avail_chars = max(width_chars // (2 if factor >= 2.0 else 1), 1)
    bold_runs = [TextRun(text=r.text, bold=True, italic=r.italic, underline=r.underline) for r in block.runs]
    lines = wrap_runs(bold_runs, avail_chars)
    return _draw_lines(draw, lines, y, width_px, font, line_height, align="center")


def _draw_paragraph(
    draw: ImageDraw.ImageDraw,
    settings: Settings,
    block: Paragraph,
    width_chars: int,
    width_px: int,
    base_size: int,
    y: int,
    align: str,
) -> int:
    font = load_font(settings.preview_font_path, base_size)
    line_height = line_height_for(font)
    lines = wrap_runs(block.runs, width_chars)
    return _draw_lines(draw, lines, y, width_px, font, line_height, align=align)


def _draw_list_item(
    image: Image.Image,
    draw: ImageDraw.ImageDraw,
    settings: Settings,
    item: ListItem,
    width_chars: int,
    width_px: int,
    base_size: int,
    y: int,
) -> int:
    if item.checked is not None:
        checklist_image = render_checklist_item(item, width_px, width_chars, settings.preview_font_path, base_size)
        image.paste(checklist_image.convert("RGB"), (0, y))
        return y + checklist_image.height

    font = load_font(settings.preview_font_path, base_size)
    line_height = line_height_for(font)

    indent_chars = LIST_INDENT * item.level
    prefix = list_item_prefix(item.ordered, item.index)
    avail = max(width_chars - indent_chars - len(prefix), 1)
    lines = wrap_runs(item.runs, avail)
    if not lines:
        lines = [[]]

    indent_px = draw.textlength(" " * indent_chars, font=font)
    prefix_px = draw.textlength(prefix, font=font)

    for i, line in enumerate(lines):
        prefixed_line = [TextFragment(text=prefix)] + line if i == 0 else line
        ind = indent_px if i == 0 else indent_px + prefix_px
        y = _draw_lines(draw, [prefixed_line], y, width_px, font, line_height, align="left", indent_px=int(ind))

    return y


def _draw_thematic_break(draw: ImageDraw.ImageDraw, width_px: int, y: int) -> int:
    y += 6
    draw.line([(MARGIN, y), (width_px - MARGIN, y)], fill="black", width=1)
    return y + 12


def _draw_timestamp(draw: ImageDraw.ImageDraw, settings: Settings, width_px: int, base_size: int, y: int) -> int:
    """Draw the current date/time, right-aligned, in the bottom-right corner."""

    font = load_font(settings.preview_font_path, int(base_size * 0.7))
    line_height = line_height_for(font)
    body_font = load_font(settings.preview_font_path, base_size)
    y += line_height_for(body_font)

    timestamp = datetime.now().strftime("%d.%m.%Y %H:%M")
    return _draw_lines(draw, [[TextFragment(text=timestamp)]], y, width_px, font, line_height, align="right")


def _draw_table(
    draw: ImageDraw.ImageDraw,
    settings: Settings,
    table: TableBlock,
    width_chars: int,
    width_px: int,
    base_size: int,
    y: int,
) -> int:
    font = load_font(settings.preview_font_path, base_size)
    line_height = line_height_for(font)

    table_layout = layout_table(table, width_chars)
    if not table_layout.widths:
        return y

    total_units = sum(table_layout.widths)
    avail_px = width_px - 2 * MARGIN
    col_px = [max(int(avail_px * w / total_units), 20) for w in table_layout.widths]
    col_px[-1] += avail_px - sum(col_px)

    row_groups: list[list[list[list[TextFragment]]]] = []
    if table_layout.header_lines:
        bold_header = [
            [[TextFragment(text=fragments_to_text(line), bold=True)] for line in col]
            for col in table_layout.header_lines
        ]
        row_groups.append(bold_header)
    row_groups.extend(table_layout.row_lines)

    x_start = MARGIN
    for row in row_groups:
        n_lines = max((len(c) for c in row), default=1) or 1
        row_h = n_lines * line_height + 2 * CELL_PADDING

        x = x_start
        for col_idx, cell_lines in enumerate(row):
            cw = col_px[col_idx]
            draw.rectangle([x, y, x + cw, y + row_h], outline="black")

            align = table_layout.alignments[col_idx]
            ty = y + CELL_PADDING
            for line in cell_lines:
                total_w = sum(draw.textlength(f.text, font=font) for f in line)
                if align == "center":
                    tx = x + (cw - total_w) / 2
                elif align == "right":
                    tx = x + cw - CELL_PADDING - total_w
                else:
                    tx = x + CELL_PADDING

                cx = tx
                for frag in line:
                    stroke = 1 if frag.bold else 0
                    draw.text((cx, ty), frag.text, font=font, fill="black", stroke_width=stroke, stroke_fill="black")
                    cx += draw.textlength(frag.text, font=font)
                ty += line_height

            x += cw

        y += row_h

    return y + MARGIN // 2
