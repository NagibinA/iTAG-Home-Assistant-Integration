"""iTAG device handler - with synthetic CCCD injection."""
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
    """Representation of iTAG device with synthetic CCCD."""

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
                _LOGGER.info("Starting persistent connection...")
                self._read_task = asyncio.create_task(self._persistent_connection())
        else:
            self._rssi = RSSI_OFFLINE_VALUE
            self._available = False

        return self._get_data_dict()

    async def _inject_cccd(self, char_uuid: str) -> bool:
        """
        Inject synthetic CCCD descriptor into characteristic.
        Bypasses Bleak's CCCD check, allowing notification subscription even without physical CCCD.
        """
        try:
            # Get characteristic
            char = self._client.services.get_characteristic(char_uuid)
            if not char:
                _LOGGER.debug("Characteristic %s not found", char_uuid)
                return False

            # Check if CCCD already exists
            for descriptor in char.descriptors:
                if descriptor.uuid == "00002902-0000-1000-8000-00805f9b34fb":
                    _LOGGER.debug("CCCD already exists for %s", char_uuid)
                    return True

            # Create synthetic CCCD descriptor
            from bleak.backends.characteristic import BleakGATTCharacteristic
            from bleak.backends.descriptor import BleakGATTDescriptor

            cccd = BleakGATTDescriptor(
                char._backend,
                handle=char.handle + 1,
                uuid="00002902-0000-1000-8000-00805f9b34fb",
                characteristic=char,
            )
            char.descriptors.append(cccd)
            _LOGGER.info("Synthetic CCCD injected for %s", char_uuid)
            return True

        except Exception as e:
            _LOGGER.debug("Failed to inject CCCD for %s: %s", char_uuid, e)
            return False

    async def _subscribe_with_cccd_injection(self, char_uuid: str, callback) -> bool:
        """Subscribe to notifications with CCCD injection if needed."""
        try:
            await self._client.start_notify(char_uuid, callback)
            _LOGGER.info("Subscribed to %s normally", char_uuid)
            return True
        except Exception as e:
            _LOGGER.debug("Normal subscribe failed for %s: %s", char_uuid, e)

            # If failed - inject CCCD and try again
            if await self._inject_cccd(char_uuid):
                try:
                    await self._client.start_notify(char_uuid, callback)
                    _LOGGER.info("Subscribed to %s after CCCD injection", char_uuid)
                    return True
                except Exception as e2:
                    _LOGGER.debug("Subscribe after injection still failed: %s", e2)

            return False

    def _battery_callback(self, sender: int, data: bytearray) -> None:
        """Battery notification callback."""
        if data and len(data) > 0:
            value = data[0]
            # Filter out placeholder 100% if we already have a real value
            if value == 100 and self._battery is not None and self._battery < 100:
                _LOGGER.debug("Ignoring placeholder 100%% battery notification")
                return
            if self._battery != value:
                self._battery = value
                _LOGGER.info("🔋 Battery notification: %s%%", self._battery)

    def _button_callback(self, sender: int, data: bytearray) -> None:
        """Button notification callback."""
        if data and len(data) > 0:
            value = data[0]
            old_state = self._button_pressed
            self._button_pressed = (value == 0x01)
            if old_state != self._button_pressed:
                _LOGGER.info("🔘 Button: %s", "PRESSED" if self._button_pressed else "released")

    async def _persistent_connection(self) -> None:
        """Maintain connection with synthetic CCCD."""
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
            _LOGGER.info("Connected! Subscribing to battery notifications...")

            # Subscribe to battery with CCCD injection
            battery_ok = await self._subscribe_with_cccd_injection(
                BATTERY_CHAR_UUID, self._battery_callback
            )

            if battery_ok:
                _LOGGER.info("Battery notifications active!")
                # Initial poll to get current value
                await asyncio.sleep(3)
                try:
                    data = await self._client.read_gatt_char(BATTERY_CHAR_UUID)
                    if data and len(data) > 0:
                        self._battery = data[0]
                        _LOGGER.info("Initial battery: %s%%", self._battery)
                except Exception as e:
                    _LOGGER.debug("Initial battery poll: %s", e)
            else:
                _LOGGER.warning("Battery notifications not available, will poll")

            # Subscribe to button with CCCD injection
            button_ok = await self._subscribe_with_cccd_injection(
                BUTTON_CHAR_UUID, self._button_callback
            )
            if button_ok:
                _LOGGER.info("Button notifications active! Press the button.")
            else:
                _LOGGER.warning("Button notifications not available")

            # Keep-alive loop
            last_poll = 0
            while self._is_connected:
                service_info = bluetooth.async_last_service_info(
                    self.hass, self.mac, connectable=True
                )
                if not service_info or service_info.rssi is None:
                    _LOGGER.info("Device disappeared, closing...")
                    break

                self._rssi = service_info.rssi

                # If notifications don't work - fallback to polling every 60 seconds
                if not battery_ok:
                    now = asyncio.get_event_loop().time()
                    if now - last_poll >= 60:
                        last_poll = now
                        try:
                            data = await self._client.read_gatt_char(BATTERY_CHAR_UUID)
                            if data and len(data) > 0 and data[0] < 100:
                                if self._battery != data[0]:
                                    self._battery = data[0]
                                    _LOGGER.info("Battery (poll): %s%%", self._battery)
                        except Exception:
                            pass

                await asyncio.sleep(30)

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
            "button_pressed": self._button_pressed,
            "available": self._available,
        }
