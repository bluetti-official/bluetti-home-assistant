"""Icon configuration for BLUETTI integration."""

# fn_code 到图标的映射
FN_CODE_ICONS = {
    # SENSOR 类型
    "SOC": "mdi:battery",
    "InvWorkState": "mdi:solar-power",
    
    # SELECT 类型
    "SetCtrlWorkMode": "mdi:cog",
    "SetDCECO": "mdi:flash",
    "SetACECO": "mdi:power-plug",
    
    # SWITCH 类型
    "SetCtrlAc": "mdi:power-socket-us",
    "SetCtrlDc": "mdi:car-battery",
    "SetCtrlPowerOn": "mdi:power",
    "Storm_Mode_Cloud_Ctrl": "mdi:weather-lightning",
    
    # BINARY_SENSOR 类型
    "onLine": "mdi:lan-connect",
}

def get_icon_for_fn_code(fn_code: str) -> str:
    """获取fn_code对应的图标."""
    return FN_CODE_ICONS.get(fn_code, "mdi:help-circle")
