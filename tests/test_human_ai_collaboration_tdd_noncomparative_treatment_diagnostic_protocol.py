from __future__ import annotations

import copy
import json
import unittest

from scripts.validate_human_ai_collaboration_tdd_noncomparative_treatment_diagnostic_protocol import (
    PROTOCOL_PATH,
    ROOT,
    validate_protocol,
)


def load() -> dict:
    return json.loads((ROOT / PROTOCOL_PATH).read_text(encoding="utf-8"))


class HumanAiCollaborationTddNoncomparativeTreatmentDiagnosticProtocolTests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.document = load()

    def test_current_protocol_is_valid(self) -> None:
        validate_protocol(self.document)

    def test_rejects_live_diagnostic_promotion(self) -> None:
        document = copy.deepcopy(self.document)
        document["decision"]["liveDiagnosticStarted"] = True
        with self.assertRaisesRegex(RuntimeError, "decision boundary"):
            validate_protocol(document)

    def test_rejects_unlocked_external_capability_authority(self) -> None:
        document = copy.deepcopy(self.document)
        document["authorityBoundary"]["mcpAppHookOrBrowserUseAuthorized"] = True
        with self.assertRaisesRegex(RuntimeError, "authority boundary"):
            validate_protocol(document)

    def test_rejects_removed_routing_exclusion(self) -> None:
        document = copy.deepcopy(self.document)
        document["routingDecision"]["excludedCapabilities"].remove(
            "CC Switch mutation"
        )
        with self.assertRaisesRegex(RuntimeError, "routing decision"):
            validate_protocol(document)

    def test_rejects_pairwise_comparison(self) -> None:
        document = copy.deepcopy(self.document)
        document["diagnosticDesign"]["pairwiseComparisonAllowed"] = True
        with self.assertRaisesRegex(RuntimeError, "noncomparative design"):
            validate_protocol(document)

    def test_rejects_shared_drift_without_batch_abort(self) -> None:
        document = copy.deepcopy(self.document)
        document["diagnosticDesign"]["abortBothOnSharedControlPlaneDrift"] = False
        with self.assertRaisesRegex(RuntimeError, "noncomparative design"):
            validate_protocol(document)

    def test_rejects_removed_host_drift_stop(self) -> None:
        document = copy.deepcopy(self.document)
        document["stopConditions"].remove(
            "model, effort, fallback, sandbox, network, ephemeral, plugin, or MCP setting drift"
        )
        with self.assertRaisesRegex(RuntimeError, "stop condition"):
            validate_protocol(document)

    def test_rejects_more_than_one_dispatch_per_candidate(self) -> None:
        document = copy.deepcopy(self.document)
        document["diagnosticDesign"]["maximumDispatchesPerCandidate"] = 2
        with self.assertRaisesRegex(RuntimeError, "dispatch cap"):
            validate_protocol(document)

    def test_rejects_candidate_preference_claim(self) -> None:
        document = copy.deepcopy(self.document)
        document["claimBoundary"]["candidatePreference"] = True
        with self.assertRaisesRegex(RuntimeError, "claim boundary"):
            validate_protocol(document)

    def test_rejects_current_matt_projection_as_release_payload(self) -> None:
        document = copy.deepcopy(self.document)
        document["candidates"][0]["governance"][
            "exactProjectionIsApprovedReleasePayload"
        ] = True
        with self.assertRaisesRegex(RuntimeError, "governance boundary"):
            validate_protocol(document)

    def test_rejects_superpowers_as_repository_approved(self) -> None:
        document = copy.deepcopy(self.document)
        document["candidates"][1]["governance"][
            "repositoryApprovedReleaseEntry"
        ] = True
        with self.assertRaisesRegex(RuntimeError, "governance boundary"):
            validate_protocol(document)

    def test_rejects_source_digest_drift(self) -> None:
        document = copy.deepcopy(self.document)
        document["candidates"][0]["files"][0]["sha256"] = "0" * 64
        with self.assertRaisesRegex(RuntimeError, "candidate source binding"):
            validate_protocol(document)

    def test_rejects_missing_rematerialization_gate(self) -> None:
        document = copy.deepcopy(self.document)
        document["preDispatchGates"][
            "exactProjectionRematerializedAndReverifiedAtDispatch"
        ] = False
        with self.assertRaisesRegex(RuntimeError, "pre-dispatch gate"):
            validate_protocol(document)

    def test_rejects_missing_source_governance_preflight_binding(self) -> None:
        document = copy.deepcopy(self.document)
        document["decision"].pop("sourceGovernancePreflightEvidence", None)
        with self.assertRaisesRegex(RuntimeError, "decision boundary"):
            validate_protocol(document)

    def test_rejects_source_governance_preflight_hash_drift(self) -> None:
        document = copy.deepcopy(self.document)
        document["decision"]["sourceGovernancePreflightFileSha256"] = "0" * 64
        with self.assertRaisesRegex(RuntimeError, "decision boundary"):
            validate_protocol(document)

    def test_rejects_missing_exact_candidate_admission_gap_audit(self) -> None:
        document = copy.deepcopy(self.document)
        document["decision"].pop(
            "exactCandidateAdmissionGapAuditEvidence",
            None,
        )
        with self.assertRaisesRegex(RuntimeError, "decision boundary"):
            validate_protocol(document)

    def test_rejects_admission_decision_promotion(self) -> None:
        document = copy.deepcopy(self.document)
        document["decision"]["candidateAdmissionDecisionMade"] = True
        with self.assertRaisesRegex(RuntimeError, "decision boundary"):
            validate_protocol(document)

    def test_rejects_missing_dispatch_identity_ledger_poc(self) -> None:
        document = copy.deepcopy(self.document)
        document["decision"].pop("dispatchIdentityLedgerPocEvidence", None)
        with self.assertRaisesRegex(RuntimeError, "decision boundary"):
            validate_protocol(document)

    def test_rejects_missing_dispatch_authorization_adapter_poc(self) -> None:
        document = copy.deepcopy(self.document)
        document["decision"].pop(
            "dispatchAuthorizationAdapterPocEvidence",
            None,
        )
        with self.assertRaisesRegex(RuntimeError, "decision boundary"):
            validate_protocol(document)

    def test_rejects_missing_runner_preflight_poc(self) -> None:
        document = copy.deepcopy(self.document)
        document["decision"].pop("runnerPreflightPocEvidence", None)
        with self.assertRaisesRegex(RuntimeError, "decision boundary"):
            validate_protocol(document)

    def test_rejects_live_ledger_authority_promotion(self) -> None:
        document = copy.deepcopy(self.document)
        document["decision"]["liveLedgerAuthorityConfigured"] = True
        with self.assertRaisesRegex(RuntimeError, "decision boundary"):
            validate_protocol(document)

    def test_rejects_live_materialization_freshness_promotion(self) -> None:
        document = copy.deepcopy(self.document)
        document["decision"][
            "sourceSnapshotToFactoryMaterializationFreshnessClosed"
        ] = True
        with self.assertRaisesRegex(RuntimeError, "decision boundary"):
            validate_protocol(document)

    def test_rejects_failure_event_recovery_promotion(self) -> None:
        document = copy.deepcopy(self.document)
        document["decision"]["failureEventAppendRecoveryImplemented"] = True
        with self.assertRaisesRegex(RuntimeError, "decision boundary"):
            validate_protocol(document)

    def test_rejects_structured_handle_validation_demotion(self) -> None:
        document = copy.deepcopy(self.document)
        document["decision"]["handleValidationBeyondNoneImplemented"] = False
        with self.assertRaisesRegex(RuntimeError, "decision boundary"):
            validate_protocol(document)

    def test_rejects_system_global_cap_promotion(self) -> None:
        document = copy.deepcopy(self.document)
        document["decision"]["systemGlobalDispatchCapProved"] = True
        with self.assertRaisesRegex(RuntimeError, "decision boundary"):
            validate_protocol(document)

    def test_rejects_runner_preflight_evidence_hash_drift(self) -> None:
        document = copy.deepcopy(self.document)
        document["decision"]["runnerPreflightPocEvidenceFileSha256"] = (
            "0" * 64
        )
        with self.assertRaisesRegex(RuntimeError, "decision boundary"):
            validate_protocol(document)

    def test_rejects_runtime_dispatch_cap_promotion(self) -> None:
        document = copy.deepcopy(self.document)
        document["runtimeEnforcement"]["singleDispatchCapRuntimeEnforced"] = True
        with self.assertRaisesRegex(RuntimeError, "runtime enforcement"):
            validate_protocol(document)

    def test_rejects_task_success_as_comparative_outcome(self) -> None:
        document = copy.deepcopy(self.document)
        document["observationContract"][
            "taskOutcomeUse"
        ] = "score candidates and choose a winner"
        with self.assertRaisesRegex(RuntimeError, "observation contract"):
            validate_protocol(document)


if __name__ == "__main__":
    unittest.main()
