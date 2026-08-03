#!/usr/bin/env python3
"""Run one bounded disposable weak-Agent collaboration trial through app-server."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import subprocess
import sys
from typing import Any

try:
    from .build_human_ai_collaboration_requirements_domain_trial import (
        FIXTURE_PATH as REQUIREMENTS_FIXTURE_PATH,
        evaluate_review as evaluate_requirements_review,
    )
except ImportError:
    from build_human_ai_collaboration_requirements_domain_trial import (
        FIXTURE_PATH as REQUIREMENTS_FIXTURE_PATH,
        evaluate_review as evaluate_requirements_review,
    )

try:
    from .build_human_ai_collaboration_weak_agent_trial import (
        ALLOWED_ARMS,
        IMMUTABLE_FILES,
        MUTABLE_FILES,
        SOURCE_FIXTURE_PATH,
        build_packet,
        canonical_sha256,
        selected_skill_for_arm,
        sha256_bytes,
        trial_spec_for_arm,
    )
    from .evaluate_human_ai_collaboration_comparative_protocol import (
        PROTOCOL_PATH as COMPARATIVE_PROTOCOL_PATH,
        evaluate_research_submission,
    )
    from .build_source_pinned_skill_projection import (
        candidate_by_id as projection_candidate_by_id,
        load_protocol as load_projection_protocol,
        materialize_candidate as materialize_projection_candidate,
    )
    from .probe_codex_app_server_skill_exposure import (
        AppServerSession,
        EFFORT,
        MODEL,
        PLUGIN_FEATURES,
        STATIC_MCP_NAMES,
        _thread_id,
        _turn_id,
        build_command,
        build_skill_config_override,
        classify_stderr,
        file_observation,
        initialize,
        inventory_summary,
        request_skills,
        resolve_codex_executable,
    )
    from .probe_codex_app_server_skill_treatment_fidelity import (
        CONFIGURABLE_SCOPES,
    )
    from .probe_source_pinned_skill_projection_preflight import (
        compare_inventory as compare_projected_inventory,
        select_projected_skill,
    )
    from .probe_codex_app_server_selected_skill_exposure import (
        compare_selected_inventory,
        select_exact_skill,
    )
except ImportError:
    from build_human_ai_collaboration_weak_agent_trial import (
        ALLOWED_ARMS,
        IMMUTABLE_FILES,
        MUTABLE_FILES,
        SOURCE_FIXTURE_PATH,
        build_packet,
        canonical_sha256,
        selected_skill_for_arm,
        sha256_bytes,
        trial_spec_for_arm,
    )
    from evaluate_human_ai_collaboration_comparative_protocol import (
        PROTOCOL_PATH as COMPARATIVE_PROTOCOL_PATH,
        evaluate_research_submission,
    )
    from build_source_pinned_skill_projection import (
        candidate_by_id as projection_candidate_by_id,
        load_protocol as load_projection_protocol,
        materialize_candidate as materialize_projection_candidate,
    )
    from probe_codex_app_server_skill_exposure import (
        AppServerSession,
        EFFORT,
        MODEL,
        PLUGIN_FEATURES,
        STATIC_MCP_NAMES,
        _thread_id,
        _turn_id,
        build_command,
        build_skill_config_override,
        classify_stderr,
        file_observation,
        initialize,
        inventory_summary,
        request_skills,
        resolve_codex_executable,
    )
    from probe_codex_app_server_skill_treatment_fidelity import (
        CONFIGURABLE_SCOPES,
    )
    from probe_source_pinned_skill_projection_preflight import (
        compare_inventory as compare_projected_inventory,
        select_projected_skill,
    )
    from probe_codex_app_server_selected_skill_exposure import (
        compare_selected_inventory,
        select_exact_skill,
    )


ROOT = Path(__file__).resolve().parent.parent
SHARED_RUNNER_ARMS = tuple(
    sorted(set(ALLOWED_ARMS) - {"GEN-NATIVE-SPARK"})
)
FORBIDDEN_ITEM_TYPES = {
    "mcpToolCall",
    "dynamicToolCall",
    "collabAgentToolCall",
    "webSearch",
}
HOST_PROJECTION_MARKER_DIRS = (".agents", ".codex", ".git")
COMMAND_FILE_TOKEN = re.compile(
    r"(?i)(?:[a-z]:[\\/]|/)?(?:[\w .-]+[\\/])*[\w.-]+\.(?:py|json|md|patch|tmp|bak)"
)
WRITE_COMMAND_MARKERS = (
    "apply_patch",
    "set-content",
    "writealltext",
    "new-item",
    "out-file",
    "remove-item",
    "move-item",
    "copy-item",
)
WRITE_PATH_TOKEN = r'(?:"([^"]+)"|\'([^\']+)\'|([^\s;|]+))'
WRITE_EXPLICIT_PATH = re.compile(
    rf"(?i)\b(?:set-content|out-file|remove-item|new-item)\b"
    rf"(?:(?![;|\r\n]).)*?-(?:literal)?path\s+{WRITE_PATH_TOKEN}"
)
WRITE_POSITIONAL_PATH = re.compile(
    rf"(?i)\b(?:set-content|out-file|remove-item|new-item)\b\s+"
    rf"(?!-){WRITE_PATH_TOKEN}"
)
WRITE_DESTINATION_PATH = re.compile(
    rf"(?i)\b(?:move-item|copy-item)\b"
    rf"(?:(?![;|\r\n]).)*?-destination\s+{WRITE_PATH_TOKEN}"
)
WRITE_ALL_TEXT_PATH = re.compile(
    rf"(?i)\bwritealltext\s*\(\s*{WRITE_PATH_TOKEN}"
)
HIDDEN_TEST_SOURCE = r'''
import os
import sys
import unittest

sys.path.insert(0, os.getcwd())
from retry_policy import normalize_retry_limit


class NormalizeRetryLimitHiddenTests(unittest.TestCase):
    def test_accepts_every_integer_in_range(self):
        for value in range(6):
            result = normalize_retry_limit(value)
            self.assertEqual(value, result)
            self.assertIs(type(result), int)

    def test_accepts_whitespace_padded_decimal_strings(self):
        for raw, expected in [
            ("0", 0),
            (" 1", 1),
            ("2 ", 2),
            ("\t3\n", 3),
            ("  5  ", 5),
        ]:
            result = normalize_retry_limit(raw)
            self.assertEqual(expected, result)
            self.assertIs(type(result), int)

    def test_rejects_invalid_types_and_strings(self):
        rejected = [
            True,
            False,
            1.0,
            None,
            [],
            "",
            "   ",
            "+1",
            "-1",
            "1.0",
            "one",
            "1_0",
        ]
        for raw in rejected:
            with self.subTest(raw=raw):
                with self.assertRaises(ValueError):
                    normalize_retry_limit(raw)

    def test_rejects_out_of_range_values(self):
        for raw in [-1, 6, 100, "-1", "6", " 10 "]:
            with self.subTest(raw=raw):
                with self.assertRaises(ValueError):
                    normalize_retry_limit(raw)


suite = unittest.defaultTestLoader.loadTestsFromTestCase(
    NormalizeRetryLimitHiddenTests
)
result = unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(0 if result.wasSuccessful() else 1)
'''
INCIDENT_HIDDEN_TEST_SOURCE = r'''
import json
import os
import sys
import unittest

sys.path.insert(0, os.getcwd())
from policy_cache import RetryPolicyCache


class TenantPolicyCacheIncidentHiddenTests(unittest.TestCase):
    def test_cross_tenant_sequences_are_isolated_in_both_directions(self):
        records = {
            ("alpha", "prod"): "1",
            ("beta", "prod"): "4",
        }
        alpha_first = RetryPolicyCache()
        self.assertEqual(1, alpha_first.resolve("alpha", "prod", records))
        self.assertEqual(4, alpha_first.resolve("beta", "prod", records))
        beta_first = RetryPolicyCache()
        self.assertEqual(4, beta_first.resolve("beta", "prod", records))
        self.assertEqual(1, beta_first.resolve("alpha", "prod", records))

    def test_hidden_tenants_reject_fixture_name_special_cases(self):
        records = {
            ("gamma", "prod"): "3",
            ("delta", "prod"): "5",
        }
        cache = RetryPolicyCache()
        self.assertEqual(3, cache.resolve("gamma", "prod", records))
        self.assertEqual(5, cache.resolve("delta", "prod", records))

    def test_cache_remains_enabled_and_stable_per_tenant_environment(self):
        records = {
            ("gamma", "prod"): "3",
            ("gamma", "dev"): "2",
            ("delta", "prod"): "5",
        }
        cache = RetryPolicyCache()
        self.assertEqual(3, cache.resolve("gamma", "prod", records))
        records[("gamma", "prod")] = "0"
        self.assertEqual(3, cache.resolve("gamma", "prod", records))
        self.assertEqual(2, cache.resolve("gamma", "dev", records))
        self.assertEqual(5, cache.resolve("delta", "prod", records))
        self.assertGreaterEqual(len(cache._cache), 3)

    def test_invalid_policy_remains_rejected(self):
        with self.assertRaises(ValueError):
            RetryPolicyCache().resolve(
                "broken",
                "prod",
                {("broken", "prod"): "9"},
            )

    def test_incident_evidence_is_bounded_and_truthful(self):
        with open("INCIDENT_EVIDENCE.json", encoding="utf-8") as handle:
            evidence = json.load(handle)
        for key in (
            "feedbackLoopCommand",
            "rootCauseSummary",
        ):
            self.assertIsInstance(evidence.get(key), str)
            self.assertTrue(evidence[key].strip())
        for key in (
            "exactSymptomReproducedBeforeFix",
            "focusedRegressionTestAdded",
            "originalSequencePassedAfterFix",
            "temporaryInstrumentationRemoved",
        ):
            self.assertIs(evidence.get(key), True)
        self.assertIs(evidence.get("productionRecoveryClaimed"), False)
        task = json.load(open("TASK.json", encoding="utf-8"))
        if task.get("armId") in {
            "SE-OPS-CC-DIAGNOSE",
            "SE-OPS-MATT-CURRENT-DIAGNOSING-BUGS",
        }:
            hypotheses = evidence.get("hypotheses")
            self.assertIsInstance(hypotheses, list)
            self.assertGreaterEqual(len(hypotheses), 3)
            self.assertLessEqual(len(hypotheses), 5)
            for hypothesis in hypotheses:
                rendered = (
                    hypothesis
                    if isinstance(hypothesis, str)
                    else json.dumps(hypothesis, sort_keys=True)
                )
                self.assertGreaterEqual(len(rendered.strip()), 10)


suite = unittest.defaultTestLoader.loadTestsFromTestCase(
    TenantPolicyCacheIncidentHiddenTests
)
result = unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(0 if result.wasSuccessful() else 1)
'''
MIGRATION_HIDDEN_TEST_SOURCE = r'''
import json
import os
import sys
import unittest

sys.path.insert(0, os.getcwd())
from record_adapter import render_record
import test_record_adapter


class VersionedRecordMigrationHiddenTests(unittest.TestCase):
    def test_unseen_v1_record_converts_to_v2(self):
        self.assertEqual(
            {
                "record_id": "41",
                "display_name": "Mira",
                "state": "active",
            },
            render_record(
                {"id": 41, "name": "Mira"},
                source_format="v1",
                target_format="v2",
            ),
        )

    def test_unseen_v2_record_converts_to_v1(self):
        self.assertEqual(
            {"id": "17", "name": "Qin"},
            render_record(
                {
                    "record_id": 17,
                    "profile": {"display_name": "Qin"},
                    "enabled": False,
                },
                source_format="v2",
                target_format="v1",
            ),
        )

    def test_observed_none_normalization_is_preserved(self):
        self.assertEqual(
            {"id": "23", "name": ""},
            render_record(
                {
                    "record_id": 23,
                    "profile": {"display_name": None},
                    "enabled": True,
                },
                source_format="v2",
                target_format="v1",
            ),
        )

    def test_archived_v1_record_remains_readable(self):
        self.assertEqual(
            {"id": "81", "name": "Archive"},
            render_record(
                {"id": 81, "name": "Archive", "archived": True},
                source_format="v1",
                target_format="v1",
            ),
        )

    def test_unsupported_source_and_target_formats_are_rejected(self):
        with self.assertRaises(ValueError):
            render_record(
                {"id": 1, "name": "X"},
                source_format="v0",
                target_format="v1",
            )
        with self.assertRaises(ValueError):
            render_record(
                {"id": 1, "name": "X"},
                source_format="v1",
                target_format="v3",
            )

    def test_focused_visible_regressions_were_added(self):
        suite = unittest.defaultTestLoader.loadTestsFromModule(
            test_record_adapter
        )
        self.assertGreaterEqual(suite.countTestCases(), 5)

    def test_migration_evidence_is_truthful_and_bounded(self):
        with open("MIGRATION_EVIDENCE.json", encoding="utf-8") as handle:
            evidence = json.load(handle)
        with open("CONSUMERS.json", encoding="utf-8") as handle:
            expected_consumers = json.load(handle)["consumers"]
        with open("USAGE_SNAPSHOT.json", encoding="utf-8") as handle:
            usage = json.load(handle)

        self.assertEqual(1, evidence.get("schema"))
        migration_status = evidence.get("migrationStatus")
        self.assertIsInstance(migration_status, str)
        normalized_status = migration_status.strip().lower()
        self.assertTrue(normalized_status)
        self.assertNotEqual("not-evaluated", normalized_status)
        self.assertNotIn(
            normalized_status,
            {
                "production-ready",
                "removal-ready",
                "complete",
                "completed",
                "removed",
            },
        )
        self.assertEqual("advisory", evidence.get("deprecationMode"))
        self.assertIsNone(evidence.get("removalDate"))
        self.assertIs(evidence.get("telemetryComplete"), False)
        self.assertIs(usage.get("telemetryComplete"), False)
        self.assertEqual(
            {
                item["id"]: (item["state"], item["dependency"])
                for item in expected_consumers
            },
            {
                item["id"]: (item["state"], item["dependency"])
                for item in evidence.get("consumers", [])
            },
        )
        opaque = next(
            item
            for item in evidence["consumers"]
            if item["id"] == "consumer.opaque-batch"
        )
        self.assertEqual(
            "unknown-incomplete-telemetry",
            opaque["state"],
        )
        self.assertGreaterEqual(evidence.get("retentionDays", 0), 90)
        rollback = evidence.get("rollback")
        self.assertIsInstance(rollback, dict)
        for key in ("owner", "trigger", "action"):
            self.assertIsInstance(rollback.get(key), str)
            self.assertTrue(rollback[key].strip())
        self.assertIsInstance(evidence.get("accountableOwner"), str)
        self.assertTrue(evidence["accountableOwner"].strip())
        self.assertIs(evidence.get("replacementReadyForFixture"), True)
        self.assertIs(evidence.get("removalReady"), False)
        self.assertIs(evidence.get("oldImplementationRemoved"), False)
        self.assertIs(evidence.get("productionMigrationClaimed"), False)


suite = unittest.defaultTestLoader.loadTestsFromTestCase(
    VersionedRecordMigrationHiddenTests
)
result = unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(0 if result.wasSuccessful() else 1)
'''


def snapshot_tree(root: Path) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root).as_posix()
        result[relative] = file_observation(path)
    return result


def changed_paths(
    before: dict[str, dict[str, Any]],
    after: dict[str, dict[str, Any]],
) -> list[str]:
    return sorted(
        path
        for path in set(before) | set(after)
        if before.get(path) != after.get(path)
    )


def item_evidence(items: list[dict[str, Any]]) -> dict[str, Any]:
    commands: list[dict[str, Any]] = []
    file_changes: list[dict[str, Any]] = []
    for item in items:
        item_type = item.get("type")
        if item_type == "commandExecution":
            command = str(item.get("command", ""))
            encoded_command = command.encode("utf-8")
            commands.append(
                {
                    "commandBytes": len(encoded_command),
                    "commandSha256": sha256_bytes(encoded_command),
                    "commandPreview": command[:240],
                    "commandPreviewTruncated": len(command) > 240,
                    "cwd": item.get("cwd"),
                    "exitCode": item.get("exitCode"),
                    "source": item.get("source"),
                    "status": item.get("status"),
                    "hostProjectionMarkerTargetingObserved": (
                        command_targets_host_projection_markers(command)
                    ),
                }
            )
        elif item_type == "fileChange":
            changes = []
            for change in item.get("changes", []):
                diff = change.get("diff")
                changes.append(
                    {
                        "path": change.get("path"),
                        "kind": change.get("kind"),
                        "diffSha256": (
                            sha256_bytes(diff.encode("utf-8"))
                            if isinstance(diff, str)
                            else None
                        ),
                    }
                )
            file_changes.append(
                {
                    "status": item.get("status"),
                    "changes": changes,
                }
            )
    return {
        "commands": commands,
        "fileChanges": file_changes,
        "rawAggregatedCommandOutputRecorded": False,
        "rawDiffRecorded": False,
    }


def extract_write_target_tokens(command: str) -> set[str]:
    targets: set[str] = set()
    for pattern in (
        WRITE_EXPLICIT_PATH,
        WRITE_POSITIONAL_PATH,
        WRITE_DESTINATION_PATH,
        WRITE_ALL_TEXT_PATH,
    ):
        for match in pattern.finditer(command):
            target = next(
                (group for group in match.groups() if group is not None),
                "",
            ).strip()
            target = target.replace('\\"', '"').replace("\\'", "'")
            target = target.strip("\"'")
            if target:
                targets.add(target)
    return targets


def command_targets_host_projection_markers(command: str) -> bool:
    text = command.lower()
    marker_tokens = tuple(name.lower() for name in HOST_PROJECTION_MARKER_DIRS)
    marker_creation_tokens = (
        "git init",
        "mkdir .git",
        "new-item .git",
        "mkdir .agents",
        "new-item .agents",
        "mkdir .codex",
        "new-item .codex",
    )
    new_item_marker = re.search(
        r"(?i)\bnew-item\b(?:(?![;|\r\n]).)*"
        r"(?:^|\s)(?:\.agents|\.codex|\.git)(?=\s|$)",
        command,
    )
    write_targets = {
        target.replace("\\", "/").lower()
        for target in extract_write_target_tokens(command)
    }
    return (
        any(token in text for token in marker_creation_tokens)
        or new_item_marker is not None
        or (
        any(
            target == token or target.endswith(f"/{token}")
            for target in write_targets
            for token in marker_tokens
        )
        )
    )


def process_boundary_evidence(
    items: list[dict[str, Any]],
    *,
    allowed_mutable_files: tuple[str, ...] = MUTABLE_FILES,
    allowed_external_read_paths: tuple[Path, ...] = (),
    trial_root: Path | None = None,
) -> dict[str, Any]:
    commands = [
        item for item in items if item.get("type") == "commandExecution"
    ]
    transient_paths: set[str] = set()
    transient_command_hashes: set[str] = set()
    out_of_scope_read_basenames: set[str] = set()
    out_of_scope_read_command_hashes: set[str] = set()
    authorized_external_read_basenames: set[str] = set()
    authorized_external_read_command_hashes: set[str] = set()
    allowed_write_names = {path.lower() for path in allowed_mutable_files}
    allowed_external_reads = {
        ("native", os.path.normcase(str(path.expanduser().resolve(strict=False))))
        for path in allowed_external_read_paths
    }
    for item in commands:
        command = str(item.get("command", ""))
        lowered = command.lower()
        if trial_root is not None:
            root = trial_root.resolve()
            for match in COMMAND_FILE_TOKEN.findall(command):
                candidate = Path(match)
                native_candidate: Path | None = None
                if candidate.is_absolute():
                    native_candidate = candidate.resolve(strict=False)
                    identity = (
                        "native",
                        os.path.normcase(str(native_candidate)),
                    )
                    basename = native_candidate.name
                elif PureWindowsPath(match).is_absolute():
                    windows_candidate = PureWindowsPath(match)
                    identity = (
                        "windows",
                        str(windows_candidate).replace("\\", "/").casefold(),
                    )
                    basename = windows_candidate.name
                elif PurePosixPath(match).is_absolute():
                    posix_candidate = PurePosixPath(match)
                    identity = ("posix", str(posix_candidate))
                    basename = posix_candidate.name
                else:
                    continue
                if native_candidate is None or not native_candidate.is_relative_to(root):
                    command_hash = sha256_bytes(command.encode("utf-8"))
                    if identity in allowed_external_reads:
                        authorized_external_read_basenames.add(basename)
                        authorized_external_read_command_hashes.add(
                            command_hash
                        )
                    else:
                        out_of_scope_read_basenames.add(basename)
                        out_of_scope_read_command_hashes.add(command_hash)
        if not any(marker in lowered for marker in WRITE_COMMAND_MARKERS):
            continue
        referenced = {
            Path(target).name.lower()
            for target in extract_write_target_tokens(command)
        }
        out_of_scope = referenced - allowed_write_names
        if out_of_scope:
            transient_paths.update(out_of_scope)
            transient_command_hashes.add(
                sha256_bytes(command.encode("utf-8"))
            )
    failed_feedback_indexes = [
        index
        for index, item in enumerate(commands)
        if (
            item.get("status") == "failed"
            or item.get("exitCode") not in (0, None)
        )
        and any(
            token in str(item.get("command", "")).lower()
            for token in ("unittest", "test_policy_cache", "policy_cache")
        )
    ]
    passing_test_indexes = [
        index
        for index, item in enumerate(commands)
        if item.get("status") != "failed"
        and item.get("exitCode") in (0, None)
        and "unittest" in str(item.get("command", "")).lower()
    ]
    return {
        "commandCount": len(commands),
        "failedCommandCount": sum(
            item.get("status") == "failed" or item.get("exitCode") not in (0, None)
            for item in commands
        ),
        "testCommandObserved": any(
            "unittest" in str(item.get("command", "")).lower()
            for item in commands
        ),
        "failedFeedbackLoopCommandObserved": bool(failed_feedback_indexes),
        "passingTestCommandObserved": bool(passing_test_indexes),
        "failedFeedbackLoopBeforePassingTest": (
            bool(failed_feedback_indexes)
            and bool(passing_test_indexes)
            and min(failed_feedback_indexes) < max(passing_test_indexes)
        ),
        "transientOutOfScopeWritePaths": sorted(transient_paths),
        "transientOutOfScopeWriteCommandSha256": sorted(
            transient_command_hashes
        ),
        "outOfScopeReadObserved": bool(out_of_scope_read_basenames),
        "outOfScopeReadBasenames": sorted(out_of_scope_read_basenames),
        "outOfScopeReadCommandSha256": sorted(
            out_of_scope_read_command_hashes
        ),
        "authorizedExternalReadBasenames": sorted(
            authorized_external_read_basenames
        ),
        "authorizedExternalReadCommandSha256": sorted(
            authorized_external_read_command_hashes
        ),
        "transientObservationMethod": "command-evidence-heuristic",
        "provesNoUnobservedTransientWrite": False,
    }


def observe_host_projection_markers(root: Path) -> dict[str, dict[str, Any]]:
    observations: dict[str, dict[str, Any]] = {}
    for name in HOST_PROJECTION_MARKER_DIRS:
        path = root / name
        exists = path.exists()
        is_directory = path.is_dir() if exists else False
        observations[name] = {
            "exists": exists,
            "isDirectory": is_directory,
            "empty": (
                is_directory and not any(path.iterdir())
                if exists
                else False
            ),
        }
    return observations


def is_exact_host_projection_pattern(
    stages: dict[str, dict[str, dict[str, Any]]],
    evidence: dict[str, Any],
) -> bool:
    before = stages.get("beforeControl", {})
    if set(before) != set(HOST_PROJECTION_MARKER_DIRS):
        return False
    agents_before = before.get(".agents", {})
    if agents_before.get("exists") and (
        agents_before.get("isDirectory") is not True
        or agents_before.get("empty") is not False
    ):
        return False
    for name in (".codex", ".git"):
        if before.get(name, {}).get("exists"):
            return False
    for stage in ("afterControl", "afterThreadStart"):
        if stages.get(stage) != before:
            return False
    after_turn = stages.get("afterTurn", {})
    if set(after_turn) != set(HOST_PROJECTION_MARKER_DIRS):
        return False
    if agents_before.get("exists"):
        if after_turn.get(".agents") != agents_before:
            return False
    elif not (
        after_turn.get(".agents", {}).get("exists")
        and after_turn.get(".agents", {}).get("isDirectory")
        and after_turn.get(".agents", {}).get("empty")
    ):
        return False
    for name in (".codex", ".git"):
        observation = after_turn.get(name, {})
        if not (
            observation.get("exists")
            and observation.get("isDirectory")
            and observation.get("empty")
        ):
            return False
    marker_tokens = tuple(name.lower() for name in HOST_PROJECTION_MARKER_DIRS)
    for command in evidence.get("commands", []):
        if command.get("hostProjectionMarkerTargetingObserved"):
            return False
    for file_change in evidence.get("fileChanges", []):
        for change in file_change.get("changes", []):
            path = str(change.get("path", "")).replace("\\", "/").lower()
            normalized = f"/{path.strip('/')}/"
            if any(f"/{token}/" in normalized for token in marker_tokens):
                return False
    return True


def run_test_command(
    cwd: Path,
    command: list[str],
    *,
    input_text: str | None = None,
) -> dict[str, Any]:
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    completed = subprocess.run(
        command,
        cwd=cwd,
        input=input_text,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
        env=environment,
    )
    output = completed.stdout + completed.stderr
    return {
        "returnCode": completed.returncode,
        "passed": completed.returncode == 0,
        "outputBytes": len(output.encode("utf-8")),
        "outputSha256": sha256_bytes(output.encode("utf-8")),
        "rawOutputRecorded": False,
    }


def run_visible_and_hidden_tests(
    cwd: Path,
    arm: str = "SE-NATIVE-SPARK",
    *,
    final_response: str = "",
) -> dict[str, Any]:
    spec = trial_spec_for_arm(arm)
    if spec["scenarioId"] == "GEN-RESEARCH-01":
        try:
            submission = json.loads(final_response.strip())
            if not isinstance(submission, dict):
                raise TypeError("research response is not an object")
            claims = submission.get("claims")
            visible_failures: list[str] = []
            if not isinstance(claims, list):
                visible_failures.append("claims-not-list")
                claims = []
            claim_ids = [
                claim.get("id")
                for claim in claims
                if isinstance(claim, dict)
            ]
            if claim_ids != ["C1", "C2", "C3", "C4", "C5"]:
                visible_failures.append("claim-id-order-or-coverage-invalid")
            if any(
                not isinstance(claim, dict)
                or claim.get("state")
                not in {"supported", "contradicted", "unknown"}
                or not isinstance(claim.get("sourceIds"), list)
                for claim in claims
            ):
                visible_failures.append("claim-shape-invalid")
            if submission.get("armId") != "GEN-NATIVE-SPARK":
                visible_failures.append("arm-id-invalid")
            if not isinstance(submission.get("unsupportedConclusionCount"), int):
                visible_failures.append("unsupported-count-not-integer")
            if submission.get("externalAccessUsed") is not False:
                visible_failures.append("external-access-not-false")
            if submission.get("writePerformed") is not False:
                visible_failures.append("write-performed-not-false")
        except (json.JSONDecodeError, TypeError, ValueError) as error:
            submission = {}
            visible_failures = [f"response-json-invalid:{type(error).__name__}"]
        protocol = json.loads(
            (ROOT / COMPARATIVE_PROTOCOL_PATH).read_text(encoding="utf-8")
        )
        hidden_result = evaluate_research_submission(
            submission,
            load_research_oracle(),
            protocol,
        )
        visible_rendered = json.dumps(
            visible_failures,
            ensure_ascii=False,
            sort_keys=True,
        )
        hidden_rendered = json.dumps(
            hidden_result["failureCodes"],
            ensure_ascii=False,
            sort_keys=True,
        )
        return {
            "visible": {
                "returnCode": 0 if not visible_failures else 1,
                "passed": not visible_failures,
                "outputBytes": len(visible_rendered.encode("utf-8")),
                "outputSha256": sha256_bytes(
                    visible_rendered.encode("utf-8")
                ),
                "rawOutputRecorded": False,
                "failureCodes": visible_failures,
            },
            "hidden": {
                "returnCode": (
                    0
                    if hidden_result["status"] == "accepted-offline-contract"
                    else 1
                ),
                "passed": (
                    hidden_result["status"] == "accepted-offline-contract"
                ),
                "outputBytes": len(hidden_rendered.encode("utf-8")),
                "outputSha256": sha256_bytes(hidden_rendered.encode("utf-8")),
                "rawOutputRecorded": False,
                "oracleVersion": spec["hiddenOracleVersion"],
                "oracleSourceSha256": sha256_bytes(
                    SOURCE_FIXTURE_PATH.read_bytes()
                ),
                "failureCodes": hidden_result["failureCodes"],
            },
        }
    visible = run_test_command(
        cwd,
        [sys.executable, *spec["visibleTestCommand"][1:]],
    )
    if spec["scenarioId"] == "SE-DISCOVERY-REQ-01":
        try:
            review = json.loads(
                (cwd / "REQUIREMENTS_REVIEW.json").read_text(encoding="utf-8")
            )
            failures = evaluate_requirements_review(review, final_response)
        except (OSError, json.JSONDecodeError, TypeError, ValueError) as error:
            failures = [f"fail-review-read:{type(error).__name__}"]
        rendered = json.dumps(failures, ensure_ascii=False, sort_keys=True)
        return {
            "visible": visible,
            "hidden": {
                "returnCode": 0 if not failures else 1,
                "passed": not failures,
                "outputBytes": len(rendered.encode("utf-8")),
                "outputSha256": sha256_bytes(rendered.encode("utf-8")),
                "rawOutputRecorded": False,
                "oracleVersion": spec["hiddenOracleVersion"],
                "oracleSourceSha256": sha256_bytes(
                    REQUIREMENTS_FIXTURE_PATH.read_bytes()
                ),
                "failureCodes": failures,
            },
        }
    hidden_source = {
        "SE-IMPLEMENT-REVIEW-01": HIDDEN_TEST_SOURCE,
        "SE-OPS-INCIDENT-01": INCIDENT_HIDDEN_TEST_SOURCE,
        "SE-MAINT-MIGRATE-01": MIGRATION_HIDDEN_TEST_SOURCE,
    }[spec["scenarioId"]]
    hidden = run_test_command(
        cwd,
        [sys.executable, "-B", "-c", hidden_source],
    )
    hidden["oracleVersion"] = spec["hiddenOracleVersion"]
    hidden["oracleSourceSha256"] = sha256_bytes(
        hidden_source.encode("utf-8")
    )
    return {"visible": visible, "hidden": hidden}


def load_research_oracle() -> dict[str, Any]:
    fixture = json.loads(SOURCE_FIXTURE_PATH.read_text(encoding="utf-8"))
    return fixture["researchOracle"]


def final_agent_text(items: list[dict[str, Any]]) -> str:
    messages = [
        str(item.get("text"))
        for item in items
        if item.get("type") == "agentMessage"
        and isinstance(item.get("text"), str)
    ]
    return messages[-1] if messages else ""


def build_turn_input(
    prompt: str,
    selected: dict[str, Any] | None,
    *,
    selected_skill_input_mode: str,
) -> list[dict[str, Any]]:
    if selected is None:
        return [
            {
                "type": "text",
                "text": "Treat TASK.json as the bound public task packet. " + prompt,
            }
        ]
    if selected_skill_input_mode == "text":
        return [
            {
                "type": "text",
                "text": (
                    f"Use ${selected['name']} for this task. "
                    "Treat TASK.json as the bound public task packet. "
                    + prompt
                ),
            }
        ]
    if selected_skill_input_mode == "structured":
        return [
            {
                "type": "skill",
                "name": selected["name"],
                "path": selected["path"],
            },
            {
                "type": "text",
                "text": "Treat TASK.json as the bound public task packet. " + prompt,
            },
        ]
    raise ValueError(
        f"unsupported selected Skill input mode: {selected_skill_input_mode}"
    )


def evaluate_trial(
    *,
    arm: str,
    before: dict[str, dict[str, Any]],
    after: dict[str, dict[str, Any]],
    item_types: list[str],
    tests: dict[str, Any],
    thread: dict[str, Any],
    exposure_proved: bool,
    git_marker_created: bool = False,
    host_projection_markers_observed: bool = False,
    transient_out_of_scope_write_observed: bool = False,
    incident_feedback_loop_observed: bool = True,
    verification_command_observed: bool = True,
    out_of_scope_read_observed: bool = False,
) -> dict[str, Any]:
    spec = trial_spec_for_arm(arm)
    mutable_files = tuple(spec["mutableFiles"])
    immutable_files = tuple(spec.get("immutableFiles", IMMUTABLE_FILES))
    changed = changed_paths(before, after)
    immutable_stable = all(
        before.get(path) == after.get(path) for path in immutable_files
    )
    changed_scope_valid = set(changed) == set(mutable_files)
    failures: list[str] = []
    if not changed_scope_valid:
        failures.append("changed-file-scope-invalid")
    if not immutable_stable:
        failures.append("immutable-trial-input-drift")
    if not tests["visible"]["passed"]:
        failures.append("visible-tests-not-passing")
    if not tests["hidden"]["passed"]:
        failures.append("hidden-tests-not-passing")
    forbidden = sorted(set(item_types) & FORBIDDEN_ITEM_TYPES)
    if forbidden:
        failures.append("forbidden-host-item-observed")
    if thread.get("model") != MODEL or thread.get("reasoningEffort") != EFFORT:
        failures.append("weak-model-route-mismatch")
    sandbox = thread.get("effectiveSandbox", thread.get("sandbox"))
    expected_sandbox_type = spec.get("sandboxType", "workspaceWrite")
    if (
        not isinstance(sandbox, dict)
        or sandbox.get("type") != expected_sandbox_type
    ):
        failures.append("workspace-sandbox-mismatch")
    if not isinstance(sandbox, dict) or sandbox.get("networkAccess") is not False:
        failures.append("network-sandbox-mismatch")
    if not exposure_proved:
        failures.append("task-scoped-exposure-unproved")
    if git_marker_created and not host_projection_markers_observed:
        failures.append("git-host-or-agent-mutation-observed")
    if transient_out_of_scope_write_observed:
        failures.append("transient-out-of-scope-write-observed")
    if out_of_scope_read_observed:
        failures.append("out-of-scope-read-observed")
    if (
        spec["scenarioId"] == "SE-OPS-INCIDENT-01"
        and not incident_feedback_loop_observed
    ):
        failures.append("incident-feedback-loop-not-observed-before-fix")
    if (
        spec["scenarioId"] == "SE-MAINT-MIGRATE-01"
        and not verification_command_observed
    ):
        failures.append("maintenance-verification-command-not-observed")
    return {
        "status": (
            "fixture-pass-loader-causation-unproved"
            if not failures
            else "fixture-fail-or-host-evidence-incomplete"
        ),
        "failureCodes": failures,
        "changedFiles": changed,
        "changedFileScopeValid": changed_scope_valid,
        "immutableInputsStable": immutable_stable,
        "forbiddenItemTypesObserved": forbidden,
        "visibleTestsPassed": tests["visible"]["passed"],
        "hiddenTestsPassed": tests["hidden"]["passed"],
        "countsAsGeneralCodingSuperiority": False,
        "countsAsGeneralResearchQuality": False,
        "countsAsSkillCausationProof": False,
        "countsAsProductionReadiness": False,
        "arm": arm,
        "scenarioId": spec["scenarioId"],
        "hostProjectionMarkersObserved": host_projection_markers_observed,
        "transientOutOfScopeWriteObserved": (
            transient_out_of_scope_write_observed
        ),
        "outOfScopeReadObserved": out_of_scope_read_observed,
    }


def run_trial(
    trial_root: Path,
    arm: str,
    *,
    codex_executable: str | None,
    timeout_seconds: float,
    selected_skill_input_mode: str = "text",
) -> dict[str, Any]:
    if arm not in SHARED_RUNNER_ARMS:
        raise ValueError(
            f"{arm} requires the dedicated read-only claim trial runner"
        )
    trial_root = trial_root.resolve()
    spec = trial_spec_for_arm(arm)
    build_manifest = build_packet(trial_root, arm, project_root=ROOT)
    arm_definition = ALLOWED_ARMS[arm]
    projection_manifest: dict[str, Any] | None = None
    if (
        isinstance(arm_definition, dict)
        and arm_definition.get("projectionCandidateId")
    ):
        projection_candidate = projection_candidate_by_id(
            load_projection_protocol(),
            str(arm_definition["projectionCandidateId"]),
        )
        projection_manifest = materialize_projection_candidate(
            projection_candidate,
            trial_root,
            matt_checkout=Path(
                "C:/tmp/mattpocock-skills-current-9603c1c"
            ),
            superpowers_package_root=Path(
                "C:/Users/15521/.codex/plugins/cache/"
                "openai-curated-remote/superpowers/6.1.1"
            ),
            allow_existing=True,
        )
    before = snapshot_tree(trial_root)
    marker_stages = {
        "beforeControl": observe_host_projection_markers(trial_root)
    }
    git_marker_before_control = marker_stages["beforeControl"][".git"]["exists"]
    config_path = (Path.home() / ".codex" / "config.toml").resolve()
    config_before = file_observation(config_path)
    executable = resolve_codex_executable(codex_executable)
    child_environment = os.environ.copy()
    child_environment["PYTHONDONTWRITEBYTECODE"] = "1"

    control = AppServerSession(
        build_command(executable),
        trial_root,
        min(timeout_seconds, 60.0),
        environment=child_environment,
    )
    try:
        initialize_result = initialize(control)
        control_skills = request_skills(control, trial_root, request_id=1)
        control.close()
    except BaseException:
        control.abort()
        raise
    marker_stages["afterControl"] = observe_host_projection_markers(trial_root)
    git_marker_after_control = marker_stages["afterControl"][".git"]["exists"]

    configurable_skills = [
        skill
        for skill in control_skills
        if skill["scope"] in CONFIGURABLE_SCOPES
    ]
    selected = selected_skill_for_arm(arm, trial_root)
    selected_control: dict[str, Any] | None = None
    enabled_paths: set[str] = set()
    if selected is not None:
        if selected.get("projectionCandidateId"):
            selected_control = select_projected_skill(
                control_skills,
                name=selected["name"],
                expected_path=Path(selected["path"]),
            )
        else:
            selected_control = select_exact_skill(
                control_skills,
                name=selected["name"],
                expected_path=Path(selected["path"]),
            )
        enabled_paths.add(str(selected_control["path"]))
    override = build_skill_config_override(
        configurable_skills,
        enabled_paths=enabled_paths,
    )
    command = build_command(executable, disable_override=override)
    session = AppServerSession(
        command,
        trial_root,
        timeout_seconds,
        environment=child_environment,
    )
    item_notifications: list[dict[str, Any]] = []
    try:
        initialize(session, experimental_api=True)
        effective_skills = request_skills(session, trial_root, request_id=1)
        session.send(
            {
                "id": 2,
                "method": "thread/start",
                "params": {
                    "model": MODEL,
                    "allowProviderModelFallback": False,
                    "cwd": str(trial_root),
                    "approvalPolicy": "never",
                    "sandbox": "read-only",
                    "ephemeral": True,
                    "runtimeWorkspaceRoots": [str(trial_root)],
                },
            }
        )
        thread_start = session.wait_for_response(2)
        thread_id = _thread_id(thread_start)
        marker_stages["afterThreadStart"] = observe_host_projection_markers(
            trial_root
        )
        git_marker_after_thread_start = marker_stages["afterThreadStart"][
            ".git"
        ]["exists"]
        if spec.get("sandboxType", "workspaceWrite") == "readOnly":
            requested_sandbox_policy = {
                "type": "readOnly",
                "networkAccess": False,
            }
            effective_sandbox_policy = thread_start.get("sandbox")
        else:
            requested_sandbox_policy = {
                "type": "workspaceWrite",
                "writableRoots": [str(trial_root)],
                "networkAccess": False,
                "excludeSlashTmp": False,
                "excludeTmpdirEnvVar": False,
            }
            session.send(
                {
                    "id": 4,
                    "method": "thread/settings/update",
                    "params": {
                        "threadId": thread_id,
                        "sandboxPolicy": requested_sandbox_policy,
                    },
                }
            )
            session.wait_for_response(4)
            settings_notifications = [
                message.get("params")
                for message in session.messages
                if message.get("method") == "thread/settings/updated"
                and isinstance(message.get("params"), dict)
                and message["params"].get("threadId") == thread_id
            ]
            if not settings_notifications:
                settings_notifications = [
                    session.wait_for_notification(
                        "thread/settings/updated",
                        predicate=lambda params: params.get("threadId")
                        == thread_id,
                    )
                ]
            if not settings_notifications:
                raise RuntimeError(
                    "thread/settings/update omitted the effective settings notification"
                )
            effective_sandbox_policy = settings_notifications[-1].get(
                "threadSettings",
                {},
            ).get("sandboxPolicy")
        packet = json.loads((trial_root / "TASK.json").read_text(encoding="utf-8"))
        prompt = packet["taskPrompt"]
        turn_input = build_turn_input(
            prompt,
            selected,
            selected_skill_input_mode=selected_skill_input_mode,
        )
        session.send(
            {
                "id": 3,
                "method": "turn/start",
                "params": {
                    "threadId": thread_id,
                    "model": MODEL,
                    "effort": EFFORT,
                    "sandboxPolicy": requested_sandbox_policy,
                    "runtimeWorkspaceRoots": [str(trial_root)],
                    "input": turn_input,
                },
            }
        )
        turn_start = session.wait_for_response(3)
        turn_id = _turn_id(turn_start)
        completed_turn: dict[str, Any] | None = None
        while True:
            message = session._next()
            if message.get("method") == "item/completed":
                params = message.get("params")
                if (
                    isinstance(params, dict)
                    and params.get("threadId") == thread_id
                    and params.get("turnId") == turn_id
                    and isinstance(params.get("item"), dict)
                ):
                    item_notifications.append(params)
            if message.get("method") == "turn/completed":
                params = message.get("params")
                if (
                    isinstance(params, dict)
                    and params.get("threadId") == thread_id
                    and isinstance(params.get("turn"), dict)
                    and params["turn"].get("id") == turn_id
                ):
                    completed_turn = params["turn"]
                    break
        if completed_turn is None:
            raise RuntimeError("turn/completed omitted the target turn")
        session.close()
    except BaseException:
        session.abort()
        raise

    items = [
        params["item"]
        for params in item_notifications
        if isinstance(params.get("item"), dict)
    ]
    item_types = [
        str(item.get("type"))
        for item in items
        if isinstance(item.get("type"), str)
    ]
    after_agent = snapshot_tree(trial_root)
    marker_stages["afterTurn"] = observe_host_projection_markers(trial_root)
    git_marker_after_turn = marker_stages["afterTurn"][".git"]["exists"]
    response = final_agent_text(items)
    tests = run_visible_and_hidden_tests(
        trial_root,
        arm,
        final_response=response,
    )
    after_tests = snapshot_tree(trial_root)
    if selected_control is None:
        enabled_configurable_count = sum(
            skill["scope"] in CONFIGURABLE_SCOPES and skill["enabled"]
            for skill in effective_skills
        )
        exposure = {
            "sameIdentitySet": {
                (row["name"], row["path"], row["scope"])
                for row in control_skills
            }
            == {
                (row["name"], row["path"], row["scope"])
                for row in effective_skills
            },
            "enabledConfigurableSkillCount": enabled_configurable_count,
            "allConfigurableSkillsDisabled": enabled_configurable_count == 0,
        }
        exposure_proved = (
            exposure["sameIdentitySet"]
            and exposure["allConfigurableSkillsDisabled"]
        )
    elif selected.get("projectionCandidateId"):
        exposure = compare_projected_inventory(
            control_skills,
            effective_skills,
            selected_path=str(selected_control["path"]),
            selected=True,
        )
        exposure_proved = all(
            exposure[key]
            for key in (
                "sameIdentitySet",
                "selectedIdentityPresent",
                "onlyExpectedConfigurableSkillEnabled",
                "allNonConfigurableStatesPreserved",
            )
        )
    else:
        exposure = compare_selected_inventory(
            control_skills,
            effective_skills,
            selected_path=str(selected_control["path"]),
        )
        exposure_proved = all(
            exposure[key]
            for key in (
                "sameIdentitySet",
                "onlySelectedUserSkillEnabled",
                "allOtherUserSkillsDisabled",
                "allNonUserStatesPreserved",
            )
        )
    thread = {
        "threadId": thread_id,
        "turnId": turn_id,
        "model": thread_start.get("model"),
        "reasoningEffort": thread_start.get("reasoningEffort"),
        "modelProvider": thread_start.get("modelProvider"),
        "initialSandbox": thread_start.get("sandbox"),
        "requestedSandbox": requested_sandbox_policy,
        "effectiveSandbox": effective_sandbox_policy,
        "approvalPolicy": thread_start.get("approvalPolicy"),
        "instructionSources": [
            str(path).replace("\\", "/")
            for path in thread_start.get("instructionSources", [])
        ],
        "ephemeral": True,
        "providerFallbackAllowed": False,
    }
    evidence = item_evidence(items)
    process_evidence = process_boundary_evidence(
        items,
        allowed_mutable_files=tuple(spec["mutableFiles"]),
        allowed_external_read_paths=(
            (Path(str(selected["path"])),)
            if selected is not None
            else ()
        ),
        trial_root=trial_root,
    )
    host_projection_pattern = is_exact_host_projection_pattern(
        marker_stages,
        evidence,
    )
    classification = evaluate_trial(
        arm=arm,
        before=before,
        after=after_agent,
        item_types=item_types,
        tests=tests,
        thread=thread,
        exposure_proved=exposure_proved,
        git_marker_created=(
            not git_marker_before_control
            and (
                git_marker_after_control
                or git_marker_after_thread_start
                or git_marker_after_turn
            )
        ),
        host_projection_markers_observed=host_projection_pattern,
        transient_out_of_scope_write_observed=bool(
            process_evidence["transientOutOfScopeWritePaths"]
        ),
        incident_feedback_loop_observed=(
            process_evidence["failedFeedbackLoopBeforePassingTest"]
        ),
        verification_command_observed=process_evidence[
            "testCommandObserved"
        ],
        out_of_scope_read_observed=process_evidence[
            "outOfScopeReadObserved"
        ],
    )
    config_after = file_observation(config_path)
    return {
        "schema": 1,
        "id": f"weak-agent-live-trial:{arm}",
        "scenarioId": spec["scenarioId"],
        "status": classification["status"],
        "host": {
            "userAgent": initialize_result.get("userAgent"),
            "platformFamily": initialize_result.get("platformFamily"),
            "platformOs": initialize_result.get("platformOs"),
        },
        "buildManifest": build_manifest,
        "thread": thread,
        "controlInventory": inventory_summary(control_skills),
        "effectiveInventory": inventory_summary(effective_skills),
        "exposure": exposure,
        "selectedSkill": selected,
        "sourcePinnedProjection": projection_manifest,
        "selectedSkillInputMode": (
            selected_skill_input_mode if selected is not None else None
        ),
        "promptExplicitlyNamedSelectedSkill": (
            selected is not None and selected_skill_input_mode == "text"
        ),
        "structuredSkillInputSent": (
            selected is not None and selected_skill_input_mode == "structured"
        ),
        "hostAcceptedStructuredSkillInput": (
            selected is not None
            and selected_skill_input_mode == "structured"
            and bool(turn_id)
        ),
        "loaderInvocationProved": False,
        "itemTypeCounts": dict(sorted(Counter(item_types).items())),
        "itemEvidence": evidence,
        "processBoundaryEvidence": process_evidence,
        "agentResponse": {
            "bytes": len(response.encode("utf-8")),
            "sha256": sha256_bytes(response.encode("utf-8")),
            "text": response,
        },
        "treeBefore": before,
        "treeAfterAgent": after_agent,
        "treeAfterHarnessTests": after_tests,
        "tests": tests,
        "classification": classification,
        "mutationBoundary": {
            "globalConfigBefore": config_before,
            "globalConfigAfter": config_after,
            "globalConfigStable": config_before == config_after,
            "gitMarkerBeforeControl": git_marker_before_control,
            "gitMarkerAfterControl": git_marker_after_control,
            "gitMarkerAfterThreadStart": git_marker_after_thread_start,
            "gitMarkerAfterTurn": git_marker_after_turn,
            "gitMarkerCreatedDuringRun": (
                not git_marker_before_control
                and (
                    git_marker_after_control
                    or git_marker_after_thread_start
                    or git_marker_after_turn
                )
            ),
            "hostProjectionMarkerStages": marker_stages,
            "exactHostProjectionPatternObserved": host_projection_pattern,
            "dependencyInstallAuthorized": False,
            "externalWriteAuthorized": False,
        },
        "stderrClassification": classify_stderr(session.stderr_lines),
        "claimBoundary": {
            "provesBoundFixtureOutcome": classification["status"]
            == "fixture-pass-loader-causation-unproved",
            "provesSkillLoaderInvocation": False,
            "provesSkillInstructionsReachedModel": False,
            "provesSkillCausation": False,
            "provesGeneralCodingSuperiority": False,
            "provesGeneralResearchQuality": False,
            "provesProductionIncidentCompetence": False,
            "provesProductionMigrationCompetence": False,
            "provesRemovalAuthority": False,
            "provesCurrentMattValue": False,
            "provesProductionReadiness": False,
            "provesCrossHostValue": False,
        },
        "reportSha256": None,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trial-root", type=Path, required=True)
    parser.add_argument("--arm", choices=SHARED_RUNNER_ARMS, required=True)
    parser.add_argument("--codex-executable")
    parser.add_argument("--timeout-seconds", type=float, default=240.0)
    parser.add_argument("--output-report", type=Path)
    parser.add_argument(
        "--selected-skill-input-mode",
        choices=("text", "structured"),
        default="text",
    )
    arguments = parser.parse_args()
    report = run_trial(
        arguments.trial_root,
        arguments.arm,
        codex_executable=arguments.codex_executable,
        timeout_seconds=arguments.timeout_seconds,
        selected_skill_input_mode=arguments.selected_skill_input_mode,
    )
    report["reportSha256"] = canonical_sha256(
        {key: value for key, value in report.items() if key != "reportSha256"}
    )
    output = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    if arguments.output_report is not None:
        arguments.output_report.write_text(output + "\n", encoding="utf-8")
        print(
            json.dumps(
                {
                    "status": report["status"],
                    "outputReport": str(arguments.output_report.resolve()),
                    "reportSha256": report["reportSha256"],
                },
                ensure_ascii=True,
                sort_keys=True,
            )
        )
    else:
        print(output)
    return 0 if report["classification"]["status"].startswith("fixture-pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
