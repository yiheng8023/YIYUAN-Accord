from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from scripts.evaluate_process_loss_longhorizon_harness_execution_preflight import (
    ACCEPTANCE_PATH,
    MUTATION_CASE_IDS,
    RECORD_PATH,
    evaluate_preflight,
    validate_preflight_record,
    validate_repository_preflight,
)


ROOT = Path(__file__).resolve().parent.parent


class ProcessLossLongHorizonHarnessExecutionPreflightTests(unittest.TestCase):
    def setUp(self) -> None:
        self.record = json.loads((ROOT / RECORD_PATH).read_text(encoding="utf-8"))
        self.request = self.record["syntheticFixture"]["request"]

    def test_repository_preflight_is_valid(self) -> None:
        record = validate_repository_preflight(ROOT)

        self.assertEqual(
            "verified-synthetic-fail-closed-preflight-no-live-execution",
            record["status"],
        )
        self.assertEqual(25, len(record["failureInjectionCaseIds"]))

    def test_complete_synthetic_request_is_eligible_but_nonexecuting(self) -> None:
        result = evaluate_preflight(self.request)

        self.assertEqual("eligible-synthetic-preflight-only", result["decision"])
        self.assertEqual([], result["blockers"])
        self.assertFalse(result["executionAuthorized"])
        self.assertFalse(result["installationAuthorized"])
        self.assertFalse(result["modelDispatchAuthorized"])

    def test_failure_injection_ledger_is_exact(self) -> None:
        self.assertEqual(
            list(MUTATION_CASE_IDS), self.record["failureInjectionCaseIds"]
        )

    def test_dangerous_bypass_or_existing_workspace_fails_closed(self) -> None:
        cases = (
            ("hostPermission", "nativeApprovalBypassAllowed"),
            ("hostPermission", "nativeSandboxBypassAllowed"),
            ("workspace", "existingUserWorkspaceAllowed"),
        )
        for container, field in cases:
            with self.subTest(field=field):
                request = copy.deepcopy(self.request)
                request[container][field] = True

                result = evaluate_preflight(request)

                self.assertEqual("blocked", result["decision"])
                self.assertFalse(result["executionAuthorized"])

    def test_auditor_write_capability_fails_closed(self) -> None:
        request = copy.deepcopy(self.request)
        request["hostPermission"]["auditor"]["workspaceWriteAllowed"] = True

        result = evaluate_preflight(request)

        self.assertEqual("blocked", result["decision"])
        self.assertIn("auditor-profile-invalid", result["blockers"])

    def test_missing_rollback_or_crash_resume_evidence_fails_closed(self) -> None:
        cases = (
            ("mutationAndRollback", "rollbackReceiptRequired"),
            ("recovery", "resumeCheckpointDigestRequired"),
        )
        for container, field in cases:
            with self.subTest(field=field):
                request = copy.deepcopy(self.request)
                request[container][field] = False

                result = evaluate_preflight(request)

                self.assertEqual("blocked", result["decision"])
                self.assertFalse(result["executionAuthorized"])

    def test_model_dispatch_promotion_fails_closed(self) -> None:
        request = copy.deepcopy(self.request)
        request["externalBoundary"]["modelDispatchAllowed"] = True

        result = evaluate_preflight(request)

        self.assertEqual("blocked", result["decision"])
        self.assertIn("external-boundary-crossed", result["blockers"])
        self.assertFalse(result["modelDispatchAuthorized"])

    def test_validator_rejects_live_authorization_claim(self) -> None:
        record = copy.deepcopy(self.record)
        record["currentDecision"]["liveComparisonAuthorized"] = True

        with self.assertRaisesRegex(RuntimeError, "current decision"):
            validate_preflight_record(record, root=ROOT)

    def test_validator_rejects_acceptance_promotion(self) -> None:
        acceptance = json.loads((ROOT / ACCEPTANCE_PATH).read_text(encoding="utf-8"))
        criterion = next(
            row
            for row in acceptance["acceptanceCriteria"]
            if row["id"] == "acceptance.end-to-end-process-fidelity"
        )
        criterion["assessment"] = "verified"

        with self.assertRaisesRegex(RuntimeError, "acceptance boundary"):
            validate_preflight_record(
                self.record, acceptance=acceptance, root=ROOT
            )


if __name__ == "__main__":
    unittest.main()
