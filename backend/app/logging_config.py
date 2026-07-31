"""Logging setup: console + rotating file handler under ``LOG_DIR``."""

from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path

from app.config import get_settings

_configured = False


def configure_logging() -> None:
    """Configure the root logger. Safe to call multiple times (idempotent)."""

    global _configured
    if _configured:
        return

    settings = get_settings()
    log_dir = Path(settings.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s] %(message)s"
    )

    root = logging.getLogger()
    root.setLevel(level)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root.addHandler(console_handler)

    file_handler = logging.handlers.RotatingFileHandler(
        log_dir / "app.log", maxBytes=5 * 1024 * 1024, backupCount=5
    )
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    _configured = True
