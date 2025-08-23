"""Copyright (C) 2025 BLUETTI Corporation."""

import logging

from homeassistant.helpers import config_entry_oauth2_flow

from .const import DOMAIN


class BluettiConfigFlow(config_entry_oauth2_flow.AbstractOAuth2FlowHandler, domain=DOMAIN):
    """BLUETTI Custom Integration config flow."""

    DOMAIN = DOMAIN

    @property
    def logger(self) -> logging.Logger:
        """Return logger."""
        return logging.getLogger(__name__)
