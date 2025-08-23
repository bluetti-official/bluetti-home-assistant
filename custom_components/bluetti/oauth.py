import logging

from homeassistant import config_entries
from homeassistant.helpers.config_entry_oauth2_flow import AbstractOAuth2FlowHandler

from .const import DOMAIN, INTEGRATION_NAME


class OAuth2FlowHandler(AbstractOAuth2FlowHandler, domain=DOMAIN):
    """BLUETTI OAUTH2 handler."""

    DOMAIN = DOMAIN

    @property
    def logger(self) -> logging.Logger:
        """Return logger."""
        return logging.getLogger(__name__)

    async def async_oauth_create_entry(self, data: dict) -> config_entries.ConfigFlowResult:
        return self.async_create_entry(title=f"{INTEGRATION_NAME} Power Integration", data=data)