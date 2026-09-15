import logging
import os

import yaml

from homeassistant.core import HomeAssistant
from homeassistant.loader import async_get_integration
from ..ble.lib.bluetti_lib_loader import BleLibLoader
from ..const import INTEGRATION_NAME,DOMAIN

__LOGGER__ = logging.getLogger(__name__)


class ApplicationProfile:
    __active: str = ""
    __configFile: str = ""
    __configPath: str = ""
    config: dict = {}

    def __init__(self, active=None):
        self.__active = active or os.getenv("BLUETTI_PROFILE_ACTIVE", "").lower()
        __LOGGER__.info("Setting up application profile: %s", "prod" if self.__active == "" else self.__active)

        if self.__active != "":
            self.__active = "-" + self.__active

        self.integrationVer = None
        self.bleLibLoader = None   # BLUETTI BLE SO Lib Loader

        self.__configFile = "application" + self.__active + ".yaml"
        self.__configPath = os.path.dirname(os.path.abspath(__file__)) + "/" + self.__configFile
        self.__configIsOk = False

    async def unload(self):
        ''' unload '''
        self.__configIsOk = False

    """加载运行环境的配置文件"""
    async def load_config(self, hass: HomeAssistant):
        if self.__configIsOk:
            return

        # Read the version of integration
        integration = await async_get_integration(hass, DOMAIN)
        self.integrationVer = str(integration.version)

        await hass.async_add_executor_job(self.__load_config)
        self.__configIsOk = True

        # Read the version of BLE SO, and download the dependency libs
        __ble_lib_version = integration.manifest.get("ble_lib_version", 20260908)
        self.bleLibLoader = BleLibLoader(__ble_lib_version, self.config["server"]["oss"])
        self.bleLibLoader.download_dependency_libs(hass)

        # __ble_lib_path = await self.bleLibLoader.download_ble_lib()
        # print(__ble_lib_path)

    def __load_config(self):
        with open(self.__configPath, "r") as file:
            __yaml__ = yaml.safe_load(file)
            __LOGGER__.info("Load profile " f"{self.__configFile} of `{INTEGRATION_NAME}` integration successfully.")

        self.config =  __yaml__['bluetti']
        self.config["app"]["app-ver"] = self.integrationVer

        __LOGGER__.info(f'config:{self.config}')
