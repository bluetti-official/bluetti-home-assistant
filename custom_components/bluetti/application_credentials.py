"""Application credentials platform for the BLUETTI integration.

Provides the default (global) OAuth2 implementation. The US (#121) and EU
(#72) region implementations are registered directly in config_flow.py
instead - see the comment there for why application_credentials' storage
can't be reused for those without them silently colliding.
"""

from homeassistant.core import HomeAssistant
from homeassistant.components.application_credentials import AuthorizationServer

from .api.bluetti import APPLICATION_PROFILE


async def async_get_authorization_server(hass: HomeAssistant) -> AuthorizationServer:
    """Return authorization server."""
    await APPLICATION_PROFILE.load_config(hass)
    return AuthorizationServer(
        authorize_url=APPLICATION_PROFILE.config["server"]["sso"] + "/oauth2/grant",
        token_url=APPLICATION_PROFILE.config["server"]["sso"] + "/oauth2/token",
    )
