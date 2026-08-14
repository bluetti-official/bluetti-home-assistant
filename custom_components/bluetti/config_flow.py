"""Copyright (C) 2025 BLUETTI Corporation."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback
from homeassistant.components.application_credentials import ClientCredential, async_import_client_credential
from homeassistant.helpers.config_entry_oauth2_flow import (
    LocalOAuth2Implementation,
    async_register_implementation,
)
from .const import AUTH_DOMAIN_EU, AUTH_DOMAIN_US, DOMAIN
from .oauth import OAuth2FlowHandler
from .options_flow import BluettiOptionsFlowHandler
from .api.bluetti import APPLICATION_PROFILE, EU_APPLICATION_PROFILE, US_APPLICATION_PROFILE

_CLIENT_ID = "HomeAssistant"
_CLIENT_SECRET = "SG9tZUFzc2lzdGFudA=="


class _NamedOAuth2Implementation(LocalOAuth2Implementation):
    """A LocalOAuth2Implementation with a caller-supplied display name.

    LocalOAuth2Implementation.name is hardcoded to "Configuration.yaml",
    which would make every region show up identically on the "Pick
    authentication method" screen.
    """

    def __init__(self, hass, domain, client_id, client_secret, authorize_url, token_url, name):
        super().__init__(hass, domain, client_id, client_secret, authorize_url, token_url)
        self._display_name = name

    @property
    def name(self) -> str:
        return self._display_name


class BluettiConfigFlow(OAuth2FlowHandler, domain=DOMAIN):
    """BLUETTI Custom Integration config flow."""

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        # 在配置流开始时导入默认的客户端凭据
        await APPLICATION_PROFILE.load_config(self.hass)
        # Global/default region, via application_credentials - existing
        # entries already reference this auth_domain, so this path stays
        # unchanged.
        await async_import_client_credential(
            self.hass,
            DOMAIN,
            ClientCredential(_CLIENT_ID, _CLIENT_SECRET, name="Global (default)"),
            auth_domain=DOMAIN,
        )

        # US (#121) and EU (#72) regions: application_credentials' storage
        # keys imported credentials by (domain, client_id) only, ignoring
        # auth_domain. Since every region shares the same public client_id,
        # importing more than one via async_import_client_credential
        # silently no-ops after the first, and the region picker never
        # appears. Register these two directly instead, which has no such
        # collision (keyed by auth_domain).
        for auth_domain, name, profile in (
            (AUTH_DOMAIN_US, "US", US_APPLICATION_PROFILE),
            (AUTH_DOMAIN_EU, "EU", EU_APPLICATION_PROFILE),
        ):
            await profile.load_config(self.hass)
            sso = profile.config["server"]["sso"]
            async_register_implementation(
                self.hass,
                DOMAIN,
                _NamedOAuth2Implementation(
                    self.hass,
                    auth_domain,
                    _CLIENT_ID,
                    _CLIENT_SECRET,
                    f"{sso}/oauth2/grant",
                    f"{sso}/oauth2/token",
                    name,
                ),
            )

        return await super().async_step_user(user_input)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> BluettiOptionsFlowHandler:
        """Return the options flow used to add more devices later."""
        return BluettiOptionsFlowHandler()
