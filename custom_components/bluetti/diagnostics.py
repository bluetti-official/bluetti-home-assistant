"""Diagnostics support for the BLUETTI integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from . import BluettiConfigEntry

TO_REDACT = {"token", "access_token", "refresh_token", "products"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: BluettiConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    runtime_data = entry.runtime_data

    devices = [
        {
            "device_id": device.device_id,
            "model": device.model,
            "online": device.online,
            "states": [
                {
                    "fn_code": state.fn_code,
                    "fn_type": state.fn_type,
                    "fn_value": state.fn_value,
                }
                for state in device.states
            ],
        }
        for device in runtime_data.bluetti_devices.devices
    ]

    coordinators = {
        device_id: {
            "last_update_success": coordinator.last_update_success,
            "update_interval": str(coordinator.update_interval),
        }
        for device_id, coordinator in runtime_data.coordinators.items()
    }

    return {
        "entry_data": async_redact_data(dict(entry.data), TO_REDACT),
        "entry_options": dict(entry.options),
        "devices": devices,
        "coordinators": coordinators,
    }
