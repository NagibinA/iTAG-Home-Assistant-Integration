"""Device tracker for iTAG - based on advertisements only."""
from __future__ import annotations

import logging
from homeassistant.components.device_tracker import ScannerEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import ITAGDataUpdateCoordinator
from .const import DOMAIN, RSSI_OFFLINE_VALUE, RSSI_PRESENCE_THRESHOLD

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up iTAG device tracker based on a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    
    async_add_entities([ITAGDeviceTracker(coordinator)])


class ITAGDeviceTracker(CoordinatorEntity, ScannerEntity):
    """Representation of iTAG device tracker."""

    def __init__(self, coordinator: ITAGDataUpdateCoordinator) -> None:
        """Initialize the tracker."""
        super().__init__(coordinator)
        self.coordinator = coordinator
        self._attr_unique_id = f"{coordinator.device.mac}_tracker"
        self._attr_name = f"{coordinator.device.name} Присутствие"
        self._attr_device_info = coordinator.device_info
        self._attr_icon = "mdi:bluetooth"

    @property
    def is_connected(self) -> bool:
        """Return true if device is advertising (RSSI above threshold)."""
        if not self.coordinator.data:
            return False
        
        rssi = self.coordinator.data.get("rssi", RSSI_OFFLINE_VALUE)
        
        if rssi > RSSI_PRESENCE_THRESHOLD:
            return True
        return False

    @property
    def should_poll(self) -> bool:
        return False

    @property
    def available(self) -> bool:
        return True

    @callback
    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()
