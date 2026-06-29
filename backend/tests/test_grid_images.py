"""Tests for app.presets.grid_images (red-grid cell detection/cropping)."""

from __future__ import annotations

from io import BytesIO

import pytest
from PIL import Image, ImageDraw

from app.exceptions import PresetScriptError
from app.presets import grid_images


def _two_cell_sheet() -> Image.Image:
    """A 100x60 RGBA sheet: two 40x50 cells separated/framed by red lines,
    each with a black motif, on an otherwise transparent background."""

    image = Image.new("RGBA", (100, 60), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    red = (255, 0, 0, 255)
    draw.rectangle([0, 0, 99, 4], fill=red)  # top border
    draw.rectangle([0, 55, 99, 59], fill=red)  # bottom border
    draw.rectangle([0, 0, 4, 59], fill=red)  # left border
    draw.rectangle([95, 0, 99, 59], fill=red)  # right border
    draw.rectangle([47, 0, 52, 59], fill=red)  # vertical divider

    draw.ellipse([15, 20, 35, 40], fill=(0, 0, 0, 255))  # left motif
    draw.ellipse([65, 20, 85, 40], fill=(0, 0, 0, 255))  # right motif

    return image


def _no_grid_sheet() -> Image.Image:
    image = Image.new("RGBA", (40, 30), (0, 0, 0, 0))
    ImageDraw.Draw(image).ellipse([5, 5, 35, 25], fill=(0, 0, 0, 255))
    return image


def _load_png(data: bytes) -> Image.Image:
    return Image.open(BytesIO(data))


def test_find_cells_detects_both_cells_and_ignores_the_red_grid():
    cells = grid_images._find_cells(_two_cell_sheet())

    assert len(cells) == 2
    xs = sorted(bbox[0] for bbox in cells)
    assert xs == [5, 53]
    for bbox in cells:
        assert bbox[1] == 5
        assert bbox[3] == 55


def test_find_cells_returns_empty_for_sheet_without_red_grid():
    assert grid_images._find_cells(_no_grid_sheet()) == []


def test_clean_cell_removes_red_and_flattens_transparency():
    image = _two_cell_sheet()
    bbox = grid_images._find_cells(image)[0]

    cleaned = grid_images._clean_cell(image, bbox)

    assert cleaned.mode == "RGB"
    colors = {color for _count, color in cleaned.getcolors()}
    assert (255, 0, 0) not in colors
    assert (0, 0, 0) in colors  # the motif survives
    assert (255, 255, 255) in colors  # transparent background -> white


def test_random_cell_png_returns_one_of_the_two_motifs(monkeypatch, tmp_path):
    sheet_path = tmp_path / "sheet.png"
    _two_cell_sheet().save(sheet_path)
    monkeypatch.setattr(grid_images, "get_settings", lambda: type("S", (), {"images_dir": str(tmp_path)})())

    data = grid_images.random_cell_png("sheet.png")
    result = _load_png(data).convert("RGB")

    assert result.size == (42, 50)
    colors = {color for _count, color in result.getcolors()}
    assert (255, 0, 0) not in colors
    assert (0, 0, 0) in colors


def test_random_cell_png_falls_back_to_whole_image_without_grid(monkeypatch, tmp_path):
    sheet_path = tmp_path / "plain.png"
    _no_grid_sheet().save(sheet_path)
    monkeypatch.setattr(grid_images, "get_settings", lambda: type("S", (), {"images_dir": str(tmp_path)})())

    data = grid_images.random_cell_png("plain.png")
    result = _load_png(data).convert("RGB")

    assert result.size == (40, 30)
    assert (0, 0, 0) in {color for _count, color in result.getcolors()}


def test_random_cell_png_missing_file_raises(settings_env):
    with pytest.raises(PresetScriptError):
        grid_images.random_cell_png("does-not-exist.png")


def test_random_cell_png_invalid_image_raises(tmp_path, monkeypatch):
    bad_path = tmp_path / "broken.png"
    bad_path.write_text("not an image")
    monkeypatch.setattr(grid_images, "get_settings", lambda: type("S", (), {"images_dir": str(tmp_path)})())

    with pytest.raises(PresetScriptError):
        grid_images.random_cell_png("broken.png")
