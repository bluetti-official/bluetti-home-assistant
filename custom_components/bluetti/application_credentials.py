"""Application credentials platform for the BLUETTI integration."""

from homeassistant.components.application_credentials import AuthorizationServer
from homeassistant.core import HomeAssistant

from .const import BLUETTI_SSO_SERVER
from .profile.ApplicationConfig import ApplicationConfig


async def async_get_authorization_server(hass: HomeAssistant) -> AuthorizationServer:
    # applicationConfig = ApplicationConfig(hass)
    # applicationConfig.load_config(hass)

    """Return authorization server."""
    return AuthorizationServer(
        authorize_url=BLUETTI_SSO_SERVER + "/oauth2/grant",
        token_url=BLUETTI_SSO_SERVER + "/oauth2/token",
    )
