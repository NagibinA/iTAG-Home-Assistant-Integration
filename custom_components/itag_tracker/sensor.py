"""Сенсор батареи для iTAG."""

import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import PERCENTAGE

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    """Настройка сенсора батареи."""
    tracker = hass.data[DOMAIN][entry.entry_id]["tracker"]
    async_add_entities([iTAGBatterySensor(tracker, entry)], True)


class iTAGBatterySensor(SensorEntity):
    """Сенсор батареи."""

    def __init__(self, tracker, entry):
        self._tracker = tracker
        self._entry = entry
        self._attr_name = f"{entry.data['name']} Battery"
        self._attr_unique_id = f"{entry.data['mac_address'].replace(':', '')}_battery"
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_device_class = "battery"

    @property
    def native_value(self):
        return self._tracker.get_battery()

    @property
    def available(self):
        return self._tracker.get_battery() is not None
