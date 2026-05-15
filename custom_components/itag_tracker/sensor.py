"""Сенсор RSSI для iTAG."""

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import SIGNAL_STRENGTH_DECIBELS_MILLIWATT

from .const import DOMAIN


async def async_setup_entry(hass, entry, async_add_entities):
    """Настройка сенсора RSSI."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([iTAGRSSISensor(coordinator, entry)], True)


class iTAGRSSISensor(SensorEntity):
    """Сенсор RSSI."""

    _attr_should_poll = False
    _attr_native_unit_of_measurement = SIGNAL_STRENGTH_DECIBELS_MILLIWATT
    _attr_device_class = "signal_strength"

    def __init__(self, coordinator, entry):
        self.coordinator = coordinator
        self._attr_name = f"{entry.data['name']} RSSI"
        self._attr_unique_id = f"{coordinator.mac.replace(':', '')}_rssi"

    @property
    def native_value(self):
        return self.coordinator.rssi

    @property
    def available(self):
        return self.coordinator.is_available

    async def async_added_to_hass(self):
        self.async_on_remove(
            self.coordinator.async_add_listener(self._handle_update)
        )

    def _handle_update(self):
        self.async_write_ha_state()
