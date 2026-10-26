import logging

from typing import Any, List
from ....models import BluettiDevice
from ...utils.commands import OakReadCmd,OakWriteCmd
from .fn_const import PROTO_FN_CODE,DEVICE_PROTO_VER
from .oak_device_gen2 import OakDeviceGen2

__LOGGER__ = logging.getLogger(__name__)


class OakDeviceGen1(OakDeviceGen2):

    fncode_gen1_map = {
        PROTO_FN_CODE.SetAC: PROTO_FN_CODE.SetAcOutputEnableG1,
        PROTO_FN_CODE.SetDC: PROTO_FN_CODE.SetDcOutputEnableG1,
        PROTO_FN_CODE.SOC: PROTO_FN_CODE.SystemBatterySocG1,
        PROTO_FN_CODE.PowerOn: PROTO_FN_CODE.SetSystemPowerOnG1,
        PROTO_FN_CODE.InvWorkState: PROTO_FN_CODE.InvWorkStatusG1,
        PROTO_FN_CODE.PackChgTime: PROTO_FN_CODE.SystemChgFullTimeG1,
        PROTO_FN_CODE.PackDsgTime: PROTO_FN_CODE.SystemDsgEmptyTimeG1,
        PROTO_FN_CODE.WorkMode: PROTO_FN_CODE.SetSystemWorkModeG1,
        PROTO_FN_CODE.SetDCECO: PROTO_FN_CODE.SetDCECOEnableG1,
        PROTO_FN_CODE.SetACECO: PROTO_FN_CODE.SetACECOEnableG1,
        PROTO_FN_CODE.ACLoadAllTotalPower: PROTO_FN_CODE.PowerAcDischargeG1,
        PROTO_FN_CODE.DCLoadAllTotalPower: PROTO_FN_CODE.PowerDcDischargeG1,
        PROTO_FN_CODE.PVAllTotalPower: PROTO_FN_CODE.PowerPvChargeG1,
        PROTO_FN_CODE.GridAllTotalPower: PROTO_FN_CODE.PowerGridChargeG1,
    }
    workmode_map = {
        1: 'workmode_3',
        2: 'workmode_0',
        4: 'workmode_2',
        3: 'workmode_1'
    }
    
    def __init__(self, address: str,bluetti_device: BluettiDevice):
        super().__init__(address,bluetti_device)

    @property
    def device_proto_ver(self) -> str:
        return DEVICE_PROTO_VER.G1

    @property
    def read_sn_command(self) -> List[OakReadCmd]:
        return [OakReadCmd(PROTO_FN_CODE.DeviceSNG1)]
    
    # fn convert
    def proto_fn_to_oakfn(self,proto_fn:str)->str:
        reverse_fncode_gen1_map = {v: k for k, v in self.fncode_gen1_map.items()}
        return reverse_fncode_gen1_map.get(proto_fn, proto_fn)
    
    @property
    def polling_commands(self) -> List[OakReadCmd]:
        local_cmds = []
        oak_server_cmds = [OakReadCmd(self.fncode_gen1_map.get(state.fn_code,state.fn_code)) for state in self.bluetti_device.states]
        have_sleep_fn = any(state.fn_code == PROTO_FN_CODE.SleepModeFnCode for state in self.bluetti_device.states)
        if have_sleep_fn == True:
            # local function,fn_type "SWITCH","SENSOR" will show in switch entity empty not show is front
            remoteSet = OakReadCmd(PROTO_FN_CODE.RemoteSet,"Sleep Switch","0","")
            remoteSetSoc = OakReadCmd(PROTO_FN_CODE.RemoteSetSoc,"Sleep Min SOC","0","")
            iotState = OakReadCmd(PROTO_FN_CODE.IotState,"Iot State","0","")
            local_cmds = [remoteSet,remoteSetSoc,iotState]
            
        cmd_dict = {cmd.fn_code: cmd for cmd in oak_server_cmds}
        cmd_dict.update({cmd.fn_code: cmd for cmd in local_cmds})
        return list(cmd_dict.values())
    
    def get_write_cmd(self,fn_code:str,fn_value:str) -> list[OakWriteCmd]:
        # work mode value convert
        if fn_code == PROTO_FN_CODE.WorkMode:
            write_value = self.workmode_state_to_value(fn_value)
        else:            
            write_value = int(fn_value)

        fn_code_g1 = self.fncode_gen1_map.get(fn_code,fn_code)
        return [OakWriteCmd(fn_code=fn_code_g1,write_value=write_value)]
    
    def workmode_value_to_state(self,value) -> str:
        return self.workmode_map.get(value, '')
    
    def workmode_state_to_value(self,value) -> int:
        reverse_workmode_map = {v: k for k, v in self.workmode_map.items()}
        return reverse_workmode_map.get(value, 0)
