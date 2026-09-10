"""Coordinator for Bluetti integration."""

from __future__ import annotations

from datetime import timedelta
import logging

import string
from bleak import BleakClient

from homeassistant.components import bluetooth
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
)

from homeassistant.components.bluetooth import async_discovered_service_info

from .device_reader_v2 import DeviceReaderV2
from .utils.device_builder import build_device_v2
from ..models import BluettiDevice

_LOGGER = logging.getLogger(__name__)

def mac_loggable(mac: str) -> str:
    """Remove parts of the mac address for logging."""
    splitted = mac.split(":")
    return "XX:XX:XX:XX:XX:" + splitted[-1]

class PollingCoordinator(DataUpdateCoordinator):
    """Polling coordinator."""

    def __init__(
        self,
        hass: HomeAssistant,
        address: str,
        bluetti_device: BluettiDevice,
        polling_interval: int,
        persistent_conn: bool,
        polling_timeout: int,
        max_retries: int,
    ):
        """Initialize coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="Bluetti polling coordinator",
            update_interval=timedelta(seconds=polling_interval),
        )

        #bluettidevice network model, oakdevice ble op device model
        self.bluetti_device = bluetti_device
        self.address = address
        self.persistent_conn = persistent_conn
        self.polling_timeout = polling_timeout
        self.max_retries = max_retries

        # Create client
        self.client = None
        self.check_address()
        self.connect_ble()

    # check ble address is valid,if not discover it
    def check_address(self):
        if self.address != None and self.address != '':
            return
        discovered_bt_devices = async_discovered_service_info(self.hass)
        for bt_device in discovered_bt_devices:
            if not bt_device.name:
                continue

            # bt_name = bt_device.name.strip()
            raw_name = bt_device.name
            bt_name = ''.join(c for c in raw_name if c in string.printable).strip()
            bt_address = bt_device.address
            if self.bluetti_device.sn == bt_name:
                self.address = bt_address
                break
        
    # connect to ble device
    def connect_ble(self):
        self.logger.debug("connect_ble")
        try:
            if self.address == None or self.address == '':
                return None
            self.client = None
            ble_device = bluetooth.async_ble_device_from_address(self.hass, self.address)
            if ble_device is None:
                self.logger.error("Device %s not available", mac_loggable(self.address))
                return None
            self.client = BleakClient(ble_device,mtu_size=200)

            oak_device = build_device_v2(self.address, self.bluetti_device)
            if oak_device is None:
                return None
            
            self.bluetti_device.device_reader = DeviceReaderV2(
                self.client,
                oak_device,
                self.hass.loop.create_future,
                persistent_conn = self.persistent_conn,
                polling_timeout = self.polling_timeout,
                max_retries = self.max_retries,
            )
        except Exception as e:
            self.address = ''
            self.logger.error(f"connect_ble error：{e}", exc_info=True)
            
        return None


    async def _async_update_data(self):
        """Fetch data from API endpoint.

        This is the place to pre-process the data to lookup tables
        so entities can quickly look up their data.
        """

        self.check_address()
        # Check if device is connected
        if self.address == None or self.address == '' or bluetooth.async_address_present(self.hass, self.address, connectable=True) is False:
            self.logger.warning(f"Device {self.bluetti_device.name}(0x{id(self)}) not connected")
            self.last_update_success = False
            return None
        
        if hasattr(self,'client') and self.client is None:
            self.logger.error("Device %s not available", mac_loggable(self.address))
            self.connect_ble()
            return None      

        data = await self.bluetti_device.read_data_from_ble()
        return data
