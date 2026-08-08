"""Constants for the BLUETTI integration."""
from enum import Enum

DOMAIN: str = "bluetti"
INTEGRATION_NAME: str = 'BLUETTI'

EVENT_TOKEN_EXPIRED: str ="onTokenExpired"
NOTIFY_ID_TOKEN_EXPIRED: str ="notifyTokenExpire"

class StringEnum(str, Enum):
    """String Enum define."""

    def __str__(self) -> str:
        return self.value


class Method(StringEnum):
    """HTTP Methods define."""

    GET = "GET"
    POST = "POST"
    DELETE = "DELETE"
