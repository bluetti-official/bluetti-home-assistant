from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import BluettiConfigEntry
from .entity import BluettiEntity
from .models import BluettiData, BluettiDevice, BluettiState

# Switch actions call the BLUETTI cloud API; serialize them to avoid
# hammering it with concurrent control requests.
PARALLEL_UPDATES = 1

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: BluettiConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> bool:
    """Set up Bluetti switches from config entry."""

    bluetti_devices: BluettiData = config_entry.runtime_data.bluetti_devices

    entities = []
    for device in bluetti_devices.devices:
        for state in device.states:
            if state.fn_type == "SWITCH":
                entities.append(BluettiSwitch(device, state))

    if entities:
        async_add_entities(entities)

    return True


class BluettiSwitch(BluettiEntity, SwitchEntity):
    """Representation of a Bluetti switch."""

    def __init__(self, device: BluettiDevice, state: BluettiState):
        super().__init__(device, state)
        self._attr_name = state.fn_name

    @property
    def is_on(self) -> bool:
        return self._state_obj.fn_value == "1"

    async def async_turn_on(self, **kwargs):
        await self._device.set_state_value(self._state_obj.fn_code, "1")

    async def async_turn_off(self, **kwargs):
        await self._device.set_state_value(self._state_obj.fn_code, "0")
