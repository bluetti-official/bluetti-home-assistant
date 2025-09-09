"""The BLUETTI integration."""
# from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_entry_oauth2_flow
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .models import BluettiData
from .oauth import ConfigEntryAuth
from .api.bluetti import APPLICATION_PROFILE
from .api.product_client import ProductClient
from .api.websocket import StompClient
from .profile.application_profile import ApplicationProfile
from .const import DOMAIN
from .model.product import UserProduct

__LOGGER__ = logging.getLogger(__name__)

# TODO List the platforms that you want to support.
# For your initial PR, limit it to 1 platform. Platform.LIGHT,
_PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.SWITCH, Platform.SELECT]

# Create ConfigEntry type alias with ConfigEntryAuth or AsyncConfigEntryAuth object
type BluettiConfigEntry = ConfigEntry[BluettiData]


# type Oauth2ConfigEntry = ConfigEntry[api.AsyncConfigEntryAuth]

async def async_setup_entry(hass: HomeAssistant, entry: BluettiConfigEntry) -> bool:
    APPLICATION_PROFILE.load_config(hass)

    enabled_devices = entry.options.get("devices", [])
    auth_token = entry.data.get('auth_token')
    all_products_data: list[dict] = entry.data.get("products", [])
    all_products: list[UserProduct] = [
        UserProduct.model_validate(p) if isinstance(p, dict) else p
        for p in all_products_data
    ]
    
    """OAUTH2: get the access token."""
    # implementation = (
    #     await config_entry_oauth2_flow.async_get_config_entry_implementation(
    #         hass, entry
    #     )
    # )
    # __LOGGER__.debug("OAuth implementation is: %s", implementation.__class__)

    httpSession = async_get_clientsession(hass)
    # oAuth2Session = config_entry_oauth2_flow.OAuth2Session(hass, entry, implementation)

    # If using a requests-based API lib
    # entry.runtime_data = ConfigEntryAuth(hass, oAuth2Session)

    # If using an aiohttp-based API lib
    # entry.runtime_data = api.AsyncConfigEntryAuth(
    #     aiohttp_client.async_get_clientsession(hass), session
    # )

    # await hass.config_entries.async_forward_entry_setups(entry, _PLATFORMS)
    # access_token = oAuth2Session.token["access_token"]
    access_token = auth_token['token']["access_token"]
    product_client = ProductClient(httpSession, access_token)
    # products = await product_client.get_user_products()
    # print(products.data[0].__class__)
    # print(products.data)

    selected_products = [p for p in all_products if p.sn in enabled_devices]

    bluetti_devices = BluettiData(hass, selected_products)

    # Register WebSocket
    stomp_client = StompClient(APPLICATION_PROFILE.config["server"]["wss"], access_token, bluetti_devices.web_socket_message_handler)
    stomp_client.connect()

    for device in bluetti_devices.devices:
        device._api_client = product_client
        # device._ws_manager = stomp_client

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "bluettiDevices": bluetti_devices
    }

    await hass.config_entries.async_forward_entry_setups(entry, _PLATFORMS)

    return True

def web_socket_message_handler(message: str):
    
    print(message)

# TODO Update entry annotation
async def async_unload_entry(hass: HomeAssistant, entry: BluettiConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, _PLATFORMS)
