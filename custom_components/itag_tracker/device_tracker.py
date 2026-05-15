"""Device tracker для iTAG."""

from homeassistant.components.device_tracker import SourceType
from homeassistant.components.device_tracker.config_entry import BaseTrackerEntity
from homeassistant.const import STATE_HOME, STATE_NOT_HOME
from homeassistant.helpers import device_registry as dr

from .const import DOMAIN


async def async_setup_entry(hass, entry, async_add_entities):
    """Настройка device tracker."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([iTAGDeviceTracker(coordinator, entry)], True)


class iTAGDeviceTracker(BaseTrackerEntity):
    """Трекер присутствия iTAG."""

    _attr_should_poll = False
    _attr_has_entity_name = True
    _attr_name = None

    def __init__(self, coordinator, entry):
        self.coordinator = coordinator
        self.entry = entry
        self._attr_unique_id = f"{coordinator.mac_normalized}_tracker"

    @property
    def device_info(self):
        """Привязка к устройству."""
        return {
            "identifiers": {(DOMAIN, self.coordinator.mac_normalized)},
        }

    @property
    def state(self):
        """Состояние присутствия."""
        return STATE_HOME if self.coordinator.is_present else STATE_NOT_HOME

    @property
    def source_type(self):
        """Тип источника."""
        return SourceType.BLUETOOTH

    @property
    def extra_state_attributes(self):
        """Дополнительные атрибуты."""
        attrs = {}
        if self.coordinator.rssi is not None:
            attrs["rssi"] = self.coordinator.rssi
        if self.coordinator.battery is not None:
            attrs["battery"] = self.coordinator.battery
        if self.coordinator.last_seen is not None:
            attrs["last_seen"] = self.coordinator.last_seen
        return attrs

    @property
    def available(self):
        """Доступность сущности."""
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
