"""Keep the BLUETTI sign-in alive without a person.

Facts this is built on (measured on a live install, 2026-10):

* A session ends 31 days after the interactive sign-in. Refresh-token grants
  succeed and report a fresh ``expires_in``, but the refreshed token dies at the
  original 31-day mark, to the minute. So ``expires_at`` cannot be trusted and a
  refresh cannot keep the integration alive.
* The cloud also rejects tokens early with msgCode 805 (or 400/403/600 on the
  websocket); a refresh-token grant does recover those.

So this owner tracks ``session_started_at`` itself and, if the user has stored
credentials, signs in again at day 28. Early rejections get a refresh first and
a sign-in if that fails. Only when no unattended route works does it raise the
"OAuth Expired" notification asking the user to reconfigure.

The ProductClient and StompClient are built with a static access token, so every
token change ends in a (deduplicated, rate-limited) reload of the entry.
"""
from __future__ import annotations

import logging
import time
from datetime import timedelta
from typing import Any, Awaitable, Callable

from homeassistant.components import persistent_notification
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_time_interval

from .const import DOMAIN, EVENT_TOKEN_EXPIRED, NOTIFY_ID_TOKEN_EXPIRED
from .sso_login import SsoLoginError, async_login

_LOGGER = logging.getLogger(__name__)

SESSION_LIFETIME = timedelta(days=31)
RELOGIN_AFTER = timedelta(days=28)
CHECK_INTERVAL = timedelta(hours=1)
REJECTION_FLOOR_S = 300
RELOAD_FLOOR_S = 300

# Entry data keys owned here.
KEY_SESSION_STARTED_AT = "session_started_at"
KEY_LAST_TOKEN_REFRESH = "last_token_refresh"
KEY_CREDENTIALS = "sso_credentials"

# Survives entry reloads, which is what a floor across reloads needs.
_last_reload: dict[str, float] = {}


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
        self._last_rejection = 0.0
        entry.async_on_unload(hass.bus.async_listen(EVENT_TOKEN_EXPIRED, self.on_token_expired_event))

    # -- lifecycle ---------------------------------------------------------

    def start_token_check(self) -> None:
        persistent_notification.async_dismiss(self.hass, notification_id=NOTIFY_ID_TOKEN_EXPIRED)
        if KEY_SESSION_STARTED_AT not in self.entry.data:
            started = seed_session_started_at(dict(self.entry.data))
            if started is not None:
                self._update_data({KEY_SESSION_STARTED_AT: started})
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
        """The cloud rejected the token (805 et al.): refresh, then sign in, then ask."""
        current = self._clock()
        if current - self._last_rejection < REJECTION_FLOOR_S:
            return
        self._last_rejection = current
        try:
            new_token = await self.oAuth2Session.implementation.async_refresh_token(self.oAuth2Session.token)
        except Exception as err:  # noqa: BLE001 - any failure means try the next route
            _LOGGER.warning("BLUETTI token refresh after rejection failed (%s); signing in", type(err).__name__)
            await self._async_relogin_or_notify("token rejected and refresh failed")
            return
        self._update_data({"token": new_token, KEY_LAST_TOKEN_REFRESH: current})
        _LOGGER.info("BLUETTI token refreshed after the cloud rejected it")
        self._schedule_reload()

    # -- routes ------------------------------------------------------------

    async def _async_relogin_or_notify(self, reason: str) -> None:
        creds = self.entry.data.get(KEY_CREDENTIALS)
        if not creds:
            _LOGGER.warning("BLUETTI session needs a new sign-in (%s) and no credentials are stored", reason)
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
        except SsoLoginError as err:
            _LOGGER.error("BLUETTI unattended sign-in failed (%s): %s", reason, err)
            self.send_expired_notification()
            return
        current = self._clock()
        self._update_data({"token": token, KEY_SESSION_STARTED_AT: current, KEY_LAST_TOKEN_REFRESH: current})
        _LOGGER.info("BLUETTI signed in again unattended (%s)", reason)
        persistent_notification.async_dismiss(self.hass, notification_id=NOTIFY_ID_TOKEN_EXPIRED)
        self._schedule_reload()

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

    # -- helpers -----------------------------------------------------------

    def _update_data(self, changes: dict[str, Any]) -> None:
        self.hass.config_entries.async_update_entry(self.entry, data={**self.entry.data, **changes})

    def _schedule_reload(self) -> None:
        """The API clients hold a static token, so a new token needs a reload; at most one per 5 min."""
        current = self._clock()
        if current - _last_reload.get(self.entry.entry_id, 0.0) < RELOAD_FLOOR_S:
            _LOGGER.debug("BLUETTI reload suppressed by the %s s floor", RELOAD_FLOOR_S)
            return
        _last_reload[self.entry.entry_id] = current
        self.hass.config_entries.async_schedule_reload(self.entry.entry_id)
