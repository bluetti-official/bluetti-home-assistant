"""Tests for async_setup_entry() in __init__.py."""

import time
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.config_entries import ConfigEntryState
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.bluetti.api.bluetti import APPLICATION_PROFILE, EU_APPLICATION_PROFILE, US_APPLICATION_PROFILE
from custom_components.bluetti.const import AUTH_DOMAIN_EU, AUTH_DOMAIN_US, DOMAIN


def _entry(hass, *, products=None, devices=None, auth_implementation=DOMAIN) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "auth_implementation": auth_implementation,
            "token": {"access_token": "tok", "expires_at": time.time() + 10000},
            "products": products or [],
        },
        options={"devices": devices or []},
    )
    entry.add_to_hass(hass)
    return entry


async def test_async_setup_entry_with_no_devices(hass, enable_custom_integrations):
    entry = _entry(hass)

    with patch("custom_components.bluetti.async_get_clientsession", MagicMock()), \
         patch(
             "custom_components.bluetti.config_entry_oauth2_flow.async_get_config_entry_implementation",
             AsyncMock(return_value=MagicMock()),
         ), \
         patch("custom_components.bluetti.config_entry_oauth2_flow.OAuth2Session") as mock_session_cls, \
         patch("custom_components.bluetti.StompClient") as mock_stomp_cls:
        mock_session_cls.return_value.token = {"access_token": "tok", "expires_at": time.time() + 10000}

        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    assert entry.runtime_data.bluetti_devices.devices == []
    assert entry.runtime_data.coordinators == {}
    mock_stomp_cls.return_value.connect.assert_called_once()


async def test_async_setup_entry_with_a_device(hass, enable_custom_integrations):
    entry = _entry(
        hass,
        products=[{"sn": "SN1", "name": "Device", "stateList": [], "online": "1"}],
        devices=["SN1"],
    )
    status_data = MagicMock(sn="SN1", isBindByCurUser="1", online="1", stateList=[])

    with patch("custom_components.bluetti.async_get_clientsession", MagicMock()), \
         patch(
             "custom_components.bluetti.config_entry_oauth2_flow.async_get_config_entry_implementation",
             AsyncMock(return_value=MagicMock()),
         ), \
         patch("custom_components.bluetti.config_entry_oauth2_flow.OAuth2Session") as mock_session_cls, \
         patch("custom_components.bluetti.StompClient") as mock_stomp_cls, \
         patch("custom_components.bluetti.ProductClient") as mock_product_cls:
        mock_session_cls.return_value.token = {"access_token": "tok", "expires_at": time.time() + 10000}
        mock_product_cls.return_value.get_device_status = AsyncMock(
            return_value=MagicMock(data=[status_data])
        )

        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    devices = entry.runtime_data.bluetti_devices.devices
    assert len(devices) == 1
    assert devices[0].device_id == "SN1"
    assert "SN1" in entry.runtime_data.coordinators
    mock_stomp_cls.return_value.connect.assert_called_once()


async def test_async_setup_entry_uses_us_region_profile(hass, enable_custom_integrations):
    """An entry authenticated against the US implementation must use the
    US gateway/websocket URLs, not the global ones (see issue #121)."""
    entry = _entry(hass, auth_implementation=AUTH_DOMAIN_US)

    with patch("custom_components.bluetti.async_get_clientsession", MagicMock()), \
         patch(
             "custom_components.bluetti.config_entry_oauth2_flow.async_get_config_entry_implementation",
             AsyncMock(return_value=MagicMock()),
         ), \
         patch("custom_components.bluetti.config_entry_oauth2_flow.OAuth2Session") as mock_session_cls, \
         patch("custom_components.bluetti.StompClient") as mock_stomp_cls, \
         patch("custom_components.bluetti.ProductClient") as mock_product_cls:
        mock_session_cls.return_value.token = {"access_token": "tok", "expires_at": time.time() + 10000}

        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED

    us_wss = US_APPLICATION_PROFILE.config["server"]["wss"]
    us_gateway = US_APPLICATION_PROFILE.config["server"]["gateway"]
    assert us_gateway != APPLICATION_PROFILE.config["server"]["gateway"]

    stomp_url = mock_stomp_cls.call_args[0][0]
    assert stomp_url == us_wss

    product_kwargs = mock_product_cls.call_args.kwargs
    assert product_kwargs["gateway_url"] == us_gateway


async def test_async_setup_entry_uses_eu_region_profile(hass, enable_custom_integrations):
    """An entry authenticated against the EU implementation must use the
    EU gateway (see issue #72); the EU profile shares the global wss."""
    entry = _entry(hass, auth_implementation=AUTH_DOMAIN_EU)

    with patch("custom_components.bluetti.async_get_clientsession", MagicMock()), \
         patch(
             "custom_components.bluetti.config_entry_oauth2_flow.async_get_config_entry_implementation",
             AsyncMock(return_value=MagicMock()),
         ), \
         patch("custom_components.bluetti.config_entry_oauth2_flow.OAuth2Session") as mock_session_cls, \
         patch("custom_components.bluetti.StompClient") as mock_stomp_cls, \
         patch("custom_components.bluetti.ProductClient") as mock_product_cls:
        mock_session_cls.return_value.token = {"access_token": "tok", "expires_at": time.time() + 10000}

        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED

    eu_gateway = EU_APPLICATION_PROFILE.config["server"]["gateway"]
    assert eu_gateway != APPLICATION_PROFILE.config["server"]["gateway"]
    assert eu_gateway == "https://gwde.bluettipower.com"

    product_kwargs = mock_product_cls.call_args.kwargs
    assert product_kwargs["gateway_url"] == eu_gateway


async def test_async_setup_entry_retries_on_failure(hass, enable_custom_integrations):
    entry = _entry(hass)

    with patch("custom_components.bluetti.async_get_clientsession", MagicMock()), \
         patch(
             "custom_components.bluetti.config_entry_oauth2_flow.async_get_config_entry_implementation",
             AsyncMock(side_effect=RuntimeError("boom")),
         ):
        assert not await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.SETUP_RETRY
