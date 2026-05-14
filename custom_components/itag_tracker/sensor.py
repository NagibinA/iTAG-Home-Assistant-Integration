"""Sensor platform for iTAG Tracker."""

import logging
from datetime import datetime

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.const import PERCENTAGE, SIGNAL_STRENGTH_DECIBELS
from homeassistant.helpers import device_registry as dr

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up iTAG sensors."""
    mac = entry.data["mac_address"]
    name = entry.data["name"]
    
    # Create device
    device_registry = dr.async_get(hass)
    device = device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, mac)},
        name=name,
        manufacturer="iTAG",
        model="BLE Tracker",
        sw_version="1.0",
        connections={(dr.CONNECTION_BLUETOOTH, mac)},
    )
    
    # Create entities
    entities = [
        iTAGBatterySensor(entry, mac, name),
        iTAGButtonSensor(entry, mac, name),
    ]
    
    async_add_entities(entities, True)


class iTAGBatterySensor(SensorEntity):
    """Battery sensor for iTAG."""

    def __init__(self, entry, mac, name):
        super().__init__()
        self._entry = entry
        self._mac = mac
        self._attr_name = f"{name} Battery"
        self._attr_unique_id = f"{mac}_battery"
        self._attr_device_class = SensorDeviceClass.BATTERY
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_icon = "mdi:battery"
        self._attr_native_value = 100  # Demo value
        
    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._mac)},
            "name": self._entry.data["name"],
            "manufacturer": "iTAG",
            "model": "BLE Tracker",
        }
    
    async def async_update(self):
        """Update battery level."""
        # TODO: Implement actual BLE reading
        # For now, keep demo value
        pass


class iTAGButtonSensor(BinarySensorEntity):
    """Button sensor for iTAG."""

    def __init__(self, entry, mac, name):
        super().__init__()
        self._entry = entry
        self._mac = mac
        self._attr_name = f"{name} Button"
        self._attr_unique_id = f"{mac}_button"
        self._attr_icon = "mdi:gesture-tap-button"
        self._attr_is_on = False
        
    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._mac)},
            "name": self._entry.data["name"],
        }
    
    async def async_update(self):
        """Update button state."""
        # TODO: Implement actual BLE button detection
        pass