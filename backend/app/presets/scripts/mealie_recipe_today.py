"""Heutiges Rezept aus Mealie (https://mealie.io/), REST-API v1: Bild und
Anleitung (Zutaten/Zubereitung) des ersten fuer heute im Essenplan
hinterlegten Rezepts.

Konfiguration ueber ``MEALIE_BASE_URL``/``MEALIE_API_TOKEN`` (dieselben
Einstellungen wie ``mealie_mealplan.py``/``mealie_shopping_list.py``, siehe
.env.example). Implementiert gegen Mealie API v1
(``/api/households/mealplans``, ``/api/recipes/{slug}`` und
``/api/media/recipes/{recipe_id}/images/original.webp``) - bei
abweichenden Mealie-Versionen ggf. anpassen.

Das Rezeptfoto haengt **nicht** unter ``/api/recipes/{slug}/image`` (das ist
nur der Upload/Update/Delete-Endpunkt fuer POST/PUT/DELETE), sondern wird
ueber die interne Rezept-``id`` (UUID, nicht der Slug) unter
``/api/media/recipes/{id}/images/original.webp`` ausgeliefert; ein Rezept
ohne hinterlegtes Bild hat ``image: null``.
"""

from __future__ import annotations

from datetime import date

import httpx

from app.config import get_effective_settings
from app.exceptions import PresetScriptError

_TIMEOUT = 10.0

_ENTRY_TYPE_ORDER = ["breakfast", "lunch", "dinner", "side"]


def _entry_sort_key(entry: dict) -> tuple[int, str]:
    entry_type = entry.get("entryType") or ""
    try:
        index = _ENTRY_TYPE_ORDER.index(entry_type)
    except ValueError:
        index = len(_ENTRY_TYPE_ORDER)
    return (index, entry_type)


def _todays_recipe_slug(base_url: str, headers: dict) -> str | None:
    today = date.today().isoformat()
    response = httpx.get(
        f"{base_url}/api/households/mealplans",
        headers=headers,
        params={"start_date": today, "end_date": today, "perPage": 100},
        timeout=_TIMEOUT,
    )
    response.raise_for_status()
    entries = response.json().get("items", [])

    recipe_entries = [entry for entry in entries if (entry.get("recipe") or {}).get("slug")]
    if not recipe_entries:
        return None

    recipe_entries.sort(key=_entry_sort_key)
    return recipe_entries[0]["recipe"]["slug"]


def _todays_recipe(base_url: str, headers: dict) -> dict | None:
    slug = _todays_recipe_slug(base_url, headers)
    if slug is None:
        return None

    response = httpx.get(f"{base_url}/api/recipes/{slug}", headers=headers, timeout=_TIMEOUT)
    response.raise_for_status()
    return response.json()


def _require_settings() -> tuple[str, dict]:
    settings = get_effective_settings()
    if not settings.mealie_base_url or not settings.mealie_api_token:
        raise PresetScriptError(
            "Mealie ist nicht konfiguriert (MEALIE_BASE_URL/MEALIE_API_TOKEN fehlen)."
        )

    base_url = settings.mealie_base_url.rstrip("/")
    headers = {"Authorization": f"Bearer {settings.mealie_api_token}"}
    return base_url, headers


def _format_ingredient(ingredient: dict) -> str:
    display = ingredient.get("display")
    if display:
        return display
    food = (ingredient.get("food") or {}).get("name")
    return food or ingredient.get("note") or "?"


def _format_recipe(recipe: dict) -> str:
    lines = [f"## {recipe.get('name') or '?'}"]

    meta = [part for part in (recipe.get("recipeYield"), recipe.get("totalTime")) if part]
    if meta:
        lines.append(" - ".join(meta))

    ingredients = recipe.get("recipeIngredient") or []
    if ingredients:
        lines.append("")
        lines.append("### Zutaten")
        lines.extend(f"- {_format_ingredient(ingredient)}" for ingredient in ingredients)

    instructions = [
        text
        for step in (recipe.get("recipeInstructions") or [])
        if (text := (step.get("text") or "").strip())
    ]
    if instructions:
        lines.append("")
        lines.append("### Zubereitung")
        lines.extend(f"{index}. {text}" for index, text in enumerate(instructions, start=1))

    return "\n".join(lines)


def generate() -> str:
    base_url, headers = _require_settings()

    try:
        recipe = _todays_recipe(base_url, headers)
    except httpx.HTTPError as exc:
        raise PresetScriptError(f"Rezept konnte nicht geladen werden: {exc}") from exc

    if recipe is None:
        return "Fuer heute ist kein Rezept im Essenplan hinterlegt."

    return _format_recipe(recipe)


def generate_image() -> bytes:
    base_url, headers = _require_settings()

    try:
        recipe = _todays_recipe(base_url, headers)
        if recipe is None:
            raise PresetScriptError("Fuer heute ist kein Rezept im Essenplan hinterlegt.")

        recipe_id = recipe.get("id")
        if not recipe_id or not recipe.get("image"):
            raise PresetScriptError("Fuer das heutige Rezept ist kein Bild in Mealie hinterlegt.")

        response = httpx.get(
            f"{base_url}/api/media/recipes/{recipe_id}/images/original.webp",
            headers=headers,
            timeout=_TIMEOUT,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise PresetScriptError(f"Rezeptbild konnte nicht geladen werden: {exc}") from exc

    return response.content
