"""Sign in to the BLUETTI SSO without a browser.

BLUETTI ends an OAuth session 31 days after the interactive sign-in, and a
refresh-token grant does not extend it: the refreshed token dies at the same
moment. Unattended operation therefore needs a fresh sign-in before day 31.

This drives the same form the SSO login page posts
(``/static/script/login-oauth.js``): a multipart POST to
``/oauth2/authentication`` answering ``{"msgCode": 0, "data": <redirect URL>}``,
whose ``code`` is then exchanged by Home Assistant's own OAuth implementation
exactly as the interactive flow does. The form is undocumented; any change to
it surfaces as ``SsoLoginError`` and the caller falls back to asking the user.

Only the SHA-256 of the password is needed by the form (``encryptedpwd``); the
plaintext field is sent empty unless the caller supplies it.
"""
from __future__ import annotations

import hashlib
import secrets
import time
from typing import Any
from urllib.parse import parse_qs, urlsplit

import aiohttp

LOGIN_PATH = "/oauth2/login"
AUTHENTICATION_PATH = "/oauth2/authentication"
REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=30)


class SsoLoginError(Exception):
    """The sign-in did not produce a token. ``refused`` is True only when the SSO itself said no."""

    def __init__(self, message: str, refused: bool = False) -> None:
        super().__init__(message)
        self.refused = refused


def password_digest(password: str) -> str:
    """Return the digest the SSO form sends as ``encryptedpwd``."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest().upper()


async def async_login(
    sso_base: str,
    implementation: Any,
    username: str,
    password_sha256: str,
    password: str = "",
    session: aiohttp.ClientSession | None = None,
) -> dict[str, Any]:
    """Sign in and return a token dict shaped like the interactive flow's.

    ``implementation`` is the config entry's OAuth2 implementation; its
    ``client_id`` and ``redirect_uri`` are the ones registered with the SSO, and
    its ``async_resolve_external_data`` performs the code exchange.
    """
    try:
        # Raises RuntimeError outside a request when the `my` integration is not
        # loaded - the case for a background renewal on such an install.
        redirect_uri = implementation.redirect_uri
    except RuntimeError as err:
        raise SsoLoginError("no redirect URI available outside a browser request") from err
    state = secrets.token_urlsafe(16)
    query = {
        "response_type": "code",
        "client_id": implementation.client_id,
        "redirect_uri": redirect_uri,
        "state": state,
    }
    fields = {
        **query,
        "scope": "",
        "encryptedpwd": password_sha256,
        "authType": "ACCOUNT",
        "phoneCountry": "",
        "username": username,
        "accountpwd": password,
    }

    # A private cookie jar: the login page may set a session cookie that the
    # authentication POST expects, and it must not leak into HA's shared session.
    own_session = session is None
    if own_session:
        session = aiohttp.ClientSession(cookie_jar=aiohttp.CookieJar(), timeout=REQUEST_TIMEOUT)
    try:
        async with session.get(sso_base + LOGIN_PATH, params=query) as resp:
            await resp.read()
        form = aiohttp.FormData()
        for key, value in fields.items():
            form.add_field(key, value)
        async with session.post(sso_base + AUTHENTICATION_PATH, data=form) as resp:
            if resp.status != 200:
                raise SsoLoginError(f"authentication answered HTTP {resp.status}")
            body = await resp.json(content_type=None)
    except aiohttp.ClientError as err:
        raise SsoLoginError(f"SSO unreachable: {type(err).__name__}") from err
    finally:
        if own_session:
            await session.close()

    if not isinstance(body, dict) or body.get("msgCode") != 0:
        code = body.get("msgCode") if isinstance(body, dict) else None
        message = body.get("message") if isinstance(body, dict) else None
        raise SsoLoginError(f"sign-in refused: msgCode={code} {message or ''}".strip(), refused=code is not None)

    params = parse_qs(urlsplit(str(body.get("data", ""))).query)
    if params.get("state", [state])[0] != state:
        raise SsoLoginError("sign-in redirect carried a different state")
    if not params.get("code"):
        raise SsoLoginError("sign-in redirect carried no code")

    try:
        token = await implementation.async_resolve_external_data(
            {"code": params["code"][0], "state": {"redirect_uri": redirect_uri}}
        )
        # Same normalisation as AbstractOAuth2FlowHandler.async_step_creation.
        token["expires_in"] = int(token["expires_in"])
    except (aiohttp.ClientError, KeyError, TypeError, ValueError) as err:
        raise SsoLoginError(f"code exchange failed: {type(err).__name__}") from err
    token["expires_at"] = time.time() + token["expires_in"]
    return token
