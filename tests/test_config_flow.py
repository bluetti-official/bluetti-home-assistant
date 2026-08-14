"""Tests for config_flow.py."""

from homeassistant.helpers import config_entry_oauth2_flow

from custom_components.bluetti.config_flow import BluettiConfigFlow
from custom_components.bluetti.const import AUTH_DOMAIN_EU, AUTH_DOMAIN_US, DOMAIN


async def test_async_step_user_registers_three_distinct_implementations(hass, enable_custom_integrations):
    """Regression test: all three regions previously shared the same
    client_id, which made application_credentials' storage collapse them
    into a single stored credential (keyed by domain+client_id, not
    auth_domain) - only "Global" ever got registered, and Home Assistant
    silently skips the "Pick authentication method" screen when there is
    only one implementation, so users never saw a region choice at all.
    """
    flow = BluettiConfigFlow()
    flow.hass = hass
    flow.context = {}

    result = await flow.async_step_user(None)

    implementations = await config_entry_oauth2_flow.async_get_implementations(hass, DOMAIN)

    assert set(implementations.keys()) == {DOMAIN, AUTH_DOMAIN_US, AUTH_DOMAIN_EU}
    assert implementations[DOMAIN].name == "Global (default)"
    assert implementations[AUTH_DOMAIN_US].name == "US"
    assert implementations[AUTH_DOMAIN_EU].name == "EU"

    # The real (unmocked) "Pick authentication method" step must present
    # all three, not silently auto-pick one.
    assert result["type"] == "form"
    assert result["step_id"] == "pick_implementation"


async def test_global_is_registered_first_and_is_the_default_choice(hass, enable_custom_integrations):
    """Home Assistant shows regions in registration order and pre-selects
    the first one, so Global must be registered before US/EU to stay both
    the first entry shown and the recommended default."""
    flow = BluettiConfigFlow()
    flow.hass = hass
    flow.context = {}

    result = await flow.async_step_user(None)

    implementations = await config_entry_oauth2_flow.async_get_implementations(hass, DOMAIN)
    assert list(implementations.keys())[0] == DOMAIN

    schema = result["data_schema"].schema
    implementation_key = next(k for k in schema if k == "implementation")
    assert implementation_key.default() == DOMAIN
    choices = list(schema[implementation_key].container)
    assert choices[0] == DOMAIN


async def test_config_flow_no_longer_requires_application_credentials(hass, enable_custom_integrations):
    """The picker must work even without the application_credentials
    component set up, now that all regions register directly."""
    assert "application_credentials" not in hass.config.components

    flow = BluettiConfigFlow()
    flow.hass = hass
    flow.context = {}

    result = await flow.async_step_user(None)

    assert result["type"] == "form"
    assert result["step_id"] == "pick_implementation"
