from __future__ import annotations

import copy
import json
import unittest

from scripts.validate_human_ai_collaboration_tdd_noncomparative_dispatch_authorization_adapter_poc_evidence import (
    EVIDENCE_PATH,
    ROOT,
    validate_evidence,
)


def load() -> dict:
    return json.loads((ROOT / EVIDENCE_PATH).read_text(encoding="utf-8"))


class HumanAiCollaborationTddNoncomparativeDispatchAuthorizationAdapterPocEvidenceTests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.document = load()

    def test_current_evidence_is_valid(self) -> None:
        validate_evidence(self.document)

    def test_rejects_current_candidate_eligibility_promotion(self) -> None:
        document = copy.deepcopy(self.document)
        document["decision"]["currentExactCandidateExecutionEligible"] = True
        with self.assertRaisesRegex(RuntimeError, "decision boundary"):
            validate_evidence(document)

    def test_rejects_live_runner_integration_promotion(self) -> None:
        document = copy.deepcopy(self.document)
        document["claimBoundary"]["liveRunnerIntegrationProved"] = True
        with self.assertRaisesRegex(RuntimeError, "claim boundary"):
            validate_evidence(document)

    def test_rejects_synthetic_admission_as_real_admission(self) -> None:
        document = copy.deepcopy(self.document)
        document["decision"]["repositoryAdmissionRecordCreated"] = True
        with self.assertRaisesRegex(RuntimeError, "decision boundary"):
            validate_evidence(document)

    def test_rejects_adapter_hash_drift(self) -> None:
        document = copy.deepcopy(self.document)
        document["artifacts"][0]["sha256"] = "0" * 64
        with self.assertRaisesRegex(RuntimeError, "artifact binding"):
            validate_evidence(document)


if __name__ == "__main__":
    unittest.main()
