from homeassistant.const import PERCENTAGE
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorDeviceClass
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import BluettiConfigEntry
from .const import DOMAIN
from .models import BluettiData, BluettiDevice, BluettiState
from .icon_config import get_icon_for_fn_code

# 映射 sensor 类
SENSOR_MAP = {
    "SOC": {
        "device_class": SensorDeviceClass.BATTERY,
        "unit": PERCENTAGE,
        "name": "Battery Level",
    },
    "InvWorkState": {
        "device_class": SensorDeviceClass.ENUM,
        "unit": None,
        "name": "Inverter Status",
    },
}

# 映射 binary_sensor 类
BINARY_SENSOR_MAP = {
    "onLine": {
        "device_class": BinarySensorDeviceClass.CONNECTIVITY,
        "name": "Online",
    }
}

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: BluettiConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> bool:
    """Set up Bluetti sensors (including binary sensors) from config entry."""

    entry_data = hass.data[DOMAIN].get(config_entry.entry_id)
    if entry_data is None:
        return False

    bluetti_devices: BluettiData = entry_data["bluettiDevices"]
    entities = []

    for device in bluetti_devices.devices:
        for state in device.states:
            if state.fn_type == "SENSOR" and state.fn_code in SENSOR_MAP:
                entities.append(BluettiSensor(device, state, SENSOR_MAP[state.fn_code]))
            elif state.fn_type == "SENSOR" and state.fn_code in BINARY_SENSOR_MAP:
                entities.append(BluettiBinarySensor(device, state, BINARY_SENSOR_MAP[state.fn_code]))

    if entities:
        async_add_entities(entities)

    return True


class BluettiSensor(SensorEntity):
    """Bluetti sensor for numeric or enum states."""
    should_poll = False

    # should_poll = True

    def __init__(self, device: BluettiDevice, state: BluettiState, meta: dict):
        self._device = device
        self._state_obj = state
        self._meta = meta

        self._attr_unique_id = f"{device.device_id}_{state.fn_code}"
        self._attr_name = f"{device.name} {meta['name']}"
        self._attr_device_class = meta.get("device_class")
        self._attr_native_unit_of_measurement = meta.get("unit")
        self._attr_icon = get_icon_for_fn_code(state.fn_code)
        self._attr_device_info = {
            "identifiers": {(DOMAIN, device.device_id)},  # 唯一ID
            "name": device.name,
            "manufacturer": device.manufacturer,
            "model": device.model,
        }
        # print(f"注册设备: {device.name}, identifiers= {(DOMAIN, device.device_id)}")
        # self._attr_icon = "mdi:generator-portable"

    @property
    def native_value(self):
        if self._state_obj.support_mode_values:
            return self._state_obj.get_name_for_value()
        return self._state_obj.fn_value

    @property
    def available(self) -> bool:
    #    # 如果设备离线，直接不可用
    #     if not self._device.online:
    #         return False
    #     # 如果当前是电源开关自己，则不受限制
    #     if self._state_obj.fn_code == "SetCtrlPowerOn":
    #         return True
    #     # 其它开关要依赖 PowerOn 状态
    #     power_state = self._device.get_state("SetCtrlPowerOn")
    #     return power_state and power_state.fn_value == "1"

        # 如果当前是电源开关自己，则不受限制
        if self._state_obj.fn_code == "SetCtrlPowerOn":
            return True
        # 如果设备离线，直接不可用
        return self._device.online

    async def async_added_to_hass(self):
        self._device.register_callback(self.async_write_ha_state)

    async def async_will_remove_from_hass(self):
        self._device.remove_callback(self.async_write_ha_state)


class BluettiBinarySensor(BinarySensorEntity):
    """Bluetti binary sensor for online/offline state."""
    should_poll = False
    # should_poll = True

    def __init__(self, device: BluettiDevice, state: BluettiState, meta: dict):
        self._device = device
        self._state_obj = state
        self._meta = meta

        self._attr_unique_id = f"{device.device_id}_{state.fn_code}"
        self._attr_name = f"{device.name} {meta['name']}"
        self._attr_icon = get_icon_for_fn_code(state.fn_code)
        self._attr_device_class = meta.get("device_class")
        self._attr_device_info = {
            "identifiers": {(DOMAIN, device.device_id)},  # 唯一ID
            "name": device.name,
            "manufacturer": device.manufacturer,
            "model": device.model,
        }
        print(f"注册设备: {device.name}, identifiers= {(DOMAIN, device.device_id)}")

    @property
    def is_on(self) -> bool:
        return self._state_obj.fn_value == "1"

    @property
    def available(self) -> bool:
        """Return if the device is available"""
        return self._device.online

    # 同步 TODO
    # def update(self):

    # 异步 TODO
    # async def async_update(self):
        # print('异步方式: Home Assistant 定时调用')
        # await self._device.async_update()

    async def async_added_to_hass(self):
        self._device.register_callback(self.async_write_ha_state)

    async def async_will_remove_from_hass(self):
        self._device.remove_callback(self.async_write_ha_state)
