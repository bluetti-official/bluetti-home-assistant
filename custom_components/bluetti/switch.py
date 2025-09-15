from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
# from homeassistant.helpers.entity import EntityCategory

from . import BluettiConfigEntry
from .const import DOMAIN
from .models import BluettiData, BluettiDevice, BluettiState


SWITCH_CODES = {
    "SetCtrlAc": {"name": "AC Switch", "icon": "mdi:power-socket-us"},
    "SetCtrlDc": {"name": "DC Switch", "icon": "mdi:car-battery"},
    "SetCtrlPowerOn": {"name": "Power", "icon": "mdi:power"},
    "Storm_Mode_Cloud_Ctrl": {"name": "Disaster Warning", "icon": "mdi:weather-lightning"},
}

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
            if state.fn_code in SWITCH_CODES:
                entities.append(BluettiSwitch(device, state, SWITCH_CODES[state.fn_code]))

    if entities:
        async_add_entities(entities)

    return True


class BluettiSwitch(SwitchEntity):
    """Representation of a Bluetti switch."""

    should_poll = False

    def __init__(self, device: BluettiDevice, state: BluettiState, meta: dict):
        self._device = device
        self._state_obj = state
        self._meta = meta

        # print(f'device.device_id= {device.device_id}')

        self._attr_unique_id = f"{device.device_id}_{state.fn_code}"
        self._attr_name = f"{device.name} {meta['name']}"
        self._attr_icon = meta.get("icon")
        self._attr_device_info = {
            "identifiers": {(DOMAIN, device.device_id)},  # 唯一ID
            "name": device.name,
            "manufacturer": device.manufacturer,
            "model": "Bluetti",
        }
        # self._attr_icon = "mdi:generator-portable"
        # self._attr_entity_category = EntityCategory.CONFIG

    @property
    def available(self) -> bool:
        return self._device.online

    @property
    def is_on(self) -> bool:
        return self._state_obj.fn_value == "1"

    async def async_turn_on(self, **kwargs):
        await self._device.set_state_value(self._state_obj.fn_code, "1")

    async def async_turn_off(self, **kwargs):
        await self._device.set_state_value(self._state_obj.fn_code, "0")

    async def async_added_to_hass(self):
        self._device.register_callback(self.async_write_ha_state)

    async def async_will_remove_from_hass(self):
        self._device.remove_callback(self.async_write_ha_state)
