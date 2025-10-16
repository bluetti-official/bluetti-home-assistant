"""Copyright (C) 2025 BLUETTI Corporation."""

from homeassistant.components.application_credentials import ClientCredential, async_import_client_credential
from .const import DOMAIN
from .oauth import OAuth2FlowHandler
from .api.bluetti import APPLICATION_PROFILE

class BluettiConfigFlow(OAuth2FlowHandler, domain=DOMAIN):
    """BLUETTI Custom Integration config flow."""
    
    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        # 在配置流开始时导入默认的客户端凭据
        await APPLICATION_PROFILE.load_config(self.hass)
        await async_import_client_credential(
            self.hass,
            DOMAIN,
            ClientCredential("HomeAssistant", "SG9tZUFzc2lzdGFudA=="),
        )
        return await super().async_step_user(user_input)