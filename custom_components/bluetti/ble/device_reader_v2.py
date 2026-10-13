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
# Wait after the latest notification before decoding.
FRAGMENT_QUIET_SECONDS = 0.5
ENCRYPTION_SCAN_TIMEOUT = 10



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
        self._notify_generation = 0
        self._fragment_timer: asyncio.TimerHandle | None = None

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

        if not self.enable_crypt and not self._client_is_connected():
            await self._detect_encryption()

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

    def _client_is_connected(self) -> bool:
        return bool(self.client and self.client.is_connected)

    async def _detect_encryption(self) -> None:
        """Set enable_crypt when the device advertises the BLUETTF flag."""
        try:
            result = await BleakScanner.discover(
                timeout=ENCRYPTION_SCAN_TIMEOUT, return_adv=True
            )
        except Exception as err:
            _LOGGER.debug("Encryption advertisement scan failed: %s", err)
            return

        serial = str(self.oak_device.sn)
        for _address, (device, adv) in result.items():
            if device.name != serial or not adv.manufacturer_data:
                continue
            if any(payload == b"BLUETTF" for payload in adv.manufacturer_data.values()):
                self.enable_crypt = True
                _LOGGER.info("%s uses encrypted BLE", serial)
                return

    def _cancel_fragment_timer(self) -> None:
        timer = self._fragment_timer
        self._fragment_timer = None
        if timer is not None:
            timer.cancel()

    def _arm_notify_future(self) -> None:
        """Prepare for one command response and invalidate an in-flight fragment flush."""
        self._notify_generation += 1
        self._cancel_fragment_timer()
        self.notify_response = bytearray()
        self.notify_future = self.create_future()

    async def _stop_notify(self):
        self._notify_generation += 1
        self._cancel_fragment_timer()
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
                        self._arm_notify_future()
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
            self._arm_notify_future()

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
                self._arm_notify_future()
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
        _LOGGER.debug("_notification_handler (%d bytes)", len(data))

        if self.is_crypting and data.hex() in self.crypt_packs:
            return

        # Late fragments of a response we already finished, or notifies that
        # arrive after a timeout.
        if self.notify_future is None or self.notify_future.done():
            _LOGGER.warning(
                "Ignoring late BLE notification (%d bytes) for %s",
                len(data),
                getattr(self.current_command, "fn_code", self.current_command),
            )
            return

        # If something went wrong, we might get weird data.
        if data == b"AT+NAME?\r" or data == b"AT+ADV?\r":
            self._cancel_fragment_timer()
            err = BadConnectionError("Got AT+ notification")
            self.notify_future.set_exception(err)
            return

        self.notify_response.extend(data)

        if self.is_crypting:
            # Handshake packets are discrete messages for the crypt module.
            _LOGGER.debug("bluetooth is encrypting...")
            self._cancel_fragment_timer()
            self.notify_future.set_result(bytes(self.notify_response))
            return

        self._cancel_fragment_timer()
        try:
            self._fragment_timer = asyncio.get_running_loop().call_later(
                FRAGMENT_QUIET_SECONDS,
                self._finish_notification,
                self._notify_generation,
            )
        except RuntimeError:
            self._finish_notification(self._notify_generation)
        
        _LOGGER.debug(
            "Buffering BLE notification, %d bytes so far",
            len(self.notify_response),
        )
        

    def _finish_notification(self, generation: int) -> None:
        self._cancel_fragment_timer()
        if generation != self._notify_generation:
            return
        if self.notify_future is None or self.notify_future.done():
            return
        if not self.notify_response:
            return

        if self.is_crypting:
            self.notify_future.set_result(bytes(self.notify_response))
            return

        decoded = {}
        
        command = self.current_command
        payload = bytes(self.notify_response)
        if type(command) in (OakReadCmd, OakWriteCmd):
            try:
                decoded = self.ble_decoder_module.message_handle(command, payload)
            except Exception as err:
                _LOGGER.warning(
                    "Failed to decode BLE response for %s: %s",
                    getattr(command, "fn_code", command),
                    err,
                )

        self.notify_future.set_result(decoded)
        

