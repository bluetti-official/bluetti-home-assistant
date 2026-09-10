"""Device reader."""

import asyncio
import logging
from typing import Any, Callable, List, cast
import async_timeout
from bleak import BleakClient, BleakError, BleakScanner
# import faulthandler

from .devices.base_device.oak_device import OakDevice
from .exceptions import BadConnectionError, ModbusError, ParseError
from .ble_decoder import bleDecoder
from .utils.commands import OakReadCmd,OakWriteCmd

_LOGGER = logging.getLogger(__name__)
# faulthandler.enable()

RESPONSE_TIMEOUT = 5
WRITE_UUID = "0000ff02-0000-1000-8000-00805f9b34fb"
NOTIFY_UUID = "0000ff01-0000-1000-8000-00805f9b34fb"
DEVICE_NAME_UUID = "00002a00-0000-1000-8000-00805f9b34fb"

class DeviceReaderV2:

    def __init__(
        self,
        bleak_client: BleakClient,
        oak_device: OakDevice,
        future_builder_method: Callable[[], asyncio.Future[Any]],
        persistent_conn: bool = False,
        polling_timeout: int = 45,
        max_retries: int = 5,
    ) -> None:
        self.client = bleak_client
        self.oak_device = oak_device
        self.create_future = future_builder_method
        self.polling_timeout = polling_timeout
        self.max_retries = max_retries

        self.has_notifier = False
        self.notify_future: asyncio.Future[Any] | None = None
        self.current_command = None
        self.notify_response = bytearray()

        # polling mutex to guard against switches
        self.polling_lock = asyncio.Lock()

        self.ble_decoder_module = bleDecoder(oak_device)

        self.is_crypting = False
        self.enable_crypt = False
        self.crypt_packs = []

    async def is_bluetooth_connected(self) -> bool:
        if self.client:
            return self.client.is_connected
        return False
    
    async def is_device_key_ok(self):
        return self.ble_decoder_module.is_device_key_ok()
    
    async def read_data(
        self,  address = None
    ) -> dict | None:
        _LOGGER.debug("Reading data")

        if self.oak_device is None:
            _LOGGER.error("Device is None")
            return None

        proto_data_ok = await self.ble_decoder_module.load_device_proto()
        if proto_data_ok == False:
            _LOGGER.error(f"proto data {self.oak_device.proto_file_path} load fail!!!")
            return None

        polling_commands = self.oak_device.polling_commands
        # pack_commands = self.oak_device.pack_polling_commands
        _LOGGER.debug("Device:"+self.oak_device.sn+" Polling commands: " + ",".join([f"{c.fn_code}" for c in polling_commands]))
        # _LOGGER.info("Pack comands: " + ",".join([f"{c.starting_address}-{c.starting_address + c.quantity - 1}" for c in pack_commands]))

        parsed_data: dict = {}

        # Whether encryption is supported
        result = await BleakScanner.discover(timeout=10, return_adv=True)
        for address, (d, adv) in result.items():
            bluetti_device_name = str(self.oak_device.sn) 
            
            if bluetti_device_name == d.name:
                if adv.manufacturer_data:
                    for cid, data in adv.manufacturer_data.items():
                        if data == b'BLUETTF':
                            self.enable_crypt = True
                            break
                            
            else:
                continue
            break

        async with self.polling_lock:
            try:
                async with async_timeout.timeout(self.polling_timeout):
                    # Reconnect if not connected
                    for attempt in range(1, self.max_retries + 1):
                        try:
                            if not self.client.is_connected:
                                
                                self.ble_decoder_module.start(self.enable_crypt)   # start bluetti crypt module
                                await self.client.connect()

                                # Check if we need to encrypt the link
                                if self.enable_crypt is True:
                                    self.is_crypting = True

                            break
                        except Exception as e:
                            if attempt == self.max_retries:
                                raise e # pass exception on max_retries attempt
                            else:
                                _LOGGER.warning(f"{self.oak_device.sn} Connect unsucessful (attempt {attempt}): {e}. Retrying...")
                                _LOGGER.error(f"{self.oak_device.sn} connect_ble error：{e}", exc_info=True)
                                await asyncio.sleep(2)

                    # Attach notifier if needed
                    if not self.has_notifier:
                        await self.client.start_notify(
                            NOTIFY_UUID, self._notification_handler
                        )
                        self.has_notifier = True
                        _LOGGER.debug(f'start notify')

                    _LOGGER.debug(f'ble is conneceted:{self.client.is_connected}')

                    # Encrypt link if needed
                    if self.is_crypting is True:
                        isSuccess = await self._encrypt_link()
                        if isSuccess == 1:
                            self.is_crypting = False
                            _LOGGER.info(f'bluetti device {self.oak_device.sn} connect success!')
                        else:
                            await self._stop_notify()
                            self.ble_decoder_module.encrypt_link_clear()
                            self.is_crypting = False
                            return None

                        if self.is_crypting is True:
                            return None

                    # Execute polling commands
                    for command in polling_commands:
                        try:
                            body = await self._async_send_command(command)                        
                            _LOGGER.debug(f"polling cmd:{command.fn_code} resultype:{type(body)} body:{body}")
                            if type(body) is dict:
                                parsed_data.update(body)
                        except ParseError:
                            _LOGGER.warning("Got a parse exception")

            except TimeoutError as err:
                _LOGGER.error(f"Polling timed out ({self.polling_timeout}s). Trying again later", exc_info=err)
                await self._stop_notify()
                self.ble_decoder_module.encrypt_link_clear()
                return None
            except BleakError as err:
                _LOGGER.error("Bleak error: %s", err)
                await self._stop_notify()
                self.ble_decoder_module.encrypt_link_clear()
                return None
            finally:
                _LOGGER.debug(f'Read Data Ok')
            # Check if dict is empty
            if not parsed_data:
                return None

            bluetti_parsed_data = self.oak_device.parse_oak_state_data(parsed_data)
            return bluetti_parsed_data

    async def _stop_notify(self):
        if self.has_notifier:
            try:
                await self.client.stop_notify(NOTIFY_UUID)
                await self.client.disconnect()
            except:
                # Ignore errors here
                pass
            self.has_notifier = False
            _LOGGER.debug(f'stop notify')

    async def _encrypt_link(self):
            """Encrypt link with Bluetti device"""

            retries = 0
            max_retries = 6;
            self.crypt_packs = []
            while retries < max_retries:
                try:
                    if self.notify_future is None or self.notify_future.done():
                        self.notify_future = self.create_future()
                        self.notify_response = bytearray()
                    # Wait for response
                    res = await asyncio.wait_for(
                        self.notify_future,
                        timeout=30)
                    
                    self.crypt_packs.append(self.notify_response.hex())
                    # use crypt module to connect bluetti device
                    status, response = self.ble_decoder_module.encrypt_link(self.notify_response)

                    if (3 == status):
                        """ Read the Serial Number and determine if it is authorized """
                        read_commands = self.oak_device.read_sn_command
                        for read_sn_command in read_commands:
                            length, cmd = self.ble_decoder_module.get_read_cmd_message(read_sn_command)                        
                            asyncio.create_task(
                                self.client.write_gatt_char(WRITE_UUID, bytes(cmd))
                            )
                            # await self.client.write_gatt_char(
                            #     WRITE_UUID,
                            #     bytes(cmd))
                    elif (4 == status):
                        """ Encrypt link connected """
                        _LOGGER.info(f'client connect success')
                        return 1
                    elif (0 <= status and 0 < len(response)):
                        """ Pass-Through data to the bluetti encrypt module """
                        asyncio.create_task(
                            self.client.write_gatt_char(WRITE_UUID, bytes(response))
                        )
                        # await self.client.write_gatt_char(
                        #     WRITE_UUID,
                        #     bytes(response))
                        # _LOGGER.debug(f'client send authen data:' + response.hex())

                    retries += 1

                except asyncio.TimeoutError:
                    retries += 1
                    _LOGGER.warning(f'{self.oak_device.sn} encrypt link timeout ')
            if retries >= (max_retries-1):
                _LOGGER.warning(f'client not receive authen data, now to disconnect')
                return -1
            return 0

    async def _async_send_command(self, command: OakReadCmd) -> bytes:
        """Send read command and return response"""
        try:
            # Prepare to make request
            self.current_command = command
            self.notify_future = self.create_future()
            self.notify_response = bytearray()

            # Make request
            _LOGGER.debug("Requesting %s", command.fn_code)

            # encrypt message
            length, cmd = self.ble_decoder_module.get_read_cmd_message(command)
            logging.debug("send len: " + str(length) + " message: " + cmd.hex())

            await self.client.write_gatt_char(WRITE_UUID, bytes(cmd))

            # Wait for response
            res = await asyncio.wait_for(self.notify_future, timeout=RESPONSE_TIMEOUT)
            
            # 原库解码为modbus二进制
            if type(res) is bytearray:
                # Process data
                _LOGGER.debug("Modbus byte Got %s bytes", len(res))
                return cast(bytes, res)
            
            # 直接解码为BLUETTI_PROTO_DATA类型
            return res

        except TimeoutError:
            _LOGGER.debug("Polling single command timed out")
        except ModbusError as err:
            _LOGGER.debug(
                "Got an invalid request error for %s: %s",
                command,
                err,
            )
        except (BadConnectionError, BleakError) as err:
            # Ignore other errors
            pass

        # caught an exception, return empty bytes object
        return bytes()
    
    async def _async_send_write_command(self, fn_code: str,fn_value:str) -> bytes:
        """Send write command and return response"""
        try:
            command_list = self.oak_device.get_write_cmd(fn_code,fn_value)

            bluetti_parsed_data = {}
            for command in command_list:
                # Prepare to make request
                self.current_command = command
                self.notify_future = self.create_future()
                self.notify_response = bytearray()
                # encrypt message
                length, cmd = self.ble_decoder_module.get_write_cmd_message(command)
                await self.client.write_gatt_char(WRITE_UUID, bytes(cmd))

                # Wait for response
                res = await asyncio.wait_for(self.notify_future, timeout=RESPONSE_TIMEOUT)
                
                bluetti_parsed_data = self.oak_device.parse_oak_state_data(res)
            # decode to dict
            return bluetti_parsed_data

        except TimeoutError:
            _LOGGER.error("Polling single command timed out")
        except ModbusError as err:
            _LOGGER.error(
                "Got an invalid request error for %s: %s",
                command,
                err,
            )
        except Exception as err:
            # Ignore other errors
            _LOGGER.error("Send Write Cmd exp",err)
            pass

        await self._stop_notify();
        self.ble_decoder_module.encrypt_link_clear();
        # caught an exception, return empty bytes object
        return bytes()

    def _notification_handler(self, _sender: int, data: bytearray):
        """Handle bt data."""
        _LOGGER.debug("_notification_handler")

        if self.is_crypting and data.hex() in self.crypt_packs:
            return
        
        # Ignore notifications we don't expect
        if self.notify_future is None or self.notify_future.done():
            _LOGGER.warning(f"Unexpected notification self.cmd:{self.current_command}")
            return

        # If something went wrong, we might get weird data.
        if data == b"AT+NAME?\r" or data == b"AT+ADV?\r":
            err = BadConnectionError("Got AT+ notification")
            self.notify_future.set_exception(err)
            return

        # Save data
        self.notify_response.extend(data)

        if self.is_crypting is False:
            bluetti_data = {}
            if type(self.current_command) is OakReadCmd:
                bluetti_data = self.ble_decoder_module.message_handle(self.current_command,data)
            elif type(self.current_command) is OakWriteCmd:
                bluetti_data = self.ble_decoder_module.message_handle(self.current_command,data)
            self.notify_future.set_result(bluetti_data)
        else:
            """ Bluetooth is establishing an encrypted channel and Pass-Through data to the bluetti encryption module """
            _LOGGER.debug(f' bluetooth is encrypting... ')
            self.notify_future.set_result(self.notify_response)                     
                                    

