from __future__ import annotations

import copy
import json
from pathlib import Path
import tempfile
import unittest

from scripts.build_human_ai_collaboration_semantic_authority_execution_plan import (
    compile_execution_plan,
    materialize_execution_plan,
    run_execution_plan_preflight,
    validate_execution_plan,
    validate_preflight_report,
)


class SemanticAuthorityExecutionPlanTests(unittest.TestCase):
    def test_native_plan_binds_route_without_dispatch_authority(self) -> None:
        plan = compile_execution_plan("SEM-NATIVE", "SEM03-CAL-001")

        self.assertEqual("SEM03-CAL-001", plan["runId"])
        self.assertEqual("SEM-NATIVE", plan["treatmentId"])
        self.assertEqual(
            {
                "model": "gpt-5.3-codex-spark",
                "reasoningEffort": "low",
                "allowProviderModelFallback": False,
            },
            plan["requestedRoute"],
        )
        self.assertFalse(plan["authority"]["modelDispatchAuthorized"])
        self.assertEqual(0, plan["authority"]["modelRequestBudget"])
        self.assertEqual([], plan["treatmentProjection"]["selectedSkillInputs"])
        self.assertEqual([], validate_execution_plan(plan))

    def test_local_plan_binds_exact_structured_skill_input(self) -> None:
        plan = compile_execution_plan(
            "SEM-LOCAL-ADAPTED-MONOLITH",
            "SEM03-CAL-002",
        )

        self.assertEqual(
            [
                {
                    "type": "skill",
                    "name": "grill-with-docs",
                    "runtimePath": (
                        ".agents/skills/grill-with-docs/SKILL.md"
                    ),
                    "sha256": (
                        "e1078020c41b954638ba94acda95a3340739908bd68b1db9bc2af129d3936035"
                    ),
                }
            ],
            plan["treatmentProjection"]["selectedSkillInputs"],
        )
        self.assertEqual(
            "repository-pinned-copy",
            plan["treatmentProjection"]["materializationMode"],
        )
        self.assertEqual([], validate_execution_plan(plan))

    def test_current_composition_plan_binds_entry_and_dependencies(self) -> None:
        plan = compile_execution_plan(
            "SEM-MATT-CURRENT-COMPOSITION",
            "SEM03-CAL-003",
        )

        projection = plan["treatmentProjection"]
        self.assertEqual("source-pinned-atomic-builder", projection["materializationMode"])
        self.assertEqual(
            ["domain-modeling", "grill-with-docs", "grilling"],
            projection["requiredSkillNames"],
        )
        self.assertEqual(
            ["grill-with-docs"],
            [item["name"] for item in projection["selectedSkillInputs"]],
        )
        self.assertFalse(projection["materializedByThisPlan"])
        self.assertEqual([], validate_execution_plan(plan))

    def test_plan_requires_four_fresh_threads_and_ordered_human_injection(self) -> None:
        plan = compile_execution_plan("SEM-NATIVE", "SEM03-CAL-004")

        self.assertEqual(
            {
                "runtimeRoot": "runtime",
                "publicPacketRoot": "runtime/public",
                "skillProjectionRoot": "runtime/.agents/skills",
                "parentControlRoot": "parent",
            },
            plan["workspaceLayout"],
        )
        phases = plan["lifecyclePhases"]
        self.assertEqual(
            [
                "SEM-PHASE-1-ELICIT",
                "SEM-PHASE-2-MODEL",
                "SEM-PHASE-3-SPEC",
                "SEM-PHASE-4-REVIEW-HANDOFF",
            ],
            [phase["id"] for phase in phases],
        )
        self.assertTrue(all(phase["freshThreadRequired"] for phase in phases))
        self.assertEqual(
            [False, True, False, False],
            [phase["injectHumanDecisionsBeforePhase"] for phase in phases],
        )
        self.assertTrue(all(phase["closeThreadAfterPhase"] for phase in phases))
        self.assertTrue(
            all(
                path.startswith("public/")
                for phase in phases
                for path in phase["inputFiles"]
            )
        )

    def test_plan_rejects_loader_and_instruction_delivery_promotion(self) -> None:
        plan = compile_execution_plan(
            "SEM-LOCAL-ADAPTED-MONOLITH",
            "SEM03-CAL-005",
        )
        promoted = copy.deepcopy(plan)
        promoted["evidenceCeiling"]["loaderInvocationProvedByPlan"] = True
        promoted["evidenceCeiling"]["skillInstructionsReachedModelProvedByPlan"] = True

        self.assertIn(
            "hard-fail-evidence-ceiling-promotion",
            validate_execution_plan(promoted),
        )

    def test_plan_rejects_dispatch_self_authorization(self) -> None:
        plan = compile_execution_plan("SEM-NATIVE", "SEM03-CAL-006")
        promoted = copy.deepcopy(plan)
        promoted["authority"]["modelDispatchAuthorized"] = True
        promoted["authority"]["modelRequestBudget"] = 1

        self.assertIn(
            "hard-fail-dispatch-authority-promotion",
            validate_execution_plan(promoted),
        )

    def test_materialized_bundle_separates_public_packet_and_parent_plan(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "bundle"
            receipt = materialize_execution_plan(
                output,
                "SEM-NATIVE",
                "SEM03-CAL-007",
            )

            runtime_root = output / "runtime"
            public_root = runtime_root / "public"
            public_task = json.loads(
                (public_root / "TASK.json").read_text(encoding="utf-8")
            )
            parent_plan = json.loads(
                (output / "parent" / "EXECUTION_PLAN.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertFalse(public_task["privateOracleIncluded"])
            self.assertFalse(parent_plan["authority"]["modelDispatchAuthorized"])
            self.assertFalse((runtime_root / "parent").exists())
            self.assertEqual("compiled-no-dispatch", receipt["status"])
            self.assertEqual([], receipt["failureCodes"])
            rendered_public = "\n".join(
                path.read_text(encoding="utf-8")
                for path in public_root.rglob("*")
                if path.is_file()
            )
            self.assertNotIn("SEM03-PRIVATE-ORACLE-CANARY-7D91C0E5", rendered_public)

    def test_materialization_rejects_nonempty_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "bundle"
            output.mkdir()
            (output / "user-file.txt").write_text("preserve", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "must be empty"):
                materialize_execution_plan(
                    output,
                    "SEM-NATIVE",
                    "SEM03-CAL-008",
                )

    def test_preflight_materializes_all_treatments_without_dispatch(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary) / "process-roots"
            report = run_execution_plan_preflight(parent)

        self.assertEqual("preflight-pass-no-dispatch", report["status"])
        self.assertEqual(
            [
                "SEM-LOCAL-ADAPTED-MONOLITH",
                "SEM-MATT-CURRENT-COMPOSITION",
                "SEM-NATIVE",
            ],
            sorted(item["treatmentId"] for item in report["treatments"]),
        )
        self.assertFalse(report["temporaryProcessRootRetained"])
        self.assertFalse(report["modelRequestSent"])
        self.assertFalse(report["threadStarted"])
        self.assertFalse(report["turnStarted"])
        self.assertEqual([], validate_preflight_report(report))

    def test_preflight_rejects_claim_and_dispatch_promotion(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            report = run_execution_plan_preflight(Path(temporary))
        promoted = copy.deepcopy(report)
        promoted["claimBoundary"]["loaderInvocationProved"] = True
        promoted["modelRequestSent"] = True

        failures = validate_preflight_report(promoted)
        self.assertIn("hard-fail-claim-promotion", failures)
        self.assertIn("hard-fail-model-dispatch", failures)


if __name__ == "__main__":
    unittest.main()
