"""Tests for config entry unload/removal behavior in __init__.py."""

from unittest.mock import MagicMock

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.bluetti import BluettiRuntimeData, async_remove_entry, async_unload_entry
from custom_components.bluetti.const import DOMAIN


def _runtime_data(stomp_client) -> BluettiRuntimeData:
    return BluettiRuntimeData(
        auth=MagicMock(),
        bluetti_devices=MagicMock(devices=[]),
        stomp_client=stomp_client,
        coordinators={},
    )


async def test_unload_entry_disconnects_websocket(hass):
    entry = MockConfigEntry(domain=DOMAIN)
    entry.add_to_hass(hass)

    stomp_client = MagicMock()
    entry.runtime_data = _runtime_data(stomp_client)

    result = await async_unload_entry(hass, entry)

    assert result is True
    stomp_client.disconnect.assert_called_once()


async def test_unload_entry_survives_disconnect_error(hass):
    entry = MockConfigEntry(domain=DOMAIN)
    entry.add_to_hass(hass)

    stomp_client = MagicMock()
    stomp_client.disconnect.side_effect = RuntimeError("socket already closed")
    entry.runtime_data = _runtime_data(stomp_client)

    # Must not raise even though disconnect() failed.
    result = await async_unload_entry(hass, entry)
    assert result is True


async def test_unload_entry_without_runtime_data_does_not_raise(hass):
    """A config entry that never finished setup has no runtime_data yet."""
    entry = MockConfigEntry(domain=DOMAIN)
    entry.add_to_hass(hass)

    result = await async_unload_entry(hass, entry)
    assert result is True


async def test_remove_entry_disconnects_websocket(hass):
    entry = MockConfigEntry(domain=DOMAIN)
    entry.add_to_hass(hass)

    stomp_client = MagicMock()
    entry.runtime_data = _runtime_data(stomp_client)

    await async_remove_entry(hass, entry)

    stomp_client.disconnect.assert_called_once()


async def test_remove_entry_without_runtime_data_does_not_raise(hass):
    """Removing a config entry that never finished setup must not crash."""
    entry = MockConfigEntry(domain=DOMAIN)
    entry.add_to_hass(hass)

    await async_remove_entry(hass, entry)
