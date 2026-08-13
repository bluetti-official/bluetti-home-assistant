"""Options flow for the BLUETTI integration.

Lets the user add devices bound to their BLUETTI account after the initial
setup, without going through the OAuth2 login flow again (the stored token
is reused).
"""

from __future__ import annotations

import logging

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, OptionsFlow, ConfigFlowResult
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api.bluetti import get_region_profile
from .api.product_client import ProductClient

__LOGGER__ = logging.getLogger(__name__)


class BluettiOptionsFlowHandler(OptionsFlow):
    """Handle an options flow to add more BLUETTI devices to an existing entry."""

    async def async_step_init(self, user_input: dict | None = None) -> ConfigFlowResult:
        """Let the user pick additional devices from their BLUETTI account."""
        entry: ConfigEntry = self.config_entry

        if user_input is not None:
            selected = user_input["devices"]
            try:
                await self._product_client.bind_devices({"bindSnList": selected})
            except Exception as err:
                __LOGGER__.error("Failed to bind BLUETTI devices: %s", err)
                return self.async_abort(reason="cannot_connect")

            current_devices = entry.options.get("devices", [])
            merged_devices = list(set(current_devices) | set(selected))

            existing_products = entry.data.get("products", [])
            existing_sns = {p.get("sn") if isinstance(p, dict) else p.sn for p in existing_products}
            new_products = [p for p in self._products if p.sn not in existing_sns]
            merged_products = existing_products + [p.model_dump() for p in new_products]

            self.hass.config_entries.async_update_entry(
                entry, data={**entry.data, "products": merged_products}
            )

            return self.async_create_entry(data={"devices": merged_devices})

        access_token = entry.data["token"]["access_token"]
        region_profile = get_region_profile(entry.data.get("auth_implementation"))
        await region_profile.load_config(self.hass)
        http_session = async_get_clientsession(self.hass)
        product_client = ProductClient(
            http_session, access_token, self.hass,
            gateway_url=region_profile.config["server"]["gateway"],
        )
        try:
            products = await product_client.get_user_products()
        except Exception as err:
            __LOGGER__.error("Failed to fetch BLUETTI products: %s", err)
            return self.async_abort(reason="cannot_connect")

        self._product_client = product_client
        self._products = products.data

        enabled_devices = set(entry.options.get("devices", []))
        available_devices = {
            product.sn: f"{product.name} - {product.sn}"
            for product in products.data
            if product.sn not in enabled_devices
        }

        if not products.data:
            return self.async_abort(reason="no_devices_available")

        if not available_devices:
            return self.async_abort(reason="all_devices_exists")

        schema = vol.Schema(
            {
                vol.Required(
                    "devices",
                    default=list(available_devices.keys()),
                ): cv.multi_select(available_devices)
            }
        )

        return self.async_show_form(step_id="init", data_schema=schema)
