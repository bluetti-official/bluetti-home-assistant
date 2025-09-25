"""Application credentials platform for the BLUETTI integration."""

from homeassistant.core import HomeAssistant
from homeassistant.components.application_credentials import AuthorizationServer

from .api.bluetti import APPLICATION_PROFILE
from .const import DOMAIN


async def async_get_authorization_server(hass: HomeAssistant) -> AuthorizationServer:
    """Return authorization server."""
    await APPLICATION_PROFILE.load_config(hass)
    return AuthorizationServer(
        authorize_url=APPLICATION_PROFILE.config["server"]["sso"] + "/oauth2/grant",
        token_url=APPLICATION_PROFILE.config["server"]["sso"] + "/oauth2/token",
    )
