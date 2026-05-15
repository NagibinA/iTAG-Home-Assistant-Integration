"""Device tracker для iTAG."""

import logging
import asyncio
from datetime import datetime

from homeassistant.components.device_tracker import SourceType, ScannerEntity
from homeassistant.helpers import device_registry as dr
from bleak import BleakScanner, BleakClient

from .const import (
    DOMAIN,
    RSSI_PRESENCE_THRESHOLD,
    CONNECTION_TIMEOUT,
    CHARGE_LVL,
    BUTTON_CHAR,
)

_LOGGER = logging.getLogger(__name__)


class iTAGDeviceTracker(ScannerEntity):
    """Отслеживание iTAG."""

    def __init__(self, hass, entry):
        self.hass = hass
        self._entry = entry
        self._mac = entry.data["mac_address"].lower()
        self._name = entry.data["name"]
        self._attr_name = self._name
        self._attr_unique_id = f"{self._mac}_tracker"  # ← УНИКАЛЬНЫЙ ID

        self._is_present = False
        self._rssi = None
        self._last_seen = None
        self._battery = None

        self._client = None
        self._scan_task = None
        self._running = False
        self._last_rssi_update = None
        self._button_callback = None

    @property
    def unique_id(self):
        """Возвращает уникальный идентификатор."""
        return self._attr_unique_id

    @property
    def device_info(self):
        mac_normalized = self._mac.replace(":", "")
        return {
            "identifiers": {(DOMAIN, mac_normalized)},
            "name": self._name,
            "manufacturer": "iTAG",
            "model": "BLE Tracker",
            "connections": {(dr.CONNECTION_BLUETOOTH, self._mac)},
        }

    @property
    def is_connected(self):
        return self._is_present

    @property
    def source_type(self):
        return SourceType.BLUETOOTH

    @property
    def extra_state_attributes(self):
        attrs = {}
        if self._rssi is not None:
            attrs["rssi"] = self._rssi
        if self._last_seen:
            attrs["last_seen"] = self._last_seen
        if self._battery is not None:
            attrs["battery"] = self._battery
        return attrs

    def set_button_callback(self, callback):
        self._button_callback = callback

    def get_battery(self):
        return self._battery

    async def start(self):
        self._running = True
        self._scan_task = asyncio.create_task(self._scan_loop())

    async def stop(self):
        self._running = False
        if self._scan_task:
            self._scan_task.cancel()
        await self._disconnect()

    async def _scan_loop(self):
        while self._running:
            try:
                device = await BleakScanner.find_device_by_address(self._mac, timeout=5)

                if device:
                    self._rssi = device.rssi
                    self._last_seen = datetime.now().isoformat()
                    self._last_rssi_update = datetime.now()

                    if not self._client and device.rssi > RSSI_PRESENCE_THRESHOLD:
                        await self._connect()

                    self._is_present = device.rssi > RSSI_PRESENCE_THRESHOLD

                    _LOGGER.debug(
                        "%s RSSI: %s dBm, present: %s",
                        self._name,
                        device.rssi,
                        self._is_present,
                    )
                else:
                    self._rssi = None
                    self._is_present = False
                    if self._client:
                        await self._disconnect()

                if self._client and self._last_rssi_update:
                    delta = (datetime.now() - self._last_rssi_update).total_seconds()
                    if delta > CONNECTION_TIMEOUT:
                        _LOGGER.debug("%s timeout, disconnecting", self._name)
                        await self._disconnect()

                self.async_write_ha_state()

            except Exception as e:
                _LOGGER.debug("Scan loop error: %s", e)

            await asyncio.sleep(5)

    async def _connect(self):
        try:
            _LOGGER.info("Connecting to %s (%s)...", self._name, self._mac)

            self._client = BleakClient(self._mac, timeout=10.0)
            await self._client.connect()

            battery_char = await self._client.read_gatt_char(CHARGE_LVL)
            self._battery = int(battery_char[0])
            _LOGGER.info("%s battery: %s%%", self._name, self._battery)

            await self._client.start_notify(BUTTON_CHAR, self._button_notify_handler)
            _LOGGER.info("%s button notifications enabled", self._name)

            _LOGGER.info("%s connected successfully", self._name)

        except Exception as e:
            _LOGGER.error("Connection failed for %s: %s", self._name, e)
            await self._disconnect()

    async def _disconnect(self):
        if self._client:
            try:
                await self._client.stop_notify(BUTTON_CHAR)
            except Exception:
                pass
            try:
                await self._client.disconnect()
            except Exception:
                pass
            self._client = None
            self._battery = None
            _LOGGER.debug("%s disconnected", self._name)

    def _button_notify_handler(self, sender, data):
        if len(data) > 0 and data[0] == 0x01:
            _LOGGER.info("%s button pressed", self._name)
            if self._button_callback:
                self.hass.async_create_task(self._button_callback())


async def async_setup_entry(hass, entry, async_add_entities):
    """Настройка device tracker платформы."""
    tracker = hass.data[DOMAIN][entry.entry_id]["tracker"]
    async_add_entities([tracker], True)
    _LOGGER.info("Device tracker entity added for %s", entry.data["name"])
