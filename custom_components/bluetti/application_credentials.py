"""Application credentials platform for the BLUETTI integration.

Registers two OAuth2 implementations - the global/default BLUETTI cloud and
the US region - so users whose traffic gets geo-resolved to the wrong region
(see issue #121) can pick the correct one from the standard "Pick
authentication method" screen instead of editing files bundled with the
integration, which would be overwritten on the next update.
"""

from homeassistant.core import HomeAssistant
from homeassistant.components.application_credentials import (
    AuthImplementation,
    AuthorizationServer,
    ClientCredential,
)

from .api.bluetti import APPLICATION_PROFILE, US_APPLICATION_PROFILE
from .const import AUTH_DOMAIN_US


async def async_get_auth_implementation(
    hass: HomeAssistant, auth_domain: str, credential: ClientCredential
) -> AuthImplementation:
    """Build the OAuth2 implementation for the given region's credential."""
    if auth_domain == AUTH_DOMAIN_US:
        profile = US_APPLICATION_PROFILE
    else:
        profile = APPLICATION_PROFILE

    await profile.load_config(hass)
    sso = profile.config["server"]["sso"]

    return AuthImplementation(
        hass,
        auth_domain,
        credential,
        AuthorizationServer(
            authorize_url=f"{sso}/oauth2/grant",
            token_url=f"{sso}/oauth2/token",
        ),
    )
