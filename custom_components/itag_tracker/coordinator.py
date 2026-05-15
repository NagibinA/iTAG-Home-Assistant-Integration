"""Координатор для iTAG — только RSSI."""

import logging
from datetime import timedelta

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from bleak import BleakScanner

from .const import DOMAIN, SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)


class iTAGDataUpdateCoordinator(DataUpdateCoordinator):
    """Координатор для получения RSSI."""

    def __init__(self, hass, entry):
        super().__init__(
            hass,
            _LOGGER,
            name=entry.data["name"],
            update_interval=timedelta(seconds=SCAN_INTERVAL),
        )
        self.entry = entry
        self.mac = entry.data["mac_address"].lower()
        self.name = entry.data["name"]
        self.rssi = None
        self.is_available = False

    async def _async_update_data(self):
        """Поиск устройства и получение RSSI."""
        _LOGGER.info("Scanning for %s (%s)...", self.name, self.mac)
        
        try:
            device = await BleakScanner.find_device_by_address(self.mac, timeout=5)
            
            if device:
                self.rssi = device.rssi
                self.is_available = True
                _LOGGER.info("%s found! RSSI: %s dBm", self.name, device.rssi)
                return {"rssi": self.rssi}
            else:
                self.rssi = None
                self.is_available = False
                _LOGGER.debug("%s not found", self.name)
                return {"rssi": None}
                
        except Exception as e:
            _LOGGER.error("Error scanning for %s: %s", self.name, e)
            self.is_available = False
            return {"rssi": None}
