"""Координатор для iTAG — диагностика структуры данных."""

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
        _LOGGER.info("=== iTAG DEBUG: Scanning ===")
        
        try:
            scanner = async_get_scanner(self.hass)
            
            if not scanner:
                _LOGGER.error("Bluetooth scanner not available!")
                return {"rssi": None}
            
            _LOGGER.info("Scanner type: %s", type(scanner))
            
            # Проверяем все возможные атрибуты
            if hasattr(scanner, 'discovered_devices'):
                devices = scanner.discovered_devices
                _LOGGER.info("discovered_devices type: %s, length: %s", type(devices), len(devices) if devices else 0)
                
                for item in devices:
                    _LOGGER.debug("Item type: %s", type(item))
                    _LOGGER.debug("Item: %s", item)
                    
                    # Пробуем получить адрес
                    address = None
                    if hasattr(item, 'address'):
                        address = item.address
                    elif hasattr(item, 'device') and hasattr(item.device, 'address'):
                        address = item.device.address
                    elif isinstance(item, tuple) and len(item) > 0:
                        address = str(item[0])
                    
                    if address and address.lower() == self.mac:
                        _LOGGER.info("✅ Found matching device!")
                        
                        # Пробуем получить RSSI
                        rssi = None
                        if hasattr(item, 'rssi'):
                            rssi = item.rssi
                        elif hasattr(item, 'device') and hasattr(item.device, 'rssi'):
                            rssi = item.device.rssi
                        elif isinstance(item, tuple) and len(item) > 1:
                            rssi = item[1]
                        
                        if rssi is not None:
                            self.rssi = rssi
                            self.is_available = True
                            _LOGGER.info("✅ RSSI: %s dBm", self.rssi)
                        else:
                            _LOGGER.warning("Could not extract RSSI from item")
                        break
                else:
                    _LOGGER.warning("Device not found")
            else:
                _LOGGER.warning("No discovered_devices attribute")
            
            return {"rssi": self.rssi}
                
        except Exception as e:
            _LOGGER.error("❌ ERROR: %s", e)
            import traceback
            _LOGGER.error(traceback.format_exc())
            self.is_available = False
            return {"rssi": None}
