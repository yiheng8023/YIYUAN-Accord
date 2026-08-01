from __future__ import annotations

import copy
import json
import unittest

from scripts.validate_human_ai_collaboration_semantic_authority_continuity_protocol import (
    PROTOCOL_PATH,
    ROOT,
    validate_protocol,
)


class SemanticAuthorityContinuityProtocolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.document = json.loads((ROOT / PROTOCOL_PATH).read_text(encoding="utf-8"))

    def validate(self, document: dict | None = None) -> None:
        validate_protocol(document or self.document, root=ROOT)

    def test_current_protocol_is_valid(self) -> None:
        self.validate()

    def test_current_remaining_no_model_gates_are_recorded(self) -> None:
        gate = self.document["executionAdmission"]
        for key in (
            "nativeDisabledExposureProved",
            "localMonolithSelectedExposureProved",
            "publicPacketPrivateOracleLeakageRejected",
        ):
            self.assertTrue(gate[key], key)

    def test_current_runner_gap_is_explicit(self) -> None:
        self.assertEqual(
            "scripts/run_human_ai_collaboration_weak_agent_trial.py",
            self.document["sourceBindings"]["candidateWeakAgentRunner"],
        )
        self.assertNotIn("weakAgentRunner", self.document["sourceBindings"])
        gate = self.document["executionAdmission"]
        self.assertIs(gate["existingRunnerSupportsSemanticTreatments"], False)
        self.assertIs(gate["existingRunnerLoaderInvocationProved"], False)
        self.assertIs(gate["existingRunnerInstructionDeliveryProved"], False)

    def test_current_execution_plan_and_dry_runtime_preflights_are_recorded(self) -> None:
        sources = self.document["sourceBindings"]
        self.assertEqual(
            "scripts/build_human_ai_collaboration_semantic_authority_execution_plan.py",
            sources["semanticExecutionPlanBuilder"],
        )
        self.assertEqual(
            (
                "audits/human-ai-collaboration-semantic-authority-execution-"
                "plan-preflight-2026-08-01/REPORT.json"
            ),
            sources["semanticExecutionPlanPreflightReport"],
        )
        self.assertEqual(
            "scripts/run_human_ai_collaboration_semantic_authority_runtime_adapter.py",
            sources["semanticDryRuntimeAdapter"],
        )
        self.assertEqual(
            (
                "audits/human-ai-collaboration-semantic-authority-runtime-"
                "adapter-preflight-2026-08-01/REPORT.json"
            ),
            sources["semanticDryRuntimeAdapterPreflightReport"],
        )
        gate = self.document["executionAdmission"]
        self.assertIs(gate["semanticExecutionPlanAdapterImplemented"], True)
        self.assertIs(gate["semanticExecutionPlanPreflightPass"], True)
        self.assertIs(gate["semanticDryRuntimeAdapterImplemented"], True)
        self.assertIs(gate["semanticDryRuntimeAdapterPreflightPass"], True)
        self.assertIs(gate["semanticLiveRuntimeAdapterImplemented"], False)
        self.assertIs(gate["dispatchReadinessProved"], False)

    def test_rejects_existing_runner_semantic_support_promotion(self) -> None:
        document = copy.deepcopy(self.document)
        document["executionAdmission"][
            "existingRunnerSupportsSemanticTreatments"
        ] = True
        with self.assertRaisesRegex(RuntimeError, "runner compatibility overclaimed"):
            self.validate(document)

    def test_rejects_existing_runner_loader_promotion(self) -> None:
        document = copy.deepcopy(self.document)
        document["executionAdmission"][
            "existingRunnerLoaderInvocationProved"
        ] = True
        with self.assertRaisesRegex(RuntimeError, "runner evidence overclaimed"):
            self.validate(document)

    def test_rejects_execution_plan_preflight_rollback(self) -> None:
        document = copy.deepcopy(self.document)
        document["executionAdmission"][
            "semanticExecutionPlanPreflightPass"
        ] = False
        with self.assertRaisesRegex(RuntimeError, "execution-plan preflight"):
            self.validate(document)

    def test_rejects_dry_runtime_adapter_preflight_rollback(self) -> None:
        document = copy.deepcopy(self.document)
        document["executionAdmission"][
            "semanticDryRuntimeAdapterPreflightPass"
        ] = False
        with self.assertRaisesRegex(RuntimeError, "dry runtime-adapter preflight"):
            self.validate(document)

    def test_rejects_live_runtime_adapter_promotion(self) -> None:
        document = copy.deepcopy(self.document)
        document["executionAdmission"][
            "semanticLiveRuntimeAdapterImplemented"
        ] = True
        with self.assertRaisesRegex(RuntimeError, "live runtime adapter overclaimed"):
            self.validate(document)

    def test_rejects_dispatch_readiness_promotion(self) -> None:
        document = copy.deepcopy(self.document)
        document["executionAdmission"]["dispatchReadinessProved"] = True
        with self.assertRaisesRegex(RuntimeError, "dispatch readiness overclaimed"):
            self.validate(document)

    def test_rejects_mutable_live_local_treatment_path(self) -> None:
        document = copy.deepcopy(self.document)
        local = next(
            item
            for item in document["treatments"]
            if item["id"] == "SEM-LOCAL-ADAPTED-MONOLITH"
        )
        local["path"] = (
            "C:/Users/15521/.cc-switch/skills/grill-with-docs/SKILL.md"
        )
        with self.assertRaisesRegex(RuntimeError, "local treatment drifted"):
            self.validate(document)

    def test_rejects_live_run_promotion(self) -> None:
        document = copy.deepcopy(self.document)
        document["decision"]["liveExecutionStarted"] = True
        with self.assertRaisesRegex(RuntimeError, "decision overclaimed"):
            self.validate(document)

    def test_rejects_self_authored_arm(self) -> None:
        document = copy.deepcopy(self.document)
        document["fixtureDesign"]["selfAuthoredSkillArmPresent"] = True
        with self.assertRaisesRegex(RuntimeError, "fixture boundary"):
            self.validate(document)

    def test_rejects_unpinned_current_component_url(self) -> None:
        document = copy.deepcopy(self.document)
        current = next(
            item
            for item in document["treatments"]
            if item["id"] == "SEM-MATT-CURRENT-COMPOSITION"
        )
        current["components"][0]["rawUrl"] = (
            "https://raw.githubusercontent.com/mattpocock/skills/main/"
            "skills/engineering/grill-with-docs/SKILL.md"
        )
        with self.assertRaisesRegex(RuntimeError, "component pin drifted"):
            self.validate(document)

    def test_rejects_literal_context_filename_requirement(self) -> None:
        document = copy.deepcopy(self.document)
        document["fixtureDesign"]["literalContextMdFilenameRequired"] = True
        with self.assertRaisesRegex(RuntimeError, "fixture boundary"):
            self.validate(document)

    def test_rejects_silent_model_substitution(self) -> None:
        document = copy.deepcopy(self.document)
        document["modelPolicy"]["silentModelSubstitutionAllowed"] = True
        with self.assertRaisesRegex(RuntimeError, "weak-Agent policy"):
            self.validate(document)

    def test_rejects_non_fresh_lifecycle_phase(self) -> None:
        document = copy.deepcopy(self.document)
        document["lifecycleSequence"][2]["freshThreadRequired"] = False
        with self.assertRaisesRegex(RuntimeError, "lifecycle sequence"):
            self.validate(document)

    def test_rejects_cc_mutation_authority(self) -> None:
        document = copy.deepcopy(self.document)
        document["authorityBoundary"][
            "ccSwitchInstallUpdateReplaceOrDeleteAuthorized"
        ] = True
        with self.assertRaisesRegex(RuntimeError, "authority expanded"):
            self.validate(document)

    def test_rejects_dependency_complete_exposure_rollback(self) -> None:
        document = copy.deepcopy(self.document)
        current = next(
            item
            for item in document["treatments"]
            if item["id"] == "SEM-MATT-CURRENT-COMPOSITION"
        )
        current["dependencyCompleteExposureProved"] = False
        with self.assertRaisesRegex(RuntimeError, "exposure was not recorded"):
            self.validate(document)

    def test_rejects_current_host_refresh_exposure_rollback(self) -> None:
        document = copy.deepcopy(self.document)
        document["executionAdmission"]["currentHostRefreshExposureProved"] = False
        with self.assertRaisesRegex(RuntimeError, "current-host exposure"):
            self.validate(document)

    def test_rejects_native_disabled_exposure_rollback(self) -> None:
        document = copy.deepcopy(self.document)
        document["executionAdmission"]["nativeDisabledExposureProved"] = False
        with self.assertRaisesRegex(RuntimeError, "native-disabled exposure"):
            self.validate(document)

    def test_rejects_local_monolith_exposure_rollback(self) -> None:
        document = copy.deepcopy(self.document)
        document["executionAdmission"][
            "localMonolithSelectedExposureProved"
        ] = False
        with self.assertRaisesRegex(RuntimeError, "local monolith exposure"):
            self.validate(document)

    def test_rejects_private_oracle_isolation_rollback(self) -> None:
        document = copy.deepcopy(self.document)
        document["executionAdmission"][
            "publicPacketPrivateOracleLeakageRejected"
        ] = False
        with self.assertRaisesRegex(RuntimeError, "private-oracle isolation"):
            self.validate(document)


if __name__ == "__main__":
    unittest.main()
