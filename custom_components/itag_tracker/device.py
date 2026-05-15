"""iTAG device handler with persistent connection."""
from __future__ import annotations

import asyncio
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
    """Representation of iTAG device with persistent connection."""

    def __init__(self, hass: HomeAssistant, mac: str, name: str) -> None:
        """Initialize the device."""
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
        # Получаем RSSI из рекламных данных
        service_info = bluetooth.async_last_service_info(
            self.hass, self.mac, connectable=True
        )
        
        if service_info and service_info.rssi is not None:
            self._rssi = service_info.rssi
            _LOGGER.debug("RSSI for %s: %s", self.mac, self._rssi)
            self._available = True
            
            # Если видим рекламные данные и нет соединения - подключаемся
            if not self._is_connected:
                _LOGGER.info("Device seen, connecting...")
                await self._connect()
        else:
            _LOGGER.debug("No advertising data for %s", self.mac)
            self._available = False

        return self._get_data_dict()

    async def _connect(self) -> None:
        """Establish persistent connection."""
        if self._is_connected and self._client and self._client.is_connected:
            return

        try:
            # Находим устройство
            device = await bluetooth.async_ble_device_from_address(
                self.hass, self.mac, connectable=True
            )
            if not device:
                _LOGGER.error("Device %s not found", self.mac)
                return

            # Подключаемся с retry
            self._client = await establish_connection(
                BleakClient,
                device,
                self.name,
                max_attempts=3,
                timeout=CONNECT_TIMEOUT,
            )
            
            self._is_connected = self._client.is_connected
            _LOGGER.info("Connected to %s", self.mac)

            # Читаем батарею
            await self._read_battery()
            
            # Подписываемся на уведомления кнопки
            await self._subscribe_button()

        except Exception as e:
            _LOGGER.error("Failed to connect to %s: %s", self.mac, e)
            self._is_connected = False
            self._client = None

    async def _read_battery(self) -> None:
        """Read battery level."""
        if not self._client or not self._client.is_connected:
            return

        try:
            battery_data = await self._client.read_gatt_char(BATTERY_SERVICE_UUID)
            if battery_data and len(battery_data) > 0:
                self._battery = battery_data[0]
                _LOGGER.debug("Battery: %s%%", self._battery)
        except Exception as e:
            _LOGGER.warning("Failed to read battery: %s", e)

    async def _subscribe_button(self) -> None:
        """Subscribe to button notifications."""
        if not self._client or not self._client.is_connected:
            return

        def button_callback(sender, data):
            """Called when button is pressed."""
            if data and len(data) > 0:
                self._button_pressed = data[0] == 1
                _LOGGER.info("Button pressed: %s", self._button_pressed)
                # Сбрасываем состояние через 1 секунду (если нужно)
                # asyncio.create_task(self._reset_button())

        try:
            await self._client.start_notify(BUTTON_SERVICE_UUID, button_callback)
            _LOGGER.info("Subscribed to button notifications")
        except Exception as e:
            _LOGGER.warning("Failed to subscribe to button: %s", e)

    async def _reset_button(self) -> None:
        """Reset button state after delay."""
        await asyncio.sleep(1)
        self._button_pressed = False
        _LOGGER.debug("Button state reset")

    async def disconnect(self) -> None:
        """Disconnect from device."""
        if self._client and self._client.is_connected:
            await self._client.disconnect()
            _LOGGER.info("Disconnected from %s", self.mac)
        self._is_connected = False
        self._client = None

    def _get_data_dict(self) -> dict:
        return {
            "rssi": self._rssi,
            "battery": self._battery,
            "button_pressed": self._button_pressed,
            "available": self._available,
        }
