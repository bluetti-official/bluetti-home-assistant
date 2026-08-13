"""Application credentials platform for the BLUETTI integration.

Registers one OAuth2 implementation per region - global/default, US (#121)
and EU (#72) - so users whose traffic gets geo-resolved to the wrong region
can pick the correct one from the standard "Pick authentication method"
screen instead of editing files bundled with the integration, which would
be overwritten on the next update.
"""

from homeassistant.core import HomeAssistant
from homeassistant.components.application_credentials import (
    AuthImplementation,
    AuthorizationServer,
    ClientCredential,
)

from .api.bluetti import get_region_profile


async def async_get_auth_implementation(
    hass: HomeAssistant, auth_domain: str, credential: ClientCredential
) -> AuthImplementation:
    """Build the OAuth2 implementation for the given region's credential."""
    profile = get_region_profile(auth_domain)
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
