"""iTAG BLE integration - advertisement only."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_MAC, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN
from .device import ITAGDevice

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=30)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up iTAG from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    mac = entry.data[CONF_MAC]
    name = entry.data[CONF_NAME]

    device = ITAGDevice(hass, mac, name)
    coordinator = ITAGDataUpdateCoordinator(hass, device, name)

    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "device": device,
    }

    await hass.config_entries.async_forward_entry_setups(entry, ["device_tracker", "sensor"])

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, ["device_tracker", "sensor"]):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


class ITAGDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching iTAG data."""

    def __init__(self, hass: HomeAssistant, device: ITAGDevice, name: str) -> None:
        """Initialize."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"{name} Coordinator",
            update_interval=SCAN_INTERVAL,
        )
        self.device = device
        self.device_info = DeviceInfo(
            identifiers={(DOMAIN, device.mac)},
            name=name,
            manufacturer="iTAG",
            model="iTAG BLE Tracker",
        )

    async def _async_update_data(self) -> dict:
        """Fetch data from iTAG."""
        try:
            data = await self.device.update()
            return data
        except Exception as error:
            raise UpdateFailed(f"Error communicating with device: {error}") from error
