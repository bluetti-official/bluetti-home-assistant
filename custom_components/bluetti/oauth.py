import logging

from typing import cast
import time
from datetime import datetime, timedelta
from homeassistant.components import persistent_notification
from homeassistant.helpers.event import async_track_time_interval
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_entry_oauth2_flow
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers import translation, selector
from homeassistant.components.bluetooth import async_discovered_service_info
from aiohttp import ClientSession
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
)
from .api.bluetti import APPLICATION_PROFILE

import voluptuous as vol

from.ble.utils.device_builder import is_device_support
from .api.product_client import ProductClient
from .const import DOMAIN, INTEGRATION_NAME,EVENT_TOKEN_EXPIRED,NOTIFY_ID_TOKEN_EXPIRED,AppPath,ControlMode

__LOGGER__ = logging.getLogger(__name__)


class OAuth2FlowHandler(config_entry_oauth2_flow.AbstractOAuth2FlowHandler, domain=DOMAIN):
    """Config flow to handle BLUETTI OAuth2 authentication."""

    DOMAIN = DOMAIN
    reauth_supported = True

    @property
    def logger(self) -> logging.Logger:
        """Return logger."""
        return logging.getLogger(__name__)

    async def _get_control_mode_options(self) -> dict[str, str]:
        """get control mode options translation."""
        translations = await translation.async_get_translations(
            self.hass, self.hass.config.language, "config", [DOMAIN]
        )
        base_key = "config.step.select_devices.data_options.control_mode"
        defaults = {ControlMode.CLOUD: "Cloud Control", ControlMode.BLE: "Bluetooth Control"}
        return {
            mode: translations.get(f"{DOMAIN}::{base_key}.{mode}", defaults[mode])
            for mode in defaults
        }

    async def _auto_match_bluetooth_devices(self, selected_cloud_products: list) -> dict[str, str]:
        """
        automatically match bluetooth devices with cloud devices

        parameters:
            selected_cloud_products: selected cloud device list

        return:
            dict: {MAC address: cloud SN} mapping dictionary
        """
        device_mapping = {}

        if not selected_cloud_products:
            return device_mapping

        __LOGGER__.debug(f"start automatically matching bluetooth devices, cloud device count: {len(selected_cloud_products)}")

        # scan discovered bluetooth devices
        discovered_bt_devices = async_discovered_service_info(self.hass)
        __LOGGER__.debug(f"scanned bluetooth devices count: {len(discovered_bt_devices)}")

        # create cloud SN to product mapping for easy lookup
        cloud_sn_to_product = {product.sn: product for product in selected_cloud_products}

        # iterate over bluetooth devices, match cloud devices
        for bt_device in discovered_bt_devices:
            if not bt_device.name:
                continue

            bt_name = bt_device.name.strip()
            bt_address = bt_device.address

            # direct match: bluetooth device name == cloud SN
            if bt_name in cloud_sn_to_product:
                cloud_product = cloud_sn_to_product[bt_name]
                device_mapping[bt_address] = cloud_product.sn
                __LOGGER__.info(
                    f"successfully matched: bluetooth device {bt_name} ({bt_address}) -> cloud device SN={cloud_product.sn}"
                )
            else:
                __LOGGER__.debug(
                    f"no match found: bluetooth device name={bt_name}, address={bt_address}"
                )

        # check unmatched cloud devices
        matched_sns = set(device_mapping.values())
        unmatched_products = [
            p for p in selected_cloud_products
            if p.sn not in matched_sns
        ]

        if unmatched_products:
            __LOGGER__.warning(
                f"the following cloud devices were not found to match the bluetooth devices: {[p.sn for p in unmatched_products]}"
            )

        __LOGGER__.info(f"automatically matching completed, successfully matched {len(device_mapping)} devices")

        return device_mapping

    async def async_oauth_create_entry(self, data: dict) -> config_entries.ConfigFlowResult:
        """Handle OAuth2 callback and create config entry."""
        self._oauth_data = data

        # reconfigure token
        if "entry_id" in self.context:
            cur_entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
            __LOGGER__.info("reconfigure token")
            new_data = {**cur_entry.data,"token":self._oauth_data["token"]}
            self.hass.config_entries.async_update_entry(
                    cur_entry,
                    data=new_data
                )
            await self.hass.config_entries.async_reload(cur_entry.entry_id)
            return self.async_abort(reason="success")
        
        # select device
        return await self.async_step_select_devices()

    async def async_step_select_devices(self, user_input=None):
        """Let user select devices after OAuth2 login."""
        
        errorDesc = None
        control_mode = None
        user_selected_device = None
        if user_input is not None:
            # print(user_input)
            await self._product_client.bind_devices({"bindSnList": user_input['devices']})

            user_selected_device = {sn: sn for sn in user_input['devices']}
            control_mode = user_input.get("control_mode", ControlMode.CLOUD)
            device_mapping = {}  # MAC address -> cloud SN mapping
            
            # get selected devices
            selected_products = [
                p for p in self._products
                if p.sn in user_input['devices']
            ]

            # if bluetooth control or auto mode is enabled, automatically match bluetooth devices
            if control_mode in [ControlMode.BLE]:
                
                # automatically match bluetooth devices
                device_mapping = await self._auto_match_bluetooth_devices(selected_products)
                
                # save data to flow context, for confirmation step use
                self._pending_user_input = user_input
                self._pending_device_mapping = device_mapping
                self._pending_selected_products = selected_products

                # get dencrypt info and check all device is suuport ble
                unsupported_sn = []
                try:
                    for product in selected_products:
                        decrypt_info_resp = await self._product_client.get_decrypt_info(product.sn)
                        decrypt_info = decrypt_info_resp.data
                        product.server_key = decrypt_info.encryptKey
                        product.proto_file_url = APPLICATION_PROFILE.config["server"]["gateway"] + AppPath.DECODE_CENTER_API +'/'+ decrypt_info.protoBufFileUrl
                        # all device have ble model,but the intergation may don't support, so check the device is supported by the cur ble lib version,
                        if not await is_device_support(product.model):
                            unsupported_sn.append(product.sn)
                except Exception as e:
                    errorDesc = f"Get Ble Key Error,Please try again later."

                if unsupported_sn:
                    errorDesc = f"The following devices do not support BLE control：{', '.join(unsupported_sn)}"                    

                # show confirmation form (whether or not to match devices)
                if errorDesc is None:
                    return await self.async_step_confirm_mapping()
            else:
                unsupported_sn = []
                for product in selected_products:
                    if product.supportNetwork != '1':
                        unsupported_sn.append(product.sn)
                # device don't support cloud
                if unsupported_sn:
                    errorDesc = f"The following devices do not support Cloud control：{', '.join(unsupported_sn)}"


            # if not bluetooth/auto mode, create entry directly
            if errorDesc is None:
                return await self._create_config_entry(user_input, control_mode, {}, device_mapping)

        httpSession = async_get_clientsession(self.hass)
        access_token = self._oauth_data['token']['access_token']
        product_client = ProductClient(httpSession, access_token,self.hass)
        products = await product_client.get_user_products()
        # print(products)
        # print(products.data[0].__class__)
        # print(products.data)

        self._product_client = product_client
        self._products = products.data

        # get integrated devices list and existing control mode
        integrated_devices = set()
        existing_control_mode = ControlMode.CLOUD
        for entry in self.hass.config_entries.async_entries(DOMAIN):
            integrated_devices.update(entry.options.get("devices", []))
            # get existing control mode as default value
            if entry.options.get("control_mode"):
                existing_control_mode = entry.options.get("control_mode")

        # filter out devices that have already been integrated
        available_devices = {
            prod.sn: f"{prod.name} - {prod.sn}" + (f"-(Cloud)" if prod.supportNetwork == '1' else "") + (f"-(BLE)" if await is_device_support(prod.model) else "")
            for prod in products.data
            if prod.sn not in integrated_devices
        }

        # if no available devices, show error

        # 如果没有可用设备，显示错误
        if not products.data:
           return self.async_abort(reason="no_devices_available")

        # all devices are already integrated
        if not available_devices:
            return self.async_abort(reason="all_devices_exists")

        # get control mode options translation
        control_mode_options = await self._get_control_mode_options()

        schema = vol.Schema(
            {
                vol.Required(
                    "devices",
                    default=list((user_selected_device or available_devices).keys())
                ): cv.multi_select(available_devices),
                vol.Required(
                    "control_mode",
                    default=control_mode or existing_control_mode
                ): vol.In(control_mode_options)
            }
        )

        return self.async_show_form(
            step_id="select_devices",
            data_schema=schema,
            errors={"base": errorDesc} if errorDesc else None,
        )

    async def async_step_confirm_mapping(self, user_input=None):
        """confirm bluetooth device mapping relationship."""
        if user_input is not None:
            # user confirmed, create config entry
            pending_input = self._pending_user_input
            pending_mapping = self._pending_device_mapping
            control_mode = pending_input.get("control_mode", "cloud")

            ble_setting = user_input

            return await self._create_config_entry(
                pending_input, control_mode, ble_setting, pending_mapping
            )

            
            
        # show mapping relationship confirmation form
        pending_mapping = self._pending_device_mapping
        pending_products = self._pending_selected_products

        description = None
        if not pending_mapping:
            # no matching bluetooth devices
            device_names = [f"{p.name} (SN: {p.sn})" for p in pending_products]
            description = (
                f"No matching Bluetooth devices found\n\n"
                f"Selected devices:\n" + "\n".join([f"• {name}" for name in device_names]) +
                f"\n\nPossible reasons:\n"
                f"• Bluetooth device out of range\n"
                f"• Bluetooth device not enabled\n"
                f"• Device name mismatch\n\n"
                f"You can continue to create the configuration, manually configure the Bluetooth mapping later, or retry after ensuring the device is in range."
            )
        
        # config ble polling_interval 
        schema = vol.Schema({
            vol.Required('ble_polling_interval',default=10,): NumberSelector(
                NumberSelectorConfig(min=5,max=60,mode=NumberSelectorMode.BOX, step=1,)
            ),
            vol.Required('ble_polling_timeout',default=120,): NumberSelector(
                NumberSelectorConfig(min=60,max=180,mode=NumberSelectorMode.BOX, step=1,)
            ),
            vol.Required('ble_max_retries',default=5,): NumberSelector(
                NumberSelectorConfig(min=3,max=10,mode=NumberSelectorMode.BOX, step=1,)
            ),
        })

        return self.async_show_form(
            step_id="confirm_mapping",
            data_schema=schema,
            errors={"base": description} if description else None,
        )

    async def _create_config_entry(
        self,
        user_input: dict,
        control_mode: str,
        ble_setting: dict,
        device_mapping: dict
    ):
        """create or update config entry."""
        # set control_mode
        for device in self._products:
            if device.sn in user_input['devices']:
                device.control_mode = control_mode

        # check if there is an integrated entry with the same name
        deviceKeyDict = {}
        existing_entry = None
        for entry in self.hass.config_entries.async_entries(DOMAIN):
            if entry.title == f"{INTEGRATION_NAME} Power Integration":
                existing_entry = entry
                break

        if existing_entry:
            # merge into existing integrated entry
            existing_devices = existing_entry.options.get("devices", [])
            existing_products = existing_entry.data.get("products", [])
            existing_deviceKeyDict = existing_entry.options.get("deviceKeyDict", {})
            existing_device_mapping = existing_entry.options.get("device_mapping", {})
            existing_ble_setting = existing_entry.options.get("ble_setting", {})

            # merge device list (remove duplicates)
            merged_devices = list(set(existing_devices + user_input['devices']))

            # merge product data (remove duplicates)
            new_products = [p for p in self._products if p.sn in user_input['devices']]
            # convert to dict
            existing_products_dict = [p.__dict__.copy() if hasattr(p, '__dict__') else p for p in existing_products]
            new_products_dict = [p.__dict__.copy() if hasattr(p, '__dict__') else p for p in new_products]
            merged_products = list({item['sn']: item for item in existing_products_dict + new_products_dict}.values())


            # update existing entry
            self.hass.config_entries.async_update_entry(
                existing_entry,
                data={
                    "auth_implementation": self._oauth_data["auth_implementation"],
                    "token": self._oauth_data["token"],
                    "products": merged_products
                },
                options={
                    "devices": merged_devices,
                    "deviceKeyDict": existing_deviceKeyDict | deviceKeyDict,
                    "device_mapping": existing_device_mapping | device_mapping,
                    "ble_setting": existing_ble_setting | ble_setting
                }
            )

            # reload integrated entry to include new devices
            await self.hass.config_entries.async_reload(existing_entry.entry_id)

            return self.async_abort(reason="success")
        else:
            # create new integrated entry
            return self.async_create_entry(
                title=f"{INTEGRATION_NAME} Power Integration",
                data={
                    "auth_implementation": self._oauth_data["auth_implementation"],
                    "token": self._oauth_data["token"],
                    "products": self._products
                },
                options={
                    "devices": user_input["devices"],
                    "deviceKeyDict": deviceKeyDict,
                    "device_mapping": device_mapping,
                    "ble_setting": ble_setting
                },
            )

    async def async_step_reconfigure(self, user_input=None):
        """reauth configure"""
        self.entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        if not self.entry:
            return self.async_abort(reason="reconfigure_failed")

        return await self.async_step_user()


class AsyncConfigEntryAuth:
    """Provide BLUETTI authentication tied to an OAuth2 based config entry."""

    def __init__(
        self,
        websession: ClientSession,
        oauth_session: config_entry_oauth2_flow.OAuth2Session,
    ) -> None:
        """Initialize BLUETTI auth."""
        self._websession = websession
        self._oauth_session = oauth_session

    async def async_get_access_token(self) -> str:
        """Return a valid access token."""
        await self._oauth_session.async_ensure_token_valid()
        return self._oauth_session.token["access_token"]


class AuthTokenRefresh:
    """Handler Token expired and refresh token."""
    def __init__(self,hass:HomeAssistant,entry,oauth_session: config_entry_oauth2_flow.OAuth2Session)->None:
        self.hass = hass
        self.entry = entry
        self.oAuth2Session = oauth_session
        unsub = hass.bus.async_listen(EVENT_TOKEN_EXPIRED, self.on_token_expired_event)
        entry.async_on_unload(unsub)

    async def on_token_expired_event(self,event):
        __LOGGER__.info("on_token_expired_event")
        self.send_expired_notification()

    def start_token_check(self):
        # first clear old notify
        persistent_notification.async_dismiss(self.hass,notification_id=NOTIFY_ID_TOKEN_EXPIRED)
        if self.is_token_valid() == False:
            __LOGGER__.info("token have expired send notify")
            self.send_expired_notification()
        else:
            interval = timedelta(days=1)
            async_track_time_interval(
                self.hass,
                self.async_check_token_expiry,  # 要执行的任务函数
                interval       # 执行间隔
            )
            __LOGGER__.info("token is valid after 24 hours to check again")
        self.hass.async_create_task(self.async_check_token_expiry())
        

    # check oauth2 token is ok
    def is_token_valid(self) -> bool:
        """check token"""
        token = self.oAuth2Session.token
        if not token:
            return False
        
        if "expires_at" in token:
            expire_timestamp = cast(float, token["expires_at"]) - 30
            current_timestamp = time.time()
            return expire_timestamp > current_timestamp
        
        if "expires_in" in token and "created_at" in token:
            expire_timestamp = cast(float, token["created_at"]) + cast(float, token["expires_in"]) - 30
            current_timestamp = time.time()
            return expire_timestamp > current_timestamp
        
        return False

    # show token expire notify
    def send_expired_notification(self):
        reauth_url = f"/config/integrations/integration/{DOMAIN}"
        notification_message = (
            f"Your OAuth Have Expired！\n"
            f"Please go to the **[integration settings]({reauth_url})** page and click [Reconfigure] to complete the login."
        )
        persistent_notification.async_create(
            self.hass,
            notification_message,
            title = 'OAuth Expired',
            notification_id = NOTIFY_ID_TOKEN_EXPIRED,
        )

    # check token is in 7 day if in 7day refesh token
    async def async_check_token_expiry(self, now=None):
        __LOGGER__.info("check token is expired")
        expire_timestamp = cast(float, self.oAuth2Session.token["expires_at"])
        current_timestamp = time.time()
        remain_timestamp = expire_timestamp - current_timestamp
        if remain_timestamp < 0:
            self.send_expired_notification()
            return
        
        if remain_timestamp < 3600*24*7 :
            try:
                __LOGGER__.info('start refresh token')
                last_refesh = self.entry.data.get("last_token_refresh", 0.0)
                # 1 hour only one time ,when server is 500 do not always refesh token
                if current_timestamp - last_refesh < 3600 : 
                    __LOGGER__.info('last refesh token in 1 hour,this do not refesh return')
                    return
                last_refesh = current_timestamp

                new_token = await self.oAuth2Session.implementation.async_refresh_token(self.oAuth2Session.token)
                self.hass.config_entries.async_update_entry(
                    self.entry, data={**self.entry.data, "token": new_token,"last_token_refresh":last_refesh}
                )
                __LOGGER__.info('refresh token ok,then reload')
                await self.hass.config_entries.async_reload(self.entry.entry_id)
            except Exception as e:
                __LOGGER__.error(f"refresh token failed: {e}")