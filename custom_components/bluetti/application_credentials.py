"""Application credentials platform for the BLUETTI integration."""

from homeassistant.core import HomeAssistant
from homeassistant.components.application_credentials import AuthorizationServer

from .api.bluetti import APPLICATION_PROFILE


async def async_get_authorization_server(hass: HomeAssistant) -> AuthorizationServer:
    """Return authorization server."""
    return AuthorizationServer(
        authorize_url=APPLICATION_PROFILE.config["server"]["sso"] + "/oauth2/grant",
        token_url=APPLICATION_PROFILE.config["server"]["sso"] + "/oauth2/token",
    )
