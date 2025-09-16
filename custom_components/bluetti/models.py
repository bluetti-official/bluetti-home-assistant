from __future__ import annotations
from typing import Callable, Optional, List
import asyncio
import random
import json

from homeassistant.util import Throttle, dt
from datetime import timedelta
from .const import DOMAIN

manufacturer = "Bluetti"

class BluettiData:
    """Data for the BLUETTI integration."""

    def __init__(self, hass, devices: Optional[List[dict]] = None):
        self.devices = [
            BluettiDevice(
                device_id=dev.sn,
                on_line=dev.online or '0',
                name=dev.name,
                sn=dev.sn,
                model=dev.model,
                state_list=dev.stateList or []
            )
            for dev in devices or []
        ]
        self.loop = hass.loop

    async def test_connection(self) -> bool:
        """Test connectivity to devices."""
        await asyncio.sleep(0.1)
        return True

    def get_device_by_sn(self, sn):
       for dev in self.devices:
        print(f"device_id= {dev.device_id}, sn= {sn}")
        if dev.device_id == sn:
            return dev
        return None

    def web_socket_message_handler(self, message: str):
        print(f"收到ws消息 {message}")

        res = json.loads(message)
        # load api
        sn = res["data"]["deviceSn"]

        device = self.get_device_by_sn(sn)
        if device:
            print(f'开始调用api获取设备状态: {sn}')
            asyncio.run_coroutine_threadsafe(device.async_update(), self.loop)

class BluettiState:
    """Represents a single function/state of the device."""

    def __init__(self, fn_code: str, fn_name: str, fn_value: str, support_mode_values: Optional[List[dict]] = None):
        self.fn_code = fn_code
        self.fn_name = fn_name
        self.fn_value = fn_value
        self.support_mode_values = support_mode_values or []

    def is_switch(self) -> bool:
        return len(self.support_mode_values) == 0

    def set_value(self, value: str):
        """Set the state value, validate if mode selection."""
        if self.is_switch() or any(v["code"] == value for v in self.support_mode_values):
            self.fn_value = value
        else:
            raise ValueError(f"Invalid value {value} for {self.fn_code}")

    def get_name_for_value(self) -> str:
        """Return human-readable name for current value."""
        if self.is_switch():
            return "On" if self.fn_value == "1" else "Off"
        for v in self.support_mode_values:
            if v["code"] == self.fn_value:
                return v["name"]
        return self.fn_value

    def __repr__(self):
        return f"<BluettiState {self.fn_code}={self.fn_value}>"


class BluettiDevice:
    """Represents a single Bluetti device."""

    def __init__(self, device_id: str, on_line: str, name: str, sn: str, model: str, state_list: Optional[List[dict]] = None, api_client=None):
        self.device_id = device_id
        self.on_line = on_line
        self.name = name
        self.sn = sn
        self.model = model
        self.manufacturer = manufacturer
        self._callbacks: set[Callable[[], None]] = set()
        self._loop = asyncio.get_event_loop()
        self.states = [
            BluettiState(
                fn_code=s.get("fnCode"),
                fn_name=s.get("fnName") or "",
                fn_value=s.get("fnValue"),
                support_mode_values=s.get("supportModeValues")
            )
            for s in state_list or []
        ]

        self._api_client = api_client
        # self._ws_manager = ws_manager

        # 创建一个定时任务轮询获取设备状态
        self.async_update = Throttle(timedelta(microseconds=1))(self._async_update)

    def __repr__(self):
        return f"<BluettiDevice id={self.device_id} name={self.name}>"

    def get_state(self, fn_code: str) -> Optional[BluettiState]:
        # print('poll get device status')
        """Return state object by fn_code."""
        for s in self.states:
            if s.fn_code == fn_code:
                return s
        return None

    async def set_state_value(self, fn_code: str, value: str):
        """Set a state value and notify callbacks."""
        state = self.get_state(fn_code)
        if not state:
            raise ValueError(f"No state with code {fn_code}")

        try:
            # TODO websocket
            # ws_manager = self._ws_manager # 需要在初始化时传入
            #
            # payload = {
            #     "action": "set", #
            #     "sn": self.sn,
            #     "fnCode": fn_code,
            #     "value": value
            # }
            # await ws_manager.send_message(payload)
            #
            # # 假设服务器会通过 WebSocket 返回确认或状态更新
            # state.set_value(value)

            # print({'sn': self.device_id, 'fnCode': fn_code, 'fnValue': value})

            api_client = self._api_client
            result = await api_client.control_device({'sn': self.device_id, 'fnCode': fn_code, 'fnValue': value})

            # print(result)
            if result.msgCode == 0:
                state.set_value(value)

        except Exception as e:
            raise Exception(f"Error sending WebSocket command: {e}")

        # state.set_value(value)
        await self.publish_updates()

    def register_callback(self, callback: Callable[[], None]):
        self._callbacks.add(callback)
        print(len(self._callbacks))

    def remove_callback(self, callback: Callable[[], None]):
        self._callbacks.discard(callback)

    async def publish_updates(self):
        """Call registered callbacks."""
        print(len(self._callbacks))
        for cb in self._callbacks:
            cb()

    @property
    def online(self) -> bool:
        return self.on_line == '1'

    @property
    def battery_level(self) -> int:
        state = self.get_state("SOC")
        if state:
            return int(state.fn_value)
        return random.randint(0, 100)

    @property
    def battery_voltage(self) -> float:
        # TODO
        return round(random.random() * 3 + 10, 2)

    @property
    def illuminance(self) -> int:
        # TODO
        return random.randint(0, 500)

    # TODO 后期删掉
    @property
    def throttle(self):
        return self._t

    # TODO 后期删掉
    @property
    def schedule_state(self):
        return self._schedule_state

    async def _async_update(self):
        api_client = self._api_client

        device_status = await api_client.get_device_status(self.device_id)
        # print(device_status.data[0])
        data = device_status.data[0]

        print(f'device_status: {data}')

        sn = data.sn
        if sn != self.device_id:
            return

        self.on_line = data.online

        new_states = data.stateList

        for s in new_states:
            state_obj = self.get_state(s["fnCode"])
            if state_obj:
                state_obj.fn_value = s["fnValue"]

        await self.publish_updates()
