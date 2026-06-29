"""Icon rendering for the receipt header.

Renders either a glyph from a Font Awesome webfont (TTF/OTF) using a
name->codepoint JSON map, or a custom SVG icon from a configurable
directory. The Font Awesome assets are loaded from a configurable location
(see ``backend/assets/fontawesome/README.md``) and are not bundled with the
application (licensing/binary size); custom SVG icons are loaded from
``backend/assets/icons/`` (see ``backend/assets/icons/README.md``). If any of
these are missing, unreadable, or the requested icon is unknown, rendering
degrades gracefully to a small placeholder box so a "defekte Icon" never
fails a print job.
"""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from io import BytesIO
from pathlib import Path

import resvg_py
from PIL import Image, ImageDraw, ImageFont

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)

CUSTOM_ICON_PREFIX = "svg-"


class IconRenderer:
    def __init__(self, settings: Settings):
        self._font_path = Path(settings.fontawesome_font_path)
        self._map_path = Path(settings.fontawesome_map_path)
        self._codepoints: dict[str, str] = {}
        self._font_available = False

        if self._font_path.is_file() and self._map_path.is_file():
            try:
                self._codepoints = self._load_map()
                self._font_available = True
            except Exception:
                logger.warning(
                    "Could not load FontAwesome icon map %s - icons will use the placeholder",
                    self._map_path,
                    exc_info=True,
                )
        else:
            logger.info(
                "FontAwesome assets not found (%s / %s) - icons will use the placeholder",
                self._font_path,
                self._map_path,
            )

        self._custom_icons = self._load_custom_icons(Path(settings.custom_icons_dir))

    def _load_map(self) -> dict[str, str]:
        data = json.loads(self._map_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("icon map must be a JSON object of name -> codepoint")
        return {str(k): str(v) for k, v in data.items()}

    def _load_custom_icons(self, icons_dir: Path) -> dict[str, Path]:
        if not icons_dir.is_dir():
            logger.info("Custom icon directory not found (%s) - no custom icons available", icons_dir)
            return {}

        return {f"{CUSTOM_ICON_PREFIX}{path.stem}": path for path in sorted(icons_dir.glob("*.svg"))}

    def available_icons(self) -> list[str]:
        """Return the sorted list of icon names known to the loaded icon map
        and custom icon directory.

        Empty if neither the icon map nor any custom icons could be loaded
        (placeholder-only mode).
        """

        return sorted({*self._codepoints, *self._custom_icons})

    def custom_icon_path(self, icon_name: str) -> Path | None:
        """Return the SVG file backing ``icon_name``, or ``None`` if
        ``icon_name`` is not a known custom icon."""

        return self._custom_icons.get(icon_name)

    def render(self, icon_name: str, size_px: int) -> Image.Image | None:
        """Render ``icon_name`` onto a ``size_px`` x ``size_px`` grayscale image.

        Returns ``None`` only if ``icon_name`` is empty - any other failure
        falls back to a placeholder glyph so the job can still print.
        """

        icon_name = (icon_name or "").strip()
        if not icon_name:
            return None

        if icon_name in self._custom_icons:
            try:
                return self._render_svg(self._custom_icons[icon_name], size_px)
            except Exception:
                logger.warning("Failed to render custom icon %r, using placeholder", icon_name, exc_info=True)

        if self._font_available and icon_name in self._codepoints:
            try:
                return self._render_glyph(self._codepoints[icon_name], size_px)
            except Exception:
                logger.warning("Failed to render icon %r from font, using placeholder", icon_name, exc_info=True)

        return self._render_placeholder(icon_name, size_px)

    def _render_glyph(self, codepoint: str, size_px: int) -> Image.Image:
        glyph = chr(int(codepoint, 16))
        font = ImageFont.truetype(str(self._font_path), size=int(size_px * 0.8))

        image = Image.new("L", (size_px, size_px), color=255)
        draw = ImageDraw.Draw(image)
        bbox = draw.textbbox((0, 0), glyph, font=font)
        w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        x = (size_px - w) / 2 - bbox[0]
        y = (size_px - h) / 2 - bbox[1]
        draw.text((x, y), glyph, font=font, fill=0)
        return image

    def _render_svg(self, svg_path: Path, size_px: int) -> Image.Image:
        png_bytes = resvg_py.svg_to_bytes(svg_path=str(svg_path), width=size_px, height=size_px)
        rendered = Image.open(BytesIO(png_bytes)).convert("RGBA")

        # Composite onto white first - SVGs are typically drawn on a
        # transparent background, which would otherwise convert to black.
        image = Image.new("RGBA", rendered.size, (255, 255, 255, 255))
        image.alpha_composite(rendered)
        image = image.convert("L")

        if image.size != (size_px, size_px):
            image = image.resize((size_px, size_px))
        return image

    def _render_placeholder(self, icon_name: str, size_px: int) -> Image.Image:
        """Draw a bordered box with a short label, used when the real
        FontAwesome font/codepoint is unavailable."""

        label = icon_name.removeprefix("fa-").replace("-", " ").strip()
        label = (label[:10] or "icon").upper()

        image = Image.new("L", (size_px, size_px), color=255)
        draw = ImageDraw.Draw(image)
        border = max(size_px // 32, 1)
        draw.rectangle([border, border, size_px - 1 - border, size_px - 1 - border], outline=0, width=border)

        font = ImageFont.load_default()
        bbox = draw.textbbox((0, 0), label, font=font)
        w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        if w > size_px and len(label) > 4:
            label = label[:4]
            bbox = draw.textbbox((0, 0), label, font=font)
            w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        x = (size_px - w) / 2 - bbox[0]
        y = (size_px - h) / 2 - bbox[1]
        draw.text((x, y), label, font=font, fill=0)
        return image


@lru_cache
def get_icon_renderer() -> IconRenderer:
    return IconRenderer(get_settings())


def reset_icon_renderer() -> None:
    get_icon_renderer.cache_clear()


def render_icon_canvas(icon_name: str | None, width_px: int, icon_size_px: int | None = None) -> Image.Image | None:
    """Render ``icon_name`` centered on a ``width_px``-wide white canvas.

    The result can be passed directly to ``printer.image()`` (full receipt
    width, icon centered without relying on printer profile settings) or
    pasted into the PNG preview. Returns ``None`` if no icon was requested.
    """

    icon_name = (icon_name or "").strip()
    if not icon_name:
        return None

    size = icon_size_px or max(min(width_px // 4, 200), 32)
    icon = get_icon_renderer().render(icon_name, size)
    if icon is None:
        return None

    canvas = Image.new("L", (width_px, size), color=255)
    x = (width_px - size) // 2
    canvas.paste(icon, (x, 0))
    return canvas.convert("1")
