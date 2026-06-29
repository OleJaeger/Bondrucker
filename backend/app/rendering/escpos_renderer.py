"""Renders a :class:`Document` to an ESC/POS printer via python-escpos."""

from __future__ import annotations

from datetime import datetime

from escpos.constants import FS
from escpos.escpos import Escpos

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
    fragments_to_text,
    layout_table,
    list_item_prefix,
    render_table_rows,
    wrap_runs,
)
from app.rendering.text_image import base_font_size, render_checklist_item
from app.templates.schema import TextStyle

# Markdown heading level -> ESC/POS size. Headings must stay smaller than
# the title (double width + double height): level 1 is double height only,
# everything else (>=2) is normal size, all bold and centered
# ("Zentrierte Ueberschriften").
_HEADING_SIZE: dict[int, dict[str, bool]] = {
    1: {"double_height": True},
}


def render_document(printer: Escpos, document: Document, settings: Settings) -> None:
    """Send ``document`` to ``printer`` using ESC/POS commands."""

    width = settings.printer_width_chars
    if document.template is not None and document.template.layout.width_chars:
        width = document.template.layout.width_chars

    font_size = base_font_size(settings.preview_font_path, settings.printer_width_px, width)

    # The V330M boots in Kanji (double-byte GBK) character mode. In that
    # mode, codepage bytes >= 0x80 emitted for German umlauts (e.g. CP437
    # 0x84 for "ä") get paired with the following byte and printed as a
    # Chinese glyph instead of the intended single-byte character. "FS ."
    # cancels Kanji mode so single-byte codepages render correctly.
    printer._raw(FS + b".")

    printer.set(align="left", bold=False, underline=0, normal_textsize=True)

    icon_image = render_icon_canvas(document.icon, settings.printer_width_px)
    if icon_image is not None:
        printer.set(align="center")
        printer.image(icon_image)
        printer.set(align="left", normal_textsize=True)
        printer.ln(1)

    if document.title:
        title_style = (
            document.template.default_formatting.title
            if document.template is not None
            else TextStyle(align="center", bold=True, double_width=True, double_height=True)
        )
        _render_title(printer, document.title, title_style, width)
        printer.ln(1)

    body_align = (
        document.template.default_formatting.body.align if document.template is not None else "left"
    )

    for block in document.blocks:
        if isinstance(block, Heading):
            _render_heading(printer, block, width)
        elif isinstance(block, Paragraph):
            _render_paragraph(printer, block, width, body_align)
        elif isinstance(block, ListItem):
            _render_list_item(printer, block, width, settings, font_size)
        elif isinstance(block, TableBlock):
            _render_table(printer, block, width)
        elif isinstance(block, ThematicBreak):
            _render_thematic_break(printer, width)
        elif isinstance(block, ImageBlock):
            _render_image(printer, block)

    if document.show_timestamp:
        _render_timestamp(printer)

    if document.template is not None:
        feed_lines = document.template.layout.feed_lines
        cut = document.template.layout.cut
    else:
        feed_lines = settings.printer_feed_lines
        cut = settings.printer_cut_after_print

    printer.set(align="left", bold=False, underline=0, normal_textsize=True)
    if feed_lines:
        printer.ln(feed_lines)
    if cut:
        printer.cut()


def _render_title(printer: Escpos, title: str, style: TextStyle, width: int) -> None:
    factor = 2 if style.double_width else 1
    avail = max(width // factor, 1)
    lines = wrap_runs([TextRun(text=title, bold=style.bold, underline=style.underline)], avail)

    size_kwargs: dict[str, bool] = {}
    if style.double_width or style.double_height:
        size_kwargs = {"double_width": style.double_width, "double_height": style.double_height}
    else:
        size_kwargs = {"normal_textsize": True}

    printer.set(align=style.align, bold=style.bold, underline=2 if style.underline else 0, **size_kwargs)
    for line in lines:
        printer.text(fragments_to_text(line) + "\n")
    printer.set(align="left", bold=False, underline=0, normal_textsize=True)


def _render_heading(printer: Escpos, block: Heading, width: int) -> None:
    size = _HEADING_SIZE.get(block.level, {})
    factor = 2 if size.get("double_width") else 1
    avail = max(width // factor, 1)
    lines = wrap_runs(block.runs, avail)

    if size:
        printer.set(align="center", bold=True, **size)
    else:
        printer.set(align="center", bold=True, normal_textsize=True)

    for line in lines:
        for frag in line:
            printer.set(bold=True, underline=2 if (frag.italic or frag.underline) else 0)
            printer.text(frag.text)
        printer.text("\n")

    printer.set(align="left", bold=False, underline=0, normal_textsize=True)


def _render_paragraph(printer: Escpos, block: Paragraph, width: int, align: str) -> None:
    lines = wrap_runs(block.runs, width)
    printer.set(align=align, normal_textsize=True)
    for line in lines:
        if not line:
            printer.text("\n")
            continue
        for frag in line:
            printer.set(bold=frag.bold, underline=2 if (frag.italic or frag.underline) else 0)
            printer.text(frag.text)
        printer.text("\n")
    printer.set(align="left", bold=False, underline=0)


def _render_list_item(printer: Escpos, item: ListItem, width: int, settings: Settings, font_size: int) -> None:
    if item.checked is not None:
        image = render_checklist_item(item, settings.printer_width_px, width, settings.preview_font_path, font_size)
        printer.set(align="left", bold=False, underline=0, normal_textsize=True)
        printer.image(image)
        return

    indent = LIST_INDENT * item.level
    prefix = list_item_prefix(item.ordered, item.index)
    hang = indent + len(prefix)
    avail = max(width - hang, 1)
    lines = wrap_runs(item.runs, avail)

    printer.set(align="left", bold=False, underline=0, normal_textsize=True)
    if not lines:
        lines = [[]]
    for i, line in enumerate(lines):
        lead = (" " * indent + prefix) if i == 0 else " " * hang
        printer.text(lead)
        for frag in line:
            printer.set(bold=frag.bold, underline=2 if (frag.italic or frag.underline) else 0)
            printer.text(frag.text)
        printer.text("\n")
    printer.set(bold=False, underline=0)


def _render_table(printer: Escpos, block: TableBlock, width: int) -> None:
    table_layout = layout_table(block, width)
    printer.set(align="left", bold=False, underline=0, normal_textsize=True)
    for line in render_table_rows(table_layout):
        for frag in line:
            printer.set(bold=frag.bold, underline=2 if (frag.italic or frag.underline) else 0)
            printer.text(frag.text)
        printer.text("\n")
    printer.set(bold=False, underline=0)


def _render_thematic_break(printer: Escpos, width: int) -> None:
    printer.set(align="left", bold=False, underline=0, normal_textsize=True)
    printer.text("-" * width + "\n")


def _render_image(printer: Escpos, block: ImageBlock) -> None:
    printer.set(align="center", bold=False, underline=0, normal_textsize=True)
    printer.image(block.image)
    printer.set(align="left", normal_textsize=True)


def _render_timestamp(printer: Escpos) -> None:
    """Print the current date/time, right-aligned, in the bottom-right corner."""

    printer.set(align="left", bold=False, underline=0, normal_textsize=True)
    printer.text("\n")
    printer.set(align="right", bold=False, underline=0, normal_textsize=True)
    printer.text(datetime.now().strftime("%d.%m.%Y %H:%M") + "\n")
    printer.set(align="left", bold=False, underline=0, normal_textsize=True)
