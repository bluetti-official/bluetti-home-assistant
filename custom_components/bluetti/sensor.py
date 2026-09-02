from typing import TypedDict

from homeassistant.const import PERCENTAGE
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorDeviceClass
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

import logging
from . import BluettiConfigEntry
from .const import DOMAIN,ControlMode
from .models import BluettiData, BluettiDevice, BluettiState
from .icon_config import get_icon_for_fn_code
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .api.bluetti import APPLICATION_PROFILE


class BaseSensorMetaInfo(TypedDict):
    device_class: SensorDeviceClass
    state_class: SensorStateClass | None
    unit: str | None

class NamedSensorMetaInfo(BaseSensorMetaInfo):
    name: str

SENSOR_MAP: dict[str, BaseSensorMetaInfo] = {
    "SensorDeviceClass.BATTERY":{
        "device_class":SensorDeviceClass.BATTERY,
        "state_class":SensorStateClass.MEASUREMENT,
        "unit": PERCENTAGE
    },
    "SensorDeviceClass.ENUM":{
        "device_class":SensorDeviceClass.ENUM,
        "state_class": None,
        "unit": None
    },
    "SensorDeviceClass.DURATION":{
        "device_class":SensorDeviceClass.DURATION,
        "state_class": None,
        "unit": "min"
    },
    "SensorDeviceClass.POWER":{
        "device_class":SensorDeviceClass.POWER,
        "state_class":SensorStateClass.MEASUREMENT,
        "unit": "W"
    }
}

# 映射 binary_sensor 类
BINARY_SENSOR_MAP = {
    "onLine": {
        "device_class": BinarySensorDeviceClass.CONNECTIVITY,
        "name": "Online",
    }
}

__LOGGER__ = logging.getLogger(__name__)

def unique_id_loggable(unique_id: str) -> str:
    """Remove parts of the unique id for logging."""
    splitted = unique_id.split("_", maxsplit=1)
    serial = splitted[0][:6]
    return serial + "XXXXXXXXXX" + splitted[1]


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: BluettiConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> bool:
    """Set up Bluetti sensors (including binary sensors) from config entry."""

    entry_data = hass.data[DOMAIN].get(config_entry.entry_id)
    if entry_data is None:
        return False

    device_mapping = config_entry.options.get("device_mapping", {})
    ble_setting = config_entry.options.get("ble_setting", {})
    # create reverse mapping: SN -> MAC address
    sn_to_mac = {sn: mac for mac, sn in device_mapping.items()}

    bluetti_devices: BluettiData = entry_data["bluettiDevices"]
    entities = []

    hasBleControl = any(device.control_mode == ControlMode.BLE for device in bluetti_devices.devices)
    if hasBleControl:
        from .ble.coordinator import PollingCoordinator

    for device in bluetti_devices.devices:
        # for state in device.states:
        #     if state.fn_type == "SENSOR" and state.fn_code in SENSOR_MAP:
        #         entities.append(BluettiSensor(device, state, SENSOR_MAP[state.fn_code]))
        #     elif state.fn_type == "SENSOR" and state.fn_code in BINARY_SENSOR_MAP:
        #         entities.append(BluettiBinarySensor(device, state, BINARY_SENSOR_MAP[state.fn_code]))

        for state in device.states:
            if state.fn_type == 'SENSOR' and state.sensor_info:
                sensorClass = SENSOR_MAP[state.sensor_info['sensorType']]
                meta: NamedSensorMetaInfo = {
                    "name": state.fn_name,
                    "unit": state.sensor_info["unit"] or sensorClass["unit"],
                    "device_class": sensorClass["device_class"],
                    "state_class": sensorClass["state_class"]
                }
                entities.append(BluettiSensor(device, state, meta))
            if state.fn_type == "SENSOR" and state.fn_code in BINARY_SENSOR_MAP:
                entities.append(BluettiBinarySensor(device, state, BINARY_SENSOR_MAP[state.fn_code]))

        if device.control_mode == ControlMode.BLE:
            mac_address = sn_to_mac.get(device.sn)
            polling_interval = ble_setting.get("ble_polling_interval",10)
            polling_timeout = ble_setting.get("ble_polling_timeout",120)
            max_retries = ble_setting.get("ble_max_retries",5)
            coordinator = PollingCoordinator(hass, mac_address, device, int(polling_interval), True, int(polling_timeout), int(max_retries))
            await coordinator.async_config_entry_first_refresh()
            if hasattr(coordinator, 'reader') and coordinator.reader is not None:
                device._bleClient = coordinator.reader.client
            entities.append(BluettiBluetoothBinarySensor(device, coordinator))

    if entities:
        async_add_entities(entities)

    return True


class BluettiSensor(SensorEntity):
    """Bluetti sensor for numeric or enum states."""
    should_poll = False

    # should_poll = True

    def __init__(self, device: BluettiDevice, state: BluettiState, meta: NamedSensorMetaInfo):
        self._device = device
        self._state_obj = state
        self._meta = meta

        self._attr_unique_id = f"{device.device_id}_{state.fn_code}"
        self._attr_name = f"{device.name} {meta['name']}"
        self._attr_device_class = meta["device_class"]
        self._attr_state_class = meta["state_class"]
        self._attr_native_unit_of_measurement = meta["unit"]
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
        __LOGGER__(f"register device: {device.name}, identifiers= {(DOMAIN, device.device_id)}")
        # print(f"注册设备: {device.name}, identifiers= {(DOMAIN, device.device_id)}")

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


class BluettiBluetoothBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Bluetti binary sensor for Bluetooth connection state."""

    should_poll = False

    def __init__(self, device: BluettiDevice, coordinator=None):
        super().__init__(coordinator)
        self.coordinator = coordinator

        self._device = device

        self._attr_unique_id = f"{device.device_id}_bluetooth_connected"
        self._attr_name = f"{device.name} Bluetooth Connected"
        self._attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
        self._attr_icon = "mdi:bluetooth"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, device.device_id)},
            "name": device.name,
            "manufacturer": device.manufacturer,
            "model": device.model,
        }

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        # 检查连接状态
        if self.coordinator and hasattr(self.coordinator, 'reader') and self.coordinator.reader:
            if not self.coordinator.reader.client.is_connected:
                __LOGGER__.debug("Bluetooth not connected, skipping update")
                return

        # 即使未读取到数据也更新状态，刷新连接状态
        if self.coordinator.data is None:
            __LOGGER__.debug("Data from coordinator is None")


        # 使用 asyncio.run_coroutine_threadsafe 在正确的线程中执行异步方法
        # 注意：_handle_coordinator_update 是同步回调，但 update_from_bluetooth 是异步方法
        # CoordinatorEntity 的回调是在 Home Assistant 的事件循环中执行的，所以可以直接创建任务
        import asyncio
        try:
            # 尝试获取当前事件循环
            loop = asyncio.get_running_loop()
            # 如果成功获取到运行中的循环，创建任务
            asyncio.create_task(self._device.update_from_bluetooth(self.coordinator.data))
        except RuntimeError:
            # 如果没有运行中的事件循环，使用设备的事件循环
            asyncio.run_coroutine_threadsafe(
                self._device.update_from_bluetooth(self.coordinator.data),
                self._device._loop
            )

        # 同时更新蓝牙连接状态传感器本身
        __LOGGER__.debug("Bluetooth connection state update triggered for %s", unique_id_loggable(self._attr_unique_id))
        self.async_write_ha_state()

    @property
    def is_on(self) -> bool:
        """Return if Bluetooth is connected."""
        return self._device.bluetooth_connected

    @property
    def available(self) -> bool:
        """Return if the device is available."""
        # 蓝牙连接状态传感器始终可用（即使未连接）
        return True

    @property
    def extra_state_attributes(self) -> dict:
        """Return extra state attributes."""
        attrs = {}

        if hasattr(self,'coordinator'):
            try:
                coordinator = self.coordinator
                if hasattr(coordinator, 'address'):
                    attrs["bluetooth_address"] = coordinator.address
                # if hasattr(coordinator, 'reader') and coordinator.reader:
                #     if hasattr(coordinator.reader, 'client'):
                #         attrs["bluetooth_connected"] = coordinator.reader.client.is_connected
                #     if hasattr(coordinator.reader, 'persistent_conn'):
                #         attrs["persistent_connection"] = coordinator.reader.persistent_conn
            except (AttributeError, Exception):
                pass

        return attrs

    async def async_added_to_hass(self):
        """Register callback when added to hass."""
        await super().async_added_to_hass()
        self._device.register_callback(self.async_write_ha_state)

    async def async_will_remove_from_hass(self):
        """Unregister callback when removed from hass."""
        await super().async_will_remove_from_hass()
        self._device.remove_callback(self.async_write_ha_state)
