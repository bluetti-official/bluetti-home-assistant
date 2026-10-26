import logging

from typing import Any, List
from abc import ABC, abstractmethod

from ....models import BluettiDevice
from ...utils.commands import OakReadCmd,OakWriteCmd
from .fn_const import PROTO_FN_CODE,DEVICE_PROTO_VER
from .oak_device import OakDevice

__LOGGER__ = logging.getLogger(__name__)


class OakDeviceGen2(OakDevice):

    def __init__(self, address: str,bluetti_device: BluettiDevice):
        super().__init__(address,bluetti_device)
    
    @property
    def polling_commands(self) -> List[OakReadCmd]:
        local_cmds = []
        oak_server_cmds = [OakReadCmd(self.oakfn_to_proto_fn(state.fn_code)) for state in self.bluetti_device.states]
        have_sleep_fn = any(state.fn_code == PROTO_FN_CODE.SleepModeFnCode for state in self.bluetti_device.states)
        if have_sleep_fn == True:
            # local function,fn_type "SWITCH","SENSOR" will show in switch entity empty not show is front
            remoteSet = OakReadCmd(PROTO_FN_CODE.RemoteSet,"Sleep Switch","0","")
            remoteSetSoc = OakReadCmd(PROTO_FN_CODE.RemoteSetSoc,"Sleep Min SOC","0","")
            iotState = OakReadCmd(PROTO_FN_CODE.IotState,"Iot State","0","")
            local_cmds = [remoteSet,remoteSetSoc,iotState]
            
        local_cmds.append(OakReadCmd(PROTO_FN_CODE.ChargingStatus,"Charging Status","0",""))
        cmd_dict = {cmd.fn_code: cmd for cmd in oak_server_cmds}
        cmd_dict.update({cmd.fn_code: cmd for cmd in local_cmds})
        return list(cmd_dict.values())
    

    @property
    def device_proto_ver(self) -> str:
        return DEVICE_PROTO_VER.G2
    
    # fn convert
    def proto_fn_to_oakfn(self,proto_fn:str)->str:
        # sleep mode
        if proto_fn == PROTO_FN_CODE.SleepState:
            return PROTO_FN_CODE.SleepModeFnCode
        return proto_fn
    
    
    # some model need to overwrite
    def get_write_cmd(self,fn_code:str,fn_value:str) -> list[OakWriteCmd]:
        # sleep mode for specal
        if fn_code == PROTO_FN_CODE.SleepModeFnCode:
            return self.build_sleep_cmd(fn_value)
        
        # work mode value convert
        if fn_code == PROTO_FN_CODE.WorkMode:
            write_value = self.workmode_state_to_value(fn_value)
        else:            
            write_value = int(fn_value)

        return [OakWriteCmd(fn_code=fn_code,write_value=write_value)]
    
    # this is fp sleep mode op logic
    def build_sleep_cmd(self,fn_value) -> list[OakWriteCmd]:
        # set sleep mode，check remoteset is 1 or 0,check so is set or not
        remote_cmds = []
        
        # fp sleep mode 3 or 4
        write_value = 3
        if fn_value == '1':
            # open sleep mode
            write_value = 4
            remote_cmds = self.build_sleep_pre_cmd()
        if fn_value == '0':
            write_value = 3

        sleep_cmd = OakWriteCmd(fn_code=PROTO_FN_CODE.PowerOn,write_value=write_value)
        return remote_cmds+[sleep_cmd]
    
    def build_sleep_pre_cmd(self) -> list[OakWriteCmd]:
        remote_set = self.device_data.get(PROTO_FN_CODE.RemoteSet,0)
        remote_setSoc = self.device_data.get(PROTO_FN_CODE.RemoteSetSoc,None)
        remote_cmds = []
        if remote_set != 1:
            __LOGGER__.debug(f'set remoteset to 1')
            remote_cmds.append(OakWriteCmd(fn_code=PROTO_FN_CODE.RemoteSet,write_value=1))
        if remote_setSoc == None or remote_setSoc <=0 or remote_setSoc >=100:
            __LOGGER__.debug(f'set remotesetsoc to 20')
            remote_cmds.append(OakWriteCmd(fn_code=PROTO_FN_CODE.RemoteSetSoc,write_value=20))
        return remote_cmds
    
    # convert local value to server define 1-workmode_3 custom 2-workmode_0 self_use 4-workmode_1 backup use 5-workmode_2 save use
    def parse_oak_state_data(self,coordinator_data: dict) -> dict:
        self.device_data.update(coordinator_data)
        __LOGGER__.debug(f'save_device_data:{self.device_data}')
        bluetti_state = {}
        for k,v in coordinator_data.items():
            bluetti_value = v
            if k == PROTO_FN_CODE.WorkMode or k == PROTO_FN_CODE.SetSystemWorkModeG1:
                bluetti_value = self.workmode_value_to_state(v)
            if k == PROTO_FN_CODE.InvWorkState:
                bluetti_value = self.invstate_value_to_state(v)
            bluetti_state[k] = bluetti_value
        return bluetti_state

    def workmode_value_to_state(self,value) -> str:
        return self.workmode_map.get(value, '')
    
    def workmode_state_to_value(self,value) -> int:
        reverse_workmode_map = {v: k for k, v in self.workmode_map.items()}
        return reverse_workmode_map.get(value, 0)

    def invstate_value_to_state(self,value)->str:
        return self.invstate_map.get(value,'state_0')
    