"""Shared text-layout helpers (word wrap, table column layout, padding).

Used by both the ESC/POS renderer and the PNG preview renderer so that the
preview matches the printed output.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.rendering.document import Alignment, TableBlock, TextRun

_TOKEN_RE = re.compile(r"\S+|\s+")

MIN_COLUMN_WIDTH = 3
COLUMN_SEPARATOR = " "

# Indentation (in characters) added per nesting level for list items.
LIST_INDENT = 2


@dataclass
class TextFragment:
    """A piece of text with uniform styling, belonging to one wrapped line."""

    text: str
    bold: bool = False
    italic: bool = False
    underline: bool = False


def runs_text_len(runs: list[TextRun]) -> int:
    """Total character length of a run list (ignoring forced line breaks)."""

    return sum(len(r.text) for r in runs if r.text != "\n")


def wrap_runs(runs: list[TextRun], width: int) -> list[list[TextFragment]]:
    """Word-wrap a list of styled text runs to ``width`` characters.

    Forced line breaks (``TextRun(text="\\n")``, produced by markdown hard
    breaks) always start a new line. Returns at least one (possibly empty)
    line.
    """

    width = max(width, 1)
    lines: list[list[TextFragment]] = []
    current: list[TextFragment] = []
    current_len = 0

    def flush() -> None:
        nonlocal current, current_len
        lines.append(current)
        current = []
        current_len = 0

    def append(text: str, style: TextRun) -> None:
        nonlocal current, current_len
        if not text:
            return
        if (
            current
            and current[-1].bold == style.bold
            and current[-1].italic == style.italic
            and current[-1].underline == style.underline
        ):
            current[-1] = TextFragment(
                text=current[-1].text + text,
                bold=style.bold,
                italic=style.italic,
                underline=style.underline,
            )
        else:
            current.append(
                TextFragment(text=text, bold=style.bold, italic=style.italic, underline=style.underline)
            )
        current_len += len(text)

    for run in runs:
        if run.text == "\n":
            flush()
            continue

        for token in _TOKEN_RE.findall(run.text):
            if token.isspace():
                if current_len == 0:
                    continue  # drop leading whitespace on a fresh line
                if current_len + 1 <= width:
                    append(" ", run)
                else:
                    flush()
                continue

            word = token
            while word:
                remaining = width - current_len
                if remaining <= 0:
                    flush()
                    remaining = width
                if len(word) <= remaining:
                    append(word, run)
                    word = ""
                elif current_len == 0:
                    # word longer than the whole line: hard-split it
                    append(word[:remaining], run)
                    word = word[remaining:]
                    flush()
                else:
                    flush()

    flush()
    return lines


def pad_fragments(fragments: list[TextFragment], width: int, align: Alignment = "left") -> list[TextFragment]:
    """Pad a wrapped line with plain-text spaces to exactly ``width`` characters."""

    text_len = sum(len(f.text) for f in fragments)
    pad = max(width - text_len, 0)
    if pad == 0:
        return fragments

    if align == "right":
        return [TextFragment(text=" " * pad), *fragments]
    if align == "center":
        left = pad // 2
        right = pad - left
        result: list[TextFragment] = []
        if left:
            result.append(TextFragment(text=" " * left))
        result.extend(fragments)
        if right:
            result.append(TextFragment(text=" " * right))
        return result

    return [*fragments, TextFragment(text=" " * pad)]


def fragments_to_text(fragments: list[TextFragment]) -> str:
    return "".join(f.text for f in fragments)


# ---------------------------------------------------------------------------
# Table layout
# ---------------------------------------------------------------------------


@dataclass
class TableLayout:
    widths: list[int]
    alignments: list[Alignment]
    header_lines: list[list[list[TextFragment]]]
    row_lines: list[list[list[list[TextFragment]]]]


def _column_widths(table: TableBlock, total_width: int) -> list[int]:
    num_cols = len(table.alignments)
    if num_cols == 0:
        return []

    sep_total = len(COLUMN_SEPARATOR) * (num_cols - 1)
    available = max(total_width - sep_total, num_cols * MIN_COLUMN_WIDTH)

    natural: list[int] = []
    for col in range(num_cols):
        cells = [table.header[col]] if col < len(table.header) else []
        cells += [row[col] for row in table.rows if col < len(row)]
        max_len = max((runs_text_len(c) for c in cells), default=0)
        natural.append(max(max_len, MIN_COLUMN_WIDTH))

    total_natural = sum(natural)
    if total_natural <= available:
        return natural

    scale = available / total_natural
    widths = [max(MIN_COLUMN_WIDTH, int(n * scale)) for n in natural]

    # Distribute any rounding remainder so the columns add up exactly.
    diff = available - sum(widths)
    i = 0
    while diff != 0 and i < 10_000:
        idx = i % len(widths)
        if diff > 0:
            widths[idx] += 1
            diff -= 1
        elif widths[idx] > MIN_COLUMN_WIDTH:
            widths[idx] -= 1
            diff += 1
        i += 1

    return widths


def layout_table(table: TableBlock, total_width: int) -> TableLayout:
    widths = _column_widths(table, total_width)

    header_lines = [wrap_runs(cell, w) for cell, w in zip(table.header, widths)]

    row_lines: list[list[list[list[TextFragment]]]] = []
    for row in table.rows:
        cells: list[list[list[TextFragment]]] = []
        for i, w in enumerate(widths):
            cell_runs = row[i] if i < len(row) else []
            cells.append(wrap_runs(cell_runs, w))
        row_lines.append(cells)

    return TableLayout(
        widths=widths,
        alignments=list(table.alignments),
        header_lines=header_lines,
        row_lines=row_lines,
    )


def render_table_rows(layout: TableLayout) -> list[list[TextFragment]]:
    """Render a table layout into plain lines (list of fragment-lines).

    Each output line is one printable row (already padded/aligned/joined
    with column separators), reusable by both renderers.
    """

    lines: list[list[TextFragment]] = []

    def render_row(cell_lines: list[list[list[TextFragment]]]) -> None:
        n_lines = max((len(c) for c in cell_lines), default=1)
        n_lines = max(n_lines, 1)
        for line_idx in range(n_lines):
            row_fragments: list[TextFragment] = []
            for col_idx, col_lines in enumerate(cell_lines):
                cell_line = col_lines[line_idx] if line_idx < len(col_lines) else []
                padded = pad_fragments(cell_line, layout.widths[col_idx], layout.alignments[col_idx])
                if col_idx:
                    row_fragments.append(TextFragment(text=COLUMN_SEPARATOR))
                row_fragments.extend(padded)
            lines.append(row_fragments)

    if layout.header_lines:
        bold_header = [
            [[TextFragment(text=fragments_to_text(line), bold=True)] for line in col]
            for col in layout.header_lines
        ]
        render_row(bold_header)
        separator = [TextFragment(text="-" * w) for w in layout.widths]
        sep_line: list[TextFragment] = []
        for i, frag in enumerate(separator):
            if i:
                sep_line.append(TextFragment(text=COLUMN_SEPARATOR))
            sep_line.append(frag)
        lines.append(sep_line)

    for row_cells in layout.row_lines:
        render_row(row_cells)

    return lines


def list_item_prefix(item_runs_ordered: bool, index: int | None) -> str:
    """Return the textual marker prefix for a (non-checkbox) list item.

    Checkbox items (``item.checked is not None``) are rendered as a bitmap
    via :func:`app.rendering.text_image.render_checklist_item` instead and
    never go through this function.
    """

    if item_runs_ordered and index is not None:
        return f"{index}. "
    return "- "
