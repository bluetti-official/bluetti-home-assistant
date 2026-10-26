import logging

from typing import Any, List
from abc import ABC, abstractmethod

from ....models import BluettiDevice
from ...utils.commands import OakReadCmd,OakWriteCmd
from .fn_const import PROTO_FN_CODE,DEVICE_PROTO_VER

__LOGGER__ = logging.getLogger(__name__)


class OakDevice(ABC):
        
    workmode_map = {
        1: 'workmode_3',
        2: 'workmode_0',
        4: 'workmode_1',
        5: 'workmode_2'
    }
    invstate_map = {
        0: 'state_0', # DeviceStateStop
        1: 'state_1', # DeviceStateOfflineRun
        2: 'state_2', # DeviceStateDWRun
        3: 'state_3', # DeviceStateAllRun
        4: 'state_4', # DeviceStateAllCharge
        5: 'state_5', # DeviceStateAllDisCharge
        6: 'state_6', # DeviceStateInvErr
        7: 'state_7' # DeviceStateErrOffline
    }
    SUPPORTED_MODELS = set()
    SUPPORTED_MODELS_CACHE = None

    @classmethod
    def _get_supported_models(cls) -> set:
        """Get all support models"""
        if cls.SUPPORTED_MODELS_CACHE is None:
            cls.SUPPORTED_MODELS_CACHE = set()
            for supported_str in cls.SUPPORTED_MODELS:
                # split model
                supported_models = [m.strip().upper() for m in supported_str.split(",")]
                cls.SUPPORTED_MODELS_CACHE.update(supported_models)
        return cls.SUPPORTED_MODELS_CACHE
    
    @classmethod
    def supports_model(cls, model: str) -> bool:
        """check model is support"""
        model = model.upper()
        return model in cls._get_supported_models()

    def __init__(self, address: str,bluetti_device: BluettiDevice):
        self.device_data = {}
        self.bluetti_device = bluetti_device
        self.slave_addr = 1
        self.address = address
        self.sn = bluetti_device.sn
        self.server_key = getattr(bluetti_device, 'server_key', '')
        self.proto_file_path = getattr(bluetti_device, 'proto_file_path', '')

    @property
    @abstractmethod
    def polling_commands(self) -> List[OakReadCmd]:
        __LOGGER__.debug(f'polling_commands no impl')
        return []
    
    @property
    def read_sn_command(self) -> List[OakReadCmd]:
        return [
            OakReadCmd(PROTO_FN_CODE.DeviceSN)
        ]
    
    @property
    @abstractmethod
    def device_proto_ver(self) -> str:
        return None
    
    # proto fn(local fn define) to oakfn(server fn define)
    @abstractmethod
    def proto_fn_to_oakfn(self,proto_fn:str)->str:
        __LOGGER__.debug(f'proto_fn_to_oakfn no impl')
        return proto_fn
    
    def oakfn_to_proto_fn(self,oakfn:str)->str:
        return oakfn
    
    # some model need to overwrite
    @abstractmethod
    def get_write_cmd(self,fn_code:str,fn_value:str) -> list[OakWriteCmd]:
        __LOGGER__.debug(f'get_write_cmd no impl')
        return [OakWriteCmd(fn_code=fn_code,write_value=fn_value)]
    
    # convert local value to server define 1-workmode_3 custom 2-workmode_0 self_use 4-workmode_1 backup use 5-workmode_2 save use
    @abstractmethod
    def parse_oak_state_data(self,coordinator_data: dict) -> dict:
        __LOGGER__.debug(f'parse_oak_state_data no impl')
        return coordinator_data