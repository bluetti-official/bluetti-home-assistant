from __future__ import annotations
from typing import Callable, Optional, List
import asyncio
import time
import os
import random
import json
import logging

from .api.bluetti import APPLICATION_PROFILE
from .model.product import UserProduct
from homeassistant.util import Throttle, dt
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.components import persistent_notification
from homeassistant.core import HomeAssistant
from datetime import timedelta
from .const import DOMAIN,DOWNDIR_DATA_KEY,AppPath,ControlMode
from .ble.devices.base_device.fn_const import PROTO_FN_CODE,DEVICE_PROTO_VER

WRITE_UUID = "0000ff02-0000-1000-8000-00805f9b34fb"

__LOGGER__ = logging.getLogger(__name__)

manufacturer = "Bluetti"
proto_file_subdir = "proto"


class BluettiData:
    """Data for the BLUETTI integration."""

    def __init__(self, hass, devices: Optional[List[dict]], control_mode: str = "cloud"):
        self.devices = [
            BluettiDevice(
                device_id=dev.sn,
                on_line=dev.online or '0',
                name=dev.name,
                sn=dev.sn,
                model=dev.model,
                state_list=dev.stateList or [],
                control_mode=dev.control_mode,
                server_key=dev.server_key,
                proto_file_url=dev.proto_file_url
            )
            for dev in devices or []
        ]
        self.loop = hass.loop


    async def test_connection(self) -> bool:
        """Test connectivity to devices."""
        await asyncio.sleep(0.1)
        return True

    async def async_poll_cloud_devices(self, now=None) -> None:
        """Fetch the state of every cloud device over REST.

        A fallback for websocket pushes, which can stop while the connection stays open,
        and the way a rejected access token gets noticed.
        """
        for device in self.devices:
            if device.control_mode != ControlMode.CLOUD:
                continue
            try:
                await device.async_update()
            except Exception as e:
                __LOGGER__.warning("BLUETTI cloud poll failed for %s: %s", device.sn, e)

    def get_device_by_sn(self, sn):
        for dev in self.devices:
            if dev.device_id == sn:
                return dev
        return None

    def web_socket_message_handler(self, message: str):
        __LOGGER__.debug(f"收到ws消息 {message}")
        __LOGGER__.debug(f"received ws message: {message}")

        res = json.loads(message)
        # load api
        sn = res["data"]["message"]["deviceSn"]

        device = self.get_device_by_sn(sn)
        if device and device.control_mode != ControlMode.BLE:
            asyncio.run_coroutine_threadsafe(device.async_update(), self.loop)

    async def asyc_start_down_proto(self,hass):
        for device in self.devices:
            hass.async_create_task(
                self.async_download_and_save_file(hass, device, proto_file_subdir)
            )

    async def async_download_and_save_file(self,hass,device,sub_dir: str = "" ):
        """
        Async Download proto file
        """
        if device.control_mode != ControlMode.BLE:
            return
        
        base_dir = hass.data[DOMAIN][DOWNDIR_DATA_KEY]
        save_dir = os.path.join(base_dir, sub_dir)
        local_down_path = save_dir+'/'+device.sn+'.bin'
        if os.path.exists(local_down_path):
            __LOGGER__.info(device.sn+'.bin exist,don''t download')
            device.local_down_path = local_down_path
            return
        decrypt_info_resp = await device._api_client.get_decrypt_info(device.sn)
        decrypt_info = decrypt_info_resp.data
        device.proto_file_url = APPLICATION_PROFILE.config["server"]["gateway"] + AppPath.DECODE_CENTER_API +'/'+ decrypt_info.protoBufFileUrl
        device.local_down_path = await device._api_client.async_download_and_save_file(device.proto_file_url,save_dir,device.sn+'.bin')

    async def disconnect_all_ble(self,hass):
        for device in self.devices:
            if device.device_reader != None:
                await device.device_reader._stop_notify()

    async def remove_download_file(self,hass):

        base_dir = hass.data[DOMAIN][DOWNDIR_DATA_KEY]
        await hass.async_add_executor_job(self.remove_download_file_task, base_dir)

    def remove_download_file_task(self,base_dir):
        save_dir = os.path.join(base_dir, proto_file_subdir)
        if os.path.exists(save_dir) == False:
            return
        for item in os.listdir(save_dir):
            full_path = os.path.join(save_dir, item)
            if os.path.isfile(full_path):
                os.remove(full_path)

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

    def __init__(self, 
                 device_id: str, 
                 on_line: str, 
                 name: str, 
                 sn: str, 
                 model: str, 
                 state_list: Optional[List[dict]] = None, 
                 api_client=None, 
                 control_mode: str = "cloud", 
                 proto_file_url: str = "", 
                 server_key: str = ""):
        self.device_id = device_id
        self.on_line = on_line
        self.name = name
        self.sn = sn
        self.model = model
        self.manufacturer = manufacturer
        self._callbacks: set[Callable[[], None]] = set()
        self._loop = asyncio.get_event_loop()
        self.control_mode = control_mode
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

        self._api_client = api_client
        self.device_reader = None
        self._bleClient = None
        self.proto_file_url = proto_file_url
        self.local_down_path = ''
        self.server_key = server_key
        
        self._unbind_processed = False
        self._hass = None
        self._entry = None
        self._entry_id = None
        # self._ws_manager = ws_manager

        # 创建一个定时任务轮询获取设备状态 TODO 蓝牙需要开启定时任务
        self.async_update = Throttle(timedelta(microseconds=1))(self._async_update)
        self._polling_lock = asyncio.Lock()

    def __repr__(self):
        return f"<BluettiDevice id={self.device_id} name={self.name}>"

    def get_state(self, fn_code: str) -> Optional[BluettiState]:
        # print('poll get device status')
        """Return state object by fn_code."""
        for s in self.states:
            if s.fn_code == fn_code:
                return s
        return None
    
    # merage local fncode and cloud fncode
    def merageFnCode(self):
        if self.control_mode == 'cloud':
            return
        if hasattr(self,'device_reader') == False or self.device_reader == None:
            return
    
        oak_state_dict = {obj.fn_code: obj for obj in self.states}
        for command in self.device_reader.oak_device.polling_commands:
            if getattr(command,'fn_code','') and command.fn_code not in oak_state_dict:
                __LOGGER__.info(f'add local ble function:{command.fn_code}') 
                self.states.append(BluettiState(
                    fn_code=command.fn_code,
                    fn_name=command.fn_name or "",
                    fn_value=command.fn_value,
                    fn_type=command.fn_type,
                ))

    async def set_state_value(self, fn_code: str, value: str):
        """Set a state value and notify callbacks."""
        state = self.get_state(fn_code)
        if not state:
            raise ValueError(f"No state with code {fn_code}")

        if self.control_mode == ControlMode.BLE:
            if self.device_reader is not None:
                # use bluetooth control device
                __LOGGER__.debug(f'start bluetooth control device for {fn_code}')
                proto_fn_code = self.device_reader.oak_device.oakfn_to_proto_fn(fn_code)
                result = await self.device_reader._async_send_write_command(proto_fn_code,value)
                __LOGGER__.debug(f'start bluetooth control device for {fn_code} result {result}')
                state.fn_value = str(result.get(fn_code,value))
            else:
                __LOGGER__.debug(f'device have no ble device reader can not control')

        if self.control_mode == 'cloud':
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
        if self.control_mode == ControlMode.BLE:
            return self.bluetooth_connected
        return self.on_line == '1'

    @property
    def bluetooth_connected(self) -> bool:
        """检查蓝牙连接状态."""
        if self.device_reader is None:
            return False

        try:
            # check if coordinator's reader and client exist and are connected
            if self.device_reader:
                reader = self.device_reader
                if hasattr(reader, 'client') and reader.client:
                    return reader.client.is_connected
                return False

        except (AttributeError, Exception) as e:
            __LOGGER__.debug(f"Error checking bluetooth connection: {e}")
            pass

        return False

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

    async def check_ble_server_key(self,data):
        if self.device_reader == None or not await self.device_reader.is_bluetooth_connected():
            return
        if data == None and self.device_reader != None and await self.device_reader.is_device_key_ok() == 0:
            __LOGGER__.info(f"Device {self.name} ble key have expired!")
            entry = self._entry
            if entry:
                all_products_data: list[dict] = entry.data.get("products", [])
                all_products: list[UserProduct] = [
                        UserProduct.model_validate(p) if isinstance(p, dict) else p
                        for p in all_products_data
                    ]
                
                is_update_entry = False
                for device in all_products:
                    if device.sn != self.sn:
                        continue
                    now_time = time.time()
                    if now_time - device.server_key_reload_time > 3600*12:
                        device.server_key = ''
                        device.server_key_reload_time = now_time
                        is_update_entry = True
                    else:
                        __LOGGER__.debug("ble key expired,last reload time in one day,don't to update again")

                if is_update_entry:
                    # update existing entry
                    self._hass.config_entries.async_update_entry(
                        entry,
                        data=dict(entry.data) | {"products":all_products}
                    )
                    __LOGGER__.info(f"Reset ble server key,Please reload to get new ble key")
                    # send notify to reload
                

    async def read_data_from_ble(
        self,  address = None
    ) -> dict | None:
        __LOGGER__.debug("Reading data from ble")
        if self.device_reader is None:
            __LOGGER__.warning('device_reader is None')
            return None

        if self.local_down_path == '' or self.local_down_path is None:
            __LOGGER__.warning('proto file not down ok!!!')
            return None

        if self.device_reader.oak_device.proto_file_path == '':
            self.device_reader.oak_device.proto_file_path = self.local_down_path

        data = await self.device_reader.read_data()

        # reset server_key to get new server key
        await self.check_ble_server_key(data)

        return data

    async def update_from_bluetooth(self, coordinator_data: dict) -> None:
        """
        update device state from bluetooth coordinator data
        parameters:
            coordinator_data: coordinator.data dictionary, contains bluetooth device returned fields
        """
        if hasattr(self,'device_reader') == False or self.device_reader == None:
            __LOGGER__.info(f'not init ble device_reader do not update ble data')
            return

        if coordinator_data is None:
            coordinator_data = {}

        oak_device = self.device_reader.oak_device

        updated_count = 0
        updated_fields = []

        #process base value
        for proto_fn_code,v in coordinator_data.items():
            oak_fn_code = oak_device.proto_fn_to_oakfn(proto_fn_code)
            state_obj = self.get_state(oak_fn_code)
            if not state_obj:
                # 如果本地ble读取的状态比较多，先暂存下来，可能后续需要使用
                __LOGGER__.debug(f"Device {self.name} does not have state for oak_fn_code: {oak_fn_code} (from proto fncode field: {proto_fn_code})")
                ble_state = BluettiState(fn_code=oak_fn_code,fn_name='',fn_value=str(v),fn_type='ble_state',support_mode_values=None,sensor_info = None)
                self.states.append(ble_state)
                continue

            bt_value = v
            if isinstance(bt_value, (int, float)):
                new_value = str(bt_value)
            elif isinstance(bt_value, str):
                new_value = bt_value
            else:
                new_value = str(bt_value)

            if state_obj.fn_value != new_value:
                old_value = state_obj.fn_value
                try:
                    # use set_value method, it will validate if the value is valid
                    state_obj.set_value(new_value)
                    updated_count += 1
                    updated_fields.append(f"{oak_fn_code}({old_value}->{new_value})")
                    __LOGGER__.debug(f"Updated {self.name} {oak_fn_code} from '{old_value}' to '{new_value}' (BT field: {proto_fn_code})")
                except ValueError as e:
                    __LOGGER__.warning(f"Failed to update {self.name} {oak_fn_code} with value '{new_value}': {e}")

        # process g2 charge and discharge 
        if oak_device.device_proto_ver == DEVICE_PROTO_VER.G2:
            chargeStatusState = self.get_state(PROTO_FN_CODE.ChargingStatus)
            chgTimeState = self.get_state(PROTO_FN_CODE.PackChgTime)
            if chargeStatusState and chargeStatusState.fn_value == '1' and self.get_state(PROTO_FN_CODE.PackChgTime)  and self.get_state(PROTO_FN_CODE.PackDsgTime):
                # charge
                self.get_state(PROTO_FN_CODE.PackChgTime).set_value(chgTimeState.fn_value)   
                self.get_state(PROTO_FN_CODE.PackDsgTime).set_value('0')   
            if chargeStatusState and chargeStatusState.fn_value != '1' and self.get_state(PROTO_FN_CODE.PackChgTime)  and self.get_state(PROTO_FN_CODE.PackDsgTime):
                # discharge 0 or 2
                self.get_state(PROTO_FN_CODE.PackDsgTime).set_value(chgTimeState.fn_value)          
                self.get_state(PROTO_FN_CODE.PackChgTime).set_value('0')

        if updated_count >= 0:
            __LOGGER__.debug(f"Updated {updated_count} states for device {self.name} from Bluetooth: {', '.join(updated_fields)}")
        await self.publish_updates()


    async def _async_update_bluetooth(self):
        # sync device state from bluetooth TODO
        print('start sync device state')

    async def _async_update(self):
        api_client = self._api_client

        device_status = await api_client.get_device_status(self.device_id)
        if hasattr(device_status,'data') == False or device_status.data == None:
            __LOGGER__.info(f'device _async_update response:{device_status}')
            return
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
            if self.device_reader:
                try:
                    reader = self.device_reader
                    if hasattr(reader, 'client') and reader.client and reader.client.is_connected :
                        await reader.client.disconnect()
                        __LOGGER__.debug(f"已断开蓝牙连接: {self.device_id}")
                except Exception as e:
                    __LOGGER__.warning(f"断开蓝牙连接时出错: {e}")

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
