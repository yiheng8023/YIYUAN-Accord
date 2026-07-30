from __future__ import annotations

from copy import deepcopy
import json
import unittest

from scripts.validate_skill_portfolio_current_55_subtractive_triage import (
    EVIDENCE_PATH,
    ROOT,
    validate_triage,
)


class SkillPortfolioCurrent55SubtractiveTriageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.document = json.loads(
            (ROOT / EVIDENCE_PATH).read_text(encoding="utf-8")
        )

    def test_current_triage_passes(self) -> None:
        validate_triage(deepcopy(self.document), root=ROOT)

    def test_rejects_partition_duplicate(self) -> None:
        document = deepcopy(self.document)
        document["portfolioPartition"]["cohorts"][1]["names"][0] = (
            document["portfolioPartition"]["cohorts"][0]["names"][0]
        )
        with self.assertRaisesRegex(RuntimeError, "coverage or exclusivity"):
            validate_triage(document, root=ROOT)

    def test_rejects_matt_snapshot_staleness_overclaim(self) -> None:
        document = deepcopy(self.document)
        document["sourceRefresh"]["mattpocock"][
            "ccSnapshotStalenessObservedForPromotedSuite"
        ] = True
        with self.assertRaisesRegex(RuntimeError, "Matt source refresh"):
            validate_triage(document, root=ROOT)

    def test_rejects_addy_source_equality_overclaim(self) -> None:
        document = deepcopy(self.document)
        document["sourceRefresh"]["addyosmani"][
            "liveBodiesEqualCurrentUpstreamAfterLfNormalization"
        ] = 5
        with self.assertRaisesRegex(RuntimeError, "Addy source refresh"):
            validate_triage(document, root=ROOT)

    def test_rejects_diagnose_ready_removal(self) -> None:
        document = deepcopy(self.document)
        document["subtractionEvidence"]["readyForManagerRemovalPreview"].append(
            "diagnose"
        )
        document["subtractionEvidence"]["blockedBeforeManagerRemoval"] = []
        with self.assertRaisesRegex(RuntimeError, "removal preview boundary"):
            validate_triage(document, root=ROOT)

    def test_rejects_manager_removal_authority_overclaim(self) -> None:
        document = deepcopy(self.document)
        document["claimBoundary"]["managerRemovalAuthorized"] = True
        with self.assertRaisesRegex(RuntimeError, "claim boundary"):
            validate_triage(document, root=ROOT)

    def test_rejects_retained_temp_source_root(self) -> None:
        document = deepcopy(self.document)
        document["cleanup"]["mattRefreshTempRootAbsent"] = False
        with self.assertRaisesRegex(RuntimeError, "cleanup evidence"):
            validate_triage(document, root=ROOT)


if __name__ == "__main__":
    unittest.main()
