from __future__ import annotations

import copy
import json
import unittest

from scripts.validate_human_ai_collaboration_tdd_noncomparative_runner_preflight_poc_evidence import (
    EVIDENCE_PATH,
    ROOT,
    validate_evidence,
)


def load() -> dict:
    return json.loads((ROOT / EVIDENCE_PATH).read_text(encoding="utf-8"))


class HumanAiCollaborationTddNoncomparativeRunnerPreflightPocEvidenceTests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.document = load()

    def test_current_evidence_is_valid(self) -> None:
        validate_evidence(self.document)

    def test_rejects_current_dispatch_authorization_promotion(self) -> None:
        document = copy.deepcopy(self.document)
        document["decision"]["currentCandidateDispatchAuthorized"] = True
        with self.assertRaisesRegex(RuntimeError, "decision boundary"):
            validate_evidence(document)

    def test_rejects_fake_factory_as_live_app_server_proof(self) -> None:
        document = copy.deepcopy(self.document)
        document["claimBoundary"][
            "liveAppServerPreconstructionOrderingProved"
        ] = True
        with self.assertRaisesRegex(RuntimeError, "claim boundary"):
            validate_evidence(document)

    def test_rejects_automatic_recovery_promotion(self) -> None:
        document = copy.deepcopy(self.document)
        document["decision"][
            "automaticReservationReleaseOrRetryImplemented"
        ] = True
        with self.assertRaisesRegex(RuntimeError, "decision boundary"):
            validate_evidence(document)

    def test_rejects_live_ledger_authority_promotion(self) -> None:
        document = copy.deepcopy(self.document)
        document["decision"]["liveLedgerAuthorityConfigured"] = True
        with self.assertRaisesRegex(RuntimeError, "decision boundary"):
            validate_evidence(document)

    def test_rejects_live_materialization_freshness_promotion(self) -> None:
        document = copy.deepcopy(self.document)
        document["decision"][
            "sourceSnapshotToFactoryMaterializationFreshnessProved"
        ] = True
        with self.assertRaisesRegex(RuntimeError, "decision boundary"):
            validate_evidence(document)

    def test_rejects_failure_event_recovery_promotion(self) -> None:
        document = copy.deepcopy(self.document)
        document["claimBoundary"]["failureEventAppendRecoveryProved"] = True
        with self.assertRaisesRegex(RuntimeError, "claim boundary"):
            validate_evidence(document)

    def test_rejects_non_none_handle_validation_promotion(self) -> None:
        document = copy.deepcopy(self.document)
        document["claimBoundary"]["handleValidationBeyondNoneProved"] = True
        with self.assertRaisesRegex(RuntimeError, "claim boundary"):
            validate_evidence(document)

    def test_rejects_system_global_dispatch_cap_promotion(self) -> None:
        document = copy.deepcopy(self.document)
        document["claimBoundary"]["systemGlobalDispatchCapProved"] = True
        with self.assertRaisesRegex(RuntimeError, "claim boundary"):
            validate_evidence(document)

    def test_rejects_runner_wrapper_hash_drift(self) -> None:
        document = copy.deepcopy(self.document)
        document["artifacts"][0]["sha256"] = "0" * 64
        with self.assertRaisesRegex(RuntimeError, "artifact binding"):
            validate_evidence(document)


if __name__ == "__main__":
    unittest.main()
