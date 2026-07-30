from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.build_human_ai_collaboration_weak_agent_trial import (
    INCIDENT_MUTABLE_FILES,
    MIGRATION_IMMUTABLE_FILES,
    MIGRATION_MUTABLE_FILES,
    MUTABLE_FILES,
    build_packet,
)


ROOT = Path(__file__).resolve().parent.parent


class HumanAiCollaborationWeakAgentTrialBuilderTests(unittest.TestCase):
    def test_builds_read_only_research_packet_without_oracle_answers(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "research"
            manifest = build_packet(
                output,
                "GEN-NATIVE-SPARK",
                project_root=ROOT,
            )
            task = json.loads(
                (output / "TASK.json").read_text(encoding="utf-8")
            )

            self.assertEqual("GEN-RESEARCH-01", task["scenarioId"])
            self.assertEqual("readOnly", task["executionSandbox"])
            self.assertEqual([], task["allowedMutableFiles"])
            self.assertIn("Nine of twelve", task["taskPrompt"])
            self.assertNotIn(
                '"sourceIds": [\n        "SRC-A"',
                task["taskPrompt"],
            )
            self.assertFalse(
                manifest["privateOracle"]["contentWrittenIntoTrial"]
            )

    def test_builds_native_and_matt_packets_with_identical_task(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            native = build_packet(
                root / "native",
                "SE-NATIVE-SPARK",
                project_root=ROOT,
            )
            matt = build_packet(
                root / "matt",
                "SE-MATT-DISCIPLINED-CODING",
                project_root=ROOT,
            )
            native_task = json.loads(
                (root / "native" / "TASK.json").read_text(encoding="utf-8")
            )
            matt_task = json.loads(
                (root / "matt" / "TASK.json").read_text(encoding="utf-8")
            )

            self.assertEqual(
                native_task["taskPrompt"],
                matt_task["taskPrompt"],
            )
            self.assertIsNone(native_task["selectedSkill"])
            self.assertEqual(
                "disciplined-coding",
                matt_task["selectedSkill"]["name"],
            )
            self.assertTrue(
                native["instructionCarrier"]["sourceAndCopyEqual"]
            )
            self.assertTrue(matt["instructionCarrier"]["sourceAndCopyEqual"])
            self.assertFalse(native["agentRunStartedAtBuildTime"])
            self.assertFalse(matt["agentRunStartedAtBuildTime"])

    def test_builder_separates_mutable_and_immutable_files(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "trial"
            manifest = build_packet(
                output,
                "SE-NATIVE-SPARK",
                project_root=ROOT,
            )

            self.assertEqual(set(MUTABLE_FILES), set(manifest["allowedMutableFiles"]))
            self.assertEqual(
                {"AGENTS.md", "TASK.json"},
                set(manifest["immutableFiles"]),
            )
            self.assertEqual(
                set(manifest["baselineFiles"]),
                set(MUTABLE_FILES) | {"AGENTS.md", "TASK.json"},
            )
            self.assertFalse(
                manifest["privateOracle"]["contentWrittenIntoTrial"]
            )

    def test_builds_identical_incident_native_and_diagnose_packets(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            native = build_packet(
                root / "native",
                "SE-OPS-NATIVE-SPARK",
                project_root=ROOT,
            )
            diagnose = build_packet(
                root / "diagnose",
                "SE-OPS-CC-DIAGNOSE",
                project_root=ROOT,
            )
            native_task = json.loads(
                (root / "native" / "TASK.json").read_text(encoding="utf-8")
            )
            diagnose_task = json.loads(
                (root / "diagnose" / "TASK.json").read_text(encoding="utf-8")
            )

            self.assertEqual("SE-OPS-INCIDENT-01", native_task["scenarioId"])
            self.assertEqual(native_task["taskPrompt"], diagnose_task["taskPrompt"])
            self.assertIsNone(native_task["selectedSkill"])
            self.assertEqual("diagnose", diagnose_task["selectedSkill"]["name"])
            self.assertEqual(
                set(INCIDENT_MUTABLE_FILES),
                set(native["allowedMutableFiles"]),
            )
            self.assertEqual(
                set(INCIDENT_MUTABLE_FILES) | {"AGENTS.md", "TASK.json"},
                set(native["baselineFiles"]),
            )
            self.assertFalse(
                native["privateOracle"]["contentWrittenIntoTrial"]
            )

    def test_builder_refuses_nonempty_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "trial"
            output.mkdir()
            (output / "existing.txt").write_text("preserve", encoding="utf-8")

            with self.assertRaisesRegex(RuntimeError, "must not already"):
                build_packet(
                    output,
                    "SE-NATIVE-SPARK",
                    project_root=ROOT,
                )

    def test_builds_identical_migration_native_and_candidate_packets(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            native = build_packet(
                root / "native",
                "SE-MAINT-NATIVE-SPARK",
                project_root=ROOT,
            )
            candidate = build_packet(
                root / "candidate",
                "SE-MAINT-CC-DEPRECATION-MIGRATION",
                project_root=ROOT,
            )
            native_task = json.loads(
                (root / "native" / "TASK.json").read_text(encoding="utf-8")
            )
            candidate_task = json.loads(
                (root / "candidate" / "TASK.json").read_text(
                    encoding="utf-8"
                )
            )

            self.assertEqual("SE-MAINT-MIGRATE-01", native_task["scenarioId"])
            self.assertEqual(
                native_task["taskPrompt"],
                candidate_task["taskPrompt"],
            )
            self.assertIsNone(native_task["selectedSkill"])
            self.assertEqual(
                "deprecation-and-migration",
                candidate_task["selectedSkill"]["name"],
            )
            self.assertEqual(
                set(MIGRATION_MUTABLE_FILES),
                set(native["allowedMutableFiles"]),
            )
            self.assertEqual(
                set(MIGRATION_IMMUTABLE_FILES),
                set(native["immutableFiles"]),
            )
            self.assertEqual(
                set(MIGRATION_IMMUTABLE_FILES)
                | set(MIGRATION_MUTABLE_FILES),
                set(native["baselineFiles"]),
            )
            self.assertFalse(
                native["privateOracle"]["contentWrittenIntoTrial"]
            )

    def test_builds_source_pinned_incident_packet_with_dynamic_project_path(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "trial"
            build_packet(
                output,
                "SE-OPS-MATT-CURRENT-DIAGNOSING-BUGS",
                project_root=ROOT,
            )
            task = json.loads(
                (output / "TASK.json").read_text(encoding="utf-8")
            )
            selected = task["selectedSkill"]
            self.assertEqual(
                "matt.current-diagnosing-bugs",
                selected["projectionCandidateId"],
            )
            self.assertEqual(
                (
                    output
                    / ".agents"
                    / "skills"
                    / "diagnosing-bugs"
                    / "SKILL.md"
                ).resolve().as_posix(),
                selected["path"],
            )

    def test_builder_rejects_unapproved_arm(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(ValueError, "unsupported"):
                build_packet(
                    Path(temporary) / "trial",
                    "SE-SUPERPOWERS-TDD",
                    project_root=ROOT,
                )


if __name__ == "__main__":
    unittest.main()
