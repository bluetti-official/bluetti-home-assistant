"""Sanity checks for hacs.json, required for HACS to recognize this repo."""

import json
from pathlib import Path

HACS_JSON_PATH = Path(__file__).parents[1] / "hacs.json"


def test_hacs_json_is_valid_and_has_a_name():
    hacs_json = json.loads(HACS_JSON_PATH.read_text())
    assert hacs_json["name"] == "BLUETTI"
