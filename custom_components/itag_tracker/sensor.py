"""Сенсоры для iTAG Tracker: батарея и расстояние."""

import logging
import math
from datetime import datetime, timedelta

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import PERCENTAGE
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.event import async_track_time_interval
from bleak import BleakScanner

from .const import (
    DOMAIN,
    CHARGE_LVL,
    BATTERY_UPDATE_INTERVAL,
    PRESENCE_SCAN_INTERVAL,
    DEFAULT_TX_POWER,
    ENVIRONMENT_FACTOR,
    DISTANCE_CLOSE,
    DISTANCE_MEDIUM,
    DISTANCE_FAR,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    """Настройка сенсоров iTAG."""
    mac = entry.data["mac_address"]
    name = entry.data["name"]

    # Регистрация устройства
    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, mac)},
        name=name,
        manufacturer="iTAG",
        model="BLE Tracker",
        connections={(dr.CONNECTION_BLUETOOTH, mac)},
    )

    # Создаём сенсоры
    sensors = [
        iTAGBatterySensor(entry, mac, name),
        iTAGDistanceSensor(entry, mac, name),
    ]

    async_add_entities(sensors, True)

    # Батарея обновляется редко (раз в час)
    battery_sensor = sensors[0]
    async def update_battery(now):
        await battery_sensor.async_update()
    async_track_time_interval(hass, update_battery, timedelta(seconds=BATTERY_UPDATE_INTERVAL))


class iTAGBatterySensor(SensorEntity):
    """Сенсор уровня заряда батареи."""

    def __init__(self, entry, mac, name):
        self._entry = entry
        self._mac = mac
        self._name = name
        self._attr_name = f"{name} Battery"
        self._attr_unique_id = f"{mac}_battery"
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_device_class = "battery"
        self._attr_icon = "mdi:battery"
        self._attr_native_value = None
        self._last_update = None

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._mac)},
            "name": self._name,
        }

    @property
    def extra_state_attributes(self):
        if self._last_update:
            return {"last_seen": self._last_update}
        return {}

    async def async_update(self):
        """Обновление уровня батареи через BLE."""
        try:
            from bleak import BleakClient

            async with BleakClient(self._mac, timeout=10.0) as client:
                value = await client.read_gatt_char(CHARGE_LVL)
                self._attr_native_value = int(value[0])
                self._last_update = datetime.now().isoformat()
                _LOGGER.info(f"{self._name} battery: {self._attr_native_value}%")

        except Exception as e:
            _LOGGER.debug(f"Battery read error for {self._mac}: {e}")


class iTAGDistanceSensor(SensorEntity):
    """Сенсор расстояния на основе RSSI (без подключения, без писка)."""

    def __init__(self, entry, mac, name):
        self._entry = entry
        self._mac = mac.lower()
        self._name = name
        self._attr_name = f"{name} Distance"
        self._attr_unique_id = f"{mac}_distance"
        self._attr_icon = "mdi:ruler"
        self._distance = None
        self._distance_level = None
        self._rssi = None
        self._last_update = None
        self._update_count = 0

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._mac)},
            "name": self._name,
        }

    @property
    def native_value(self):
        """Текстовое представление расстояния: близко, средне, далеко, очень далеко."""
        return self._distance_level

    @property
    def extra_state_attributes(self):
        """Дополнительные атрибуты."""
        attrs = {}
        if self._distance is not None:
            attrs["distance_meters"] = round(self._distance, 2)
        if self._rssi is not None:
            attrs["rssi"] = self._rssi
            attrs["rssi_dbm"] = f"{self._rssi} dBm"
        if self._last_update:
            attrs["last_seen"] = self._last_update
        attrs["tx_power_used"] = DEFAULT_TX_POWER
        attrs["environment_factor"] = ENVIRONMENT_FACTOR
        return attrs

    def _calculate_distance(self, rssi):
        """Расчёт расстояния из RSSI."""
        if rssi is None:
            return None

        # Если сигнал сильнее эталонного — ближе 1 метра
        if rssi > DEFAULT_TX_POWER:
            ratio = (DEFAULT_TX_POWER - rssi) / 20
            distance = 1 - ratio
            if distance < 0.1:
                distance = 0.1
        else:
            exponent = (DEFAULT_TX_POWER - rssi) / (10 * ENVIRONMENT_FACTOR)
            distance = math.pow(10, exponent)

        # Ограничиваем
        if distance > 50:
            distance = 50
        elif distance < 0.1:
            distance = 0.1

        return distance

    def _get_distance_level(self, distance):
        """Преобразование метров в текстовый уровень."""
        if distance is None:
            return "unknown"

        if distance < DISTANCE_CLOSE:
            return "близко"
        elif distance < DISTANCE_MEDIUM:
            return "средне"
        elif distance < DISTANCE_FAR:
            return "далеко"
        else:
            return "очень далеко"

    async def async_update(self):
        """Сканирование RSSI и обновление расстояния."""
        self._update_count += 1

        # Каждые PRESENCE_SCAN_INTERVAL секунд обновляем
        # (вызывается из device_tracker или по таймеру)

        try:
            device = await BleakScanner.find_device_by_address(self._mac)

            if device:
                self._rssi = device.rssi
                self._distance = self._calculate_distance(self._rssi)
                self._distance_level = self._get_distance_level(self._distance)
                self._last_update = datetime.now().isoformat()

                _LOGGER.debug(
                    f"{self._name} RSSI: {self._rssi} dBm, "
                    f"Distance: {self._distance:.2f} m, "
                    f"Level: {self._distance_level}"
                )
            else:
                # Если устройство не найдено
                self._rssi = None
                self._distance = None
                self._distance_level = "не обнаружен"
                _LOGGER.debug(f"{self._name} not found")

        except Exception as e:
            _LOGGER.debug(f"Distance scan error for {self._name}: {e}")