"""iTAG Tracker integration."""

import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from .const import DOMAIN, MANUFACTURER, MODEL
from .coordinator import iTAGDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["device_tracker", "sensor", "binary_sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up iTAG Tracker from a config entry."""
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}

    mac = entry.data["mac_address"]
    mac_normalized = mac.replace(":", "")

    # Регистрация устройства
    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, mac_normalized)},
        name=entry.data["name"],
        manufacturer=MANUFACTURER,
        model=MODEL,
        connections={(dr.CONNECTION_BLUETOOTH, mac)},
    )

    # Создание координатора
    coordinator = iTAGDataUpdateCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Настройка платформ
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Обновление при изменении опций
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    _LOGGER.info("iTAG Tracker setup complete for %s", entry.data["name"])
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload iTAG Tracker."""
    coordinator = hass.data[DOMAIN].get(entry.entry_id)
    if coordinator:
        await coordinator.async_stop()

    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id, None)

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await hass.config_entries.async_reload(entry.entry_id)
