"""Координатор для iTAG — показываем всё содержимое."""

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
        _LOGGER.info("=== iTAG DEBUG ===")
        
        try:
            scanner = async_get_scanner(self.hass)
            
            if not scanner:
                _LOGGER.error("Bluetooth scanner not available!")
                return {"rssi": None}
            
            if not hasattr(scanner, 'discovered_devices'):
                _LOGGER.warning("No discovered_devices")
                return {"rssi": None}
            
            for item in scanner.discovered_devices:
                # Выводим ВСЮ информацию об элементе
                _LOGGER.info("ITEM: %s", item)
                _LOGGER.info("ITEM type: %s", type(item))
                _LOGGER.info("ITEM dir: %s", [a for a in dir(item) if not a.startswith('_')])
                
                # Пробуем получить адрес разными способами
                address = None
                if hasattr(item, 'address'):
                    address = item.address
                    _LOGGER.info("  has address: %s", address)
                if hasattr(item, 'device') and hasattr(item.device, 'address'):
                    address = item.device.address
                    _LOGGER.info("  has device.address: %s", address)
                if isinstance(item, tuple) and len(item) > 0:
                    address = str(item[0])
                    _LOGGER.info("  tuple[0]: %s", address)
                
                if address and address.lower() == self.mac:
                    _LOGGER.info("✅ MATCH found for %s!", self.mac)
                    
                    # Пробуем получить RSSI
                    if hasattr(item, 'rssi'):
                        self.rssi = item.rssi
                        _LOGGER.info("  item.rssi: %s", self.rssi)
                    if hasattr(item, 'device') and hasattr(item.device, 'rssi'):
                        self.rssi = item.device.rssi
                        _LOGGER.info("  item.device.rssi: %s", self.rssi)
                    if isinstance(item, tuple) and len(item) > 1:
                        self.rssi = item[1]
                        _LOGGER.info("  tuple[1]: %s", self.rssi)
                    
                    if self.rssi is not None:
                        self.is_available = True
                        _LOGGER.info("✅ RSSI extracted: %s dBm", self.rssi)
                    else:
                        _LOGGER.warning("RSSI not found in item")
                    break
            else:
                _LOGGER.debug("Device %s not found in scanner", self.mac)
            
            return {"rssi": self.rssi}
                
        except Exception as e:
            _LOGGER.error("ERROR: %s", e)
            import traceback
            _LOGGER.error(traceback.format_exc())
            return {"rssi": None}
