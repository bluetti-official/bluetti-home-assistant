"""Tests for the async_setup_entry() function of each entity platform."""

from unittest.mock import MagicMock

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.bluetti import BluettiRuntimeData
from custom_components.bluetti.const import DOMAIN
from custom_components.bluetti.models import BluettiData, BluettiDevice
from custom_components.bluetti.select import BluettiSelect, async_setup_entry as select_setup_entry
from custom_components.bluetti.sensor import BluettiBinarySensor, BluettiSensor, async_setup_entry as sensor_setup_entry
from custom_components.bluetti.switch import BluettiSwitch, async_setup_entry as switch_setup_entry


def _entry_with_devices(hass, devices: list[BluettiDevice]) -> MockConfigEntry:
    for device in devices:
        device.coordinator = MagicMock()
    entry = MockConfigEntry(domain=DOMAIN)
    entry.add_to_hass(hass)
    bluetti_data = BluettiData.__new__(BluettiData)
    bluetti_data.devices = devices
    entry.runtime_data = BluettiRuntimeData(
        auth=MagicMock(), bluetti_devices=bluetti_data, stomp_client=MagicMock(), coordinators={},
    )
    return entry


async def test_sensor_setup_entry_creates_expected_entities(hass):
    device = BluettiDevice(
        device_id="SN1", on_line="1", name="Test", sn="SN1", model="AC200L",
        state_list=[
            {
                "fnCode": "SOC", "fnName": "Battery", "fnValue": "50", "fnType": "SENSOR",
                "sensorInfo": {"sensorType": "SensorDeviceClass.BATTERY", "unit": None},
            },
            {
                "fnCode": "InvWorkState", "fnName": "Inverter", "fnValue": "1", "fnType": "SENSOR",
                "sensorInfo": {"sensorType": "SensorDeviceClass.ENUM", "unit": None},
                "supportModeValues": [{"code": "1", "name": "Grid"}],
            },
            {
                "fnCode": "Weird", "fnName": "Weird sensor", "fnValue": "1", "fnType": "SENSOR",
                "sensorInfo": {"sensorType": "SensorDeviceClass.UNKNOWN", "unit": None},
            },
            {"fnCode": "onLine", "fnName": "Online", "fnValue": "1", "fnType": "SENSOR"},
        ],
    )
    entry = _entry_with_devices(hass, [device])
    added = []

    await sensor_setup_entry(hass, entry, added.extend)

    assert len(added) == 3  # SOC + InvWorkState sensors, plus the onLine binary sensor
    sensors = [e for e in added if isinstance(e, BluettiSensor)]
    binary_sensors = [e for e in added if isinstance(e, BluettiBinarySensor)]
    assert len(sensors) == 2
    assert len(binary_sensors) == 1

    enum_sensor = next(s for s in sensors if s._state_obj.fn_code == "InvWorkState")
    assert enum_sensor.native_value == "Grid"  # exercises the support_mode_values branch

    assert binary_sensors[0].is_on is True


async def test_sensor_setup_entry_with_no_matching_states_adds_nothing(hass):
    device = BluettiDevice(
        device_id="SN1", on_line="1", name="Test", sn="SN1", model="AC200L",
        state_list=[{"fnCode": "SetCtrlAc", "fnName": "AC", "fnValue": "0", "fnType": "SWITCH"}],
    )
    entry = _entry_with_devices(hass, [device])
    async_add_entities = MagicMock()

    result = await sensor_setup_entry(hass, entry, async_add_entities)

    assert result is True
    async_add_entities.assert_not_called()


async def test_switch_setup_entry_creates_switch_and_controls_it(hass):
    device = BluettiDevice(
        device_id="SN1", on_line="1", name="Test", sn="SN1", model="AC200L",
        state_list=[{"fnCode": "SetCtrlAc", "fnName": "AC", "fnValue": "0", "fnType": "SWITCH"}],
    )
    device._api_client = MagicMock()
    entry = _entry_with_devices(hass, [device])
    added = []

    await switch_setup_entry(hass, entry, added.extend)

    assert len(added) == 1
    switch = added[0]
    assert isinstance(switch, BluettiSwitch)
    assert switch.is_on is False

    async def fake_control_device(payload):
        return MagicMock(msgCode=0)

    device._api_client.control_device = fake_control_device
    await switch.async_turn_on()
    assert switch.is_on is True

    await switch.async_turn_off()
    assert switch.is_on is False


async def test_select_setup_entry_creates_select_and_controls_it(hass):
    device = BluettiDevice(
        device_id="SN1", on_line="1", name="Test", sn="SN1", model="AC200L",
        state_list=[{
            "fnCode": "SetCtrlWorkMode", "fnName": "Mode", "fnValue": "0", "fnType": "SELECT",
            "supportModeValues": [{"code": "0", "name": "Standard"}, {"code": "1", "name": "Silent"}],
        }],
    )
    device._api_client = MagicMock()
    entry = _entry_with_devices(hass, [device])
    added = []

    await select_setup_entry(hass, entry, added.extend)

    assert len(added) == 1
    select = added[0]
    assert isinstance(select, BluettiSelect)

    async def fake_control_device(payload):
        return MagicMock(msgCode=0)

    device._api_client.control_device = fake_control_device
    await select.async_select_option("Silent")
    assert select.current_option == "Silent"


async def test_select_setup_entry_ignores_states_without_modes(hass):
    device = BluettiDevice(
        device_id="SN1", on_line="1", name="Test", sn="SN1", model="AC200L",
        state_list=[{"fnCode": "SetCtrlAc", "fnName": "AC", "fnValue": "0", "fnType": "SWITCH"}],
    )
    entry = _entry_with_devices(hass, [device])
    async_add_entities = MagicMock()

    await select_setup_entry(hass, entry, async_add_entities)

    async_add_entities.assert_not_called()
