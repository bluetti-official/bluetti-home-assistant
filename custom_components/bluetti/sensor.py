import logging
from typing import TypedDict

from homeassistant.const import PERCENTAGE
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorDeviceClass
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import BluettiConfigEntry
from .entity import BluettiEntity
from .models import BluettiData, BluettiDevice, BluettiState

__LOGGER__ = logging.getLogger(__name__)


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

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: BluettiConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> bool:
    """Set up Bluetti sensors (including binary sensors) from config entry."""

    bluetti_devices: BluettiData = config_entry.runtime_data.bluetti_devices
    entities = []

    for device in bluetti_devices.devices:
        for state in device.states:
            if state.fn_type == 'SENSOR' and state.sensor_info:
                sensorClass = SENSOR_MAP.get(state.sensor_info.get('sensorType'))
                if sensorClass is None:
                    __LOGGER__.warning(
                        "Unknown sensor type '%s' for fn_code=%s, skipping",
                        state.sensor_info.get('sensorType'), state.fn_code,
                    )
                    continue
                meta: NamedSensorMetaInfo = {
                    "name": state.fn_name,
                    "unit": state.sensor_info["unit"] or sensorClass["unit"],
                    "device_class": sensorClass["device_class"],
                    "state_class": sensorClass["state_class"]
                }
                entities.append(BluettiSensor(device, state, meta))
            if state.fn_type == "SENSOR" and state.fn_code in BINARY_SENSOR_MAP:
                entities.append(BluettiBinarySensor(device, state, BINARY_SENSOR_MAP[state.fn_code]))

    if entities:
        async_add_entities(entities)

    return True


class BluettiSensor(BluettiEntity, SensorEntity):
    """Bluetti sensor for numeric or enum states."""

    def __init__(self, device: BluettiDevice, state: BluettiState, meta: NamedSensorMetaInfo):
        super().__init__(device, state)
        self._meta = meta

        self._attr_name = meta["name"]
        self._attr_device_class = meta["device_class"]
        self._attr_state_class = meta["state_class"]
        self._attr_native_unit_of_measurement = meta["unit"]

    @property
    def native_value(self):
        if self._state_obj.support_mode_values:
            return self._state_obj.get_name_for_value()
        return self._state_obj.fn_value


class BluettiBinarySensor(BluettiEntity, BinarySensorEntity):
    """Bluetti binary sensor for online/offline state."""

    def __init__(self, device: BluettiDevice, state: BluettiState, meta: dict):
        super().__init__(device, state)
        self._meta = meta

        self._attr_name = meta["name"]
        self._attr_device_class = meta.get("device_class")

    @property
    def is_on(self) -> bool:
        return self._state_obj.fn_value == "1"
