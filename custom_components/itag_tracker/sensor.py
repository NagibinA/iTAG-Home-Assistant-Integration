"""Сенсоры для iTAG Tracker: батарея и расстояние."""

import logging
import math

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import PERCENTAGE

from .const import (
    DOMAIN,
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
    tracker = hass.data[DOMAIN][entry.entry_id]["tracker"]

    sensors = [
        iTAGBatterySensor(entry, mac, name, tracker),
        iTAGDistanceSensor(entry, mac, name, tracker),
    ]

    async_add_entities(sensors, True)


class iTAGBatterySensor(SensorEntity):
    """Сенсор уровня заряда батареи."""

    def __init__(self, entry, mac, name, tracker):
        self._entry = entry
        self._mac = mac
        self._name = name
        self._tracker = tracker
        self._attr_name = f"{name} Battery"
        self._attr_unique_id = f"{mac}_battery"
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_device_class = "battery"
        self._attr_icon = "mdi:battery"
        self._attr_native_value = None

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._mac)},
        }

    async def async_update(self):
        """Обновление батареи из tracker."""
        self._attr_native_value = self._tracker.get_battery()


class iTAGDistanceSensor(SensorEntity):
    """Сенсор расстояния на основе RSSI."""

    def __init__(self, entry, mac, name, tracker):
        self._entry = entry
        self._mac = mac.lower()
        self._name = name
        self._tracker = tracker
        self._attr_name = f"{name} Distance"
        self._attr_unique_id = f"{mac}_distance"
        self._attr_icon = "mdi:ruler"
        self._distance = None
        self._distance_level = None

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._mac)},
        }

    @property
    def native_value(self):
        return self._distance_level

    @property
    def extra_state_attributes(self):
        attrs = {}
        if self._distance is not None:
            attrs["distance_meters"] = round(self._distance, 2)
        rssi = self._tracker.get_rssi()
        if rssi is not None:
            attrs["rssi"] = rssi
        return attrs

    def _calculate_distance(self, rssi):
        if rssi is None:
            return None

        exponent = (DEFAULT_TX_POWER - rssi) / (10 * ENVIRONMENT_FACTOR)
        distance = math.pow(10, exponent)

        if distance > 50:
            distance = 50
        elif distance < 0.1:
            distance = 0.1

        return distance

    def _get_distance_level(self, distance):
        if distance is None:
            return "не обнаружен"

        if distance < DISTANCE_CLOSE:
            return "близко"
        elif distance < DISTANCE_MEDIUM:
            return "средне"
        elif distance < DISTANCE_FAR:
            return "далеко"
        else:
            return "очень далеко"

    async def async_update(self):
        """Обновление расстояния из tracker."""
        rssi = self._tracker.get_rssi()
        if rssi is not None:
            self._distance = self._calculate_distance(rssi)
            self._distance_level = self._get_distance_level(self._distance)
        else:
            self._distance = None
            self._distance_level = "не обнаружен"