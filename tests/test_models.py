"""Tests for the BLUETTI data models."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.exceptions import HomeAssistantError

from custom_components.bluetti.models import BluettiData, BluettiDevice, BluettiState


def test_state_is_switch_without_modes():
    state = BluettiState(fn_code="SetCtrlAc", fn_name="AC", fn_value="0", fn_type="SWITCH")
    assert state.is_switch() is True
    assert state.get_name_for_value() == "Off"


def test_state_set_value_switch():
    state = BluettiState(fn_code="SetCtrlAc", fn_name="AC", fn_value="0", fn_type="SWITCH")
    state.set_value("1")
    assert state.fn_value == "1"
    assert state.get_name_for_value() == "On"


def test_state_select_valid_value():
    modes = [{"code": "0", "name": "Standard"}, {"code": "1", "name": "Silent"}]
    state = BluettiState(
        fn_code="SetCtrlWorkMode", fn_name="Mode", fn_value="0", fn_type="SELECT",
        support_mode_values=modes,
    )
    state.set_value("1")
    assert state.fn_value == "1"
    assert state.get_name_for_value() == "Silent"


def test_state_select_invalid_value_raises():
    modes = [{"code": "0", "name": "Standard"}]
    state = BluettiState(
        fn_code="SetCtrlWorkMode", fn_name="Mode", fn_value="0", fn_type="SELECT",
        support_mode_values=modes,
    )
    with pytest.raises(ValueError):
        state.set_value("99")


def test_device_get_state_returns_none_for_missing_code():
    device = BluettiDevice(device_id="SN1", on_line="1", name="Test", sn="SN1", model="AC200L")
    assert device.get_state("does-not-exist") is None


def test_state_falls_back_to_fn_code_when_fn_name_is_blank():
    """Some fn_codes come back from the API without a localized fnName.

    With has_entity_name = True, an empty entity name makes Home
    Assistant's frontend display the raw entity_id (which contains the
    device serial number) instead of a real label, so BluettiDevice must
    fall back to a non-empty name when building its states.
    """
    device = BluettiDevice(
        device_id="SN1", on_line="1", name="Test", sn="SN1", model="AC200L",
        state_list=[{"fnCode": "SetCtrlWorkMode", "fnValue": "2", "fnType": "SELECT"}],
    )
    state = device.get_state("SetCtrlWorkMode")
    assert state.fn_name == "SetCtrlWorkMode"


def test_device_battery_level_reads_soc_state():
    device = BluettiDevice(
        device_id="SN1", on_line="1", name="Test", sn="SN1", model="AC200L",
        state_list=[{"fnCode": "SOC", "fnName": "Battery", "fnValue": "42", "fnType": "SENSOR"}],
    )
    assert device.battery_level == 42


def test_device_battery_level_defaults_to_zero_without_soc():
    device = BluettiDevice(device_id="SN1", on_line="1", name="Test", sn="SN1", model="AC200L")
    assert device.battery_level == 0


def test_device_online_property():
    device = BluettiDevice(device_id="SN1", on_line="1", name="Test", sn="SN1", model="AC200L")
    assert device.online is True
    device.on_line = "0"
    assert device.online is False


def test_bluetti_data_get_device_by_sn():
    fake_hass = SimpleNamespace(loop=None)
    product = SimpleNamespace(sn="SN1", online="1", name="Test", model="AC200L", stateList=[])
    data = BluettiData(fake_hass, [product])
    assert data.get_device_by_sn("SN1") is not None
    assert data.get_device_by_sn("unknown") is None


async def test_async_refresh_from_api_updates_states():
    device = BluettiDevice(
        device_id="SN1", on_line="0", name="Test", sn="SN1", model="AC200L",
        state_list=[{"fnCode": "SOC", "fnName": "Battery", "fnValue": "10", "fnType": "SENSOR"}],
    )
    status_data = SimpleNamespace(
        sn="SN1", online="1", isBindByCurUser="1",
        stateList=[{"fnCode": "SOC", "fnValue": "77"}],
    )
    device._api_client = AsyncMock()
    device._api_client.get_device_status.return_value = SimpleNamespace(data=[status_data])

    await device.async_refresh_from_api()

    assert device.online is True
    assert device.get_state("SOC").fn_value == "77"


async def test_async_refresh_from_api_raises_on_empty_data():
    device = BluettiDevice(device_id="SN1", on_line="1", name="Test", sn="SN1", model="AC200L")
    device._api_client = AsyncMock()
    device._api_client.get_device_status.return_value = SimpleNamespace(data=[])

    with pytest.raises(RuntimeError):
        await device.async_refresh_from_api()


async def test_async_refresh_from_api_ignores_mismatched_sn():
    device = BluettiDevice(
        device_id="SN1", on_line="0", name="Test", sn="SN1", model="AC200L",
        state_list=[{"fnCode": "SOC", "fnName": "Battery", "fnValue": "10", "fnType": "SENSOR"}],
    )
    status_data = SimpleNamespace(sn="OTHER-SN", online="1", isBindByCurUser="1", stateList=[])
    device._api_client = AsyncMock()
    device._api_client.get_device_status.return_value = SimpleNamespace(data=[status_data])

    await device.async_refresh_from_api()

    # Nothing should have changed since the response was for a different device.
    assert device.on_line == "0"
    assert device.get_state("SOC").fn_value == "10"


async def test_set_state_value_applies_optimistic_update_and_notifies_coordinator():
    device = BluettiDevice(
        device_id="SN1", on_line="1", name="Test", sn="SN1", model="AC200L",
        state_list=[{"fnCode": "SetCtrlAc", "fnName": "AC", "fnValue": "0", "fnType": "SWITCH"}],
    )
    device._api_client = AsyncMock()
    device._api_client.control_device.return_value = SimpleNamespace(msgCode=0)
    device.coordinator = MagicMock()

    await device.set_state_value("SetCtrlAc", "1")

    assert device.get_state("SetCtrlAc").fn_value == "1"
    device.coordinator.async_set_updated_data.assert_called_once_with(device)


async def test_set_state_value_does_not_apply_on_server_error_code():
    device = BluettiDevice(
        device_id="SN1", on_line="1", name="Test", sn="SN1", model="AC200L",
        state_list=[{"fnCode": "SetCtrlAc", "fnName": "AC", "fnValue": "0", "fnType": "SWITCH"}],
    )
    device._api_client = AsyncMock()
    device._api_client.control_device.return_value = SimpleNamespace(msgCode=1)
    device.coordinator = MagicMock()

    await device.set_state_value("SetCtrlAc", "1")

    assert device.get_state("SetCtrlAc").fn_value == "0"


async def test_set_state_value_wraps_api_errors():
    device = BluettiDevice(
        device_id="SN1", on_line="1", name="Test", sn="SN1", model="AC200L",
        state_list=[{"fnCode": "SetCtrlAc", "fnName": "AC", "fnValue": "0", "fnType": "SWITCH"}],
    )
    device._api_client = AsyncMock()
    device._api_client.control_device.side_effect = RuntimeError("boom")

    with pytest.raises(HomeAssistantError):
        await device.set_state_value("SetCtrlAc", "1")


async def test_set_state_value_unknown_fn_code_raises_value_error():
    device = BluettiDevice(device_id="SN1", on_line="1", name="Test", sn="SN1", model="AC200L")

    with pytest.raises(ValueError):
        await device.set_state_value("does-not-exist", "1")
