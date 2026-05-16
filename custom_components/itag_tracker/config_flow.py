"""Config flow for iTAG BLE integration."""
from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_ADDRESS, CONF_NAME
from homeassistant.components.bluetooth import async_discovered_service_info
from homeassistant.data_entry_flow import FlowResult
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN


class ITAGConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for iTAG."""

    VERSION = 1

    async def async_step_user(self, user_input=None) -> FlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            address = user_input[CONF_ADDRESS]
            if address == "manual":
                return await self.async_step_manual()
            
            await self.async_set_unique_id(address)
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=user_input[CONF_NAME],
                data={
                    "mac": address,
                    CONF_NAME: user_input[CONF_NAME],
                },
            )

        discovered = async_discovered_service_info(self.hass)
        devices = {"manual": "Enter MAC address manually"}
        
        for discovery in discovered:
            address = discovery.address
            name = discovery.name or address
            if name.rstrip() == "iTAG":
                devices[address] = f"{name} ({address})"

        data_schema = vol.Schema({
            vol.Required(CONF_ADDRESS): vol.In(devices),
            vol.Required(CONF_NAME, default="iTAG"): cv.string,
        })

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )

    async def async_step_manual(self, user_input=None) -> FlowResult:
        """Handle manual MAC input."""
        if user_input is not None:
            address = user_input[CONF_ADDRESS]
            await self.async_set_unique_id(address)
            self._abort_if_unique_id_configured()
            
            return self.async_create_entry(
                title=user_input[CONF_NAME],
                data={
                    "mac": address,
                    CONF_NAME: user_input[CONF_NAME],
                },
            )
        
        data_schema = vol.Schema({
            vol.Required(CONF_ADDRESS): cv.string,
            vol.Required(CONF_NAME, default="iTAG"): cv.string,
        })
        
        return self.async_show_form(step_id="manual", data_schema=data_schema)
