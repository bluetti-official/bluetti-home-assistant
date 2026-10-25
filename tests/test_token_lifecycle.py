"""The token owner: day-28 sign-in, rejection recovery, the reload floor, seeding."""
from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed

from conftest import sso_login, token_lifecycle as tl

DAY = 86400.0
T0 = 1_790_000_000.0  # session start used throughout
CREDS = {"username": "me@example.com", "password_sha256": "DIGEST"}


class Clock:
    def __init__(self, t):
        self.t = t

    def __call__(self):
        return self.t


def make(hass, *, age_days, creds=True, login=None, refresh=None):
    data = {"token": {"access_token": "old", "expires_at": T0 + 31 * DAY}, tl.KEY_SESSION_STARTED_AT: T0}
    if creds:
        data[tl.KEY_CREDENTIALS] = dict(CREDS)
    entry = MockConfigEntry(domain="bluetti", data=data)
    entry.add_to_hass(hass)
    session = MagicMock()
    session.token = data["token"]
    session.implementation.async_refresh_token = refresh or AsyncMock(return_value={"access_token": "refreshed"})
    login = login or AsyncMock(return_value={"access_token": "new", "expires_at": T0 + 59 * DAY})
    clock = Clock(T0 + age_days * DAY)
    owner = tl.AuthTokenRefresh(hass, entry, session, "https://sso.example", login=login, clock=clock)
    return entry, owner, login, session, clock


@pytest.fixture
def reload_spy(hass):
    with patch.object(hass.config_entries, "async_schedule_reload") as spy:
        yield spy


@pytest.fixture
def notify_spy():
    with patch.object(tl.persistent_notification, "async_create") as spy:
        yield spy


# -- day 28 ------------------------------------------------------------------

async def test_no_sign_in_before_day_28(hass, reload_spy, notify_spy):
    entry, owner, login, *_ = make(hass, age_days=27.9)
    await owner.async_check_token_expiry()
    login.assert_not_awaited()
    reload_spy.assert_not_called()
    notify_spy.assert_not_called()


async def test_day_28_signs_in_once_and_restarts_the_session_clock(hass, reload_spy, notify_spy):
    entry, owner, login, _, clock = make(hass, age_days=28.0)
    await owner.async_check_token_expiry()
    login.assert_awaited_once()
    assert login.await_args.args[2:4] == ("me@example.com", "DIGEST")
    assert entry.data["token"]["access_token"] == "new"
    assert entry.data[tl.KEY_SESSION_STARTED_AT] == clock.t
    assert entry.data[tl.KEY_CREDENTIALS] == CREDS
    reload_spy.assert_called_once_with(entry.entry_id)
    notify_spy.assert_not_called()
    clock.t += 3600
    await owner.async_check_token_expiry()
    login.assert_awaited_once()


async def test_day_28_without_credentials_asks_the_user(hass, reload_spy, notify_spy):
    entry, owner, login, *_ = make(hass, age_days=28.5, creds=False)
    await owner.async_check_token_expiry()
    login.assert_not_awaited()
    notify_spy.assert_called_once()
    reload_spy.assert_not_called()


@pytest.mark.parametrize("error", [sso_login.SsoLoginError("sign-in refused: msgCode=1012", refused=True),
                                   RuntimeError("anything else")])
async def test_failed_sign_in_asks_the_user_and_keeps_the_old_token(hass, reload_spy, notify_spy, error):
    entry, owner, *_ = make(hass, age_days=29, login=AsyncMock(side_effect=error))
    await owner.async_check_token_expiry()
    notify_spy.assert_called_once()
    assert entry.data["token"]["access_token"] == "old"
    reload_spy.assert_not_called()


async def test_failed_credentials_are_not_retried_hourly(hass, reload_spy, notify_spy):
    failing = AsyncMock(side_effect=sso_login.SsoLoginError("refused", refused=True))
    entry, owner, login, _, clock = make(hass, age_days=29, login=failing)
    for _ in range(5):
        await owner.async_check_token_expiry()
        clock.t += 3600
    assert login.await_count == 1
    clock.t += tl.LOGIN_FAILURE_BACKOFF_S
    await owner.async_check_token_expiry()
    assert login.await_count == 2


async def test_new_credentials_lift_the_backoff(hass, reload_spy, notify_spy):
    failing = AsyncMock(side_effect=sso_login.SsoLoginError("refused", refused=True))
    entry, owner, login, _, clock = make(hass, age_days=29, login=failing)
    await owner.async_check_token_expiry()
    hass.config_entries.async_update_entry(
        entry, data={**entry.data, tl.KEY_CREDENTIALS: {"username": "me@example.com", "password_sha256": "NEW"}})
    clock.t += 3600
    await owner.async_check_token_expiry()
    assert login.await_count == 2


# -- rejections --------------------------------------------------------------

async def test_rejection_refreshes_without_touching_the_session_clock(hass, reload_spy, notify_spy):
    entry, owner, login, session, _ = make(hass, age_days=3)
    await owner.on_token_expired_event()
    session.implementation.async_refresh_token.assert_awaited_once()
    assert entry.data["token"]["access_token"] == "refreshed"
    assert entry.data[tl.KEY_SESSION_STARTED_AT] == T0
    login.assert_not_awaited()
    reload_spy.assert_called_once()


async def test_rejection_falls_back_to_sign_in_when_refresh_fails(hass, reload_spy, notify_spy):
    entry, owner, login, *_ = make(hass, age_days=3, refresh=AsyncMock(side_effect=RuntimeError("400")))
    await owner.on_token_expired_event()
    login.assert_awaited_once()
    assert entry.data["token"]["access_token"] == "new"
    notify_spy.assert_not_called()


async def test_rejection_after_a_refresh_signs_in_even_across_a_reload(hass, reload_spy, notify_spy):
    entry, owner, login, session, clock = make(hass, age_days=3)
    await owner.on_token_expired_event()
    assert session.implementation.async_refresh_token.await_count == 1
    # The reload builds a new owner; the refreshed token is rejected again.
    clock.t += tl.REJECTION_FLOOR_S + 1
    again = tl.AuthTokenRefresh(hass, entry, session, "https://sso.example", login=login, clock=clock)
    await again.on_token_expired_event()
    assert session.implementation.async_refresh_token.await_count == 1
    login.assert_awaited_once()
    assert entry.data[tl.KEY_SESSION_STARTED_AT] == clock.t


async def test_rejection_storm_is_handled_once_per_floor(hass, reload_spy, notify_spy):
    entry, owner, login, session, clock = make(hass, age_days=3)
    for _ in range(5):
        await owner.on_token_expired_event()
    clock.t += tl.REJECTION_FLOOR_S - 1
    await owner.on_token_expired_event()
    assert session.implementation.async_refresh_token.await_count == 1
    login.assert_not_awaited()


# -- reloads and notifications ------------------------------------------------

async def test_reload_inside_the_floor_is_deferred_not_dropped(hass, reload_spy, notify_spy):
    entry, owner, *_ = make(hass, age_days=3)
    now = dt_util.utcnow().timestamp()
    tl.schedule_reload(hass, entry, now)
    tl.schedule_reload(hass, entry, now + 10)
    tl.schedule_reload(hass, entry, now + 20)
    assert reload_spy.call_count == 1
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=tl.RELOAD_FLOOR_S + 1))
    await hass.async_block_till_done()
    assert reload_spy.call_count == 2


async def test_record_new_session_is_the_one_writer_for_a_fresh_sign_in(hass, reload_spy):
    entry, *_ = make(hass, age_days=40)
    with patch.object(tl.persistent_notification, "async_dismiss") as dismiss:
        tl.record_new_session(hass, entry, {"access_token": "interactive"}, now=T0 + 40 * DAY)
    assert entry.data["token"]["access_token"] == "interactive"
    assert entry.data[tl.KEY_SESSION_STARTED_AT] == T0 + 40 * DAY
    assert entry.data[tl.KEY_CREDENTIALS] == CREDS
    dismiss.assert_called_once()
    reload_spy.assert_called_once()


async def test_start_does_not_dismiss_an_open_expiry_notice(hass, reload_spy, notify_spy):
    entry, owner, *_ = make(hass, age_days=40, creds=False)
    with patch.object(tl.persistent_notification, "async_dismiss") as dismiss:
        owner.start_token_check()
        await hass.async_block_till_done()
    dismiss.assert_not_called()
    notify_spy.assert_called_once()


async def test_start_registers_its_timer_for_unload(hass, reload_spy, notify_spy):
    entry, owner, *_ = make(hass, age_days=1)
    with patch.object(tl, "async_track_time_interval", return_value="UNSUB") as track, \
            patch.object(entry, "async_on_unload") as on_unload:
        owner.start_token_check()
        await hass.async_block_till_done()
    track.assert_called_once()
    assert track.call_args.args[2] == tl.CHECK_INTERVAL
    on_unload.assert_called_once_with("UNSUB")


# -- seeding -------------------------------------------------------------------

def test_seed_is_exact_for_an_interactive_token():
    assert tl.seed_session_started_at({"token": {"expires_at": T0 + 31 * DAY}}) == T0


def test_seed_assumes_the_earliest_start_for_a_refreshed_token():
    # A refresh at T0+25 d reports a fresh 31 d. The real start is unknown but no
    # later than the refresh; the seed assumes the earliest possible start.
    refreshed = T0 + 25 * DAY
    data = {"token": {"expires_at": refreshed + 31 * DAY}, tl.KEY_LAST_TOKEN_REFRESH: refreshed}
    assert tl.seed_session_started_at(data) == refreshed - 31 * DAY


def test_seed_keeps_a_recorded_start():
    assert tl.seed_session_started_at({tl.KEY_SESSION_STARTED_AT: T0, "token": {"expires_at": 1}}) == T0


def test_session_expiry_is_start_plus_31_days():
    assert tl.session_expires_at({tl.KEY_SESSION_STARTED_AT: T0}) == T0 + 31 * DAY
    assert tl.session_expires_at({}) is None
