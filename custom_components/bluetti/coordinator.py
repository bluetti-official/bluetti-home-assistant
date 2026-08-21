"""DataUpdateCoordinator for the BLUETTI integration."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .application_exception import ApplicationRuntimeException
from .models import BluettiDevice

_LOGGER = logging.getLogger(__name__)

UPDATE_INTERVAL = timedelta(seconds=30)

# msgCode values that mean the OAuth token is no longer valid.
AUTH_ERROR_CODES = {401, 805}


class BluettiDeviceCoordinator(DataUpdateCoordinator[BluettiDevice]):
    """Coordinate REST polling and websocket-triggered refreshes for one device."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, device: BluettiDevice) -> None:
        """Initialize the coordinator for a single BLUETTI device."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"bluetti-{device.device_id}",
            update_interval=UPDATE_INTERVAL,
        )
        self.device = device
        device.coordinator = self

    async def _async_update_data(self) -> BluettiDevice:
        """Fetch the latest state for the device from the BLUETTI cloud API."""
        try:
            await self.device.async_refresh_from_api()
        except ApplicationRuntimeException as err:
            if err.msgCode in AUTH_ERROR_CODES:
                raise ConfigEntryAuthFailed("BLUETTI authentication expired") from err
            raise UpdateFailed(f"Error communicating with BLUETTI API: {err}") from err
        except Exception as err:
            raise UpdateFailed(f"Error communicating with BLUETTI API: {err}") from err
        return self.device
