"""Keep the BLUETTI sign-in alive without a person.

Facts this is built on (measured on a live install, 2026-10):

* A session ends 31 days after the interactive sign-in. Refresh-token grants
  succeed and report a fresh ``expires_in``, but the refreshed token dies at the
  original 31-day mark, to the minute. So ``expires_at`` cannot be trusted and a
  refresh cannot keep the integration alive.
* The cloud also rejects tokens early with msgCode 805 (or 400/403/600 on the
  websocket); a refresh-token grant recovers some of those.

So this owner tracks ``session_started_at`` itself and, if the user has stored
credentials, signs in again at day 28. A rejected token gets a refresh first;
a rejection that comes back soon after a refresh gets a sign-in. Only when no
unattended route works does it raise the "OAuth Expired" notification asking
the user to reconfigure.

Every new token, from whatever route, goes through ``record_new_session`` or
``record_refreshed_token``. The ProductClient and StompClient are built with a
static access token, so each token change ends in a reload of the entry, at
most one per ``RELOAD_FLOOR_S`` and deferred (not dropped) inside the floor.
"""
from __future__ import annotations

import hashlib
import logging
import time
from datetime import timedelta
from typing import Any, Awaitable, Callable

from homeassistant.components import persistent_notification
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_call_later, async_track_time_interval

from .const import DOMAIN, EVENT_TOKEN_EXPIRED, NOTIFY_ID_TOKEN_EXPIRED
from .sso_login import SsoLoginError, async_login

_LOGGER = logging.getLogger(__name__)

SESSION_LIFETIME = timedelta(days=31)
RELOGIN_AFTER = timedelta(days=28)
CHECK_INTERVAL = timedelta(hours=1)
REJECTION_FLOOR_S = 300
REFRESH_DID_NOT_HELP_S = 1800
RELOAD_FLOOR_S = 300
LOGIN_FAILURE_BACKOFF_S = 6 * 3600

# Entry data keys owned here.
KEY_SESSION_STARTED_AT = "session_started_at"
KEY_LAST_TOKEN_REFRESH = "last_token_refresh"
KEY_CREDENTIALS = "sso_credentials"

_STATE_KEY = f"{DOMAIN}_token_state"


def session_expires_at(entry_data: dict[str, Any]) -> float | None:
    """Server-side end of the current session, as a POSIX timestamp."""
    started = entry_data.get(KEY_SESSION_STARTED_AT)
    if started is None:
        return None
    return float(started) + SESSION_LIFETIME.total_seconds()


def seed_session_started_at(entry_data: dict[str, Any]) -> float | None:
    """Best estimate of when the current session began, for entries made before this owner existed."""
    started = entry_data.get(KEY_SESSION_STARTED_AT)
    if started is not None:
        return float(started)
    expires_at = (entry_data.get("token") or {}).get("expires_at")
    if expires_at is None:
        return None
    issued = float(expires_at) - SESSION_LIFETIME.total_seconds()
    refreshed = entry_data.get(KEY_LAST_TOKEN_REFRESH)
    if refreshed is not None and float(refreshed) >= issued - 60:
        # The stored token came from a refresh, which reports a fresh 31 d without
        # extending the session. The real start is unknown but no later than the
        # refresh; assume the earliest it could be, so the sign-in comes early.
        return float(refreshed) - SESSION_LIFETIME.total_seconds()
    # A token from an interactive sign-in: exact.
    return issued


def new_session_data(token: dict[str, Any], now: float) -> dict[str, Any]:
    """Entry-data fields for a token from a fresh sign-in (interactive or unattended)."""
    return {"token": token, KEY_SESSION_STARTED_AT: now, KEY_LAST_TOKEN_REFRESH: now}


def record_new_session(
    hass: HomeAssistant,
    entry: Any,
    token: dict[str, Any],
    *,
    credentials: dict[str, Any] | None = None,
    now: float | None = None,
) -> None:
    """Store a token from a fresh sign-in, clear any expiry notice, and reload the entry."""
    now = time.time() if now is None else now
    changes = new_session_data(token, now)
    if credentials is not None:
        changes[KEY_CREDENTIALS] = credentials
    hass.config_entries.async_update_entry(entry, data={**entry.data, **changes})
    state = _state(hass, entry)
    state.pop("login_failed", None)
    state.pop("refreshed_at", None)
    persistent_notification.async_dismiss(hass, notification_id=NOTIFY_ID_TOKEN_EXPIRED)
    schedule_reload(hass, entry, now)


def record_refreshed_token(hass: HomeAssistant, entry: Any, token: dict[str, Any], now: float) -> None:
    """Store a refreshed token. The session clock does not move: a refresh does not extend the session."""
    hass.config_entries.async_update_entry(entry, data={**entry.data, "token": token, KEY_LAST_TOKEN_REFRESH: now})
    _state(hass, entry)["refreshed_at"] = now
    started = entry.data.get(KEY_SESSION_STARTED_AT)
    if started is not None and now - float(started) < RELOGIN_AFTER.total_seconds():
        # Past day 28 a refresh cannot rescue the session, so an open notice stays open.
        persistent_notification.async_dismiss(hass, notification_id=NOTIFY_ID_TOKEN_EXPIRED)
    schedule_reload(hass, entry, now)


def schedule_reload(hass: HomeAssistant, entry: Any, now: float) -> None:
    """Reload the entry so its clients pick up the new token: at most one per floor, deferred inside it."""
    state = _state(hass, entry)
    if state.get("reload_pending"):
        return
    wait = state.get("last_reload", float("-inf")) + RELOAD_FLOOR_S - now
    if wait <= 0:
        state["last_reload"] = now
        hass.config_entries.async_schedule_reload(entry.entry_id)
        return

    # @callback keeps this on the event loop; a plain function here would be run
    # in an executor thread, where async_schedule_reload must not be called.
    @callback
    def _deferred(_now: Any) -> None:
        state["reload_pending"] = False
        state["last_reload"] = time.time()
        hass.config_entries.async_schedule_reload(entry.entry_id)

    state["reload_pending"] = True
    # Deliberately not bound to the entry's unload: the reload must still happen if
    # the entry reloads for another reason in between (async_schedule_reload dedupes).
    async_call_later(hass, wait, _deferred)


def _state(hass: HomeAssistant, entry: Any) -> dict[str, Any]:
    """Per-entry state that must survive the entry's own reloads."""
    return hass.data.setdefault(_STATE_KEY, {}).setdefault(entry.entry_id, {})


def _credentials_fingerprint(creds: dict[str, Any]) -> str:
    return hashlib.sha256(f"{creds.get('username')}\0{creds.get('password_sha256')}".encode()).hexdigest()


class AuthTokenRefresh:
    """Owns the entry's token: early-rejection recovery, day-28 sign-in, and the last-resort notification."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: Any,
        oauth_session: Any,
        sso_base: str,
        login: Callable[..., Awaitable[dict[str, Any]]] = async_login,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.hass = hass
        self.entry = entry
        self.oAuth2Session = oauth_session
        self._sso_base = sso_base
        self._login = login
        self._clock = clock
        entry.async_on_unload(hass.bus.async_listen(EVENT_TOKEN_EXPIRED, self.on_token_expired_event))

    def start_token_check(self) -> None:
        if KEY_SESSION_STARTED_AT not in self.entry.data:
            started = seed_session_started_at(dict(self.entry.data))
            if started is not None:
                self.hass.config_entries.async_update_entry(
                    self.entry, data={**self.entry.data, KEY_SESSION_STARTED_AT: started}
                )
        self.entry.async_on_unload(
            async_track_time_interval(self.hass, self.async_check_token_expiry, CHECK_INTERVAL)
        )
        self.hass.async_create_task(self.async_check_token_expiry())

    async def async_check_token_expiry(self, now: Any = None) -> None:
        """Hourly: sign in again before the session's 31-day end."""
        started = self.entry.data.get(KEY_SESSION_STARTED_AT)
        current = self._clock()
        if started is not None and current - float(started) >= RELOGIN_AFTER.total_seconds():
            await self._async_relogin_or_notify("session is %.1f days old" % ((current - float(started)) / 86400))
            return
        expires_at = (self.oAuth2Session.token or {}).get("expires_at")
        if expires_at is not None and float(expires_at) - 30 <= current:
            await self._async_relogin_or_notify("access token expired")

    async def on_token_expired_event(self, event: Any = None) -> None:
        """The cloud rejected the token (805 et al.): refresh; if a refresh recently failed to help, sign in."""
        state = _state(self.hass, self.entry)
        current = self._clock()
        if current - state.get("last_rejection", float("-inf")) < REJECTION_FLOOR_S:
            return
        state["last_rejection"] = current
        if current - state.get("refreshed_at", float("-inf")) < REFRESH_DID_NOT_HELP_S:
            await self._async_relogin_or_notify("token rejected again soon after a refresh")
            return
        try:
            new_token = await self.oAuth2Session.implementation.async_refresh_token(self.oAuth2Session.token)
        except Exception as err:  # noqa: BLE001 - any failure means try the next route
            _LOGGER.warning("BLUETTI token refresh after rejection failed (%s); signing in", type(err).__name__)
            await self._async_relogin_or_notify("token rejected and refresh failed")
            return
        _LOGGER.info("BLUETTI token refreshed after the cloud rejected it")
        record_refreshed_token(self.hass, self.entry, new_token, current)

    async def _async_relogin_or_notify(self, reason: str) -> None:
        creds = self.entry.data.get(KEY_CREDENTIALS)
        if not creds:
            _LOGGER.warning("BLUETTI session needs a new sign-in (%s) and no credentials are stored", reason)
            self.send_expired_notification()
            return
        state = _state(self.hass, self.entry)
        current = self._clock()
        failed = state.get("login_failed")
        fingerprint = _credentials_fingerprint(creds)
        if failed and failed["creds"] == fingerprint and current - failed["at"] < LOGIN_FAILURE_BACKOFF_S:
            # Same credentials failed recently: do not hammer the account into a lockout.
            self.send_expired_notification()
            return
        try:
            token = await self._login(
                self._sso_base,
                self.oAuth2Session.implementation,
                creds["username"],
                creds["password_sha256"],
                creds.get("password", ""),
            )
        except Exception as err:  # noqa: BLE001 - every failure must reach the user, never die in a timer
            detail = str(err) if isinstance(err, SsoLoginError) else type(err).__name__
            _LOGGER.error("BLUETTI unattended sign-in failed (%s): %s", reason, detail)
            state["login_failed"] = {"creds": fingerprint, "at": current}
            self.send_expired_notification()
            return
        _LOGGER.info("BLUETTI signed in again unattended (%s)", reason)
        record_new_session(self.hass, self.entry, token, now=current)

    def send_expired_notification(self) -> None:
        reauth_url = f"/config/integrations/integration/{DOMAIN}"
        persistent_notification.async_create(
            self.hass,
            "Your BLUETTI sign-in has expired and could not be renewed automatically.\n"
            f"Go to the **[integration settings]({reauth_url})**, click Reconfigure and sign in. "
            "Storing your BLUETTI credentials in the integration options lets it renew by itself.",
            title="OAuth Expired",
            notification_id=NOTIFY_ID_TOKEN_EXPIRED,
        )
