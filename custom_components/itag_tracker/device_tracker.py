"""Device tracker для iTAG."""

import logging
from typing import Any, Mapping

from homeassistant.components.device_tracker import SourceType
from homeassistant.components.device_tracker.config_entry import BaseTrackerEntity
from homeassistant.const import STATE_HOME, STATE_NOT_HOME
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
    """Load Device Tracker entities."""
    coordinator: iTAGDataUpdateCoordinator = entry.runtime_data
    async_add_entities([iTAGDeviceTracker(coordinator, entry)])


class iTAGDeviceTracker(BaseTrackerEntity):
    """Trackable iTAG Device."""

    _attr_should_poll = False
    _attr_has_entity_name = True
    _attr_name = None

    def __init__(self, coordinator: iTAGDataUpdateCoordinator, entry: ConfigEntry) -> None:
        """Initialize the tracker."""
        self.coordinator = coordinator
        self.entry = entry
        self._attr_unique_id = f"{coordinator.mac_normalized}_tracker"

    @property
    def device_info(self):
        """Return device info (только identifiers!)."""
        return self.coordinator.device_info

    @property
    def state(self) -> str:
        """Return the state of the device."""
        return STATE_HOME if self.coordinator.is_present else STATE_NOT_HOME

    @property
    def source_type(self) -> SourceType:
        """Return the source type."""
        return SourceType.BLUETOOTH_LE

    @property
    def extra_state_attributes(self) -> Mapping[str, Any]:
        """Return extra state attributes."""
        attrs = {}
        if self.coordinator.rssi is not None:
            attrs["rssi"] = self.coordinator.rssi
        if self.coordinator.battery is not None:
            attrs["battery"] = self.coordinator.battery
        if self.coordinator.last_seen is not None:
            attrs["last_seen"] = self.coordinator.last_seen
        return attrs

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success

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
