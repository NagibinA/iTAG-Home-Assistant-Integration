"""iTAG Tracker integration."""

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import device_registry as dr

from .const import DOMAIN
from .device_tracker import iTAGDeviceTracker

PLATFORMS = ["sensor", "binary_sensor", "device_tracker"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up iTAG Tracker from a config entry."""
    mac = entry.data["mac_address"]
    name = entry.data["name"]

    # Регистрируем устройство один раз
    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, mac)},
        name=name,
        manufacturer="iTAG",
        model="BLE Tracker",
        connections={(dr.CONNECTION_BLUETOOTH, mac)},
    )

    # Сохраняем данные
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "mac": mac,
        "name": name,
    }

    # Создаём device tracker (управляет подключением)
    tracker = iTAGDeviceTracker(hass, entry)
    hass.data[DOMAIN][entry.entry_id]["tracker"] = tracker
    
    # Запускаем сканирование
    await tracker.start()

    # Настраиваем платформы
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Останавливаем трекер
    tracker = hass.data[DOMAIN][entry.entry_id].get("tracker")
    if tracker:
        await tracker.stop()
    
    hass.data[DOMAIN].pop(entry.entry_id, None)
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)