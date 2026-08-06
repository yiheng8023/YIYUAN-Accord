from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from scripts.validate_claude_plugin_skill_root_readonly_inventory import (
    RECORD_PATH,
    validate_inventory_record,
    validate_repository_inventory,
)


ROOT = Path(__file__).resolve().parent.parent


class ClaudePluginSkillRootReadonlyInventoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.record = json.loads((ROOT / RECORD_PATH).read_text(encoding="utf-8"))

    def test_repository_inventory_is_valid_and_partial(self) -> None:
        record = validate_repository_inventory(ROOT)

        self.assertEqual(
            "verified-readonly-field-bound-inventory-partial", record["status"]
        )
        self.assertEqual("partial", record["acceptanceBoundary"]["assessment"])

    def test_inventory_distinguishes_cache_from_install_and_enablement(self) -> None:
        observations = self.record["observations"]

        self.assertEqual(1, observations["registeredMarketplaceCount"])
        self.assertEqual(257, observations["catalogPluginMetadataCount"])
        self.assertEqual(17, observations["localSkillRootCount"])
        self.assertEqual(4, observations["manifestDeclaredRemoteSkillEntryCount"])
        self.assertEqual(21, len(self.record["inventoryItems"]))
        self.assertTrue(
            all(
                "unknown" in item["cache-or-install-state"]
                for item in self.record["inventoryItems"]
            )
        )

    def test_authorization_is_read_only_and_does_not_expand_adjacent_authority(self) -> None:
        authority = self.record["authorityBoundary"]

        self.assertTrue(authority["readOnlyInventoryAuthorized"])
        for field, value in authority.items():
            if field != "readOnlyInventoryAuthorized":
                self.assertFalse(value, field)

    def test_inventory_items_are_field_bound(self) -> None:
        allowed = set(self.record["inventoryScope"]["allowedFields"])

        for item in self.record["inventoryItems"]:
            self.assertEqual(allowed, set(item))

    def test_validator_rejects_install_state_promotion(self) -> None:
        record = copy.deepcopy(self.record)
        record["inventoryItems"][0]["cache-or-install-state"] = (
            "installed-and-enabled"
        )

        with self.assertRaisesRegex(RuntimeError, "install or enablement"):
            validate_inventory_record(record, root=ROOT)

    def test_validator_rejects_payload_read_or_claim_promotion(self) -> None:
        for section, field in (
            ("executionBoundary", "pluginPayloadBodyRead"),
            ("claimBoundary", "provesEnablement"),
            ("claimBoundary", "provesBehavior"),
        ):
            with self.subTest(section=section, field=field):
                record = copy.deepcopy(self.record)
                record[section][field] = True

                with self.assertRaises(RuntimeError):
                    validate_inventory_record(record, root=ROOT)

    def test_validator_rejects_path_escape(self) -> None:
        record = copy.deepcopy(self.record)
        record["inventoryItems"][0]["skill-root-relative-path"] = (
            "../../outside/skills"
        )

        with self.assertRaisesRegex(RuntimeError, "path boundary"):
            validate_inventory_record(record, root=ROOT)


if __name__ == "__main__":
    unittest.main()
