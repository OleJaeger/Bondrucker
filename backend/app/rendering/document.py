"""Printer-agnostic intermediate representation (IR) of a rendered document.

Both the ESC/POS renderer and the PNG preview renderer operate on this same
IR, which guarantees that the preview matches what is actually printed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Union

from PIL import Image

from app.templates.schema import TemplateConfig

Alignment = Literal["left", "center", "right"]


@dataclass
class TextRun:
    """A run of text with uniform inline styling."""

    text: str
    bold: bool = False
    italic: bool = False
    underline: bool = False


@dataclass
class Heading:
    level: int
    runs: list[TextRun]


@dataclass
class Paragraph:
    runs: list[TextRun]


@dataclass
class ListItem:
    runs: list[TextRun]
    ordered: bool = False
    index: int | None = None
    # None = plain list item, True/False = checkbox state (task list)
    checked: bool | None = None
    level: int = 0


@dataclass
class TableBlock:
    header: list[list[TextRun]]
    rows: list[list[list[TextRun]]]
    alignments: list[Alignment]


@dataclass
class ThematicBreak:
    pass


@dataclass
class ImageBlock:
    """An uploaded image or generated QR code, rendered as a single raster
    image (already centered, mode "1")."""

    image: Image.Image


Block = Union[Heading, Paragraph, ListItem, TableBlock, ThematicBreak, ImageBlock]


@dataclass
class Document:
    """A fully resolved print job ready for rendering."""

    title: str
    icon: str | None
    blocks: list[Block] = field(default_factory=list)
    template: TemplateConfig | None = None
    # Whether to print the current date/time in the bottom-right corner.
    show_timestamp: bool = True
