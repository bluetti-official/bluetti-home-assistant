import logging
from datetime import datetime
from typing import TypedDict

from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfEnergy
from homeassistant.components.sensor import (
    RestoreSensor,
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorDeviceClass
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from . import BluettiConfigEntry
from .entity import BluettiEntity
from .models import BluettiData, BluettiDevice, BluettiState

__LOGGER__ = logging.getLogger(__name__)

# Entities only read from the coordinator and never poll or call the API
# themselves, so there is no need to limit concurrent updates.
PARALLEL_UPDATES = 0


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
                if meta["device_class"] == SensorDeviceClass.POWER:
                    # Bluetti only ever reports power (W), never cumulated
                    # energy. Integrate it over time (trapezoidal method,
                    # kilo prefix, hours) the same way a manually added
                    # Home Assistant "Integral - Riemann sum" helper would,
                    # so this works out of the box for every power sensor.
                    entities.append(BluettiEnergySensor(device, state))
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


class BluettiEnergySensor(BluettiEntity, RestoreSensor):
    """Cumulated energy (kWh) integrated from a BLUETTI power (W) sensor.

    Mirrors what a manually added Home Assistant "Integral - Riemann sum"
    helper (trapezoidal method, kilo prefix, hours) would compute on top of
    the power sensor, but built in so it works without any manual setup.
    """

    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_suggested_display_precision = 2

    def __init__(self, device: BluettiDevice, power_state: BluettiState) -> None:
        super().__init__(device, power_state)
        self._power_state = power_state

        # power_state's fn_code is shared with the power sensor itself;
        # this companion entity needs its own identity.
        self._attr_unique_id = f"{device.device_id}_{power_state.fn_code}_energy"
        self._attr_translation_key = None
        self._attr_name = f"{power_state.fn_name} Energy"

        self._total_kwh: float = 0.0
        self._last_power_w: float | None = None
        self._last_updated: datetime | None = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last_data = await self.async_get_last_sensor_data()
        if last_data is not None and last_data.native_value is not None:
            self._total_kwh = float(last_data.native_value)

        self._last_power_w = self._current_power_w() if self.available else None
        self._last_updated = dt_util.utcnow()

    def _current_power_w(self) -> float | None:
        try:
            return float(self._power_state.fn_value)
        except (TypeError, ValueError):
            return None

    def _handle_coordinator_update(self) -> None:
        now = dt_util.utcnow()
        current_w = self._current_power_w() if self.available else None

        if (
            current_w is not None
            and self._last_power_w is not None
            and self._last_updated is not None
        ):
            elapsed_hours = (now - self._last_updated).total_seconds() / 3600
            average_w = (self._last_power_w + current_w) / 2
            self._total_kwh += (average_w * elapsed_hours) / 1000

        self._last_power_w = current_w
        self._last_updated = now

        super()._handle_coordinator_update()

    @property
    def native_value(self) -> float:
        return round(self._total_kwh, 4)


class BluettiBinarySensor(BluettiEntity, BinarySensorEntity):
    """Bluetti binary sensor for online/offline state."""

    def __init__(self, device: BluettiDevice, state: BluettiState, meta: dict):
        super().__init__(device, state)
        self._meta = meta

        self._attr_name = meta["name"]
        self._attr_device_class = meta.get("device_class")
        # Connectivity status is diagnostic information, not a primary
        # measurement.
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def is_on(self) -> bool:
        return self._state_obj.fn_value == "1"
