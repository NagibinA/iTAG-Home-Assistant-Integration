"""BLE scanner for iTAG devices."""

import asyncio
import logging
from datetime import datetime
from bleak import BleakScanner, BleakClient

from .const import (
    CHARGE_LVL, BUTTON, ALERT_LVL, ALERT_HIGH, ALERT_NO,
    SERVICE_BUTTON
)

_LOGGER = logging.getLogger(__name__)


class iTAGDevice:
    """iTAG device handler."""

    def __init__(self, hass, mac, name, entry_id):
        self.hass = hass
        self.mac = mac
        self.name = name
        self.entry_id = entry_id
        self.battery_level = None
        self.rssi = None
        self.button_pressed = False
        self.last_seen = None
        self._scan_task = None
        self._running = False

    async def start(self):
        """Start monitoring iTAG device."""
        self._running = True
        self._scan_task = self.hass.async_create_task(self._monitor_loop())

    async def stop(self):
        """Stop monitoring."""
        self._running = False
        if self._scan_task:
            self._scan_task.cancel()

    async def _monitor_loop(self):
        """Main monitoring loop."""
        while self._running:
            try:
                # Scan for RSSI
                device = await BleakScanner.find_device_by_address(self.mac)
                if device:
                    self.rssi = device.rssi
                    self.last_seen = datetime.now().isoformat()
                
                # Connect for battery and button
                await self._connect_and_update()
                
            except Exception as e:
                _LOGGER.debug(f"iTAG {self.name} monitor error: {e}")
            
            await asyncio.sleep(60)  # Scan every 60 seconds

    async def _connect_and_update(self):
        """Connect to iTAG and read battery/button."""
        try:
            async with BleakClient(self.mac, timeout=10.0) as client:
                _LOGGER.debug(f"Connected to {self.mac}")
                
                # Read battery level
                try:
                    battery_char = await client.read_gatt_char(CHARGE_LVL)
                    self.battery_level = int(battery_char[0])
                    _LOGGER.debug(f"Battery level: {self.battery_level}%")
                except Exception as e:
                    _LOGGER.debug(f"Could not read battery: {e}")
                
                # Subscribe to button notifications
                try:
                    # Check if button service exists
                    for service in client.services:
                        if service.uuid == SERVICE_BUTTON:
                            await client.start_notify(BUTTON, self._button_notify_handler)
                            await asyncio.sleep(1)  # Wait for notifications
                            await client.stop_notify(BUTTON)
                            break
                except Exception as e:
                    _LOGGER.debug(f"Button notification error: {e}")
                    
        except Exception as e:
            _LOGGER.debug(f"Connection failed: {e}")

    def _button_notify_handler(self, sender, data):
        """Handle button press notification."""
        if len(data) > 0 and data[0] == 0x01:
            self.button_pressed = True
            _LOGGER.info(f"Button pressed on {self.name}")
            
            # Reset button state after delay
            async def reset_button():
                await asyncio.sleep(1)
                self.button_pressed = False
            asyncio.create_task(reset_button())

    async def alert(self, duration=10):
        """Make iTAG beep."""
        try:
            async with BleakClient(self.mac, timeout=10.0) as client:
                # Send high alert
                await client.write_gatt_char(
                    ALERT_LVL,
                    bytes([ALERT_HIGH]),
                    response=True
                )
                await asyncio.sleep(duration)
                # Stop alert
                await client.write_gatt_char(
                    ALERT_LVL,
                    bytes([ALERT_NO]),
                    response=True
                )
                _LOGGER.info(f"Alert triggered on {self.name} for {duration}s")
        except Exception as e:
            _LOGGER.error(f"Alert error on {self.name}: {e}")


class iTAGManager:
    """Manager for iTAG devices."""

    def __init__(self, hass):
        self.hass = hass
        self.devices = {}

    async def start(self):
        """Start manager."""
        _LOGGER.info("iTAG Manager started")
        # Devices will be added via config entries

    async def stop(self):
        """Stop all devices."""
        for device in self.devices.values():
            await device.stop()
        _LOGGER.info("iTAG Manager stopped")

    def add_device(self, mac, name, entry_id):
        """Add device to manager."""
        if mac not in self.devices:
            device = iTAGDevice(self.hass, mac, name, entry_id)
            self.devices[mac] = device
            return device
        return self.devices[mac]

    async def alert_device(self, mac, duration=10):
        """Trigger alert on specific device."""
        if mac in self.devices:
            await self.devices[mac].alert(duration)