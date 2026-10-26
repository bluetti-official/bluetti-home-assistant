"""Device commands."""

# Copy of https://github.com/warhammerkid/bluetti_mqtt/blob/main/bluetti_mqtt/core/commands.py

import struct
import crcmod.predefined

modbus_crc = crcmod.predefined.mkCrcFun("modbus")

class OakCmd:
    def __init__(self,fn_code):
        self.fn_code = fn_code

    def is_exception_response(self, response: bytes):
        """Checks the response code to see if it's a MODBUS exception"""
        if len(response) < 2:
            return False
        else:
            return True

    def is_valid_response(self, response: bytes):
        """Validates that the response is complete and uncorrupted"""
        if len(response) < 3:
            return False

        crc = modbus_crc(response[0:-2])
        crc_bytes = crc.to_bytes(2, byteorder="little")
        return response[-2:] == crc_bytes

class OakReadCmd(OakCmd):
    def __init__(self,fn_code,fn_name:str='',ble_fn_value:str='',ble_fn_type:str=''):
        super().__init__(fn_code)
        self.fn_name = fn_name
        self.fn_value = ble_fn_value
        # SWITCH SENSOR ... will show front with type.empty will not show 
        self.fn_type = ble_fn_type
    
    def is_exception_response(self, response: bytes):
        """Checks the response code to see if it's a MODBUS exception"""
        if len(response) < 2:
            return False
        else:
            return response[1] == 0x03 + 0x80
        
    
class OakWriteCmd(OakCmd):
    def __init__(self,fn_code,write_value):
        super().__init__(fn_code)
        self.write_value = write_value
    
    @property
    def write_type(self) -> int:
        return 3