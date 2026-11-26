"""Constants for the BLUETTI integration."""
from enum import Enum

DOMAIN: str = "bluetti"
INTEGRATION_NAME: str = 'BLUETTI'
DOWNDIR: str = "downloads"
DOWNDIR_DATA_KEY: str = "download_dir"

# Cloud gateway per region, chosen in the integration options. "default" keeps
# the gateway from profile/application.yaml. Accounts registered in Europe may
# need the EU gateway: the default one can fail there (#72, #81), including a
# 404 on the BLE proto file download.
CONF_GATEWAY_REGION: str = "gateway_region"
GATEWAY_REGION_DEFAULT: str = "default"
GATEWAY_REGIONS: dict[str, str] = {
    "global": "https://gw.bluettipower.com",
    "europe": "https://gwde.bluettipower.com",
}

EVENT_BLUETTI_SETUP_OK: str ="onBluettiSetup"

EVENT_TOKEN_EXPIRED: str ="onTokenExpired"
NOTIFY_ID_TOKEN_EXPIRED: str ="notifyTokenExpire"
# Cloud msgCodes meaning the access token is no longer accepted.
# 805 = expired; 800 = "访问令牌已过期" (token revoked early by the backend).
TOKEN_REJECTED_CODES: frozenset[int] = frozenset({800, 805})

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


class AppPath(StringEnum):
    """App Path define."""

    SMART_HOME_API = "/api/bluiotdata"
    DECODE_CENTER_API = "/api/bluiotcodec"

class ControlMode(StringEnum):
    """Control Mode define."""

    CLOUD = "cloud"
    BLE = "bluetooth"
