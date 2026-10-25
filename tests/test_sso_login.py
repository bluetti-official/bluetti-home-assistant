"""The unattended SSO sign-in: what it posts and how it reads the answer."""
import hashlib
import re
from unittest.mock import AsyncMock

import pytest
from aioresponses import aioresponses

from conftest import sso_login

SSO = "https://sso.example"
AUTH_URL = SSO + sso_login.AUTHENTICATION_PATH
LOGIN_RE = re.compile(re.escape(SSO + sso_login.LOGIN_PATH) + r".*")
REDIRECT = "https://my.home-assistant.io/redirect/oauth"


def implementation():
    impl = AsyncMock()
    impl.client_id = "HomeAssistant"
    impl.redirect_uri = REDIRECT
    impl.async_resolve_external_data.return_value = {"access_token": "a", "refresh_token": "r", "expires_in": "2678400"}
    return impl


def posted_fields(mock, url):
    form = mock.requests[("POST", __import__("yarl").URL(url))][0].kwargs["data"]
    return {f[0]["name"]: f[2] for f in form._fields}


def test_password_digest_matches_the_login_page():
    # login-oauth.js: CryptoJS.SHA256(pwd).toString().toUpperCase()
    assert sso_login.password_digest("pa55") == hashlib.sha256(b"pa55").hexdigest().upper()


@pytest.mark.asyncio
async def test_sign_in_posts_the_form_and_exchanges_the_code():
    impl = implementation()
    with aioresponses() as m:
        m.get(LOGIN_RE, status=200, body="<html/>")
        m.post(AUTH_URL, payload={"msgCode": 0, "data": REDIRECT + "?code=abc"})
        token = await sso_login.async_login(SSO, impl, "me@example.com", "DIGEST")
        fields = posted_fields(m, AUTH_URL)
    assert fields["username"] == "me@example.com"
    assert fields["encryptedpwd"] == "DIGEST"
    assert fields["accountpwd"] == ""
    assert fields["client_id"] == "HomeAssistant" and fields["redirect_uri"] == REDIRECT
    impl.async_resolve_external_data.assert_awaited_once_with({"code": "abc", "state": {"redirect_uri": REDIRECT}})
    assert token["expires_in"] == 2678400 and token["expires_at"] > 0


@pytest.mark.asyncio
async def test_a_failed_code_exchange_is_an_sso_login_error():
    impl = implementation()
    impl.async_resolve_external_data.side_effect = KeyError("expires_in")
    with aioresponses() as m:
        m.get(LOGIN_RE, status=200, body="")
        m.post(AUTH_URL, payload={"msgCode": 0, "data": REDIRECT + "?code=abc"})
        with pytest.raises(sso_login.SsoLoginError, match="code exchange failed") as info:
            await sso_login.async_login(SSO, impl, "me@example.com", "DIGEST")
    assert info.value.refused is False


@pytest.mark.asyncio
async def test_no_redirect_uri_outside_a_request_is_an_sso_login_error():
    impl = implementation()
    type(impl).redirect_uri = property(lambda self: (_ for _ in ()).throw(RuntimeError("No current request")))
    with pytest.raises(sso_login.SsoLoginError, match="no redirect URI"):
        await sso_login.async_login(SSO, impl, "me@example.com", "DIGEST")


@pytest.mark.asyncio
async def test_only_an_sso_refusal_is_marked_refused():
    impl = implementation()
    with aioresponses() as m:
        m.get(LOGIN_RE, status=200, body="")
        m.post(AUTH_URL, payload={"msgCode": 1012, "message": "wrong password"})
        with pytest.raises(sso_login.SsoLoginError) as info:
            await sso_login.async_login(SSO, impl, "me@example.com", "DIGEST")
    assert info.value.refused is True


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status,payload,match",
    [
        (200, {"msgCode": 1012, "message": "wrong password"}, "msgCode=1012"),
        (200, {"msgCode": 0, "data": REDIRECT + "?state=x"}, "no code|different state"),
        (200, {"msgCode": 0, "data": REDIRECT + "?code=abc&state=forged"}, "different state"),
        (500, {"msgCode": 0}, "HTTP 500"),
    ],
)
async def test_refusals_raise_and_never_exchange(status, payload, match):
    impl = implementation()
    with aioresponses() as m:
        m.get(LOGIN_RE, status=200, body="")
        m.post(AUTH_URL, status=status, payload=payload)
        with pytest.raises(sso_login.SsoLoginError, match=match):
            await sso_login.async_login(SSO, impl, "me@example.com", "DIGEST")
    impl.async_resolve_external_data.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("post_kwargs", [{"body": "<html>maintenance</html>"}, {"exception": TimeoutError()}])
async def test_unreadable_or_slow_answers_raise(post_kwargs):
    impl = implementation()
    with aioresponses() as m:
        m.get(LOGIN_RE, status=200, body="")
        m.post(AUTH_URL, status=200, **post_kwargs)
        with pytest.raises(sso_login.SsoLoginError, match="unreachable or unreadable"):
            await sso_login.async_login(SSO, impl, "me@example.com", "DIGEST")
