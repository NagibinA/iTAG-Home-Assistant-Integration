"""iTAG Tracker integration."""

import logging
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import device_registry as dr

from .const import DOMAIN
from .device_tracker import iTAGDeviceTracker

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor", "binary_sensor", "device_tracker"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up iTAG Tracker from a config entry."""
    mac = entry.data["mac_address"].upper()
    name = entry.data["name"]
    mac_normalized = mac.replace(":", "")

    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, mac_normalized)},
        name=name,
        manufacturer="iTAG",
        model="BLE Tracker",
        connections={(dr.CONNECTION_BLUETOOTH, mac)},
    )

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "mac": mac,
        "name": name,
        "mac_normalized": mac_normalized,
    }

    tracker = iTAGDeviceTracker(hass, entry)
    hass.data[DOMAIN][entry.entry_id]["tracker"] = tracker

    try:
        await tracker.start()
    except Exception as e:
        _LOGGER.error("Failed to start tracker: %s", e)
        return False

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    _LOGGER.info("iTAG Tracker setup complete for %s", name)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    tracker = hass.data[DOMAIN][entry.entry_id].get("tracker")
    if tracker:
        await tracker.stop()

    hass.data[DOMAIN].pop(entry.entry_id, None)
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
