"""Config flow для iTAG Tracker."""

import re
import voluptuous as vol
from homeassistant import config_entries
from .const import DOMAIN


def is_valid_mac(mac: str) -> bool:
    return bool(re.match(r"^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$", mac))


class iTAGConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            name = user_input["name"].strip()
            mac = user_input["mac_address"].upper()

            if not is_valid_mac(mac):
                errors["mac_address"] = "invalid_mac"
            elif not name:
                errors["name"] = "invalid_name"
            else:
                await self.async_set_unique_id(mac)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=name,
                    data={"name": name, "mac_address": mac},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("name", default="iTAG"): str,
                vol.Required("mac_address"): str,
            }),
            errors=errors,
        )
