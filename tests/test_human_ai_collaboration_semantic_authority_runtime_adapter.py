from __future__ import annotations

import copy
import json
from pathlib import Path
import tempfile
import unittest

from scripts.build_human_ai_collaboration_semantic_authority_execution_plan import (
    compile_execution_plan,
)
from scripts.run_human_ai_collaboration_semantic_authority_runtime_adapter import (
    _normalized_runtime_path,
    build_runtime_skill_override,
    compile_phase_envelopes,
    run_runtime_adapter_preflight,
    validate_phase_envelopes,
    validate_runtime_adapter_report,
)


def fake_projection(treatment_id: str, runtime_root: Path) -> dict:
    names = {
        "SEM-NATIVE": [],
        "SEM-LOCAL-ADAPTED-MONOLITH": ["grill-with-docs"],
        "SEM-MATT-CURRENT-COMPOSITION": [
            "domain-modeling",
            "grill-with-docs",
            "grilling",
        ],
    }[treatment_id]
    paths = {}
    for name in names:
        path = runtime_root / ".agents" / "skills" / name / "SKILL.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"---\nname: {name}\n---\n", encoding="utf-8")
        paths[name] = str(path.resolve())
    projection = {
        "requiredSkillNames": names,
        "skillPaths": paths,
        "selectedEntry": (
            {"name": "grill-with-docs", "path": paths["grill-with-docs"]}
            if names
            else None
        ),
        "sourceProjectionVerified": True,
        "sourceExternalReadPerformed": treatment_id
        == "SEM-MATT-CURRENT-COMPOSITION",
    }
    if treatment_id == "SEM-LOCAL-ADAPTED-MONOLITH":
        projection["projectedTreeSha256"] = (
            "e1078020c41b954638ba94acda95a3340739908bd68b1db9bc2af129d3936035"
        )
    if treatment_id == "SEM-MATT-CURRENT-COMPOSITION":
        projection.update(
            {
                "projectedTreeSha256": (
                    "295c4f5819f38e49cd4955d81294a5da1ce3197d78fc52c24bfecaf92027daa5"
                ),
                "sourceRevision": "ed37663cc5fbef691ddfecd080dff42f7e7e350d",
                "sourceTransport": "git-object-exact-revision",
                "licenseSha256": (
                    "0e7ac423bf2c6e223b7c5b156f8cf72da49d748e56a1641402c31f22ad07dbb5"
                ),
            }
        )
    return projection


def fake_inventory_probe(
    runtime_root: Path,
    required_skill_names: list[str],
    skill_paths: dict[str, str],
) -> dict:
    repo_count = len(required_skill_names)
    counts = {"system": 6, "user": 41}
    if repo_count:
        counts = {"repo": repo_count, **counts}
    return {
        "status": "pass-no-turn",
        "requiredSkillNames": required_skill_names,
        "requiredSkillPaths": skill_paths,
        "allRequiredExactPathsPresent": True,
        "onlyExpectedConfigurableSkillsEnabled": True,
        "allNonConfigurableStatesPreserved": True,
        "controlInventory": {
            "countsByScope": counts,
            "enabledCountsByScope": counts,
        },
        "effectiveInventory": {
            "countsByScope": counts,
            "enabledCountsByScope": {
                **({"repo": repo_count} if repo_count else {}),
                "system": 6,
                "user": 0,
            },
        },
        "appServerSessionCount": 2,
        "appServerRequestCount": 4,
        "appServerInventoryRequestsTransmitted": True,
        "threadStarted": False,
        "turnStarted": False,
        "modelRequestSent": False,
    }


class SemanticAuthorityRuntimeAdapterTests(unittest.TestCase):
    def test_normalizes_actual_random_isolated_codex_home_prefix(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            runtime_root = (Path(temporary) / "runtime").resolve()
            path = (
                runtime_root
                / ".aah-codex-home-random-a1b2"
                / "skills"
                / ".system"
                / "example"
                / "SKILL.md"
            )
            self.assertEqual(
                "$CODEX_HOME/skills/.system/example/SKILL.md",
                _normalized_runtime_path(str(path), runtime_root),
            )

    def test_native_empty_configurable_inventory_uses_explicit_empty_override(self) -> None:
        self.assertEqual(
            "skills.config=[]",
            build_runtime_skill_override([], enabled_paths=set()),
        )
        with self.assertRaisesRegex(RuntimeError, "enabled Skill path"):
            build_runtime_skill_override(
                [],
                enabled_paths={"C:/missing/SKILL.md"},
            )

    def test_phase_envelopes_bind_runtime_and_public_sandbox_without_send(self) -> None:
        plan = compile_execution_plan("SEM-NATIVE", "SEM03-DRY-NATIVE-001")
        with tempfile.TemporaryDirectory() as temporary:
            runtime_root = (Path(temporary) / "runtime").resolve()
            runtime_root.mkdir()
            (runtime_root / "public").mkdir()
            envelopes = compile_phase_envelopes(
                plan,
                runtime_root,
                selected_skill=None,
            )

        self.assertEqual(4, len(envelopes))
        self.assertEqual([], validate_phase_envelopes(
            plan,
            envelopes,
            runtime_root,
            selected_skill=None,
        ))
        for envelope in envelopes:
            self.assertFalse(envelope["requestsTransmitted"])
            self.assertEqual(
                "gpt-5.3-codex-spark",
                envelope["threadStart"]["params"]["model"],
            )
            self.assertFalse(
                envelope["threadStart"]["params"]["allowProviderModelFallback"]
            )
            sandbox = envelope["threadSettingsUpdate"]["params"]["sandboxPolicy"]
            self.assertEqual("workspaceWrite", sandbox["type"])
            self.assertEqual([str(runtime_root / "public")], sandbox["writableRoots"])
            self.assertFalse(sandbox["networkAccess"])

    def test_current_treatment_sends_only_structured_entry_skill(self) -> None:
        plan = compile_execution_plan(
            "SEM-MATT-CURRENT-COMPOSITION",
            "SEM03-DRY-CURRENT-001",
        )
        with tempfile.TemporaryDirectory() as temporary:
            runtime_root = (Path(temporary) / "runtime").resolve()
            runtime_root.mkdir()
            (runtime_root / "public").mkdir()
            selected = {
                "name": "grill-with-docs",
                "path": str(
                    runtime_root
                    / ".agents"
                    / "skills"
                    / "grill-with-docs"
                    / "SKILL.md"
                ),
            }
            envelopes = compile_phase_envelopes(
                plan,
                runtime_root,
                selected_skill=selected,
            )

        for envelope in envelopes:
            turn_input = envelope["turnStart"]["params"]["input"]
            self.assertEqual("skill", turn_input[0]["type"])
            self.assertEqual("grill-with-docs", turn_input[0]["name"])
            self.assertEqual(selected["path"], turn_input[0]["path"])
            self.assertEqual(1, sum(item["type"] == "skill" for item in turn_input))

    def test_phase_validator_rejects_request_transmission_promotion(self) -> None:
        plan = compile_execution_plan("SEM-NATIVE", "SEM03-DRY-NATIVE-002")
        with tempfile.TemporaryDirectory() as temporary:
            runtime_root = (Path(temporary) / "runtime").resolve()
            runtime_root.mkdir()
            (runtime_root / "public").mkdir()
            envelopes = compile_phase_envelopes(plan, runtime_root, selected_skill=None)
            promoted = copy.deepcopy(envelopes)
            promoted[0]["requestsTransmitted"] = True

            self.assertIn(
                "hard-fail-runtime-request-transmitted",
                validate_phase_envelopes(
                    plan,
                    promoted,
                    runtime_root,
                    selected_skill=None,
                ),
            )

    def test_preflight_materializes_three_runtime_roots_and_cleans_up(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            process_parent = Path(temporary) / "process"
            report = run_runtime_adapter_preflight(
                process_parent,
                projection_materializer=fake_projection,
                inventory_probe=fake_inventory_probe,
            )

        self.assertEqual("preflight-pass-no-dispatch", report["status"])
        self.assertEqual(3, len(report["treatments"]))
        self.assertFalse(report["temporaryProcessRootRetained"])
        self.assertFalse(report["threadStarted"])
        self.assertFalse(report["turnStarted"])
        self.assertFalse(report["modelRequestSent"])
        self.assertEqual([], validate_runtime_adapter_report(report))

    def test_preflight_report_normalizes_temporary_runtime_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            process_parent = (Path(temporary) / "process").resolve()
            report = run_runtime_adapter_preflight(
                process_parent,
                projection_materializer=fake_projection,
                inventory_probe=fake_inventory_probe,
            )

        rendered = json.dumps(report, ensure_ascii=False).replace("\\", "/")
        self.assertNotIn(str(process_parent).replace("\\", "/"), rendered)
        current = next(
            row
            for row in report["treatments"]
            if row["treatmentId"] == "SEM-MATT-CURRENT-COMPOSITION"
        )
        self.assertEqual(
            "runtime/.agents/skills/grill-with-docs/SKILL.md",
            current["projection"]["selectedEntry"]["path"],
        )
        self.assertNotIn(
            "projectionManifestSha256",
            current["projection"],
        )

    def test_report_rejects_thread_turn_model_and_claim_promotion(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            report = run_runtime_adapter_preflight(
                Path(temporary) / "process",
                projection_materializer=fake_projection,
                inventory_probe=fake_inventory_probe,
            )
        promoted = copy.deepcopy(report)
        promoted["threadStarted"] = True
        promoted["turnStarted"] = True
        promoted["modelRequestSent"] = True
        promoted["claimBoundary"]["dispatchReadinessProved"] = True

        failures = validate_runtime_adapter_report(promoted)
        self.assertIn("hard-fail-runtime-dispatch", failures)
        self.assertIn("hard-fail-runtime-claim-promotion", failures)

    def test_report_rejects_treatment_projection_identity_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            report = run_runtime_adapter_preflight(
                Path(temporary) / "process",
                projection_materializer=fake_projection,
                inventory_probe=fake_inventory_probe,
            )
        mutated = copy.deepcopy(report)
        current = next(
            row
            for row in mutated["treatments"]
            if row["treatmentId"] == "SEM-MATT-CURRENT-COMPOSITION"
        )
        current["projection"]["requiredSkillNames"] = []
        current["projection"]["skillPaths"] = {}
        current["projection"]["selectedEntry"] = None

        self.assertIn(
            "hard-fail-runtime-treatment-projection",
            validate_runtime_adapter_report(mutated),
        )

    def test_report_rejects_treatment_send_inventory_and_claim_shape_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            report = run_runtime_adapter_preflight(
                Path(temporary) / "process",
                projection_materializer=fake_projection,
                inventory_probe=fake_inventory_probe,
            )
        mutated = copy.deepcopy(report)
        mutated["treatments"][0]["phaseRequestsTransmitted"] = True
        mutated["treatments"][0]["inventory"][
            "allRequiredExactPathsPresent"
        ] = False
        mutated["claimBoundary"].pop("semanticContinuityProved")

        failures = validate_runtime_adapter_report(mutated)
        self.assertIn("hard-fail-phase-request-transmitted", failures)
        self.assertIn("hard-fail-runtime-inventory-boundary", failures)
        self.assertIn("hard-fail-runtime-claim-promotion", failures)

    def test_report_rejects_session_and_current_source_identity_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            report = run_runtime_adapter_preflight(
                Path(temporary) / "process",
                projection_materializer=fake_projection,
                inventory_probe=fake_inventory_probe,
            )
        mutated = copy.deepcopy(report)
        mutated["appServerSessionCount"] = 4
        current = next(
            row
            for row in mutated["treatments"]
            if row["treatmentId"] == "SEM-MATT-CURRENT-COMPOSITION"
        )
        current["projection"]["sourceRevision"] = "0" * 40

        failures = validate_runtime_adapter_report(mutated)
        self.assertIn("hard-fail-runtime-session-boundary", failures)
        self.assertIn("hard-fail-runtime-treatment-projection", failures)

    def test_report_rejects_exact_host_inventory_count_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            report = run_runtime_adapter_preflight(
                Path(temporary) / "process",
                projection_materializer=fake_projection,
                inventory_probe=fake_inventory_probe,
            )
        mutated = copy.deepcopy(report)
        inventory = mutated["treatments"][0]["inventory"]
        inventory["controlInventory"]["countsByScope"]["user"] = 40
        inventory["effectiveInventory"]["countsByScope"]["user"] = 40

        self.assertIn(
            "hard-fail-runtime-inventory-boundary",
            validate_runtime_adapter_report(mutated),
        )


if __name__ == "__main__":
    unittest.main()
