from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from scripts.validate_user_supplied_human_ai_sdlc_research_intake import (
    validate_intake,
)


ROOT = Path(__file__).resolve().parent.parent


def load() -> dict:
    return json.loads(
        (
            ROOT
            / "registry/user-supplied-human-ai-sdlc-research-intake-2026-07-24.json"
        ).read_text(encoding="utf-8")
    )


class UserSuppliedHumanAiSdlcResearchIntakeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.document = load()

    def test_current_intake_is_valid(self) -> None:
        validate_intake(self.document, root=ROOT)

    def test_rejects_hard_standard_promotion(self) -> None:
        document = copy.deepcopy(self.document)
        document["authorityBoundary"]["hardStandardPromotionAuthorized"] = True
        with self.assertRaisesRegex(RuntimeError, "hardStandardPromotionAuthorized"):
            validate_intake(document, root=ROOT)

    def test_rejects_whole_lifecycle_promotion(self) -> None:
        document = copy.deepcopy(self.document)
        document["lifecycleProjection"]["fullSoftwareLifecycleCoverageAccepted"] = True
        with self.assertRaisesRegex(RuntimeError, "Full lifecycle"):
            validate_intake(document, root=ROOT)

    def test_rejects_imported_report_confidence(self) -> None:
        document = copy.deepcopy(self.document)
        document["citationIntegrityAudit"]["sampleSummary"][
            "reportHighConfidenceLabelsAccepted"
        ] = True
        with self.assertRaisesRegex(RuntimeError, "reportHighConfidenceLabelsAccepted"):
            validate_intake(document, root=ROOT)

    def test_rejects_invented_prior_kimi_provenance(self) -> None:
        document = copy.deepcopy(self.document)
        document["historicalComparison"]["priorKimiReportProvableFromRepository"] = True
        with self.assertRaisesRegex(RuntimeError, "Earlier Kimi provenance"):
            validate_intake(document, root=ROOT)

    def test_rejects_archive_hash_drift(self) -> None:
        document = copy.deepcopy(self.document)
        document["sourceArtifact"]["archiveSha256"] = "0" * 64
        with self.assertRaisesRegex(RuntimeError, "Archive hash"):
            validate_intake(document, root=ROOT)

    def test_rejects_process_loss_promoted_to_complete_model(self) -> None:
        document = copy.deepcopy(self.document)
        document["processLossCrossCutAudit"]["classification"] = (
            "complete-end-to-end-loss-model"
        )
        with self.assertRaisesRegex(RuntimeError, "Process-loss coverage"):
            validate_intake(document, root=ROOT)

    def test_rejects_restored_archive_as_remote_durable(self) -> None:
        document = copy.deepcopy(self.document)
        document["sourceArtifact"]["restoredArchiveObservation"][
            "gitOrRemoteDurabilityProved"
        ] = True
        with self.assertRaisesRegex(RuntimeError, "durability"):
            validate_intake(document, root=ROOT)

    def test_rejects_repository_source_custody_path_drift(self) -> None:
        document = copy.deepcopy(self.document)
        document["sourceArtifact"]["restoredArchiveObservation"][
            "repositoryRelativePath"
        ] = "sources/user-supplied-human-ai-sdlc-research/missing.zip"
        with self.assertRaisesRegex(RuntimeError, "custody metadata"):
            validate_intake(document, root=ROOT)


if __name__ == "__main__":
    unittest.main()
