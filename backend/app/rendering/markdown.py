"""Markdown -> :mod:`app.rendering.document` IR conversion.

Uses ``mistune`` in AST mode. Elements without a sensible ESC/POS
representation are degraded according to the table in
``docs/markdown-mapping.md``:

* links            -> link text only, URL dropped
* images           -> ``[alt text]`` placeholder (or dropped if no alt text)
* strikethrough    -> rendered as plain text
* inline code      -> rendered as plain text
* code blocks      -> rendered as a left-aligned plain-text paragraph
* block quotes     -> each contained line prefixed with "> "
* unknown elements -> children are flattened into the surrounding content
"""

from __future__ import annotations

from typing import Any

import mistune

from app.exceptions import InvalidMarkdownError
from app.rendering.document import (
    Block,
    Heading,
    ListItem,
    Paragraph,
    TableBlock,
    TextRun,
    ThematicBreak,
)

_parser = mistune.create_markdown(
    renderer=None, plugins=["table", "task_lists", "strikethrough"]
)

# Hard guard against pathological input (e.g. deeply nested lists) causing
# excessive recursion / render time.
_MAX_MARKDOWN_LENGTH = 50_000


def parse_markdown(text: str) -> list[Block]:
    """Parse a markdown string into a list of IR blocks.

    Raises :class:`InvalidMarkdownError` if the input cannot be processed.
    """

    if len(text) > _MAX_MARKDOWN_LENGTH:
        raise InvalidMarkdownError(
            f"Markdown ist zu lang ({len(text)} Zeichen, Limit "
            f"{_MAX_MARKDOWN_LENGTH})"
        )

    try:
        tokens = _parser(text)
    except Exception as exc:  # mistune raises a variety of exception types
        raise InvalidMarkdownError(f"Markdown konnte nicht verarbeitet werden: {exc}") from exc

    if not isinstance(tokens, list):
        raise InvalidMarkdownError("Markdown lieferte ein unerwartetes Ergebnis")

    try:
        return _convert_blocks(tokens)
    except InvalidMarkdownError:
        raise
    except Exception as exc:
        raise InvalidMarkdownError(f"Markdown konnte nicht gerendert werden: {exc}") from exc


# ---------------------------------------------------------------------------
# Block-level conversion
# ---------------------------------------------------------------------------


def _convert_blocks(tokens: list[dict[str, Any]]) -> list[Block]:
    blocks: list[Block] = []
    for token in tokens:
        ttype = token.get("type")

        if ttype in ("heading",):
            level = int(token.get("attrs", {}).get("level", 1))
            blocks.append(Heading(level=level, runs=_convert_inline(token.get("children", []))))

        elif ttype in ("paragraph", "block_text"):
            blocks.append(Paragraph(runs=_convert_inline(token.get("children", []))))

        elif ttype == "thematic_break":
            blocks.append(ThematicBreak())

        elif ttype == "block_code":
            blocks.append(_convert_code_block(token))

        elif ttype == "block_quote":
            blocks.extend(_convert_block_quote(token.get("children", [])))

        elif ttype == "list":
            ordered = bool(token.get("attrs", {}).get("ordered", False))
            blocks.extend(_convert_list(token, ordered=ordered, level=0))

        elif ttype == "table":
            blocks.append(_convert_table(token))

        elif ttype == "blank_line":
            continue

        else:
            # Unknown block type: flatten any children, otherwise drop.
            children = token.get("children")
            if children:
                blocks.extend(_convert_blocks(children))

    return blocks


def _convert_code_block(token: dict[str, Any]) -> Paragraph:
    raw = token.get("raw", "")
    lines = raw.rstrip("\n").split("\n")
    runs: list[TextRun] = []
    for i, line in enumerate(lines):
        if i:
            runs.append(TextRun(text="\n"))
        if line:
            runs.append(TextRun(text=line))
    return Paragraph(runs=runs)


def _convert_block_quote(children: list[dict[str, Any]]) -> list[Block]:
    inner = _convert_blocks(children)
    prefixed: list[Block] = []
    for block in inner:
        if isinstance(block, (Paragraph, Heading, ListItem)):
            block.runs = [TextRun(text="> ")] + block.runs
        prefixed.append(block)
    return prefixed


def _convert_list(token: dict[str, Any], *, ordered: bool, level: int) -> list[Block]:
    items: list[Block] = []
    start = token.get("attrs", {}).get("start", 1)
    index = start if ordered else None

    for item in token.get("children", []):
        checked: bool | None = None
        if item.get("type") == "task_list_item":
            checked = bool(item.get("attrs", {}).get("checked", False))

        runs: list[TextRun] = []
        nested: list[Block] = []

        for child in item.get("children", []):
            ctype = child.get("type")
            if ctype in ("block_text", "paragraph"):
                runs.extend(_convert_inline(child.get("children", [])))
            elif ctype == "list":
                child_ordered = bool(child.get("attrs", {}).get("ordered", False))
                nested.extend(_convert_list(child, ordered=child_ordered, level=level + 1))
            else:
                nested.extend(_convert_blocks([child]))

        items.append(
            ListItem(runs=runs, ordered=ordered, index=index, checked=checked, level=level)
        )
        items.extend(nested)

        if ordered and index is not None:
            index += 1

    return items


def _convert_table(token: dict[str, Any]) -> TableBlock:
    head_token = next(
        (c for c in token.get("children", []) if c.get("type") == "table_head"), None
    )
    body_token = next(
        (c for c in token.get("children", []) if c.get("type") == "table_body"), None
    )

    header: list[list[TextRun]] = []
    alignments: list[str] = []
    if head_token is not None:
        for cell in head_token.get("children", []):
            header.append(_convert_inline(cell.get("children", [])))
            align = cell.get("attrs", {}).get("align") or "left"
            alignments.append(align)

    rows: list[list[list[TextRun]]] = []
    if body_token is not None:
        for row in body_token.get("children", []):
            rows.append([_convert_inline(cell.get("children", [])) for cell in row.get("children", [])])

    return TableBlock(header=header, rows=rows, alignments=alignments)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Inline conversion
# ---------------------------------------------------------------------------


def _convert_inline(
    children: list[dict[str, Any]],
    *,
    bold: bool = False,
    italic: bool = False,
    underline: bool = False,
) -> list[TextRun]:
    runs: list[TextRun] = []

    for token in children:
        ttype = token.get("type")

        if ttype == "text":
            text = token.get("raw", "")
            if text:
                runs.append(TextRun(text=text, bold=bold, italic=italic, underline=underline))

        elif ttype == "strong":
            runs.extend(
                _convert_inline(token.get("children", []), bold=True, italic=italic, underline=underline)
            )

        elif ttype == "emphasis":
            runs.extend(
                _convert_inline(token.get("children", []), bold=bold, italic=True, underline=underline)
            )

        elif ttype in ("codespan", "code"):
            text = token.get("raw", "")
            if text:
                runs.append(TextRun(text=text, bold=bold, italic=italic, underline=underline))

        elif ttype == "strikethrough":
            # Degrade: no strikethrough on ESC/POS, render as plain text.
            runs.extend(_convert_inline(token.get("children", []), bold=bold, italic=italic, underline=underline))

        elif ttype == "linebreak":
            runs.append(TextRun(text="\n"))

        elif ttype == "softbreak":
            # A single newline in the source is treated as a forced line
            # break (not collapsed to a space), so line breaks the user
            # types in the textarea are preserved in the markdown and on
            # the printout.
            runs.append(TextRun(text="\n"))

        elif ttype == "link":
            # Degrade: keep the link text, drop the URL.
            runs.extend(_convert_inline(token.get("children", []), bold=bold, italic=italic, underline=underline))

        elif ttype == "image":
            alt = _plain_text(token.get("children", [])).strip()
            if alt:
                runs.append(TextRun(text=f"[{alt}]", bold=bold, italic=italic, underline=underline))

        else:
            children2 = token.get("children")
            if children2:
                runs.extend(_convert_inline(children2, bold=bold, italic=italic, underline=underline))
            elif "raw" in token:
                runs.append(TextRun(text=token["raw"], bold=bold, italic=italic, underline=underline))

    return runs


def _plain_text(children: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for token in children:
        if "raw" in token:
            parts.append(token["raw"])
        elif "children" in token:
            parts.append(_plain_text(token["children"]))
    return "".join(parts)
