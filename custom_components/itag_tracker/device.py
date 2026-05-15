"""iTAG device handler."""
from __future__ import annotations

import asyncio
import logging
from bleak import BleakClient
from homeassistant.components import bluetooth
from homeassistant.core import HomeAssistant

from .const import (
    BATTERY_SERVICE_UUID,
    BUTTON_SERVICE_UUID,
    RSSI_CONNECT_THRESHOLD,
    CONNECT_TIMEOUT,
    DISCONNECT_DELAY,
)

_LOGGER = logging.getLogger(__name__)


class ITAGDevice:
    """Representation of iTAG device."""

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
        self._keep_connected = False
        self._disconnect_task = None

    @property
    def rssi(self) -> int | None:
        """Return RSSI value."""
        return self._rssi

    @property
    def battery(self) -> int | None:
        """Return battery level."""
        return self._battery

    @property
    def button_pressed(self) -> bool:
        """Return button state."""
        return self._button_pressed

    @property
    def available(self) -> bool:
        """Return device availability."""
        return self._available

    async def update(self) -> dict:
        """Update device data."""
        try:
            # Get RSSI from Bluetooth stack
            ble_device = bluetooth.async_ble_device_from_address(
                self.hass, self.mac, connectable=True
            )

            if ble_device:
                service_info = bluetooth.async_last_service_info(
                    self.hass, self.mac, connectable=True
                )
                if service_info and service_info.rssi is not None:
                    self._rssi = service_info.rssi
                    _LOGGER.debug("RSSI for %s: %s", self.mac, self._rssi)
                else:
                    _LOGGER.debug("No RSSI data for %s", self.mac)
                    await self._disconnect()
                    self._available = False
                    return self._get_data_dict()
            else:
                _LOGGER.debug("No BLE device found for %s", self.mac)
                await self._disconnect()
                self._available = False
                return self._get_data_dict()

            # Check if RSSI is strong enough to connect
            rssi_strong = self._rssi is not None and self._rssi > RSSI_CONNECT_THRESHOLD

            if rssi_strong:
                # RSSI strong - should be connected
                if not self._keep_connected:
                    # Need to connect
                    _LOGGER.debug("RSSI strong (%s), connecting...", self._rssi)
                    await self._connect()
                else:
                    # Already connected, just update battery periodically
                    _LOGGER.debug("RSSI strong (%s), already connected", self._rssi)
                    await self._read_battery()
                self._available = True
                # Cancel any pending disconnect
                self._cancel_disconnect()
            else:
                # RSSI weak - schedule disconnect if not already scheduled
                if self._keep_connected:
                    _LOGGER.debug("RSSI weak (%s), scheduling disconnect in %s seconds",
                                  self._rssi, DISCONNECT_DELAY)
                    self._schedule_disconnect()
                self._available = False

            return self._get_data_dict()

        except Exception as e:
            _LOGGER.error("Error updating iTAG %s: %s", self.mac, e)
            await self._disconnect()
            self._available = False
            return self._get_data_dict()

    async def _connect(self) -> None:
        """Connect to device and setup notifications."""
        try:
            if self._client and self._client.is_connected:
                return

            _LOGGER.debug("Connecting to %s...", self.mac)
            self._client = BleakClient(self.mac, timeout=CONNECT_TIMEOUT)
            await self._client.connect()
            _LOGGER.debug("Connected to %s", self.mac)

            # Setup button notification
            def button_callback(sender, data):
                _LOGGER.debug("Button notification: %s", data.hex() if data else None)
                if data and len(data) > 0:
                    self._button_pressed = data[0] == 1
                    _LOGGER.debug("Button state: %s", self._button_pressed)
                    # Reset button state after reading? 
                    # Some devices need explicit reset, some auto-reset
                    # We'll keep the value until next notification

            await self._client.start_notify(BUTTON_SERVICE_UUID, button_callback)
            _LOGGER.debug("Subscribed to button notifications")

            # Read initial battery
            await self._read_battery()

            self._keep_connected = True

        except Exception as e:
            _LOGGER.error("Failed to connect to %s: %s", self.mac, e)
            await self._disconnect()

    async def _read_battery(self) -> None:
        """Read battery level."""
        if not self._client or not self._client.is_connected:
            return

        try:
            battery_data = await self._client.read_gatt_char(BATTERY_SERVICE_UUID)
            if battery_data and len(battery_data) > 0:
                self._battery = battery_data[0]
                _LOGGER.debug("Battery level: %s%%", self._battery)
        except Exception as e:
            _LOGGER.warning("Failed to read battery: %s", e)

    async def _disconnect(self) -> None:
        """Disconnect from device."""
        self._keep_connected = False
        self._cancel_disconnect()

        if self._client and self._client.is_connected:
            try:
                # Try to stop notifications
                try:
                    await self._client.stop_notify(BUTTON_SERVICE_UUID)
                except:
                    pass
                await self._client.disconnect()
                _LOGGER.debug("Disconnected from %s", self.mac)
            except Exception as e:
                _LOGGER.debug("Error during disconnect: %s", e)
            finally:
                self._client = None

    def _schedule_disconnect(self):
        """Schedule disconnect after delay."""
        if self._disconnect_task is None:
            self._disconnect_task = asyncio.create_task(self._delayed_disconnect())

    def _cancel_disconnect(self):
        """Cancel scheduled disconnect."""
        if self._disconnect_task and not self._disconnect_task.done():
            self._disconnect_task.cancel()
        self._disconnect_task = None

    async def _delayed_disconnect(self):
        """Disconnect after delay."""
        try:
            await asyncio.sleep(DISCONNECT_DELAY)
            _LOGGER.debug("Disconnect delay finished, disconnecting from %s", self.mac)
            await self._disconnect()
        except asyncio.CancelledError:
            _LOGGER.debug("Disconnect cancelled for %s", self.mac)
        except Exception as e:
            _LOGGER.error("Error in delayed disconnect: %s", e)

    def _get_data_dict(self) -> dict:
        """Return data as dictionary."""
        return {
            "rssi": self._rssi,
            "battery": self._battery,
            "button_pressed": self._button_pressed,
            "available": self._available,
        }
