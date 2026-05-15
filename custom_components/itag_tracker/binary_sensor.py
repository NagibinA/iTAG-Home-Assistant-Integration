"""Бинарный сенсор кнопки для iTAG."""

import asyncio
import logging

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import iTAGDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up button sensor."""
    coordinator: iTAGDataUpdateCoordinator = entry.runtime_data
    sensor = iTAGButtonSensor(coordinator)
    coordinator.set_button_callback(sensor.trigger_button_press)
    async_add_entities([sensor])


class iTAGButtonSensor(BinarySensorEntity):
    """Button sensor for iTAG."""

    _attr_should_poll = False
    _attr_device_class = "button"

    def __init__(self, coordinator: iTAGDataUpdateCoordinator) -> None:
        """Initialize the sensor."""
        self.coordinator = coordinator
        self._attr_unique_id = f"{coordinator.mac_normalized}_button"
        self._attr_name = f"{coordinator.name} Button"
        self._attr_is_on = False

    @property
    def device_info(self):
        """Return device info (только identifiers!)."""
        return self.coordinator.device_info

    async def trigger_button_press(self) -> None:
        """Called when button is pressed."""
        self._attr_is_on = True
        self.async_write_ha_state()
        await asyncio.sleep(1)
        self._attr_is_on = False
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()
