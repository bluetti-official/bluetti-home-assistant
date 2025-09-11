"""Application credentials platform for the BLUETTI integration."""

from homeassistant.core import HomeAssistant
from homeassistant.components.application_credentials import AuthorizationServer,ClientCredential,async_import_client_credential

from .api.bluetti import APPLICATION_PROFILE
from .const import DOMAIN


async def async_get_authorization_server(hass: HomeAssistant) -> AuthorizationServer:
    """Return authorization server."""
    await APPLICATION_PROFILE.load_config(hass)
    #set default client_id and secret
    await async_import_client_credential(
            hass,
            DOMAIN,
            ClientCredential(
                APPLICATION_PROFILE.config["server"]["client-id"],
                APPLICATION_PROFILE.config["server"]["client-secret"],
            ),
        )
    return AuthorizationServer(
        authorize_url=APPLICATION_PROFILE.config["server"]["sso"] + "/oauth2/grant",
        token_url=APPLICATION_PROFILE.config["server"]["sso"] + "/oauth2/token",
    )
