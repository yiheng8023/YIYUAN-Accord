from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from scripts.validate_human_ai_collaboration_new_feature_tdd_protocol import (
    PROTOCOL_PATH,
    validate_protocol,
)


ROOT = Path(__file__).resolve().parent.parent


class HumanAiCollaborationNewFeatureTddProtocolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.document = json.loads(
            (ROOT / PROTOCOL_PATH).read_text(encoding="utf-8")
        )

    def test_current_protocol_is_valid(self) -> None:
        validate_protocol(self.document, root=ROOT)

    def test_rejects_stale_local_matt_as_current(self) -> None:
        document = copy.deepcopy(self.document)
        document["sourceBindings"][0]["localNavigationCheckoutIsCurrent"] = True
        with self.assertRaisesRegex(RuntimeError, "Matt TDD source boundary"):
            validate_protocol(document, root=ROOT)

    def test_rejects_full_superpowers_treatment(self) -> None:
        document = copy.deepcopy(self.document)
        document["sourceBindings"][1][
            "treatmentBoundary"
        ] = "Full Superpowers plugin"
        document["contentComparison"][
            "fullFrameworkConfoundControl"
        ] = "Full workflow enabled"
        with self.assertRaisesRegex(RuntimeError, "overlap or conflict"):
            validate_protocol(document, root=ROOT)

    def test_rejects_live_run_promotion(self) -> None:
        document = copy.deepcopy(self.document)
        document["decisionBoundary"]["validFormalRepetitionCount"] = 1
        with self.assertRaisesRegex(RuntimeError, "next action"):
            validate_protocol(document, root=ROOT)

    def test_rejects_missing_exact_candidate_admission_gap_audit(self) -> None:
        document = copy.deepcopy(self.document)
        document["decisionBoundary"].pop(
            "exactCandidateAdmissionGapAuditEvidence",
            None,
        )
        with self.assertRaisesRegex(RuntimeError, "audit binding"):
            validate_protocol(document, root=ROOT)

    def test_rejects_missing_dispatch_identity_ledger_poc(self) -> None:
        document = copy.deepcopy(self.document)
        document["decisionBoundary"].pop(
            "dispatchIdentityLedgerPocEvidence",
            None,
        )
        with self.assertRaisesRegex(RuntimeError, "next action"):
            validate_protocol(document, root=ROOT)

    def test_rejects_missing_dispatch_authorization_adapter_poc(self) -> None:
        document = copy.deepcopy(self.document)
        document["decisionBoundary"].pop(
            "dispatchAuthorizationAdapterPocEvidence",
            None,
        )
        with self.assertRaisesRegex(RuntimeError, "next action"):
            validate_protocol(document, root=ROOT)

    def test_rejects_missing_runner_preflight_poc(self) -> None:
        document = copy.deepcopy(self.document)
        document["decisionBoundary"].pop(
            "runnerPreflightPocEvidence",
            None,
        )
        with self.assertRaisesRegex(RuntimeError, "next action"):
            validate_protocol(document, root=ROOT)

    def test_rejects_live_ledger_authority_promotion(self) -> None:
        document = copy.deepcopy(self.document)
        document["decisionBoundary"]["liveLedgerAuthorityConfigured"] = True
        with self.assertRaisesRegex(RuntimeError, "next action"):
            validate_protocol(document, root=ROOT)

    def test_rejects_live_materialization_freshness_promotion(self) -> None:
        document = copy.deepcopy(self.document)
        document["decisionBoundary"][
            "sourceSnapshotToFactoryMaterializationFreshnessClosed"
        ] = True
        with self.assertRaisesRegex(RuntimeError, "next action"):
            validate_protocol(document, root=ROOT)

    def test_rejects_failure_event_recovery_promotion(self) -> None:
        document = copy.deepcopy(self.document)
        document["decisionBoundary"][
            "failureEventAppendRecoveryImplemented"
        ] = True
        with self.assertRaisesRegex(RuntimeError, "next action"):
            validate_protocol(document, root=ROOT)

    def test_rejects_structured_handle_validation_demotion(self) -> None:
        document = copy.deepcopy(self.document)
        document["decisionBoundary"][
            "handleValidationBeyondNoneImplemented"
        ] = False
        with self.assertRaisesRegex(RuntimeError, "next action"):
            validate_protocol(document, root=ROOT)

    def test_rejects_system_global_cap_promotion(self) -> None:
        document = copy.deepcopy(self.document)
        document["decisionBoundary"]["systemGlobalDispatchCapProved"] = True
        with self.assertRaisesRegex(RuntimeError, "next action"):
            validate_protocol(document, root=ROOT)

    def test_rejects_runner_preflight_evidence_hash_drift(self) -> None:
        document = copy.deepcopy(self.document)
        document["decisionBoundary"][
            "runnerPreflightPocEvidenceFileSha256"
        ] = "0" * 64
        with self.assertRaisesRegex(RuntimeError, "next action"):
            validate_protocol(document, root=ROOT)

    def test_rejects_unordered_green_as_valid_measurement(self) -> None:
        document = copy.deepcopy(self.document)
        document["processInstrumentationGate"][
            "claimLimit"
        ] = "Final green is enough."
        with self.assertRaisesRegex(RuntimeError, "instrumentation boundary"):
            validate_protocol(document, root=ROOT)

    def test_rejects_builder_content_hash_drift(self) -> None:
        document = copy.deepcopy(self.document)
        document["fixtureArtifacts"]["builderSha256"] = "0" * 64
        with self.assertRaisesRegex(RuntimeError, "content hash"):
            validate_protocol(document, root=ROOT)


if __name__ == "__main__":
    unittest.main()
