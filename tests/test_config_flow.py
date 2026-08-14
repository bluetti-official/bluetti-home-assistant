"""Tests for config_flow.py."""

from unittest.mock import AsyncMock, patch

from homeassistant.helpers import config_entry_oauth2_flow
from homeassistant.setup import async_setup_component

from custom_components.bluetti.config_flow import BluettiConfigFlow
from custom_components.bluetti.const import AUTH_DOMAIN_EU, AUTH_DOMAIN_US, DOMAIN


async def test_async_step_user_imports_credentials_and_delegates(hass, enable_custom_integrations):
    await async_setup_component(hass, "application_credentials", {})

    flow = BluettiConfigFlow()
    flow.hass = hass

    with patch.object(
        config_entry_oauth2_flow.AbstractOAuth2FlowHandler,
        "async_step_user",
        new=AsyncMock(return_value={"type": "form", "step_id": "pick_implementation"}),
    ) as mock_super:
        result = await flow.async_step_user(None)

    mock_super.assert_awaited_once_with(None)
    assert result["step_id"] == "pick_implementation"


async def test_async_step_user_registers_three_distinct_implementations(hass, enable_custom_integrations):
    """Regression test: all three regions previously shared the same
    client_id, which made application_credentials' storage collapse them
    into a single stored credential (keyed by domain+client_id, not
    auth_domain) - only "Global" ever got registered, and Home Assistant
    silently skips the "Pick authentication method" screen when there is
    only one implementation, so users never saw a region choice at all.
    """
    await async_setup_component(hass, "application_credentials", {})

    flow = BluettiConfigFlow()
    flow.hass = hass

    with patch.object(
        config_entry_oauth2_flow.AbstractOAuth2FlowHandler,
        "async_step_user",
        new=AsyncMock(return_value={"type": "form", "step_id": "pick_implementation"}),
    ):
        await flow.async_step_user(None)

    implementations = await config_entry_oauth2_flow.async_get_implementations(hass, DOMAIN)

    assert set(implementations.keys()) == {DOMAIN, AUTH_DOMAIN_US, AUTH_DOMAIN_EU}
    assert implementations[DOMAIN].name == "Global (default)"
    assert implementations[AUTH_DOMAIN_US].name == "US"
    assert implementations[AUTH_DOMAIN_EU].name == "EU"


async def test_the_real_pick_implementation_step_shows_all_three_regions(hass, enable_custom_integrations):
    """End-to-end: the actual HA "Pick authentication method" step (not
    mocked) must present all three regions, not silently auto-pick one."""
    await async_setup_component(hass, "application_credentials", {})

    flow = BluettiConfigFlow()
    flow.hass = hass
    flow.context = {"source": "user"}

    result = await flow.async_step_user(None)

    assert result["type"] == "form"
    assert result["step_id"] == "pick_implementation"
    choices = result["data_schema"].schema["implementation"].container
    assert set(choices) == {DOMAIN, AUTH_DOMAIN_US, AUTH_DOMAIN_EU}
