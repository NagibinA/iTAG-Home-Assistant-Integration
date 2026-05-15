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

# Пороги присутствия
PRESENT_THRESHOLD = -85   # RSSI >= -85 → дома
ABSENT_THRESHOLD = -95    # RSSI < -95 → не дома


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
        self._prev_state = None

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
        """Return latitude (not used for BLE)."""
        return None

    @property
    def longitude(self) -> float | None:
        """Return longitude (not used for BLE)."""
        return None

    @property
    def location_name(self) -> str | None:
        """Return location name."""
        return None

    @property
    def should_poll(self) -> bool:
        """No polling needed."""
        return False

    @property
    def available(self) -> bool:
        """Return True if device is available."""
        return self.coordinator.data.get("available", False) if self.coordinator.data else False

    @property
    def is_connected(self) -> bool:
        """Return true if device is considered home."""
        if not self.coordinator.data:
            return False
        
        rssi = self.coordinator.data.get("rssi")
        if rssi is None:
            return False
        
        # RSSI >= -85 → дома
        if rssi >= PRESENT_THRESHOLD:
            _LOGGER.debug("RSSI %s >= %s → home", rssi, PRESENT_THRESHOLD)
            return True
        
        # RSSI < -95 → не дома
        if rssi < ABSENT_THRESHOLD:
            _LOGGER.debug("RSSI %s < %s → not home", rssi, ABSENT_THRESHOLD)
            return False
        
        # -95 <= RSSI < -85 → пограничная зона, возвращаем предыдущее состояние
        _LOGGER.debug("RSSI %s in border zone (%s to %s), keeping previous state: %s", 
                      rssi, ABSENT_THRESHOLD, PRESENT_THRESHOLD, self._prev_state)
        return self._prev_state if self._prev_state is not None else False

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        # Сохраняем предыдущее состояние перед обновлением
        self._prev_state = self.is_connected
        self.async_write_ha_state()
