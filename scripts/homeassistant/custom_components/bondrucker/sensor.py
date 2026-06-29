from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_HOST, DOMAIN
from .coordinator import BondruckerStatusCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: BondruckerStatusCoordinator = hass.data[DOMAIN][entry.entry_id][
        "status_coordinator"
    ]
    async_add_entities(
        [
            BondruckerOnlineSensor(coordinator, entry),
            BondruckerQueueSensor(coordinator, entry),
            BondruckerCurrentJobSensor(coordinator, entry),
        ]
    )


def _device_info(entry: ConfigEntry) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name="Bondrucker",
        manufacturer="Bondrucker",
        model="ESC/POS Thermodrucker",
        configuration_url=entry.data[CONF_HOST],
    )


class BondruckerOnlineSensor(CoordinatorEntity[BondruckerStatusCoordinator], SensorEntity):
    """Printer connectivity state."""

    _attr_has_entity_name = True
    _attr_name = "Drucker Status"
    _attr_icon = "mdi:printer-check"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = ["verbunden", "getrennt"]
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: BondruckerStatusCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_online"
        self._attr_device_info = _device_info(entry)

    @property
    def native_value(self) -> str | None:
        if self.coordinator.data is None:
            return None
        return "verbunden" if self.coordinator.data.get("online") else "getrennt"


class BondruckerQueueSensor(CoordinatorEntity[BondruckerStatusCoordinator], SensorEntity):
    """Number of jobs waiting in the queue."""

    _attr_has_entity_name = True
    _attr_name = "Warteschlange"
    _attr_icon = "mdi:printer-pos"
    _attr_native_unit_of_measurement = "Jobs"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: BondruckerStatusCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_queue_length"
        self._attr_device_info = _device_info(entry)

    @property
    def native_value(self) -> int | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get("queue_length")


class BondruckerCurrentJobSensor(CoordinatorEntity[BondruckerStatusCoordinator], SensorEntity):
    """ID of the job currently being printed."""

    _attr_has_entity_name = True
    _attr_name = "Aktueller Druckauftrag"
    _attr_icon = "mdi:file-document-outline"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: BondruckerStatusCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_current_job"
        self._attr_device_info = _device_info(entry)

    @property
    def native_value(self) -> str | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get("current_job") or "inaktiv"
