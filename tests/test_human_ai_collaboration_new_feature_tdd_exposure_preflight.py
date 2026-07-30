from __future__ import annotations

import copy
import json
import unittest

from scripts.validate_human_ai_collaboration_new_feature_tdd_exposure_preflight import (
    EVIDENCE_PATH,
    ROOT,
    validate_evidence,
)


def load() -> dict:
    return json.loads((ROOT / EVIDENCE_PATH).read_text(encoding="utf-8"))


class HumanAiCollaborationNewFeatureTddExposurePreflightTests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.document = load()

    def test_current_evidence_is_valid(self) -> None:
        validate_evidence(self.document)

    def test_rejects_body_delivery_promotion(self) -> None:
        document = copy.deepcopy(self.document)
        document["claimBoundary"]["provesSkillBodyDelivery"] = True
        with self.assertRaisesRegex(RuntimeError, "claim boundary"):
            validate_evidence(document)

    def test_rejects_started_turn(self) -> None:
        document = copy.deepcopy(self.document)
        document["host"]["turnStarted"] = True
        with self.assertRaisesRegex(RuntimeError, "host boundary"):
            validate_evidence(document)

    def test_rejects_candidate_inventory_count_drift(self) -> None:
        document = copy.deepcopy(self.document)
        document["candidateEvidence"][0]["preflight"]["skillCount"] = 111
        with self.assertRaisesRegex(RuntimeError, "inventory or stability"):
            validate_evidence(document)

    def test_rejects_candidate_preference(self) -> None:
        document = copy.deepcopy(self.document)
        document["decision"]["candidatePreferenceAllowed"] = True
        with self.assertRaisesRegex(RuntimeError, "decision was promoted"):
            validate_evidence(document)

    def test_rejects_projected_file_evidence_drift(self) -> None:
        document = copy.deepcopy(self.document)
        document["candidateEvidence"][0]["projectedFiles"][0][
            "sha256"
        ] = "0" * 64
        with self.assertRaisesRegex(RuntimeError, "projected file evidence"):
            validate_evidence(document)

    def test_rejects_selected_count_drift(self) -> None:
        document = copy.deepcopy(self.document)
        document["candidateEvidence"][1]["preflight"][
            "selectedEnabledConfigurableSkillCount"
        ] = 2
        with self.assertRaisesRegex(RuntimeError, "inventory or stability"):
            validate_evidence(document)

    def test_rejects_stability_scope_promotion(self) -> None:
        document = copy.deepcopy(self.document)
        document["rawEvidenceBoundary"][
            "projectionStabilityObservationScope"
        ] = "entire disposable root"
        with self.assertRaisesRegex(RuntimeError, "observation-scope"):
            validate_evidence(document)


if __name__ == "__main__":
    unittest.main()
