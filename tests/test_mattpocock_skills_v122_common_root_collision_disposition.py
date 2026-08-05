from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parent.parent
EVENT = (
    ROOT
    / "registry/mattpocock-skills-v1.2.2-codex-common-root-collision-and-disposition-2026-08-06.json"
)


class MattPocockSkillsV122CommonRootCollisionDispositionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.event = json.loads(EVENT.read_text(encoding="utf-8"))
        self.report_path = ROOT / self.event["probe"]["report"]
        self.report = json.loads(self.report_path.read_text(encoding="utf-8"))

    def test_event_binds_zero_model_probe(self) -> None:
        self.assertEqual(
            hashlib.sha256(self.report_path.read_bytes()).hexdigest(),
            self.event["probe"]["reportFileSha256"],
        )
        self.assertEqual(
            self.report["reportSha256"],
            self.event["probe"]["reportSha256"],
        )
        self.assertEqual(
            ["initialize", "initialized", "skills/list"],
            self.report["requestBoundary"]["sentMethods"],
        )
        self.assertEqual(0, self.report["requestBoundary"]["threadStartCount"])
        self.assertEqual(0, self.report["requestBoundary"]["turnStartCount"])
        self.assertEqual(0, self.report["requestBoundary"]["modelRequestCount"])
        self.assertTrue(
            self.report["mutationBoundary"]["allObservedSurfacesStable"]
        )

    def test_thirteen_directories_are_collisions_not_a_single_disposition_bucket(self) -> None:
        rows = self.event["commonRootDisposition"]["entries"]
        self.assertEqual(13, len(rows))
        self.assertEqual(
            13,
            sum(row["listingClassification"] == "both-listed" for row in rows),
        )
        self.assertEqual(
            6,
            sum(row["sourceTreeClassification"] == "prior-only" for row in rows),
        )
        self.assertEqual(
            7,
            sum(
                row["sourceTreeClassification"] == "both-prior-and-release"
                for row in rows
            ),
        )
        self.assertEqual(
            ["writing-great-skills"],
            [row["name"] for row in rows if row["targetReleaseRetainsName"] is False],
        )

    def test_manager_update_and_common_root_mutation_remain_separate_gates(self) -> None:
        decision = self.event["decision"]
        self.assertTrue(decision["commonRootReconciliationNecessary"])
        self.assertFalse(decision["commonRootMutationAuthorized"])
        self.assertFalse(decision["managerAtomicCohortUpdateProved"])
        self.assertFalse(decision["managerUpdateExecutionEligible"])
        self.assertTrue(decision["directoryContainerMustRemain"])
        self.assertTrue(decision["wizardMustRemainDisabled"])
        self.assertFalse(
            self.event["claimBoundary"]["instructionDeliveryPrecedenceProved"]
        )


if __name__ == "__main__":
    unittest.main()
