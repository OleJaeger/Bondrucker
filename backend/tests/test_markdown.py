"""Markdown -> IR conversion, including the documented degradation rules."""

from __future__ import annotations

import pytest

from app.exceptions import InvalidMarkdownError
from app.rendering.document import Heading, ListItem, Paragraph, TableBlock, TextRun, ThematicBreak
from app.rendering.markdown import parse_markdown


def test_empty_markdown_returns_no_blocks():
    assert parse_markdown("") == []


def test_too_long_markdown_raises():
    with pytest.raises(InvalidMarkdownError):
        parse_markdown("x" * 50_001)


def test_headings():
    blocks = parse_markdown("# Titel\n\n## Untertitel\n")
    assert isinstance(blocks[0], Heading)
    assert blocks[0].level == 1
    assert blocks[0].runs == [TextRun(text="Titel")]
    assert isinstance(blocks[1], Heading)
    assert blocks[1].level == 2


def test_bold_and_italic_runs():
    blocks = parse_markdown("Hallo **fett** und *kursiv* Text")
    runs = blocks[0].runs
    styles = {r.text: (r.bold, r.italic) for r in runs}
    assert styles["fett"] == (True, False)
    assert styles["kursiv"] == (False, True)


def test_unordered_list():
    blocks = parse_markdown("- Eins\n- Zwei\n")
    assert all(isinstance(b, ListItem) and not b.ordered for b in blocks)
    assert [b.runs[0].text for b in blocks] == ["Eins", "Zwei"]


def test_ordered_list_indices_respect_start_value():
    blocks = parse_markdown("3. Drei\n4. Vier\n")
    assert [(b.ordered, b.index) for b in blocks] == [(True, 3), (True, 4)]


def test_task_list_checkboxes():
    blocks = parse_markdown("- [ ] Milch\n- [x] Brot\n")
    assert [b.checked for b in blocks] == [False, True]
    assert [b.runs[0].text for b in blocks] == ["Milch", "Brot"]


def test_nested_list_increments_level():
    blocks = parse_markdown("- Eins\n  - Eins.Eins\n- Zwei\n")
    assert [b.level for b in blocks] == [0, 1, 0]


def test_table_with_alignment():
    md = "| A | B |\n| :-- | --: |\n| 1 | 2 |\n"
    table = parse_markdown(md)[0]
    assert isinstance(table, TableBlock)
    assert [cell[0].text for cell in table.header] == ["A", "B"]
    assert table.alignments == ["left", "right"]
    assert table.rows[0][0][0].text == "1"
    assert table.rows[0][1][0].text == "2"


def test_link_degrades_to_text_only():
    blocks = parse_markdown("[Klick hier](https://example.com)")
    assert "".join(r.text for r in blocks[0].runs) == "Klick hier"


def test_image_with_alt_becomes_placeholder():
    blocks = parse_markdown("![Logo](logo.png)")
    assert "".join(r.text for r in blocks[0].runs) == "[Logo]"


def test_image_without_alt_is_dropped():
    blocks = parse_markdown("![](logo.png)")
    assert blocks[0].runs == []


def test_strikethrough_renders_as_plain_text():
    blocks = parse_markdown("~~durchgestrichen~~")
    run = blocks[0].runs[0]
    assert run.text == "durchgestrichen"
    assert not run.bold and not run.italic and not run.underline


def test_inline_code_renders_as_plain_text():
    blocks = parse_markdown("Das ist `code`.")
    texts = [r.text for r in blocks[0].runs]
    assert texts == ["Das ist ", "code", "."]


def test_code_block_becomes_multiline_paragraph():
    para = parse_markdown("```\nzeile1\nzeile2\n```\n")[0]
    assert isinstance(para, Paragraph)
    assert [r.text for r in para.runs] == ["zeile1", "\n", "zeile2"]


def test_block_quote_prefixes_lines():
    para = parse_markdown("> Zitat\n")[0]
    assert isinstance(para, Paragraph)
    assert para.runs[0].text == "> "
    assert para.runs[1].text == "Zitat"


def test_thematic_break():
    assert isinstance(parse_markdown("---\n")[0], ThematicBreak)


def test_hard_line_break_within_paragraph():
    para = parse_markdown("Zeile1  \nZeile2\n")[0]
    assert [r.text for r in para.runs] == ["Zeile1", "\n", "Zeile2"]


def test_soft_line_break_within_paragraph_becomes_forced_line_break():
    # A plain single newline (no trailing spaces) - as produced by pressing
    # Enter in a <textarea> - must also force a line break, not collapse
    # into a space.
    para = parse_markdown("Zeile1\nZeile2\n")[0]
    assert [r.text for r in para.runs] == ["Zeile1", "\n", "Zeile2"]
