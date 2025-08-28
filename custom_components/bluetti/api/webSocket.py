import asyncio
import json
import websocket
from ..models import BluettiData
from ..const import BLUETTI_WSS_SERVER

class BluettiWebSocket:
    """Manage websocket connection to Bluetti devices."""

    def __init__(self, bluetti_data: BluettiData, url: str = BLUETTI_WSS_SERVER):
        self._bluetti_data = bluetti_data
        self._url = url
        self._ws = None
        self._task = None

    async def connect(self):
        """Start websocket listener."""
        self._task = asyncio.create_task(self._listen())

    async def _listen(self):
        async for ws in websockets.connect(self._url):
            self._ws = ws
            try:
                await self._subscribe_devices()
                async for message in ws:
                    await self._handle_message(message)
            except websockets.ConnectionClosed:
                print("WebSocket closed, retrying in 5s...")
                await asyncio.sleep(5)

    # TODO
    async def _subscribe_devices(self):
        """Send subscribe request for device SNs."""
        sns = [dev.sn for dev in self._bluetti_data.devices]
        payload = {
            "action": "subscribe",
            "sns": sns
        }
        await self._ws.send(json.dumps(payload))

    # TODO
    async def _handle_message(self, message: str):
        """Handle incoming websocket message."""
        data = json.loads(message)
        sn = data.get("sn")
        states = data.get("stateList", [])
        device = self._bluetti_data.get_device_by_sn(sn)
        if not device:
            return
        for s in states:
            state_obj = device.get_state(s["fnCode"])
            if state_obj:
                state_obj.fn_value = s["fnValue"]
        await device.publish_updates()