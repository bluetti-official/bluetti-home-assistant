"""The BLUETTI integration."""
# from __future__ import annotations

import logging
from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_entry_oauth2_flow, device_registry as dr, entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers import storage

from .coordinator import BluettiDeviceCoordinator
from .models import BluettiData
from .oauth import AsyncConfigEntryAuth,AuthTokenRefresh
from .api.bluetti import APPLICATION_PROFILE
from .api.product_client import ProductClient
from .api.websocket import StompClient
from .const import DOMAIN
from .model.product import UserProduct

__LOGGER__ = logging.getLogger(__name__)

_PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.SWITCH, Platform.SELECT]


@dataclass
class BluettiRuntimeData:
    """Runtime data stored on a BLUETTI config entry."""

    auth: AsyncConfigEntryAuth
    bluetti_devices: BluettiData
    stomp_client: StompClient
    coordinators: dict[str, BluettiDeviceCoordinator]


type BluettiConfigEntry = ConfigEntry[BluettiRuntimeData]


async def async_setup_entry(hass: HomeAssistant, entry: BluettiConfigEntry) -> bool:
    try:
        await APPLICATION_PROFILE.load_config(hass)

        enabled_devices = entry.options.get("devices", [])
        all_products_data: list[dict] = entry.data.get("products", [])
        all_products: list[UserProduct] = [
            UserProduct.model_validate(p) if isinstance(p, dict) else p
            for p in all_products_data
        ]

        """OAUTH2: get the access token."""
        implementation = (
            await config_entry_oauth2_flow.async_get_config_entry_implementation(
                hass, entry
            )
        )
        __LOGGER__.debug("OAuth implementation is: %s", implementation.__class__)

        httpSession = async_get_clientsession(hass)
        oAuth2Session = config_entry_oauth2_flow.OAuth2Session(hass, entry, implementation)
        auth = AsyncConfigEntryAuth(httpSession, oAuth2Session)

        authTokenRefresh = AuthTokenRefresh(hass,entry,oAuth2Session)
        authTokenRefresh.start_token_check()

        # await oAuth2Session.async_ensure_token_valid()
        access_token = oAuth2Session.token["access_token"]
        product_client = ProductClient(httpSession, access_token,hass)
        # products = await product_client.get_user_products()
        # print(products.data[0].__class__)
        # print(products.data)
    except Exception as err:
        raise ConfigEntryNotReady(f"BLUETTI setup failed: {err}") from err

    selected_products = [p for p in all_products if p.sn in enabled_devices]

    bluetti_devices = BluettiData(hass, selected_products)

    # Register WebSocket
    stomp_client = StompClient(APPLICATION_PROFILE.config["server"]["wss"], access_token, bluetti_devices.web_socket_message_handler,hass)
    stomp_client.connect()

    coordinators: dict[str, BluettiDeviceCoordinator] = {}
    for device in bluetti_devices.devices:
        device._api_client = product_client
        device.name = device.sn
        device._hass = hass
        device._entry = entry
        device._entry_id = entry.entry_id
        coordinators[device.device_id] = BluettiDeviceCoordinator(hass, entry, device)

    for coordinator in coordinators.values():
        await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = BluettiRuntimeData(
        auth=auth,
        bluetti_devices=bluetti_devices,
        stomp_client=stomp_client,
        coordinators=coordinators,
    )

    await hass.config_entries.async_forward_entry_setups(entry, _PLATFORMS)

    __LOGGER__.info('bluetti init ok')

    return True


async def async_unload_entry(hass: HomeAssistant, entry: BluettiConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, _PLATFORMS)
    runtime_data = getattr(entry, "runtime_data", None)
    if unloaded and runtime_data:
        try:
            runtime_data.stomp_client.disconnect()
        except Exception as e:
            __LOGGER__.warning("Error while disconnecting websocket: %s", e)
    return unloaded

async def async_remove_entry(hass, entry: BluettiConfigEntry):
    """Handle removal of an entry."""
    runtime_data = getattr(entry, "runtime_data", None)
    if runtime_data:
        try:
            runtime_data.stomp_client.disconnect()
        except Exception as e:
            __LOGGER__.warning("Error while disconnecting websocket: %s", e)

    device_registry = dr.async_get(hass)
    for device in dr.async_entries_for_config_entry(device_registry, entry.entry_id):
        device_registry.async_remove_device(device.id)

    entity_registry = er.async_get(hass)
    for entity in er.async_entries_for_config_entry(entity_registry, entry.entry_id):
        entity_registry.async_remove(entity.entity_id)

    store = storage.Store(hass, 1, f"{DOMAIN}_data_{entry.entry_id}.json")
    await store.async_remove()