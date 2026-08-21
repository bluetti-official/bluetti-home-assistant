"""Tests for strings.json / translations/*.json content."""

import json
from pathlib import Path

BASE = Path(__file__).parents[1] / "custom_components" / "bluetti"


def _flatten_keys(value, prefix: str = "") -> set[str]:
    """Return the set of dotted leaf-key paths in a nested dict."""
    if not isinstance(value, dict):
        return {prefix}
    keys: set[str] = set()
    for key, sub_value in value.items():
        keys |= _flatten_keys(sub_value, f"{prefix}.{key}" if prefix else key)
    return keys


def test_every_translation_file_has_every_strings_json_key():
    # strings.json is the source of truth for which keys exist; every
    # shipped translation must define all of them, or Home Assistant falls
    # back to showing the raw key/English text for whatever is missing.
    strings_keys = _flatten_keys(json.loads((BASE / "strings.json").read_text()))

    translations_dir = BASE / "translations"
    translation_files = sorted(translations_dir.glob("*.json"))
    assert translation_files, "no translation files found"

    for path in translation_files:
        translated_keys = _flatten_keys(json.loads(path.read_text()))
        missing = strings_keys - translated_keys
        assert not missing, f"{path.name} is missing keys: {sorted(missing)}"
