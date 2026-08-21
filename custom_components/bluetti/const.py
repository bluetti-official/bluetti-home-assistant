"""Constants for the BLUETTI integration."""
from enum import Enum

DOMAIN: str = "bluetti"
INTEGRATION_NAME: str = 'BLUETTI'

EVENT_TOKEN_EXPIRED: str ="onTokenExpired"
NOTIFY_ID_TOKEN_EXPIRED: str ="notifyTokenExpire"

# The BLUETTI cloud API does not expose a stable per-account identifier, and
# this integration is designed around a single config entry that accumulates
# every device bound to whichever BLUETTI account the user authenticates
# with. This fixed unique_id lets the config flow use Home Assistant's
# standard duplicate-prevention mechanism instead of matching on the entry
# title.
ACCOUNT_UNIQUE_ID: str = "account"

class StringEnum(str, Enum):
    """String Enum define."""

    def __str__(self) -> str:
        return self.value


class Method(StringEnum):
    """HTTP Methods define."""

    GET = "GET"
    POST = "POST"
    DELETE = "DELETE"
