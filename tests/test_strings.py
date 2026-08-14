"""Tests for strings.json / translations/en.json content."""

import json
from pathlib import Path

BASE = Path(__file__).parents[1] / "custom_components" / "bluetti"


def test_pick_implementation_field_has_a_region_label():
    strings = json.loads((BASE / "strings.json").read_text())
    en = json.loads((BASE / "translations" / "en.json").read_text())

    for source in (strings, en):
        label = source["config"]["step"]["pick_implementation"]["data"]["implementation"]
        assert label == "Region"
