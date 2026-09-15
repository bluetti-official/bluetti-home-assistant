import logging
import json
import time
from threading import Thread
from typing import Callable

import stomper
import websocket
import threading

from homeassistant.core import HomeAssistant
from ..application_exception import ApplicationRuntimeException

from ..const import EVENT_TOKEN_EXPIRED

__LOGGER__ = logging.getLogger(__name__)


class StompClient(object):
    def __init__(self, url: str, access_token: str, config: dict, handler: Callable[[str], None] = None,
                 hass: HomeAssistant = None):
        self.__url = url
        self.__headers = {
            "Host": self.__get_host(url),
            "Authorization": access_token,
            "x-os": "open",
            "x-app-key": f"{config["app"]["app-key"]}",
            "x-app-ver": f"{config["app"]["app-ver"]}"
        }
        self.listener = StompListener(self, handler)
        self.hass = hass
        self.websocket = None
        self.running = False

        self.heartbeat_thread = None
        self.heartbeat_interval = 60

        self.reconnect_delay = None
        self.max_reconnect_delay = None
        # __LOGGER__.info(f"ws use token:{access_token}")

    @staticmethod
    def __get_host(connection_url: str):
        host = connection_url.split("//")[1]
        index = host.find("/")
        host = host[0:index]

        if host.find(":") > -1:
            host = host.split(":")[0]
        return host

    def connect(self):
        """
        Connect to the ws server by the long term.
        :return:
        """

        stomp_trace = True
        websocket.enableTrace(stomp_trace)

        __LOGGER__.info("Start to connect the BLUETTI WebSocket Server.")
        __LOGGER__.info("Stomp client trace enable: %s", stomp_trace)

        self.websocket = websocket.WebSocketApp(self.__url,
                                                on_message=self.listener.on_message,
                                                on_error=self.listener.on_error,
                                                on_close=self.listener.on_close, )
        # bind the `on_open` function
        self.websocket.on_open = self.__on_open
        self.running = True
        self.reconnect_delay = 1  # 初始重连延迟（秒）
        self.max_reconnect_delay = 30  # 最大重连延迟（秒）
        # Run until interruption to client or server terminates connection.
        Thread(target=self._run_forever_safe, daemon=True, name="bluetti-ws").start()

    # These codes were contributed by @chpego
    def _run_forever_safe(self):
        try:
            self.websocket.run_forever()
        except Exception as e:
            __LOGGER__.exception(f"BLUETTI WebSocket thread crashed: {e}")
            if self.running:
                self.reconnect()

    def disconnect(self):
        self.running = False
        if self.heartbeat_thread and self.heartbeat_thread.is_alive():
            self.heartbeat_thread.join(timeout=5)
        self.websocket.close()

    def __on_open(self, ws):
        # Initial CONNECT required to initialize the server's client registries.
        interval = self.heartbeat_interval * 1000
        headers = {
            "accept-version": "1.0,1.1,2.0",
            "heart-beat": f"{str(interval)},{str(interval)}",
            **self.__headers
        }

        lines = ["CONNECT"]
        for name, value in headers.items():
            lines.append(f"{name}:{value}")

        # connect = ("CONNECT\n"
        #            "accept-version:1.0,1.1,2.0\n"
        #            "Host:" + self.__headers["Host"] + "\n"
        #            "Authorization:" + self.__headers["Authorization"] + "\n"
        #            "heart-beat:" + str(interval) + "," + str(interval) + "\n"
        #            "x-os:" + self.__headers["x-os"] + "\n"
        #            "x-app-key:" + self.__headers["x-app-key"] + "\n"
        #            "\n\x00")

        connect = "\n".join(lines) + "\n\n\x00"
        ws.send(connect)

        # start heartbeat thread
        # the heartbeat thread starts after receiving the CONNECTED frame. From now on, it will no longer start.
        # self._start_heartbeat()

    def start_heartbeat(self):
        """start heartbeat thread"""
        if self.heartbeat_thread and self.heartbeat_thread.is_alive():
            return

        self.heartbeat_thread = threading.Thread(target=self._send_heartbeat, daemon=True, name="bluetti-heartbeat")
        self.heartbeat_thread.start()

    def _send_heartbeat(self):
        """loop send heartbeat"""
        while self.running and self.websocket and hasattr(self.websocket, 'sock') and self.websocket.sock:
            try:
                if not self.websocket.sock.connected:
                    break

                self.websocket.send("\n")
                __LOGGER__.debug("Sent STOMP heartbeat")

            except Exception as e:
                __LOGGER__.error(f"Failed to send heartbeat: {e}")
                break

            time.sleep(self.heartbeat_interval)

    def reconnect(self):
        __LOGGER__.info("Websocket reconnect")
        if self.running:
            time.sleep(self.reconnect_delay)
            self.reconnect_delay = min(self.reconnect_delay * 2, self.max_reconnect_delay)
            self.connect()
        else:
            __LOGGER__.info("Websocket have stop do not reconnect")


class StompListener:
    def __init__(self, stompClient: StompClient, handler: Callable[[str], None] = None):
        self.__handler = handler
        self.client = stompClient

    def __callback(self, callback, *args) -> None:
        if callback:
            try:
                callback(*args)

            except Exception as e:
                __LOGGER__.error(f"error from callback {callback}: {e}")
                # if self.on_error:
                #    self.on_error(self, e)

    def __on_subscribe(self, ws: websocket, destination: str):
        sub = stomper.subscribe(destination, "clientUniqueId", ack="auto")
        ws.send(sub)

    def on_message(self, ws: websocket, message):
        __LOGGER__.debug("Received the BLUETTI websocket message:\n %s", message)

        if not message or message == "\n":
            __LOGGER__.debug("Received heartbeat from server")
            return

        frame = stomper.Frame()
        frame.unpack(message)

        if frame.cmd == "ERROR":
            error = frame.headers['message'].replace("\\c", ":")
            error = json.loads(error)

            match error['msgCode']:
                case 400 | 403 | 600 | 805:
                    self.client.disconnect()
                    self.client.hass.bus.fire(EVENT_TOKEN_EXPIRED)
                    __LOGGER__.error("Websocket connection terminated: " + error['message'])
                case _:
                    raise ApplicationRuntimeException(msgCode=error['msgCode'], errMessage=error['message'])

        elif frame.cmd == "CONNECTED":
            heartbeat = frame.headers.get('heart-beat', '0,0')
            server_send, server_receive = map(int, heartbeat.split(','))
            __LOGGER__.info("Connect the BLUETTI WebSocket Server successfully.")
            __LOGGER__.debug(f"Server heartbeat configuration: send={server_send}, receive={server_receive}")

            # Heartbeat negotiation takes effect: The maximum value between the client's
            # proposal and the server's configuration is adopted (in accordance with the STOMP specification)
            client_propose_ms = (self.client.heartbeat_interval - 5) * 1000
            negotiated_ms = max(client_propose_ms, server_send, server_receive)
            self.client.heartbeat_interval = negotiated_ms // 1000
            __LOGGER__.debug(f"Heartbeat negotiated: {self.client.heartbeat_interval}s")

            # These codes were contributed by @chpego
            username = frame.headers.get('user-name')
            if not username:
                __LOGGER__.error("CONNECTED frame missing 'user-name' header, cannot subscribe.")
                return

            # start heartbeat thread
            self.client.start_heartbeat()

            # subscribe
            destination = f"/ws-subscribe/user/{username}/notify"
            self.__on_subscribe(ws, destination)

        elif frame.cmd == "MESSAGE":
            self.__callback(self.__handler, frame.body)
            # print(frame.body)

    @staticmethod
    def on_error(ws, error):
        """
        Handler when an error is raised.

        Args:
          error(str): Error received.

        """
        __LOGGER__.error("The BLUETTI WebSocket raised an error: %s", error)

    def on_close(self, ws, close_status_code, close_msg):
        print(f"WebSocket disconnected. Status code: {close_status_code}, Message: {close_msg}")
        # sleep 2 seconds
        time.sleep(2)
        __LOGGER__.debug(f"WebSocket 断开连接。状态码: {close_status_code}, 消息: {close_msg}")
        self.client.reconnect()
