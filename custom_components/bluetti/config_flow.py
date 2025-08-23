"""Copyright (C) 2025 BLUETTI Corporation."""

from .const import DOMAIN
from .oauth import OAuth2FlowHandler


class BluettiConfigFlow(OAuth2FlowHandler, domain=DOMAIN):
    """BLUETTI Custom Integration config flow."""
