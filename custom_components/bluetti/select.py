from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import BluettiConfigEntry
from .const import DOMAIN
from .models import BluettiData, BluettiDevice, BluettiState

SELECT_CODES = {
    "SetCtrlWorkMode": {"name": "Working Mode", "icon": "mdi:cog"},
    "SetDCECO": {"name": "DC ECO Mode", "icon": "mdi:flash"},
    "SetACECO": {"name": "AC ECO Mode", "icon": "mdi:power-plug"},
    "InvWorkState": {"name": "Inverter Status", "icon": "mdi:solar-power", "readonly": True},  # 也可以只读
}

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
            if state.fn_code in SELECT_CODES and state.support_mode_values:
                entities.append(BluettiSelect(device, state, SELECT_CODES[state.fn_code]))

    if entities:
        async_add_entities(entities)

    return True


class BluettiSelect(SelectEntity):
    """Representation of a Bluetti select (mode choice)."""

    should_poll = False

    def __init__(self, device: BluettiDevice, state: BluettiState, meta: dict):
        self._device = device
        self._state_obj = state
        self._meta = meta

        self._attr_unique_id = f"{device.device_id}_{state.fn_code}"
        self._attr_name = f"{device.name} {meta['name']}"
        self._attr_icon = meta.get("icon")
        self._attr_device_info = {
            "identifiers": {(DOMAIN, device.device_id)},
            "name": device.name,
            "manufacturer": device.manufacturer,
        }

        # 可选项 = supportModeValues 的 name
        self._attr_options = [v["name"] for v in state.support_mode_values]

        # 是否只读
        self._readonly = meta.get("readonly", False)

        # 如果只读，让 Home Assistant 前端显示为只读（灰掉）
        if self._readonly:
            self._attr_options = []  # 不显示可选项
            self._attr_entity_category = "diagnostic"  # 可选，标记为非操作类实体

    @property
    def available(self) -> bool:
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