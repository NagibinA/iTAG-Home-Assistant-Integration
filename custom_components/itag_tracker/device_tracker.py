"""Device tracker for iTAG."""
from __future__ import annotations

from homeassistant.components.device_tracker import SourceType, TrackerEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import ITAGDataUpdateCoordinator
from .const import DOMAIN, RSSI_PRESENCE_THRESHOLD


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
        """Return true if device is connected (RSSI above threshold)."""
        if not self.coordinator.data:
            return False
        rssi = self.coordinator.data.get("rssi")
        if rssi is None:
            return False
        return rssi > RSSI_PRESENCE_THRESHOLD

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()
