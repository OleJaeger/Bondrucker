"""Pydantic schema for print template configuration files (YAML)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

Alignment = Literal["left", "center", "right"]


class TextStyle(BaseModel):
    """ESC/POS text style applied to a section of the document."""

    align: Alignment = "left"
    bold: bool = False
    underline: bool = False
    double_width: bool = False
    double_height: bool = False


class LayoutConfig(BaseModel):
    """Physical layout parameters for a template."""

    # Overrides the global PRINTER_WIDTH_CHARS for this template, if set.
    width_chars: int | None = Field(default=None, gt=0, le=128)
    # Whether to send a paper-cut command after the job.
    cut: bool = True
    # Blank lines fed after the content, before the cut.
    feed_lines: int = Field(default=3, ge=0, le=20)


class DefaultFormatting(BaseModel):
    """Default formatting for the title and body of the document."""

    title: TextStyle = Field(
        default_factory=lambda: TextStyle(
            align="center", bold=True, double_width=True, double_height=True
        )
    )
    body: TextStyle = Field(default_factory=TextStyle)


class TemplateFields(BaseModel):
    """Which input fields the "create job" form exposes for this template.

    Used by templates with a fixed layout (e.g. "Gemaelde") that do not
    accept free-form content from the user.
    """

    markdown: bool = True
    attachment: bool = True


class TemplateConfig(BaseModel):
    """A fully validated template configuration.

    ``key`` is derived from the YAML filename (without extension) and is the
    identifier used in the ``template`` field of a print job.
    """

    key: str
    name: str
    type: str
    layout: LayoutConfig = Field(default_factory=LayoutConfig)
    default_formatting: DefaultFormatting = Field(default_factory=DefaultFormatting)
    # Optional default icon name - either Font Awesome (e.g.
    # "fa-cart-shopping") or a custom SVG icon (e.g. "svg-logo") - used when
    # a job does not specify its own ``icon``.
    icon: str | None = None
    fields: TemplateFields = Field(default_factory=TemplateFields)
    # Markdown content used to pre-fill the job when ``fields.markdown`` is
    # False (the user cannot edit it themselves).
    default_markdown: str | None = None

    @field_validator("type", "name")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("must not be empty")
        return value
