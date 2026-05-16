"""iTAG device handler - with BlueZ StartNotify."""
from __future__ import annotations

import asyncio
import logging
from bleak import BleakClient
from bleak_retry_connector import establish_connection
from homeassistant.components import bluetooth
from homeassistant.core import HomeAssistant

from .const import (
    BATTERY_CHAR_UUID,
    BUTTON_CHAR_UUID,
    CONNECT_TIMEOUT,
    RSSI_OFFLINE_VALUE,
)

_LOGGER = logging.getLogger(__name__)


class ITAGDevice:
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
        self._read_task = None
        self._device = None

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
        service_info = bluetooth.async_last_service_info(
            self.hass, self.mac, connectable=True
        )
        if service_info and service_info.rssi is not None:
            self._rssi = service_info.rssi
            self._available = True
            self._device = bluetooth.async_ble_device_from_address(
                self.hass, self.mac, connectable=True
            )
            if self._device and not self._is_connected and (self._read_task is None or self._read_task.done()):
                _LOGGER.info("Starting persistent connection...")
                self._read_task = asyncio.create_task(self._persistent_connection())
        else:
            self._rssi = RSSI_OFFLINE_VALUE
            self._available = False
        return self._get_data_dict()

    async def _subscribe_with_cccd_injection(self, char_uuid: str, callback) -> bool:
        """Subscribe using BlueZ StartNotify (works without CCCD)."""
        try:
            # КЛЮЧЕВОЕ ИЗМЕНЕНИЕ: принудительно используем BlueZ StartNotify
            await self._client.start_notify(char_uuid, callback, bluez=True)
            _LOGGER.info("✅ Subscribed to %s via BlueZ StartNotify", char_uuid)
            return True
        except Exception as e:
            _LOGGER.debug("BlueZ notify failed for %s: %s", char_uuid, e)
            
            # Fallback: пробуем через инжекцию CCCD
            try:
                if await self._inject_cccd(char_uuid):
                    await self._client.start_notify(char_uuid, callback, bluez=True)
                    _LOGGER.info("✅ Subscribed to %s after CCCD injection", char_uuid)
                    return True
            except Exception as e2:
                _LOGGER.debug("Injection also failed: %s", e2)
            
            return False

    async def _inject_cccd(self, char_uuid: str) -> bool:
        """Inject synthetic CCCD descriptor."""
        try:
            char = self._client.services.get_characteristic(char_uuid)
            if not char:
                return False
            
            for descriptor in char.descriptors:
                if descriptor.uuid == "00002902-0000-1000-8000-00805f9b34fb":
                    return True
            
            from bleak.backends.descriptor import BleakGATTDescriptor
            
            cccd = BleakGATTDescriptor(
                char._backend,
                char.handle + 1,
                "00002902-0000-1000-8000-00805f9b34fb",
                char,
            )
            char.descriptors.append(cccd)
            _LOGGER.info("Synthetic CCCD injected for %s", char_uuid)
            return True
        except Exception as e:
            _LOGGER.debug("CCCD injection failed: %s", e)
            return False

    def _battery_callback(self, sender: int, data: bytearray) -> None:
        if data and len(data) > 0:
            value = data[0]
            if self._battery != value:
                self._battery = value
                _LOGGER.info("🔋 Battery: %s%%", self._battery)

    def _button_callback(self, sender: int, data: bytearray) -> None:
        if data and len(data) > 0:
            value = data[0]
            old = self._button_pressed
            self._button_pressed = (value == 0x01)
            if old != self._button_pressed:
                _LOGGER.info("🔘 Button: %s", "PRESSED" if self._button_pressed else "released")

    async def _persistent_connection(self) -> None:
        try:
            _LOGGER.info("Connecting to %s...", self.mac)
            self._client = await establish_connection(
                BleakClient,
                self._device,
                self.name,
                max_attempts=3,
                timeout=CONNECT_TIMEOUT,
            )
            if not self._client.is_connected:
                _LOGGER.error("Failed to connect")
                self._is_connected = False
                return

            self._is_connected = True
            _LOGGER.info("Connected! Subscribing to notifications...")

            # Подписываемся с bluez=True
            battery_ok = await self._subscribe_with_cccd_injection(
                BATTERY_CHAR_UUID, self._battery_callback
            )
            if battery_ok:
                _LOGGER.info("Battery notifications active!")
                # Начальное чтение
                await asyncio.sleep(3)
                try:
                    data = await self._client.read_gatt_char(BATTERY_CHAR_UUID)
                    if data and len(data) > 0:
                        self._battery = data[0]
                        _LOGGER.info("Initial battery: %s%%", self._battery)
                except Exception as e:
                    _LOGGER.debug("Initial poll: %s", e)

            button_ok = await self._subscribe_with_cccd_injection(
                BUTTON_CHAR_UUID, self._button_callback
            )
            if button_ok:
                _LOGGER.info("Button notifications active! Press the button.")

            # Keep-alive
            while self._is_connected:
                service_info = bluetooth.async_last_service_info(
                    self.hass, self.mac, connectable=True
                )
                if not service_info or service_info.rssi is None:
                    _LOGGER.info("Device disappeared")
                    break
                self._rssi = service_info.rssi
                await asyncio.sleep(30)

        except asyncio.CancelledError:
            _LOGGER.debug("Task cancelled")
        except Exception as e:
            _LOGGER.error("Connection error: %s", e)
        finally:
            if self._client and self._client.is_connected:
                await self._client.disconnect()
                _LOGGER.info("Disconnected")
            self._is_connected = False
            self._client = None
            self._read_task = None

    async def stop(self) -> None:
        self._is_connected = False
        if self._read_task and not self._read_task.done():
            self._read_task.cancel()
        if self._client and self._client.is_connected:
            await self._client.disconnect()

    def _get_data_dict(self) -> dict:
        return {
            "rssi": self._rssi,
            "battery": self._battery,
            "button_pressed": self._button_pressed,
            "available": self._available,
        }
