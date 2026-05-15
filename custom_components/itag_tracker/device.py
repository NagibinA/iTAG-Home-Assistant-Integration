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
        _LOGGER.info("=== UPDATE called for %s ===", self.mac)
        
        # Получаем RSSI из рекламных данных
        service_info = bluetooth.async_last_service_info(
            self.hass, self.mac, connectable=True
        )
        
        _LOGGER.debug("service_info: %s", service_info)
        
        if service_info and service_info.rssi is not None:
            self._rssi = service_info.rssi
            _LOGGER.info("RSSI for %s: %s", self.mac, self._rssi)
            self._available = True
            
            # Если видим рекламные данные и нет соединения - подключаемся
            if not self._is_connected:
                _LOGGER.info("Device seen, attempting to connect...")
                await self._connect()
            else:
                _LOGGER.debug("Already connected, checking battery...")
                await self._read_battery()
        else:
            _LOGGER.debug("No advertising data for %s", self.mac)
            self._available = False

        _LOGGER.info("Update result: RSSI=%s, Battery=%s, Button=%s, Available=%s, Connected=%s",
                     self._rssi, self._battery, self._button_pressed, self._available, self._is_connected)
        
        return self._get_data_dict()

    async def _connect(self) -> None:
        """Establish persistent connection."""
        _LOGGER.info("=== _connect called for %s ===", self.mac)
        
        if self._is_connected and self._client and self._client.is_connected:
            _LOGGER.debug("Already connected, skipping")
            return

        try:
            # Находим устройство - НЕ await, это синхронная функция
            _LOGGER.info("Looking for device %s...", self.mac)
            device = bluetooth.async_ble_device_from_address(
                self.hass, self.mac, connectable=True
            )
            _LOGGER.debug("Device found: %s", device)
            
            if not device:
                _LOGGER.error("Device %s not found", self.mac)
                return

            # Подключаемся с retry
            _LOGGER.info("Establishing connection to %s...", self.mac)
            self._client = await establish_connection(
                BleakClient,
                device,
                self.name,
                max_attempts=3,
                timeout=CONNECT_TIMEOUT,
            )
            
            self._is_connected = self._client.is_connected
            _LOGGER.info("Connected to %s, is_connected=%s", self.mac, self._is_connected)

            # Читаем батарею
            _LOGGER.info("Reading battery...")
            await self._read_battery()
            
            # Подписываемся на уведомления кнопки
            _LOGGER.info("Subscribing to button...")
            await self._subscribe_button()

        except Exception as e:
            _LOGGER.error("Failed to connect to %s: %s", self.mac, e, exc_info=True)
            self._is_connected = False
            self._client = None

    async def _read_battery(self) -> None:
        """Read battery level."""
        _LOGGER.debug("_read_battery called, connected=%s", self._is_connected)
        
        if not self._client or not self._client.is_connected:
            _LOGGER.warning("Cannot read battery - not connected")
            return

        try:
            _LOGGER.info("Reading battery from UUID: %s", BATTERY_SERVICE_UUID)
            battery_data = await self._client.read_gatt_char(BATTERY_SERVICE_UUID)
            _LOGGER.info("Battery raw data: %s", battery_data.hex() if battery_data else None)
            
            if battery_data and len(battery_data) > 0:
                self._battery = battery_data[0]
                _LOGGER.info("Battery level: %s%%", self._battery)
            else:
                _LOGGER.warning("No battery data received")
        except Exception as e:
            _LOGGER.error("Failed to read battery: %s", e, exc_info=True)

    async def _subscribe_button(self) -> None:
        """Subscribe to button notifications."""
        _LOGGER.debug("_subscribe_button called, connected=%s", self._is_connected)
        
        if not self._client or not self._client.is_connected:
            _LOGGER.warning("Cannot subscribe to button - not connected")
            return

        def button_callback(sender, data):
            """Called when button is pressed."""
            _LOGGER.info("!!! BUTTON CALLBACK RECEIVED !!!")
            _LOGGER.info("Button data: %s", data.hex() if data else None)
            if data and len(data) > 0:
                self._button_pressed = data[0] == 1
                _LOGGER.info("Button state: %s", self._button_pressed)

        try:
            _LOGGER.info("Starting notify for UUID: %s", BUTTON_SERVICE_UUID)
            await self._client.start_notify(BUTTON_SERVICE_UUID, button_callback)
            _LOGGER.info("Successfully subscribed to button notifications")
        except Exception as e:
            _LOGGER.error("Failed to subscribe to button: %s", e, exc_info=True)

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
