"""Config flow для iTAG Tracker."""

import voluptuous as vol
import re

from homeassistant import config_entries
from homeassistant.core import callback

from .const import DOMAIN


def is_valid_mac(mac: str) -> bool:
    """Проверка формата MAC-адреса."""
    return bool(re.match(r"^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$", mac))


def normalize_mac(mac: str) -> str:
    """Нормализация MAC-адреса."""
    return mac.upper()


class iTAGConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Настройка iTAG Tracker."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Шаг настройки: ввод имени и MAC."""
        errors = {}

        if user_input is not None:
            name = user_input["name"].strip()
            mac = normalize_mac(user_input["mac_address"])

            if not is_valid_mac(mac):
                errors["mac_address"] = "invalid_mac"
            elif not name:
                errors["name"] = "invalid_name"
            else:
                await self.async_set_unique_id(mac)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=name,
                    data={
                        "name": name,
                        "mac_address": mac,
                    },
                )

        data_schema = vol.Schema({
            vol.Required("name", default="iTAG"): str,
            vol.Required("mac_address"): str,
        })

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )
