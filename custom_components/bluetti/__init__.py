"""The BLUETTI integration."""
# from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_entry_oauth2_flow, device_registry as dr, entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers import storage
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED

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
    await APPLICATION_PROFILE.load_config(hass)

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
        "bluettiDevices": bluetti_devices,
        "stompClient": stomp_client,
    }

    await hass.config_entries.async_forward_entry_setups(entry, _PLATFORMS)

    async def _after_start(event):
        # print(event)
        for device in bluetti_devices.devices:
            await device.async_update()

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _after_start)

    return True

def web_socket_message_handler(message: str):
    
    print(message)

# TODO Update entry annotation
async def async_unload_entry(hass: HomeAssistant, entry: BluettiConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, _PLATFORMS)

async def async_remove_entry(hass, entry):
    """Handle removal of an entry."""
    data = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if data and "stompClient" in data:
        stomp_client = data["stompClient"]
        try:
            stomp_client.disconnect()
        except Exception as e:
            __LOGGER__.warning("Error while disconnecting websocket: %s", e)

    device_registry = dr.async_get(hass)
    for device in dr.async_entries_for_config_entry(device_registry, entry.entry_id):
        device_registry.async_remove_device(device.id)

    entity_registry = er.async_get(hass)
    for entity in er.async_entries_for_config_entry(entity_registry, entry.entry_id):
        entity_registry.async_remove(entity.entity_id)

    if DOMAIN in hass.data:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        if not hass.data[DOMAIN]:
            hass.data.pop(DOMAIN)

    store = storage.Store(hass, 1, f"{DOMAIN}_data_{entry.entry_id}.json")
    await store.async_remove()