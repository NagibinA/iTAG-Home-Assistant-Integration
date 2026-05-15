"""Сенсор батареи для iTAG."""

import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import PERCENTAGE
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
    """Set up battery sensor."""
    coordinator: iTAGDataUpdateCoordinator = entry.runtime_data
    async_add_entities([iTAGBatterySensor(coordinator)])


class iTAGBatterySensor(SensorEntity):
    """Battery sensor for iTAG."""

    _attr_should_poll = False
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_device_class = "battery"

    def __init__(self, coordinator: iTAGDataUpdateCoordinator) -> None:
        """Initialize the sensor."""
        self.coordinator = coordinator
        self._attr_unique_id = f"{coordinator.mac_normalized}_battery"
        self._attr_name = f"{coordinator.name} Battery"

    @property
    def device_info(self):
        """Return device info (только identifiers!)."""
        return self.coordinator.device_info

    @property
    def native_value(self) -> int | None:
        """Return battery level."""
        return self.coordinator.battery

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success and self.coordinator.battery is not None

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()
        self.async_on_remove(
            self.coordinator.async_add_listener(self._handle_coordinator_update)
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()
