"""Load the token-lifecycle modules without the integration's package __init__.

custom_components/bluetti/__init__.py pulls in the Bluetooth stack and the BLE
library, which these tests do not exercise. The modules under test import only
`.const` and each other, so they are loaded as members of a bare package that
points at the same directory.
"""
import importlib
import sys
import types
from pathlib import Path

import pytest

PKG = "bluetti_under_test"
_dir = Path(__file__).resolve().parents[1] / "custom_components" / "bluetti"
_pkg = types.ModuleType(PKG)
_pkg.__path__ = [str(_dir)]
sys.modules[PKG] = _pkg

sso_login = importlib.import_module(f"{PKG}.sso_login")
token_lifecycle = importlib.import_module(f"{PKG}.token_lifecycle")


@pytest.fixture
def anyio_backend():
    return "asyncio"
