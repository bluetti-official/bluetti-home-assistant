import logging
from typing import TypedDict

from homeassistant.const import PERCENTAGE
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorDeviceClass
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import BluettiConfigEntry
from .const import DOMAIN
from .coordinator import BluettiDeviceCoordinator
from .models import BluettiData, BluettiDevice, BluettiState
from .icon_config import get_icon_for_fn_code

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

    entry_data = hass.data[DOMAIN].get(config_entry.entry_id)
    if entry_data is None:
        return False

    bluetti_devices: BluettiData = entry_data["bluettiDevices"]
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


class BluettiSensor(CoordinatorEntity[BluettiDeviceCoordinator], SensorEntity):
    """Bluetti sensor for numeric or enum states."""

    _attr_has_entity_name = True

    def __init__(self, device: BluettiDevice, state: BluettiState, meta: NamedSensorMetaInfo):
        super().__init__(device.coordinator)
        self._device = device
        self._state_obj = state
        self._meta = meta

        self._attr_unique_id = f"{device.device_id}_{state.fn_code}"
        self._attr_name = meta["name"]
        self._attr_device_class = meta["device_class"]
        self._attr_state_class = meta["state_class"]
        self._attr_native_unit_of_measurement = meta["unit"]
        self._attr_icon = get_icon_for_fn_code(state.fn_code)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device.device_id)},
            name=device.name,
            manufacturer=device.manufacturer,
            model=device.model,
        )

    @property
    def native_value(self):
        if self._state_obj.support_mode_values:
            return self._state_obj.get_name_for_value()
        return self._state_obj.fn_value

    @property
    def available(self) -> bool:
        if not super().available:
            return False
        # The power switch itself should stay controllable even if the
        # device otherwise reports as offline.
        if self._state_obj.fn_code == "SetCtrlPowerOn":
            return True
        return self._device.online


class BluettiBinarySensor(CoordinatorEntity[BluettiDeviceCoordinator], BinarySensorEntity):
    """Bluetti binary sensor for online/offline state."""

    _attr_has_entity_name = True

    def __init__(self, device: BluettiDevice, state: BluettiState, meta: dict):
        super().__init__(device.coordinator)
        self._device = device
        self._state_obj = state
        self._meta = meta

        self._attr_unique_id = f"{device.device_id}_{state.fn_code}"
        self._attr_name = meta["name"]
        self._attr_icon = get_icon_for_fn_code(state.fn_code)
        self._attr_device_class = meta.get("device_class")
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device.device_id)},
            name=device.name,
            manufacturer=device.manufacturer,
            model=device.model,
        )

    @property
    def is_on(self) -> bool:
        return self._state_obj.fn_value == "1"

    @property
    def available(self) -> bool:
        """Return if the device is available."""
        return super().available and self._device.online
