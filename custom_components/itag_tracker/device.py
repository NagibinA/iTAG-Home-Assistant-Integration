"""iTAG device handler - persistent connection with battery notifications."""
from __future__ import annotations

import asyncio
import logging
from bleak import BleakClient
from bleak_retry_connector import establish_connection
from homeassistant.components import bluetooth
from homeassistant.core import HomeAssistant

from .const import (
    BATTERY_CHAR_UUID,
    CONNECT_TIMEOUT,
    RSSI_OFFLINE_VALUE,
)

_LOGGER = logging.getLogger(__name__)


class ITAGDevice:
    """Representation of iTAG device with persistent connection."""

    def __init__(self, hass: HomeAssistant, mac: str, name: str) -> None:
        self.hass = hass
        self.mac = mac
        self.name = name
        self._rssi = None
        self._battery = None
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
    def available(self) -> bool:
        return self._available

    async def update(self) -> dict:
        """Update RSSI - called every 30 seconds."""
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
                _LOGGER.info("Starting persistent connection with battery notifications...")
                self._read_task = asyncio.create_task(self._persistent_connection())
        else:
            self._rssi = RSSI_OFFLINE_VALUE
            self._available = False

        return self._get_data_dict()

    def _battery_callback(self, sender: int, data: bytearray) -> None:
        """Callback when battery notification is received."""
        if data and len(data) > 0:
            new_battery = data[0]
            # iTAG may send placeholder 100% first, filter it
            if new_battery == 100 and self._battery is not None and self._battery < 100:
                _LOGGER.debug("Ignoring placeholder 100%% notification (real is %s%%)", self._battery)
                return

            if self._battery != new_battery:
                self._battery = new_battery
                _LOGGER.info("🔋 Battery notification: %s%%", self._battery)
        else:
            _LOGGER.debug("Empty battery notification received")

    async def _enable_battery_notifications(self) -> bool:
        """
        Enable battery notifications.
        Tries standard method first, then fallback without CCCD check.
        """
        try:
            # Try standard notify
            await self._client.start_notify(BATTERY_CHAR_UUID, self._battery_callback)
            _LOGGER.info("Battery notifications enabled successfully")
            return True
        except Exception as e:
            _LOGGER.debug("Standard notify failed: %s", e)

            # Try fallback - get characteristic and try to enable notifications directly
            try:
                char = self._client.services.get_characteristic(BATTERY_CHAR_UUID)
                if not char:
                    _LOGGER.debug("Battery characteristic not found")
                    return False

                # Try to start notify without CCCD check (some devices work this way)
                await self._client.start_notify(char, self._battery_callback)
                _LOGGER.info("Battery notifications enabled via direct characteristic")
                return True

            except Exception as e2:
                _LOGGER.debug("Fallback notify also failed: %s", e2)
                return False

    async def _battery_poll_fallback(self) -> None:
        """Fallback: read battery via polling if notifications don't work."""
        try:
            battery_data = await self._client.read_gatt_char(BATTERY_CHAR_UUID)
            if battery_data and len(battery_data) > 0:
                value = battery_data[0]
                if self._battery != value:
                    self._battery = value
                    _LOGGER.info("Battery (poll fallback): %s%%", self._battery)
        except Exception as e:
            _LOGGER.debug("Battery poll error: %s", e)

    async def _persistent_connection(self) -> None:
        """Maintain connection with battery notifications."""
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
            _LOGGER.info("Connected! Enabling battery notifications...")

            # Try to enable battery notifications
            notifications_enabled = await self._enable_battery_notifications()

            if notifications_enabled:
                _LOGGER.info("Battery notifications active - values will update automatically")

                # Wait a bit then do an initial poll to get current value
                await asyncio.sleep(3)
                await self._battery_poll_fallback()
            else:
                _LOGGER.warning("Battery notifications not available, falling back to polling every 60s")

            # Keep connection alive loop
            last_poll = 0

            while self._is_connected:
                # Check if device is still advertising
                service_info = bluetooth.async_last_service_info(
                    self.hass, self.mac, connectable=True
                )
                if not service_info or service_info.rssi is None:
                    _LOGGER.info("Device disappeared, closing connection...")
                    break

                # If notifications are not working, fall back to polling
                if not notifications_enabled:
                    now = asyncio.get_event_loop().time()
                    if now - last_poll >= 60:
                        last_poll = now
                        await self._battery_poll_fallback()

                await asyncio.sleep(10)

        except asyncio.CancelledError:
            _LOGGER.debug("Connection task cancelled")
        except Exception as e:
            _LOGGER.error("Connection error: %s", e)
        finally:
            if self._client and self._client.is_connected:
                try:
                    await self._client.disconnect()
                    _LOGGER.info("Disconnected")
                except:
                    pass
            self._is_connected = False
            self._client = None
            self._read_task = None

    async def stop(self) -> None:
        """Stop persistent connection."""
        self._is_connected = False
        if self._read_task and not self._read_task.done():
            self._read_task.cancel()
        if self._client and self._client.is_connected:
            try:
                await self._client.disconnect()
            except:
                pass

    def _get_data_dict(self) -> dict:
        return {
            "rssi": self._rssi,
            "battery": self._battery,
            "available": self._available,
        }
