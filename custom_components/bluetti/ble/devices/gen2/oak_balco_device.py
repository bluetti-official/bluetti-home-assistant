from typing import Any, List

from ....models import BluettiDevice
from ...utils.commands import OakWriteCmd
from ..base_device.oak_device_gen2 import OakDeviceGen2
from ..base_device.fn_const import PROTO_FN_CODE

class OakBalcoDevice(OakDeviceGen2):
    SUPPORTED_MODELS = {"Balco260","Balco500"}
    SUPPORTED_MODELS_CACHE = None

    def __init__(self, address: str,bluetti_device:BluettiDevice):
        super().__init__(address,bluetti_device)
        self.slave_addr = 0

    # return the ble cmd
    def get_write_cmd(self,fn_code:str,fn_value:str) -> list[OakWriteCmd]:
        if fn_code == PROTO_FN_CODE.SetAC:
            write_value = (1 if '0' == fn_value else 0)
            return [OakWriteCmd(fn_code=PROTO_FN_CODE.SetAC,write_value=write_value)]
              
        return super().get_write_cmd(fn_code,fn_value)
    
    def parse_oak_state_data(self,coordinator_data: dict) -> dict:
        bluetti_state = super().parse_oak_state_data(coordinator_data)
        
        for k,v in bluetti_state.items():
            bluetti_value = v
            if k == PROTO_FN_CODE.SetAC:
                bluetti_value = ('1' if 0 == bluetti_value else '0')
            bluetti_state[k] = bluetti_value

        return bluetti_state

    # call when read ble data to state value,after parse_oak_state_data
    def proto_fn_to_oakfn(self,proto_fn:str)->str:
        if proto_fn == PROTO_FN_CODE.WorkMode:
            return PROTO_FN_CODE.WorkModeBalco
        # balco standby 
        if proto_fn == PROTO_FN_CODE.SetAC:
            return PROTO_FN_CODE.BalcoStandby
        return super().proto_fn_to_oakfn(proto_fn)

    # call when send cmd to device,before get_write_cmd
    def oakfn_to_proto_fn(self,oakfn:str)->str:
        if oakfn == PROTO_FN_CODE.WorkModeBalco:
            return PROTO_FN_CODE.WorkMode
        # balco standby 
        if oakfn == PROTO_FN_CODE.BalcoStandby:
            return PROTO_FN_CODE.SetAC
        return super().oakfn_to_proto_fn(oakfn)