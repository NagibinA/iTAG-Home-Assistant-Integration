"""Бинарный сенсор кнопки для iTAG."""

import asyncio
import logging

from homeassistant.components.binary_sensor import BinarySensorEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    """Настройка сенсора кнопки."""
    tracker = hass.data[DOMAIN][entry.entry_id]["tracker"]
    sensor = iTAGButtonSensor(tracker, entry)
    tracker.set_button_callback(sensor.trigger_button_press)
    async_add_entities([sensor], True)


class iTAGButtonSensor(BinarySensorEntity):
    """Сенсор кнопки."""

    def __init__(self, tracker, entry):
        self._tracker = tracker
        self._entry = entry
        self._attr_name = f"{entry.data['name']} Button"
        self._attr_unique_id = f"{entry.data['mac_address'].replace(':', '')}_button"
        self._attr_device_class = "button"
        self._attr_is_on = False

    async def trigger_button_press(self):
        """Вызывается при нажатии кнопки."""
        self._attr_is_on = True
        self.async_write_ha_state()
        await asyncio.sleep(1)
        self._attr_is_on = False
        self.async_write_ha_state()
