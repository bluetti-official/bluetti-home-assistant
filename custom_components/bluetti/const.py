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

# Some regions (notably Europe) can have their traffic geo-resolved to the
# BLUETTI US cloud nodes, which don't recognize tokens issued by the global
# nodes and repeatedly report the OAuth token as expired even though it is
# still valid (see issue #121). Registering a second OAuth2 implementation
# under this auth_domain lets users pick "US" on the login screen instead of
# editing files inside the integration, which would be wiped out on update.
AUTH_DOMAIN_US: str = f"{DOMAIN}_us"

class StringEnum(str, Enum):
    """String Enum define."""

    def __str__(self) -> str:
        return self.value


class Method(StringEnum):
    """HTTP Methods define."""

    GET = "GET"
    POST = "POST"
    DELETE = "DELETE"
