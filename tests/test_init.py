"""Tests for config entry unload/removal behavior in __init__.py."""

from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.helpers import device_registry as dr, entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.bluetti import (
    BluettiRuntimeData,
    _async_update_listener,
    async_remove_entry,
    async_unload_entry,
)
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


async def test_remove_entry_survives_disconnect_error(hass):
    entry = MockConfigEntry(domain=DOMAIN)
    entry.add_to_hass(hass)

    stomp_client = MagicMock()
    stomp_client.disconnect.side_effect = RuntimeError("boom")
    entry.runtime_data = _runtime_data(stomp_client)

    # Must not raise even though disconnect() failed.
    await async_remove_entry(hass, entry)


async def test_remove_entry_cleans_up_device_and_entity_registries(hass):
    entry = MockConfigEntry(domain=DOMAIN)
    entry.add_to_hass(hass)
    entry.runtime_data = _runtime_data(MagicMock())

    device_registry = dr.async_get(hass)
    device_entry = device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, "SN1")},
        name="Test Device",
        manufacturer="Bluetti",
        model="AC200L",
    )
    entity_registry = er.async_get(hass)
    # Deliberately not linked to device_entry: device removal cascades to
    # its own entities, so this checks the explicit entity cleanup loop.
    entity_registry.async_get_or_create(
        "sensor", DOMAIN, "SN1_standalone", config_entry=entry,
    )

    await async_remove_entry(hass, entry)

    assert device_registry.async_get_device(identifiers={(DOMAIN, "SN1")}) is None
    assert entity_registry.async_get_entity_id("sensor", DOMAIN, "SN1_standalone") is None


async def test_update_listener_reloads_entry(hass):
    entry = MockConfigEntry(domain=DOMAIN)
    entry.add_to_hass(hass)

    with patch.object(hass.config_entries, "async_reload", AsyncMock()) as mock_reload:
        await _async_update_listener(hass, entry)

    mock_reload.assert_awaited_once_with(entry.entry_id)
