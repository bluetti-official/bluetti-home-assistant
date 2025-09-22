import logging
import json
from threading import Thread
from typing import Callable

import stomper
import websocket

from ..application_exception import ApplicationRuntimeException

__LOGGER__ = logging.getLogger(__name__)


class StompClient(object):
    def __init__(self, url: str, access_token: str, handler: Callable[[str], None] = None):
        self.__url = url + "/websocket"
        self.__headers = {
            "Host": self.__get_host(url),
            "Authorization": access_token
        }
        self.listener = StompListener(handler)
        self.websocket = None

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

        stomp_trace = False
        websocket.enableTrace(stomp_trace)

        __LOGGER__.info("Start to connect the BLUETTI WebSocket Server.")
        __LOGGER__.info("Stomp client trace enable: %s", stomp_trace)

        self.websocket = websocket.WebSocketApp(self.__url,
                                                on_message=self.listener.on_message,
                                                on_error=self.listener.on_error)
        # bind the `on_open` function
        self.websocket.on_open = self.__on_open

        # Run until interruption to client or server terminates connection.
        Thread(target=self.websocket.run_forever).start()

    def disconnect(self):
        self.websocket.close()

    def __on_open(self, ws):
        # Initial CONNECT required to initialize the server's client registries.
        connect = ("CONNECT\n"
                   "accept-version:1.0,1.1,2.0\n"
                   "Host:" + self.__headers["Host"] + "\n"
                   "Authorization: " + self.__headers["Authorization"] + "\n"
                   "\n\x00\n")

        __LOGGER__.info("Connect the BLUETTI WebSocket Server successfully.")
        ws.send(connect)


class StompListener:
    def __init__(self, handler: Callable[[str], None] = None):
        self.__handler = handler

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

        frame = stomper.Frame()
        frame.unpack(message)

        if frame.cmd == "ERROR":
            error = frame.headers['message'].replace("\\c", ":")
            error = json.loads(error)
            raise ApplicationRuntimeException(msgCode=error['msgCode'], errMessage=error['message'])
        elif frame.cmd == "CONNECTED":
            destination = "/ws-subscribe/user/" + frame.headers['user-name'] + "/notify"
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
        print("The Error is:- " + error)
