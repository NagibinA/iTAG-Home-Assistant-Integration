"""Device tracker for iTAG: presence and RSSI."""

import logging
from datetime import datetime, timedelta

from homeassistant.components.device_tracker import SourceType
from homeassistant.components.device_tracker.config_entry import ScannerEntity
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.event import async_track_time_interval
from bleak import BleakScanner

from .const import DOMAIN, PRESENCE_SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up iTAG device tracker."""
    mac = entry.data["mac_address"]
    name = entry.data["name"]

    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, mac)},
        name=name,
        manufacturer="iTAG",
        model="BLE Tracker",
        connections={(dr.CONNECTION_BLUETOOTH, mac)},
    )

    tracker = iTAGDeviceTracker(entry, mac, name)
    async_add_entities([tracker], True)

    async def scan(now):
        await tracker.async_update()

    async_track_time_interval(hass, scan, timedelta(seconds=PRESENCE_SCAN_INTERVAL))
    await tracker.async_update()


class iTAGDeviceTracker(ScannerEntity):
    """Track iTAG presence by RSSI."""

    def __init__(self, entry, mac, name):
        self._entry = entry
        self._mac = mac.lower()
        self._name = name
        self._attr_name = name
        self._attr_unique_id = f"{mac}_tracker"
        self._is_home = False
        self._rssi = None
        self._last_seen = None

    @property
    def is_connected(self):
        return self._is_home

    @property
    def source_type(self):
        return SourceType.BLUETOOTH

    @property
    def extra_state_attributes(self):
        attrs = {}
        if self._rssi is not None:
            attrs["rssi"] = self._rssi
            attrs["rssi_dbm"] = f"{self._rssi} dBm"
        if self._last_seen:
            attrs["last_seen"] = self._last_seen
        return attrs

    async def async_update(self):
        """Passive scan - no connection, no beeping."""
        try:
            device = await BleakScanner.find_device_by_address(self._mac)

            if device:
                self._rssi = device.rssi
                self._last_seen = datetime.now().isoformat()
                self._is_home = device.rssi > -80

                _LOGGER.debug(
                    f"{self._name} RSSI: {device.rssi} dBm, home: {self._is_home}"
                )
            else:
                self._is_home = False
                self._rssi = None
                _LOGGER.debug(f"{self._name} not found")

        except Exception as e:
            _LOGGER.debug(f"Scan error for {self._name}: {e}")
            self._is_home = False