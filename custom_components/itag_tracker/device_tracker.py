"""Device tracker for iTAG."""
from __future__ import annotations

import logging
from homeassistant.components.device_tracker import SourceType, TrackerEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import ITAGDataUpdateCoordinator
from .const import DOMAIN, RSSI_PRESENCE_THRESHOLD, RSSI_ABSENT_THRESHOLD

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

    @property
    def source_type(self) -> SourceType:
        """Return the source type."""
        return SourceType.BLUETOOTH

    @property
    def icon(self) -> str:
        """Return icon based on connection state."""
        if self.is_connected:
            return "mdi:bluetooth"
        return "mdi:bluetooth-off"

    @property
    def latitude(self) -> float | None:
        return None

    @property
    def longitude(self) -> float | None:
        return None

    @property
    def location_name(self) -> str | None:
        return None

    @property
    def should_poll(self) -> bool:
        return False

    @property
    def available(self) -> bool:
        """Всегда True, чтобы не было unavailable."""
        return True

    @property
    def is_connected(self) -> bool:
        """Return true if device is considered home."""
        if not self.coordinator.data:
            _LOGGER.debug("No coordinator data, assuming not home")
            return False
        
        rssi = self.coordinator.data.get("rssi")
        _LOGGER.debug("Presence check - RSSI: %s", rssi)
        
        if rssi is None:
            _LOGGER.debug("No RSSI, assuming not home")
            return False
        
        # RSSI >= -85 → дома
        if rssi >= RSSI_PRESENCE_THRESHOLD:
            _LOGGER.debug("RSSI %s >= %s → home", rssi, RSSI_PRESENCE_THRESHOLD)
            return True
        
        # RSSI < -95 → не дома
        if rssi < RSSI_ABSENT_THRESHOLD:
            _LOGGER.debug("RSSI %s < %s → not home", rssi, RSSI_ABSENT_THRESHOLD)
            return False
        
        # -95 <= RSSI < -85 → пограничная зона, считаем что не дома
        _LOGGER.debug("RSSI %s in border zone (%s to %s) → not home", 
                      rssi, RSSI_ABSENT_THRESHOLD, RSSI_PRESENCE_THRESHOLD)
        return False

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()
