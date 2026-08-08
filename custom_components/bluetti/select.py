from homeassistant.components.select import SelectEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
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
    """Set up Bluetti selects from config entry."""

    entry_data = hass.data[DOMAIN].get(config_entry.entry_id)
    if entry_data is None:
        return False

    bluetti_devices: BluettiData = entry_data["bluettiDevices"]

    entities = []
    for device in bluetti_devices.devices:
        for state in device.states:
            if state.fn_type == 'SELECT' and state.support_mode_values:
                entities.append(BluettiSelect(device, state))

    if entities:
        async_add_entities(entities)

    return True


class BluettiSelect(CoordinatorEntity[BluettiDeviceCoordinator], SelectEntity):
    """Representation of a Bluetti select (mode choice)."""

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

        self._attr_options = [v["name"] for v in state.support_mode_values]

        # Some fn_codes (e.g. InvWorkState) only report a mode, they cannot
        # be changed by the user.
        self._readonly = state.fn_code == "InvWorkState"

        # Keep _attr_options populated even when read-only, so current_option
        # (sourced from the device's reported value) is never outside of the
        # advertised options list - Home Assistant would otherwise log a
        # "not in the list of available options" warning on every update.
        if self._readonly:
            self._attr_entity_category = EntityCategory.DIAGNOSTIC

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
    def current_option(self) -> str:
        return self._state_obj.get_name_for_value()

    async def async_select_option(self, option: str) -> None:
        if self._readonly:
            raise ServiceValidationError(
                f"{self._state_obj.fn_code} is read-only and cannot be changed"
            )

        for v in self._state_obj.support_mode_values:
            if v["name"] == option:
                await self._device.set_state_value(self._state_obj.fn_code, v["code"])
                return
        raise ServiceValidationError(
            f"Invalid option {option} for {self._state_obj.fn_code}"
        )
