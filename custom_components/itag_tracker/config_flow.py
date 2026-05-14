"""Config flow for iTAG Tracker."""

import voluptuous as vol
import re
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN, DEFAULT_NAME

DATA_SCHEMA = vol.Schema({
    vol.Required("name", default=DEFAULT_NAME): cv.string,
    vol.Required("mac_address"): str,
    vol.Optional("scan_interval", default=60): cv.positive_int,
})


def is_valid_mac(mac: str) -> bool:
    """Validate MAC address format."""
    return bool(re.match(r"^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$", mac))


class iTAGConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle config flow for iTAG Tracker."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    async def async_step_user(self, user_input=None):
        """Handle user step."""
        errors = {}
        
        if user_input is not None:
            # Validate MAC address
            mac = user_input["mac_address"].upper()
            
            if not is_valid_mac(mac):
                errors["mac_address"] = "invalid_mac"
            else:
                # Check if already configured
                await self.async_set_unique_id(mac)
                self._abort_if_unique_id_configured()
                
                return self.async_create_entry(
                    title=user_input["name"],
                    data=user_input
                )
        
        return self.async_show_form(
            step_id="user",
            data_schema=DATA_SCHEMA,
            errors=errors,
            description_placements={
                "mac_address": "Format: AA:BB:CC:DD:EE:FF"
            }
        )
    
    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get options flow."""
        return iTAGOptionsFlow(config_entry)


class iTAGOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for iTAG Tracker."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Handle options step."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required(
                    "scan_interval",
                    default=self.config_entry.options.get("scan_interval", 60)
                ): vol.All(vol.Coerce(int), vol.Range(min=10, max=300)),
            })
        )