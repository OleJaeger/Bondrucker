"""Offene Positionen der Einkaufsliste aus Mealie (https://mealie.io/), REST-API v1.

Konfiguration ueber ``MEALIE_BASE_URL``/``MEALIE_API_TOKEN`` (erforderlich)
und ``MEALIE_SHOPPING_LIST_ID`` (optional, sonst wird die erste vorhandene
Einkaufsliste verwendet). Implementiert gegen Mealie API v1
(``/api/households/shopping/lists`` und ``/api/households/shopping/items``)
- bei abweichenden Mealie-Versionen ggf. anpassen.
"""

from __future__ import annotations

import httpx

from app.config import get_effective_settings
from app.exceptions import PresetScriptError

_TIMEOUT = 10.0


def generate() -> str:
    settings = get_effective_settings()
    if not settings.mealie_base_url or not settings.mealie_api_token:
        raise PresetScriptError(
            "Mealie ist nicht konfiguriert (MEALIE_BASE_URL/MEALIE_API_TOKEN fehlen)."
        )

    base_url = settings.mealie_base_url.rstrip("/")
    headers = {"Authorization": f"Bearer {settings.mealie_api_token}"}

    try:
        list_id = settings.mealie_shopping_list_id
        if not list_id:
            response = httpx.get(
                f"{base_url}/api/households/shopping/lists", headers=headers, timeout=_TIMEOUT
            )
            response.raise_for_status()
            lists = response.json().get("items", [])
            if not lists:
                raise PresetScriptError("In Mealie ist keine Einkaufsliste vorhanden.")
            list_id = lists[0]["id"]

        response = httpx.get(
            f"{base_url}/api/households/shopping/items",
            headers=headers,
            params={"queryFilter": f'shoppingListId="{list_id}"', "perPage": 100},
            timeout=_TIMEOUT,
        )
        response.raise_for_status()
        items = response.json().get("items", [])
    except httpx.HTTPError as exc:
        raise PresetScriptError(f"Einkaufsliste konnte nicht geladen werden: {exc}") from exc

    open_items = [item for item in items if not item.get("checked")]
    if not open_items:
        return "Die Einkaufsliste ist leer."

    no_label = "Ohne Label"
    groups: dict[str, list[dict]] = {}
    for item in open_items:
        label = item.get("label") or {}
        label_name = label.get("name") or no_label
        groups.setdefault(label_name, []).append(item)

    lines: list[str] = []
    for label_name in sorted(groups, key=lambda name: (name == no_label, name.lower())):
        if lines:
            lines.append("")
        lines.append(f"## {label_name}")
        for item in groups[label_name]:
            food = item.get("food") or {}
            name = food.get("name") or item.get("display") or item.get("note") or "?"
            quantity = item.get("quantity")
            if quantity:
                lines.append(f"- [ ] {name} ({quantity:g})")
            else:
                lines.append(f"- [ ] {name}")

    return "\n".join(lines)
