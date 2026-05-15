"""iTAG device handler."""
from __future__ import annotations

import logging
from bleak import BleakClient
from homeassistant.components import bluetooth
from homeassistant.core import HomeAssistant

from .const import (
    BATTERY_SERVICE_UUID,
    BUTTON_SERVICE_UUID,
    RSSI_CONNECT_THRESHOLD,
    CONNECT_TIMEOUT,
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
            
            if ble_device and ble_device.rssi is not None:
                self._rssi = ble_device.rssi
                _LOGGER.debug("RSSI for %s: %s", self.mac, self._rssi)
            else:
                _LOGGER.debug("No BLE device found for %s", self.mac)
                self._available = False
                return self._get_data_dict()

            # Check if RSSI is strong enough to connect
            if self._rssi > RSSI_CONNECT_THRESHOLD:
                await self._connect_and_read()
                self._available = True
            else:
                _LOGGER.debug("RSSI too weak to connect: %s", self._rssi)
                self._available = False

            return self._get_data_dict()

        except Exception as e:
            _LOGGER.error("Error updating iTAG %s: %s", self.mac, e)
            self._available = False
            return self._get_data_dict()

    async def _connect_and_read(self) -> None:
        """Connect to device and read characteristics."""
        try:
            async with BleakClient(self.mac, timeout=CONNECT_TIMEOUT) as client:
                if not client.is_connected:
                    _LOGGER.warning("Failed to connect to %s", self.mac)
                    return

                _LOGGER.debug("Connected to %s", self.mac)

                # Read battery level
                try:
                    battery_data = await client.read_gatt_char(BATTERY_SERVICE_UUID)
                    if battery_data and len(battery_data) > 0:
                        self._battery = battery_data[0]
                        _LOGGER.debug("Battery level: %s%%", self._battery)
                except Exception as e:
                    _LOGGER.warning("Failed to read battery: %s", e)

                # Read button state
                try:
                    button_data = await client.read_gatt_char(BUTTON_SERVICE_UUID)
                    if button_data and len(button_data) > 0:
                        self._button_pressed = button_data[0] == 1
                        _LOGGER.debug("Button state: %s", self._button_pressed)
                except Exception as e:
                    _LOGGER.debug("Failed to read button state: %s", e)

        except Exception as e:
            _LOGGER.error("BleakClient error for %s: %s", self.mac, e)

    def _get_data_dict(self) -> dict:
        """Return data as dictionary."""
        return {
            "rssi": self._rssi,
            "battery": self._battery,
            "button_pressed": self._button_pressed,
            "available": self._available,
        }
