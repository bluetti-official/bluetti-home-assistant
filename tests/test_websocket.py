"""Tests for api/websocket.py (StompClient / StompListener)."""

import json
from unittest.mock import MagicMock, patch

import pytest

from custom_components.bluetti.api.websocket import StompClient, StompListener
from custom_components.bluetti.application_exception import ApplicationRuntimeException
from custom_components.bluetti.const import EVENT_TOKEN_EXPIRED


def _client(handler=None) -> StompClient:
    hass = MagicMock()
    return StompClient("wss://gw.bluettipower.com/api/edgeiotgw/ws-coordination", "token", handler, hass)


# --- StompClient.__get_host -------------------------------------------------

@pytest.mark.parametrize(
    "url,expected",
    [
        ("wss://gw.bluettipower.com/api/foo", "gw.bluettipower.com"),
        ("wss://gw.bluettipower.com:443/api/foo", "gw.bluettipower.com"),
        ("ws://local-gw:18888/api/foo", "local-gw"),
    ],
)
def test_get_host_strips_port_and_path(url, expected):
    assert StompClient._StompClient__get_host(url) == expected


# --- StompClient.connect / _run_forever_safe --------------------------------

def test_connect_starts_daemon_thread():
    client = _client()
    with patch("custom_components.bluetti.api.websocket.websocket.WebSocketApp") as mock_app_cls, \
         patch("custom_components.bluetti.api.websocket.Thread") as mock_thread_cls:
        client.connect()

    assert client.running is True
    mock_app_cls.assert_called_once()
    mock_thread_cls.assert_called_once_with(
        target=client._run_forever_safe, daemon=True, name="bluetti-ws"
    )
    mock_thread_cls.return_value.start.assert_called_once()


def test_run_forever_safe_reconnects_on_crash_while_running():
    client = _client()
    client.websocket = MagicMock()
    client.websocket.run_forever.side_effect = RuntimeError("boom")
    client.running = True
    client.reconnect = MagicMock()

    client._run_forever_safe()

    client.reconnect.assert_called_once()


def test_run_forever_safe_does_not_reconnect_when_stopped():
    client = _client()
    client.websocket = MagicMock()
    client.websocket.run_forever.side_effect = RuntimeError("boom")
    client.running = False
    client.reconnect = MagicMock()

    client._run_forever_safe()

    client.reconnect.assert_not_called()


def test_run_forever_safe_normal_return_does_not_reconnect():
    client = _client()
    client.websocket = MagicMock()
    client.websocket.run_forever.return_value = None
    client.running = True
    client.reconnect = MagicMock()

    client._run_forever_safe()

    client.reconnect.assert_not_called()


# --- StompClient.disconnect --------------------------------------------------

def test_disconnect_closes_socket_and_joins_heartbeat_thread():
    client = _client()
    client.websocket = MagicMock()
    client.heartbeat_thread = MagicMock()
    client.heartbeat_thread.is_alive.return_value = True

    client.disconnect()

    assert client.running is False
    client.heartbeat_thread.join.assert_called_once_with(timeout=5)
    client.websocket.close.assert_called_once()


def test_disconnect_without_heartbeat_thread():
    client = _client()
    client.websocket = MagicMock()
    client.heartbeat_thread = None

    client.disconnect()

    client.websocket.close.assert_called_once()


# --- StompClient.__on_open / heartbeat --------------------------------------

def test_on_open_sends_connect_frame_and_starts_heartbeat():
    client = _client()
    client._start_heartbeat = MagicMock()
    ws = MagicMock()

    client._StompClient__on_open(ws)

    sent_frame = ws.send.call_args[0][0]
    assert sent_frame.startswith("CONNECT\n")
    assert "Authorization: token" in sent_frame
    client._start_heartbeat.assert_called_once()


def test_start_heartbeat_skips_when_already_alive():
    client = _client()
    client.heartbeat_thread = MagicMock()
    client.heartbeat_thread.is_alive.return_value = True

    with patch("custom_components.bluetti.api.websocket.threading.Thread") as mock_thread_cls:
        client._start_heartbeat()

    mock_thread_cls.assert_not_called()


def test_start_heartbeat_starts_new_thread_when_not_running():
    client = _client()
    client.heartbeat_thread = None

    with patch("custom_components.bluetti.api.websocket.threading.Thread") as mock_thread_cls:
        client._start_heartbeat()

    mock_thread_cls.assert_called_once()
    mock_thread_cls.return_value.start.assert_called_once()


def test_send_heartbeat_without_websocket_does_nothing():
    client = _client()
    client.running = True
    client.websocket = None

    client._send_heartbeat()  # loop condition false immediately, must not raise


def test_send_heartbeat_breaks_when_socket_not_connected():
    client = _client()
    client.running = True
    client.websocket = MagicMock()
    client.websocket.sock.connected = False

    with patch("custom_components.bluetti.api.websocket.time.sleep") as mock_sleep:
        client._send_heartbeat()

    client.websocket.send.assert_not_called()
    mock_sleep.assert_not_called()


def test_send_heartbeat_sends_and_sleeps_then_stops():
    client = _client()
    client.running = True
    client.heartbeat_interval = 0
    client.websocket = MagicMock()
    client.websocket.sock.connected = True

    def _stop_after_send(_msg):
        client.running = False

    client.websocket.send.side_effect = _stop_after_send

    with patch("custom_components.bluetti.api.websocket.time.sleep") as mock_sleep:
        client._send_heartbeat()

    client.websocket.send.assert_called_once_with("\n")
    mock_sleep.assert_called_once_with(0)


def test_send_heartbeat_breaks_on_send_error():
    client = _client()
    client.running = True
    client.websocket = MagicMock()
    client.websocket.sock.connected = True
    client.websocket.send.side_effect = RuntimeError("boom")

    with patch("custom_components.bluetti.api.websocket.time.sleep") as mock_sleep:
        client._send_heartbeat()  # must not raise

    mock_sleep.assert_not_called()


# --- StompClient.reconnect ---------------------------------------------------

def test_reconnect_when_running_backs_off_and_reconnects():
    client = _client()
    client.running = True
    client.reconnect_delay = 1
    client.max_reconnect_delay = 30
    client.connect = MagicMock()

    with patch("custom_components.bluetti.api.websocket.time.sleep") as mock_sleep:
        client.reconnect()

    mock_sleep.assert_called_once_with(1)
    assert client.reconnect_delay == 2
    client.connect.assert_called_once()


def test_reconnect_when_stopped_does_nothing():
    client = _client()
    client.running = False
    client.connect = MagicMock()

    with patch("custom_components.bluetti.api.websocket.time.sleep") as mock_sleep:
        client.reconnect()

    mock_sleep.assert_not_called()
    client.connect.assert_not_called()


# --- StompListener.__callback -------------------------------------------------

def test_listener_callback_invokes_handler():
    handler = MagicMock()
    listener = StompListener(MagicMock(), handler)

    listener._StompListener__callback(handler, "payload")

    handler.assert_called_once_with("payload")


def test_listener_callback_swallows_handler_errors():
    handler = MagicMock(side_effect=RuntimeError("boom"))
    listener = StompListener(MagicMock(), handler)

    listener._StompListener__callback(handler, "payload")  # must not raise


def test_listener_callback_does_nothing_without_handler():
    listener = StompListener(MagicMock(), None)
    listener._StompListener__callback(None, "payload")  # must not raise


# --- StompListener.on_message -------------------------------------------------

def test_on_message_ignores_empty_and_heartbeat():
    listener = StompListener(MagicMock())
    listener.on_message(MagicMock(), "")
    listener.on_message(MagicMock(), "\n")


def test_on_message_error_805_disconnects_and_fires_event():
    client = MagicMock()
    listener = StompListener(client)
    payload = json.dumps({"msgCode": 805, "message": "expired"}).replace(":", "\\c")
    raw = f"ERROR\nmessage:{payload}\n\n\x00"

    listener.on_message(MagicMock(), raw)

    client.disconnect.assert_called_once()
    client.hass.bus.fire.assert_called_once_with(EVENT_TOKEN_EXPIRED)


def test_on_message_error_other_code_raises():
    client = MagicMock()
    listener = StompListener(client)
    payload = json.dumps({"msgCode": 500, "message": "server error"}).replace(":", "\\c")
    raw = f"ERROR\nmessage:{payload}\n\n\x00"

    with pytest.raises(ApplicationRuntimeException) as exc_info:
        listener.on_message(MagicMock(), raw)

    assert exc_info.value.msgCode == 500


def test_on_message_connected_with_user_name_subscribes():
    listener = StompListener(MagicMock())
    ws = MagicMock()
    raw = "CONNECTED\nheart-beat:10000,10000\nuser-name:bob\n\n\x00"

    listener.on_message(ws, raw)

    sent = ws.send.call_args[0][0]
    assert "/ws-subscribe/user/bob/notify" in sent


def test_on_message_connected_without_user_name_logs_and_returns():
    listener = StompListener(MagicMock())
    ws = MagicMock()
    raw = "CONNECTED\nheart-beat:10000,10000\n\n\x00"

    listener.on_message(ws, raw)

    ws.send.assert_not_called()


def test_on_message_message_frame_invokes_handler():
    handler = MagicMock()
    listener = StompListener(MagicMock(), handler)
    raw = "MESSAGE\ndestination:/topic\n\nhello body\x00"

    listener.on_message(MagicMock(), raw)

    handler.assert_called_once_with("hello body")


# --- StompListener.on_error / on_close ---------------------------------------

def test_on_error_logs_without_raising():
    StompListener.on_error(MagicMock(), "boom")


def test_on_close_triggers_reconnect():
    client = MagicMock()
    listener = StompListener(client)

    listener.on_close(MagicMock(), 1006, "closed")

    client.reconnect.assert_called_once()
