import asyncio
import logging
import platform
import importlib
import os

from .utils.commands import OakReadCmd,OakWriteCmd
from .devices.base_device.oak_device import OakDevice


_LOGGER = logging.getLogger(__name__)

    
machine = platform.machine().lower()
try:
    if machine in ["x86_64", "amd64"]:
        from .lib.x86_64 import bluetti_ble_lib
        from .lib.x86_64.bluetti_ble_lib import BLUETTI_PROTO_DATA
    elif machine in ["arm64", "aarch64"]:
        from .lib.aarch64 import bluetti_ble_lib
        from .lib.aarch64.bluetti_ble_lib import BLUETTI_PROTO_DATA
    else:
        raise ImportError(f"Unsupported architecture: {machine}")
except ImportError as e:
    _LOGGER.error(f'unsupport {machine} default load x86_64')
    # raise RuntimeError(f"Failed to import crypt module: {e}")

def start_ble_lib():
    bluetti_ble_lib.clear_link_device()
    
class bleDecoder:
    def __init__(self,oak_device:OakDevice=None):
        self.cryptoClient = None
        self.enable = False
        self.oak_device = oak_device
        self.mode_sn = self.oak_device.sn
        _LOGGER.debug(f'self.mode_sn: {self.mode_sn}')
        self.proto_data = None
        
    async def load_device_proto(self)->bool:
        wait_count = 0
        while wait_count < 5 and self.proto_data == None:
            if os.path.exists(self.oak_device.proto_file_path):
                self.proto_data = await self.async_read_bin_file(self.oak_device.proto_file_path)
                _LOGGER.debug(f'load proto data len: {len(self.proto_data)}')
                return True
            else:
                wait_count += 1
                await asyncio.sleep(1)
        return self.proto_data != None
    
    async def async_read_bin_file(hass, file_path: str) -> bytes:
        """异步读取二进制文件（自定义模式）"""
        # 将同步 open() 放到线程中执行，不阻塞事件循环
        def _sync_read():
            with open(file_path, "rb") as f:
                return f.read()
        
        bin_data = await asyncio.to_thread(_sync_read)
        return bin_data

    def start(self, enable: bool = True):
        try:
            self.enable = enable
            _LOGGER.info('Bluetti BLE lib software version: V2')
        except ImportError:
            _LOGGER.warning("bluetti_ble_lib not available, encryption disabled")
            self.enable = False

    def encrypt_link_clear(self):
        if self.mode_sn:
            bluetti_ble_lib.clear_linked_device(self.mode_sn)
            
    def is_device_key_ok(self):
        return bluetti_ble_lib.is_device_key_ok(self.mode_sn)

    def encrypt_link(self, data: bytearray):
        if not self.enable or self.oak_device.server_key == None or self.oak_device.server_key == '':
            _LOGGER.error(f'encrypt link not self.enable:{self.enable} server_key:{self.oak_device.server_key}') 
            return 3, b''
        if data == None:
            data = b''
        message, ret,message_len = bluetti_ble_lib.crypt_link(self.mode_sn,self.oak_device.server_key,bytes(data),len(data))
        if message == None:
            message = b''
        return ret, message

    def get_read_cmd_message(self, cmd: OakReadCmd):
        if not self.enable:
            return 0, b''
        message,message_len = bluetti_ble_lib.get_read_encrypt_cmd(self.mode_sn,self.proto_data,len(self.proto_data),cmd.fn_code,self.oak_device.slave_addr)
        _LOGGER.debug(f'get_read_cmd_message fncode:{cmd.fn_code} message: {message.hex()}')
        return len(message), message
    
    def get_write_cmd_message(self, cmd: OakWriteCmd):
        if not self.enable:
            return 0, b''
        message = b''
        if cmd.write_type == 3:
            message,message_len = bluetti_ble_lib.get_write_single_encrypt_cmd(self.mode_sn,self.proto_data,len(self.proto_data),cmd.fn_code,self.oak_device.slave_addr,cmd.write_value)
        _LOGGER.debug(f'get_write_cmd_message fncode:{cmd.fn_code} message: {message.hex()}')
        return len(message), message
    
    def message_handle(self, cmd: OakReadCmd,data: bytearray):
        if not self.enable:
            return len(data), data
        bluetti_result = bluetti_ble_lib.parse_bluetti_encrypt(self.mode_sn,self.proto_data,len(self.proto_data),bytes(data),len(data),cmd.fn_code)
        dict_data = self.decode_data_to_dict(bluetti_result)
        bluetti_ble_lib.free_bluetti_proto_data(bluetti_result)
        return dict_data

    def decode_data_to_dict(self,bluetti_result:BLUETTI_PROTO_DATA):
        data_dict = {}
        if type(bluetti_result) is BLUETTI_PROTO_DATA:                                
            for i in range(bluetti_result.reg_data_len):
                reg = bluetti_result.reg_data[i]
                # dig
                if reg.value_type == 1:
                    data_dict[reg.fn_code] = reg.fn_value
                # str
                if reg.value_type == 2:
                    data_dict[reg.fn_code] = reg.fn_value_str
                # bit
                if reg.value_type == 3:
                    for j in range(reg.bit_values_len):
                        bit_field = reg.bit_values[j]
                        data_dict[reg.fn_code+':'+bit_field.bit_code] = bit_field.bit_value
        return data_dict  

