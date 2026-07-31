"""Zufaelliges Tier zum Ausmalen aus assets/images/animals.png.

Die Bilddatei enthaelt mehrere Tiermotive, durch ein rotes Raster getrennt
(siehe app.presets.grid_images). Bei jedem Druck wird ein zufaelliges Motiv
ausgeschnitten, das Raster entfernt und als PNG zurueckgegeben.
"""

from __future__ import annotations

from app.presets.grid_images import random_cell_png


def generate_image() -> bytes:
    """Gibt die PNG-Bytes eines zufaelligen Tiermotivs zurueck."""

    return random_cell_png("animals.png")
