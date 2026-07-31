"""Jagdtag heute: aktuell jagdbares Wild (Haarwild/Federwild) aus der
PostgreSQL-Tabelle ``jagdzeiten`` sowie Wetter, Windrichtung und
Sonnenuntergang aus HomeAssistant.

Konfiguration: JAGD_DB_HOST/PORT/NAME/USER/PASSWORD,
HOMEASSISTANT_URL, HOMEASSISTANT_TOKEN, WEATHER_LOCATION_NAME
(siehe ``app.config.Settings``).

Aktuelle Werte kommen von der Wetterstation (HA-Sensoren):
  sensor.wetterstation_outdoor_temperature
  sensor.wetterstation_wind_direction_10m_avg  (Grad, 0 = Nord)
  sensor.wetterstation_wind_speed

Bedingung und Vorhersage kommen aus weather.openweathermap (via HA).
Sonnenuntergang aus sun.sun (Attribut next_setting).

Die Tabelle ``jagdzeiten`` enthaelt pro Jagdzeitraum eine Zeile:

- ``title``: der Zeitraum als "TT.MM - TT.MM" (z. B. "01.10 - 31.12."),
  ``"ganzjaehrig"`` (das ganze Jahr jagdbar) oder ``"ganzjaehrig geschont"``
  (das ganze Jahr Schonzeit, nie jagdbar).
- ``wild_haarwild`` / ``wild_federwild``: kommagetrennte Liste der Wildarten,
  fuer die dieser Zeitraum gilt (je nach Kategorie).
"""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any

import httpx
import psycopg

from app.config import get_effective_settings
from app.exceptions import PresetScriptError

_TIMEOUT = 10.0

# "01.10 - 31.12." / "1.10-31.12" / "01.10. - 31.12" / ...
_RANGE_RE = re.compile(r"(\d{1,2})\.(\d{1,2})\.?\s*-\s*(\d{1,2})\.(\d{1,2})\.?")

_HA_CONDITIONS: dict[str, str] = {
    "clear-night": "Klare Nacht",
    "cloudy": "Bewoelkt",
    "exceptional": "Aussergewoehnlich",
    "fog": "Nebel",
    "hail": "Hagel",
    "lightning": "Gewitter",
    "lightning-rainy": "Gewitter mit Regen",
    "partlycloudy": "Teilweise bewoelkt",
    "pouring": "Starkregen",
    "rainy": "Regen",
    "snowy": "Schnee",
    "snowy-rainy": "Schnee und Regen",
    "sunny": "Sonnig",
    "windy": "Windig",
    "windy-variant": "Windig (mit Boeen)",
}

_COMPASS = ["N", "NNO", "NO", "ONO", "O", "OSO", "SO", "SSO", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]

def _degrees_to_compass(degrees: float) -> str:
    return _COMPASS[round(degrees / 22.5) % 16]

def _is_jagdzeit_relevant(title: str | None, today: tuple[int, int]) -> bool:
    """Prueft, ob der Jagdzeitraum ``title`` "heute" (Monat, Tag) abdeckt.

    ``title`` ist entweder ein "TT.MM - TT.MM"-Zeitraum (ggf. ueber den
    Jahreswechsel laufend, z. B. "01.05 - 31.01."), ``"ganzjaehrig"`` (immer
    relevant) oder ``"ganzjaehrig geschont"`` (nie relevant).
    """

    if not title:
        return False

    normalized = title.strip().lower()
    if "geschont" in normalized:
        return False
    if normalized in ("ganzjaehrig", "ganzjährig"):
        return True

    match = _RANGE_RE.search(title)
    if not match:
        return False

    start_day, start_month, end_day, end_month = (int(group) for group in match.groups())
    start = (start_month, start_day)
    end = (end_month, end_day)

    if start <= end:
        return start <= today <= end
    return today >= start or today <= end


def _split_species(value: str | None) -> list[str]:
    if not value:
        return []
    return [name.strip() for name in value.split(",") if name.strip()]


def _fetch_jagdbares_wild(settings, today: tuple[int, int]) -> tuple[list[str], list[str]]:
    if not (settings.jagd_db_host and settings.jagd_db_name and settings.jagd_db_user and settings.jagd_db_password):
        raise PresetScriptError(
            "Jagdzeiten-Datenbank ist nicht konfiguriert "
            "(JAGD_DB_HOST/JAGD_DB_NAME/JAGD_DB_USER/JAGD_DB_PASSWORD fehlen)."
        )

    try:
        with psycopg.connect(
            host=settings.jagd_db_host,
            port=settings.jagd_db_port,
            dbname=settings.jagd_db_name,
            user=settings.jagd_db_user,
            password=settings.jagd_db_password,
            connect_timeout=int(_TIMEOUT),
        ) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT title, wild_haarwild, wild_federwild "
                    "FROM public.jagdzeiten ORDER BY nc_order"
                )
                rows = cur.fetchall()
    except psycopg.Error as exc:
        raise PresetScriptError(f"Jagdzeiten konnten nicht geladen werden: {exc}") from exc

    haarwild: list[str] = []
    federwild: list[str] = []
    for title, wild_haarwild, wild_federwild in rows:
        if not _is_jagdzeit_relevant(title, today):
            continue
        haarwild.extend(_split_species(wild_haarwild))
        federwild.extend(_split_species(wild_federwild))

    return haarwild, federwild


def _get_ha_state(base_url: str, token: str, entity_id: str) -> dict[str, Any]:
    url = f"{base_url.rstrip('/')}/api/states/{entity_id}"
    try:
        response = httpx.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=_TIMEOUT)
        response.raise_for_status()
        return response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise PresetScriptError(f"Wetterdaten konnten nicht geladen werden: {exc}") from exc


def _fetch_weather(settings) -> str:
    if not settings.homeassistant_url or not settings.homeassistant_token:
        raise PresetScriptError(
            "HOMEASSISTANT_URL und HOMEASSISTANT_TOKEN muessen konfiguriert sein."
        )

    ha_url = settings.homeassistant_url
    ha_token = settings.homeassistant_token

    temp_data = _get_ha_state(ha_url, ha_token, "sensor.wetterstation_outdoor_temperature")
    wind_dir_data = _get_ha_state(ha_url, ha_token, "sensor.wetterstation_wind_direction_10m_avg")
    wind_speed_data = _get_ha_state(ha_url, ha_token, "sensor.wetterstation_wind_speed")
    owm_data = _get_ha_state(ha_url, ha_token, "weather.openweathermap")
    sun_data = _get_ha_state(ha_url, ha_token, "sun.sun")

    try:
        temperature = float(temp_data["state"])
        wind_direction_deg = float(wind_dir_data["state"])
        wind_speed = float(wind_speed_data["state"])
    except (KeyError, TypeError, ValueError) as exc:
        raise PresetScriptError(f"Sensordaten konnten nicht gelesen werden: {exc}") from exc

    condition_key = owm_data.get("state", "")
    description = _HA_CONDITIONS.get(condition_key, condition_key or "Unbekannt")

    wind_compass = _degrees_to_compass(wind_direction_deg)
    wind_unit = wind_speed_data.get("attributes", {}).get("unit_of_measurement", "km/h")

    forecast = owm_data.get("attributes", {}).get("forecast", [])
    t_max = t_min = precipitation = None
    if forecast:
        today_fc = forecast[0]
        t_max = today_fc.get("temperature")
        t_min = today_fc.get("templow")
        precipitation = today_fc.get("precipitation_probability")

    next_setting = sun_data.get("attributes", {}).get("next_setting", "")
    try:
        sunset_text = datetime.fromisoformat(next_setting).strftime("%H:%M")
    except (ValueError, TypeError):
        sunset_text = "unbekannt"

    lines = [
        description,
        "",
        f"- Temperatur: {temperature:.1f} Grad C",
    ]
    if t_max is not None:
        lines.append(f"- Hoechsttemperatur: {t_max:.0f} Grad C")
    if t_min is not None:
        lines.append(f"- Tiefsttemperatur: {t_min:.0f} Grad C")
    if precipitation is not None:
        lines.append(f"- Niederschlagswahrscheinlichkeit: {precipitation:.0f} %")
    lines.extend([
        f"- Windrichtung: {wind_compass} ({wind_direction_deg:.0f} Grad)",
        f"- Windgeschwindigkeit: {wind_speed:.0f} {wind_unit}",
        f"- Sonnenuntergang: {sunset_text} Uhr",
    ])

    return "\n".join(lines) + "\n"


def _format_section(items: list[str]) -> str:
    if not items:
        return "Heute nichts jagdbar."
    return "\n".join(f"- {item}" for item in items)


def generate() -> str:
    settings = get_effective_settings()
    today_date = date.today()
    today = (today_date.month, today_date.day)

    haarwild, federwild = _fetch_jagdbares_wild(settings, today)
    weather = _fetch_weather(settings)

    return (
        # f"**{settings.weather_location_name}, {today_date.strftime('%d.%m.%Y')}**\n\n"
        f"## Haarwild\n\n{_format_section(haarwild)}\n\n"
        f"## Federwild\n\n{_format_section(federwild)}\n\n"
        f"## Wetter\n\n{weather}"
    )
