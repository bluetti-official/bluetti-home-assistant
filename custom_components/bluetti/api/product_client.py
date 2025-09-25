import logging

import aiohttp

from .bluetti import Bluetti
from .unify_response import UnifyResponse
from ..const import Method
from ..model.product import UserProduct


class ProductClient(Bluetti):
    """Class describing for the BLUETTI products."""

    __LOGGER__ = None
    """The api client logger."""

    def __init__(self, httpSession: aiohttp.ClientSession, accessToken):
        super().__init__(httpSession, accessToken)

    @property
    def logger(self) -> logging.Logger:
        """
        Get the api client logger.
        定义API客户端的日志记录器
        """
        if self.__LOGGER__ is None:
            self.__LOGGER__ = logging.getLogger(__name__ + "." + __class__.__name__)
        return self.__LOGGER__

    async def get_user_products(self) -> UnifyResponse[list[UserProduct]]:
        """
        Get user belongs power stations/devices by send an api request.
        请求接口，获取用户所属的发电站/设备信息。
        """
        return await self._request(
            list[UserProduct],
            Method.GET,
            "/api/bluiotdata/ha/v1/devices",
        )

    async def get_device_status(self, sns: str = None) -> UnifyResponse[list[UserProduct]]:
        """
        轮询获取设备状态
        """
        return await self._request(
            list[UserProduct],
            Method.GET,
            "/api/bluiotdata/ha/v1/deviceStates",
            params={'sns': sns}
        )

    async def control_device(self, payload: str = None):
        """
        控制设备
        """
        return await self._request(
            dict,
            method=Method.POST,
            path="/api/bluiotdata/ha/v1/fulfillment",
            body=payload
        )
    async def bind_devices(self, payload: str = None):
        """
        bind devices
        """
        return await self._request(
            dict,
            method=Method.POST,
            path="/api/bluiotdata/ha/v1/bindDevices",
            body=payload
        )