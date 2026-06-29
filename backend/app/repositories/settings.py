"""Data-access layer for web-configured Settings overrides (``app_settings``).

See ``app.config.get_effective_settings()`` for how these overrides are
layered on top of the .env-based ``Settings``.
"""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AppSetting


class SettingsRepository:
    def __init__(self, session: Session):
        self._session = session

    def get_all(self) -> dict[str, Any]:
        rows = self._session.scalars(select(AppSetting))
        return {row.key: json.loads(row.value_json) for row in rows}

    def set(self, key: str, value: Any) -> None:
        encoded = json.dumps(value)
        existing = self._session.get(AppSetting, key)
        if existing is None:
            self._session.add(AppSetting(key=key, value_json=encoded))
        else:
            existing.value_json = encoded
        self._session.commit()

    def delete(self, key: str) -> None:
        existing = self._session.get(AppSetting, key)
        if existing is not None:
            self._session.delete(existing)
            self._session.commit()
