from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from scripts.validate_human_ai_collaboration_coverage_rebaseline import (
    validate_rebaseline,
)


ROOT = Path(__file__).resolve().parent.parent


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class HumanAiCollaborationCoverageRebaselineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.document = load(
            "registry/human-ai-collaboration-coverage-rebaseline-2026-07-24.json"
        )
        self.program = load("registry/curation-program-plan.json")
        self.acceptance = load("registry/program-acceptance-map.json")

    def validate(
        self,
        *,
        document: dict | None = None,
        program: dict | None = None,
        acceptance: dict | None = None,
    ) -> None:
        validate_rebaseline(
            document or self.document,
            program or self.program,
            acceptance or self.acceptance,
            root=ROOT,
        )

    def test_current_rebaseline_is_valid(self) -> None:
        self.validate()

    def test_rejects_solution_framing_promotion(self) -> None:
        document = copy.deepcopy(self.document)
        document["decision"]["selfAuthoredSkillsDefineProblemSpace"] = True
        with self.assertRaisesRegex(RuntimeError, "selfAuthoredSkillsDefineProblemSpace"):
            self.validate(document=document)

    def test_rejects_whole_domain_coverage_claim(self) -> None:
        document = copy.deepcopy(self.document)
        document["decision"]["wholeHumanAiCoverageClaimed"] = True
        with self.assertRaisesRegex(RuntimeError, "wholeHumanAiCoverageClaimed"):
            self.validate(document=document)

    def test_rejects_software_lifecycle_completeness_promotion(self) -> None:
        document = copy.deepcopy(self.document)
        document["coverageModel"]["softwareEngineeringSpecialization"]["status"] = (
            "complete"
        )
        with self.assertRaisesRegex(RuntimeError, "promoted to completeness"):
            self.validate(document=document)

    def test_rejects_missing_software_lifecycle_slice(self) -> None:
        document = copy.deepcopy(self.document)
        document["coverageModel"]["softwareEngineeringSpecialization"][
            "lifecycleSlices"
        ].pop()
        with self.assertRaisesRegex(RuntimeError, "lifecycle slices drifted"):
            self.validate(document=document)

    def test_rejects_process_fidelity_cross_cut_removal(self) -> None:
        document = copy.deepcopy(self.document)
        document["coverageModel"]["crossCuttingRisks"] = []
        with self.assertRaisesRegex(RuntimeError, "Process-fidelity"):
            self.validate(document=document)

    def test_rejects_lossless_process_fidelity_promotion(self) -> None:
        document = copy.deepcopy(self.document)
        document["decision"]["endToEndProcessFidelityCoverageClaimed"] = True
        with self.assertRaisesRegex(
            RuntimeError, "endToEndProcessFidelityCoverageClaimed"
        ):
            self.validate(document=document)

    def test_rejects_calibration_write_authority(self) -> None:
        document = copy.deepcopy(self.document)
        document["authorityBoundary"]["calibrationWriteAuthorized"] = True
        with self.assertRaisesRegex(RuntimeError, "calibrationWriteAuthorized"):
            self.validate(document=document)

    def test_rejects_hard_standard_promotion(self) -> None:
        document = copy.deepcopy(self.document)
        document["decision"]["hardStandardPromotionAuthorized"] = True
        with self.assertRaisesRegex(RuntimeError, "hardStandardPromotionAuthorized"):
            self.validate(document=document)

    def test_rejects_discarding_narrow_evidence(self) -> None:
        document = copy.deepcopy(self.document)
        document["decision"]["existingNarrowEvidenceRetained"] = False
        with self.assertRaisesRegex(RuntimeError, "existingNarrowEvidenceRetained"):
            self.validate(document=document)

    def test_rejects_acceptance_overclaim(self) -> None:
        acceptance = copy.deepcopy(self.acceptance)
        criterion = next(
            item
            for item in acceptance["acceptanceCriteria"]
            if item["id"] == "acceptance.software-engineering-lifecycle-specialization"
        )
        criterion["assessment"] = "verified"
        with self.assertRaisesRegex(RuntimeError, "assessment overclaimed"):
            self.validate(acceptance=acceptance)

    def test_rejects_ai_era_revalidation_evidence_projection_removal(self) -> None:
        acceptance = copy.deepcopy(self.acceptance)
        criterion = next(
            item
            for item in acceptance["acceptanceCriteria"]
            if item["id"] == "acceptance.ai-independent-hard-standard-boundary"
        )
        criterion["evidenceIds"].remove(
            "evidence.ai-era-classical-software-engineering-principles-"
            "revalidation-2026-07-31"
        )
        with self.assertRaisesRegex(RuntimeError, "evidence mapping drifted"):
            self.validate(acceptance=acceptance)

    def test_rejects_source_snapshot_evidence_projection_removal(self) -> None:
        acceptance = copy.deepcopy(self.acceptance)
        criterion = next(
            item
            for item in acceptance["acceptanceCriteria"]
            if item["id"] == "acceptance.software-engineering-lifecycle-specialization"
        )
        criterion["evidenceIds"].remove(
            "evidence.multidimensional-software-engineering-source-snapshot-"
            "2026-07-31"
        )
        with self.assertRaisesRegex(RuntimeError, "evidence mapping drifted"):
            self.validate(acceptance=acceptance)

    def test_rejects_semantic_authority_continuity_evidence_removal(self) -> None:
        acceptance = copy.deepcopy(self.acceptance)
        criterion = next(
            item
            for item in acceptance["acceptanceCriteria"]
            if item["id"] == "acceptance.end-to-end-process-fidelity"
        )
        criterion["evidenceIds"].remove(
            "evidence.human-ai-collaboration-semantic-authority-"
            "continuity-protocol-2026-07-28"
        )
        with self.assertRaisesRegex(RuntimeError, "evidence mapping drifted"):
            self.validate(acceptance=acceptance)

    def test_rejects_current_matt_exposure_refresh_evidence_removal(self) -> None:
        acceptance = copy.deepcopy(self.acceptance)
        criterion = next(
            item
            for item in acceptance["acceptanceCriteria"]
            if item["id"] == "acceptance.end-to-end-process-fidelity"
        )
        criterion["evidenceIds"].remove(
            "evidence.human-ai-collaboration-semantic-authority-"
            "current-matt-no-model-exposure-refresh-2026-07-31"
        )
        with self.assertRaisesRegex(RuntimeError, "evidence mapping drifted"):
            self.validate(acceptance=acceptance)

    def test_rejects_native_local_exposure_evidence_removal(self) -> None:
        acceptance = copy.deepcopy(self.acceptance)
        criterion = next(
            item
            for item in acceptance["acceptanceCriteria"]
            if item["id"] == "acceptance.end-to-end-process-fidelity"
        )
        criterion["evidenceIds"].remove(
            "evidence.human-ai-collaboration-semantic-authority-native-local-"
            "no-model-exposure-and-oracle-2026-08-01"
        )
        with self.assertRaisesRegex(RuntimeError, "evidence mapping drifted"):
            self.validate(acceptance=acceptance)


if __name__ == "__main__":
    unittest.main()
