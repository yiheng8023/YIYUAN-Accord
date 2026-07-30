from __future__ import annotations

import copy
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from scripts.validate_mcp_thread_creator_connection_close_calibration_attempt import (
    ATTEMPT_PROBE_SHA256,
    ATTEMPT_ROOT,
    CURRENT_PROBE_SHA256,
    DOCUMENTATION_PATH,
    NORMALIZED_EVIDENCE_PATH,
    NORMALIZED_EVIDENCE_SHA256,
    PROBE_PATH,
    RECORD_PATH,
    SENTINEL_INSTANCE_ID,
    SENTINEL_PID,
    file_sha256,
    validate_attempt,
)


ROOT = Path(__file__).resolve().parent.parent


class McpThreadCreatorConnectionCloseCalibrationAttemptTests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.record = json.loads(
            (ROOT / RECORD_PATH).read_text(encoding="utf-8")
        )

    def validate(
        self,
        record: dict | None = None,
        *,
        root: Path = ROOT,
    ) -> None:
        validate_attempt(
            self.record if record is None else record,
            root=root,
        )

    def make_temp_root(self, directory: str) -> Path:
        root = Path(directory)
        for relative_path in (
            PROBE_PATH,
            DOCUMENTATION_PATH,
            NORMALIZED_EVIDENCE_PATH,
        ):
            destination = root / relative_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / relative_path, destination)
        return root

    def test_current_attempt_record_and_local_evidence_are_valid(self) -> None:
        self.validate()
        self.assertEqual(
            file_sha256(ROOT / PROBE_PATH), CURRENT_PROBE_SHA256
        )
        self.assertNotEqual(ATTEMPT_PROBE_SHA256, CURRENT_PROBE_SHA256)
        self.assertEqual(
            file_sha256(ROOT / NORMALIZED_EVIDENCE_PATH),
            NORMALIZED_EVIDENCE_SHA256,
        )

    def test_rejects_formal_live_count_promotion(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["attempt"]["formalLivePairedRunCount"] = 1
        with self.assertRaisesRegex(
            RuntimeError, "attempt boundary drifted"
        ):
            self.validate(mutated)

    def test_rejects_paired_window_entry_promotion(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["attempt"]["pairedWindowEntered"] = True
        with self.assertRaisesRegex(
            RuntimeError, "attempt boundary drifted"
        ):
            self.validate(mutated)

    def test_rejects_pair_report_generated_promotion(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["attempt"]["pairReportGenerated"] = True
        with self.assertRaisesRegex(
            RuntimeError, "attempt boundary drifted"
        ):
            self.validate(mutated)

    def test_rejects_physical_pair_report(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self.make_temp_root(directory)
            attempt_root = root / ATTEMPT_ROOT
            attempt_root.mkdir(parents=True)
            (attempt_root / "pair-report.json").write_text(
                "{}\n", encoding="utf-8"
            )
            with self.assertRaisesRegex(
                RuntimeError, "pair report exists"
            ):
                self.validate(root=root)

    def test_rejects_attempt_sha_promoted_as_current_identity(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["probe"]["sha256AtAttemptRole"] = (
            "current-executable-identity"
        )
        with self.assertRaisesRegex(
            RuntimeError, "probe identity boundary drifted"
        ):
            self.validate(mutated)

    def test_rejects_current_probe_sha_mutation(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["probe"]["currentSha256"] = ATTEMPT_PROBE_SHA256
        with self.assertRaisesRegex(
            RuntimeError, "probe identity boundary drifted"
        ):
            self.validate(mutated)

    def test_rejects_current_probe_file_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self.make_temp_root(directory)
            probe = root / PROBE_PATH
            probe.write_bytes(probe.read_bytes() + b"\n")
            with self.assertRaisesRegex(
                RuntimeError, "Current remediated probe SHA256 drifted"
            ):
                self.validate(root=root)

    def test_rejects_wait_for_rollout_restoration_claim(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["probe"]["currentProbeContainsWaitForRollout"] = True
        with self.assertRaisesRegex(
            RuntimeError, "probe identity boundary drifted"
        ):
            self.validate(mutated)

    def test_rejects_normalized_evidence_byte_or_hash_drift(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self.make_temp_root(directory)
            evidence = root / NORMALIZED_EVIDENCE_PATH
            evidence.write_bytes(evidence.read_bytes() + b"\n")
            with self.assertRaisesRegex(
                RuntimeError, "normalized evidence file drifted"
            ):
                self.validate(root=root)

    def test_rejects_sentinel_pid_mutation(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["observedLocalEvidence"]["sentinelPid"] = SENTINEL_PID + 1
        with self.assertRaisesRegex(
            RuntimeError, "Sentinel evidence boundary drifted"
        ):
            self.validate(mutated)

    def test_rejects_sentinel_instance_mutation(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["observedLocalEvidence"]["sentinelInstanceId"] = (
            SENTINEL_INSTANCE_ID + "-changed"
        )
        with self.assertRaisesRegex(
            RuntimeError, "Sentinel evidence boundary drifted"
        ):
            self.validate(mutated)

    def test_rejects_process_family_absence_overclaim(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["observedLocalEvidence"][
            "broaderProcessFamilyAbsenceProved"
        ] = True
        with self.assertRaisesRegex(
            RuntimeError, "Sentinel evidence boundary drifted"
        ):
            self.validate(mutated)

    def test_rejects_authority_conflict_erasure(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["authorityIncident"][
            "protocolLoopbackBoundaryWasFalse"
        ] = False
        with self.assertRaisesRegex(
            RuntimeError, "authority conflict boundary drifted"
        ):
            self.validate(mutated)

    def test_rejects_live_rerun_promotion(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["remediation"]["liveRerunPerformed"] = True
        with self.assertRaisesRegex(
            RuntimeError, "no-rerun boundary drifted"
        ):
            self.validate(mutated)

    def test_rejects_cleanup_authorization_promotion(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["cleanupBoundary"]["deletionAuthorizedOn"] = "2026-07-29"
        with self.assertRaisesRegex(
            RuntimeError, "cleanup retention boundary drifted"
        ):
            self.validate(mutated)

    def test_rejects_missing_retained_root(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["cleanupBoundary"]["rootsOriginallyRetained"].pop()
        with self.assertRaisesRegex(
            RuntimeError, "cleanup retention boundary drifted"
        ):
            self.validate(mutated)

    def test_rejects_any_release_or_controller_claim(self) -> None:
        for claim in self.record["claimBoundary"]:
            with self.subTest(claim=claim):
                mutated = copy.deepcopy(self.record)
                mutated["claimBoundary"][claim] = True
                with self.assertRaisesRegex(
                    RuntimeError,
                    "release/task-end/lease/resource/controller claim",
                ):
                    self.validate(mutated)

    def test_rejects_rerun_without_explicit_authorization(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["authorityIncident"][
            "rerunRequiresExplicitLoopbackExecutionAuthorization"
        ] = False
        with self.assertRaisesRegex(
            RuntimeError, "authority conflict boundary drifted"
        ):
            self.validate(mutated)

    def test_repository_verifier_wires_record_validator_and_test(self) -> None:
        source = (ROOT / "scripts" / "verify.py").read_text(
            encoding="utf-8"
        )
        for required in (
            (
                "from "
                "validate_mcp_thread_creator_connection_close_calibration_"
                "attempt import"
            ),
            (
                '"registry/mcp-thread-creator-connection-close-calibration-'
                'attempt-2026-07-27.json"'
            ),
            (
                '"docs/mcp-thread-creator-connection-close-calibration-'
                'attempt-2026-07-27.md"'
            ),
            (
                '"scripts/validate_mcp_thread_creator_connection_close_'
                'calibration_attempt.py"'
            ),
            (
                '"tests/test_mcp_thread_creator_connection_close_calibration_'
                'attempt.py"'
            ),
            (
                "validate_mcp_thread_creator_connection_close_calibration_"
                "attempt("
            ),
        ):
            self.assertIn(required, source)


if __name__ == "__main__":
    unittest.main()
