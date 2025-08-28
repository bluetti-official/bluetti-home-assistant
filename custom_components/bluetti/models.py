from __future__ import annotations
from typing import Callable, Optional, List
import asyncio
import time
import random

manufacturer = "Bluetti"

class BluettiData:
    """Data for the BLUETTI integration."""

    def __init__(self, devices: Optional[List[dict]] = None):
        self.devices = [
            BluettiDevice(
                device_id=dev.sn,
                name=dev.name,
                sn=dev.sn,
                state_list=dev.stateList or []
            )
            for dev in devices or []
        ]
        self.online = True

    async def test_connection(self) -> bool:
        """Test connectivity to devices."""
        await asyncio.sleep(0.1)
        return True

    def get_device_by_sn(self, sn):
        return self.devices


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

    def __init__(self, device_id: str, name: str, sn: str, state_list: Optional[List[dict]] = None):
        self.device_id = device_id
        self.name = name
        self.sn = sn
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

    def __repr__(self):
        return f"<BluettiDevice id={self.device_id} name={self.name}>"

    def get_state(self, fn_code: str) -> Optional[BluettiState]:
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
        state.set_value(value)
        await self.publish_updates()

    def register_callback(self, callback: Callable[[], None]):
        self._callbacks.add(callback)

    def remove_callback(self, callback: Callable[[], None]):
        self._callbacks.discard(callback)

    async def publish_updates(self):
        """Call registered callbacks."""
        for cb in self._callbacks:
            cb()

    @property
    def online(self) -> bool:
        # TODO
        return random.random() > 0.1

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
