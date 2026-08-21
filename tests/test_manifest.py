"""Sanity checks for manifest.json against Home Assistant guidelines."""

import json
from pathlib import Path

import yaml

MANIFEST_PATH = Path(__file__).parents[1] / "custom_components" / "bluetti" / "manifest.json"
QUALITY_SCALE_PATH = Path(__file__).parents[1] / "custom_components" / "bluetti" / "quality_scale.yaml"

QUALITY_SCALE_TIERS = {
    "bronze": [
        "action-setup", "appropriate-polling", "brands", "common-modules",
        "config-flow-test-coverage", "config-flow", "dependency-transparency",
        "docs-actions", "docs-high-level-description", "docs-installation-instructions",
        "docs-removal-instructions", "entity-event-setup", "entity-unique-id",
        "has-entity-name", "runtime-data", "test-before-configure", "test-before-setup",
        "unique-config-entry",
    ],
    "silver": [
        "action-exceptions", "config-entry-unloading", "docs-configuration-parameters",
        "docs-installation-parameters", "entity-unavailable", "integration-owner",
        "log-when-unavailable", "parallel-updates", "reauthentication-flow", "test-coverage",
    ],
    "gold": [
        "devices", "diagnostics", "discovery-update-info", "discovery", "docs-data-update",
        "docs-examples", "docs-known-limitations", "docs-supported-devices",
        "docs-supported-functions", "docs-troubleshooting", "docs-use-cases",
        "dynamic-devices", "entity-category", "entity-device-class",
        "entity-disabled-by-default", "entity-translations", "exception-translations",
        "icon-translations", "reconfiguration-flow", "repair-issues", "stale-devices",
    ],
    "platinum": ["async-dependency", "inject-websession", "strict-typing"],
}
TIER_ORDER = ["bronze", "silver", "gold", "platinum"]


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


def test_manifest_has_issue_tracker():
    # Required by HACS for default-repository inclusion.
    # https://hacs.xyz/docs/publish/integration
    manifest = json.loads(MANIFEST_PATH.read_text())
    assert manifest["issue_tracker"] == "https://github.com/bluetti-official/bluetti-home-assistant/issues"


def test_manifest_keys_are_sorted_domain_name_then_alphabetical():
    """hassfest requires this exact key order: domain, name, then alphabetical.

    See sort_manifest() in home-assistant/core's script/hassfest/manifest.py -
    the "Validate" CI workflow runs the real hassfest action, so a manifest
    that fails this locally would fail CI too.
    """
    keys = [key for key, _ in json.loads(
        MANIFEST_PATH.read_text(), object_pairs_hook=lambda pairs: pairs
    )]
    assert keys[:2] == ["domain", "name"]
    assert keys[2:] == sorted(keys[2:])


def test_quality_scale_yaml_covers_every_known_rule():
    rules = yaml.safe_load(QUALITY_SCALE_PATH.read_text())["rules"]
    all_known_rules = {rule for tier_rules in QUALITY_SCALE_TIERS.values() for rule in tier_rules}
    assert set(rules) == all_known_rules


def test_manifest_quality_scale_claim_is_backed_by_quality_scale_yaml():
    """The declared quality_scale must have every rule at or below its tier done/exempt."""
    manifest = json.loads(MANIFEST_PATH.read_text())
    claimed_tier = manifest["quality_scale"]
    rules = yaml.safe_load(QUALITY_SCALE_PATH.read_text())["rules"]

    tiers_to_check = TIER_ORDER[: TIER_ORDER.index(claimed_tier) + 1]
    unmet = [
        rule
        for tier in tiers_to_check
        for rule in QUALITY_SCALE_TIERS[tier]
        if (rules[rule] if isinstance(rules[rule], str) else rules[rule]["status"]) == "todo"
    ]
    assert not unmet, f"manifest claims '{claimed_tier}' but these rules are still todo: {unmet}"
