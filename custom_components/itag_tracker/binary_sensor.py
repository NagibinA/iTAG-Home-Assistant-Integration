"""Бинарный сенсор кнопки для iTAG."""

import asyncio
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.helpers import device_registry as dr

from .const import DOMAIN


async def async_setup_entry(hass, entry, async_add_entities):
    """Настройка сенсора кнопки."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    sensor = iTAGButtonSensor(coordinator, entry)
    coordinator.set_button_callback(sensor.trigger_button_press)
    async_add_entities([sensor], True)


class iTAGButtonSensor(BinarySensorEntity):
    """Сенсор кнопки iTAG."""

    _attr_should_poll = False
    _attr_device_class = "button"

    def __init__(self, coordinator, entry):
        self.coordinator = coordinator
        self.entry = entry
        self._attr_name = f"{entry.data['name']} Button"
        self._attr_unique_id = f"{coordinator.mac_normalized}_button"
        self._attr_is_on = False

    @property
    def device_info(self):
        """Привязка к устройству."""
        return {
            "identifiers": {(DOMAIN, self.coordinator.mac_normalized)},
        }

    async def trigger_button_press(self):
        """Вызывается при нажатии кнопки."""
        self._attr_is_on = True
        self.async_write_ha_state()
        await asyncio.sleep(1)
        self._attr_is_on = False
        self.async_write_ha_state()

    async def async_added_to_hass(self):
        """При добавлении в Home Assistant."""
        await super().async_added_to_hass()
        self.async_on_remove(
            self.coordinator.async_add_listener(self._handle_update)
        )

    def _handle_update(self):
        """Обновление состояния."""
        self.async_write_ha_state()
