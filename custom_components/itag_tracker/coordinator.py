"""Координатор для iTAG — через HA Bluetooth API (исправлен)."""

import logging
from datetime import timedelta

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.components.bluetooth import async_get_scanner

from .const import DOMAIN, SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)


class iTAGDataUpdateCoordinator(DataUpdateCoordinator):
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
        _LOGGER.info("=== iTAG DEBUG: Using HA Bluetooth Scanner ===")
        
        try:
            scanner = async_get_scanner(self.hass)
            
            if not scanner:
                _LOGGER.error("Bluetooth scanner not available!")
                return {"rssi": None}
            
            _LOGGER.info("Scanner found, looking for %s...", self.mac)
            
            # Правильный способ: перебираем discovered_devices
            found = False
            for device in scanner.discovered_devices:
                _LOGGER.debug("HA Scanner sees: %s", device.address)
                if device.address.lower() == self.mac:
                    # Получаем advertisement_data для этого устройства
                    adv_data = scanner.discovered_devices_and_advertisement_data.get(device.address)
                    if adv_data:
                        self.rssi = adv_data.rssi
                        self.is_available = True
                        found = True
                        _LOGGER.info("✅ FOUND %s via HA Scanner! RSSI: %s dBm", self.name, self.rssi)
                        break
            
            if not found:
                _LOGGER.warning("❌ %s not found in HA Scanner", self.name)
                self.rssi = None
                self.is_available = False
            
            return {"rssi": self.rssi}
                
        except Exception as e:
            _LOGGER.error("❌ ERROR: %s", e)
            self.is_available = False
            return {"rssi": None}
