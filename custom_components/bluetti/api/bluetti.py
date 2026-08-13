"""BLUETTI Cloud API for Python."""
import aiohttp
import logging

from abc import abstractmethod
from json import dumps, loads
from typing import Any, TypeVar, Generic

from pydantic import TypeAdapter
from homeassistant.core import HomeAssistant

from .unify_response import UnifyResponse
from ..const import Method,EVENT_TOKEN_EXPIRED
from ..application_exception import ApplicationRuntimeException
from ..profile.application_profile import ApplicationProfile

T = TypeVar('T')

# The application profile (global/default region).
APPLICATION_PROFILE = ApplicationProfile()

# The US region profile, used when the account was authenticated against
# the US OAuth implementation (see const.AUTH_DOMAIN_US and issue #121).
US_APPLICATION_PROFILE = ApplicationProfile(active="us")


class Bluetti(Generic[T]):
    """Base class describing interactions with BLUETTI cloud service."""
    _accessToken: str | None = None
    _headers: dict[str, str]
    _httpSession: aiohttp.ClientSession
    _hass: HomeAssistant

    @property
    @abstractmethod
    def logger(self) -> logging.Logger:
        """The subclass's logger."""

    def __init__(
            self,
            httpSession: aiohttp.ClientSession,
            accessToken: str | None = None,
            hass: HomeAssistant | None = None,
            gateway_url: str | None = None,
    ):
        self._httpSession = httpSession
        self._accessToken = accessToken
        self._hass = hass
        # Falls back to the global/default profile's gateway when not given
        # a region-specific one explicitly (e.g. in existing call sites).
        self._gateway_url = gateway_url

    async def _request(
            self,
            responseType: Any,
            method: Method,
            path: str,
            params: dict[str, Any] | None = None,
            body: dict[str, Any] | None = None
    ) -> UnifyResponse[T] | str:
        """
        Send a request to the server.\n
        - **responseType**: The type of response data type, do not include wrapper class `UnifyResponse`.
        - **method**: The HTTP method.
        """

        # when the method is 'GET', the request body must be null.
        if method == Method.GET:
            body = None

        headers = {
            "Authorization": f"{self._accessToken}",
        }

        # Remove None values from params and json
        if params:
            params = {k: v for k, v in params.items() if v is not None}
            self.logger.debug("======> Client request parameters: %s", params)
        if body:
            body = {k: v for k, v in body.items() if v is not None}
            self.logger.debug("======> Client request body: %s", dumps(body))
            headers["Content-Type"] = "application/json"

        gateway_url = self._gateway_url or APPLICATION_PROFILE.config["server"]["gateway"]
        async with self._httpSession.request(
                method,
                f"{gateway_url}{path}",
                headers=headers,
                json=body,
                params=params,
        ) as response:
            self.logger.debug("<====== Server response status %s from %s", response.status, response.url)
            self.logger.debug("<====== Server response type is: %s", response.content_type)

            if not response.ok:
                # await raise_for_status(resp)
                raise ApplicationRuntimeException(msgCode=response.status, data=await response.text())

            # if not response.content_type.lower().startswith("application/json"):
            #     raise ApplicationRuntimeException(msgCode=response.status, data=await response.text())

            if response.content_type.lower().startswith("application/json"):
                data = await response.json()  # read response body to JSON
                unify_response = TypeAdapter(UnifyResponse[responseType]).validate_python(data)
                # self.logger.debug("<====== Server response body: %s", dumps(data, indent=4, ensure_ascii=False))
                # print(repr(unify_response))
                if data.get('msgCode') == 805:
                    self._hass.bus.fire(EVENT_TOKEN_EXPIRED)
                    self.logger.info("token have expired")
                return unify_response
            else:
                data = await response.text()
                # self.logger.debug("<====== Server response body: %s", data)
                return data
