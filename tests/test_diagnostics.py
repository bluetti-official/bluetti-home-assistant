"""Tests for diagnostics.py."""

from unittest.mock import MagicMock

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.bluetti import BluettiRuntimeData
from custom_components.bluetti.const import DOMAIN
from custom_components.bluetti.diagnostics import async_get_config_entry_diagnostics
from custom_components.bluetti.models import BluettiDevice


async def test_diagnostics_redacts_sensitive_data_and_lists_devices(hass):
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "auth_implementation": DOMAIN,
            "token": {"access_token": "super-secret", "refresh_token": "also-secret"},
            "products": [{"sn": "SN1", "name": "Device"}],
        },
        options={"devices": ["SN1"]},
    )
    entry.add_to_hass(hass)

    device = BluettiDevice(
        device_id="SN1", on_line="1", name="Test", sn="SN1", model="AC200L",
        state_list=[
            {
                "fnCode": "SOC", "fnName": "Battery", "fnValue": "80", "fnType": "SENSOR",
                "sensorInfo": {"sensorType": "SensorDeviceClass.BATTERY", "unit": None},
            },
            # No sensorInfo at all - some SENSOR-type states never carry one.
            {"fnCode": "Weird", "fnName": "Weird", "fnValue": "1", "fnType": "SENSOR"},
        ],
    )
    coordinator = MagicMock(last_update_success=True, update_interval="0:00:30")
    entry.runtime_data = BluettiRuntimeData(
        auth=MagicMock(),
        bluetti_devices=MagicMock(devices=[device]),
        stomp_client=MagicMock(),
        coordinators={"SN1": coordinator},
    )

    diagnostics = await async_get_config_entry_diagnostics(hass, entry)

    assert diagnostics["entry_data"]["token"] == "**REDACTED**"
    assert diagnostics["entry_data"]["products"] == "**REDACTED**"
    assert diagnostics["entry_options"] == {"devices": ["SN1"]}

    assert diagnostics["devices"] == [{
        "device_id": "SN1",
        "model": "AC200L",
        "online": True,
        "states": [
            {
                "fn_code": "SOC", "fn_type": "SENSOR", "fn_value": "80",
                "sensor_info": {"sensorType": "SensorDeviceClass.BATTERY", "unit": None},
            },
            {"fn_code": "Weird", "fn_type": "SENSOR", "fn_value": "1", "sensor_info": None},
        ],
    }]

    assert diagnostics["coordinators"]["SN1"]["last_update_success"] is True
