"""Координатор для iTAG — выводим все атрибуты."""

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
                # Получаем адрес
                address = None
                if hasattr(item, 'address'):
                    address = item.address
                elif hasattr(item, 'device') and hasattr(item.device, 'address'):
                    address = item.device.address
                elif isinstance(item, tuple) and len(item) > 0:
                    address = str(item[0])
                
                if address and address.lower() == self.mac:
                    _LOGGER.info("✅ MATCH found for %s!", self.mac)
                    _LOGGER.info("FULL ITEM: %s", item)
                    _LOGGER.info("ITEM TYPE: %s", type(item))
                    
                    # Выводим ВСЕ атрибуты
                    attrs = [a for a in dir(item) if not a.startswith('_')]
                    _LOGGER.info("ALL ATTRIBUTES: %s", attrs)
                    
                    # Для каждого атрибута выводим значение
                    for attr in attrs:
                        try:
                            value = getattr(item, attr)
                            _LOGGER.info("  .%s = %s (type: %s)", attr, value, type(value))
                        except Exception as e:
                            _LOGGER.info("  .%s = ERROR: %s", attr, e)
                    
                    # Если это tuple, выводим все элементы
                    if isinstance(item, tuple):
                        for i, val in enumerate(item):
                            _LOGGER.info("  tuple[%s] = %s (type: %s)", i, val, type(val))
                    
                    break
            else:
                _LOGGER.debug("Device %s not found in scanner", self.mac)
            
            return {"rssi": self.rssi}
                
        except Exception as e:
            _LOGGER.error("ERROR: %s", e)
            import traceback
            _LOGGER.error(traceback.format_exc())
            return {"rssi": None}
