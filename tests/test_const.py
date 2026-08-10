"""Tests for const.py."""

from custom_components.bluetti.const import Method


def test_string_enum_str_returns_value():
    assert str(Method.GET) == "GET"
    assert str(Method.POST) == "POST"
    assert str(Method.DELETE) == "DELETE"
