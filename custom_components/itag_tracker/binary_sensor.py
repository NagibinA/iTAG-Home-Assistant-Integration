"""Бинарный сенсор для iTAG Tracker: кнопка."""

import logging
import asyncio
from datetime import datetime

from homeassistant.components.binary_sensor import BinarySensorEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    """Настройка сенсора кнопки iTAG."""
    mac = entry.data["mac_address"]
    name = entry.data["name"]
    tracker = hass.data[DOMAIN][entry.entry_id]["tracker"]

    button_sensor = iTAGButtonSensor(entry, mac, name, tracker)
    async_add_entities([button_sensor], True)
    
    # Устанавливаем callback от tracker
    async def button_callback():
        await button_sensor.async_update()
    
    tracker.set_button_callback(button_callback)


class iTAGButtonSensor(BinarySensorEntity):
    """Сенсор кнопки iTAG."""

    def __init__(self, entry, mac, name, tracker):
        self._entry = entry
        self._mac = mac
        self._name = name
        self._tracker = tracker
        self._attr_name = f"{name} Button"
        self._attr_unique_id = f"{mac}_button"
        self._attr_icon = "mdi:gesture-tap-button"
        self._attr_is_on = False
        self._last_press = None

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._mac)},
        }

    @property
    def extra_state_attributes(self):
        if self._last_press:
            return {"last_press": self._last_press}
        return {}

    async def async_update(self):
        """Обновление состояния кнопки."""
        pass

    def set_pressed(self):
        """Вызывается из tracker при нажатии кнопки."""
        self._attr_is_on = True
        self._last_press = datetime.now().isoformat()
        _LOGGER.info(f"{self._name} button pressed")
        self.async_write_ha_state()
        
        async def reset():
            await asyncio.sleep(1)
            self._attr_is_on = False
            self.async_write_ha_state()
        
        asyncio.create_task(reset())