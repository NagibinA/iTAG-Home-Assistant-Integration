"""iTAG device handler - stable version (battery works, button reads)."""
from __future__ import annotations

import logging
from bleak import BleakClient
from homeassistant.components import bluetooth
from homeassistant.core import HomeAssistant

from .const import (
    BATTERY_SERVICE_UUID,
    BUTTON_SERVICE_UUID,
    CONNECT_TIMEOUT,
)

_LOGGER = logging.getLogger(__name__)


class ITAGDevice:
    """Representation of iTAG device."""

    def __init__(self, hass: HomeAssistant, mac: str, name: str) -> None:
        self.hass = hass
        self.mac = mac
        self.name = name
        self._rssi = None
        self._battery = None
        self._button_pressed = False
        self._available = False

    @property
    def rssi(self) -> int | None:
        return self._rssi

    @property
    def battery(self) -> int | None:
        return self._battery

    @property
    def button_pressed(self) -> bool:
        return self._button_pressed

    @property
    def available(self) -> bool:
        return self._available

    async def update(self) -> dict:
        """Update device data - called every 3 seconds."""
        try:
            # Получаем RSSI из рекламных данных
            service_info = bluetooth.async_last_service_info(
                self.hass, self.mac, connectable=True
            )
            
            if service_info and service_info.rssi is not None:
                self._rssi = service_info.rssi
                self._available = True
                
                # Подключаемся и читаем данные
                await self._connect_and_read()
            else:
                self._available = False

        except Exception as e:
            _LOGGER.error("Update error: %s", e)
            self._available = False

        return self._get_data_dict()

    async def _connect_and_read(self) -> None:
        """Connect, read data, disconnect."""
        client = None
        try:
            client = BleakClient(self.mac, timeout=CONNECT_TIMEOUT)
            await client.connect()
            
            if not client.is_connected:
                return
            
            # Читаем батарею
            try:
                battery_data = await client.read_gatt_char(BATTERY_SERVICE_UUID)
                if battery_data and len(battery_data) > 0:
                    if self._battery != battery_data[0]:
                        self._battery = battery_data[0]
                        _LOGGER.info("Battery: %s%%", self._battery)
            except Exception as e:
                _LOGGER.debug("Battery read error: %s", e)
            
            # Читаем кнопку
            try:
                button_data = await client.read_gatt_char(BUTTON_SERVICE_UUID)
                if button_data and len(button_data) > 0:
                    old_state = self._button_pressed
                    self._button_pressed = button_data[0] == 1
                    if old_state != self._button_pressed:
                        _LOGGER.info("🔘 Button: %s", "PRESSED" if self._button_pressed else "normal")
            except Exception as e:
                _LOGGER.debug("Button read error: %s", e)
            
            await client.disconnect()
            
        except Exception as e:
            _LOGGER.debug("Connection error: %s", e)
            if client and client.is_connected:
                try:
                    await client.disconnect()
                except:
                    pass

    def _get_data_dict(self) -> dict:
        return {
            "rssi": self._rssi,
            "battery": self._battery,
            "button_pressed": self._button_pressed,
            "available": self._available,
        }
