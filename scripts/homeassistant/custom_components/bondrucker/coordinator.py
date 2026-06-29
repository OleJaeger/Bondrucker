from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CONF_API_KEY, CONF_HOST, DEFAULT_PRESET_SCAN_INTERVAL, REQUEST_TIMEOUT

_LOGGER = logging.getLogger(__name__)


class BondruckerStatusCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Polls /api/printer/status at the configured interval."""

    def __init__(self, hass: HomeAssistant, entry_data: dict) -> None:
        self._host = entry_data[CONF_HOST].rstrip("/")
        self._api_key = entry_data[CONF_API_KEY]
        self._session = async_get_clientsession(hass)
        super().__init__(
            hass,
            _LOGGER,
            name="Bondrucker Status",
            update_interval=timedelta(seconds=entry_data.get("scan_interval", 30)),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        url = f"{self._host}/api/printer/status"
        try:
            async with self._session.get(
                url,
                headers={"X-API-Key": self._api_key},
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT),
            ) as resp:
                if resp.status != 200:
                    raise UpdateFailed(f"HTTP {resp.status} von {url}")
                return await resp.json()
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Verbindungsfehler: {err}") from err


class BondruckerPresetCoordinator(DataUpdateCoordinator[list[dict[str, Any]]]):
    """Polls /api/presets every DEFAULT_PRESET_SCAN_INTERVAL seconds."""

    def __init__(self, hass: HomeAssistant, entry_data: dict) -> None:
        self._host = entry_data[CONF_HOST].rstrip("/")
        self._api_key = entry_data[CONF_API_KEY]
        self._session = async_get_clientsession(hass)
        super().__init__(
            hass,
            _LOGGER,
            name="Bondrucker Presets",
            update_interval=timedelta(seconds=DEFAULT_PRESET_SCAN_INTERVAL),
        )

    async def _async_update_data(self) -> list[dict[str, Any]]:
        url = f"{self._host}/api/presets"
        try:
            async with self._session.get(
                url,
                headers={"X-API-Key": self._api_key},
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT),
            ) as resp:
                if resp.status != 200:
                    raise UpdateFailed(f"HTTP {resp.status} von {url}")
                return await resp.json()
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Verbindungsfehler: {err}") from err
