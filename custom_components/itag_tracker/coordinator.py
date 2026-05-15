"""Data coordinator для iTAG Tracker с автоочисткой старых устройств."""

import asyncio
import logging
from datetime import datetime, timedelta

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from bleak import BleakScanner, BleakClient

from .const import (
    DOMAIN,
    RSSI_PRESENCE_THRESHOLD,
    RSSI_STRONG_SIGNAL,
    CONNECTION_TIMEOUT,
    CHARGE_LVL,
    BUTTON_CHAR,
    ALT_BUTTON_CHAR,
    SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)


class iTAGDataUpdateCoordinator(DataUpdateCoordinator):
    """Координатор для управления iTAG устройством с автоочисткой."""

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
        self.is_present = False
        self.rssi = None
        self.battery = None
        self.last_seen = None

        # Управление подключением
        self._client = None
        self._button_callback = None

        # Регистрируем устройство С ПРЕДВАРИТЕЛЬНОЙ ОЧИСТКОЙ
        self._register_device_clean()

    def _register_device_clean(self) -> None:
        """
        Регистрация устройства в device registry с ПРЕДВАРИТЕЛЬНЫМ удалением старых записей.
        Это ВАРИАНТ А - гарантированно чистое создание.
        """
        device_registry = dr.async_get(self.hass)

        # 1. Проверяем, есть ли УЖЕ устройство с таким MAC
        existing_device = device_registry.async_get_device(
            identifiers={(DOMAIN, self.mac_normalized)}
        )

        # 2. Если ЕСТЬ и оно активное (или "грязное"), мы его удаляем.
        if existing_device:
            _LOGGER.warning(
                "Found stale device %s (ID: %s), removing before fresh registration...",
                self.mac_normalized,
                existing_device.id
            )
            device_registry.async_remove_device(existing_device.id)
            _LOGGER.info("Stale device removed successfully")

        # 3. Теперь, когда "старого" устройства точно нет, создаём новое.
        device_registry.async_get_or_create(
            config_entry_id=self.entry.entry_id,
            identifiers={(DOMAIN, self.mac_normalized)},
            name=self.name,
            manufacturer="iTAG",
            model="BLE Tracker",
            connections={(dr.CONNECTION_BLUETOOTH, self.mac)},
        )
        _LOGGER.info("Fresh device registered: %s (%s)", self.name, self.mac_normalized)

    @property
    def device_info(self):
        """Для привязки сущностей к устройству (только identifiers!)."""
        return {
            "identifiers": {(DOMAIN, self.mac_normalized)},
        }

    def set_button_callback(self, callback):
        """Установка callback для кнопки."""
        self._button_callback = callback

    async def _async_update_data(self):
        """Обновление данных (вызывается каждые SCAN_INTERVAL секунд)."""
        try:
            device = await BleakScanner.find_device_by_address(self.mac, timeout=5)

            if device:
                self.rssi = device.rssi
                self.last_seen = datetime.now().isoformat()
                self.is_present = device.rssi > RSSI_PRESENCE_THRESHOLD

                # Подключаемся при сильном сигнале
                if not self._client and self.rssi > RSSI_STRONG_SIGNAL:
                    await self._connect()

                # Отключаемся при слабом сигнале
                if self._client and not self.is_present:
                    await self._disconnect()

                _LOGGER.debug(
                    "%s RSSI: %s dBm, present: %s",
                    self.name,
                    device.rssi,
                    self.is_present,
                )
            else:
                self.rssi = None
                self.is_present = False
                if self._client:
                    await self._disconnect()

            # Таймаут подключения
            if self._client and self.last_seen:
                last_seen_dt = datetime.fromisoformat(self.last_seen)
                delta = (datetime.now() - last_seen_dt).total_seconds()
                if delta > CONNECTION_TIMEOUT:
                    _LOGGER.debug("%s timeout, disconnecting", self.name)
                    await self._disconnect()

            return {
                "is_present": self.is_present,
                "rssi": self.rssi,
                "battery": self.battery,
                "last_seen": self.last_seen,
            }

        except Exception as e:
            _LOGGER.error("Update failed for %s: %s", self.name, e)
            raise UpdateFailed(f"Update failed: {e}")

    async def _connect(self):
        """Активное подключение."""
        if self._client:
            return
        try:
            _LOGGER.info("Connecting to %s (%s)...", self.name, self.mac)

            self._client = BleakClient(self.mac, timeout=10.0)
            await self._client.connect()

            # Читаем батарею
            try:
                battery_char = await self._client.read_gatt_char(CHARGE_LVL)
                self.battery = int(battery_char[0])
                _LOGGER.info("%s battery: %s%%", self.name, self.battery)
            except Exception as e:
                _LOGGER.warning("Could not read battery: %s", e)

            # Подписываемся на кнопку (пробуем оба UUID)
            try:
                await self._client.start_notify(BUTTON_CHAR, self._button_notify_handler)
                _LOGGER.info("%s button notifications enabled", self.name)
            except Exception:
                try:
                    await self._client.start_notify(ALT_BUTTON_CHAR, self._button_notify_handler)
                    _LOGGER.info("%s button notifications enabled (alt)", self.name)
                except Exception as e:
                    _LOGGER.warning("Could not enable button notifications: %s", e)

            _LOGGER.info("%s connected successfully", self.name)

            # Уведомляем подписчиков об изменении состояния
            self.async_update_listeners()

        except Exception as e:
            _LOGGER.error("Connection failed for %s: %s", self.name, e)
            await self._disconnect()

    async def _disconnect(self):
        """Отключение."""
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
            self.battery = None
            _LOGGER.debug("%s disconnected", self.name)

    def _button_notify_handler(self, sender, data):
        """Обработчик кнопки."""
        if len(data) > 0 and data[0] == 0x01:
            _LOGGER.info("%s button pressed", self.name)
            if self._button_callback:
                self.hass.async_create_task(self._button_callback())
