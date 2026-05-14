"""Sensor platform for iTAG Tracker."""

import logging
from datetime import timedelta

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.const import PERCENTAGE, SIGNAL_STRENGTH_DECIBELS
from homeassistant.helpers.entity import Entity
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .ble_scanner import iTAGDevice

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=60)


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
    
    # Create iTAG device handler
    itag_device = iTAGDevice(hass, mac, name, entry.entry_id)
    hass.data[DOMAIN][entry.entry_id]["device"] = itag_device
    
    # Create entities
    entities = [
        iTAGBatterySensor(hass, entry, device, mac, itag_device),
        iTAGRSSISensor(hass, entry, device, mac, itag_device),
        iTAGButtonSensor(hass, entry, device, mac, itag_device),
    ]
    
    async_add_entities(entities, True)
    
    # Start device monitoring
    await itag_device.start()


class iTAGBatterySensor(SensorEntity):
    """Battery sensor for iTAG."""

    def __init__(self, hass, entry, device, mac, itag_device):
        super().__init__()
        self.hass = hass
        self._entry = entry
        self._device = device
        self._mac = mac
        self._itag_device = itag_device
        self._state = None
        self._attr_name = f"{self._entry.data['name']} Battery"
        self._attr_unique_id = f"{mac}_battery"
        self._attr_device_class = SensorDeviceClass.BATTERY
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_icon = "mdi:battery"
        
    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._mac)},
            "name": self._entry.data["name"],
            "manufacturer": "iTAG",
            "model": "BLE Tracker",
        }
    
    @property
    def native_value(self):
        return self._state
    
    async def async_update(self):
        """Update battery level."""
        self._state = self._itag_device.battery_level
        if self._state is not None:
            self._attr_extra_state_attributes = {
                "device_id": self._mac,
                "last_seen": self._itag_device.last_seen
            }


class iTAGRSSISensor(SensorEntity):
    """RSSI sensor for iTAG."""

    def __init__(self, hass, entry, device, mac, itag_device):
        super().__init__()
        self.hass = hass
        self._entry = entry
        self._device = device
        self._mac = mac
        self._itag_device = itag_device
        self._state = None
        self._attr_name = f"{self._entry.data['name']} RSSI"
        self._attr_unique_id = f"{mac}_rssi"
        self._attr_device_class = SensorDeviceClass.SIGNAL_STRENGTH
        self._attr_native_unit_of_measurement = SIGNAL_STRENGTH_DECIBELS
        
    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._mac)},
            "name": self._entry.data["name"],
        }
    
    @property
    def native_value(self):
        return self._state
    
    async def async_update(self):
        """Update RSSI level."""
        self._state = self._itag_device.rssi
        if self._state is not None:
            self._attr_extra_state_attributes = {
                "device_id": self._mac,
                "last_seen": self._itag_device.last_seen
            }


class iTAGButtonSensor(BinarySensorEntity):
    """Button sensor for iTAG."""

    def __init__(self, hass, entry, device, mac, itag_device):
        super().__init__()
        self.hass = hass
        self._entry = entry
        self._device = device
        self._mac = mac
        self._itag_device = itag_device
        self._state = False
        self._attr_name = f"{self._entry.data['name']} Button"
        self._attr_unique_id = f"{mac}_button"
        self._attr_icon = "mdi:gesture-tap-button"
        
    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._mac)},
            "name": self._entry.data["name"],
        }
    
    @property
    def is_on(self):
        return self._state
    
    async def async_update(self):
        """Update button state."""
        if self._itag_device.button_pressed:
            self._state = True
            self._attr_extra_state_attributes = {
                "device_id": self._mac,
                "last_seen": self._itag_device.last_seen,
                "button_event": "pressed"
            }
            # Reset after short delay (handled by device)
        else:
            self._state = False
            self._attr_extra_state_attributes = {
                "device_id": self._mac,
                "last_seen": self._itag_device.last_seen
            }