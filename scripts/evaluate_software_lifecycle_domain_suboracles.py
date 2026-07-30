#!/usr/bin/env python3
"""Compose existing deterministic domain classifiers for the lifecycle slice."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from tempfile import TemporaryDirectory
from typing import Any

try:
    from .build_human_ai_collaboration_tdd_trial import (
        evaluate_tdd_timeline,
    )
    from .build_human_ai_collaboration_weak_agent_trial import (
        build_packet,
        trial_spec_for_arm,
    )
    from .evaluate_lifecycle_metabolism_fixtures import evaluate_case
    from .evaluate_software_lifecycle_architecture_security_suboracle import (
        EVALUATOR_PATH as ARCHITECTURE_SECURITY_EVALUATOR_PATH,
        FIXTURE_PATH as ARCHITECTURE_SECURITY_FIXTURE_PATH,
        build_architecture_security_suboracle_pack,
    )
    from .evaluate_process_fidelity_cumulative_loss_accounting import (
        build_cumulative_loss_ledger,
    )
    from .run_human_ai_collaboration_weak_agent_trial import (
        EFFORT,
        MODEL,
        changed_paths,
        evaluate_trial,
        run_visible_and_hidden_tests,
        snapshot_tree,
    )
except ImportError:  # pragma: no cover - direct script execution
    from build_human_ai_collaboration_tdd_trial import (
        evaluate_tdd_timeline,
    )
    from build_human_ai_collaboration_weak_agent_trial import (
        build_packet,
        trial_spec_for_arm,
    )
    from evaluate_lifecycle_metabolism_fixtures import evaluate_case
    from evaluate_software_lifecycle_architecture_security_suboracle import (
        EVALUATOR_PATH as ARCHITECTURE_SECURITY_EVALUATOR_PATH,
        FIXTURE_PATH as ARCHITECTURE_SECURITY_FIXTURE_PATH,
        build_architecture_security_suboracle_pack,
    )
    from evaluate_process_fidelity_cumulative_loss_accounting import (
        build_cumulative_loss_ledger,
    )
    from run_human_ai_collaboration_weak_agent_trial import (
        EFFORT,
        MODEL,
        changed_paths,
        evaluate_trial,
        run_visible_and_hidden_tests,
        snapshot_tree,
    )


ROOT = Path(__file__).resolve().parent.parent
TDD_FIXTURE_PATH = (
    "tests/fixtures/"
    "human-ai-collaboration-tdd-timeline-fixtures-2026-07-26.json"
)
METABOLISM_FIXTURE_PATH = (
    "tests/fixtures/lifecycle-metabolism-fixtures-2026-07-18.json"
)
CUMULATIVE_LOSS_PROTOCOL_PATH = (
    "registry/human-ai-collaboration-process-fidelity-chained-transform-"
    "trial-protocol-2026-07-27.json"
)
DOMAIN_SUBORACLE_ARTIFACT_ID = "DOMAIN-SUBORACLE-PACK"
WEAK_TRIAL_BUILDER_PATH = (
    "scripts/build_human_ai_collaboration_weak_agent_trial.py"
)
WEAK_TRIAL_RUNNER_PATH = (
    "scripts/run_human_ai_collaboration_weak_agent_trial.py"
)
DOMAIN_SUBORACLE_EVALUATOR_PATH = (
    "scripts/evaluate_software_lifecycle_domain_suboracles.py"
)

_UNITTEST_RESULT_LINE = re.compile(
    r"^(?P<method>test_[^\s]+) "
    r"\((?P<test_id>[^)]+)\) \.\.\. "
    r"(?P<status>ok|FAIL|ERROR)$"
)

INCIDENT_CAUSAL_FIX = '''
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
'''.lstrip()

INCIDENT_REGRESSION = '''


class RetryPolicyCacheCrossTenantRegressionTests(unittest.TestCase):
    def test_alpha_then_beta_remain_isolated(self):
        cache = RetryPolicyCache()
        self.assertEqual(1, cache.resolve("alpha", "prod", RECORDS))
        self.assertEqual(4, cache.resolve("beta", "prod", RECORDS))
'''

MIGRATION_BOUNDED_FIX = '''
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
'''.lstrip()

MIGRATION_REGRESSION = '''


class RecordAdapterFocusedMigrationTests(unittest.TestCase):
    def test_v1_to_v2(self):
        try:
            actual = render_record(
                {"id": 4, "name": "A"},
                source_format="v1",
                target_format="v2",
            )
        except Exception as error:
            actual = {"unexpectedException": type(error).__name__}
        self.assertEqual(
            {
                "record_id": "4",
                "display_name": "A",
                "state": "active",
            },
            actual,
        )

    def test_v2_none_to_legacy_empty_string(self):
        try:
            actual = render_record(
                {
                    "record_id": 5,
                    "profile": {"display_name": None},
                    "enabled": True,
                },
                source_format="v2",
                target_format="v1",
            )
        except Exception as error:
            actual = {"unexpectedException": type(error).__name__}
        self.assertEqual(
            {"id": "5", "name": ""},
            actual,
        )
'''

INCIDENT_BEHAVIOR_HIDDEN_SOURCE = r'''
import os
import sys
import unittest

sys.path.insert(0, os.getcwd())
from policy_cache import RetryPolicyCache


class IncidentBehaviorHiddenTests(unittest.TestCase):
    def test_hidden_tenants_remain_isolated(self):
        records = {
            ("hidden-a", "prod"): "1",
            ("hidden-b", "prod"): "5",
        }
        cache = RetryPolicyCache()
        self.assertEqual(1, cache.resolve("hidden-a", "prod", records))
        self.assertEqual(5, cache.resolve("hidden-b", "prod", records))


suite = unittest.defaultTestLoader.loadTestsFromTestCase(
    IncidentBehaviorHiddenTests
)
result = unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(0 if result.wasSuccessful() else 1)
'''

MIGRATION_BEHAVIOR_HIDDEN_SOURCE = r'''
import os
import sys
import unittest

sys.path.insert(0, os.getcwd())
from record_adapter import render_record


class MigrationBehaviorHiddenTests(unittest.TestCase):
    def test_hidden_v1_record_converts_to_v2(self):
        try:
            actual = render_record(
                {"id": 41, "name": "Mira"},
                source_format="v1",
                target_format="v2",
            )
        except Exception as error:
            actual = {"unexpectedException": type(error).__name__}
        self.assertEqual(
            {
                "record_id": "41",
                "display_name": "Mira",
                "state": "active",
            },
            actual,
        )


suite = unittest.defaultTestLoader.loadTestsFromTestCase(
    MigrationBehaviorHiddenTests
)
result = unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(0 if result.wasSuccessful() else 1)
'''


def _load(root: Path, relative_path: str) -> dict[str, Any]:
    return json.loads((root / relative_path).read_text(encoding="utf-8"))


def _file_sha256(root: Path, relative_path: str) -> str:
    return hashlib.sha256((root / relative_path).read_bytes()).hexdigest()


def _case(document: dict[str, Any], case_id: str) -> dict[str, Any]:
    return next(
        item for item in document["cases"] if item.get("id") == case_id
    )


def _runner_contract_result(
    *,
    arm: str,
    incident_feedback_loop_observed: bool = True,
    verification_command_observed: bool = True,
) -> dict[str, Any]:
    spec = trial_spec_for_arm(arm)
    mutable_files = tuple(spec["mutableFiles"])
    before = {
        path: {"sha256": f"before:{path}"} for path in mutable_files
    }
    after = {
        path: {"sha256": f"after:{path}"} for path in mutable_files
    }
    return evaluate_trial(
        arm=arm,
        before=before,
        after=after,
        item_types=[],
        tests={
            "visible": {"passed": True},
            "hidden": {"passed": True},
        },
        thread={
            "model": MODEL,
            "reasoningEffort": EFFORT,
            "effectiveSandbox": {
                "type": spec.get("sandboxType", "workspaceWrite"),
                "networkAccess": False,
            },
        },
        exposure_proved=True,
        incident_feedback_loop_observed=(
            incident_feedback_loop_observed
        ),
        verification_command_observed=verification_command_observed,
    )


def _stable_test_summary(tests: dict[str, Any]) -> dict[str, Any]:
    return {
        "visible": {
            "returnCode": tests["visible"]["returnCode"],
            "passed": tests["visible"]["passed"],
        },
        "hidden": {
            "returnCode": tests["hidden"]["returnCode"],
            "passed": tests["hidden"]["passed"],
            "oracleVersion": tests["hidden"].get("oracleVersion"),
            "oracleSourceSha256": tests["hidden"].get(
                "oracleSourceSha256"
            ),
        },
    }


def _canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _tree_sha256(tree: dict[str, dict[str, Any]]) -> str:
    return _canonical_sha256(tree)


def _classify_unittest_result(
    *,
    command: list[str],
    return_code: int,
    output: str,
    expected_test_ids: list[str],
) -> dict[str, Any]:
    parsed = []
    for line in output.splitlines():
        match = _UNITTEST_RESULT_LINE.match(line.strip())
        if match:
            parsed.append(match.groupdict())
    actual_test_ids = sorted(item["test_id"] for item in parsed)
    expected = sorted(expected_test_ids)
    exact_identity = actual_test_ids == expected
    statuses = [item["status"] for item in parsed]
    wrong_error_tokens = (
        "SyntaxError",
        "ImportError",
        "ModuleNotFoundError",
        "Ran 0 tests",
    )
    if return_code == 0 and exact_identity and statuses and all(
        status == "ok" for status in statuses
    ):
        failure_class = "green"
    elif (
        return_code != 0
        and exact_identity
        and statuses
        and all(status == "FAIL" for status in statuses)
        and "AssertionError" in output
        and not any(token in output for token in wrong_error_tokens)
    ):
        failure_class = "expected-behavior-assertion"
    else:
        failure_class = "wrong-error-or-test-identity"
    normalized_command = []
    inline_source_sha256 = None
    for index, part in enumerate(command):
        if index == 0:
            normalized_command.append("<python>")
        elif index > 0 and command[index - 1] == "-c":
            normalized_command.append("<inline-python>")
            inline_source_sha256 = hashlib.sha256(
                part.encode("utf-8")
            ).hexdigest()
        else:
            normalized_command.append(part)
    return {
        "command": normalized_command,
        "commandCanonicalSha256": _canonical_sha256(
            normalized_command
        ),
        "inlineSourceSha256": inline_source_sha256,
        "cwdClass": "disposable-trial-root",
        "returnCode": return_code,
        "passed": return_code == 0,
        "testCount": len(parsed),
        "expectedTestIds": expected,
        "actualTestIds": actual_test_ids,
        "testIdentityExact": exact_identity,
        "resultStatuses": statuses,
        "failureClass": failure_class,
        "diagnosticSummaryCanonicalSha256": _canonical_sha256(
            {
                "returnCode": return_code,
                "actualTestIds": actual_test_ids,
                "resultStatuses": statuses,
                "failureClass": failure_class,
            }
        ),
        "rawOutputRecorded": False,
        "rawOutputExcludedFromDeterministicReceipt": True,
    }


def _run_observed_unittest(
    *,
    cwd: Path,
    command: list[str],
    expected_test_ids: list[str],
) -> dict[str, Any]:
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    completed = subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
        env=environment,
    )
    return _classify_unittest_result(
        command=command,
        return_code=completed.returncode,
        output=completed.stdout + completed.stderr,
        expected_test_ids=expected_test_ids,
    )


def _stage_receipt(
    *,
    stage_id: str,
    tree: dict[str, dict[str, Any]],
    previous_receipt_sha256: str | None,
    changed_from_previous: list[str],
    command_observations: list[dict[str, Any]],
) -> dict[str, Any]:
    receipt = {
        "stageId": stage_id,
        "treeCanonicalSha256": _tree_sha256(tree),
        "previousReceiptSha256": previous_receipt_sha256,
        "changedFromPrevious": changed_from_previous,
        "commandObservationCanonicalSha256s": [
            _canonical_sha256(item)
            for item in command_observations
        ],
    }
    receipt["receiptSha256"] = _canonical_sha256(receipt)
    return receipt


def _red_gate(
    *,
    visible: dict[str, Any],
    hidden_behavior: dict[str, Any],
    pre_test_tree: dict[str, dict[str, Any]],
    red_tree: dict[str, dict[str, Any]],
    implementation_path: str,
    expected_red_mutations: list[str],
) -> dict[str, Any]:
    failures: list[str] = []
    if visible["failureClass"] != "expected-behavior-assertion":
        failures.append("visible-red-not-expected-behavior-assertion")
    if hidden_behavior["failureClass"] != (
        "expected-behavior-assertion"
    ):
        failures.append("hidden-red-not-expected-behavior-assertion")
    if (
        pre_test_tree.get(implementation_path)
        != red_tree.get(implementation_path)
    ):
        failures.append("implementation-mutated-before-red")
    if changed_paths(pre_test_tree, red_tree) != sorted(
        expected_red_mutations
    ):
        failures.append("red-stage-mutation-scope-invalid")
    return {
        "decision": "accept-red" if not failures else "reject-red",
        "failureCodes": failures,
    }


def run_incident_fixture_execution(
    *, root: Path = ROOT
) -> dict[str, Any]:
    """Run a hash-bound incident RED/mutation/GREEN calibration."""

    with TemporaryDirectory(prefix="aah-incident-zero-model-") as temporary:
        trial = Path(temporary) / "trial"
        manifest = build_packet(
            trial,
            "SE-OPS-NATIVE-SPARK",
            project_root=root,
        )
        stage_0_tree = snapshot_tree(trial)
        test_path = trial / "test_policy_cache.py"
        test_path.write_text(
            test_path.read_text(encoding="utf-8")
            + INCIDENT_REGRESSION,
            encoding="utf-8",
            newline="\n",
        )
        stage_1_tree = snapshot_tree(trial)
        focused_visible_command = [
            sys.executable,
            "-B",
            "-m",
            "unittest",
            "-v",
            (
                "test_policy_cache."
                "RetryPolicyCacheCrossTenantRegressionTests."
                "test_alpha_then_beta_remain_isolated"
            ),
        ]
        visible_red = _run_observed_unittest(
            cwd=trial,
            command=focused_visible_command,
            expected_test_ids=[
                (
                    "test_policy_cache."
                    "RetryPolicyCacheCrossTenantRegressionTests."
                    "test_alpha_then_beta_remain_isolated"
                )
            ],
        )
        hidden_behavior_command = [
            sys.executable,
            "-B",
            "-c",
            INCIDENT_BEHAVIOR_HIDDEN_SOURCE,
        ]
        hidden_red = _run_observed_unittest(
            cwd=trial,
            command=hidden_behavior_command,
            expected_test_ids=[
                (
                    "__main__.IncidentBehaviorHiddenTests."
                    "test_hidden_tenants_remain_isolated"
                )
            ],
        )
        red_gate = _red_gate(
            visible=visible_red,
            hidden_behavior=hidden_red,
            pre_test_tree=stage_0_tree,
            red_tree=stage_1_tree,
            implementation_path="policy_cache.py",
            expected_red_mutations=["test_policy_cache.py"],
        )
        (trial / "policy_cache.py").write_text(
            INCIDENT_CAUSAL_FIX,
            encoding="utf-8",
            newline="\n",
        )
        (trial / "INCIDENT_EVIDENCE.json").write_text(
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
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
            newline="\n",
        )
        stage_2_tree = snapshot_tree(trial)
        focused_visible_green = _run_observed_unittest(
            cwd=trial,
            command=focused_visible_command,
            expected_test_ids=visible_red["expectedTestIds"],
        )
        hidden_behavior_green = _run_observed_unittest(
            cwd=trial,
            command=hidden_behavior_command,
            expected_test_ids=hidden_red["expectedTestIds"],
        )
        final = run_visible_and_hidden_tests(
            trial,
            "SE-OPS-NATIVE-SPARK",
        )
        stage_3_tree = snapshot_tree(trial)
        changed = changed_paths(stage_0_tree, stage_3_tree)
        expected_changed = sorted(manifest["allowedMutableFiles"])
        stage_0 = _stage_receipt(
            stage_id="S0-packet-built",
            tree=stage_0_tree,
            previous_receipt_sha256=None,
            changed_from_previous=[],
            command_observations=[],
        )
        stage_1 = _stage_receipt(
            stage_id="S1-regression-red",
            tree=stage_1_tree,
            previous_receipt_sha256=stage_0["receiptSha256"],
            changed_from_previous=changed_paths(
                stage_0_tree,
                stage_1_tree,
            ),
            command_observations=[visible_red, hidden_red],
        )
        stage_2 = _stage_receipt(
            stage_id="S2-bounded-fix",
            tree=stage_2_tree,
            previous_receipt_sha256=stage_1["receiptSha256"],
            changed_from_previous=changed_paths(
                stage_1_tree,
                stage_2_tree,
            ),
            command_observations=[],
        )
        stage_3 = _stage_receipt(
            stage_id="S3-focused-and-private-green",
            tree=stage_3_tree,
            previous_receipt_sha256=stage_2["receiptSha256"],
            changed_from_previous=changed_paths(
                stage_2_tree,
                stage_3_tree,
            ),
            command_observations=[
                focused_visible_green,
                hidden_behavior_green,
            ],
        )
        return {
            "scenarioId": "SE-OPS-INCIDENT-01",
            "armId": "SE-OPS-NATIVE-SPARK",
            "executionClass": (
                "parent-zero-model-disposable-subprocess-tests"
            ),
            "redBeforeFix": {
                "visible": visible_red,
                "hidden": hidden_red,
                "gate": red_gate,
            },
            "greenAfterFix": {
                **_stable_test_summary(final),
                "focusedVisible": focused_visible_green,
                "hiddenBehavior": hidden_behavior_green,
            },
            "stageReceipts": [
                stage_0,
                stage_1,
                stage_2,
                stage_3,
            ],
            "stageReceiptChainValid": (
                stage_1["previousReceiptSha256"]
                == stage_0["receiptSha256"]
                and stage_2["previousReceiptSha256"]
                == stage_1["receiptSha256"]
                and stage_3["previousReceiptSha256"]
                == stage_2["receiptSha256"]
            ),
            "redImplementationHashStable": (
                stage_0_tree["policy_cache.py"]
                == stage_1_tree["policy_cache.py"]
            ),
            "redStageScopeExact": (
                changed_paths(stage_0_tree, stage_1_tree)
                == ["test_policy_cache.py"]
            ),
            "fixStageScopeExact": (
                changed_paths(stage_1_tree, stage_2_tree)
                == ["INCIDENT_EVIDENCE.json", "policy_cache.py"]
            ),
            "greenStageTreeStable": stage_2_tree == stage_3_tree,
            "changedFiles": changed,
            "changedFileScopeExact": changed == expected_changed,
            "immutableInputsStable": all(
                stage_0_tree.get(path) == stage_3_tree.get(path)
                for path in manifest["immutableFiles"]
            ),
            "agentDispatchCount": 0,
            "modelCallCount": 0,
            "sideEffectObservation": {
                "subprocessCommandsBound": True,
                "subprocessCwdBoundToDisposableRoot": True,
                "networkInstrumentationAvailable": False,
                "networkAbsenceProved": False,
                "outsideTemporaryRootInstrumentationAvailable": False,
                "externalWriteAbsenceProved": False,
                "gitCommandInvokedByEvaluator": False,
                "gitMutationAbsenceProved": False,
            },
            "claimBoundary": {
                "liveIncidentHandled": False,
                "productionRecoveryProved": False,
                "agentCompetenceProved": False,
                "skillValueProved": False,
                "networkAbsenceProved": False,
                "externalWriteAbsenceProved": False,
                "gitMutationAbsenceProved": False,
            },
        }


def run_migration_fixture_execution(
    *, root: Path = ROOT
) -> dict[str, Any]:
    """Run a hash-bound migration RED/mutation/GREEN calibration."""

    with TemporaryDirectory(prefix="aah-migration-zero-model-") as temporary:
        trial = Path(temporary) / "trial"
        manifest = build_packet(
            trial,
            "SE-MAINT-NATIVE-SPARK",
            project_root=root,
        )
        stage_0_tree = snapshot_tree(trial)
        test_path = trial / "test_record_adapter.py"
        test_path.write_text(
            test_path.read_text(encoding="utf-8")
            + MIGRATION_REGRESSION,
            encoding="utf-8",
            newline="\n",
        )
        stage_1_tree = snapshot_tree(trial)
        focused_visible_command = [
            sys.executable,
            "-B",
            "-m",
            "unittest",
            "-v",
            (
                "test_record_adapter."
                "RecordAdapterFocusedMigrationTests"
            ),
        ]
        visible_red = _run_observed_unittest(
            cwd=trial,
            command=focused_visible_command,
            expected_test_ids=[
                (
                    "test_record_adapter."
                    "RecordAdapterFocusedMigrationTests."
                    "test_v1_to_v2"
                ),
                (
                    "test_record_adapter."
                    "RecordAdapterFocusedMigrationTests."
                    "test_v2_none_to_legacy_empty_string"
                ),
            ],
        )
        hidden_behavior_command = [
            sys.executable,
            "-B",
            "-c",
            MIGRATION_BEHAVIOR_HIDDEN_SOURCE,
        ]
        hidden_red = _run_observed_unittest(
            cwd=trial,
            command=hidden_behavior_command,
            expected_test_ids=[
                (
                    "__main__.MigrationBehaviorHiddenTests."
                    "test_hidden_v1_record_converts_to_v2"
                )
            ],
        )
        red_gate = _red_gate(
            visible=visible_red,
            hidden_behavior=hidden_red,
            pre_test_tree=stage_0_tree,
            red_tree=stage_1_tree,
            implementation_path="record_adapter.py",
            expected_red_mutations=["test_record_adapter.py"],
        )
        (trial / "record_adapter.py").write_text(
            MIGRATION_BOUNDED_FIX,
            encoding="utf-8",
            newline="\n",
        )
        consumers = json.loads(
            (trial / "CONSUMERS.json").read_text(encoding="utf-8")
        )["consumers"]
        (trial / "MIGRATION_EVIDENCE.json").write_text(
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
                        "action": (
                            "route through the retained v1 adapter"
                        ),
                    },
                    "accountableOwner": "fixture-owner",
                    "replacementReadyForFixture": True,
                    "removalReady": False,
                    "oldImplementationRemoved": False,
                    "productionMigrationClaimed": False,
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
            newline="\n",
        )
        stage_2_tree = snapshot_tree(trial)
        focused_visible_green = _run_observed_unittest(
            cwd=trial,
            command=focused_visible_command,
            expected_test_ids=visible_red["expectedTestIds"],
        )
        hidden_behavior_green = _run_observed_unittest(
            cwd=trial,
            command=hidden_behavior_command,
            expected_test_ids=hidden_red["expectedTestIds"],
        )
        final = run_visible_and_hidden_tests(
            trial,
            "SE-MAINT-NATIVE-SPARK",
        )
        stage_3_tree = snapshot_tree(trial)
        changed = changed_paths(stage_0_tree, stage_3_tree)
        expected_changed = sorted(manifest["allowedMutableFiles"])
        stage_0 = _stage_receipt(
            stage_id="S0-packet-built",
            tree=stage_0_tree,
            previous_receipt_sha256=None,
            changed_from_previous=[],
            command_observations=[],
        )
        stage_1 = _stage_receipt(
            stage_id="S1-regression-red",
            tree=stage_1_tree,
            previous_receipt_sha256=stage_0["receiptSha256"],
            changed_from_previous=changed_paths(
                stage_0_tree,
                stage_1_tree,
            ),
            command_observations=[visible_red, hidden_red],
        )
        stage_2 = _stage_receipt(
            stage_id="S2-bounded-fix",
            tree=stage_2_tree,
            previous_receipt_sha256=stage_1["receiptSha256"],
            changed_from_previous=changed_paths(
                stage_1_tree,
                stage_2_tree,
            ),
            command_observations=[],
        )
        stage_3 = _stage_receipt(
            stage_id="S3-focused-and-private-green",
            tree=stage_3_tree,
            previous_receipt_sha256=stage_2["receiptSha256"],
            changed_from_previous=changed_paths(
                stage_2_tree,
                stage_3_tree,
            ),
            command_observations=[
                focused_visible_green,
                hidden_behavior_green,
            ],
        )
        return {
            "scenarioId": "SE-MAINT-MIGRATE-01",
            "armId": "SE-MAINT-NATIVE-SPARK",
            "executionClass": (
                "parent-zero-model-disposable-subprocess-tests"
            ),
            "redBeforeFix": {
                "visible": visible_red,
                "hidden": hidden_red,
                "gate": red_gate,
            },
            "greenAfterFix": {
                **_stable_test_summary(final),
                "focusedVisible": focused_visible_green,
                "hiddenBehavior": hidden_behavior_green,
            },
            "stageReceipts": [
                stage_0,
                stage_1,
                stage_2,
                stage_3,
            ],
            "stageReceiptChainValid": (
                stage_1["previousReceiptSha256"]
                == stage_0["receiptSha256"]
                and stage_2["previousReceiptSha256"]
                == stage_1["receiptSha256"]
                and stage_3["previousReceiptSha256"]
                == stage_2["receiptSha256"]
            ),
            "redImplementationHashStable": (
                stage_0_tree["record_adapter.py"]
                == stage_1_tree["record_adapter.py"]
            ),
            "redStageScopeExact": (
                changed_paths(stage_0_tree, stage_1_tree)
                == ["test_record_adapter.py"]
            ),
            "fixStageScopeExact": (
                changed_paths(stage_1_tree, stage_2_tree)
                == ["MIGRATION_EVIDENCE.json", "record_adapter.py"]
            ),
            "greenStageTreeStable": stage_2_tree == stage_3_tree,
            "changedFiles": changed,
            "changedFileScopeExact": changed == expected_changed,
            "immutableInputsStable": all(
                stage_0_tree.get(path) == stage_3_tree.get(path)
                for path in manifest["immutableFiles"]
            ),
            "agentDispatchCount": 0,
            "modelCallCount": 0,
            "sideEffectObservation": {
                "subprocessCommandsBound": True,
                "subprocessCwdBoundToDisposableRoot": True,
                "networkInstrumentationAvailable": False,
                "networkAbsenceProved": False,
                "outsideTemporaryRootInstrumentationAvailable": False,
                "externalWriteAbsenceProved": False,
                "gitCommandInvokedByEvaluator": False,
                "gitMutationAbsenceProved": False,
            },
            "claimBoundary": {
                "productionMigrationProved": False,
                "removalReadinessProved": False,
                "agentCompetenceProved": False,
                "skillValueProved": False,
                "networkAbsenceProved": False,
                "externalWriteAbsenceProved": False,
                "gitMutationAbsenceProved": False,
            },
        }


def build_domain_suboracle_pack(
    *, root: Path = ROOT
) -> dict[str, Any]:
    """Return recomputable, zero-model sub-oracle outputs and controls."""

    tdd_fixture = _load(root, TDD_FIXTURE_PATH)
    valid_tdd = evaluate_tdd_timeline(
        _case(
            tdd_fixture,
            "valid-red-before-production-then-green",
        )["events"]
    )
    invalid_tdd = evaluate_tdd_timeline(
        _case(tdd_fixture, "syntax-error-is-not-red")["events"]
    )

    metabolism_fixture = _load(root, METABOLISM_FIXTURE_PATH)
    valid_rollback = evaluate_case(
        _case(metabolism_fixture, "rollback-after-validation-failure")
    )
    invalid_retirement = evaluate_case(
        _case(
            metabolism_fixture,
            "reject-retirement-without-migration-or-rollback",
        )
    )
    valid_maintenance = evaluate_case(
        _case(metabolism_fixture, "retire-after-verified-migration")
    )

    valid_incident = _runner_contract_result(
        arm="SE-OPS-NATIVE-SPARK",
    )
    invalid_incident = _runner_contract_result(
        arm="SE-OPS-NATIVE-SPARK",
        incident_feedback_loop_observed=False,
    )
    valid_migration = _runner_contract_result(
        arm="SE-MAINT-NATIVE-SPARK",
    )
    invalid_migration = _runner_contract_result(
        arm="SE-MAINT-NATIVE-SPARK",
        verification_command_observed=False,
    )
    incident_execution = run_incident_fixture_execution(root=root)
    migration_execution = run_migration_fixture_execution(root=root)
    architecture_security_pack = (
        build_architecture_security_suboracle_pack(root=root)
    )

    cumulative_protocol = _load(
        root,
        CUMULATIVE_LOSS_PROTOCOL_PATH,
    )
    zero_loss_stages = [
        {
            "stageId": stage_id,
            "activeLossIds": [],
            "weightedDelta": 0,
        }
        for stage_id in (
            "requirements-domain",
            "architecture-design",
            "implementation-tdd",
            "independent-review-test-security",
            "release-rollback-gating",
            "observation-incident-handling",
            "maintenance-evolution",
        )
    ]
    zero_loss_ledger = build_cumulative_loss_ledger(
        zero_loss_stages,
        cumulative_protocol,
        cumulative_unique_loss_weight_max=0,
    )
    reintroduction_ledger = build_cumulative_loss_ledger(
        [
            {
                "stageId": "loss-introduced",
                "activeLossIds": ["invariant-omitted:authority"],
                "weightedDelta": 5,
            },
            {
                "stageId": "loss-recovered",
                "activeLossIds": [],
                "weightedDelta": 0,
            },
            {
                "stageId": "loss-reintroduced",
                "activeLossIds": ["invariant-omitted:authority"],
                "weightedDelta": 5,
            },
        ],
        cumulative_protocol,
    )
    syntax_error_control = _classify_unittest_result(
        command=["python", "-B", "-m", "unittest", "-v", "target"],
        return_code=1,
        output=(
            "ERROR: target (unittest.loader._FailedTest.target)\n"
            "SyntaxError: invalid syntax\n"
            "Ran 1 test in 0.001s\nFAILED (errors=1)\n"
        ),
        expected_test_ids=["fixture.TargetTests.test_expected_behavior"],
    )
    wrong_test_control = _classify_unittest_result(
        command=["python", "-B", "-m", "unittest", "-v", "wrong"],
        return_code=1,
        output=(
            "test_wrong (fixture.WrongTests.test_wrong) ... FAIL\n"
            "AssertionError: wrong test failed\n"
            "Ran 1 test in 0.001s\nFAILED (failures=1)\n"
        ),
        expected_test_ids=["fixture.TargetTests.test_expected_behavior"],
    )
    mutation_before_red_control = _red_gate(
        visible={"failureClass": "expected-behavior-assertion"},
        hidden_behavior={
            "failureClass": "expected-behavior-assertion"
        },
        pre_test_tree={
            "implementation.py": {"sha256": "before"},
            "test_implementation.py": {"sha256": "before-test"},
        },
        red_tree={
            "implementation.py": {"sha256": "mutated"},
            "test_implementation.py": {"sha256": "after-test"},
        },
        implementation_path="implementation.py",
        expected_red_mutations=["test_implementation.py"],
    )

    positive_acceptance = {
        "tdd": (
            valid_tdd["status"]
            == "accepted-offline-tdd-timeline"
        ),
        "releaseRollback": (
            valid_rollback["decision"] == "accept"
        ),
        "incidentContract": (
            valid_incident["status"]
            == "fixture-pass-loader-causation-unproved"
        ),
        "maintenancePolicy": (
            valid_maintenance["decision"] == "accept"
        ),
        "maintenanceRunnerContract": (
            valid_migration["status"]
            == "fixture-pass-loader-causation-unproved"
        ),
        "incidentDisposableFixture": (
            incident_execution["redBeforeFix"]["visible"]["passed"]
            is False
            and incident_execution["redBeforeFix"]["visible"][
                "failureClass"
            ]
            == "expected-behavior-assertion"
            and incident_execution["redBeforeFix"]["hidden"][
                "failureClass"
            ]
            == "expected-behavior-assertion"
            and incident_execution["redBeforeFix"]["gate"][
                "decision"
            ]
            == "accept-red"
            and incident_execution["greenAfterFix"]["visible"][
                "passed"
            ]
            is True
            and incident_execution["greenAfterFix"]["hidden"][
                "passed"
            ]
            is True
            and incident_execution["greenAfterFix"][
                "focusedVisible"
            ]["failureClass"]
            == "green"
            and incident_execution["greenAfterFix"][
                "hiddenBehavior"
            ]["failureClass"]
            == "green"
            and incident_execution["stageReceiptChainValid"] is True
            and incident_execution["redImplementationHashStable"]
            is True
            and incident_execution["redStageScopeExact"] is True
            and incident_execution["fixStageScopeExact"] is True
            and incident_execution["greenStageTreeStable"] is True
            and incident_execution["changedFileScopeExact"] is True
            and incident_execution["immutableInputsStable"] is True
        ),
        "migrationDisposableFixture": (
            migration_execution["redBeforeFix"]["visible"]["passed"]
            is False
            and migration_execution["redBeforeFix"]["visible"][
                "failureClass"
            ]
            == "expected-behavior-assertion"
            and migration_execution["redBeforeFix"]["hidden"][
                "failureClass"
            ]
            == "expected-behavior-assertion"
            and migration_execution["redBeforeFix"]["gate"][
                "decision"
            ]
            == "accept-red"
            and migration_execution["greenAfterFix"]["visible"][
                "passed"
            ]
            is True
            and migration_execution["greenAfterFix"]["hidden"][
                "passed"
            ]
            is True
            and migration_execution["greenAfterFix"][
                "focusedVisible"
            ]["failureClass"]
            == "green"
            and migration_execution["greenAfterFix"][
                "hiddenBehavior"
            ]["failureClass"]
            == "green"
            and migration_execution["stageReceiptChainValid"] is True
            and migration_execution["redImplementationHashStable"]
            is True
            and migration_execution["redStageScopeExact"] is True
            and migration_execution["fixStageScopeExact"] is True
            and migration_execution["greenStageTreeStable"] is True
            and migration_execution["changedFileScopeExact"] is True
            and migration_execution["immutableInputsStable"] is True
        ),
        "architecture": architecture_security_pack[
            "positiveAcceptance"
        ]["architecture"],
        "independentSecurityReview": architecture_security_pack[
            "positiveAcceptance"
        ]["independentSecurityReview"],
        "cumulativeLossControl": (
            zero_loss_ledger["cumulativeUniqueLossWeight"] == 0
            and zero_loss_ledger["peakActiveLossWeight"] == 0
        ),
    }
    negative_rejection = {
        "tddWrongRed": (
            invalid_tdd["status"]
            == "rejected-offline-tdd-timeline"
        ),
        "retirementWithoutSafeguards": (
            invalid_retirement["decision"] == "reject"
        ),
        "incidentWithoutFeedbackLoop": (
            invalid_incident["status"]
            == "fixture-fail-or-host-evidence-incomplete"
            and "incident-feedback-loop-not-observed-before-fix"
            in invalid_incident["failureCodes"]
        ),
        "maintenanceWithoutVerification": (
            invalid_migration["status"]
            == "fixture-fail-or-host-evidence-incomplete"
            and "maintenance-verification-command-not-observed"
            in invalid_migration["failureCodes"]
        ),
        "incidentPrivateOracleRejectsBuggyBaseline": (
            incident_execution["redBeforeFix"]["hidden"]["passed"]
            is False
        ),
        "migrationPrivateOracleRejectsIncompleteBaseline": (
            migration_execution["redBeforeFix"]["hidden"]["passed"]
            is False
        ),
        "syntaxFailureIsNotAcceptedAsRed": (
            syntax_error_control["failureClass"]
            == "wrong-error-or-test-identity"
        ),
        "wrongTestIdentityIsNotAcceptedAsRed": (
            wrong_test_control["failureClass"]
            == "wrong-error-or-test-identity"
        ),
        "implementationMutationBeforeRedIsRejected": (
            mutation_before_red_control["decision"] == "reject-red"
            and "implementation-mutated-before-red"
            in mutation_before_red_control["failureCodes"]
            and "red-stage-mutation-scope-invalid"
            in mutation_before_red_control["failureCodes"]
        ),
        "architectureSecurityNegativeControls": (
            architecture_security_pack[
                "allNegativeControlsRejected"
            ]
            is True
        ),
        "reintroducedLossNotDoubleCounted": (
            reintroduction_ledger["cumulativeUniqueLossWeight"] == 5
            and reintroduction_ledger["hops"][2][
                "reintroducedLossIds"
            ]
            == ["invariant-omitted:authority"]
        ),
    }
    return {
        "schema": 1,
        "kind": "software-lifecycle-domain-suboracle-pack",
        "mode": (
            "zero-model-recomputed-existing-classifiers-and-"
            "disposable-fixtures"
        ),
        "sourceBindings": [
            {
                "path": path,
                "fileSha256": _file_sha256(root, path),
            }
            for path in (
                TDD_FIXTURE_PATH,
                METABOLISM_FIXTURE_PATH,
                CUMULATIVE_LOSS_PROTOCOL_PATH,
                WEAK_TRIAL_BUILDER_PATH,
                WEAK_TRIAL_RUNNER_PATH,
                DOMAIN_SUBORACLE_EVALUATOR_PATH,
                ARCHITECTURE_SECURITY_FIXTURE_PATH,
                ARCHITECTURE_SECURITY_EVALUATOR_PATH,
            )
        ],
        "classifierBindings": [
            {
                "module": (
                    "scripts.build_human_ai_collaboration_tdd_trial"
                ),
                "callable": "evaluate_tdd_timeline",
            },
            {
                "module": "scripts.evaluate_lifecycle_metabolism_fixtures",
                "callable": "evaluate_case",
            },
            {
                "module": (
                    "scripts.run_human_ai_collaboration_weak_agent_trial"
                ),
                "callable": "evaluate_trial",
            },
            {
                "module": (
                    "scripts.evaluate_process_fidelity_"
                    "cumulative_loss_accounting"
                ),
                "callable": "build_cumulative_loss_ledger",
            },
            {
                "module": (
                    "scripts.evaluate_software_lifecycle_"
                    "domain_suboracles"
                ),
                "callable": "run_incident_fixture_execution",
            },
            {
                "module": (
                    "scripts.evaluate_software_lifecycle_"
                    "domain_suboracles"
                ),
                "callable": "run_migration_fixture_execution",
            },
            {
                "module": (
                    "scripts.evaluate_software_lifecycle_"
                    "architecture_security_suboracle"
                ),
                "callable": (
                    "build_architecture_security_suboracle_pack"
                ),
            },
        ],
        "results": {
            "architecture": architecture_security_pack["results"][
                "architecture"
            ],
            "independentSecurityReview": (
                architecture_security_pack["results"][
                    "independentSecurityReview"
                ]
            ),
            "tdd": {
                "positive": valid_tdd,
                "negativeControl": invalid_tdd,
            },
            "releaseRollback": {
                "positive": valid_rollback,
                "negativeControl": invalid_retirement,
            },
            "incident": {
                "positive": valid_incident,
                "negativeControl": invalid_incident,
                "disposableFixtureExecution": incident_execution,
            },
            "maintenance": {
                "policyPositive": valid_maintenance,
                "runnerPositive": valid_migration,
                "negativeControl": invalid_migration,
                "disposableFixtureExecution": migration_execution,
            },
            "cumulativeLoss": {
                "control": zero_loss_ledger,
                "reintroductionControl": reintroduction_ledger,
            },
            "redGateNegativeControls": {
                "syntaxError": syntax_error_control,
                "wrongTestIdentity": wrong_test_control,
                "mutationBeforeRed": mutation_before_red_control,
            },
        },
        "positiveAcceptance": positive_acceptance,
        "negativeControlRejection": negative_rejection,
        "allPositiveAccepted": all(positive_acceptance.values()),
        "allNegativeControlsRejected": all(
            negative_rejection.values()
        ),
        "claimBoundary": {
            "liveAgentBehaviorProved": False,
            "liveModelRouteProved": False,
            "domainTaskExecutionProved": False,
            "loaderCausationProved": False,
            "productionLifecycleProved": False,
        },
    }


def stage_suboracle_bindings(
    stage_class: str,
    pack: dict[str, Any],
) -> list[dict[str, Any]]:
    """Bind only the existing classifiers relevant to one lifecycle stage."""

    result_keys = {
        "architecture-design": ["architecture"],
        "implementation-tdd": ["tdd"],
        "independent-review-test-security": [
            "independentSecurityReview"
        ],
        "release-rollback-gating": ["releaseRollback"],
        "observation-incident-handling": ["incident"],
        "maintenance-evolution": ["maintenance", "cumulativeLoss"],
    }.get(stage_class, [])
    return [
        {
            "artifactId": DOMAIN_SUBORACLE_ARTIFACT_ID,
            "resultKey": key,
            "resultCanonicalSha256": hashlib.sha256(
                json.dumps(
                    pack["results"][key],
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            ).hexdigest(),
            "evidenceClass": (
                (
                    "recomputed-zero-model-existing-classifier-plus-"
                    "disposable-stage-receipts"
                )
                if key in {"incident", "maintenance"}
                else (
                    "zero-model-synthetic-seeded-fault-suboracle"
                    if key
                    in {"architecture", "independentSecurityReview"}
                    else "recomputed-zero-model-existing-classifier"
                )
            ),
        }
        for key in result_keys
    ]


def main() -> int:
    pack = build_domain_suboracle_pack()
    print(json.dumps(pack, ensure_ascii=False, indent=2))
    return (
        0
        if pack["allPositiveAccepted"]
        and pack["allNegativeControlsRejected"]
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
