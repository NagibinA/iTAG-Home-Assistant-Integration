"""iTAG device handler - advertisement only."""
from __future__ import annotations

import logging
from homeassistant.components import bluetooth
from homeassistant.core import HomeAssistant

from .const import RSSI_OFFLINE_VALUE

_LOGGER = logging.getLogger(__name__)


class ITAGDevice:
    """Representation of iTAG device - no connection, only advertisements."""

    def __init__(self, hass: HomeAssistant, mac: str, name: str) -> None:
        self.hass = hass
        self.mac = mac
        self.name = name
        self._rssi = None
        self._available = False

    @property
    def rssi(self) -> int | None:
        return self._rssi

    @property
    def available(self) -> bool:
        return self._available

    async def update(self) -> dict:
        """Update device data from advertisement packets only."""
        try:
            # Получаем RSSI из рекламных данных
            service_info = bluetooth.async_last_service_info(
                self.hass, self.mac, connectable=True
            )
            
            if service_info and service_info.rssi is not None:
                self._rssi = service_info.rssi
                self._available = True
                _LOGGER.debug("RSSI from advertisement: %s", self._rssi)
            else:
                self._rssi = RSSI_OFFLINE_VALUE
                self._available = False
                _LOGGER.debug("No advertisement from %s", self.mac)

        except Exception as e:
            _LOGGER.error("Update error: %s", e)
            self._available = False

        return self._get_data_dict()

    def _get_data_dict(self) -> dict:
        return {
            "rssi": self._rssi,
            "available": self._available,
        }
