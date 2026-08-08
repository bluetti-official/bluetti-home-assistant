"""Sanity checks for manifest.json against Home Assistant guidelines."""

import json
from pathlib import Path

MANIFEST_PATH = Path(__file__).parents[1] / "custom_components" / "bluetti" / "manifest.json"


def test_manifest_is_valid_json():
    json.loads(MANIFEST_PATH.read_text())


def test_manifest_has_required_and_recommended_fields():
    manifest = json.loads(MANIFEST_PATH.read_text())

    assert manifest["domain"] == "bluetti"
    assert manifest["iot_class"] == "cloud_push"
    assert manifest["integration_type"] == "hub"
    assert manifest["config_flow"] is True
    assert "version" in manifest
    assert manifest["codeowners"]


def test_manifest_requirements_are_pinned():
    manifest = json.loads(MANIFEST_PATH.read_text())
    for requirement in manifest["requirements"]:
        assert ">=" in requirement, f"{requirement} should specify a minimum version"
