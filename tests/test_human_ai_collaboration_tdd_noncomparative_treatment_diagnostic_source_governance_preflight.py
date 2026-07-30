from __future__ import annotations

import copy
import json
import unittest

from scripts.validate_human_ai_collaboration_tdd_noncomparative_treatment_diagnostic_source_governance_preflight import (
    EVIDENCE_PATH,
    ROOT,
    validate_evidence,
)


def load() -> dict:
    return json.loads((ROOT / EVIDENCE_PATH).read_text(encoding="utf-8"))


class HumanAiCollaborationTddNoncomparativeTreatmentDiagnosticSourceGovernancePreflightTests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.document = load()

    def test_current_evidence_is_valid(self) -> None:
        validate_evidence(self.document)

    def test_rejects_live_turn_claim(self) -> None:
        document = copy.deepcopy(self.document)
        document["decision"]["liveDiagnosticStarted"] = True
        with self.assertRaisesRegex(RuntimeError, "decision boundary"):
            validate_evidence(document)

    def test_rejects_matt_remote_main_drift(self) -> None:
        document = copy.deepcopy(self.document)
        document["candidateObservations"][0]["currentMainMatchesPinned"] = False
        with self.assertRaisesRegex(RuntimeError, "Matt observation"):
            validate_evidence(document)

    def test_rejects_superpowers_byte_drift(self) -> None:
        document = copy.deepcopy(self.document)
        document["candidateObservations"][1]["files"][0]["sha256"] = "0" * 64
        with self.assertRaisesRegex(RuntimeError, "candidate source binding"):
            validate_evidence(document)

    def test_rejects_execution_admission_promotion(self) -> None:
        document = copy.deepcopy(self.document)
        document["governanceObservation"][
            "anyExactCandidateExecutionAdmissionSatisfied"
        ] = True
        with self.assertRaisesRegex(RuntimeError, "governance observation"):
            validate_evidence(document)

    def test_rejects_network_replay_claim(self) -> None:
        document = copy.deepcopy(self.document)
        document["rawEvidenceBoundary"]["validatorReplaysGithubApi"] = True
        with self.assertRaisesRegex(RuntimeError, "raw evidence boundary"):
            validate_evidence(document)

    def test_rejects_fresh_for_dispatch_promotion(self) -> None:
        document = copy.deepcopy(self.document)
        document["decision"]["freshForDispatch"] = True
        with self.assertRaisesRegex(RuntimeError, "decision boundary"):
            validate_evidence(document)

    def test_rejects_toolchain_digest_drift(self) -> None:
        document = copy.deepcopy(self.document)
        document["toolchainObservation"]["projectionBuilder"][
            "sha256"
        ] = "0" * 64
        with self.assertRaisesRegex(RuntimeError, "toolchain binding"):
            validate_evidence(document)

    def test_rejects_candidate_value_claim(self) -> None:
        document = copy.deepcopy(self.document)
        document["claimBoundary"]["candidateValue"] = True
        with self.assertRaisesRegex(RuntimeError, "claim boundary"):
            validate_evidence(document)


if __name__ == "__main__":
    unittest.main()
