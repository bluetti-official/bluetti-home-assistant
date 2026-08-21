"""Tests for ApplicationRuntimeException."""

import pytest

from custom_components.bluetti.application_exception import ApplicationRuntimeException


def test_inherits_from_exception():
    """It must inherit from Exception, not BaseException, to be catchable."""
    assert issubclass(ApplicationRuntimeException, Exception)


def test_can_be_caught_by_except_exception():
    try:
        raise ApplicationRuntimeException(msgCode=500, errMessage="boom")
    except Exception as err:
        assert err.msgCode == 500
        assert err.message == "boom"
    else:
        pytest.fail("ApplicationRuntimeException was not caught by except Exception")


def test_default_message_used_when_none_provided():
    err = ApplicationRuntimeException(msgCode=1)
    assert err.message == "An unknown error has occurred."
