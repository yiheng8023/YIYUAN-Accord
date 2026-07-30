from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.build_human_ai_collaboration_tdd_trial import (
    ALLOWED_ARMS,
    FIXTURE_PATH,
    PRIVATE_ORACLE,
    build_packet,
    build_trial_package,
    canonical_sha256,
    evaluate_fixture_document,
    evaluate_tdd_timeline,
    materialize_treatment_projection,
)


ROOT = Path(__file__).resolve().parent.parent


class HumanAiCollaborationTddTrialBuilderTests(unittest.TestCase):
    def test_all_normalized_timeline_fixtures_match(self) -> None:
        fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        results = evaluate_fixture_document(fixture)
        self.assertEqual(7, len(results))
        self.assertTrue(
            all(
                result["actualStatus"] == result["expectedStatus"]
                for result in results
            )
        )

    def test_valid_timeline_requires_real_red_before_production(self) -> None:
        events = [
            {
                "type": "fileMutation",
                "paths": ["test_feature.py"],
                "timelineObservable": True,
            },
            {
                "type": "commandExecution",
                "focusedTestCommand": True,
                "exitCode": 1,
                "failureClass": "expected-behavior-assertion",
                "timelineObservable": True,
            },
            {
                "type": "fileMutation",
                "paths": ["feature.py"],
                "timelineObservable": True,
            },
            {
                "type": "commandExecution",
                "focusedTestCommand": True,
                "exitCode": 0,
                "failureClass": None,
                "timelineObservable": True,
            },
        ]
        result = evaluate_tdd_timeline(events)
        self.assertEqual("accepted-offline-tdd-timeline", result["status"])
        self.assertEqual(1, result["validRedCount"])
        self.assertEqual(2, result["firstProductionMutationIndex"])

    def test_builder_materializes_same_task_for_all_arms(self) -> None:
        manifests = []
        task_payloads = []
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for arm in sorted(ALLOWED_ARMS):
                output = root / arm
                manifest = build_packet(output, arm, project_root=ROOT)
                manifests.append(manifest)
                task = json.loads(
                    (output / "TASK.json").read_text(encoding="utf-8")
                )
                task_payloads.append(
                    {
                        key: value
                        for key, value in task.items()
                        if key not in {"packetId", "armId"}
                    }
                )
                self.assertFalse((output / "test_feature.py").exists())
                self.assertIn(
                    "return None",
                    (output / "feature.py").read_text(encoding="utf-8"),
                )
                serialized = "\n".join(
                    path.read_text(encoding="utf-8", errors="replace")
                    for path in output.iterdir()
                    if path.is_file()
                )
                self.assertNotIn(
                    canonical_sha256(PRIVATE_ORACLE),
                    serialized,
                )
                self.assertFalse(
                    manifest["privateOracle"]["contentWrittenIntoTrial"]
                )
                self.assertFalse(manifest["treatmentProjectionMaterialized"])
                self.assertFalse(manifest["liveExecutionStarted"])
        self.assertTrue(
            all(payload == task_payloads[0] for payload in task_payloads)
        )

    def test_builder_rejects_nonempty_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "trial"
            output.mkdir()
            (output / "keep.txt").write_text("keep", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "empty directory"):
                build_packet(
                    output,
                    "SE-TDD-NATIVE-SPARK",
                    project_root=ROOT,
                )

    def test_native_arm_has_no_candidate_projection(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(ValueError, "no candidate projection"):
                materialize_treatment_projection(
                    Path(temporary),
                    "SE-TDD-NATIVE-SPARK",
                )

    def test_combined_package_reports_materialized_projection(self) -> None:
        calls = []

        def projection_builder(output, arm, **kwargs):
            calls.append((output, arm, kwargs))
            skill = output / ".agents" / "skills" / "tdd" / "SKILL.md"
            skill.parent.mkdir(parents=True)
            skill.write_text("---\nname: tdd\n---\n", encoding="utf-8")
            return {
                "candidateId": "tdd.matt.current",
                "manifestSha256": "a" * 64,
            }

        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "trial"
            result = build_trial_package(
                output,
                "SE-TDD-MATT-CURRENT",
                materialize_treatment=True,
                project_root=ROOT,
                projection_builder=projection_builder,
            )
        self.assertTrue(
            result["build"]["treatmentProjectionMaterialized"]
        )
        self.assertEqual(
            "tdd.matt.current",
            result["projection"]["candidateId"],
        )
        self.assertEqual(1, len(calls))
        self.assertIn(
            ".agents/skills/tdd/SKILL.md",
            result["build"]["postProjectionTree"]["files"],
        )
        self.assertGreater(
            result["build"]["postProjectionTree"]["fileCount"],
            result["build"]["preProjectionTree"]["fileCount"],
        )

    def test_timeline_rejects_unobservable_event(self) -> None:
        result = evaluate_tdd_timeline(
            [
                {
                    "type": "fileMutation",
                    "paths": ["test_feature.py"],
                    "timelineObservable": False,
                }
            ]
        )
        self.assertIn(
            "timeline-observability-incomplete",
            result["failureCodes"],
        )


if __name__ == "__main__":
    unittest.main()
