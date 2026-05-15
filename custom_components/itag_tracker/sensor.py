"""Сенсоры для iTAG."""

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import SIGNAL_STRENGTH_DECIBELS_MILLIWATT, PERCENTAGE
from homeassistant.helpers import device_registry as dr

from .const import DOMAIN


async def async_setup_entry(hass, entry, async_add_entities):
    """Настройка сенсоров."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        iTAGRSSISensor(coordinator, entry),
        iTAGBatterySensor(coordinator, entry),
    ], True)


class iTAGRSSISensor(SensorEntity):
    """Сенсор RSSI."""

    _attr_should_poll = False
    _attr_device_class = "signal_strength"
    _attr_native_unit_of_measurement = SIGNAL_STRENGTH_DECIBELS_MILLIWATT

    def __init__(self, coordinator, entry):
        self.coordinator = coordinator
        self.entry = entry
        self._attr_name = f"{entry.data['name']} RSSI"
        self._attr_unique_id = f"{coordinator.mac_normalized}_rssi"

    @property
    def device_info(self):
        """Привязка к устройству."""
        return {
            "identifiers": {(DOMAIN, self.coordinator.mac_normalized)},
        }

    @property
    def native_value(self):
        """Значение RSSI."""
        return self.coordinator.rssi

    @property
    def available(self):
        """Доступность."""
        return self.coordinator.rssi is not None

    async def async_added_to_hass(self):
        """При добавлении в Home Assistant."""
        await super().async_added_to_hass()
        self.async_on_remove(
            self.coordinator.async_add_listener(self._handle_update)
        )

    def _handle_update(self):
        """Обновление состояния."""
        self.async_write_ha_state()


class iTAGBatterySensor(SensorEntity):
    """Сенсор батареи."""

    _attr_should_poll = False
    _attr_device_class = "battery"
    _attr_native_unit_of_measurement = PERCENTAGE

    def __init__(self, coordinator, entry):
        self.coordinator = coordinator
        self.entry = entry
        self._attr_name = f"{entry.data['name']} Battery"
        self._attr_unique_id = f"{coordinator.mac_normalized}_battery"

    @property
    def device_info(self):
        """Привязка к устройству."""
        return {
            "identifiers": {(DOMAIN, self.coordinator.mac_normalized)},
        }

    @property
    def native_value(self):
        """Уровень батареи."""
        return self.coordinator.battery

    @property
    def available(self):
        """Доступность."""
        return self.coordinator.battery is not None

    async def async_added_to_hass(self):
        """При добавлении в Home Assistant."""
        await super().async_added_to_hass()
        self.async_on_remove(
            self.coordinator.async_add_listener(self._handle_update)
        )

    def _handle_update(self):
        """Обновление состояния."""
        self.async_write_ha_state()
