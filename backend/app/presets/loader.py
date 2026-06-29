"""Loads and validates standard print object (preset) configurations from YAML files."""

from __future__ import annotations

import logging
from pathlib import Path

import yaml
from pydantic import ValidationError

from app.config import get_settings
from app.exceptions import PresetNotFoundError
from app.presets.schema import PresetConfig

logger = logging.getLogger(__name__)


class PresetRegistry:
    """In-memory registry of standard print object (preset) configurations.

    Invalid files (bad YAML or failing schema validation) are logged and
    skipped so that a single broken config cannot take down the whole
    application ("ungueltige Standarddruckobjekte").
    """

    def __init__(self, presets_dir: str | Path):
        self._dir = Path(presets_dir)
        self._presets: dict[str, PresetConfig] = {}
        self.reload()

    def reload(self) -> None:
        presets: dict[str, PresetConfig] = {}

        if not self._dir.is_dir():
            logger.warning("Presets directory %s does not exist", self._dir)
            self._presets = presets
            return

        # "custom/" holds personal presets that are gitignored (see
        # config/presets/custom/README.md) - loaded after the main directory,
        # so a custom file can locally override a shipped preset of the same
        # key.
        paths = (
            sorted(self._dir.glob("*.yaml"))
            + sorted(self._dir.glob("*.yml"))
            + sorted(self._dir.glob("custom/*.yaml"))
            + sorted(self._dir.glob("custom/*.yml"))
        )
        for path in paths:
            key = path.stem
            try:
                raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
                if not isinstance(raw, dict):
                    raise ValueError("top-level YAML document must be a mapping")
                config = PresetConfig.model_validate({**raw, "key": key})
            except (yaml.YAMLError, ValidationError, ValueError) as exc:
                logger.error("Skipping invalid preset config %s: %s", path, exc)
                continue

            presets[key] = config

        self._presets = presets
        logger.info(
            "Loaded %d preset configuration(s): %s",
            len(presets),
            ", ".join(sorted(presets)) or "-",
        )

    def get(self, key: str) -> PresetConfig:
        try:
            return self._presets[key]
        except KeyError as exc:
            raise PresetNotFoundError(key) from exc

    def list(self) -> list[PresetConfig]:
        return list(self._presets.values())


_registry: PresetRegistry | None = None


def get_preset_registry() -> PresetRegistry:
    """Return the process-wide preset registry, loading it on first use."""

    global _registry
    if _registry is None:
        settings = get_settings()
        _registry = PresetRegistry(settings.presets_dir)
    return _registry


def reset_preset_registry() -> None:
    """Drop the cached registry so it is reloaded on next access (tests)."""

    global _registry
    _registry = None
