from __future__ import annotations

import logging
from typing import Any

import aiohttp

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_API_KEY, CONF_HOST, DOMAIN, REQUEST_TIMEOUT
from .coordinator import BondruckerPresetCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: BondruckerPresetCoordinator = hass.data[DOMAIN][entry.entry_id][
        "preset_coordinator"
    ]
    async_add_entities(
        BondruckerPresetButton(coordinator, entry, preset)
        for preset in (coordinator.data or [])
    )


class BondruckerPresetButton(CoordinatorEntity[BondruckerPresetCoordinator], ButtonEntity):
    """A button that triggers one Bondrucker preset."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:printer"

    def __init__(
        self,
        coordinator: BondruckerPresetCoordinator,
        entry: ConfigEntry,
        preset: dict[str, Any],
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._preset_key = preset["key"]
        self._attr_unique_id = f"{entry.entry_id}_{preset['key']}"
        self._attr_name = preset["name"]
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Bondrucker",
            manufacturer="Bondrucker",
            model="ESC/POS Thermodrucker",
            configuration_url=entry.data[CONF_HOST],
        )

    async def async_press(self) -> None:
        host = self._entry.data[CONF_HOST].rstrip("/")
        api_key = self._entry.data[CONF_API_KEY]
        url = f"{host}/api/presets/{self._preset_key}/print"
        session = async_get_clientsession(self.hass)
        try:
            async with session.post(
                url,
                headers={"X-API-Key": api_key},
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT),
            ) as resp:
                if resp.status not in (200, 201):
                    body = await resp.text()
                    _LOGGER.error("Preset %s: HTTP %s – %s", self._preset_key, resp.status, body)
                    raise HomeAssistantError(
                        f"Druckauftrag fehlgeschlagen (HTTP {resp.status})"
                    )
        except aiohttp.ClientError as err:
            raise HomeAssistantError(f"Verbindungsfehler beim Drucken: {err}") from err
