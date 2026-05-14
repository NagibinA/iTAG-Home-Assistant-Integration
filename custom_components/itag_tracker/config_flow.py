"""Config flow for iTAG Tracker."""

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
import re

DOMAIN = "itag_tracker"

DATA_SCHEMA = vol.Schema({
    vol.Required("name", default="iTAG"): str,
    vol.Required("mac_address"): str,
})

def is_valid_mac(mac: str) -> bool:
    """Validate MAC address."""
    return bool(re.match(r"^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$", mac))

class iTAGConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle config flow."""
    
    VERSION = 1
    
    async def async_step_user(self, user_input=None):
        """Handle user step."""
        errors = {}
        
        if user_input is not None:
            mac = user_input["mac_address"].upper()
            
            if not is_valid_mac(mac):
                errors["mac_address"] = "invalid_mac"
            else:
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
        )