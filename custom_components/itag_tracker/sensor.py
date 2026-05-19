"""Sensors for iTAG - RSSI diagnostic."""
from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import SIGNAL_STRENGTH_DECIBELS
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import ITAGDataUpdateCoordinator
from .const import DOMAIN, RSSI_OFFLINE_VALUE


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up iTAG sensors based on a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    
    async_add_entities([ITAGRSSISensor(coordinator)])


class ITAGRSSISensor(CoordinatorEntity, SensorEntity):
    """Representation of iTAG RSSI sensor - diagnostic."""

    def __init__(self, coordinator: ITAGDataUpdateCoordinator) -> None:
        """Initialize the RSSI sensor."""
        super().__init__(coordinator)
        self.coordinator = coordinator
        self._attr_unique_id = f"{coordinator.device.mac}_rssi"
        self._attr_name = f"{coordinator.device.name} RSSI"
        self._attr_device_class = SensorDeviceClass.SIGNAL_STRENGTH
        self._attr_native_unit_of_measurement = SIGNAL_STRENGTH_DECIBELS
        self._attr_device_info = coordinator.device_info
        self._attr_icon = "mdi:signal"
        self._attr_entity_category = "diagnostic"  # RSSI в диагностике

    @property
    def native_value(self) -> int | None:
        """Return the RSSI value."""
        if not self.coordinator.data:
            return RSSI_OFFLINE_VALUE
        return self.coordinator.data.get("rssi", RSSI_OFFLINE_VALUE)

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.coordinator.last_update_success

    @callback
    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()
