import json
import logging

from abc import ABC
from asyncio import run_coroutine_threadsafe
from aiohttp import ClientSession

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_entry_oauth2_flow
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession

import voluptuous as vol

from .api.product_client import ProductClient
from .const import DOMAIN, INTEGRATION_NAME

__LOGGER__ = logging.getLogger(__name__)


class OAuth2FlowHandler(config_entry_oauth2_flow.AbstractOAuth2FlowHandler, domain=DOMAIN):
    """BLUETTI OAUTH2 handler."""

    DOMAIN = DOMAIN

    @property
    def logger(self) -> logging.Logger:
        """Return logger."""
        return logging.getLogger(__name__)

    async def async_oauth_create_entry(self, data: dict) -> config_entries.ConfigFlowResult:
        # return self.async_create_entry(title=f"{INTEGRATION_NAME} Power Integration", data=data)
        self._oauth_data = data
        return await self.async_step_select_devices()

    async def async_step_select_devices(self, user_input=None):
        """Let user select devices after OAuth2 login."""
        if user_input is not None:
            print(user_input)
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
                    data={"auth_token": self._oauth_data, "products": merged_products},
                    options={"devices": merged_devices}
                )
                
                # 重新加载集成以包含新设备
                await self.hass.config_entries.async_reload(existing_entry.entry_id)
                
                return self.async_abort(reason="success")
            else:
                # 创建新的集成条目
                return self.async_create_entry(
                    title=f"{INTEGRATION_NAME} Power Integration",
                    data={"auth_token": self._oauth_data, "products":  self._products},
                    options=user_input,
                )

        httpSession = async_get_clientsession(self.hass)
        product_client = ProductClient(httpSession, self._oauth_data['token']['access_token'])
        products = await product_client.get_user_products()
        print(products)
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
            prod.sn: prod.name or prod.sn 
            for prod in products.data 
            if prod.sn not in integrated_devices
        }

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

# TODO the following two API examples are based on our suggested best practices
# for libraries using OAuth2 with requests or aiohttp. Delete the one you won't use.
# For more info see the docs at https://developers.home-assistant.io/docs/api_lib_auth/#oauth2.
class AbstractAuth(ABC):
    def __init__(self, token):
        """Initialize the auth."""
        self.token = token
        # print(type(token))
        __LOGGER__.debug(json.dumps(token, indent=4, ensure_ascii=False))

    # @abstractmethod
    async def async_get_access_token(self) -> str:
        """Return a valid access token."""
        print(self)
        return self.token["access_token"]


class ConfigEntryAuth(AbstractAuth):
    """Provide BLUETTI authentication tied to an OAuth2 based config entry."""

    def __init__(
        self,
        hass: HomeAssistant,
        oauth_session: config_entry_oauth2_flow.OAuth2Session,
    ) -> None:
        """Initialize BLUETTI Auth."""
        self.hass = hass
        self.session = oauth_session
        super().__init__(self.session.token)

    def refresh_tokens(self) -> str:
        """Refresh and return new BLUETTI tokens using Home Assistant OAuth2 session."""
        run_coroutine_threadsafe(
            self.session.async_ensure_token_valid(), self.hass.loop
        ).result()

        return self.session.token["access_token"]


class AsyncConfigEntryAuth(AbstractAuth):
    """Provide BLUETTI authentication tied to an OAuth2 based config entry."""

    def __init__(
        self,
        websession: ClientSession,
        oauth_session: config_entry_oauth2_flow.OAuth2Session,
    ) -> None:
        """Initialize BLUETTI auth."""
        super().__init__(websession)
        self._oauth_session = oauth_session

    async def async_get_access_token(self) -> str:
        """Return a valid access token."""
        await self._oauth_session.async_ensure_token_valid()

        return self._oauth_session.token["access_token"]