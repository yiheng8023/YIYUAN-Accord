import copy
import json
from pathlib import Path
import unittest

from scripts.validate_harness_three_lane_program_acceptance_reconciliation import (
    PROGRAM_PATH,
    RECONCILIATION_PATH,
    validate_reconciliation,
)


ROOT = Path(__file__).resolve().parent.parent


class HarnessThreeLaneProgramAcceptanceReconciliationTests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.document = json.loads(
            (ROOT / RECONCILIATION_PATH).read_text(encoding="utf-8")
        )
        self.program = json.loads(
            (ROOT / PROGRAM_PATH).read_text(encoding="utf-8")
        )

    def test_current_reconciliation_is_valid(self) -> None:
        validate_reconciliation(
            self.document,
            root=ROOT,
            program=self.program,
        )

    def test_external_or_host_action_cannot_be_claimed(self) -> None:
        mutated = copy.deepcopy(self.document)
        mutated["executionBoundary"]["hostConfigurationChanged"] = True
        with self.assertRaisesRegex(RuntimeError, "execution boundary"):
            validate_reconciliation(
                mutated,
                root=ROOT,
                program=self.program,
            )

    def test_host_probe_model_request_scope_cannot_be_promoted(self) -> None:
        mutated = copy.deepcopy(self.document)
        mutated["executionBoundary"]["hostProbeModelRequestSent"] = True
        with self.assertRaisesRegex(RuntimeError, "execution boundary"):
            validate_reconciliation(
                mutated,
                root=ROOT,
                program=self.program,
            )

    def test_evidence_hash_drift_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.document)
        mutated["lanes"][0]["evidence"][0]["sha256"] = "0" * 64
        with self.assertRaisesRegex(RuntimeError, "hash drifted"):
            validate_reconciliation(
                mutated,
                root=ROOT,
                program=self.program,
            )

    def test_dynamic_acceptance_must_remain_partial(self) -> None:
        mutated = copy.deepcopy(self.program)
        criterion = next(
            item
            for item in mutated["acceptanceCriteria"]
            if item["id"]
            == "acceptance.dynamic-runtime-control-gap-research"
        )
        criterion["assessment"] = "verified"
        with self.assertRaisesRegex(RuntimeError, "projection drifted"):
            validate_reconciliation(
                self.document,
                root=ROOT,
                program=mutated,
            )

    def test_additive_program_evidence_support_must_be_single_target(
        self,
    ) -> None:
        mutated = copy.deepcopy(self.program)
        evidence = next(
            item
            for item in mutated["evidence"]
            if item["id"]
            == "evidence.context-handoff-receiver-delta-ledger-2026-07-27"
        )
        evidence["supports"] = [
            "acceptance.end-to-end-process-fidelity",
            "acceptance.residual-gap-proof",
        ]
        with self.assertRaisesRegex(RuntimeError, "program mapping drifted"):
            validate_reconciliation(
                self.document,
                root=ROOT,
                program=mutated,
            )

    def test_additive_program_evidence_reverse_mapping_must_be_unique(
        self,
    ) -> None:
        mutated = copy.deepcopy(self.program)
        criterion = next(
            item
            for item in mutated["acceptanceCriteria"]
            if item["id"] == "acceptance.native-task-orchestration-boundary"
        )
        criterion["evidenceIds"].append(
            "evidence.mcp-thread-creator-close-observer-acquisition-path-admission-2026-07-27"
        )
        with self.assertRaisesRegex(RuntimeError, "reverse mapping is not unique"):
            validate_reconciliation(
                self.document,
                root=ROOT,
                program=mutated,
            )

    def test_additive_program_evidence_target_must_remain_partial(self) -> None:
        mutated = copy.deepcopy(self.program)
        criterion = next(
            item
            for item in mutated["acceptanceCriteria"]
            if item["id"] == "acceptance.end-to-end-process-fidelity"
        )
        criterion["assessment"] = "verified"
        with self.assertRaisesRegex(RuntimeError, "target must remain partial"):
            validate_reconciliation(
                self.document,
                root=ROOT,
                program=mutated,
            )

    def test_source_backed_transport_cannot_become_context_proof(self) -> None:
        mutated = copy.deepcopy(self.document)
        mutated["lanes"][0]["unproved"].remove(
            "automatic new-thread creation"
        )
        with self.assertRaisesRegex(RuntimeError, "documentation|claim"):
            validate_reconciliation(
                mutated,
                root=ROOT,
                program=self.program,
            )

    def test_shared_projection_cannot_become_atomic_snapshot_proof(self) -> None:
        mutated = copy.deepcopy(self.document)
        mutated["lanes"][0]["unproved"].remove(
            "atomic build/create snapshot"
        )
        with self.assertRaisesRegex(RuntimeError, "documentation|claim"):
            validate_reconciliation(
                mutated,
                root=ROOT,
                program=self.program,
            )

    def test_receiver_delta_ledger_cannot_become_weak_agent_proof(self) -> None:
        mutated = copy.deepcopy(self.document)
        mutated["lanes"][0]["unproved"].remove(
            "weak-Agent receiver behavior or cross-host receiver behavior"
        )
        with self.assertRaisesRegex(RuntimeError, "documentation|claim"):
            validate_reconciliation(
                mutated,
                root=ROOT,
                program=self.program,
            )

    def test_user_repository_safety_cannot_be_inferred(self) -> None:
        mutated = copy.deepcopy(self.document)
        mutated["lanes"][1]["unproved"].remove(
            "safe creation or mutation in a bound user repository"
        )
        with self.assertRaisesRegex(RuntimeError, "documentation|claim"):
            validate_reconciliation(
                mutated,
                root=ROOT,
                program=self.program,
            )

    def test_same_thread_mcp_control_cannot_be_promoted(self) -> None:
        mutated = copy.deepcopy(self.document)
        mutated["lanes"][2]["unproved"].remove(
            "same-thread live enable or disable"
        )
        with self.assertRaisesRegex(RuntimeError, "documentation|claim"):
            validate_reconciliation(
                mutated,
                root=ROOT,
                program=self.program,
            )

    def test_invalid_creator_close_calibration_cannot_become_formal_run(
        self,
    ) -> None:
        mutated = copy.deepcopy(self.document)
        mutated["executionBoundary"]["formalCreatorClosePairedRunCount"] = 1
        with self.assertRaisesRegex(RuntimeError, "execution boundary"):
            validate_reconciliation(
                mutated,
                root=ROOT,
                program=self.program,
            )

    def test_creator_close_authority_conflict_cannot_be_erased(self) -> None:
        mutated = copy.deepcopy(self.document)
        mutated["executionBoundary"][
            "creatorCloseAuthorityConflictRecorded"
        ] = False
        with self.assertRaisesRegex(RuntimeError, "execution boundary"):
            validate_reconciliation(
                mutated,
                root=ROOT,
                program=self.program,
            )

    def test_offline_remediation_cannot_become_live_rerun(self) -> None:
        mutated = copy.deepcopy(self.document)
        mutated["executionBoundary"][
            "creatorCloseLiveRerunPerformed"
        ] = True
        with self.assertRaisesRegex(RuntimeError, "execution boundary"):
            validate_reconciliation(
                mutated,
                root=ROOT,
                program=self.program,
            )

    def test_auto_attach_v2_offline_scenarios_cannot_become_live_runs(
        self,
    ) -> None:
        mutated = copy.deepcopy(self.document)
        mutated["executionBoundary"]["mcpAutoAttachV2FormalLiveRunCount"] = 1
        with self.assertRaisesRegex(RuntimeError, "execution boundary"):
            validate_reconciliation(
                mutated,
                root=ROOT,
                program=self.program,
            )

    def test_auto_attach_gate_cannot_become_second_subscription_proof(
        self,
    ) -> None:
        mutated = copy.deepcopy(self.document)
        mutated["lanes"][2]["unproved"].remove(
            "auto-attach as a second independently releasable subscription or owner"
        )
        with self.assertRaisesRegex(RuntimeError, "documentation|claim"):
            validate_reconciliation(
                mutated,
                root=ROOT,
                program=self.program,
            )

    def test_auto_attach_v2_live_readiness_remains_unproved(self) -> None:
        mutated = copy.deepcopy(self.document)
        mutated["lanes"][2]["unproved"].remove(
            "auto-attach v2 live readiness, execution, or outcome"
        )
        with self.assertRaisesRegex(RuntimeError, "documentation|claim"):
            validate_reconciliation(
                mutated,
                root=ROOT,
                program=self.program,
            )

    def test_unsubscribe_cannot_be_promoted_to_final_release_semantics(
        self,
    ) -> None:
        mutated = copy.deepcopy(self.document)
        mutated["lanes"][2]["unproved"].remove(
            "overlapping task or subscription ownership and final-release semantics"
        )
        with self.assertRaisesRegex(RuntimeError, "documentation|claim"):
            validate_reconciliation(
                mutated,
                root=ROOT,
                program=self.program,
            )

    def test_self_authored_controller_remains_unjustified(self) -> None:
        mutated = copy.deepcopy(self.document)
        mutated["decision"]["selfAuthoredRuntimeControllerJustified"] = True
        with self.assertRaisesRegex(RuntimeError, "decision boundary"):
            validate_reconciliation(
                mutated,
                root=ROOT,
                program=self.program,
            )

    def test_cleanup_authority_cannot_be_implied(self) -> None:
        mutated = copy.deepcopy(self.document)
        mutated["cleanupBoundary"]["cleanupAuthorityGranted"] = True
        with self.assertRaisesRegex(RuntimeError, "cleanup boundary"):
            validate_reconciliation(
                mutated,
                root=ROOT,
                program=self.program,
            )

    def test_invalid_calibration_cleanup_debt_cannot_be_deleted(self) -> None:
        mutated = copy.deepcopy(self.document)
        mutated["cleanupBoundary"][
            "invalidCreatorCloseCalibrationDeletionAuthorized"
        ] = True
        with self.assertRaisesRegex(RuntimeError, "cleanup boundary"):
            validate_reconciliation(
                mutated,
                root=ROOT,
                program=self.program,
            )

    def test_supported_boundary_cannot_be_broadened(self) -> None:
        mutated = copy.deepcopy(self.document)
        mutated["lanes"][2]["supportedBoundary"] = (
            "All MCP reload and task-end release behavior is proved."
        )
        with self.assertRaisesRegex(RuntimeError, "claim boundary"):
            validate_reconciliation(
                mutated,
                root=ROOT,
                program=self.program,
            )

    def test_forbidden_promotion_cannot_be_weakened(self) -> None:
        mutated = copy.deepcopy(self.document)
        mutated["lanes"][2]["forbiddenPromotion"] = "Promotion is unrestricted."
        with self.assertRaisesRegex(RuntimeError, "claim boundary"):
            validate_reconciliation(
                mutated,
                root=ROOT,
                program=self.program,
            )

    def test_top_level_claim_limit_cannot_be_broadened(self) -> None:
        mutated = copy.deepcopy(self.document)
        mutated["claimLimit"] = "All three lanes are universally verified."
        with self.assertRaisesRegex(RuntimeError, "documentation binding"):
            validate_reconciliation(
                mutated,
                root=ROOT,
                program=self.program,
            )


if __name__ == "__main__":
    unittest.main()
