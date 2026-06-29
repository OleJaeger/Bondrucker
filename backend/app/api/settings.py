"""Web-configurable application settings endpoints (``/api/settings``).

Exposes exactly the ``Settings`` fields listed in ``app.config.WEB_SETTINGS_FIELDS``
(the preset integrations: Mealie, HomeAssistant, Super Productivity, Jagdtag) -
everything else (printer, storage paths, security, ...) stays .env-only and is
not part of this API. A field set via the environment/.env is "locked" and can
only be changed there - see ``app.config.env_locked_fields()``.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import SettingFieldSpec, WEB_SETTINGS_FIELDS, Settings, env_locked_fields, get_effective_settings
from app.database import get_session
from app.presets.loader import get_preset_registry
from app.repositories.settings import SettingsRepository
from app.schemas import SettingFieldInfo
from app.security import require_api_key

router = APIRouter(prefix="/api/settings", tags=["settings"], dependencies=[Depends(require_api_key)])


def _presets_using(key: str) -> list[str]:
    return sorted(preset.name for preset in get_preset_registry().list() if key in preset.config_keys)


def _coerce_value(spec: SettingFieldSpec, raw: object) -> str | int:
    if spec.type == "int":
        try:
            return int(raw)  # type: ignore[arg-type]
        except (TypeError, ValueError) as exc:
            raise HTTPException(400, f"{spec.key} muss eine ganze Zahl sein") from exc
    return str(raw)


def _build_response() -> list[SettingFieldInfo]:
    effective = get_effective_settings()
    locked = env_locked_fields()

    fields = []
    for key, spec in WEB_SETTINGS_FIELDS.items():
        current = getattr(effective, key)
        is_set = current is not None and current != ""
        fields.append(
            SettingFieldInfo(
                key=key,
                group=spec.group,
                label=spec.label,
                type=spec.type,
                secret=spec.secret,
                locked=key in locked,
                value=None if spec.secret else current,
                is_set=is_set,
                default=None if spec.secret else Settings.model_fields[key].default,
                used_by_presets=_presets_using(key),
            )
        )
    return fields


@router.get("", response_model=list[SettingFieldInfo])
def list_settings() -> list[SettingFieldInfo]:
    """List all web-configurable settings fields and their current/effective values."""

    return _build_response()


@router.put("", response_model=list[SettingFieldInfo])
def update_settings(
    payload: dict[str, str | int | None], session: Session = Depends(get_session)
) -> list[SettingFieldInfo]:
    """Update one or more settings fields.

    ``payload`` is sparse - only keys to change need to be included. A value
    of ``null`` removes the web-configured override (reverts to default).
    Fields locked by the environment/.env cannot be changed here.
    """

    locked = env_locked_fields()
    repo = SettingsRepository(session)

    for key, value in payload.items():
        spec = WEB_SETTINGS_FIELDS.get(key)
        if spec is None:
            raise HTTPException(400, f"Unbekanntes Settings-Feld: {key}")
        if key in locked:
            raise HTTPException(400, f"{key} ist per .env gesperrt und kann nicht ueber die Web-App geaendert werden")

        if value is None:
            repo.delete(key)
        else:
            repo.set(key, _coerce_value(spec, value))

    return _build_response()
