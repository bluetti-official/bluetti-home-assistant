"""Tests for application_credentials.py."""

from custom_components.bluetti.api.bluetti import APPLICATION_PROFILE
from custom_components.bluetti.application_credentials import async_get_authorization_server


async def test_async_get_authorization_server(hass):
    server = await async_get_authorization_server(hass)

    gateway_sso = APPLICATION_PROFILE.config["server"]["sso"]
    assert server.authorize_url == f"{gateway_sso}/oauth2/grant"
    assert server.token_url == f"{gateway_sso}/oauth2/token"
