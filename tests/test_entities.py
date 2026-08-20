"""Tests for the BLUETTI entity platforms (sensor/binary_sensor, switch, select)."""

import pytest
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.exceptions import ServiceValidationError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.bluetti.const import DOMAIN
from custom_components.bluetti.coordinator import BluettiDeviceCoordinator
from custom_components.bluetti.models import BluettiDevice
from custom_components.bluetti.select import BluettiSelect
from custom_components.bluetti.sensor import BluettiBinarySensor, BluettiSensor
from custom_components.bluetti.switch import BluettiSwitch


def _make_coordinator(hass) -> BluettiDeviceCoordinator:
    device = BluettiDevice(
        device_id="SN1",
        on_line="1",
        name="Test Device",
        sn="SN1",
        model="AC200L",
        state_list=[
            {"fnCode": "SOC", "fnName": "Battery Level", "fnValue": "80", "fnType": "SENSOR"},
            {"fnCode": "SetCtrlAc", "fnName": "AC Output", "fnValue": "0", "fnType": "SWITCH"},
            {
                "fnCode": "SetCtrlWorkMode", "fnName": "Work Mode", "fnValue": "0",
                "fnType": "SELECT",
                "supportModeValues": [
                    {"code": "0", "name": "Standard"},
                    {"code": "1", "name": "Silent"},
                ],
            },
            {
                "fnCode": "InvWorkState", "fnName": "Inverter Status", "fnValue": "0",
                "fnType": "SELECT",
                "supportModeValues": [{"code": "0", "name": "Idle"}],
            },
        ],
    )
    entry = MockConfigEntry(domain=DOMAIN)
    entry.add_to_hass(hass)
    return BluettiDeviceCoordinator(hass, entry, device)


async def test_sensor_uses_has_entity_name_and_device_info(hass):
    coordinator = _make_coordinator(hass)
    state = coordinator.device.get_state("SOC")
    meta = {
        "name": state.fn_name,
        "unit": "%",
        "device_class": SensorDeviceClass.BATTERY,
        "state_class": None,
    }

    entity = BluettiSensor(coordinator.device, state, meta)

    assert entity.has_entity_name is True
    assert entity.name == "Battery Level"
    assert entity.unique_id == "SN1_SOC"
    assert entity.device_info["identifiers"] == {(DOMAIN, "SN1")}
    assert entity.native_value == "80"
    assert entity.available is True


async def test_sensor_unavailable_when_device_offline(hass):
    coordinator = _make_coordinator(hass)
    coordinator.device.on_line = "0"
    state = coordinator.device.get_state("SOC")
    meta = {"name": state.fn_name, "unit": "%", "device_class": None, "state_class": None}

    entity = BluettiSensor(coordinator.device, state, meta)

    assert entity.available is False


async def test_sensor_unavailable_when_coordinator_update_failed(hass):
    coordinator = _make_coordinator(hass)
    coordinator.last_update_success = False
    state = coordinator.device.get_state("SOC")
    meta = {"name": state.fn_name, "unit": "%", "device_class": None, "state_class": None}

    entity = BluettiSensor(coordinator.device, state, meta)

    assert entity.available is False


async def test_binary_sensor_reflects_state_value(hass):
    coordinator = _make_coordinator(hass)
    state = coordinator.device.states[0]
    state.fn_value = "1"

    entity = BluettiBinarySensor(coordinator.device, state, {"name": "Online"})

    assert entity.is_on is True
    assert entity.has_entity_name is True


async def test_switch_is_on_and_off(hass):
    coordinator = _make_coordinator(hass)
    state = coordinator.device.get_state("SetCtrlAc")

    entity = BluettiSwitch(coordinator.device, state)

    assert entity.is_on is False
    assert entity.name == "AC Output"
    assert entity.unique_id == "SN1_SetCtrlAc"


async def test_switch_power_toggle_available_even_when_offline(hass):
    coordinator = _make_coordinator(hass)
    coordinator.device.on_line = "0"
    # SetCtrlPowerOn is not in the fixture state list; add it directly.
    from custom_components.bluetti.models import BluettiState

    power_state = BluettiState(
        fn_code="SetCtrlPowerOn", fn_name="Power", fn_value="1", fn_type="SWITCH"
    )
    coordinator.device.states.append(power_state)

    entity = BluettiSwitch(coordinator.device, power_state)

    assert entity.available is True


async def test_select_current_option_and_editability(hass):
    coordinator = _make_coordinator(hass)
    state = coordinator.device.get_state("SetCtrlWorkMode")

    entity = BluettiSelect(coordinator.device, state)

    assert entity.options == ["Standard", "Silent"]
    assert entity.current_option == "Standard"
    assert entity._readonly is False


async def test_select_readonly_state_keeps_options_populated(hass):
    coordinator = _make_coordinator(hass)
    state = coordinator.device.get_state("InvWorkState")

    entity = BluettiSelect(coordinator.device, state)

    assert entity._readonly is True
    # Options must stay populated so current_option is never reported as
    # outside of the advertised options list.
    assert entity.options == ["Idle"]
    assert entity.current_option == "Idle"


async def test_select_readonly_option_cannot_be_changed(hass):
    coordinator = _make_coordinator(hass)
    state = coordinator.device.get_state("InvWorkState")
    entity = BluettiSelect(coordinator.device, state)

    with pytest.raises(ServiceValidationError):
        await entity.async_select_option("Idle")


async def test_select_invalid_option_raises(hass):
    coordinator = _make_coordinator(hass)
    state = coordinator.device.get_state("SetCtrlWorkMode")
    entity = BluettiSelect(coordinator.device, state)

    with pytest.raises(ServiceValidationError):
        await entity.async_select_option("does-not-exist")
