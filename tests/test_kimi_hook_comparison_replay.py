import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from scripts.run_kimi_hook_comparison_replay import (
    ARTIFACT_TREATMENTS,
    EXPECTED_CLAIM_BOUNDARY,
    EXPECTED_TOPOLOGY,
    canonical_sha256,
    validate_temporary_parent,
    validate_report,
    write_report_atomically,
)


ROOT = Path(__file__).resolve().parent.parent
REPORT = (
    ROOT
    / "audits"
    / "kimi-three-hook-comparison-replay-2026-08-01"
    / "REPORT.json"
)


class KimiHookComparisonReplayTests(unittest.TestCase):
    def test_frozen_report_is_valid_and_remains_zero_model(self) -> None:
        report = json.loads(REPORT.read_text(encoding="utf-8"))

        self.assertEqual([], validate_report(report))
        self.assertFalse(report["modelRequestSent"])
        self.assertFalse(report["liveConfigurationRead"])
        self.assertFalse(report["liveConfigurationWritten"])
        self.assertTrue(report["isolatedTemporaryRootRemoved"])
        self.assertEqual(EXPECTED_CLAIM_BOUNDARY, report["claimBoundary"])
        self.assertEqual(EXPECTED_TOPOLOGY, report["topology"])
        self.assertEqual(ARTIFACT_TREATMENTS, report["artifactTreatments"])
        self.assertFalse(report["claimBoundary"]["allBoundArtifactsExecuted"])
        self.assertFalse(report["claimBoundary"]["hostHookRegistrationProved"])
        self.assertFalse(report["claimBoundary"]["skillInstructionDeliveryProved"])
        self.assertFalse(report["claimBoundary"]["permissionRuleEffectProved"])
        self.assertGreater(report["evidenceCost"]["evaluatorToCandidateHookByteRatio"], 1)
        self.assertTrue(report["evidenceCost"]["excludesTestsReportsAndDocumentation"])

    def test_report_covers_all_three_hooks_and_harness_context_decisions(self) -> None:
        report = json.loads(REPORT.read_text(encoding="utf-8"))
        cases = {row["id"]: row for row in report["mechanismCases"]}

        self.assertEqual(
            {
                "mcp-explicit-off",
                "mcp-pinned-default-on",
                "mcp-default-off",
                "mcp-explicit-on",
                "mcp-built-in-pass",
                "mcp-missing-gate-fail-open",
                "session-fresh-injection",
                "session-stale-handoff-excluded",
                "context-low-continue",
                "context-warning-wait",
                "context-warning-hysteresis",
                "context-critical-wait",
                "context-compaction-reset",
            },
            set(cases),
        )
        self.assertEqual("CONTINUE", cases["context-low-continue"]["harnessState"])
        self.assertEqual("WAIT", cases["context-warning-wait"]["harnessState"])
        self.assertEqual("WAIT", cases["context-critical-wait"]["harnessState"])
        self.assertEqual("CONTINUE", cases["context-compaction-reset"]["harnessState"])
        self.assertEqual(
            "shared-injection-infrastructure",
            cases["session-fresh-injection"]["role"],
        )
        self.assertEqual(2, report["topology"]["executablePrototypeCount"])
        self.assertIsNone(report["topology"]["lanes"][1]["executablePrototype"])
        self.assertEqual(
            [
                {
                    "id": "lane-1-context-handoff-rules",
                    "role": "rule-text",
                    "passed": True,
                },
                {
                    "id": "lane-2-git-discipline-rules",
                    "role": "rule-text-no-executable-prototype",
                    "passed": True,
                },
            ],
            report["ruleCases"],
        )

    def test_claim_promotion_and_digest_tampering_fail_closed(self) -> None:
        report = json.loads(REPORT.read_text(encoding="utf-8"))
        promoted = copy.deepcopy(report)
        promoted["claimBoundary"]["resourceSavingsProved"] = True
        promoted["reportSha256"] = canonical_sha256(
            {key: value for key, value in promoted.items() if key != "reportSha256"}
        )
        self.assertIn("hard-fail-kimi-replay-claim-promotion", validate_report(promoted))

        tampered = copy.deepcopy(report)
        tampered["mechanismCases"][0]["passed"] = False
        self.assertIn("hard-fail-kimi-replay-report-digest", validate_report(tampered))

        runtime_tampered = copy.deepcopy(report)
        runtime_tampered["runtime"]["nodeVersion"] = "v999.0.0"
        runtime_tampered["reportSha256"] = canonical_sha256(
            {
                key: value
                for key, value in runtime_tampered.items()
                if key != "reportSha256"
            }
        )
        self.assertIn(
            "hard-fail-kimi-replay-runtime-identity",
            validate_report(runtime_tampered),
        )

        cost_tampered = copy.deepcopy(report)
        cost_tampered["evidenceCost"]["evaluatorSourceBytes"] += 1
        cost_tampered["reportSha256"] = canonical_sha256(
            {
                key: value
                for key, value in cost_tampered.items()
                if key != "reportSha256"
            }
        )
        self.assertIn(
            "hard-fail-kimi-replay-evidence-cost",
            validate_report(cost_tampered),
        )

    def test_temporary_parent_must_be_system_temp(self) -> None:
        with tempfile.TemporaryDirectory() as safe_parent:
            self.assertEqual(
                Path(safe_parent).resolve(),
                validate_temporary_parent(Path(safe_parent)),
            )
        with tempfile.TemporaryDirectory(dir=ROOT) as unsafe_parent:
            with self.assertRaisesRegex(RuntimeError, "system temporary root"):
                validate_temporary_parent(Path(unsafe_parent))

    def test_atomic_writer_refuses_overwrite(self) -> None:
        report = json.loads(REPORT.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as temporary_root:
            output = Path(temporary_root) / "REPORT.json"
            write_report_atomically(output, report)
            self.assertEqual(report, json.loads(output.read_text(encoding="utf-8")))
            with self.assertRaisesRegex(RuntimeError, "already exists"):
                write_report_atomically(output, report)

    def test_atomic_writer_cannot_overwrite_concurrent_creator(self) -> None:
        report = json.loads(REPORT.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as temporary_root:
            output = Path(temporary_root) / "REPORT.json"
            real_link = os.link

            def competing_link(source: Path, destination: Path) -> None:
                Path(destination).write_text("competitor\n", encoding="utf-8")
                real_link(source, destination)

            with mock.patch(
                "scripts.run_kimi_hook_comparison_replay.os.link",
                side_effect=competing_link,
            ):
                with self.assertRaisesRegex(RuntimeError, "already exists"):
                    write_report_atomically(output, report)
            self.assertEqual("competitor\n", output.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
