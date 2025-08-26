"""BLUETTI Cloud API for Python."""
import aiohttp
import logging

from abc import abstractmethod
from json import dumps, loads
from typing import Any

from .unify_response import UnifyResponse
from ..application_exception import ApplicationRuntimeException
from ..const import BLUETTI_GATEWAY_SERVER, Method


class Bluetti[T]:
    """Base class describing interactions with BLUETTI cloud service."""
    _accessToken: str | None = None
    _headers: dict[str, str]
    _httpSession: aiohttp.ClientSession

    @property
    @abstractmethod
    def logger(self) -> logging.Logger:
        """The subclass's logger."""

    def __init__(
            self,
            httpSession: aiohttp.ClientSession,
            accessToken: str | None = None
    ):
        self._httpSession = httpSession
        self._accessToken = accessToken

    async def _request(
            self,
            method: Method,
            path: str,
            params: dict[str, Any] | None = None,
            body: dict[str, Any] | None = {}
    ) -> UnifyResponse[T] | str:
        """Send a request to the server."""

        # when the method is 'GET', the request body must be null.
        if method == Method.GET:
            body = None

        # prepare the request header.
        headers = {
            "Authorization": f"{self._accessToken}",
        }

        # Remove None values from params and json
        if params:
            params = {k: v for k, v in params.items() if v is not None}
            self.logger.debug("Client request parameters: %s", params)
        if body:
            body = {k: v for k, v in body.items() if v is not None}
            self.logger.debug("Client request body: %s", dumps(body))
            headers["Content-Type"] = "application/json"

        async with self._httpSession.request(
                method,
                f"{BLUETTI_GATEWAY_SERVER}{path}",
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
                # self.logger.debug("<====== Server response body: %s", dumps(data, indent=4, ensure_ascii=False))
                # unify_response: UnifyResponse[T] = UnifyResponse(**data)
                # return unify_response

                unify_response: UnifyResponse[T] = UnifyResponse(data["msgId"], data["msgCode"])
                unify_response.data = data["data"]
                return unify_response
            else:
                data = await response.text()
                # self.logger.debug("<====== Server response body: %s", data)
                return data
