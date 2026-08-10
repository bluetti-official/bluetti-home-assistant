"""Tests for api/unify_response.py."""

from custom_components.bluetti.api.unify_response import UnifyResponse


def test_is_ok_true_when_msg_code_zero():
    response = UnifyResponse[dict](msgId="1", msgCode=0, data={})
    assert response.is_ok() is True


def test_is_ok_false_when_msg_code_nonzero():
    response = UnifyResponse[dict](msgId="1", msgCode=1)
    assert response.is_ok() is False


def test_has_data_true_when_ok_and_data_present():
    response = UnifyResponse[dict](msgId="1", msgCode=0, data={"a": 1})
    assert response.has_data() is True


def test_has_data_false_when_data_missing():
    response = UnifyResponse[dict](msgId="1", msgCode=0, data=None)
    assert response.has_data() is False


def test_has_data_false_when_not_ok():
    response = UnifyResponse[dict](msgId="1", msgCode=1, data={"a": 1})
    assert response.has_data() is False
