"""iTAG Tracker integration for Home Assistant."""

import asyncio
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import CONF_MAC_ADDRESS
from homeassistant.helpers import device_registry as dr

from .const import DOMAIN
from .ble_scanner import iTAGManager

PLATFORMS = ["sensor", "binary_sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up iTAG Tracker from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    
    # Store the manager instance
    manager = iTAGManager(hass)
    hass.data[DOMAIN][entry.entry_id] = {
        "manager": manager,
        "mac": entry.data["mac_address"],
        "name": entry.data["name"],
        "scan_interval": entry.options.get("scan_interval", 60)
    }
    
    # Register alert service
    async def alert_service(call):
        """Handle alert service call."""
        entity_id = call.data.get("entity_id")
        duration = call.data.get("duration", 10)
        
        # Find the device by entity_id
        for entry_id, data in hass.data[DOMAIN].items():
            if entry_id != "manager":
                continue
            # Forward to device
            if hasattr(manager, "alert_device"):
                await manager.alert_device(
                    data.get("mac"), 
                    duration
                )
    
    hass.services.async_register(DOMAIN, "alert", alert_service)
    
    # Forward entry setup to platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    # Start scanner
    await manager.start()
    
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        # Stop scanner
        manager = hass.data[DOMAIN].get("manager")
        if manager:
            await manager.stop()
        hass.data[DOMAIN].pop(entry.entry_id)
    
    return unload_ok


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove a config entry."""
    # Clean up device registry
    device_registry = dr.async_get(hass)
    device_registry.async_remove_device(
        device_registry.async_get_device(
            identifiers={(DOMAIN, entry.data["mac_address"])}
        )
    )