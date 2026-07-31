"""Essenplan der aktuellen Woche aus Mealie (https://mealie.io/), REST-API v1.

Konfiguration ueber ``MEALIE_BASE_URL``/``MEALIE_API_TOKEN`` (dieselben
Einstellungen wie ``mealie_shopping_list.py``, siehe .env.example).
Implementiert gegen Mealie API v1 (``/api/households/mealplans``) - bei
abweichenden Mealie-Versionen ggf. anpassen.
"""

from __future__ import annotations

from datetime import date, timedelta

import httpx

from app.config import get_effective_settings
from app.exceptions import PresetScriptError

_TIMEOUT = 10.0

_WEEKDAYS = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]

_ENTRY_TYPE_ORDER = ["breakfast", "lunch", "dinner", "side"]
_ENTRY_TYPE_LABELS = {
    "breakfast": "Fruehstueck",
    "lunch": "Mittagessen",
    "dinner": "Abendessen",
    "side": "Beilage",
}


def _entry_name(entry: dict) -> str:
    recipe = entry.get("recipe") or {}
    return recipe.get("name") or entry.get("title") or entry.get("text") or "?"


def _entry_sort_key(entry: dict) -> tuple[int, str]:
    entry_type = entry.get("entryType") or ""
    try:
        index = _ENTRY_TYPE_ORDER.index(entry_type)
    except ValueError:
        index = len(_ENTRY_TYPE_ORDER)
    return (index, entry_type)


def generate() -> str:
    settings = get_effective_settings()
    if not settings.mealie_base_url or not settings.mealie_api_token:
        raise PresetScriptError(
            "Mealie ist nicht konfiguriert (MEALIE_BASE_URL/MEALIE_API_TOKEN fehlen)."
        )

    base_url = settings.mealie_base_url.rstrip("/")
    headers = {"Authorization": f"Bearer {settings.mealie_api_token}"}

    today = date.today()
    start = today - timedelta(days=today.weekday())
    end = start + timedelta(days=6)

    try:
        response = httpx.get(
            f"{base_url}/api/households/mealplans",
            headers=headers,
            params={"start_date": start.isoformat(), "end_date": end.isoformat(), "perPage": 100},
            timeout=_TIMEOUT,
        )
        response.raise_for_status()
        entries = response.json().get("items", [])
    except httpx.HTTPError as exc:
        raise PresetScriptError(f"Essenplan konnte nicht geladen werden: {exc}") from exc

    days: dict[date, list[dict]] = {}
    for entry in entries:
        try:
            entry_date = date.fromisoformat(entry["date"])
        except (KeyError, ValueError, TypeError):
            continue
        days.setdefault(entry_date, []).append(entry)

    if not days:
        return "Fuer diese Woche ist kein Essenplan hinterlegt."

    lines: list[str] = []
    current = start
    while current <= end:
        day_entries = days.get(current)
        if day_entries:
            if lines:
                lines.append("")
            weekday_name = _WEEKDAYS[current.weekday()]
            lines.append(f"## {weekday_name}, {current.strftime('%d.%m.')}")
            for entry in sorted(day_entries, key=_entry_sort_key):
                label = _ENTRY_TYPE_LABELS.get(entry.get("entryType"), entry.get("entryType") or "")
                name = _entry_name(entry)
                lines.append(f"- {name} ({label})" if label else f"- {name}")
        current += timedelta(days=1)

    return "\n".join(lines)
