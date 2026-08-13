"""Tests for the Bluetti base API client (api/bluetti.py) via ProductClient."""

from unittest.mock import MagicMock

import pytest

from custom_components.bluetti.api.bluetti import (
    APPLICATION_PROFILE,
    EU_APPLICATION_PROFILE,
    US_APPLICATION_PROFILE,
    get_region_profile,
)
from custom_components.bluetti.api.product_client import ProductClient
from custom_components.bluetti.application_exception import ApplicationRuntimeException
from custom_components.bluetti.const import AUTH_DOMAIN_EU, AUTH_DOMAIN_US, DOMAIN, EVENT_TOKEN_EXPIRED


class _FakeResponse:
    def __init__(self, status=200, content_type="application/json", json_data=None, text_data=""):
        self.status = status
        self.ok = 200 <= status < 400
        self.content_type = content_type
        self.url = "https://gw.bluettipower.com/fake"
        self._json_data = json_data
        self._text_data = text_data

    async def json(self):
        return self._json_data

    async def text(self):
        return self._text_data


class _FakeRequestContextManager:
    def __init__(self, response):
        self._response = response

    async def __aenter__(self):
        return self._response

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakeSession:
    def __init__(self, response):
        self._response = response
        self.calls = []

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        return _FakeRequestContextManager(self._response)


@pytest.fixture(autouse=True)
def _application_profile_config():
    """Ensure APPLICATION_PROFILE.config is populated for every test in this module."""
    original = APPLICATION_PROFILE.config
    APPLICATION_PROFILE.config = {"server": {"gateway": "https://gw.bluettipower.com"}}
    yield
    APPLICATION_PROFILE.config = original


def _client(session) -> ProductClient:
    hass = MagicMock()
    return ProductClient(session, "test-token", hass), hass


async def test_get_user_products_success():
    response = _FakeResponse(json_data={"msgId": "1", "msgCode": 0, "data": []})
    session = _FakeSession(response)
    client, _hass = _client(session)

    result = await client.get_user_products()

    assert result.is_ok()
    assert result.data == []
    # GET requests must not send a body.
    method, url, kwargs = session.calls[0]
    assert kwargs["json"] is None


async def test_get_device_status_strips_none_params():
    response = _FakeResponse(json_data={"msgId": "1", "msgCode": 0, "data": []})
    session = _FakeSession(response)
    client, _hass = _client(session)

    await client.get_device_status(sns=None)

    _method, _url, kwargs = session.calls[0]
    assert kwargs["params"] == {}


async def test_control_device_strips_none_body_values():
    response = _FakeResponse(json_data={"msgId": "1", "msgCode": 0, "data": {}})
    session = _FakeSession(response)
    client, _hass = _client(session)

    await client.control_device({"sn": "SN1", "fnCode": "AC", "fnValue": "1", "extra": None})

    _method, _url, kwargs = session.calls[0]
    assert kwargs["json"] == {"sn": "SN1", "fnCode": "AC", "fnValue": "1"}
    assert kwargs["headers"]["Content-Type"] == "application/json"


async def test_request_fires_token_expired_event_on_805():
    response = _FakeResponse(json_data={"msgId": "1", "msgCode": 805, "data": None})
    session = _FakeSession(response)
    client, hass = _client(session)

    await client.get_user_products()

    hass.bus.fire.assert_called_once_with(EVENT_TOKEN_EXPIRED)


async def test_request_raises_on_non_ok_status():
    response = _FakeResponse(status=401, text_data="unauthorized")
    session = _FakeSession(response)
    client, _hass = _client(session)

    with pytest.raises(ApplicationRuntimeException) as exc_info:
        await client.get_user_products()

    assert exc_info.value.msgCode == 401
    assert exc_info.value.data == "unauthorized"


async def test_request_returns_raw_text_for_non_json_response():
    response = _FakeResponse(content_type="text/plain", text_data="plain response")
    session = _FakeSession(response)
    client, _hass = _client(session)

    result = await client.get_user_products()

    assert result == "plain response"


async def test_bind_devices_posts_payload():
    response = _FakeResponse(json_data={"msgId": "1", "msgCode": 0, "data": {}})
    session = _FakeSession(response)
    client, _hass = _client(session)

    await client.bind_devices({"bindSnList": ["SN1"]})

    _method, url, kwargs = session.calls[0]
    assert url.endswith("/api/bluiotdata/ha/v1/bindDevices")
    assert kwargs["json"] == {"bindSnList": ["SN1"]}


async def test_explicit_gateway_url_overrides_default_profile():
    """A region-specific gateway_url (e.g. US) must be used instead of the
    globally configured one - this is what makes issue #121's region
    selector actually take effect for API calls."""
    response = _FakeResponse(json_data={"msgId": "1", "msgCode": 0, "data": []})
    session = _FakeSession(response)
    hass = MagicMock()
    client = ProductClient(session, "test-token", hass, gateway_url="https://gwus.bluettipower.com")

    await client.get_user_products()

    _method, url, _kwargs = session.calls[0]
    assert url.startswith("https://gwus.bluettipower.com")


def test_get_region_profile_default_is_global():
    assert get_region_profile(DOMAIN) is APPLICATION_PROFILE
    assert get_region_profile(None) is APPLICATION_PROFILE
    assert get_region_profile("something-unknown") is APPLICATION_PROFILE


def test_get_region_profile_us():
    assert get_region_profile(AUTH_DOMAIN_US) is US_APPLICATION_PROFILE


def test_get_region_profile_eu():
    assert get_region_profile(AUTH_DOMAIN_EU) is EU_APPLICATION_PROFILE


async def test_eu_profile_has_distinct_gateway_but_shared_sso(hass):
    """The EU fix for issue #72 only swaps the data gateway; the SSO login
    endpoint must stay the same as the default/global profile."""
    await EU_APPLICATION_PROFILE.load_config(hass)
    await APPLICATION_PROFILE.load_config(hass)

    assert EU_APPLICATION_PROFILE.config["server"]["gateway"] != APPLICATION_PROFILE.config["server"]["gateway"]
    assert EU_APPLICATION_PROFILE.config["server"]["sso"] == APPLICATION_PROFILE.config["server"]["sso"]
    assert EU_APPLICATION_PROFILE.config["server"]["gateway"] == "https://gwde.bluettipower.com"
