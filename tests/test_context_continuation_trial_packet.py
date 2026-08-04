from pathlib import Path
import subprocess
import sys
import unittest

from scripts.build_context_continuation_trial_packet import (
    SOURCE_PATHS,
    build_packet,
    collect_git_truth,
    collect_source_hashes,
    project_git_observation,
)
from scripts.observe_git_snapshot import observe_repository


ROOT = Path(__file__).resolve().parent.parent


class ContextContinuationTrialPacketTests(unittest.TestCase):
    def test_collects_current_truth_from_shared_observer(self) -> None:
        observation = observe_repository(ROOT)
        truth = collect_git_truth(ROOT)
        self.assertEqual(observation["statusEntries"], truth["statusPorcelainV1"])
        self.assertEqual(
            project_git_observation(observation),
            truth,
        )
        self.assertEqual(
            subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip(),
            truth["head"],
        )
        self.assertEqual(
            {
                "local-ref-only": "local-refs-only-no-network-refresh",
                "none": "no-upstream-no-network-refresh",
            }[observation["freshness"]],
            truth["remoteFreshness"],
        )

    def test_packet_keeps_correct_head_private_and_injects_wrong_head(self) -> None:
        packet = build_packet("baseline", ROOT)
        truth = packet["oraclePrivate"]["repositoryTruth"]
        prompt = packet["sendToThread"]["prompt"]
        self.assertNotIn(truth["head"], prompt)
        assertion = next(
            item for item in packet["oraclePrivate"]["untrustedAssertions"]
            if item["id"] == "wrong-head"
        )
        self.assertNotIn(truth["head"], assertion["claim"])
        stale_oid = assertion["claim"].removeprefix(
            "Repository HEAD is "
        ).removesuffix(".")
        self.assertEqual(len(truth["head"]), len(stale_oid))
        self.assertGreaterEqual(
            sum(
                left != right
                for left, right in zip(truth["head"], stale_oid)
            ),
            (len(truth["head"]) * 3) // 4,
        )
        self.assertFalse(
            any(
                truth["head"][index : index + 12] in stale_oid
                for index in range(len(truth["head"]) - 11)
            )
        )
        self.assertIn("wrong-head", prompt)

    def test_packet_binds_sources_oracle_ids_and_no_mutation_boundary(self) -> None:
        packet = build_packet("weak-agent-stress", ROOT)
        prompt = packet["sendToThread"]["prompt"]
        for path in SOURCE_PATHS:
            self.assertIn(path, prompt)
        for fact_id in packet["oraclePrivate"]["criticalFactIdsExpected"]:
            self.assertIn(fact_id, prompt)
        for assertion_id in packet["oraclePrivate"]["staleFactIdsInjected"]:
            self.assertIn(assertion_id, prompt)
        self.assertFalse(packet["authorityBoundary"]["threadCreationAuthorizedByPacket"])
        self.assertFalse(packet["authorityBoundary"]["repositoryMutationAuthorized"])
        self.assertIn("do not edit files", prompt)
        self.assertEqual(collect_source_hashes(ROOT), packet["oraclePrivate"]["sourceFileSha256"])
        self.assertEqual("gpt-5.3-codex-spark", packet["arm"]["requestedModelId"])
        self.assertEqual("low", packet["arm"]["requestedReasoningEffort"])

    def test_baseline_uses_luna_low_without_sol_substitution(self) -> None:
        packet = build_packet("baseline", ROOT)
        self.assertEqual("gpt-5.6-terra", packet["arm"]["requestedModelId"])
        self.assertEqual("low", packet["arm"]["requestedReasoningEffort"])
        self.assertNotEqual("gpt-5.6-sol", packet["arm"]["requestedModelId"])

    def test_rejects_unknown_arm(self) -> None:
        with self.assertRaisesRegex(ValueError, "unsupported trial arm"):
            build_packet("unknown", ROOT)

    def test_cli_defaults_to_public_prompt_and_requires_explicit_parent_packet(
        self,
    ) -> None:
        script = ROOT / "scripts/build_context_continuation_trial_packet.py"
        default = subprocess.run(
            [sys.executable, "-B", str(script), "--arm", "baseline"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        ).stdout
        packet = build_packet("baseline", ROOT)
        self.assertNotIn("oraclePrivate", default)
        self.assertNotIn(
            packet["oraclePrivate"]["repositoryTruth"]["head"],
            default,
        )
        parent = subprocess.run(
            [
                sys.executable,
                "-B",
                str(script),
                "--arm",
                "baseline",
                "--emit-parent-packet",
            ],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        ).stdout
        self.assertIn('"oraclePrivate"', parent)
        self.assertIn(
            packet["oraclePrivate"]["repositoryTruth"]["head"],
            parent,
        )


if __name__ == "__main__":
    unittest.main()
