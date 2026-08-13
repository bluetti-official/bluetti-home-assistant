"""Tests for application_credentials.py."""

from homeassistant.components.application_credentials import ClientCredential

from custom_components.bluetti.api.bluetti import APPLICATION_PROFILE, US_APPLICATION_PROFILE
from custom_components.bluetti.application_credentials import async_get_auth_implementation
from custom_components.bluetti.const import AUTH_DOMAIN_US, DOMAIN


async def test_global_auth_domain_uses_default_profile(hass):
    credential = ClientCredential("id", "secret", name="Global (default)")

    implementation = await async_get_auth_implementation(hass, DOMAIN, credential)

    sso = APPLICATION_PROFILE.config["server"]["sso"]
    assert implementation.authorize_url == f"{sso}/oauth2/grant"
    assert implementation.token_url == f"{sso}/oauth2/token"
    assert implementation.domain == DOMAIN


async def test_us_auth_domain_uses_us_profile(hass):
    credential = ClientCredential("id", "secret", name="US")

    implementation = await async_get_auth_implementation(hass, AUTH_DOMAIN_US, credential)

    sso = US_APPLICATION_PROFILE.config["server"]["sso"]
    assert implementation.authorize_url == f"{sso}/oauth2/grant"
    assert implementation.token_url == f"{sso}/oauth2/token"
    assert implementation.domain == AUTH_DOMAIN_US
    # The US and global SSO endpoints must actually differ, otherwise this
    # feature does nothing for accounts affected by issue #121.
    assert sso != APPLICATION_PROFILE.config["server"]["sso"]
