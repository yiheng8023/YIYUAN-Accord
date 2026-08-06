from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from scripts.validate_claude_consumer_skill_projection_snapshot import (
    RECORD_PATH,
    validate_repository_snapshot,
    validate_snapshot_record,
)


ROOT = Path(__file__).resolve().parent.parent


class ClaudeConsumerSkillProjectionSnapshotTests(unittest.TestCase):
    def setUp(self) -> None:
        self.record = json.loads((ROOT / RECORD_PATH).read_text(encoding="utf-8"))

    def test_repository_snapshot_is_valid(self) -> None:
        record = validate_repository_snapshot(ROOT)

        self.assertEqual("claude-consumer-skill-projection-snapshot-v1", record["id"])

    def test_rejects_projection_count_drift(self) -> None:
        record = copy.deepcopy(self.record)
        record["claudeSkillRoot"]["symbolicLinkCount"] = 42

        with self.assertRaisesRegex(RuntimeError, "Claude root"):
            validate_snapshot_record(record, root=ROOT)

    def test_rejects_cross_consumer_shape_collapse(self) -> None:
        record = copy.deepcopy(self.record)
        record["crossConsumerDifference"]["controlContractsUseCcSwitchLinksOnClaude"] = False

        with self.assertRaisesRegex(RuntimeError, "cross-consumer"):
            validate_snapshot_record(record, root=ROOT)

    def test_rejects_plugin_inventory_overclaim(self) -> None:
        record = copy.deepcopy(self.record)
        record["pluginBoundary"]["pluginSkillRootsInventoried"] = True

        with self.assertRaisesRegex(RuntimeError, "plugin boundary"):
            validate_snapshot_record(record, root=ROOT)

    def test_rejects_behavior_overclaim(self) -> None:
        record = copy.deepcopy(self.record)
        record["claimBoundary"]["provesBehavior"] = True

        with self.assertRaisesRegex(RuntimeError, "claim boundary"):
            validate_snapshot_record(record, root=ROOT)

    def test_rejects_authority_expansion(self) -> None:
        record = copy.deepcopy(self.record)
        record["authorityBoundary"]["projectionMutationAuthorized"] = True

        with self.assertRaisesRegex(RuntimeError, "authority"):
            validate_snapshot_record(record, root=ROOT)

    def test_supported_acceptance_stays_partial(self) -> None:
        acceptance = json.loads(
            (ROOT / "registry/program-acceptance-map.json").read_text(encoding="utf-8")
        )
        criteria = {row["id"]: row for row in acceptance["acceptanceCriteria"]}
        evidence_id = "evidence.claude-consumer-skill-projection-snapshot-2026-08-07"

        for acceptance_id in (
            "acceptance.consumer-mapping-evidence",
            "acceptance.cc-switch-source-preserving-skill-pool",
            "acceptance.foreign-managed-capability-coexistence",
        ):
            self.assertEqual("partial", criteria[acceptance_id]["assessment"])
            self.assertIn(evidence_id, criteria[acceptance_id]["evidenceIds"])


if __name__ == "__main__":
    unittest.main()
