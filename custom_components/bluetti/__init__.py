from core import HomeAssistant
from constants import (DOMAIN)


async def async_setup(hass: HomeAssistant, config):
    #hass.data.setdefault(DOMAIN, {})
    hass.states.async_set("bluetti.world", "Hello World")
    return True
