"""Dispatches a preset's ``content_script`` name to an ``app.presets.scripts`` module."""

from __future__ import annotations

import importlib
from types import ModuleType

from app.exceptions import PresetScriptError


def _import_script(name: str) -> ModuleType:
    """Import ``app.presets.scripts.<name>``, falling back to
    ``app.presets.scripts.custom.<name>`` for personal/local scripts that are
    gitignored (see ``app/presets/scripts/custom/README.md``).
    """

    try:
        return importlib.import_module(f"app.presets.scripts.{name}")
    except ModuleNotFoundError:
        try:
            return importlib.import_module(f"app.presets.scripts.custom.{name}")
        except ImportError as exc:
            raise PresetScriptError(f"Skript {name!r} nicht gefunden") from exc
    except ImportError as exc:
        raise PresetScriptError(f"Skript {name!r} nicht gefunden") from exc


def run_content_script(name: str) -> str:
    """Import ``app.presets.scripts.<name>`` and call its ``generate()`` function.

    Raises :class:`~app.exceptions.PresetScriptError` if the module or its
    ``generate()`` function does not exist, the function raises, or it does
    not return a string.
    """

    module = _import_script(name)

    generate = getattr(module, "generate", None)
    if not callable(generate):
        raise PresetScriptError(f"Skript {name!r} hat keine generate()-Funktion")

    try:
        content = generate()
    except PresetScriptError:
        raise
    except Exception as exc:  # noqa: BLE001 - any script failure becomes a user-facing error
        raise PresetScriptError(f"Skript {name!r} fehlgeschlagen: {exc}") from exc

    if not isinstance(content, str):
        raise PresetScriptError(f"Skript {name!r} hat keinen Text zurueckgegeben")

    return content


def run_image_script(name: str) -> bytes:
    """Import ``app.presets.scripts.<name>`` and call its ``generate_image()`` function.

    Raises :class:`~app.exceptions.PresetScriptError` if the module or its
    ``generate_image()`` function does not exist, the function raises, or it
    does not return ``bytes``.
    """

    module = _import_script(name)

    generate_image = getattr(module, "generate_image", None)
    if not callable(generate_image):
        raise PresetScriptError(f"Skript {name!r} hat keine generate_image()-Funktion")

    try:
        image = generate_image()
    except PresetScriptError:
        raise
    except Exception as exc:  # noqa: BLE001 - any script failure becomes a user-facing error
        raise PresetScriptError(f"Skript {name!r} fehlgeschlagen: {exc}") from exc

    if not isinstance(image, bytes):
        raise PresetScriptError(f"Skript {name!r} hat keine Bilddaten (bytes) zurueckgegeben")

    return image
