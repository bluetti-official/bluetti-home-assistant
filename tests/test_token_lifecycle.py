"""The token owner: day-28 sign-in, rejection recovery, the reload floor, seeding."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from conftest import sso_login, token_lifecycle as tl

DAY = 86400.0
T0 = 1_790_000_000.0  # session start used throughout
CREDS = {"username": "me@example.com", "password_sha256": "DIGEST"}


class Clock:
    def __init__(self, t):
        self.t = t

    def __call__(self):
        return self.t


@pytest.fixture(autouse=True)
def _reset_reload_floor():
    tl._last_reload.clear()


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
    # The next hourly check sees a fresh session and does nothing.
    clock.t += 3600
    await owner.async_check_token_expiry()
    login.assert_awaited_once()


async def test_day_28_without_credentials_asks_the_user(hass, reload_spy, notify_spy):
    entry, owner, login, *_ = make(hass, age_days=28.5, creds=False)
    await owner.async_check_token_expiry()
    login.assert_not_awaited()
    notify_spy.assert_called_once()
    reload_spy.assert_not_called()


async def test_failed_sign_in_asks_the_user_and_keeps_the_old_token(hass, reload_spy, notify_spy):
    failing = AsyncMock(side_effect=sso_login.SsoLoginError("sign-in refused: msgCode=1012"))
    entry, owner, *_ = make(hass, age_days=29, login=failing)
    await owner.async_check_token_expiry()
    notify_spy.assert_called_once()
    assert entry.data["token"]["access_token"] == "old"
    reload_spy.assert_not_called()


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


async def test_rejection_storm_is_handled_once_per_floor(hass, reload_spy, notify_spy):
    entry, owner, _, session, clock = make(hass, age_days=3)
    for _ in range(5):
        await owner.on_token_expired_event()
    clock.t += tl.REJECTION_FLOOR_S - 1
    await owner.on_token_expired_event()
    assert session.implementation.async_refresh_token.await_count == 1
    clock.t += 2
    await owner.on_token_expired_event()
    assert session.implementation.async_refresh_token.await_count == 2
    # The two refreshes are 301 s apart, outside the 300 s reload floor, so both reload.
    assert reload_spy.call_count == 2


async def test_reload_floor_survives_a_new_owner_instance(hass, reload_spy, notify_spy):
    entry, owner, *_ = make(hass, age_days=3)
    await owner.on_token_expired_event()
    # The reload builds a new owner for the same entry; its first token change inside 5 min must not reload again.
    other = tl.AuthTokenRefresh(hass, entry, owner.oAuth2Session, "https://sso.example",
                                login=owner._login, clock=owner._clock)
    await other.on_token_expired_event()
    reload_spy.assert_called_once()


async def test_start_registers_its_timer_for_unload(hass, reload_spy, notify_spy):
    entry, owner, *_ = make(hass, age_days=1)
    with patch.object(tl, "async_track_time_interval", return_value="UNSUB") as track, \
            patch.object(entry, "async_on_unload") as on_unload:
        owner.start_token_check()
        await hass.async_block_till_done()
    track.assert_called_once()
    assert track.call_args.args[2] == tl.CHECK_INTERVAL
    on_unload.assert_called_once_with("UNSUB")


def test_seed_is_exact_for_an_interactive_token():
    data = {"token": {"expires_at": T0 + 31 * DAY}}
    assert tl.seed_session_started_at(data) == T0


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
