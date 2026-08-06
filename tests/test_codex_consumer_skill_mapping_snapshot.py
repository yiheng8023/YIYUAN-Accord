from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from scripts.validate_codex_consumer_skill_mapping_snapshot import (
    RECORD_PATH,
    validate_repository_snapshot,
    validate_snapshot_record,
)


ROOT = Path(__file__).resolve().parent.parent


class CodexConsumerSkillMappingSnapshotTests(unittest.TestCase):
    def setUp(self) -> None:
        self.record = json.loads((ROOT / RECORD_PATH).read_text(encoding="utf-8"))

    def test_repository_snapshot_is_valid(self) -> None:
        validated = validate_repository_snapshot(ROOT)

        self.assertEqual("codex-consumer-skill-mapping-snapshot-v1", validated["id"])
        self.assertEqual("verified-read-only-physical-mapping-partial", validated["status"])

    def test_rejects_common_root_count_drift(self) -> None:
        record = copy.deepcopy(self.record)
        record["commonRoot"]["entryCount"] = 45

        with self.assertRaisesRegex(RuntimeError, "common-root"):
            validate_snapshot_record(record, root=ROOT)

    def test_rejects_duplicate_projection_name(self) -> None:
        record = copy.deepcopy(self.record)
        record["projectionBuckets"]["localSymlinks"].append("caveman")

        with self.assertRaisesRegex(RuntimeError, "projection buckets"):
            validate_snapshot_record(record, root=ROOT)

    def test_rejects_source_revision_drift(self) -> None:
        record = copy.deepcopy(self.record)
        record["databaseReconciliation"]["sourceRevision"] = "main"

        with self.assertRaisesRegex(RuntimeError, "source-backed"):
            validate_snapshot_record(record, root=ROOT)

    def test_rejects_materialized_owner_drift(self) -> None:
        record = copy.deepcopy(self.record)
        record["materializedOwnership"]["consumerRepositoryExactTreeNames"].pop()

        with self.assertRaisesRegex(RuntimeError, "materialized ownership"):
            validate_snapshot_record(record, root=ROOT)

    def test_rejects_authority_expansion(self) -> None:
        record = copy.deepcopy(self.record)
        record["authorityBoundary"]["consumerMutationAuthorized"] = True

        with self.assertRaisesRegex(RuntimeError, "authority"):
            validate_snapshot_record(record, root=ROOT)

    def test_rejects_loader_or_behavior_overclaim(self) -> None:
        for claim in ("provesLoaderPrecedence", "provesInstructionDelivery", "provesBehavior"):
            with self.subTest(claim=claim):
                record = copy.deepcopy(self.record)
                record["claimBoundary"][claim] = True

                with self.assertRaisesRegex(RuntimeError, "claim boundary"):
                    validate_snapshot_record(record, root=ROOT)

    def test_acceptance_stays_partial_and_binds_snapshot(self) -> None:
        acceptance = json.loads(
            (ROOT / "registry/program-acceptance-map.json").read_text(encoding="utf-8")
        )
        criteria = {row["id"]: row for row in acceptance["acceptanceCriteria"]}
        evidence_id = "evidence.codex-consumer-skill-mapping-snapshot-2026-08-07"

        for acceptance_id in (
            "acceptance.consumer-mapping-evidence",
            "acceptance.cc-switch-source-preserving-skill-pool",
            "acceptance.foreign-managed-capability-coexistence",
        ):
            self.assertEqual("partial", criteria[acceptance_id]["assessment"])
            self.assertIn(evidence_id, criteria[acceptance_id]["evidenceIds"])


if __name__ == "__main__":
    unittest.main()
