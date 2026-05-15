"""Координатор для iTAG Tracker с активным и пассивным режимом."""

import asyncio
import logging
from datetime import datetime, timedelta

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.components.bluetooth import async_ble_device_from_address
from bleak import BleakClient

from .const import (
    DOMAIN,
    SCAN_INTERVAL,
    RSSI_PRESENCE_THRESHOLD,
    RSSI_CONNECT_THRESHOLD,
    CONNECTION_TIMEOUT,
    BATTERY_CHAR_UUID,
    BUTTON_CHAR_UUID,
    ALT_BUTTON_CHAR_UUID,
)

_LOGGER = logging.getLogger(__name__)


class iTAGDataUpdateCoordinator(DataUpdateCoordinator):
    """Координатор для iTAG."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Инициализация координатора."""
        super().__init__(
            hass,
            _LOGGER,
            name=entry.data["name"],
            update_interval=timedelta(seconds=SCAN_INTERVAL),
        )
        self.entry = entry
        self.mac = entry.data["mac_address"].lower()
        self.name = entry.data["name"]
        self.mac_normalized = self.mac.replace(":", "")

        # Состояния
        self.rssi = None
        self.battery = None
        self.is_present = False
        self.last_seen = None

        # Управление подключением
        self._client = None
        self._button_callback = None
        self._is_connecting = False
        self._last_rssi_update = None

    def set_button_callback(self, callback):
        """Установка callback для кнопки."""
        self._button_callback = callback

    async def async_stop(self):
        """Остановка координатора."""
        await self._disconnect()

    async def _async_update_data(self):
        """Обновление данных (пассивный режим)."""
        # Получаем устройство через HA API
        ble_device = async_ble_device_from_address(self.hass, self.mac)

        if ble_device:
            self.rssi = ble_device.rssi
            self.last_seen = datetime.now().isoformat()
            self._last_rssi_update = datetime.now()
            was_present = self.is_present
            self.is_present = self.rssi > RSSI_PRESENCE_THRESHOLD

            _LOGGER.debug(
                "%s: RSSI=%s, present=%s (threshold=%s)",
                self.name, self.rssi, self.is_present, RSSI_PRESENCE_THRESHOLD
            )

            # Активное подключение при сильном сигнале
            if not self._client and not self._is_connecting and self.rssi > RSSI_CONNECT_THRESHOLD:
                self.hass.async_create_task(self._connect())

            # Отключение при слабом сигнале или таймауте
            if self._client:
                if not self.is_present:
                    await self._disconnect()
                elif self._last_rssi_update:
                    delta = (datetime.now() - self._last_rssi_update).total_seconds()
                    if delta > CONNECTION_TIMEOUT:
                        _LOGGER.debug("%s: connection timeout", self.name)
                        await self._disconnect()

        else:
            if self.rssi is not None:
                _LOGGER.debug("%s: device not found", self.name)
            self.rssi = None
            self.is_present = False
            if self._client:
                await self._disconnect()

        return {
            "rssi": self.rssi,
            "battery": self.battery,
            "is_present": self.is_present,
            "last_seen": self.last_seen,
        }

    async def _connect(self):
        """Активное подключение для чтения батареи и кнопки."""
        if self._client or self._is_connecting:
            return

        self._is_connecting = True
        try:
            _LOGGER.info("Connecting to %s (%s)...", self.name, self.mac)

            self._client = BleakClient(self.mac, timeout=10.0)
            await self._client.connect()
            _LOGGER.info("%s: connected", self.name)

            # Чтение батареи
            try:
                battery_char = await self._client.read_gatt_char(BATTERY_CHAR_UUID)
                self.battery = int(battery_char[0])
                _LOGGER.info("%s: battery = %s%%", self.name, self.battery)
            except Exception as e:
                _LOGGER.warning("%s: could not read battery: %s", self.name, e)

            # Подписка на кнопку (пробуем оба UUID)
            try:
                await self._client.start_notify(BUTTON_CHAR_UUID, self._button_notify_handler)
                _LOGGER.info("%s: button notifications enabled", self.name)
            except Exception:
                try:
                    await self._client.start_notify(ALT_BUTTON_CHAR_UUID, self._button_notify_handler)
                    _LOGGER.info("%s: button notifications enabled (alt)", self.name)
                except Exception as e:
                    _LOGGER.warning("%s: could not enable button: %s", self.name, e)

            self.async_update_listeners()

        except Exception as e:
            _LOGGER.error("%s: connection failed: %s", self.name, e)
            await self._disconnect()
        finally:
            self._is_connecting = False

    async def _disconnect(self):
        """Отключение от устройства."""
        if self._client:
            try:
                await self._client.stop_notify(BUTTON_CHAR_UUID)
            except Exception:
                pass
            try:
                await self._client.disconnect()
            except Exception:
                pass
            self._client = None
            self.battery = None
            _LOGGER.debug("%s: disconnected", self.name)

    def _button_notify_handler(self, sender, data):
        """Обработчик нажатия кнопки."""
        if len(data) > 0 and data[0] == 0x01:
            _LOGGER.info("%s: button pressed", self.name)
            if self._button_callback:
                self.hass.async_create_task(self._button_callback())
