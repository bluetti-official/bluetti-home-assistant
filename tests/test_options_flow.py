"""Tests for the BLUETTI options flow (add devices without re-authenticating)."""

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from homeassistant.helpers.json import JSONEncoder
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.bluetti.const import DOMAIN
from custom_components.bluetti.model.product import UserProduct
from custom_components.bluetti.options_flow import BluettiOptionsFlowHandler


def _flow(hass, entry) -> BluettiOptionsFlowHandler:
    flow = BluettiOptionsFlowHandler()
    flow.hass = hass
    flow.handler = entry.entry_id
    return flow


def _entry(hass, *, products=None, devices=None) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "auth_implementation": DOMAIN,
            "token": {"access_token": "tok"},
            "products": products or [],
        },
        options={"devices": devices or []},
    )
    entry.add_to_hass(hass)
    return entry


async def test_shows_form_with_available_devices(hass):
    entry = _entry(hass, devices=["SN1"])
    flow = _flow(hass, entry)
    products = [
        UserProduct(sn="SN1", name="Already added", stateList=[], online="1"),
        UserProduct(sn="SN2", name="New device", stateList=[], online="1"),
    ]

    with patch("custom_components.bluetti.options_flow.async_get_clientsession"), \
         patch("custom_components.bluetti.options_flow.ProductClient") as mock_client_cls:
        mock_client_cls.return_value.get_user_products = AsyncMock(
            return_value=SimpleNamespace(data=products)
        )
        result = await flow.async_step_init(user_input=None)

    assert result["type"] == "form"
    assert result["step_id"] == "init"


async def test_no_devices_available_aborts(hass):
    entry = _entry(hass)
    flow = _flow(hass, entry)

    with patch("custom_components.bluetti.options_flow.async_get_clientsession"), \
         patch("custom_components.bluetti.options_flow.ProductClient") as mock_client_cls:
        mock_client_cls.return_value.get_user_products = AsyncMock(
            return_value=SimpleNamespace(data=[])
        )
        result = await flow.async_step_init(user_input=None)

    assert result["type"] == "abort"
    assert result["reason"] == "no_devices_available"


async def test_all_devices_already_enabled_aborts(hass):
    entry = _entry(hass, devices=["SN1"])
    flow = _flow(hass, entry)
    products = [UserProduct(sn="SN1", name="Already added", stateList=[], online="1")]

    with patch("custom_components.bluetti.options_flow.async_get_clientsession"), \
         patch("custom_components.bluetti.options_flow.ProductClient") as mock_client_cls:
        mock_client_cls.return_value.get_user_products = AsyncMock(
            return_value=SimpleNamespace(data=products)
        )
        result = await flow.async_step_init(user_input=None)

    assert result["type"] == "abort"
    assert result["reason"] == "all_devices_exists"


async def test_fetch_failure_aborts_cannot_connect(hass):
    entry = _entry(hass)
    flow = _flow(hass, entry)

    with patch("custom_components.bluetti.options_flow.async_get_clientsession"), \
         patch("custom_components.bluetti.options_flow.ProductClient") as mock_client_cls:
        mock_client_cls.return_value.get_user_products = AsyncMock(side_effect=RuntimeError("boom"))
        result = await flow.async_step_init(user_input=None)

    assert result["type"] == "abort"
    assert result["reason"] == "cannot_connect"


async def test_submit_binds_and_merges_devices_and_products(hass):
    entry = _entry(
        hass,
        products=[{"sn": "SN1", "name": "Existing", "stateList": [], "online": "1"}],
        devices=["SN1"],
    )
    flow = _flow(hass, entry)
    flow._product_client = AsyncMock()
    flow._products = [UserProduct(sn="SN2", name="New Device", stateList=[], online="1")]

    result = await flow.async_step_init(user_input={"devices": ["SN2"]})

    assert result["type"] == "create_entry"
    assert set(result["data"]["devices"]) == {"SN1", "SN2"}
    flow._product_client.bind_devices.assert_awaited_once_with({"bindSnList": ["SN2"]})

    updated = hass.config_entries.async_get_entry(entry.entry_id)
    stored_sns = {p["sn"] for p in updated.data["products"]}
    assert stored_sns == {"SN1", "SN2"}
    json.dumps(dict(updated.data), cls=JSONEncoder)  # must stay JSON-serializable


async def test_submit_bind_failure_aborts_cannot_connect(hass):
    entry = _entry(hass)
    flow = _flow(hass, entry)
    flow._product_client = AsyncMock()
    flow._product_client.bind_devices.side_effect = RuntimeError("boom")

    result = await flow.async_step_init(user_input={"devices": ["SN1"]})

    assert result["type"] == "abort"
    assert result["reason"] == "cannot_connect"


async def test_config_flow_exposes_options_flow(hass):
    from custom_components.bluetti.config_flow import BluettiConfigFlow

    entry = _entry(hass)
    flow = BluettiConfigFlow.async_get_options_flow(entry)

    assert isinstance(flow, BluettiOptionsFlowHandler)
