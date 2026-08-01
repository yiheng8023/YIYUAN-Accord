from __future__ import annotations

import copy
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from scripts.build_human_ai_collaboration_semantic_authority_execution_plan import (
    compile_execution_plan,
)
from scripts.build_human_ai_collaboration_semantic_authority_live_dispatch_gate import (
    DECISION_SHA256,
    canonical_sha256,
    compile_zero_authority_matrix,
    compile_dispatch_gate,
    evaluate_simulated_phase_observation,
    validate_zero_authority_matrix,
    write_report_atomically,
)


def simulation_receipt(plan: dict) -> dict:
    receipt = {
        "schema": 1,
        "id": "human-ai-collaboration-semantic-authority-live-authority-receipt-v1",
        "status": "test-simulation-only",
        "authorityClass": "test-simulation",
        "scenarioId": plan["scenarioId"],
        "runId": plan["runId"],
        "treatmentId": plan["treatmentId"],
        "planSha256": plan["planSha256"],
        "adapterDecisionSha256": DECISION_SHA256,
        "modelDispatchAuthorized": False,
        "appServerProcessCreationAuthorized": False,
    }
    receipt["receiptSha256"] = canonical_sha256(receipt)
    return receipt


class SemanticAuthorityLiveDispatchGateTests(unittest.TestCase):
    def test_zero_authority_matrix_denies_all_three_treatments(self) -> None:
        report = compile_zero_authority_matrix()

        self.assertEqual("blocked-no-live-authority", report["status"])
        self.assertEqual([], validate_zero_authority_matrix(report))
        self.assertEqual(3, len(report["treatments"]))
        self.assertTrue(
            all(
                row["gate"]["mayCreateAppServerProcess"] is False
                and row["gate"]["modelRequestBudget"] == 0
                and row["gate"]["authorizedPhases"] == []
                for row in report["treatments"]
            )
        )
        self.assertFalse(report["modelRequestSent"])
        self.assertFalse(report["appServerProcessStarted"])

    def test_missing_authority_receipt_denies_process_and_model_budget(self) -> None:
        plan = compile_execution_plan("SEM-NATIVE", "SEM03-LIVE-NATIVE-001")

        gate = compile_dispatch_gate(plan, authority_receipt=None)

        self.assertEqual("blocked-missing-live-authority-receipt", gate["status"])
        self.assertFalse(gate["mayCreateAppServerProcess"])
        self.assertEqual(0, gate["modelRequestBudget"])
        self.assertEqual([], gate["authorizedPhases"])
        self.assertFalse(gate["modelRequestSent"])

    def test_report_rejects_rehashed_inner_runtime_promotion(self) -> None:
        report = compile_zero_authority_matrix()
        mutated = copy.deepcopy(report)
        gate = mutated["treatments"][0]["gate"]
        gate["modelRequestSent"] = True
        gate["gateSha256"] = canonical_sha256(
            {key: value for key, value in gate.items() if key != "gateSha256"}
        )
        mutated["reportSha256"] = canonical_sha256(
            {
                key: value
                for key, value in mutated.items()
                if key != "reportSha256"
            }
        )

        self.assertIn(
            "hard-fail-live-gate-treatment-boundary",
            validate_zero_authority_matrix(mutated),
        )

    def test_report_rejects_rehashed_decision_digest_drift(self) -> None:
        report = compile_zero_authority_matrix()
        mutated = copy.deepcopy(report)
        for row in mutated["treatments"]:
            gate = row["gate"]
            gate["adapterDecisionSha256"] = "0" * 64
            gate["gateSha256"] = canonical_sha256(
                {key: value for key, value in gate.items() if key != "gateSha256"}
            )
        mutated["reportSha256"] = canonical_sha256(
            {
                key: value
                for key, value in mutated.items()
                if key != "reportSha256"
            }
        )

        self.assertIn(
            "hard-fail-live-gate-treatment-boundary",
            validate_zero_authority_matrix(mutated),
        )

    def test_report_rejects_rehashed_claim_ceiling_key_removal(self) -> None:
        report = compile_zero_authority_matrix()
        mutated = copy.deepcopy(report)
        del mutated["claimBoundary"]["loaderInvocationProved"]
        mutated["reportSha256"] = canonical_sha256(
            {
                key: value
                for key, value in mutated.items()
                if key != "reportSha256"
            }
        )

        self.assertIn(
            "hard-fail-live-gate-claim-promotion",
            validate_zero_authority_matrix(mutated),
        )

    def test_atomic_report_write_cleans_staging_on_replace_failure(self) -> None:
        report = compile_zero_authority_matrix()
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "REPORT.json"
            with mock.patch(
                "scripts.build_human_ai_collaboration_semantic_authority_"
                "live_dispatch_gate.os.replace",
                side_effect=OSError("simulated replace failure"),
            ):
                with self.assertRaisesRegex(OSError, "simulated replace failure"):
                    write_report_atomically(output, report)

            self.assertFalse(output.exists())
            self.assertEqual([], list(Path(temporary).iterdir()))

    def test_simulation_receipt_compiles_four_unsent_phase_intents_only(self) -> None:
        plan = compile_execution_plan("SEM-NATIVE", "SEM03-LIVE-NATIVE-001")

        gate = compile_dispatch_gate(
            plan,
            authority_receipt=simulation_receipt(plan),
        )

        self.assertEqual("simulation-ready-no-live-authority", gate["status"])
        self.assertFalse(gate["mayCreateAppServerProcess"])
        self.assertEqual(0, gate["modelRequestBudget"])
        self.assertEqual([], gate["authorizedPhases"])
        self.assertEqual(
            [phase["id"] for phase in plan["lifecyclePhases"]],
            [phase["phaseId"] for phase in gate["simulatedPhases"]],
        )
        self.assertTrue(
            all(
                phase["requestsTransmitted"] is False
                for phase in gate["simulatedPhases"]
            )
        )

    def test_simulated_parent_observation_accepts_exact_completed_phase(self) -> None:
        observation = {
            "phaseId": "SEM-PHASE-1-ELICIT",
            "threadStart": {
                "model": "gpt-5.3-codex-spark",
                "reasoningEffort": "low",
                "providerFallbackAllowed": False,
            },
            "notificationMethods": [
                "turn/started",
                "thread/tokenUsage/updated",
                "turn/completed",
            ],
            "turnTerminalStatus": "completed",
            "modelReroutedObserved": False,
            "writeOutsidePublicRootObserved": False,
            "forbiddenToolObserved": False,
            "appServerProcessExited": True,
            "temporaryRootRemoved": True,
        }

        result = evaluate_simulated_phase_observation(observation)

        self.assertEqual("simulation-phase-pass", result["status"])
        self.assertEqual([], result["failureCodes"])
        self.assertEqual([], result["requiredStopActions"])
        self.assertFalse(result["countsAsLiveEvidence"])

    def test_simulated_reroute_and_unclosed_process_require_interrupt_and_abort(self) -> None:
        observation = {
            "phaseId": "SEM-PHASE-2-MODEL",
            "threadStart": {
                "model": "gpt-5.3-codex-spark",
                "reasoningEffort": "low",
                "providerFallbackAllowed": False,
            },
            "notificationMethods": [
                "turn/started",
                "model/rerouted",
                "thread/tokenUsage/updated",
            ],
            "turnTerminalStatus": "inProgress",
            "modelReroutedObserved": True,
            "writeOutsidePublicRootObserved": False,
            "forbiddenToolObserved": False,
            "appServerProcessExited": False,
            "temporaryRootRemoved": False,
        }

        result = evaluate_simulated_phase_observation(observation)

        self.assertEqual("simulation-phase-fail-closed", result["status"])
        self.assertIn("hard-fail-simulation-model-reroute", result["failureCodes"])
        self.assertIn(
            "hard-fail-simulation-cleanup-boundary",
            result["failureCodes"],
        )
        self.assertEqual(
            [
                "turn/interrupt",
                "abort-app-server-process",
                "stop-before-next-phase",
                "do-not-score-run",
            ],
            result["requiredStopActions"],
        )


if __name__ == "__main__":
    unittest.main()
