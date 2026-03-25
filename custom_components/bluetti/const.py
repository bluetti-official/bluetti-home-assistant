"""Constants for the BLUETTI integration."""
from enum import Enum

DOMAIN: str = "bluetti"
INTEGRATION_NAME: str = 'BLUETTI'

EVENT_TOKEN_EXPIRED: str ="onTokenExpired"
NOTIFY_ID_TOKEN_EXPIRED: str ="notifyTokenExpire"

# TODO Update with your own urls
BLUETTI_WSS_SERVER: str = "ws://local-gw.poweroak.ltd:18888/api/edgeiotgw/ws-coordination/websocket"

class StringEnum(str, Enum):
    """String Enum define."""

    def __str__(self) -> str:
        return self.value


class Method(StringEnum):
    """HTTP Methods define."""

    GET = "GET"
    POST = "POST"
    DELETE = "DELETE"
