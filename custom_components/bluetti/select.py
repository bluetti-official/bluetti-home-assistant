from homeassistant.components.select import SelectEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import BluettiConfigEntry
from .const import DOMAIN
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


class BluettiSelect(SelectEntity):
    """Representation of a Bluetti select (mode choice)."""

    should_poll = False

    def __init__(self, device: BluettiDevice, state: BluettiState):
        self._device = device
        self._state_obj = state

        self._attr_unique_id = f"{device.device_id}_{state.fn_code}"
        self._attr_name = f"{device.name} {state.fn_name}"
        self._attr_icon = get_icon_for_fn_code(state.fn_code)
        self._attr_device_info = {
            "identifiers": {(DOMAIN, device.device_id)},  # 唯一ID
            "name": device.name,
            "manufacturer": device.manufacturer,
            "model": device.model,
        }

        # 可选项 = supportModeValues 的 name
        self._attr_options = [v["name"] for v in state.support_mode_values]

        # 检查是否为只读（根据fn_code判断）
        self._readonly = state.fn_code == "InvWorkState"

        # 如果只读，让 Home Assistant 前端显示为只读（灰掉）
        if self._readonly:
            self._attr_options = []  # 不显示可选项
            self._attr_entity_category = EntityCategory.DIAGNOSTIC  # 可选，标记为非操作类实体

        print(f"注册设备: {device.name}, identifiers= {(DOMAIN, device.device_id)}")

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
    def current_option(self) -> str:
        return self._state_obj.get_name_for_value()

    async def async_select_option(self, option: str) -> None:
        if self._readonly:
            # 只读的选项不允许修改
            raise ValueError(f"{self._state_obj.fn_code} is read-only and cannot be changed")

        # 找到对应的 code
        for v in self._state_obj.support_mode_values:
            if v["name"] == option:
                await self._device.set_state_value(self._state_obj.fn_code, v["code"])
                return
        raise ValueError(f"Invalid option {option} for {self._state_obj.fn_code}")

    async def async_added_to_hass(self):
        self._device.register_callback(self.async_write_ha_state)

    async def async_will_remove_from_hass(self):
        self._device.remove_callback(self.async_write_ha_state)