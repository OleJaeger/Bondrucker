"""Word wrap, padding and table layout helpers shared by both renderers."""

from __future__ import annotations

from app.rendering.document import TableBlock, TextRun
from app.rendering.layout import (
    TextFragment,
    fragments_to_text,
    layout_table,
    list_item_prefix,
    pad_fragments,
    render_table_rows,
    wrap_runs,
)


def test_wrap_runs_basic_word_wrap():
    lines = wrap_runs([TextRun(text="Hello world foo bar")], 11)
    assert [fragments_to_text(line) for line in lines] == ["Hello world", "foo bar"]


def test_wrap_runs_forced_line_break():
    runs = [TextRun(text="foo"), TextRun(text="\n"), TextRun(text="bar")]
    lines = wrap_runs(runs, 10)
    assert [fragments_to_text(line) for line in lines] == ["foo", "bar"]


def test_wrap_runs_hard_splits_overlong_words():
    lines = wrap_runs([TextRun(text="Supercalifragilisticexpialidocious")], 10)
    texts = [fragments_to_text(line) for line in lines]
    assert all(len(t) <= 10 for t in texts)
    assert "".join(texts) == "Supercalifragilisticexpialidocious"


def test_wrap_runs_merges_adjacent_fragments_with_same_style():
    runs = [TextRun(text="foo", bold=True), TextRun(text=" bar", bold=True)]
    lines = wrap_runs(runs, 20)
    assert lines == [[TextFragment(text="foo bar", bold=True)]]


def test_wrap_runs_returns_one_empty_line_for_empty_input():
    assert wrap_runs([], 10) == [[]]


def test_pad_fragments_left_align_pads_right():
    padded = pad_fragments([TextFragment(text="ab")], 5, "left")
    assert fragments_to_text(padded) == "ab   "


def test_pad_fragments_right_align_pads_left():
    padded = pad_fragments([TextFragment(text="ab")], 5, "right")
    assert fragments_to_text(padded) == "   ab"


def test_pad_fragments_center_align_splits_padding():
    padded = pad_fragments([TextFragment(text="ab")], 5, "center")
    assert fragments_to_text(padded) == " ab  "


def test_pad_fragments_noop_when_already_wide_enough():
    frags = [TextFragment(text="abcde")]
    assert pad_fragments(frags, 5, "left") is frags


def _simple_table() -> TableBlock:
    return TableBlock(
        header=[[TextRun(text="A")], [TextRun(text="B")]],
        rows=[[[TextRun(text="1")], [TextRun(text="2")]]],
        alignments=["left", "right"],
    )


def test_layout_table_uses_natural_widths_when_they_fit():
    layout = layout_table(_simple_table(), 48)
    assert layout.widths == [3, 3]


def test_layout_table_shrinks_proportionally_when_too_wide():
    table = TableBlock(
        header=[[TextRun(text="A" * 20)], [TextRun(text="B" * 20)], [TextRun(text="C" * 20)]],
        rows=[],
        alignments=["left", "left", "left"],
    )
    layout = layout_table(table, 20)
    # 2 separators between 3 columns -> total printable width must be 20.
    assert sum(layout.widths) + 2 == 20
    assert all(w >= 3 for w in layout.widths)


def test_render_table_rows_bolds_header_and_adds_separator():
    layout = layout_table(_simple_table(), 48)
    rows = render_table_rows(layout)

    header_line, separator_line, data_line = rows
    assert fragments_to_text(header_line) == "A     B"
    assert all(f.bold for f in header_line if f.text.strip())
    assert fragments_to_text(separator_line) == "--- ---"
    assert fragments_to_text(data_line) == "1     2"


def test_list_item_prefix_variants():
    assert list_item_prefix(True, 5) == "5. "
    assert list_item_prefix(False, None) == "- "
