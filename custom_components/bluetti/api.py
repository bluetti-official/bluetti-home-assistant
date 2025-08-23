"""API for BLUETTI bound to Home Assistant OAuth."""
import json
import logging

from abc import ABC, abstractmethod
from asyncio import run_coroutine_threadsafe

from aiohttp import ClientSession
# import my_pypi_package

from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_entry_oauth2_flow

_LOGGER = logging.getLogger(__name__)

# TODO the following two API examples are based on our suggested best practices
# for libraries using OAuth2 with requests or aiohttp. Delete the one you won't use.
# For more info see the docs at https://developers.home-assistant.io/docs/api_lib_auth/#oauth2.


class AbstractAuth(ABC):
    def __init__(self, token):
        """Initialize the auth."""
        self.token = token
        # print(type(token))
        _LOGGER.debug(json.dumps(token, indent=4, ensure_ascii=False))

    # @abstractmethod
    async def async_get_access_token(self) -> str:
        """Return a valid access token."""
        print(self)
        return self.token["access_token"]


# class ConfigEntryAuth(my_pypi_package.AbstractAuth):
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


# class AsyncConfigEntryAuth(my_pypi_package.AbstractAuth):
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
