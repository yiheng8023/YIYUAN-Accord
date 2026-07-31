from __future__ import annotations

import copy
import json
from pathlib import Path
import tempfile
import unittest

from scripts.build_human_ai_collaboration_semantic_authority_continuity_trial import (
    build_packet,
    evaluate_bundle,
    evaluate_offline_examples,
    inject_human_decisions,
    load_fixture,
    validate_public_packet_oracle_isolation,
)


class SemanticAuthorityContinuityTrialTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = load_fixture()
        self.positive = copy.deepcopy(self.fixture["positiveBundle"])

    def test_offline_examples_match_expected_outcomes(self) -> None:
        self.assertEqual([], evaluate_offline_examples(self.fixture))

    def test_positive_bundle_passes_private_oracle(self) -> None:
        self.assertEqual([], evaluate_bundle(self.positive))

    def test_missing_term_fails_continuity(self) -> None:
        self.positive["semanticAuthority"]["terms"].pop(0)
        self.assertIn(
            "fail-term-identity-continuity",
            evaluate_bundle(self.positive),
        )

    def test_terminal_status_cannot_erase_conflict(self) -> None:
        self.positive["implementationReview"]["releaseReady"] = True
        self.positive["handoff"]["complete"] = True
        failures = evaluate_bundle(self.positive)
        self.assertIn("hard-fail-review-status-promotion", failures)
        self.assertIn("hard-fail-handoff-status-promotion", failures)

    def test_packet_excludes_private_oracle_and_human_decisions(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "trial"
            manifest = build_packet(root, "SEM-NATIVE")
            self.assertFalse(manifest["privateOracleIncludedInPacket"])
            self.assertFalse(manifest["humanDecisionsIncludedInitially"])
            task = json.loads((root / "TASK.json").read_text(encoding="utf-8"))
            self.assertFalse(task["privateOracleIncluded"])
            rendered = json.dumps(task, ensure_ascii=False)
            self.assertNotIn("requiredConflict", rendered)
            self.assertNotIn("requiredUnresolvedAction", rendered)
            self.assertFalse((root / "HUMAN_DECISIONS.json").exists())
            self.assertFalse((root / "CONTEXT.md").exists())
            self.assertEqual(
                {
                    "status": "pass",
                    "checkedFileCount": len(manifest["files"]),
                    "unmanifestedFilesPresent": False,
                    "privateOracleCanaryPresent": False,
                },
                manifest["privateOracleIsolation"],
            )

    def test_public_packet_rejects_full_private_oracle_file_leak(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "trial"
            manifest = build_packet(root, "SEM-NATIVE")
            (root / "PRIVATE_ORACLE.json").write_text(
                json.dumps(self.fixture["privateOracle"], ensure_ascii=False),
                encoding="utf-8",
            )
            failures = validate_public_packet_oracle_isolation(root, manifest)
            self.assertIn("hard-fail-unmanifested-public-file", failures)
            self.assertIn("hard-fail-private-oracle-leak", failures)

    def test_public_packet_rejects_partial_private_oracle_canary_leak(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "trial"
            manifest = build_packet(root, "SEM-NATIVE")
            canary = self.fixture["privateOracle"]["nonPublicLeakageCanary"]
            with (root / "DRAFT_PITCH_PLAN.md").open(
                "a", encoding="utf-8", newline="\n"
            ) as handle:
                handle.write(f"\n{canary}\n")
            failures = validate_public_packet_oracle_isolation(root, manifest)
            self.assertIn("hard-fail-private-oracle-leak", failures)
            self.assertIn("hard-fail-public-file-digest-drift", failures)

    def test_human_decisions_are_injected_once_after_packet_build(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "trial"
            build_packet(root, "SEM-LOCAL-ADAPTED-MONOLITH")
            evidence = inject_human_decisions(root)
            self.assertEqual("HUMAN_DECISIONS.json", evidence["path"])
            decisions = json.loads(
                (root / "HUMAN_DECISIONS.json").read_text(encoding="utf-8")
            )
            self.assertEqual(4, len(decisions["decisions"]))
            with self.assertRaisesRegex(RuntimeError, "already injected"):
                inject_human_decisions(root)

    def test_current_composition_packet_is_metadata_only(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "trial"
            build_packet(root, "SEM-MATT-CURRENT-COMPOSITION")
            task = json.loads((root / "TASK.json").read_text(encoding="utf-8"))
            self.assertFalse(
                task["treatment"]["executionAdmissionSatisfied"]
            )
            self.assertFalse((root / ".agents").exists())
            self.assertFalse((root / ".codex").exists())

    def test_nonempty_output_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "trial"
            root.mkdir()
            (root / "user-file.txt").write_text("preserve", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "must not already contain"):
                build_packet(root)


if __name__ == "__main__":
    unittest.main()
