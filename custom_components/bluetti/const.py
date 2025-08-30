"""Constants for the BLUETTI integration."""
from enum import Enum

DOMAIN: str = "bluetti"
INTEGRATION_NAME: str = 'BLUETTI'

# TODO Update with your own urls
BLUETTI_WSS_SERVER: str = "wss://"

class StringEnum(str, Enum):
    """String Enum define."""

    def __str__(self) -> str:
        return self.value


class Method(StringEnum):
    """HTTP Methods define."""

    GET = "GET"
    POST = "POST"
    DELETE = "DELETE"
