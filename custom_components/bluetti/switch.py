from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
# from homeassistant.helpers.entity import EntityCategory

import logging

# from . import LOCALIZATION_MANAGER
from . import BluettiConfigEntry
from .const import DOMAIN
from .models import BluettiData, BluettiDevice, BluettiState
from .icon_config import get_icon_for_fn_code
from .entity_name import BluettiEntityNameMixin

__LOGGER__ = logging.getLogger(__name__)
BLUE_RES_PRE = "bluett.res."


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
        # add local ble fncode
        if (
            (device.control_mode == 'bluetooth' or device.control_mode == 'auto') 
            and hasattr(device,'device_reader') and device.device_reader != None
            ):
            oak_state_dict = {obj.fn_code: obj for obj in device.states}
            for command in device.device_reader.oak_device.polling_commands:
                if getattr(command,'fn_code','') and command.fn_code not in oak_state_dict and command.fn_type == 'SWITCH':
                    __LOGGER__.info(f'add local ble function:{command.fn_code}') 
                    device.states.append(BluettiState(
                        fn_code=command.fn_code,
                        fn_name=command.fn_name or "",
                        fn_value=command.fn_value,
                        fn_type=command.fn_type,
                    ))

        for state in device.states:
            # print(f'fn_type= {state.fn_type}, fn_name = {state.fn_name}, fn_code = {state.fn_code}')
            if state.fn_type == "SWITCH":
                entities.append(BluettiSwitch(hass,device, state)) 

    if entities:
        async_add_entities(entities)

    return True


class BluettiSwitch(BluettiEntityNameMixin, SwitchEntity):
    """Representation of a Bluetti switch."""

    should_poll = False

    def __init__(self,hass: HomeAssistant, device: BluettiDevice, state: BluettiState):
        self._hass = hass
        self._device = device
        self._state_obj = state
        # print(f'device.device_id= {device.device_id}')

        self._attr_unique_id = f"{device.device_id}_{state.fn_code}"
        self._set_entity_name("switch", device, state)
        self._attr_icon = get_icon_for_fn_code(state.fn_code)
        self._attr_device_info = {
            "identifiers": {(DOMAIN, device.device_id)},  # 唯一ID
            "name": device.name,
            "manufacturer": device.manufacturer,
            "model": device.model,
        }
        self._meta = {"name": state.fn_name, "icon": self._attr_icon}
        # self._attr_icon = "mdi:generator-portable"
        # self._attr_entity_category = EntityCategory.CONFIG

        # print(f"注册设备: {device.name}, identifiers= {(DOMAIN, device.device_id)}")
    
    # @property
    # def name(self) -> str:
    #     """Entity Name """
    #     a = LOCALIZATION_MANAGER.get_text(self._state_obj.fn_code)
    #     print(f'aaa:{a}')
    #     return f"{self._state_obj.fn_name}"
    
    @property
    def extra_state_attributes(self) -> dict:
        """extern attr"""
        return {
            "description": 'desc',
            "current_language": 'cur'
        }
    @property
    def available(self) -> bool:
        # # 如果设备离线，直接不可用
        # if not self._device.online:
        #     return False
        # # 如果当前是电源开关自己，则不受限制
        # if self._state_obj.fn_code == "SetCtrlPowerOn":
        #     return True
        # # 其它开关要依赖 PowerOn 状态
        # power_state = self._device.get_state("SetCtrlPowerOn")
        # return power_state and power_state.fn_value == "1"
        # 如果当前是电源开关自己，则不受限制
        if self._state_obj.fn_code == "SetCtrlPowerOn":
            return True
        # 如果设备离线，直接不可用
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
