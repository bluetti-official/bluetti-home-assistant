"""Device builder functions."""

import re
import logging
import platform
from ..devices.base_device.oak_device import *
from ..devices.gen2.oak_balco_device import OakBalcoDevice
from ..devices.gen2.oak_car_product_device import OakCarProductDevice
from ..devices.gen2.oak_fp_device import OakFPDevice
from ..devices.gen2.oak_portable_device import OakPortableDevice
from ..devices.gen2.oak_versatile_v1_device import OakVersatileV1Device
from ..devices.gen2.oak_versatile_v2_device import OakVersatileV2Device
from ..devices.gen1.oak_portable_device import OakPortableDeviceG1
from ..devices.gen1.oak_ble_only_device import OakBleOnlyDeviceG1

_LOGGER = logging.getLogger(__name__)

_device_classes = []
libc = ''
machine = ''

def register_device(device_class: type):
    """add device"""
    if issubclass(device_class, OakDevice):
        _device_classes.append(device_class)

def build_device_v2(address: str,bluetti_device: BluettiDevice):
    if bluetti_device is None or not bluetti_device.sn:
        _LOGGER.error("Device is empty")
        return None
    
    sn = bluetti_device.sn
    model = bluetti_device.model
    
    device_models = model.split('-')
    device_model = device_models[len(device_models)-1]  # PR30V2

    device_model = device_model.upper()
    for device_class in _device_classes:
        if device_class.supports_model(device_model):
            return device_class(address,bluetti_device)
        
    _LOGGER.info(f"unsupport model：{model}")
    return None

async def is_device_support(model: str):
    global libc,machine
    if libc == '':
        libc,machine = await get_libc_ver()
    if libc == 'musl' and machine in ["x86_64", "amd64"]:
        return False
    
    device_models = model.split('-')
    device_model = device_models[len(device_models)-1]
    device_model = device_model.upper()
    for device_class in _device_classes:
        if device_class.supports_model(device_model):
            return True
    return False

async def get_libc_ver():
    libname, ver = platform.libc_ver()
    machine = platform.machine().lower()
    return libname,machine

# "PR30V2,EL30V2,AORA30V2","PR100V2,EL100V2,AORA100V2"
register_device(OakPortableDevice)
# "Balco260","Balco500"
register_device(OakBalcoDevice)
# "RV5"
register_device(OakCarProductDevice)
# "FP"
register_device(OakFPDevice)
# "EL400","EL320,AORA320","PR200V2,Elite 200 V2,AORA200"
register_device(OakVersatileV1Device)
# "EL300,AORA300","AP300,AP300V2","AP200"
register_device(OakVersatileV2Device)
# "AC200L","AC200PL"
register_device(OakPortableDeviceG1)
# "EB3A"
register_device(OakBleOnlyDeviceG1)