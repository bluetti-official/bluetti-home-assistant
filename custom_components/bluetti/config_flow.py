"""Copyright (C) 2025 BLUETTI Corporation."""

import voluptuous as vol

from homeassistant.components.application_credentials import ClientCredential, async_import_client_credential
from homeassistant.config_entries import ConfigEntry, OptionsFlowWithReload
from homeassistant.core import callback
from homeassistant.helpers.selector import SelectSelector, SelectSelectorConfig, SelectSelectorMode
from .const import DOMAIN, CONF_GATEWAY_REGION, GATEWAY_REGION_DEFAULT, GATEWAY_REGIONS
from .oauth import OAuth2FlowHandler
from .api.bluetti import APPLICATION_PROFILE, apply_gateway_region


class BluettiConfigFlow(OAuth2FlowHandler, domain=DOMAIN):
    """BLUETTI Custom Integration config flow."""

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> "BluettiOptionsFlow":
        """Options: cloud region."""
        return BluettiOptionsFlow()

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        # 在配置流开始时导入默认的客户端凭据
        await APPLICATION_PROFILE.load_config(self.hass)
        # On reconfigure, talk to the region already chosen for the entry
        entries = self.hass.config_entries.async_entries(DOMAIN)
        if entries:
            apply_gateway_region(entries[0])
        await async_import_client_credential(
            self.hass,
            DOMAIN,
            ClientCredential(APPLICATION_PROFILE.config["oauth"]["client-id"],
                             APPLICATION_PROFILE.config["oauth"]["client-secret"]),
        )
        return await super().async_step_user(user_input)


class BluettiOptionsFlow(OptionsFlowWithReload):
    """Choose the cloud region (gateway). The entry reloads when it changes."""

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(data={**self.config_entry.options, **user_input})

        current = self.config_entry.options.get(CONF_GATEWAY_REGION, GATEWAY_REGION_DEFAULT)
        schema = vol.Schema({
            vol.Required(CONF_GATEWAY_REGION, default=current): SelectSelector(
                SelectSelectorConfig(
                    options=[GATEWAY_REGION_DEFAULT, *GATEWAY_REGIONS],
                    translation_key=CONF_GATEWAY_REGION,
                    mode=SelectSelectorMode.DROPDOWN,
                )
            ),
        })
        return self.async_show_form(step_id="init", data_schema=schema)
