"""iTAG device handler - button via reading."""
from __future__ import annotations

import logging
from bleak import BleakClient
from bleak_retry_connector import establish_connection
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
        self._client = None
        self._is_connected = False

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
        """Update device data - called every 30 seconds."""
        # Получаем RSSI
        service_info = bluetooth.async_last_service_info(
            self.hass, self.mac, connectable=True
        )
        
        if service_info and service_info.rssi is not None:
            self._rssi = service_info.rssi
            _LOGGER.info("RSSI: %s", self._rssi)
            self._available = True
            
            # Если нет соединения - подключаемся
            if not self._is_connected:
                _LOGGER.info("Connecting...")
                await self._connect()
            else:
                # Если уже подключены - читаем данные
                await self._read_data()
        else:
            self._available = False

        return self._get_data_dict()

    async def _connect(self) -> None:
        """Connect and read data."""
        if self._is_connected:
            return

        try:
            device = bluetooth.async_ble_device_from_address(
                self.hass, self.mac, connectable=True
            )
            if not device:
                _LOGGER.error("Device not found")
                return

            _LOGGER.info("Establishing connection...")
            self._client = await establish_connection(
                BleakClient,
                device,
                self.name,
                max_attempts=3,
                timeout=CONNECT_TIMEOUT,
            )
            
            self._is_connected = self._client.is_connected
            _LOGGER.info("Connected!")
            
            # Читаем данные после подключения
            await self._read_data()

        except Exception as e:
            _LOGGER.error("Connection error: %s", e)
            self._is_connected = False
            self._client = None

    async def _read_data(self) -> None:
        """Read battery and button."""
        if not self._client or not self._client.is_connected:
            return

        # Читаем батарею
        try:
            battery_data = await self._client.read_gatt_char(BATTERY_SERVICE_UUID)
            if battery_data and len(battery_data) > 0:
                self._battery = battery_data[0]
                _LOGGER.info("Battery: %s%%", self._battery)
        except Exception as e:
            _LOGGER.error("Battery read error: %s", e)

        # Читаем кнопку
        try:
            button_data = await self._client.read_gatt_char(BUTTON_SERVICE_UUID)
            if button_data and len(button_data) > 0:
                old_state = self._button_pressed
                self._button_pressed = button_data[0] == 1
                if old_state != self._button_pressed:
                    _LOGGER.info("Button state changed to: %s", 
                                 "PRESSED" if self._button_pressed else "released")
        except Exception as e:
            _LOGGER.error("Button read error: %s", e)

    async def disconnect(self) -> None:
        """Disconnect from device."""
        if self._client and self._client.is_connected:
            await self._client.disconnect()
            _LOGGER.info("Disconnected")
        self._is_connected = False
        self._client = None

    def _get_data_dict(self) -> dict:
        return {
            "rssi": self._rssi,
            "battery": self._battery,
            "button_pressed": self._button_pressed,
            "available": self._available,
        }
