"""Бинарный сенсор для iTAG Tracker: кнопка."""

import logging
import asyncio
from datetime import datetime

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.helpers import device_registry as dr

from .const import DOMAIN, BUTTON_CHAR

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    """Настройка сенсора кнопки iTAG."""
    mac = entry.data["mac_address"]
    name = entry.data["name"]

    async_add_entities([iTAGButtonSensor(entry, mac, name)], True)


class iTAGButtonSensor(BinarySensorEntity):
    """Сенсор кнопки iTAG."""

    def __init__(self, entry, mac, name):
        self._entry = entry
        self._mac = mac
        self._name = name
        self._attr_name = f"{name} Button"
        self._attr_unique_id = f"{mac}_button"
        self._attr_icon = "mdi:gesture-tap-button"
        self._attr_is_on = False
        self._last_press = None

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._mac)},
            "name": self._name,
        }

    @property
    def extra_state_attributes(self):
        if self._last_press:
            return {"last_press": self._last_press}
        return {}

    async def async_update(self):
        """Проверка нажатия кнопки."""
        try:
            from bleak import BleakClient

            async with BleakClient(self._mac, timeout=3.0) as client:
                await client.start_notify(BUTTON_CHAR, self._button_handler)
                await asyncio.sleep(0.3)
                await client.stop_notify(BUTTON_CHAR)

        except Exception:
            pass  # Тихая ошибка, не спамим лог

    def _button_handler(self, sender, data):
        """Обработчик нажатия кнопки."""
        if len(data) > 0 and data[0] == 0x01:
            self._attr_is_on = True
            self._last_press = datetime.now().isoformat()
            _LOGGER.info(f"{self._name} button pressed")

            async def reset():
                await asyncio.sleep(1)
                self._attr_is_on = False
                self.async_write_ha_state()

            asyncio.create_task(reset())
            self.async_write_ha_state()