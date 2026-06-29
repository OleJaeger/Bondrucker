"""Wettervorhersage aus HomeAssistant.

Aktuelle Messwerte kommen von der lokalen Wetterstation (HA-Sensoren):
  sensor.wetterstation_outdoor_temperature
  sensor.wetterstation_feels_like_temperature
  sensor.wetterstation_wind_direction_10m_avg  (Grad, 0 = Nord)
  sensor.wetterstation_wind_speed

Wetterbedingung und Vorhersage kommen aus weather.openweathermap (via HA).

Konfiguration: HOMEASSISTANT_URL, HOMEASSISTANT_TOKEN, WEATHER_LOCATION_NAME
(siehe ``app.config.Settings``).
"""

from __future__ import annotations

from datetime import date
from typing import Any

import httpx

from app.config import get_effective_settings
from app.exceptions import PresetScriptError

_TIMEOUT = 10.0

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


def _get_state(base_url: str, token: str, entity_id: str) -> dict[str, Any]:
    url = f"{base_url.rstrip('/')}/api/states/{entity_id}"
    try:
        response = httpx.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=_TIMEOUT)
        response.raise_for_status()
        return response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise PresetScriptError(f"HomeAssistant-Abfrage fuer {entity_id} fehlgeschlagen: {exc}") from exc


def generate() -> str:
    settings = get_effective_settings()

    if not settings.homeassistant_url or not settings.homeassistant_token:
        raise PresetScriptError(
            "HOMEASSISTANT_URL und HOMEASSISTANT_TOKEN muessen konfiguriert sein."
        )

    ha_url = settings.homeassistant_url
    ha_token = settings.homeassistant_token

    temp_data = _get_state(ha_url, ha_token, "sensor.wetterstation_outdoor_temperature")
    feels_data = _get_state(ha_url, ha_token, "sensor.wetterstation_feels_like_temperature")
    wind_dir_data = _get_state(ha_url, ha_token, "sensor.wetterstation_wind_direction_10m_avg")
    wind_speed_data = _get_state(ha_url, ha_token, "sensor.wetterstation_wind_speed")
    owm_data = _get_state(ha_url, ha_token, "weather.openweathermap")

    try:
        temperature = float(temp_data["state"])
        feels_like = float(feels_data["state"])
        wind_direction_deg = float(wind_dir_data["state"])
        wind_speed = float(wind_speed_data["state"])
    except (KeyError, TypeError, ValueError) as exc:
        raise PresetScriptError(f"Sensordaten konnten nicht gelesen werden: {exc}") from exc

    condition_key = owm_data.get("state", "")
    condition = _HA_CONDITIONS.get(condition_key, condition_key or "Unbekannt")

    wind_compass = _degrees_to_compass(wind_direction_deg)
    wind_unit = wind_speed_data.get("attributes", {}).get("unit_of_measurement", "km/h")

    forecast = owm_data.get("attributes", {}).get("forecast", [])
    t_max = t_min = precipitation = None
    if forecast:
        today_fc = forecast[0]
        t_max = today_fc.get("temperature")
        t_min = today_fc.get("templow")
        precipitation = today_fc.get("precipitation_probability")

    today = date.today().strftime("%d.%m.%Y")
    lines = [
        f"**{settings.weather_location_name}, {today}**",
        "",
        condition,
        "",
        f"- Temperatur: {temperature:.1f} Grad C",
        f"- Gefuehlte Temperatur: {feels_like:.1f} Grad C",
        f"- Wind: {wind_speed:.0f} {wind_unit} aus {wind_compass} ({wind_direction_deg:.0f} Grad)",
    ]

    if t_max is not None:
        lines.append(f"- Hoechsttemperatur: {t_max:.0f} Grad C")
    if t_min is not None:
        lines.append(f"- Tiefsttemperatur: {t_min:.0f} Grad C")
    if precipitation is not None:
        lines.append(f"- Niederschlagswahrscheinlichkeit: {precipitation:.0f} %")

    return "\n".join(lines) + "\n"
