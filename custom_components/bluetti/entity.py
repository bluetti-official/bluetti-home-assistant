"""Base entity for the BLUETTI integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import BluettiDeviceCoordinator
from .icon_config import get_icon_for_fn_code
from .models import BluettiDevice, BluettiState


class BluettiEntity(CoordinatorEntity[BluettiDeviceCoordinator]):
    """Common behavior shared by all BLUETTI entities.

    Subclasses are expected to set self._attr_name after calling super().__init__(),
    since the name source (a device state's fn_name, or a static label) varies by
    platform.
    """

    _attr_has_entity_name = True

    def __init__(self, device: BluettiDevice, state: BluettiState) -> None:
        super().__init__(device.coordinator)
        self._device = device
        self._state_obj = state

        self._attr_unique_id = f"{device.device_id}_{state.fn_code}"
        self._attr_icon = get_icon_for_fn_code(state.fn_code)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device.device_id)},
            name=device.name,
            manufacturer=device.manufacturer,
            model=device.model,
        )

    @property
    def available(self) -> bool:
        if not super().available:
            return False
        # The power switch itself should stay controllable even if the
        # device otherwise reports as offline.
        if self._state_obj.fn_code == "SetCtrlPowerOn":
            return True
        return self._device.online
