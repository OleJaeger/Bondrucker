"""Loads and validates print template configurations from YAML files."""

from __future__ import annotations

import logging
from pathlib import Path

import yaml
from pydantic import ValidationError

from app.config import get_settings
from app.exceptions import TemplateNotFoundError
from app.templates.schema import TemplateConfig

logger = logging.getLogger(__name__)


class TemplateRegistry:
    """In-memory registry of template configurations.

    Invalid files (bad YAML or failing schema validation) are logged and
    skipped so that a single broken config cannot take down the whole
    application ("ungueltige Vorlagen").
    """

    def __init__(self, templates_dir: str | Path):
        self._dir = Path(templates_dir)
        self._templates: dict[str, TemplateConfig] = {}
        self.reload()

    def reload(self) -> None:
        templates: dict[str, TemplateConfig] = {}

        if not self._dir.is_dir():
            logger.warning("Templates directory %s does not exist", self._dir)
            self._templates = templates
            return

        # "custom/" holds personal templates that are gitignored (see
        # config/templates/custom/README.md) - loaded after the main
        # directory, so a custom file can locally override a shipped
        # template of the same key.
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
                config = TemplateConfig.model_validate({**raw, "key": key})
            except (yaml.YAMLError, ValidationError, ValueError) as exc:
                logger.error("Skipping invalid template config %s: %s", path, exc)
                continue

            templates[key] = config

        self._templates = templates
        logger.info(
            "Loaded %d template configuration(s): %s",
            len(templates),
            ", ".join(sorted(templates)) or "-",
        )

    def get(self, key: str) -> TemplateConfig:
        try:
            return self._templates[key]
        except KeyError as exc:
            raise TemplateNotFoundError(key) from exc

    def list(self) -> list[TemplateConfig]:
        return list(self._templates.values())


_registry: TemplateRegistry | None = None


def get_template_registry() -> TemplateRegistry:
    """Return the process-wide template registry, loading it on first use."""

    global _registry
    if _registry is None:
        settings = get_settings()
        _registry = TemplateRegistry(settings.templates_dir)
    return _registry


def reset_template_registry() -> None:
    """Drop the cached registry so it is reloaded on next access (tests)."""

    global _registry
    _registry = None
