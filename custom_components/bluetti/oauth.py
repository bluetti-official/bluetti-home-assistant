import logging

import asyncio
from typing import cast
import time
from datetime import timedelta
from homeassistant.components import persistent_notification
from homeassistant.helpers.event import async_track_time_interval
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_entry_oauth2_flow
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from aiohttp import ClientSession

import voluptuous as vol

from .api.product_client import ProductClient
from .const import DOMAIN, INTEGRATION_NAME,EVENT_TOKEN_EXPIRED,NOTIFY_ID_TOKEN_EXPIRED

__LOGGER__ = logging.getLogger(__name__)


class OAuth2FlowHandler(config_entry_oauth2_flow.AbstractOAuth2FlowHandler, domain=DOMAIN):
    """BLUETTI OAUTH2 handler."""

    DOMAIN = DOMAIN
    reauth_supported = True

    @property
    def logger(self) -> logging.Logger:
        """Return logger."""
        return logging.getLogger(__name__)

    async def async_oauth_create_entry(self, data: dict) -> config_entries.ConfigFlowResult:
        """Handle OAuth2 callback and create config entry."""
        self._oauth_data = data
        return await self.async_step_select_devices()

    async def async_step_select_devices(self, user_input=None):
        """Let user select devices after OAuth2 login."""
        if user_input is not None:
            # print(user_input)
            await self._product_client.bind_devices({"bindSnList": user_input['devices']})
            
            # 检查是否存在同名的集成条目
            existing_entry = None
            for entry in self.hass.config_entries.async_entries(DOMAIN):
                if entry.title == f"{INTEGRATION_NAME} Power Integration":
                    existing_entry = entry
                    break
            
            if existing_entry:
                # 合并到现有集成条目
                existing_devices = existing_entry.options.get("devices", [])
                existing_products = existing_entry.data.get("products", [])
                
                # 合并设备列表（去重）
                merged_devices = list(set(existing_devices + user_input['devices']))
                
                # 合并产品数据（去重）
                existing_product_sns = {p.get('sn') if isinstance(p, dict) else p.sn for p in existing_products}
                new_products = [p for p in self._products if p.sn not in existing_product_sns]
                merged_products = existing_products + [p.__dict__ if hasattr(p, '__dict__') else p for p in new_products]
                
                # 更新现有条目
                self.hass.config_entries.async_update_entry(
                    existing_entry,
                    data={
                        "auth_implementation": self._oauth_data["auth_implementation"],
                        "token": self._oauth_data["token"],
                        "products": merged_products
                    },
                    options={"devices": merged_devices}
                )
                
                # 重新加载集成以包含新设备
                await self.hass.config_entries.async_reload(existing_entry.entry_id)
                
                return self.async_abort(reason="success")
            else:
                # 创建新的集成条目
                return self.async_create_entry(
                    title=f"{INTEGRATION_NAME} Power Integration",
                    data={
                        "auth_implementation": self._oauth_data["auth_implementation"],
                        "token": self._oauth_data["token"],
                        "products": self._products
                    },
                    options=user_input,
                )

        httpSession = async_get_clientsession(self.hass)
        access_token = self._oauth_data['token']['access_token']
        product_client = ProductClient(httpSession, access_token,self.hass)
        products = await product_client.get_user_products()
        # print(products)
        # print(products.data[0].__class__)
        # print(products.data)

        self._product_client = product_client
        self._products = products.data

        # 获取已集成的设备列表
        integrated_devices = set()
        for entry in self.hass.config_entries.async_entries(DOMAIN):
            integrated_devices.update(entry.options.get("devices", []))

        # 过滤掉已经集成过的设备
        available_devices = {
            prod.sn: f"{prod.name} - {prod.sn}"   
            for prod in products.data
            if prod.sn not in integrated_devices
        }


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

        # 如果没有可用设备，显示错误
        if not products.data:
            return self.async_abort(reason="no_devices_available")
        
        # 已全部集成
        if not available_devices:
            return self.async_abort(reason="all_devices_exists")

        schema = vol.Schema(
            {
                vol.Required(
                    "devices",
                    default=list(available_devices.keys())
                ): cv.multi_select(available_devices)
            }
        )

        return self.async_show_form(
            step_id="select_devices",
            data_schema=schema,
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
    async def async_check_token_expiry(self):
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