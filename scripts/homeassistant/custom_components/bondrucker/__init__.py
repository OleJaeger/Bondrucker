from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import DOMAIN
from .coordinator import BondruckerPresetCoordinator, BondruckerStatusCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.BUTTON, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    status_coordinator = BondruckerStatusCoordinator(hass, entry.data)
    preset_coordinator = BondruckerPresetCoordinator(hass, entry.data)

    try:
        await status_coordinator.async_config_entry_first_refresh()
        await preset_coordinator.async_config_entry_first_refresh()
    except Exception as err:
        raise ConfigEntryNotReady(f"Bondrucker nicht erreichbar: {err}") from err

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "status_coordinator": status_coordinator,
        "preset_coordinator": preset_coordinator,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
