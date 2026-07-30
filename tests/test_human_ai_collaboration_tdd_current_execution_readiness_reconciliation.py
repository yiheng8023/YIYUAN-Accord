from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from scripts.validate_human_ai_collaboration_tdd_current_execution_readiness_reconciliation import (
    ROOT,
    RECONCILIATION_PATH,
    validate_reconciliation,
)


class HumanAiCollaborationTddCurrentExecutionReadinessReconciliationTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls) -> None:
        cls.document = json.loads(
            (ROOT / RECONCILIATION_PATH).read_text(encoding="utf-8")
        )

    def mutated(self) -> dict:
        return copy.deepcopy(self.document)

    def assert_rejected(self, document: dict) -> None:
        with self.assertRaises(RuntimeError):
            validate_reconciliation(document)

    def test_current_reconciliation_is_valid(self) -> None:
        validate_reconciliation(self.mutated())

    def test_rejects_source_binding_drift(self) -> None:
        document = self.mutated()
        document["sourceBindings"][0]["sha256"] = "0" * 64
        self.assert_rejected(document)

    def test_rejects_artifact_identity_drift(self) -> None:
        document = self.mutated()
        document["currentArtifactIdentities"][0]["bytes"] += 1
        self.assert_rejected(document)

    def test_rejects_missing_candidate(self) -> None:
        document = self.mutated()
        document["candidateReconciliation"].pop()
        self.assert_rejected(document)

    def test_rejects_candidate_execution_promotion(self) -> None:
        document = self.mutated()
        document["candidateReconciliation"][0][
            "currentExecutionAuthorized"
        ] = True
        self.assert_rejected(document)

    def test_rejects_release_admission_promotion(self) -> None:
        document = self.mutated()
        document["candidateReconciliation"][1][
            "approvedReleaseAdmission"
        ] = True
        self.assert_rejected(document)

    def test_rejects_protocol_gate_promotion(self) -> None:
        document = self.mutated()
        gate = next(
            row
            for row in document["gateReconciliation"]
            if row["gateId"] == "gate.protocol-execution-eligibility"
        )
        gate["status"] = "satisfied"
        self.assert_rejected(document)

    def test_rejects_freshness_gate_promotion(self) -> None:
        document = self.mutated()
        gate = next(
            row
            for row in document["gateReconciliation"]
            if row["gateId"]
            == "gate.dispatch-source-and-toolchain-freshness"
        )
        gate["status"] = "satisfied"
        self.assert_rejected(document)

    def test_rejects_adapter_envelope_conflation(self) -> None:
        document = self.mutated()
        gate = next(
            row
            for row in document["gateReconciliation"]
            if row["gateId"] == "gate.dispatch-authorization-envelope"
        )
        gate["blockers"] = [
            "static admission is sufficient for current dispatch"
        ]
        self.assert_rejected(document)

    def test_rejects_live_ledger_promotion(self) -> None:
        document = self.mutated()
        document["decision"]["liveLedgerAuthorityConfigured"] = True
        self.assert_rejected(document)

    def test_rejects_materialization_freshness_promotion(self) -> None:
        document = self.mutated()
        document["decision"][
            "sourceSnapshotToMaterializationFreshnessSatisfied"
        ] = True
        self.assert_rejected(document)

    def test_rejects_real_resource_contract_promotion(self) -> None:
        document = self.mutated()
        document["decision"]["realAppServerResourceContractSatisfied"] = True
        self.assert_rejected(document)

    def test_rejects_cross_process_atomicity_promotion(self) -> None:
        document = self.mutated()
        document["decision"]["crossProcessAtomicitySatisfied"] = True
        self.assert_rejected(document)

    def test_rejects_crash_recovery_promotion(self) -> None:
        document = self.mutated()
        document["decision"]["crashRecoverySatisfied"] = True
        self.assert_rejected(document)

    def test_rejects_formal_runner_integration_promotion(self) -> None:
        document = self.mutated()
        document["decision"]["formalRunnerIntegratedWithDispatchGate"] = True
        self.assert_rejected(document)

    def test_rejects_diagnostic_runner_integration_promotion(self) -> None:
        document = self.mutated()
        document["decision"][
            "diagnosticRunnerOrSharedTransportIntegrated"
        ] = True
        self.assert_rejected(document)

    def test_rejects_static_audit_freshness_conflation(self) -> None:
        document = self.mutated()
        gate = next(
            row
            for row in document["gateReconciliation"]
            if row["gateId"] == "gate.dispatch-authorization-envelope"
        )
        gate["blockers"] = [
            item
            for item in gate["blockers"]
            if "historical static gap audit permanently binds" not in item
        ]
        self.assert_rejected(document)

    def test_rejects_pre_send_intent_gap_deletion(self) -> None:
        document = self.mutated()
        gate = next(
            row
            for row in document["gateReconciliation"]
            if row["gateId"] == "gate.dispatch-identity-ledger"
        )
        gate["blockers"] = [
            item
            for item in gate["blockers"]
            if "thread-start-intent" not in item
        ]
        self.assert_rejected(document)

    def test_rejects_current_execution_ready_promotion(self) -> None:
        document = self.mutated()
        document["decision"]["currentCandidateExecutionReady"] = True
        self.assert_rejected(document)

    def test_rejects_model_dispatch_claim(self) -> None:
        document = self.mutated()
        document["decision"]["modelRequestSent"] = True
        self.assert_rejected(document)

    def test_rejects_value_claim(self) -> None:
        document = self.mutated()
        document["claimBoundary"]["candidateValueProved"] = True
        self.assert_rejected(document)

    def test_rejects_residual_gap_claim(self) -> None:
        document = self.mutated()
        document["claimBoundary"]["selfAuthoredResidualGapProved"] = True
        self.assert_rejected(document)

    def test_rejects_side_effect_record(self) -> None:
        document = self.mutated()
        document["authorityBoundary"]["appServerStarted"] = True
        self.assert_rejected(document)


if __name__ == "__main__":
    unittest.main()
