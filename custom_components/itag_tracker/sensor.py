"""Sensors for iTAG."""
from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, SIGNAL_STRENGTH_DECIBELS
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import ITAGDataUpdateCoordinator
from .const import DOMAIN
from .icons import get_icon


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up iTAG sensors based on a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    
    entities = [
        ITAGRSSISensor(coordinator),
        ITAGBatterySensor(coordinator),
        ITAGButtonSensor(coordinator),
    ]
    
    async_add_entities(entities)


class ITAGRSSISensor(CoordinatorEntity, SensorEntity):
    """Representation of iTAG RSSI sensor."""

    def __init__(self, coordinator: ITAGDataUpdateCoordinator) -> None:
        """Initialize the RSSI sensor."""
        super().__init__(coordinator)
        self.coordinator = coordinator
        self._attr_unique_id = f"{coordinator.device.mac}_rssi"
        self._attr_name = f"{coordinator.device.name} RSSI"
        self._attr_device_class = SensorDeviceClass.SIGNAL_STRENGTH
        self._attr_native_unit_of_measurement = SIGNAL_STRENGTH_DECIBELS
        self._attr_device_info = coordinator.device_info

    @property
    def native_value(self) -> int | None:
        """Return the RSSI value."""
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get("rssi")
    
    @property
    def icon(self) -> str:
        """Return icon for RSSI."""
        return get_icon("rssi_sensor", self.native_value)

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.coordinator.last_update_success

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()


class ITAGBatterySensor(CoordinatorEntity, SensorEntity):
    """Representation of iTAG battery sensor."""

    def __init__(self, coordinator: ITAGDataUpdateCoordinator) -> None:
        """Initialize the battery sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.device.mac}_battery"
        self._attr_name = f"{coordinator.device.name} Battery"
        self._attr_device_class = SensorDeviceClass.BATTERY
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_device_info = coordinator.device_info

    @property
    def native_value(self) -> int | None:
        """Return the battery level."""
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get("battery")
    
    @property
    def icon(self) -> str:
        """Return icon for battery level."""
        return get_icon("battery_sensor", self.native_value)

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.coordinator.last_update_success and self.coordinator.data and self.coordinator.data.get("battery") is not None

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()


class ITAGButtonSensor(CoordinatorEntity, SensorEntity):
    """Representation of iTAG button sensor."""

    def __init__(self, coordinator: ITAGDataUpdateCoordinator) -> None:
        """Initialize the button sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.device.mac}_button"
        self._attr_name = f"{coordinator.device.name} Button"
        self._attr_device_info = coordinator.device_info

    @property
    def native_value(self) -> str:
        """Return the button state."""
        if not self.coordinator.data:
            return "unknown"
        return "pressed" if self.coordinator.data.get("button_pressed") else "normal"
    
    @property
    def icon(self) -> str:
        """Return icon for button."""
        return get_icon("button_sensor")

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.coordinator.last_update_success

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()
