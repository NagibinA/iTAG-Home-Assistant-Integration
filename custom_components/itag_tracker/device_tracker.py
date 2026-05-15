"""Device tracker for iTAG."""
from __future__ import annotations

import logging
from homeassistant.components.device_tracker import SourceType, TrackerEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import ITAGDataUpdateCoordinator
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up iTAG device tracker based on a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    
    async_add_entities([ITAGDeviceTracker(coordinator)])


class ITAGDeviceTracker(CoordinatorEntity, TrackerEntity):
    """Representation of iTAG device tracker."""

    def __init__(self, coordinator: ITAGDataUpdateCoordinator) -> None:
        """Initialize the tracker."""
        super().__init__(coordinator)
        self.coordinator = coordinator
        self._attr_unique_id = f"{coordinator.device.mac}_tracker"
        self._attr_name = f"{coordinator.device.name} Presence"
        self._attr_device_info = coordinator.device_info
        self._attr_should_poll = False

    @property
    def source_type(self) -> SourceType:
        """Return the source type."""
        return SourceType.BLUETOOTH

    @property
    def icon(self) -> str:
        """Return icon."""
        return "mdi:bluetooth"

    @property
    def location_name(self) -> str | None:
        """Return location name."""
        if not self.coordinator.data:
            return None
        
        rssi = self.coordinator.data.get("rssi")
        _LOGGER.debug("Presence check - RSSI: %s", rssi)
        
        if rssi is None:
            return "not_home"
        
        # RSSI >= -85 → дома
        if rssi >= -85:
            _LOGGER.debug("RSSI %s >= -85 → home", rssi)
            return "home"
        
        # RSSI < -85 → не дома
        _LOGGER.debug("RSSI %s < -85 → not_home", rssi)
        return "not_home"

    @property
    def should_poll(self) -> bool:
        """No polling needed."""
        return False

    @property
    def available(self) -> bool:
        """Always available."""
        return True

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()
