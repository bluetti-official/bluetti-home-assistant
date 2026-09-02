"""The BLUETTI integration."""
import json
# from __future__ import annotations

import logging
import os
import asyncio

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_entry_oauth2_flow, device_registry as dr, entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers import storage
from homeassistant.loader import async_get_integration

from .models import BluettiData
from .oauth import AsyncConfigEntryAuth, AuthTokenRefresh
from .api.bluetti import APPLICATION_PROFILE
from .api.product_client import ProductClient
from .api.websocket import StompClient
from .profile.application_profile import ApplicationProfile
from .const import DOMAIN, DOWNDIR, DOWNDIR_DATA_KEY, EVENT_BLUETTI_SETUP_OK, ControlMode
from .model.product import UserProduct

# from .localization import LocalizationManager


__LOGGER__ = logging.getLogger(__name__)

# TODO List the platforms that you want to support.
# For your initial PR, limit it to 1 platform. Platform.LIGHT,
_PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.SWITCH, Platform.SELECT]

# Create ConfigEntry type alias with ConfigEntryAuth or AsyncConfigEntryAuth object
type BluettiConfigEntry = ConfigEntry[BluettiData]


# LOCALIZATION_MANAGER: LocalizationManager = None

# type Oauth2ConfigEntry = ConfigEntry[api.AsyncConfigEntryAuth]


async def async_setup_entry(hass: HomeAssistant, entry: BluettiConfigEntry) -> bool:
    await APPLICATION_PROFILE.load_config(hass)

    # global LOCALIZATION_MANAGER
    # LOCALIZATION_MANAGER = LocalizationManager(hass, DOMAIN)

    DOWNLOAD_DIR = os.path.join(hass.config.config_dir, f"custom_components/{DOMAIN}/{DOWNDIR}")
    if os.path.exists(DOWNLOAD_DIR) == False:
        # 2. 确保目录存在（异步执行文件操作，避免阻塞）
        await hass.async_add_executor_job(os.makedirs, DOWNLOAD_DIR)
    hass.data.setdefault(DOMAIN, {})[DOWNDIR_DATA_KEY] = DOWNLOAD_DIR

    enabled_devices = entry.options.get("devices", [])
    deviceKeyDict = entry.options.get("deviceKeyDict", {})
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

    # __LOGGER__.setLevel(logging.DEBUG)
    # __LOGGER__.debug("OAuth implementation is: %s", implementation.__class__)

    httpSession = async_get_clientsession(hass)
    oAuth2Session = config_entry_oauth2_flow.OAuth2Session(hass, entry, implementation)

    # If using a requests-based API lib
    # entry.runtime_data = ConfigEntryAuth(hass, oAuth2Session)

    # If using an aiohttp-based API lib
    entry.runtime_data = AsyncConfigEntryAuth(
        httpSession, oAuth2Session
    )

    authTokenRefresh = AuthTokenRefresh(hass, entry, oAuth2Session)
    authTokenRefresh.start_token_check()

    # await oAuth2Session.async_ensure_token_valid()
    access_token = oAuth2Session.token["access_token"]
    # TODO APIs should be invoked only after AccessToken processing succeeds,
    #  prioritizing the host address prefix returned by the cloud.
    product_client = ProductClient(httpSession, access_token, hass)
    # products = await product_client.get_user_products()
    # print(products.data[0].__class__)
    # print(products.data)

    selected_products = [p for p in all_products if p.sn in enabled_devices]

    # check ble key is ok
    is_update_entry = False
    for device in selected_products:
        if device.control_mode == ControlMode.BLE and device.server_key == None or device.server_key == '':
            decrypt_info_resp = await product_client.get_decrypt_info(device.sn)
            decrypt_info = decrypt_info_resp.data
            device.server_key = decrypt_info.encryptKey
            is_update_entry = True
    if is_update_entry:
        # update existing entry
        hass.config_entries.async_update_entry(
            entry,
            data=dict(entry.data) | {"products": all_products}
        )

    bluetti_devices = BluettiData(hass=hass, devices=selected_products)

    # initialize stomp_client to None
    stomp_client = None
    hasCloudControl = any(device.control_mode == ControlMode.CLOUD for device in bluetti_devices.devices)
    if hasCloudControl:
        # In most cases, according to the principle of nearest access,
        # the IP address of the server in the nearest data center to the customer will be returned.
        # However, the intelligent DNS service may also encounter misjudgment situations,
        # or if the customer uses a network proxy, this would violate the principle of nearest access,
        # resulting in the customer accessing the wrong data center.
        # Therefore, a reliable approach is to select an appropriate data center
        # based on the country where the customer account is registered,
        # and to follow the principle of nearest access as much as possible.
        # print(json.dumps(oAuth2Session.token, indent=2, ensure_ascii=False, default=str))
        config_token = dict(entry.data.get("token", {}))
        cloud_host = config_token.get("host", None)

        if "host" in oAuth2Session.token and cloud_host != oAuth2Session.token["host"]:
            cloud_host = oAuth2Session.token["host"]
            config_token.setdefault("host", cloud_host)
            hass.config_entries.async_update_entry(entry, data={**entry.data, "token": config_token})

        # Determine the WebSocket protocol
        endpoint = (cloud_host or APPLICATION_PROFILE.config["server"]["gateway"]).split("://")
        if endpoint[0] == "https":
            ws_protocol = "wss://"
        else:
            ws_protocol = "ws://"

        ws_url = ws_protocol + endpoint[1] + "/api/edgeiotgw/ws-coordination/websocket"
        # print(ws_url)
        # Register WebSocket
        stomp_client = StompClient(ws_url, access_token, APPLICATION_PROFILE.config,
                                   bluetti_devices.web_socket_message_handler, hass)
        stomp_client.connect()

    hasBleControl = any(device.control_mode == ControlMode.BLE for device in bluetti_devices.devices)
    if hasBleControl:
        from .ble.ble_decoder import start_ble_lib
        start_ble_lib()

    # initialize data storage structure
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault(entry.entry_id, {})

    for device in bluetti_devices.devices:
        device._api_client = product_client
        device.name = device.sn
        device._hass = hass
        device._entry = entry
        device._entry_id = entry.entry_id

    hass.data[DOMAIN][entry.entry_id].update({
        "bluettiDevices": bluetti_devices,
        "stompClient": stomp_client,
    })

    await hass.config_entries.async_forward_entry_setups(entry, _PLATFORMS)

    async def _after_bluetti_setup_ok(event):
        __LOGGER__.debug('ble mode _after_component_loaded')
        # update data from cloud
        for device in bluetti_devices.devices:
            if device.control_mode == ControlMode.CLOUD:
                asyncio.run_coroutine_threadsafe(device.async_update(), hass.loop)

        # start ble proto file down
        await bluetti_devices.asyc_start_down_proto(hass=hass)

    unsub = hass.bus.async_listen(EVENT_BLUETTI_SETUP_OK, _after_bluetti_setup_ok)
    entry.async_on_unload(unsub)
    hass.bus.fire(EVENT_BLUETTI_SETUP_OK)

    __LOGGER__.info('bluetti init ok')

    return True


def web_socket_message_handler(message: str):
    __LOGGER__.debug(message)


# TODO Update entry annotation
async def async_unload_entry(hass: HomeAssistant, entry: BluettiConfigEntry) -> bool:
    """Unload a config entry."""

    # global LOCALIZATION_MANAGER
    # if LOCALIZATION_MANAGER:
    #     await LOCALIZATION_MANAGER.async_cleanup()
    await disconnect_ws(hass, entry)

    # remove download file
    bluetti_devices: BluettiData = hass.data[DOMAIN][entry.entry_id]["bluettiDevices"]
    await bluetti_devices.disconnect_all_ble(hass)
    await bluetti_devices.remove_download_file(hass)

    # reload config file
    await APPLICATION_PROFILE.unload();

    return await hass.config_entries.async_unload_platforms(entry, _PLATFORMS)


async def async_remove_entry(hass, entry):
    """Handle removal of an entry."""
    await disconnect_ws(hass, entry)

    # remove download file
    bluetti_devices: BluettiData = hass.data[DOMAIN][entry.entry_id]["bluettiDevices"]
    await bluetti_devices.remove_download_file(hass)

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


async def disconnect_ws(hass, entry):
    data = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if data and "stompClient" in data:
        stomp_client = data["stompClient"]
        try:
            if stomp_client != None:
                stomp_client.disconnect()
        except Exception as e:
            __LOGGER__.warning("Error while disconnecting websocket: %s", e)
