from __future__ import annotations
from typing import Callable, Optional, List
import asyncio
import random
import json
import logging

from homeassistant.util import Throttle, dt
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.components import persistent_notification
from datetime import timedelta
from .const import DOMAIN

__LOGGER__ = logging.getLogger(__name__)

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
            # print(f'开始调用api获取设备状态: {sn}')
            asyncio.run_coroutine_threadsafe(device.async_update(), self.loop)

class BluettiState:
    """Represents a single function/state of the device."""

    def __init__(self, fn_code: str, fn_name: str, fn_value: str, fn_type: str, support_mode_values: Optional[List[dict]] = None, sensor_info:dict=None):
        self.fn_code = fn_code
        self.fn_name = fn_name
        self.fn_value = fn_value
        self.fn_type = fn_type
        self.support_mode_values = support_mode_values or []
        self.sensor_info = sensor_info or {}

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

    def __init__(self, device_id: str, on_line: str, name: str, sn: str, model: str, state_list: Optional[List[dict]] = None):
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
                fn_type=s.get("fnType"),
                support_mode_values=s.get("supportModeValues"),
                sensor_info = s.get("sensorInfo")
            )
            for s in state_list or []
        ]

        self._api_client = None
        self._unbind_processed = False
        self._hass = None
        self._entry = None
        self._entry_id = None
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
        # print(len(self._callbacks))

    def remove_callback(self, callback: Callable[[], None]):
        self._callbacks.discard(callback)

    async def publish_updates(self):
        """Call registered callbacks."""
        # print(len(self._callbacks))
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
        return 0

    @property
    def battery_voltage(self) -> float:
        # TODO
        return round(random.random() * 3 + 10, 2)

    @property
    def illuminance(self) -> int:
        # TODO
        return random.randint(0, 500)

    @property
    def throttle(self):
        return self._t

    @property
    def schedule_state(self):
        return self._schedule_state

    async def _async_update(self):
        api_client = self._api_client

        device_status = await api_client.get_device_status(self.device_id)
        # print(device_status.data[0])
        data = device_status.data[0]

        # print(f'device_status: {data}')

        sn = data.sn
        if sn != self.device_id:
            return
        
        if data.isBindByCurUser == '0':
            # unbind device
            if not self._unbind_processed:
                await self._handle_unbind()
            

        self.on_line = data.online

        new_states = data.stateList

        for s in new_states:
            state_obj = self.get_state(s["fnCode"])
            if state_obj:
                state_obj.fn_value = s["fnValue"]

        await self.publish_updates()

    async def _handle_unbind(self):
        """Handle device unbinding: Clean up the device, entity, and configuration, and display the notification."""
        self._unbind_processed = True
        
        __LOGGER__.info(f"Detected device unbinding: {self.name} ({self.device_id})")
        
        # Check if the necessary references exist
        if not self._hass or not self._entry:
            __LOGGER__.error(f"Cannot handle device unbinding: Missing necessary references (hass={self._hass is not None}, entry={self._entry is not None})")
            return
        
        hass = self._hass
        entry = self._entry
        entry_id = self._entry_id or entry.entry_id
        
        try:
            __LOGGER__.info(f"Start handling device unbinding: {self.device_id}")
            
            # 1. Get the device registry and entity registry
            device_registry = dr.async_get(hass)
            entity_registry = er.async_get(hass)
            
            # 2. Find and delete all entities of the device
            device_entry = None
            for dev_entry in dr.async_entries_for_config_entry(device_registry, entry_id):
                if (DOMAIN, self.device_id) in dev_entry.identifiers:
                    device_entry = dev_entry
                    break
            
            if device_entry:
                # Delete all entities of the device
                entities_to_remove = []
                for entity_entry in er.async_entries_for_config_entry(entity_registry, entry_id):
                    if entity_entry.device_id == device_entry.id:
                        entities_to_remove.append(entity_entry.entity_id)
                
                for entity_id in entities_to_remove:
                    try:
                        entity_registry.async_remove(entity_id)
                        __LOGGER__.debug(f"Deleted entity: {entity_id}")
                    except Exception as e:
                        __LOGGER__.warning(f"Error deleting entity {entity_id}: {e}")
                
                # 3. Delete the device registry
                try:
                    device_registry.async_remove_device(device_entry.id)
                    __LOGGER__.debug(f"Deleted device registry: {device_entry.id}")
                except Exception as e:
                    __LOGGER__.warning(f"Error deleting device registry: {e}")
            else:
                __LOGGER__.warning(f"Device registry not found: {self.device_id}")
            
            # 4. Clean up the bluetooth connection (if exists)
            # if hasattr(self, '_bt_coordinator') and self._bt_coordinator:
            #     try:
            #         if hasattr(self._bt_coordinator, 'reader') and self._bt_coordinator.reader:
            #             reader = self._bt_coordinator.reader
            #             if hasattr(reader, 'client') and reader.client and reader.client.is_connected:
            #                 await reader.client.disconnect()
            #                 __LOGGER__.debug(f"已断开蓝牙连接: {self.device_id}")
            #     except Exception as e:
            #         __LOGGER__.warning(f"断开蓝牙连接时出错: {e}")
            
            # 5. Remove the device from the runtime data
            try:
                domain_data = hass.data.get(DOMAIN, {})
                entry_data = domain_data.get(entry_id)
                if entry_data and "bluettiDevices" in entry_data:
                    bluetti_data = entry_data["bluettiDevices"]
                    if hasattr(bluetti_data, 'devices'):
                        bluetti_data.devices = [
                            d for d in bluetti_data.devices 
                            if d.device_id != self.device_id
                        ]
                        __LOGGER__.debug(f"Removed device from runtime data: {self.device_id}")
            except Exception as e:
                __LOGGER__.warning(f"Error removing device from runtime data: {e}")
            
            # 6. Remove the device from the configuration entry
            try:
                current_options = dict(entry.options)
                current_devices = current_options.get("devices", [])
                
                if self.device_id in current_devices:
                    new_devices = [d for d in current_devices if d != self.device_id]
                    
                    hass.config_entries.async_update_entry(
                        entry,
                        options={**current_options, "devices": new_devices}
                    )
                    __LOGGER__.debug(f"Removed device from configuration entry: {self.device_id}")
                else:
                    __LOGGER__.warning(f"Device {self.device_id} not in the device list of the configuration entry")
            except Exception as e:
                __LOGGER__.error(f"Error updating configuration entry: {e}", exc_info=True)
                # Even if the update fails, continue to display the notification
            
            # 7. Display persistent notification
            try:
                notification_id = f"bluetti_unbind_{self.device_id}"
                notification_title = "BLUETTI device has been unbound"
                notification_message = (
                    f"Device **{self.name}** ({self.device_id}) has been unbound in the cloud, "
                    f"and has been automatically removed from the Home Assistant integration.\n\n"
                    f"If this is a mistake, please re-add the device."
                )
                
                persistent_notification.create(
                    hass,
                    title=notification_title,
                    message=notification_message,
                    notification_id=notification_id
                )
                __LOGGER__.debug(f"Displayed unbinding notification: {self.device_id}")
            except Exception as e:
                __LOGGER__.warning(f"Error displaying notification: {e}")
            
            # 8. Reload the configuration entry after a delay (ensure all cleanup operations are completed)
            async def _reload_after_cleanup():
                try:
                    await asyncio.sleep(1)  # Delay 1 second to ensure all cleanup operations are completed
                    await hass.config_entries.async_reload(entry_id)
                    __LOGGER__.info(f"Reloaded configuration entry: {entry_id}")
                except Exception as e:
                    __LOGGER__.error(f"Error reloading configuration entry: {e}", exc_info=True)
            
            hass.async_create_task(_reload_after_cleanup())
            
            __LOGGER__.info(f"Device unbinding processing completed: {self.device_id}")
            
        except Exception as e:
            __LOGGER__.error(f"Error handling device unbinding: {e}", exc_info=True)
