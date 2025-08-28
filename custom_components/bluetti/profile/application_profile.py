import logging
import os

import yaml

from ..const import INTEGRATION_NAME

__LOGGER__ = logging.getLogger(__name__)


class ApplicationProfile:
    __active: str = ""
    __configFile: str = ""
    __configPath: str = ""
    config: dict = {}

    def __init__(self, active=None):
        self.__active = active or os.getenv("bluetti.profile.active", "").lower()
        __LOGGER__.info("Setting up application profile: %s", "prod" if self.__active == "" else self.__active)

        if self.__active != "":
            self.__active = "-" + self.__active

        self.__configFile = "application" + self.__active + ".yaml"
        self.__configPath = os.path.dirname(os.path.abspath(__file__)) + "/" + self.__configFile

    """加载运行环境的配置文件"""
    def load_config(self, hass):
        hass.async_add_executor_job(self.__load_config)

    def __load_config(self):
        with open(self.__configPath, "r") as file:
            __yaml__ = yaml.safe_load(file)
            __LOGGER__.info("Load profile " f"{self.__configFile} of `{INTEGRATION_NAME}` integration successfully.")

        self.config = __yaml__['bluetti']
        # print(self.config)
