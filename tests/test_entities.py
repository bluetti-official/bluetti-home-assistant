"""Tests for the BLUETTI entity platforms (sensor/binary_sensor, switch, select)."""

from datetime import timedelta

import pytest
from homeassistant.components.sensor import SensorDeviceClass, SensorExtraStoredData, SensorStateClass
from homeassistant.exceptions import ServiceValidationError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.bluetti.const import DOMAIN
from custom_components.bluetti.coordinator import BluettiDeviceCoordinator
from custom_components.bluetti.models import BluettiDevice, BluettiState
from custom_components.bluetti.select import BluettiSelect
from custom_components.bluetti.sensor import BluettiBinarySensor, BluettiEnergySensor, BluettiSensor
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


def _add_power_state(coordinator) -> BluettiState:
    power_state = BluettiState(
        fn_code="PVAllTotalPower", fn_name="PV Input Power", fn_value="100", fn_type="SENSOR",
    )
    coordinator.device.states.append(power_state)
    return power_state


async def test_energy_sensor_has_distinct_unique_id_and_energy_attributes(hass):
    coordinator = _make_coordinator(hass)
    power_state = _add_power_state(coordinator)
    power_sensor = BluettiSensor(
        coordinator.device, power_state,
        {"name": power_state.fn_name, "unit": "W", "device_class": SensorDeviceClass.POWER,
         "state_class": SensorStateClass.MEASUREMENT},
    )

    energy_sensor = BluettiEnergySensor(coordinator.device, power_state)

    # Both entities share the same underlying state (same fn_code), so the
    # energy companion must not collide with the power sensor's unique_id.
    assert energy_sensor.unique_id == "SN1_PVAllTotalPower_energy"
    assert energy_sensor.unique_id != power_sensor.unique_id
    assert energy_sensor.name == "PV Input Power Energy"
    assert energy_sensor.device_class == SensorDeviceClass.ENERGY
    assert energy_sensor.native_unit_of_measurement == "kWh"
    assert energy_sensor.native_value == 0.0


async def test_energy_sensor_integrates_power_trapezoidally_over_time(hass, freezer):
    coordinator = _make_coordinator(hass)
    power_state = _add_power_state(coordinator)
    entity = BluettiEnergySensor(coordinator.device, power_state)
    entity.hass = hass
    entity.entity_id = "sensor.test_pv_energy"

    await entity.async_added_to_hass()

    freezer.tick(timedelta(hours=1))
    power_state.fn_value = "300"
    entity._handle_coordinator_update()

    # Trapezoidal rule: (100 W + 300 W) / 2 = 200 W average over 1 hour =
    # 0.2 kWh - the same result a manually added "Integral - Riemann sum"
    # helper (trapezoidal, kilo prefix, hours) would compute.
    assert entity.native_value == 0.2

    freezer.tick(timedelta(hours=2))
    power_state.fn_value = "300"
    entity._handle_coordinator_update()

    # Constant 300 W for 2 more hours = 0.6 kWh, cumulated on top of the 0.2
    # already integrated.
    assert entity.native_value == 0.8

    await coordinator.async_shutdown()


async def test_energy_sensor_restores_previous_total_on_startup(hass):
    coordinator = _make_coordinator(hass)
    power_state = _add_power_state(coordinator)
    entity = BluettiEnergySensor(coordinator.device, power_state)
    entity.hass = hass
    entity.entity_id = "sensor.test_pv_energy"

    async def fake_last_sensor_data():
        return SensorExtraStoredData(42.5, "kWh")

    entity.async_get_last_sensor_data = fake_last_sensor_data

    await entity.async_added_to_hass()

    assert entity.native_value == 42.5

    await coordinator.async_shutdown()


async def test_energy_sensor_treats_non_numeric_power_value_as_unknown(hass, freezer):
    coordinator = _make_coordinator(hass)
    power_state = _add_power_state(coordinator)
    entity = BluettiEnergySensor(coordinator.device, power_state)
    entity.hass = hass
    entity.entity_id = "sensor.test_pv_energy"

    await entity.async_added_to_hass()

    freezer.tick(timedelta(hours=1))
    power_state.fn_value = None  # e.g. a transient malformed API response
    entity._handle_coordinator_update()
    # A non-numeric reading can't contribute to the trapezoidal area, and
    # must not crash the update either.
    assert entity.native_value == 0.0

    await coordinator.async_shutdown()


async def test_energy_sensor_skips_integration_across_unavailable_gap(hass, freezer):
    coordinator = _make_coordinator(hass)
    power_state = _add_power_state(coordinator)
    entity = BluettiEnergySensor(coordinator.device, power_state)
    entity.hass = hass
    entity.entity_id = "sensor.test_pv_energy"

    await entity.async_added_to_hass()

    coordinator.device.on_line = "0"
    freezer.tick(timedelta(hours=5))
    entity._handle_coordinator_update()
    # No area is computed while the device (and thus this sensor) is
    # unavailable, to avoid a bogus energy spike once it reconnects.
    assert entity.native_value == 0.0

    coordinator.device.on_line = "1"
    freezer.tick(timedelta(hours=1))
    power_state.fn_value = "200"
    entity._handle_coordinator_update()
    # Only one real sample is known since coming back online, so no area
    # can be computed yet for this first post-outage update.
    assert entity.native_value == 0.0

    freezer.tick(timedelta(hours=1))
    power_state.fn_value = "200"
    entity._handle_coordinator_update()
    assert entity.native_value == 0.2

    await coordinator.async_shutdown()


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
