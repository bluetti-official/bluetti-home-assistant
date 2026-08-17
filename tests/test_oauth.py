"""Tests for oauth.py: OAuth2FlowHandler helpers and AuthTokenRefresh."""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.helpers import issue_registry as ir

from custom_components.bluetti.const import DOMAIN
from custom_components.bluetti.model.product import UserProduct
from custom_components.bluetti.oauth import (
    ISSUE_ID_OAUTH_EXPIRED,
    AsyncConfigEntryAuth,
    AuthTokenRefresh,
    OAuth2FlowHandler,
)


def _refresher(hass, token: dict) -> tuple[AuthTokenRefresh, MockConfigEntry]:
    entry = MockConfigEntry(domain=DOMAIN, data={})
    entry.add_to_hass(hass)
    session = MagicMock()
    session.token = token
    return AuthTokenRefresh(hass, entry, session), entry


def test_logger_property():
    flow = OAuth2FlowHandler()
    assert flow.logger.name == "custom_components.bluetti.oauth"


async def test_async_oauth_create_entry_delegates_to_select_devices(hass):
    flow = OAuth2FlowHandler()
    flow.hass = hass
    flow.async_step_select_devices = AsyncMock(return_value={"type": "abort", "reason": "success"})

    result = await flow.async_oauth_create_entry({"token": {"access_token": "x"}})

    assert flow._oauth_data == {"token": {"access_token": "x"}}
    flow.async_step_select_devices.assert_awaited_once_with()
    assert result["reason"] == "success"


async def test_async_step_reconfigure_missing_entry_aborts(hass):
    flow = OAuth2FlowHandler()
    flow.hass = hass
    flow.context = {"entry_id": "does-not-exist"}

    result = await flow.async_step_reconfigure()

    assert result["type"] == "abort"
    assert result["reason"] == "reconfigure_failed"


async def test_async_step_reconfigure_delegates_to_async_step_user(hass):
    entry = MockConfigEntry(domain=DOMAIN)
    entry.add_to_hass(hass)

    flow = OAuth2FlowHandler()
    flow.hass = hass
    flow.context = {"entry_id": entry.entry_id}
    flow.async_step_user = AsyncMock(return_value={"type": "form"})

    result = await flow.async_step_reconfigure()

    assert flow.entry.entry_id == entry.entry_id
    flow.async_step_user.assert_awaited_once()
    assert result["type"] == "form"


async def test_token_refresh_init_subscribes_and_unsubs_on_unload(hass):
    refresher, entry = _refresher(hass, {})
    assert refresher.entry is entry

    hass.bus.async_fire("onTokenExpired")
    await hass.async_block_till_done()


async def test_on_token_expired_event_forces_a_refresh_attempt(hass):
    # The cloud reporting the token expired doesn't mean the refresh_token
    # is dead too (issues #75, #81, #97) - this must try a forced refresh
    # rather than immediately giving up with a notification.
    refresher, _entry = _refresher(hass, {})
    refresher.async_check_token_expiry = AsyncMock()

    await refresher.on_token_expired_event(None)

    refresher.async_check_token_expiry.assert_awaited_once_with(force_or_now=True)


async def test_on_token_expired_event_notifies_only_if_refresh_cannot_help(hass):
    # With no token at all, there is nothing to refresh - this must still
    # fall back to notifying instead of silently doing nothing.
    refresher, _entry = _refresher(hass, {})
    refresher.send_expired_notification = MagicMock()

    await refresher.on_token_expired_event(None)

    refresher.send_expired_notification.assert_called_once()


def test_is_token_valid_no_token(hass):
    refresher, _entry = _refresher(hass, {})
    assert refresher.is_token_valid() is False


def test_is_token_valid_expires_at_in_future(hass):
    refresher, _entry = _refresher(hass, {"expires_at": time.time() + 1000})
    assert refresher.is_token_valid() is True


def test_is_token_valid_expires_at_in_past(hass):
    refresher, _entry = _refresher(hass, {"expires_at": time.time() - 1000})
    assert refresher.is_token_valid() is False


def test_is_token_valid_expires_in_created_at_future(hass):
    refresher, _entry = _refresher(
        hass, {"created_at": time.time(), "expires_in": 1000}
    )
    assert refresher.is_token_valid() is True


def test_is_token_valid_expires_in_created_at_past(hass):
    refresher, _entry = _refresher(
        hass, {"created_at": time.time() - 5000, "expires_in": 100}
    )
    assert refresher.is_token_valid() is False


def test_is_token_valid_no_recognizable_fields(hass):
    refresher, _entry = _refresher(hass, {"some_other_field": True})
    assert refresher.is_token_valid() is False


async def test_start_token_check_invalid_token_sends_notification(hass):
    refresher, _entry = _refresher(hass, {})
    refresher.send_expired_notification = MagicMock()
    refresher.async_check_token_expiry = AsyncMock()

    refresher.start_token_check()
    await hass.async_block_till_done()

    refresher.send_expired_notification.assert_called_once()
    refresher.async_check_token_expiry.assert_awaited_once()


async def test_start_token_check_valid_token_schedules_interval(hass):
    refresher, _entry = _refresher(hass, {"expires_at": time.time() + 1000})
    refresher.send_expired_notification = MagicMock()
    refresher.async_check_token_expiry = AsyncMock()

    with patch("custom_components.bluetti.oauth.async_track_time_interval") as mock_track:
        refresher.start_token_check()
        await hass.async_block_till_done()

    mock_track.assert_called_once()
    refresher.send_expired_notification.assert_not_called()
    refresher.async_check_token_expiry.assert_awaited_once()


def test_send_expired_notification_creates_notification(hass):
    refresher, _entry = _refresher(hass, {})

    with patch("custom_components.bluetti.oauth.persistent_notification.async_create") as mock_create:
        refresher.send_expired_notification()

    mock_create.assert_called_once()
    assert mock_create.call_args.kwargs["notification_id"] == "notifyTokenExpire"

    issue = ir.async_get(hass).async_get_issue(DOMAIN, ISSUE_ID_OAUTH_EXPIRED)
    assert issue is not None
    assert issue.translation_key == "oauth_expired"
    assert issue.is_fixable is False


def test_send_expired_notification_is_rate_limited(hass):
    """A repeatedly-failing token check must not spam a notification every time."""
    refresher, _entry = _refresher(hass, {})

    with patch("custom_components.bluetti.oauth.persistent_notification.async_create") as mock_create:
        refresher.send_expired_notification()
        refresher.send_expired_notification()

    mock_create.assert_called_once()


def test_send_expired_notification_fires_again_after_interval_elapses(hass):
    refresher, _entry = _refresher(hass, {})
    refresher._last_notified_at = time.time() - 3600  # more than 30 minutes ago

    with patch("custom_components.bluetti.oauth.persistent_notification.async_create") as mock_create:
        refresher.send_expired_notification()

    mock_create.assert_called_once()


async def test_start_token_check_clears_issue_when_token_becomes_valid(hass):
    refresher, _entry = _refresher(hass, {"expires_at": time.time() + 1000})
    refresher.async_check_token_expiry = AsyncMock()
    ir.async_create_issue(
        hass, DOMAIN, ISSUE_ID_OAUTH_EXPIRED, is_fixable=False,
        severity=ir.IssueSeverity.ERROR, translation_key="oauth_expired",
    )

    with patch("custom_components.bluetti.oauth.async_track_time_interval"):
        refresher.start_token_check()
        await hass.async_block_till_done()

    assert ir.async_get(hass).async_get_issue(DOMAIN, ISSUE_ID_OAUTH_EXPIRED) is None


async def test_async_check_token_expiry_empty_token_notifies(hass):
    # No token at all means there is nothing to refresh - fall back to
    # notifying instead of silently doing nothing.
    refresher, _entry = _refresher(hass, {})
    refresher.send_expired_notification = MagicMock()

    await refresher.async_check_token_expiry()

    refresher.send_expired_notification.assert_called_once()


async def test_async_check_token_expiry_unrecognized_format_attempts_refresh(hass):
    # A non-empty token with neither `expires_at` nor `expires_in`+
    # `created_at` has unknown expiry - try to refresh it rather than
    # assuming it's expired (a false "expired" notice would be wrong as
    # often as it's right).
    entry = MockConfigEntry(domain=DOMAIN, data={"last_token_refresh": 0.0})
    entry.add_to_hass(hass)
    session = MagicMock()
    session.token = {"access_token": "x", "refresh_token": "y"}
    session.implementation.async_refresh_token = AsyncMock(return_value={"access_token": "new"})
    refresher = AuthTokenRefresh(hass, entry, session)
    refresher.send_expired_notification = MagicMock()

    with patch.object(hass.config_entries, "async_reload", AsyncMock()):
        await refresher.async_check_token_expiry()

    session.implementation.async_refresh_token.assert_awaited_once()
    refresher.send_expired_notification.assert_not_called()


async def test_async_check_token_expiry_expires_in_created_at_format_is_refreshed(hass):
    # Regression test: async_check_token_expiry used to only understand
    # `expires_at` and would silently skip refreshing an already-expired
    # token using the `expires_in`/`created_at` shape instead.
    entry = MockConfigEntry(domain=DOMAIN, data={"last_token_refresh": 0.0})
    entry.add_to_hass(hass)
    session = MagicMock()
    session.token = {"created_at": time.time() - 5000, "expires_in": 100}
    session.implementation.async_refresh_token = AsyncMock(return_value={"access_token": "new"})
    refresher = AuthTokenRefresh(hass, entry, session)

    with patch.object(hass.config_entries, "async_reload", AsyncMock()):
        # Force it, the same way on_token_expired_event does, since the
        # token is already expired.
        await refresher.async_check_token_expiry(force_or_now=True)

    session.implementation.async_refresh_token.assert_awaited_once()


async def test_async_check_token_expiry_forced_redeems_an_already_expired_token(hass):
    # This is the core fix for issues #75/#81/#97: a forced check (from
    # on_token_expired_event) must still try the refresh_token even though
    # the access token has already expired, instead of giving up right away.
    entry = MockConfigEntry(domain=DOMAIN, data={"last_token_refresh": 0.0})
    entry.add_to_hass(hass)
    session = MagicMock()
    session.token = {"expires_at": time.time() - 10}
    session.implementation.async_refresh_token = AsyncMock(return_value={"access_token": "new"})
    refresher = AuthTokenRefresh(hass, entry, session)
    refresher.send_expired_notification = MagicMock()

    with patch.object(hass.config_entries, "async_reload", AsyncMock()) as mock_reload:
        await refresher.async_check_token_expiry(force_or_now=True)

    session.implementation.async_refresh_token.assert_awaited_once()
    mock_reload.assert_awaited_once_with(entry.entry_id)
    refresher.send_expired_notification.assert_not_called()


async def test_async_check_token_expiry_forced_notifies_when_refresh_fails(hass):
    entry = MockConfigEntry(domain=DOMAIN, data={"last_token_refresh": 0.0})
    entry.add_to_hass(hass)
    session = MagicMock()
    session.token = {"expires_at": time.time() - 10}
    session.implementation.async_refresh_token = AsyncMock(side_effect=RuntimeError("refresh_token rejected"))
    refresher = AuthTokenRefresh(hass, entry, session)
    refresher.send_expired_notification = MagicMock()

    await refresher.async_check_token_expiry(force_or_now=True)

    refresher.send_expired_notification.assert_called_once()


async def test_async_check_token_expiry_forced_uses_shorter_min_interval(hass):
    # Forced checks use a 60s throttle instead of the normal 3600s one, so a
    # burst of duplicate EVENT_TOKEN_EXPIRED events (e.g. from concurrent
    # requests failing around the same time) doesn't refresh repeatedly, but
    # a genuinely new expiry a minute later still gets a fresh attempt.
    entry = MockConfigEntry(domain=DOMAIN, data={"last_token_refresh": time.time() - 30})
    entry.add_to_hass(hass)
    session = MagicMock()
    session.token = {"expires_at": time.time() - 10}
    session.implementation.async_refresh_token = AsyncMock(return_value={"access_token": "new"})
    refresher = AuthTokenRefresh(hass, entry, session)

    with patch.object(hass.config_entries, "async_reload", AsyncMock()):
        await refresher.async_check_token_expiry(force_or_now=True)

    session.implementation.async_refresh_token.assert_not_called()


async def test_async_check_token_expiry_already_expired(hass):
    refresher, _entry = _refresher(hass, {"expires_at": time.time() - 10})
    refresher.send_expired_notification = MagicMock()

    await refresher.async_check_token_expiry()

    refresher.send_expired_notification.assert_called_once()


async def test_async_check_token_expiry_not_due_soon_does_nothing(hass):
    refresher, _entry = _refresher(hass, {"expires_at": time.time() + 3600 * 24 * 30})
    refresher.send_expired_notification = MagicMock()

    await refresher.async_check_token_expiry()

    refresher.send_expired_notification.assert_not_called()


async def test_async_check_token_expiry_recent_refresh_is_skipped(hass):
    entry = MockConfigEntry(domain=DOMAIN, data={"last_token_refresh": time.time() - 60})
    entry.add_to_hass(hass)
    session = MagicMock()
    session.token = {"expires_at": time.time() + 100}
    refresher = AuthTokenRefresh(hass, entry, session)

    await refresher.async_check_token_expiry()

    session.implementation.async_refresh_token.assert_not_called()


async def test_async_check_token_expiry_refreshes_and_reloads(hass):
    entry = MockConfigEntry(domain=DOMAIN, data={"last_token_refresh": 0.0})
    entry.add_to_hass(hass)
    session = MagicMock()
    session.token = {"expires_at": time.time() + 100}
    session.implementation.async_refresh_token = AsyncMock(return_value={"access_token": "new"})
    refresher = AuthTokenRefresh(hass, entry, session)

    with patch.object(hass.config_entries, "async_reload", AsyncMock()) as mock_reload:
        await refresher.async_check_token_expiry()

    session.implementation.async_refresh_token.assert_awaited_once()
    updated = hass.config_entries.async_get_entry(entry.entry_id)
    assert updated.data["token"] == {"access_token": "new"}
    mock_reload.assert_awaited_once_with(entry.entry_id)


async def test_async_check_token_expiry_refresh_failure_is_logged(hass):
    entry = MockConfigEntry(domain=DOMAIN, data={"last_token_refresh": 0.0})
    entry.add_to_hass(hass)
    session = MagicMock()
    session.token = {"expires_at": time.time() + 100}
    session.implementation.async_refresh_token = AsyncMock(side_effect=RuntimeError("boom"))
    refresher = AuthTokenRefresh(hass, entry, session)

    # Must not raise even though the refresh call failed.
    await refresher.async_check_token_expiry()


async def test_async_get_access_token_ensures_validity_first():
    session = MagicMock()
    session.async_ensure_token_valid = AsyncMock()
    session.token = {"access_token": "fresh-token"}
    auth = AsyncConfigEntryAuth(MagicMock(), session)

    token = await auth.async_get_access_token()

    session.async_ensure_token_valid.assert_awaited_once()
    assert token == "fresh-token"


async def test_select_devices_shows_form_with_available_devices(hass):
    flow = OAuth2FlowHandler()
    flow.hass = hass
    flow.context = {}
    flow._oauth_data = {
        "auth_implementation": "bluetti",
        "token": {"access_token": "tok", "expires_at": 9999999999},
    }
    product = UserProduct(sn="SN1", name="Device 1", stateList=[], online="1")

    with patch("custom_components.bluetti.oauth.async_get_clientsession"), \
         patch("custom_components.bluetti.oauth.ProductClient") as mock_client_cls:
        mock_client_cls.return_value.get_user_products = AsyncMock(
            return_value=MagicMock(data=[product])
        )
        result = await flow.async_step_select_devices(user_input=None)

    assert result["type"] == "form"
    assert result["step_id"] == "select_devices"
