"""Tests for config entry unload/removal behavior in __init__.py."""

from unittest.mock import MagicMock

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.bluetti import async_remove_entry, async_unload_entry
from custom_components.bluetti.const import DOMAIN


async def test_unload_entry_disconnects_websocket(hass):
    entry = MockConfigEntry(domain=DOMAIN)
    entry.add_to_hass(hass)

    stomp_client = MagicMock()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "bluettiDevices": MagicMock(devices=[]),
        "stompClient": stomp_client,
        "coordinators": {},
    }

    result = await async_unload_entry(hass, entry)

    assert result is True
    stomp_client.disconnect.assert_called_once()


async def test_unload_entry_survives_disconnect_error(hass):
    entry = MockConfigEntry(domain=DOMAIN)
    entry.add_to_hass(hass)

    stomp_client = MagicMock()
    stomp_client.disconnect.side_effect = RuntimeError("socket already closed")
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "bluettiDevices": MagicMock(devices=[]),
        "stompClient": stomp_client,
        "coordinators": {},
    }

    # Must not raise even though disconnect() failed.
    result = await async_unload_entry(hass, entry)
    assert result is True


async def test_remove_entry_cleans_up_domain_data(hass):
    entry = MockConfigEntry(domain=DOMAIN)
    entry.add_to_hass(hass)

    stomp_client = MagicMock()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "bluettiDevices": MagicMock(devices=[]),
        "stompClient": stomp_client,
        "coordinators": {},
    }

    await async_remove_entry(hass, entry)

    stomp_client.disconnect.assert_called_once()
    assert DOMAIN not in hass.data
