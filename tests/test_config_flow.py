"""Tests for config_flow.py."""

from unittest.mock import AsyncMock, patch

from homeassistant.helpers import config_entry_oauth2_flow
from homeassistant.setup import async_setup_component

from custom_components.bluetti.config_flow import BluettiConfigFlow


async def test_async_step_user_imports_credentials_and_delegates(hass, enable_custom_integrations):
    await async_setup_component(hass, "application_credentials", {})

    flow = BluettiConfigFlow()
    flow.hass = hass

    with patch.object(
        config_entry_oauth2_flow.AbstractOAuth2FlowHandler,
        "async_step_user",
        new=AsyncMock(return_value={"type": "form", "step_id": "pick_implementation"}),
    ) as mock_super:
        result = await flow.async_step_user(None)

    mock_super.assert_awaited_once_with(None)
    assert result["step_id"] == "pick_implementation"
