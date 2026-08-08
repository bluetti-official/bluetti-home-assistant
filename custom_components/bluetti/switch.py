from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import BluettiConfigEntry
from .const import DOMAIN
from .coordinator import BluettiDeviceCoordinator
from .models import BluettiData, BluettiDevice, BluettiState
from .icon_config import get_icon_for_fn_code

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: BluettiConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> bool:
    """Set up Bluetti switches from config entry."""

    entry_data = hass.data[DOMAIN].get(config_entry.entry_id)
    if entry_data is None:
        return False

    bluetti_devices: BluettiData = entry_data["bluettiDevices"]

    entities = []
    for device in bluetti_devices.devices:
        for state in device.states:
            if state.fn_type == "SWITCH":
                entities.append(BluettiSwitch(device, state))

    if entities:
        async_add_entities(entities)

    return True


class BluettiSwitch(CoordinatorEntity[BluettiDeviceCoordinator], SwitchEntity):
    """Representation of a Bluetti switch."""

    _attr_has_entity_name = True

    def __init__(self, device: BluettiDevice, state: BluettiState):
        super().__init__(device.coordinator)
        self._device = device
        self._state_obj = state

        self._attr_unique_id = f"{device.device_id}_{state.fn_code}"
        self._attr_name = state.fn_name
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

    @property
    def is_on(self) -> bool:
        return self._state_obj.fn_value == "1"

    async def async_turn_on(self, **kwargs):
        await self._device.set_state_value(self._state_obj.fn_code, "1")

    async def async_turn_off(self, **kwargs):
        await self._device.set_state_value(self._state_obj.fn_code, "0")
