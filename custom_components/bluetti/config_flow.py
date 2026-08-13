"""Copyright (C) 2025 BLUETTI Corporation."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback
from homeassistant.components.application_credentials import ClientCredential, async_import_client_credential
from .const import AUTH_DOMAIN_EU, AUTH_DOMAIN_US, DOMAIN
from .oauth import OAuth2FlowHandler
from .options_flow import BluettiOptionsFlowHandler
from .api.bluetti import APPLICATION_PROFILE

class BluettiConfigFlow(OAuth2FlowHandler, domain=DOMAIN):
    """BLUETTI Custom Integration config flow."""

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        # 在配置流开始时导入默认的客户端凭据
        await APPLICATION_PROFILE.load_config(self.hass)
        # Global/default region.
        await async_import_client_credential(
            self.hass,
            DOMAIN,
            ClientCredential("HomeAssistant", "SG9tZUFzc2lzdGFudA==", name="Global (default)"),
            auth_domain=DOMAIN,
        )
        # US region, for accounts affected by geo-IP routing issues (#121).
        await async_import_client_credential(
            self.hass,
            DOMAIN,
            ClientCredential("HomeAssistant", "SG9tZUFzc2lzdGFudA==", name="US"),
            auth_domain=AUTH_DOMAIN_US,
        )
        # EU region: same login endpoint as the default, different data
        # gateway (#72).
        await async_import_client_credential(
            self.hass,
            DOMAIN,
            ClientCredential("HomeAssistant", "SG9tZUFzc2lzdGFudA==", name="EU"),
            auth_domain=AUTH_DOMAIN_EU,
        )
        return await super().async_step_user(user_input)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> BluettiOptionsFlowHandler:
        """Return the options flow used to add more devices later."""
        return BluettiOptionsFlowHandler()