"""Copyright (C) 2025 BLUETTI Corporation."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback
from homeassistant.helpers.config_entry_oauth2_flow import (
    LocalOAuth2Implementation,
    async_register_implementation,
)
from .const import AUTH_DOMAIN_EU, AUTH_DOMAIN_US, DOMAIN
from .oauth import OAuth2FlowHandler
from .options_flow import BluettiOptionsFlowHandler
from .api.bluetti import APPLICATION_PROFILE, EU_APPLICATION_PROFILE, US_APPLICATION_PROFILE

# BLUETTI's public OAuth client for the Home Assistant integration (not a
# per-user secret - shared by every installation, same as any other public/
# native OAuth client per RFC 8252). _CLIENT_SECRET base64-decodes to the
# literal string "HomeAssistant"; there is nothing confidential to redact
# here, and this predates this branch's changes.
_CLIENT_ID = "HomeAssistant"
_CLIENT_SECRET = "SG9tZUFzc2lzdGFudA=="

# Registration order controls both the display order and the pre-selected
# default on the "Pick authentication method" screen (Home Assistant shows
# them in dict-insertion order and defaults to the first one) - Global goes
# first so it stays the recommended default.
_REGIONS = (
    (DOMAIN, "Global (default)", APPLICATION_PROFILE),
    (AUTH_DOMAIN_US, "US", US_APPLICATION_PROFILE),
    (AUTH_DOMAIN_EU, "EU", EU_APPLICATION_PROFILE),
)


class _NamedOAuth2Implementation(LocalOAuth2Implementation):
    """A LocalOAuth2Implementation with a caller-supplied display name.

    LocalOAuth2Implementation.name is hardcoded to "Configuration.yaml",
    which would make every region look identical on the picker screen.
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
        # One implementation per BLUETTI cloud region (#121, #72), all
        # registered directly: application_credentials' storage keys
        # imported credentials by (domain, client_id) only, ignoring which
        # region they're for, so importing more than one there under the
        # same shared public client_id silently collapses them into a
        # single entry and the region picker never appears.
        for auth_domain, name, profile in _REGIONS:
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
