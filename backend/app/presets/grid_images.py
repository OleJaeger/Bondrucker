"""Random crops from "motif sheet" images for preset image scripts.

A motif sheet is a single PNG in ``settings.images_dir`` containing several
individual motifs (e.g. animals to color in) separated by a red grid. The
red lines exist only to mark the cell boundaries for this module - they are
detected, used to crop out one random cell, and then removed (painted
white) so only the motif itself ends up on the printout. A sheet without any
red grid is treated as a single motif and printed as a whole (flattened onto
a white background).

This is what makes ``settings.images_dir`` extensible: dropping in a new
sheet (with or without a red grid) needs no code changes, only a script like
``app.presets.scripts.random_animal`` that points ``random_cell_png()`` at
the new file.
"""

from __future__ import annotations

import random
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw

from app.config import get_settings
from app.exceptions import PresetScriptError

# Thresholds for "this pixel is part of a red grid line" - generous enough
# to catch anti-aliased edges without flagging skin-tone/orange motif lines.
_RED_MIN = 150
_GREEN_MAX = 120
_BLUE_MAX = 120
_ALPHA_MIN = 80

# After cropping, pixels still noticeably more red than green/blue (the
# anti-aliased fringe right next to a removed grid line) are painted white
# too.
_RED_FRINGE_DELTA = 25

# Connected-component candidates smaller than this are ignored as noise
# (e.g. an isolated anti-aliased speck), and a candidate covering most of
# the image means no grid was found at all (the whole image is one "cell").
_MIN_CELL_AREA_PX = 2000
_MAX_CELL_AREA_RATIO = 0.95

# Hard cap on detected cells, so a pathological image can't spin the
# flood-fill loop forever.
_MAX_CELLS = 64


def random_cell_png(filename: str) -> bytes:
    """Return PNG bytes for one random cell of the motif sheet ``filename``.

    ``filename`` is relative to ``settings.images_dir``. If the sheet has no
    red grid, the whole (flattened) image is returned. Raises
    :class:`PresetScriptError` if the file is missing or not a valid image.
    """

    image = _load_image(filename)
    cells = _find_cells(image)

    if cells:
        cell = _clean_cell(image, random.choice(cells))
    else:
        cell = _flatten_to_white(image)

    buffer = BytesIO()
    cell.save(buffer, format="PNG")
    return buffer.getvalue()


def _load_image(filename: str) -> Image.Image:
    path = Path(get_settings().images_dir) / filename
    try:
        image = Image.open(path)
        image.load()
    except (OSError, ValueError) as exc:
        raise PresetScriptError(f"Bilddatei {filename!r} konnte nicht geladen werden") from exc

    return image.convert("RGBA")


def _red_mask(image: Image.Image) -> Image.Image:
    red, green, blue, alpha = image.split()
    is_red = red.point(lambda v: 255 if v >= _RED_MIN else 0)
    is_dark_green = green.point(lambda v: 255 if v < _GREEN_MAX else 0)
    is_dark_blue = blue.point(lambda v: 255 if v < _BLUE_MAX else 0)
    is_opaque = alpha.point(lambda v: 255 if v >= _ALPHA_MIN else 0)
    return ImageChops.multiply(
        ImageChops.multiply(is_red, is_dark_green),
        ImageChops.multiply(is_dark_blue, is_opaque),
    )


def _find_cells(image: Image.Image) -> list[tuple[int, int, int, int]]:
    """Connected-component bounding boxes of the non-red regions of
    ``image`` - i.e. the cells enclosed by a red grid, if any.

    Pure-Pillow flood fill (no numpy/scipy dependency): repeatedly seeds a
    fill from the first remaining "open" (non-red) pixel and reads the
    bounding box of the newly filled area off the before/after diff.
    """

    open_mask = ImageChops.invert(_red_mask(image))
    width, height = open_mask.size
    max_area = width * height * _MAX_CELL_AREA_RATIO

    cells: list[tuple[int, int, int, int]] = []
    for _ in range(_MAX_CELLS):
        data = open_mask.tobytes()
        index = data.find(255)
        if index == -1:
            break

        x, y = index % width, index // width
        before = open_mask.copy()
        ImageDraw.floodfill(open_mask, (x, y), 1, thresh=0)
        bbox = ImageChops.difference(before, open_mask).getbbox()
        if bbox is None:
            continue

        area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
        if area < _MIN_CELL_AREA_PX or area > max_area:
            continue
        cells.append(bbox)

    return cells


def _flatten_to_white(image: Image.Image) -> Image.Image:
    canvas = Image.new("RGBA", image.size, (255, 255, 255, 255))
    canvas.paste(image, (0, 0), mask=image.split()[3])
    return canvas.convert("RGB")


def _clean_cell(image: Image.Image, bbox: tuple[int, int, int, int]) -> Image.Image:
    flat = _flatten_to_white(image.crop(bbox))

    red, green, blue = flat.split()
    redder_than_green = ImageChops.subtract(red, green).point(lambda v: 255 if v > _RED_FRINGE_DELTA else 0)
    redder_than_blue = ImageChops.subtract(red, blue).point(lambda v: 255 if v > _RED_FRINGE_DELTA else 0)
    fringe_mask = ImageChops.multiply(redder_than_green, redder_than_blue)

    white = Image.new("RGB", flat.size, (255, 255, 255))
    flat.paste(white, (0, 0), mask=fringe_mask)
    return flat
