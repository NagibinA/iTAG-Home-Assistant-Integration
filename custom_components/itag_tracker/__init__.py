"""iTAG Tracker integration for Home Assistant."""

import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import CONF_MAC_ADDRESS
from homeassistant.helpers import device_registry as dr

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up iTAG Tracker from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    
    # Store config
    hass.data[DOMAIN][entry.entry_id] = {
        "mac": entry.data["mac_address"],
        "name": entry.data["name"],
        "scan_interval": entry.options.get("scan_interval", 60)
    }
    
    # Register alert service
    async def alert_service(call):
        """Handle alert service call."""
        entity_id = call.data.get("entity_id")
        duration = call.data.get("duration", 10)
        _LOGGER.info(f"Alert service called for {entity_id} with duration {duration}")
        # TODO: Implement actual alert
        hass.components.persistent_notification.create(
            f"Alert triggered for {duration} seconds",
            title="iTAG Alert"
        )
    
    hass.services.async_register(DOMAIN, "alert", alert_service)
    
    # Forward entry setup to platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    
    return unload_ok


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove a config entry."""
    # Clean up device registry
    device_registry = dr.async_get(hass)
    device = device_registry.async_get_device(
        identifiers={(DOMAIN, entry.data["mac_address"])}
    )
    if device:
        device_registry.async_remove_device(device.id)