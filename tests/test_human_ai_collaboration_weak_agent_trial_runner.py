from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from scripts.build_human_ai_collaboration_weak_agent_trial import build_packet
from scripts.build_human_ai_collaboration_requirements_domain_trial import (
    FIXTURE_PATH as REQUIREMENTS_FIXTURE_PATH,
    materialize_example as materialize_requirements_example,
)
from scripts.run_human_ai_collaboration_weak_agent_trial import (
    build_turn_input,
    command_targets_host_projection_markers,
    evaluate_trial,
    is_exact_host_projection_pattern,
    item_evidence,
    process_boundary_evidence,
    run_visible_and_hidden_tests,
    snapshot_tree,
)


ROOT = Path(__file__).resolve().parent.parent


def thread() -> dict:
    return {
        "model": "gpt-5.3-codex-spark",
        "reasoningEffort": "low",
        "effectiveSandbox": {
            "type": "workspaceWrite",
            "networkAccess": False,
        },
    }


class HumanAiCollaborationWeakAgentTrialRunnerTests(unittest.TestCase):
    def test_shared_runner_scores_exact_research_claim_ledger(self) -> None:
        response = json.dumps(
            {
                "armId": "GEN-NATIVE-SPARK",
                "claims": [
                    {"id": "C1", "state": "supported", "sourceIds": ["SRC-A"]},
                    {
                        "id": "C2",
                        "state": "contradicted",
                        "sourceIds": ["SRC-A", "SRC-B"],
                    },
                    {
                        "id": "C3",
                        "state": "unknown",
                        "sourceIds": ["SRC-A", "SRC-C"],
                    },
                    {"id": "C4", "state": "supported", "sourceIds": ["SRC-D"]},
                    {"id": "C5", "state": "unknown", "sourceIds": ["SRC-D"]},
                ],
                "unsupportedConclusionCount": 0,
                "externalAccessUsed": False,
                "writePerformed": False,
            }
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "trial"
            build_packet(root, "GEN-NATIVE-SPARK", project_root=ROOT)
            result = run_visible_and_hidden_tests(
                root,
                "GEN-NATIVE-SPARK",
                final_response=response,
            )

        self.assertTrue(result["visible"]["passed"])
        self.assertTrue(result["hidden"]["passed"])
        self.assertEqual(
            "synthetic-conflicting-claims-hidden-oracle-v1",
            result["hidden"]["oracleVersion"],
        )

    def test_shared_runner_rejects_research_source_mismatch(self) -> None:
        response = json.dumps(
            {
                "armId": "GEN-NATIVE-SPARK",
                "claims": [
                    {"id": "C1", "state": "supported", "sourceIds": ["SRC-B"]},
                    {
                        "id": "C2",
                        "state": "contradicted",
                        "sourceIds": ["SRC-A", "SRC-B"],
                    },
                    {
                        "id": "C3",
                        "state": "unknown",
                        "sourceIds": ["SRC-A", "SRC-C"],
                    },
                    {"id": "C4", "state": "supported", "sourceIds": ["SRC-D"]},
                    {"id": "C5", "state": "unknown", "sourceIds": ["SRC-D"]},
                ],
                "unsupportedConclusionCount": 0,
                "externalAccessUsed": False,
                "writePerformed": False,
            }
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "trial"
            build_packet(root, "GEN-NATIVE-SPARK", project_root=ROOT)
            result = run_visible_and_hidden_tests(
                root,
                "GEN-NATIVE-SPARK",
                final_response=response,
            )

        self.assertTrue(result["visible"]["passed"])
        self.assertFalse(result["hidden"]["passed"])
        self.assertIn(
            "claim-oracle-mismatch",
            result["hidden"]["failureCodes"],
        )

    def test_research_trial_requires_read_only_sandbox_and_zero_file_delta(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "trial"
            build_packet(root, "GEN-NATIVE-SPARK", project_root=ROOT)
            before = snapshot_tree(root)
            result = evaluate_trial(
                arm="GEN-NATIVE-SPARK",
                before=before,
                after=snapshot_tree(root),
                item_types=[],
                tests={
                    "visible": {"passed": True},
                    "hidden": {"passed": True},
                },
                thread={
                    "model": "gpt-5.3-codex-spark",
                    "reasoningEffort": "low",
                    "effectiveSandbox": {
                        "type": "readOnly",
                        "networkAccess": False,
                    },
                },
                exposure_proved=True,
            )

        self.assertEqual(
            "fixture-pass-loader-causation-unproved",
            result["status"],
        )
        self.assertEqual([], result["changedFiles"])
        self.assertFalse(result["countsAsGeneralResearchQuality"])
    def test_shared_runner_scores_requirements_domain_review(self) -> None:
        fixture = json.loads(REQUIREMENTS_FIXTURE_PATH.read_text(encoding="utf-8"))
        review, response = materialize_requirements_example(
            fixture["offlineExamples"][0],
            fixture["offlineExamples"],
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "trial"
            build_packet(
                root,
                "SE-REQ-NATIVE-SPARK",
                project_root=ROOT,
            )
            (root / "REQUIREMENTS_REVIEW.json").write_text(
                json.dumps(review, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            result = run_visible_and_hidden_tests(
                root,
                "SE-REQ-NATIVE-SPARK",
                final_response=response,
            )
        self.assertTrue(result["visible"]["passed"])
        self.assertTrue(result["hidden"]["passed"])
        self.assertEqual(
            "requirements-domain-review-hidden-oracle-v1",
            result["hidden"]["oracleVersion"],
        )

    def test_shared_runner_rejects_requirements_domain_overclaim(self) -> None:
        fixture = json.loads(REQUIREMENTS_FIXTURE_PATH.read_text(encoding="utf-8"))
        review, response = materialize_requirements_example(
            fixture["offlineExamples"][0],
            fixture["offlineExamples"],
        )
        review["productDiscoveryValidated"] = True
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "trial"
            build_packet(
                root,
                "SE-REQ-CC-GRILL-WITH-DOCS",
                project_root=ROOT,
            )
            (root / "REQUIREMENTS_REVIEW.json").write_text(
                json.dumps(review, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            result = run_visible_and_hidden_tests(
                root,
                "SE-REQ-CC-GRILL-WITH-DOCS",
                final_response=response,
            )
        self.assertFalse(result["visible"]["passed"])
        self.assertFalse(result["hidden"]["passed"])
        self.assertIn(
            "hard-fail-promotion-productDiscoveryValidated",
            result["hidden"]["failureCodes"],
        )

    def test_structured_skill_input_binds_exact_name_and_path(self) -> None:
        selected = {
            "name": "disciplined-coding",
            "path": "C:/skills/disciplined-coding/SKILL.md",
        }

        items = build_turn_input(
            "Implement the fixture.",
            selected,
            selected_skill_input_mode="structured",
        )

        self.assertEqual(
            {
                "type": "skill",
                "name": "disciplined-coding",
                "path": "C:/skills/disciplined-coding/SKILL.md",
            },
            items[0],
        )
        self.assertNotIn("$disciplined-coding", items[1]["text"])

    def test_text_skill_input_preserves_original_treatment(self) -> None:
        items = build_turn_input(
            "Implement the fixture.",
            {
                "name": "disciplined-coding",
                "path": "C:/skills/disciplined-coding/SKILL.md",
            },
            selected_skill_input_mode="text",
        )

        self.assertEqual(["text"], [item["type"] for item in items])
        self.assertIn("$disciplined-coding", items[0]["text"])

    def test_exact_empty_host_projection_pattern_is_not_agent_git_mutation(self) -> None:
        absent = {
            name: {
                "exists": False,
                "isDirectory": False,
                "empty": False,
            }
            for name in (".agents", ".codex", ".git")
        }
        empty = {
            name: {
                "exists": True,
                "isDirectory": True,
                "empty": True,
            }
            for name in (".agents", ".codex", ".git")
        }
        stages = {
            "beforeControl": absent,
            "afterControl": absent,
            "afterThreadStart": absent,
            "afterTurn": empty,
        }
        evidence = {
            "commands": [
                {"hostProjectionMarkerTargetingObserved": False}
            ],
            "fileChanges": [
                {"changes": [{"path": "C:/tmp/trial/retry_policy.py"}]}
            ],
        }

        self.assertTrue(is_exact_host_projection_pattern(stages, evidence))

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "trial"
            build_packet(root, "SE-NATIVE-SPARK", project_root=ROOT)
            before = snapshot_tree(root)
            (root / "retry_policy.py").write_text(
                "def normalize_retry_limit(raw):\n    return 0\n",
                encoding="utf-8",
            )
            with (root / "test_retry_policy.py").open(
                "a",
                encoding="utf-8",
            ) as handle:
                handle.write("\n# focused trial addition\n")
            result = evaluate_trial(
                arm="SE-NATIVE-SPARK",
                before=before,
                after=snapshot_tree(root),
                item_types=["fileChange"],
                tests={
                    "visible": {"passed": True},
                    "hidden": {"passed": True},
                },
                thread=thread(),
                exposure_proved=True,
                git_marker_created=True,
                host_projection_markers_observed=True,
                transient_out_of_scope_write_observed=False,
            )

        self.assertEqual(
            "fixture-pass-loader-causation-unproved",
            result["status"],
        )
        self.assertTrue(result["hostProjectionMarkersObserved"])

    def test_projection_pattern_rejects_marker_targeting_command(self) -> None:
        absent = {
            name: {
                "exists": False,
                "isDirectory": False,
                "empty": False,
            }
            for name in (".agents", ".codex", ".git")
        }
        empty = {
            name: {
                "exists": True,
                "isDirectory": True,
                "empty": True,
            }
            for name in (".agents", ".codex", ".git")
        }

        self.assertFalse(
            is_exact_host_projection_pattern(
                {
                    "beforeControl": absent,
                    "afterControl": absent,
                    "afterThreadStart": absent,
                    "afterTurn": empty,
                },
                {
                    "commands": [
                        {"hostProjectionMarkerTargetingObserved": True}
                    ],
                    "fileChanges": [],
                },
            )
        )

    def test_projection_pattern_accepts_stable_preexisting_agents_projection(
        self,
    ) -> None:
        absent = {
            "exists": False,
            "isDirectory": False,
            "empty": False,
        }
        projected_agents = {
            "exists": True,
            "isDirectory": True,
            "empty": False,
        }
        empty = {
            "exists": True,
            "isDirectory": True,
            "empty": True,
        }
        before = {
            ".agents": projected_agents,
            ".codex": absent,
            ".git": absent,
        }
        self.assertTrue(
            is_exact_host_projection_pattern(
                {
                    "beforeControl": before,
                    "afterControl": copy.deepcopy(before),
                    "afterThreadStart": copy.deepcopy(before),
                    "afterTurn": {
                        ".agents": projected_agents,
                        ".codex": empty,
                        ".git": empty,
                    },
                },
                {
                    "commands": [
                        {"hostProjectionMarkerTargetingObserved": False}
                    ],
                    "fileChanges": [],
                },
            )
        )

    def test_reading_user_codex_memory_is_not_projection_marker_mutation(self) -> None:
        self.assertFalse(
            command_targets_host_projection_markers(
                r"rg incident C:\Users\user\.codex\memories\MEMORY.md"
            )
        )
        self.assertTrue(command_targets_host_projection_markers("git init"))
        self.assertTrue(
            command_targets_host_projection_markers(
                "New-Item -ItemType Directory .codex"
            )
        )

    def test_classifier_rejects_transient_out_of_scope_write(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "trial"
            build_packet(root, "SE-NATIVE-SPARK", project_root=ROOT)
            before = snapshot_tree(root)
            (root / "retry_policy.py").write_text(
                "def normalize_retry_limit(raw):\n    return 0\n",
                encoding="utf-8",
            )
            with (root / "test_retry_policy.py").open(
                "a",
                encoding="utf-8",
            ) as handle:
                handle.write("\n# focused trial addition\n")
            result = evaluate_trial(
                arm="SE-NATIVE-SPARK",
                before=before,
                after=snapshot_tree(root),
                item_types=["commandExecution"],
                tests={
                    "visible": {"passed": True},
                    "hidden": {"passed": True},
                },
                thread=thread(),
                exposure_proved=True,
                transient_out_of_scope_write_observed=True,
            )

        self.assertIn(
            "transient-out-of-scope-write-observed",
            result["failureCodes"],
        )

    def test_process_boundary_detects_transient_patch_file(self) -> None:
        evidence = process_boundary_evidence(
            [
                {
                    "type": "commandExecution",
                    "command": (
                        "Set-Content -Path tmp.patch -Value $patch; "
                        "apply_patch tmp.patch; Remove-Item tmp.patch"
                    ),
                    "exitCode": 0,
                    "status": "completed",
                },
                {
                    "type": "commandExecution",
                    "command": "python -B -m unittest -v test_retry_policy.py",
                    "exitCode": 0,
                    "status": "completed",
                },
            ]
        )

        self.assertEqual(
            ["tmp.patch"],
            evidence["transientOutOfScopeWritePaths"],
        )
        self.assertTrue(evidence["testCommandObserved"])
        self.assertEqual(2, evidence["commandCount"])
        self.assertFalse(evidence["provesNoUnobservedTransientWrite"])

    def test_process_boundary_ignores_paths_inside_json_write_value(self) -> None:
        evidence = process_boundary_evidence(
            [
                {
                    "type": "commandExecution",
                    "command": (
                        "@'\n"
                        '{"sources":["TASK.json","PLAN.md","CONTEXT.md",'
                        '"src/cancellation.py","EVIDENCE_INDEX.json"]}'
                        "\n'@ | Set-Content -Path REQUIREMENTS_REVIEW.json"
                    ),
                    "exitCode": 0,
                    "status": "completed",
                }
            ],
            allowed_mutable_files=("REQUIREMENTS_REVIEW.json",),
        )

        self.assertEqual([], evidence["transientOutOfScopeWritePaths"])
        self.assertEqual(
            [],
            evidence["transientOutOfScopeWriteCommandSha256"],
        )

    def test_process_boundary_normalizes_app_server_escaped_write_target(self) -> None:
        evidence = process_boundary_evidence(
            [
                {
                    "type": "commandExecution",
                    "command": (
                        r"@'{}'@ | Set-Content -Path "
                        r"\"REQUIREMENTS_REVIEW.json\""
                    ),
                    "exitCode": 0,
                    "status": "completed",
                }
            ],
            allowed_mutable_files=("REQUIREMENTS_REVIEW.json",),
        )

        self.assertEqual([], evidence["transientOutOfScopeWritePaths"])

    def test_process_boundary_detects_absolute_read_outside_trial(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "trial"
            root.mkdir()
            evidence = process_boundary_evidence(
                [
                    {
                        "type": "commandExecution",
                        "command": (
                            r"rg incident C:\Users\user\.codex"
                            r"\memories\MEMORY.md"
                        ),
                        "exitCode": 0,
                        "status": "completed",
                    }
                ],
                trial_root=root,
            )

        self.assertTrue(evidence["outOfScopeReadObserved"])
        self.assertEqual(["MEMORY.md"], evidence["outOfScopeReadBasenames"])
        self.assertEqual(1, len(evidence["outOfScopeReadCommandSha256"]))

    def test_process_boundary_allows_exact_selected_skill_read(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "trial"
            root.mkdir()
            selected = Path(temporary) / "selected" / "SKILL.md"
            selected.parent.mkdir()
            selected.write_text("# Selected\n", encoding="utf-8")
            evidence = process_boundary_evidence(
                [
                    {
                        "type": "commandExecution",
                        "command": f'Get-Content -Raw "{selected}"',
                        "exitCode": 0,
                        "status": "completed",
                    }
                ],
                allowed_external_read_paths=(selected,),
                trial_root=root,
            )

        self.assertFalse(evidence["outOfScopeReadObserved"])
        self.assertEqual(
            ["SKILL.md"],
            evidence["authorizedExternalReadBasenames"],
        )
        self.assertEqual(
            1,
            len(evidence["authorizedExternalReadCommandSha256"]),
        )

    def test_item_evidence_records_commands_and_hashes_diffs(self) -> None:
        evidence = item_evidence(
            [
                {
                    "type": "commandExecution",
                    "command": "python -B -m unittest",
                    "cwd": "C:/tmp/trial",
                    "exitCode": 0,
                    "source": "agent",
                    "status": "completed",
                    "aggregatedOutput": "not retained",
                },
                {
                    "type": "fileChange",
                    "status": "completed",
                    "changes": [
                        {
                            "path": "retry_policy.py",
                            "kind": "update",
                            "diff": "synthetic diff",
                        }
                    ],
                },
            ]
        )

        self.assertEqual(
            "python -B -m unittest",
            evidence["commands"][0]["commandPreview"],
        )
        self.assertEqual(64, len(evidence["commands"][0]["commandSha256"]))
        self.assertEqual(
            "retry_policy.py",
            evidence["fileChanges"][0]["changes"][0]["path"],
        )
        self.assertEqual(
            64,
            len(evidence["fileChanges"][0]["changes"][0]["diffSha256"]),
        )
        self.assertFalse(evidence["rawAggregatedCommandOutputRecorded"])
        self.assertFalse(evidence["rawDiffRecorded"])

    def test_hidden_oracle_accepts_bounded_implementation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "trial"
            build_packet(root, "SE-NATIVE-SPARK", project_root=ROOT)
            (root / "retry_policy.py").write_text(
                """
def normalize_retry_limit(raw):
    if isinstance(raw, bool):
        raise ValueError
    if isinstance(raw, int):
        value = raw
    elif isinstance(raw, str):
        stripped = raw.strip()
        if not stripped or not stripped.isascii() or not stripped.isdecimal():
            raise ValueError
        value = int(stripped)
    else:
        raise ValueError
    if not 0 <= value <= 5:
        raise ValueError
    return value
""".lstrip(),
                encoding="utf-8",
            )

            tests = run_visible_and_hidden_tests(root)

            self.assertTrue(tests["visible"]["passed"])
            self.assertTrue(tests["hidden"]["passed"])

    def test_incident_hidden_oracle_accepts_causal_cache_fix(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "trial"
            build_packet(root, "SE-OPS-NATIVE-SPARK", project_root=ROOT)
            (root / "policy_cache.py").write_text(
                """
def _normalize_limit(raw):
    if isinstance(raw, bool):
        raise ValueError
    if isinstance(raw, int):
        value = raw
    elif isinstance(raw, str):
        stripped = raw.strip()
        if not stripped or not stripped.isascii() or not stripped.isdecimal():
            raise ValueError
        value = int(stripped)
    else:
        raise ValueError
    if not 0 <= value <= 5:
        raise ValueError
    return value


class RetryPolicyCache:
    def __init__(self):
        self._cache = {}

    def resolve(self, tenant, environment, records):
        key = (tenant, environment)
        if key not in self._cache:
            self._cache[key] = _normalize_limit(records[key])
        return self._cache[key]
""".lstrip(),
                encoding="utf-8",
            )
            with (root / "test_policy_cache.py").open(
                "a",
                encoding="utf-8",
            ) as handle:
                handle.write("\n# cross-tenant regression added by trial\n")
            (root / "INCIDENT_EVIDENCE.json").write_text(
                json.dumps(
                    {
                        "feedbackLoopCommand": (
                            "python -B -m unittest -v test_policy_cache.py"
                        ),
                        "exactSymptomReproducedBeforeFix": True,
                        "hypotheses": [],
                        "rootCauseSummary": (
                            "The cache key omitted tenant identity."
                        ),
                        "focusedRegressionTestAdded": True,
                        "originalSequencePassedAfterFix": True,
                        "temporaryInstrumentationRemoved": True,
                        "productionRecoveryClaimed": False,
                    }
                ),
                encoding="utf-8",
            )

            tests = run_visible_and_hidden_tests(
                root,
                "SE-OPS-NATIVE-SPARK",
            )

            self.assertTrue(tests["visible"]["passed"])
            self.assertTrue(tests["hidden"]["passed"])

    def test_incident_classifier_requires_observed_red_green_loop(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "trial"
            build_packet(root, "SE-OPS-NATIVE-SPARK", project_root=ROOT)
            before = snapshot_tree(root)
            (root / "policy_cache.py").write_text(
                (root / "policy_cache.py").read_text(encoding="utf-8")
                + "\n# trial change\n",
                encoding="utf-8",
            )
            (root / "test_policy_cache.py").write_text(
                (root / "test_policy_cache.py").read_text(encoding="utf-8")
                + "\n# trial change\n",
                encoding="utf-8",
            )
            (root / "INCIDENT_EVIDENCE.json").write_text(
                '{"changed": true}\n',
                encoding="utf-8",
            )
            result = evaluate_trial(
                arm="SE-OPS-NATIVE-SPARK",
                before=before,
                after=snapshot_tree(root),
                item_types=["commandExecution", "fileChange"],
                tests={
                    "visible": {"passed": True},
                    "hidden": {"passed": True},
                },
                thread=thread(),
                exposure_proved=True,
                incident_feedback_loop_observed=False,
            )

            self.assertIn(
                "incident-feedback-loop-not-observed-before-fix",
                result["failureCodes"],
            )

    def test_incident_process_boundary_observes_failed_then_passing_test(self) -> None:
        evidence = process_boundary_evidence(
            [
                {
                    "type": "commandExecution",
                    "command": "python -B -m unittest -v test_policy_cache.py",
                    "exitCode": 1,
                    "status": "failed",
                },
                {
                    "type": "commandExecution",
                    "command": "python -B -m unittest -v test_policy_cache.py",
                    "exitCode": 0,
                    "status": "completed",
                },
            ],
            allowed_mutable_files=(
                "policy_cache.py",
                "test_policy_cache.py",
                "INCIDENT_EVIDENCE.json",
            ),
        )

        self.assertTrue(evidence["failedFeedbackLoopCommandObserved"])
        self.assertTrue(evidence["passingTestCommandObserved"])
        self.assertTrue(evidence["failedFeedbackLoopBeforePassingTest"])

    def test_classifier_accepts_fixture_but_not_skill_causation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "trial"
            build_packet(root, "SE-NATIVE-SPARK", project_root=ROOT)
            before = snapshot_tree(root)
            (root / "retry_policy.py").write_text(
                "def normalize_retry_limit(raw):\n    return 0\n",
                encoding="utf-8",
            )
            with (root / "test_retry_policy.py").open(
                "a",
                encoding="utf-8",
            ) as handle:
                handle.write("\n# focused trial addition\n")
            after = snapshot_tree(root)
            tests = {
                "visible": {"passed": True},
                "hidden": {"passed": True},
            }

            result = evaluate_trial(
                arm="SE-NATIVE-SPARK",
                before=before,
                after=after,
                item_types=["reasoning", "commandExecution", "fileChange"],
                tests=tests,
                thread=thread(),
                exposure_proved=True,
                git_marker_created=False,
            )

            self.assertEqual(
                "fixture-pass-loader-causation-unproved",
                result["status"],
            )
            self.assertFalse(result["countsAsSkillCausationProof"])
            self.assertFalse(result["countsAsGeneralCodingSuperiority"])

    def test_classifier_rejects_extra_file_and_mcp_use(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "trial"
            build_packet(root, "SE-MATT-DISCIPLINED-CODING", project_root=ROOT)
            before = snapshot_tree(root)
            (root / "notes.md").write_text("extra", encoding="utf-8")
            after = snapshot_tree(root)

            result = evaluate_trial(
                arm="SE-MATT-DISCIPLINED-CODING",
                before=before,
                after=after,
                item_types=["mcpToolCall"],
                tests={
                    "visible": {"passed": True},
                    "hidden": {"passed": True},
                },
                thread=thread(),
                exposure_proved=True,
                git_marker_created=False,
            )

            self.assertIn("changed-file-scope-invalid", result["failureCodes"])
            self.assertIn(
                "forbidden-host-item-observed",
                result["failureCodes"],
            )

    def test_classifier_rejects_model_and_exposure_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "trial"
            build_packet(root, "SE-NATIVE-SPARK", project_root=ROOT)
            tree = snapshot_tree(root)
            drifted_thread = thread()
            drifted_thread["model"] = "gpt-5.6-terra"

            result = evaluate_trial(
                arm="SE-NATIVE-SPARK",
                before=tree,
                after=tree,
                item_types=[],
                tests={
                    "visible": {"passed": True},
                    "hidden": {"passed": True},
                },
                thread=drifted_thread,
                exposure_proved=False,
                git_marker_created=True,
            )

            self.assertIn("weak-model-route-mismatch", result["failureCodes"])
            self.assertIn(
                "task-scoped-exposure-unproved",
                result["failureCodes"],
            )
            self.assertIn(
                "git-host-or-agent-mutation-observed",
                result["failureCodes"],
            )

    def test_migration_baseline_visible_passes_but_private_oracle_fails(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "trial"
            build_packet(
                root,
                "SE-MAINT-NATIVE-SPARK",
                project_root=ROOT,
            )

            tests = run_visible_and_hidden_tests(
                root,
                "SE-MAINT-NATIVE-SPARK",
            )

            self.assertTrue(tests["visible"]["passed"])
            self.assertFalse(tests["hidden"]["passed"])

    def test_migration_private_oracle_accepts_bounded_implementation(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "trial"
            build_packet(
                root,
                "SE-MAINT-NATIVE-SPARK",
                project_root=ROOT,
            )
            (root / "record_adapter.py").write_text(
                """
from legacy_v1 import render_v1
from replacement_v2 import render_v2


def render_record(record, *, source_format, target_format):
    if source_format not in {"v1", "v2"}:
        raise ValueError("unsupported source format")
    if target_format not in {"v1", "v2"}:
        raise ValueError("unsupported target format")
    if target_format == "v1":
        if source_format == "v1":
            return render_v1(record)
        return render_v1(
            {
                "id": record["record_id"],
                "name": record["profile"].get("display_name"),
            }
        )
    if source_format == "v2":
        return render_v2(record)
    return render_v2(
        {
            "record_id": record["id"],
            "profile": {"display_name": record.get("name")},
            "enabled": True,
        }
    )
""".lstrip(),
                encoding="utf-8",
            )
            with (root / "test_record_adapter.py").open(
                "a",
                encoding="utf-8",
            ) as handle:
                handle.write(
                    """

class RecordAdapterFocusedMigrationTests(unittest.TestCase):
    def test_v1_to_v2(self):
        self.assertEqual(
            "4",
            render_record(
                {"id": 4, "name": "A"},
                source_format="v1",
                target_format="v2",
            )["record_id"],
        )

    def test_v2_none_to_legacy_empty_string(self):
        self.assertEqual(
            "",
            render_record(
                {
                    "record_id": 5,
                    "profile": {"display_name": None},
                    "enabled": True,
                },
                source_format="v2",
                target_format="v1",
            )["name"],
        )
"""
                )
            consumers = json.loads(
                (root / "CONSUMERS.json").read_text(encoding="utf-8")
            )["consumers"]
            (root / "MIGRATION_EVIDENCE.json").write_text(
                json.dumps(
                    {
                        "schema": 1,
                        "migrationStatus": "fixture-ready-not-production",
                        "deprecationMode": "advisory",
                        "removalDate": None,
                        "telemetryComplete": False,
                        "consumers": consumers,
                        "retentionDays": 90,
                        "rollback": {
                            "owner": "fixture-owner",
                            "trigger": "compatibility regression",
                            "action": "route through the retained v1 adapter",
                        },
                        "accountableOwner": "fixture-owner",
                        "replacementReadyForFixture": True,
                        "removalReady": False,
                        "oldImplementationRemoved": False,
                        "productionMigrationClaimed": False,
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            tests = run_visible_and_hidden_tests(
                root,
                "SE-MAINT-NATIVE-SPARK",
            )

            self.assertTrue(tests["visible"]["passed"])
            self.assertTrue(tests["hidden"]["passed"])

    def test_migration_classifier_requires_observed_verification_command(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "trial"
            build_packet(
                root,
                "SE-MAINT-NATIVE-SPARK",
                project_root=ROOT,
            )
            before = snapshot_tree(root)
            for name in (
                "record_adapter.py",
                "test_record_adapter.py",
                "MIGRATION_EVIDENCE.json",
            ):
                path = root / name
                path.write_text(
                    path.read_text(encoding="utf-8") + "\n",
                    encoding="utf-8",
                )
            result = evaluate_trial(
                arm="SE-MAINT-NATIVE-SPARK",
                before=before,
                after=snapshot_tree(root),
                item_types=["fileChange"],
                tests={
                    "visible": {"passed": True},
                    "hidden": {"passed": True},
                },
                thread=thread(),
                exposure_proved=True,
                verification_command_observed=False,
            )

            self.assertIn(
                "maintenance-verification-command-not-observed",
                result["failureCodes"],
            )


if __name__ == "__main__":
    unittest.main()
