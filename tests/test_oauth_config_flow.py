"""Regression tests for the OAuth2 config flow's config entry data.

entry.data must only ever contain plain JSON-serializable values. If it
contains pydantic model instances (or anything else json.dumps can't
handle), Home Assistant's config entry storage silently fails to persist
the entry in the background - the integration works until the next
restart, at which point the entry (and its device) is gone.
"""

import json
from unittest.mock import AsyncMock

from homeassistant.helpers.json import JSONEncoder

from custom_components.bluetti.model.product import UserProduct
from custom_components.bluetti.oauth import OAuth2FlowHandler


async def test_new_entry_products_are_json_serializable(hass):
    flow = OAuth2FlowHandler()
    flow.hass = hass
    flow.context = {}
    flow._oauth_data = {
        "auth_implementation": "bluetti",
        "token": {"access_token": "tok", "expires_at": 9999999999},
    }
    flow._products = [UserProduct(sn="SN1", name="Device 1", stateList=[], online="1")]
    flow._product_client = AsyncMock()

    result = await flow.async_step_select_devices(user_input={"devices": ["SN1"]})

    assert result["type"] == "create_entry"
    stored_products = result["data"]["products"]
    assert all(isinstance(p, dict) for p in stored_products)
    # Must not raise: this is what Home Assistant does to persist the entry.
    json.dumps(result["data"], cls=JSONEncoder)
