#!/usr/bin/env python3
"""Normalize ordered Codex app-server items into a bounded TDD timeline."""

from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
import shlex
from typing import Any


NORMALIZER_CONTRACT_VERSION = "codex-app-server-tdd-normalizer-v2"
RAW_FIXTURE_SCHEMA = 1
RAW_FIXTURE_REQUIRED_FIELDS = {
    "id",
    "mutation",
    "expectedNormalizerStatus",
    "expectedOfflineStatus",
}
RAW_FIXTURE_NORMALIZER_STATUSES = {
    "normalized-observable",
    "normalization-incomplete-or-boundary-failed",
}
RAW_FIXTURE_OFFLINE_STATUSES = {
    "accepted-offline-tdd-timeline",
    "rejected-offline-tdd-timeline",
}
CAUSAL_ITEM_TYPES = {"commandExecution", "fileChange"}
KNOWN_NONCAUSAL_ITEM_TYPES = {
    "agentMessage",
    "contextCompaction",
    "hookPrompt",
    "plan",
    "reasoning",
    "userMessage",
}
BOUNDARY_ITEM_TYPES = {
    "collabAgentToolCall",
    "dynamicToolCall",
    "mcpToolCall",
    "webSearch",
}
KNOWN_NONCAUSAL_METHOD_PREFIXES = (
    "item/agentMessage/",
    "item/plan/",
    "item/reasoning/",
)
KNOWN_TURN_METHODS = {
    "turn/started",
    "turn/completed",
    "turn/diff/updated",
    "thread/tokenUsage/updated",
}
HOOK_METHODS = {"hook/started", "hook/completed"}
KNOWN_ITEM_METHODS = {
    "item/started",
    "item/completed",
    "item/commandExecution/outputDelta",
    "item/commandExecution/terminalInteraction",
    "item/fileChange/outputDelta",
    "item/fileChange/patchUpdated",
}
APPROVAL_METHODS = {
    "item/commandExecution/requestApproval",
    "item/fileChange/requestApproval",
    "item/tool/requestUserInput",
}
ALLOWED_MUTABLE_FILES = {
    "feature.py",
    "test_feature.py",
    "PROCESS_EVIDENCE.json",
}
TEST_TARGET_RE = re.compile(
    r"^test_feature(?:\.py)?(?:[.:]{1,2}[A-Za-z_][A-Za-z0-9_]*){2,}$"
)
RAN_TESTS_RE = re.compile(r"Ran\s+(\d+)\s+tests?", re.IGNORECASE)
MUTATING_COMMAND_RE = re.compile(
    r"\b(?:set-content|out-file|add-content|new-item|move-item|copy-item|"
    r"remove-item|apply_patch|tee)\b",
    re.IGNORECASE,
)
NULL_REDIRECTION_RE = re.compile(
    r"(?i)(?:\d|\*)?>{1,2}\s*(?:[\"']?\$null[\"']?|nul\b|/dev/null\b)"
)
FILE_REDIRECTION_RE = re.compile(r"(?:\d|\*)?>{1,2}")


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def validate_raw_fixture_document(document: dict[str, Any]) -> None:
    if document.get("schema") != RAW_FIXTURE_SCHEMA:
        raise RuntimeError("raw TDD app-server fixture schema mismatch")
    if document.get("normalizerContractVersion") != NORMALIZER_CONTRACT_VERSION:
        raise RuntimeError("raw TDD app-server normalizer contract mismatch")
    cases = document.get("cases")
    if not isinstance(cases, list) or not cases:
        raise RuntimeError("raw TDD app-server fixture cases missing")
    case_ids: list[str] = []
    mutations: list[str] = []
    for case in cases:
        if not isinstance(case, dict):
            raise RuntimeError("raw TDD app-server fixture case is not an object")
        if set(case) != RAW_FIXTURE_REQUIRED_FIELDS:
            raise RuntimeError("raw TDD app-server fixture case fields mismatch")
        if not all(
            isinstance(case.get(field), str) and case[field]
            for field in RAW_FIXTURE_REQUIRED_FIELDS
        ):
            raise RuntimeError("raw TDD app-server fixture case value invalid")
        if (
            case["expectedNormalizerStatus"]
            not in RAW_FIXTURE_NORMALIZER_STATUSES
        ):
            raise RuntimeError(
                "raw TDD app-server fixture normalizer status invalid"
            )
        if case["expectedOfflineStatus"] not in RAW_FIXTURE_OFFLINE_STATUSES:
            raise RuntimeError(
                "raw TDD app-server fixture offline status invalid"
            )
        case_ids.append(case["id"])
        mutations.append(case["mutation"])
    if len(case_ids) != len(set(case_ids)):
        raise RuntimeError("raw TDD app-server fixture case id duplicated")
    if len(mutations) != len(set(mutations)):
        raise RuntimeError("raw TDD app-server fixture mutation duplicated")
    required_mutations = {
        "none",
        "production-before-red",
        "syntax-red",
        "zero-tests-green",
        "output-conflict",
        "mixed-mutation",
        "out-of-scope",
        "missing-start",
        "unknown-method",
        "known-noncausal",
        "future-plan-shape",
        "identity-mismatch",
        "process-evidence",
        "opaque-write-command",
        "noncausal-empty-output",
    }
    if set(mutations) != required_mutations:
        raise RuntimeError("raw TDD app-server fixture mutation coverage mismatch")


def _dedupe(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


def _target_params(
    message: dict[str, Any],
    *,
    thread_id: str,
    turn_id: str,
) -> dict[str, Any] | None:
    params = message.get("params")
    if not isinstance(params, dict):
        return None
    if params.get("threadId") != thread_id:
        return None
    direct_turn = params.get("turnId")
    nested_turn = params.get("turn")
    nested_id = nested_turn.get("id") if isinstance(nested_turn, dict) else None
    if direct_turn != turn_id and nested_id != turn_id:
        return None
    return params


def _safe_relative_path(path_value: str, trial_root: Path) -> str | None:
    candidate = Path(path_value)
    if not candidate.is_absolute():
        candidate = trial_root / candidate
    resolved = candidate.resolve(strict=False)
    root = trial_root.resolve()
    if not resolved.is_relative_to(root):
        return None
    return resolved.relative_to(root).as_posix()


def _command_tokens(command: str) -> list[str]:
    try:
        return shlex.split(command, posix=False)
    except ValueError:
        return []


def _command_token_segments(command: str) -> list[list[str]]:
    primary = _command_tokens(command)
    segments = [primary]
    lowered = [token.strip("\"'").lower() for token in primary]
    for marker in ("-command", "-c"):
        if marker not in lowered:
            continue
        index = lowered.index(marker)
        if index + 1 >= len(primary):
            continue
        nested = primary[index + 1].strip("\"'")
        nested_tokens = _command_tokens(nested)
        if nested_tokens:
            segments.append(nested_tokens)
    return segments


def command_may_write_files(command: str) -> bool:
    if MUTATING_COMMAND_RE.search(command) is not None:
        return True
    without_null_redirections = NULL_REDIRECTION_RE.sub(
        "",
        command,
    )
    return FILE_REDIRECTION_RE.search(without_null_redirections) is not None


def _known_noncausal_plan_update(params: dict[str, Any]) -> bool:
    if set(params) != {"explanation", "plan", "threadId", "turnId"}:
        return False
    if not isinstance(params.get("explanation"), str):
        return False
    plan = params.get("plan")
    if not isinstance(plan, list) or not plan:
        return False
    for item in plan:
        if (
            not isinstance(item, dict)
            or set(item) != {"status", "step"}
            or item.get("status")
            not in {"pending", "inProgress", "completed"}
            or not isinstance(item.get("step"), str)
            or not item["step"]
        ):
            return False
    return True


def classify_unittest_invocation(command: str) -> dict[str, Any]:
    for segment in _command_token_segments(command):
        tokens = [token.strip("\"'") for token in segment]
        lowered = [token.lower() for token in tokens]
        try:
            module_index = lowered.index("-m")
        except ValueError:
            continue
        if (
            module_index + 1 >= len(tokens)
            or lowered[module_index + 1] != "unittest"
        ):
            continue
        targets = [
            token
            for token in tokens[module_index + 2 :]
            if token and not token.startswith("-")
        ]
        focused = next(
            (target for target in targets if TEST_TARGET_RE.match(target)),
            None,
        )
        if focused is not None:
            return {"testScope": "focused", "testIdentity": focused}
        if any(
            target in {"test_feature.py", "test_feature"}
            for target in targets
        ):
            return {"testScope": "full-visible-suite", "testIdentity": None}
    return {"testScope": "unknown", "testIdentity": None}


def classify_unittest_result(
    *,
    exit_code: int | None,
    output: str,
) -> dict[str, Any]:
    ran_match = RAN_TESTS_RE.search(output)
    ran_count = int(ran_match.group(1)) if ran_match else None
    lowered = output.lower()
    import_or_syntax_error = (
        re.search(r"(?im)^ERROR:", output) is not None
        or "syntaxerror" in lowered
        or "importerror" in lowered
        or "modulenotfounderror" in lowered
    )
    if exit_code == 0:
        green = ran_count is not None and ran_count > 0 and "ok" in lowered
        return {
            "failureClass": None if green else "path-or-discovery-error",
            "greenProved": green,
            "ranTestCount": ran_count,
        }
    if import_or_syntax_error:
        return {
            "failureClass": "syntax-or-import-error",
            "greenProved": False,
            "ranTestCount": ran_count,
        }
    if (
        ran_count == 0
        or "no tests" in lowered
        or "file not found" in lowered
        or "no such file" in lowered
        or "failed to import test module" in lowered
    ):
        return {
            "failureClass": "path-or-discovery-error",
            "greenProved": False,
            "ranTestCount": ran_count,
        }
    if (
        "sandbox" in lowered
        or "permission denied" in lowered
        or "access is denied" in lowered
        or "timed out" in lowered
    ):
        return {
            "failureClass": "harness-or-sandbox-error",
            "greenProved": False,
            "ranTestCount": ran_count,
        }
    if "fail:" in lowered and "assertionerror" in lowered:
        return {
            "failureClass": "expected-behavior-assertion",
            "greenProved": False,
            "ranTestCount": ran_count,
        }
    return {
        "failureClass": "unknown",
        "greenProved": False,
        "ranTestCount": ran_count,
    }


def _lifecycle_record(item_id: str) -> dict[str, Any]:
    return {
        "itemId": item_id,
        "started": [],
        "completed": [],
        "outputDeltas": [],
        "patchUpdates": [],
        "terminalInteractions": [],
    }


def normalize_tdd_app_server_event_stream(
    messages: list[dict[str, Any]],
    *,
    thread_id: str,
    turn_id: str,
    trial_root: Path,
) -> dict[str, Any]:
    failures: list[str] = []
    boundary_violations: list[str] = []
    unknown_methods: list[str] = []
    unknown_item_types: list[str] = []
    known_noncausal = Counter()
    raw_envelopes: list[dict[str, Any]] = []
    lifecycles: dict[str, dict[str, Any]] = defaultdict(dict)
    hook_runs: list[dict[str, Any]] = []

    for ordinal, message in enumerate(messages):
        if not isinstance(message, dict):
            failures.append("raw-message-not-object")
            continue
        method = message.get("method")
        if not isinstance(method, str):
            known_noncausal["jsonRpcResponse"] += 1
            continue
        params = _target_params(
            message,
            thread_id=thread_id,
            turn_id=turn_id,
        )
        if params is None:
            continue
        raw = canonical_bytes(message)
        item = params.get("item")
        item_id = (
            item.get("id")
            if isinstance(item, dict)
            else params.get("itemId")
        )
        raw_envelopes.append(
            {
                "receiveOrdinal": ordinal,
                "method": method,
                "itemId": item_id,
                "rawBytes": len(raw),
                "rawSha256": hashlib.sha256(raw).hexdigest(),
            }
        )

        if method in APPROVAL_METHODS:
            boundary_violations.append(f"approval-request:{method}")
            continue
        if method in HOOK_METHODS:
            run = params.get("run")
            if not isinstance(run, dict):
                failures.append("hook-run-shape-invalid")
                continue
            entries = run.get("entries")
            if not isinstance(entries, list):
                entries = []
            entry_kinds = [
                entry.get("kind")
                for entry in entries
                if isinstance(entry, dict)
            ]
            if any(kind != "context" for kind in entry_kinds):
                failures.append("hook-noncontext-entry-observed")
            hook_runs.append(
                {
                    "method": method,
                    "id": run.get("id"),
                    "eventName": run.get("eventName"),
                    "scope": run.get("scope"),
                    "source": run.get("source"),
                    "handlerType": run.get("handlerType"),
                    "executionMode": run.get("executionMode"),
                    "status": run.get("status"),
                    "entryKinds": entry_kinds,
                    "entryTextSha256": [
                        hashlib.sha256(
                            str(entry.get("text", "")).encode("utf-8")
                        ).hexdigest()
                        for entry in entries
                        if isinstance(entry, dict)
                    ],
                }
            )
            known_noncausal[method] += 1
            continue
        if method == "turn/plan/updated":
            if _known_noncausal_plan_update(params):
                known_noncausal[method] += 1
            else:
                unknown_methods.append(method)
            continue
        if method in KNOWN_TURN_METHODS:
            known_noncausal[method] += 1
            continue
        if method not in KNOWN_ITEM_METHODS and not any(
            method.startswith(prefix)
            for prefix in KNOWN_NONCAUSAL_METHOD_PREFIXES
        ):
            unknown_methods.append(method)
            continue
        if any(
            method.startswith(prefix)
            for prefix in KNOWN_NONCAUSAL_METHOD_PREFIXES
        ):
            known_noncausal[method] += 1
            continue
        if not isinstance(item_id, str) or not item_id:
            failures.append("target-item-id-missing")
            continue
        lifecycle = lifecycles.get(item_id)
        if not lifecycle:
            lifecycle = _lifecycle_record(item_id)
            lifecycles[item_id] = lifecycle
        entry = {
            "receiveOrdinal": ordinal,
            "method": method,
            "params": params,
        }
        if method == "item/started":
            lifecycle["started"].append(entry)
        elif method == "item/completed":
            lifecycle["completed"].append(entry)
        elif method == "item/commandExecution/outputDelta":
            lifecycle["outputDeltas"].append(entry)
        elif method == "item/fileChange/patchUpdated":
            lifecycle["patchUpdates"].append(entry)
        elif method == "item/commandExecution/terminalInteraction":
            lifecycle["terminalInteractions"].append(entry)
        elif method == "item/fileChange/outputDelta":
            failures.append("deprecated-file-change-output-delta-observed")

    normalized_events: list[tuple[int, dict[str, Any]]] = []
    lifecycle_summaries: list[dict[str, Any]] = []
    causal_intervals: list[tuple[int, int, str]] = []
    command_diagnostics: list[dict[str, Any]] = []

    for item_id in sorted(lifecycles):
        lifecycle = lifecycles[item_id]
        started = lifecycle["started"]
        completed = lifecycle["completed"]
        if len(started) != 1:
            failures.append(
                "causal-item-start-missing"
                if not started
                else "causal-item-start-duplicate"
            )
        if len(completed) != 1:
            failures.append(
                "causal-item-complete-missing"
                if not completed
                else "causal-item-complete-duplicate"
            )
        start_item = (
            started[0]["params"].get("item")
            if len(started) == 1
            else None
        )
        complete_item = (
            completed[0]["params"].get("item")
            if len(completed) == 1
            else None
        )
        start_type = (
            start_item.get("type") if isinstance(start_item, dict) else None
        )
        complete_type = (
            complete_item.get("type")
            if isinstance(complete_item, dict)
            else None
        )
        item_type = complete_type or start_type
        lifecycle_complete = (
            len(started) == 1
            and len(completed) == 1
            and start_type == complete_type
        )
        if (
            start_type is not None
            and complete_type is not None
            and start_type != complete_type
        ):
            failures.append("causal-item-type-mismatch")
        if item_type in BOUNDARY_ITEM_TYPES:
            boundary_violations.append(f"forbidden-item-type:{item_type}")
        elif item_type in KNOWN_NONCAUSAL_ITEM_TYPES:
            known_noncausal[f"item:{item_type}"] += 1
        elif item_type not in CAUSAL_ITEM_TYPES:
            unknown_item_types.append(str(item_type))

        start_ordinal = (
            started[0]["receiveOrdinal"] if len(started) == 1 else None
        )
        complete_ordinal = (
            completed[0]["receiveOrdinal"] if len(completed) == 1 else None
        )
        if (
            item_type == "fileChange"
            and isinstance(start_ordinal, int)
            and isinstance(complete_ordinal, int)
        ):
            causal_intervals.append(
                (start_ordinal, complete_ordinal, item_id)
            )
        lifecycle_summaries.append(
            {
                "itemId": item_id,
                "type": item_type,
                "startedOrdinal": start_ordinal,
                "completedOrdinal": complete_ordinal,
                "outputDeltaOrdinals": [
                    entry["receiveOrdinal"]
                    for entry in lifecycle["outputDeltas"]
                ],
                "patchUpdateOrdinals": [
                    entry["receiveOrdinal"]
                    for entry in lifecycle["patchUpdates"]
                ],
                "lifecycleComplete": lifecycle_complete,
            }
        )
        if not lifecycle_complete or not isinstance(complete_item, dict):
            continue

        if item_type == "fileChange":
            changes = complete_item.get("changes")
            if not isinstance(changes, list) or not changes:
                failures.append("file-change-shape-invalid")
                continue
            relative_paths: list[str] = []
            for change in changes:
                path_value = (
                    change.get("path")
                    if isinstance(change, dict)
                    else None
                )
                if not isinstance(path_value, str):
                    failures.append("file-change-path-invalid")
                    continue
                relative = _safe_relative_path(path_value, trial_root)
                if relative is None:
                    failures.append("file-change-path-escaped-trial")
                    continue
                relative_paths.append(relative)
            path_set = set(relative_paths)
            if not path_set:
                continue
            if not path_set <= ALLOWED_MUTABLE_FILES:
                boundary_violations.append("out-of-scope-file-change")
            if "feature.py" in path_set and "test_feature.py" in path_set:
                failures.append("mixed-test-and-production-mutation")
                normalized_events.append(
                    (
                        complete_ordinal,
                        {
                            "type": "unknownRawItem",
                            "rawType": "ambiguousMixedMutation",
                            "timelineObservable": False,
                        },
                    )
                )
            else:
                normalized_events.append(
                    (
                        complete_ordinal,
                        {
                            "type": "fileMutation",
                            "paths": sorted(path_set),
                            "timelineObservable": True,
                            "itemId": item_id,
                            "completedOrdinal": complete_ordinal,
                        },
                    )
                )
        elif item_type == "commandExecution":
            command = complete_item.get("command")
            exit_code = complete_item.get("exitCode")
            aggregated = complete_item.get("aggregatedOutput")
            deltas = [
                entry["params"].get("delta")
                for entry in lifecycle["outputDeltas"]
            ]
            if any(not isinstance(delta, str) for delta in deltas):
                failures.append("command-output-delta-shape-invalid")
                deltas = []
            streamed = "".join(deltas)
            if (
                isinstance(aggregated, str)
                and streamed
                and aggregated != streamed
            ):
                failures.append("command-output-conflict")
            output = (
                streamed
                if streamed
                else aggregated
                if isinstance(aggregated, str)
                else ""
            )
            if not isinstance(command, str) or not isinstance(exit_code, int):
                failures.append("command-completion-shape-invalid")
                continue
            invocation = classify_unittest_invocation(command)
            write_capable = command_may_write_files(command)
            if (
                not output
                and (
                    invocation["testScope"]
                    in {"focused", "full-visible-suite"}
                    or write_capable
                )
            ):
                failures.append("command-output-missing")
            result = classify_unittest_result(
                exit_code=exit_code,
                output=output,
            )
            if (
                invocation["testScope"]
                in {"focused", "full-visible-suite"}
                or write_capable
            ) and isinstance(start_ordinal, int):
                causal_intervals.append(
                    (start_ordinal, complete_ordinal, item_id)
                )
            if write_capable:
                failures.append("opaque-write-command")
            if (
                invocation["testScope"] == "focused"
                and exit_code == 0
                and not result["greenProved"]
            ):
                failures.append("focused-green-not-proved")
            event = {
                "type": "commandExecution",
                "focusedTestCommand": invocation["testScope"] == "focused",
                "fullVisibleSuiteCommand": (
                    invocation["testScope"] == "full-visible-suite"
                ),
                "testScope": invocation["testScope"],
                "testIdentity": invocation["testIdentity"],
                "exitCode": exit_code,
                "failureClass": result["failureClass"],
                "greenProved": result["greenProved"],
                "ranTestCount": result["ranTestCount"],
                "timelineObservable": True,
                "itemId": item_id,
                "startedOrdinal": start_ordinal,
                "completedOrdinal": complete_ordinal,
                "commandSha256": hashlib.sha256(
                    command.encode("utf-8")
                ).hexdigest(),
                "outputSha256": hashlib.sha256(
                    output.encode("utf-8")
                ).hexdigest(),
            }
            command_diagnostics.append(event)
            normalized_events.append((complete_ordinal, event))

    causal_intervals.sort()
    for index, (start, end, item_id) in enumerate(causal_intervals):
        if end < start:
            failures.append("causal-item-completed-before-started")
        for other_start, other_end, other_id in causal_intervals[index + 1 :]:
            if other_start > end:
                break
            if other_start < end and start < other_end:
                failures.append(
                    f"causal-item-lifecycle-overlap:{item_id}:{other_id}"
                )

    red_commands = [
        item
        for item in command_diagnostics
        if item["focusedTestCommand"]
        and item["exitCode"] != 0
        and item["failureClass"] == "expected-behavior-assertion"
    ]
    green_commands = [
        item
        for item in command_diagnostics
        if item["focusedTestCommand"] and item["greenProved"]
    ]
    identity_match: bool | None = None
    if red_commands and green_commands:
        identity_match = (
            red_commands[0]["testIdentity"]
            == green_commands[-1]["testIdentity"]
        )
        if not identity_match:
            failures.append("red-green-test-identity-mismatch")

    for method in unknown_methods:
        failures.append(f"unknown-target-turn-method:{method}")
    for item_type in unknown_item_types:
        failures.append(f"unknown-target-turn-item-type:{item_type}")
    for violation in boundary_violations:
        failures.append(f"boundary-violation:{violation}")
    failures = _dedupe(failures)

    normalized_events.sort(key=lambda row: row[0])
    events = [event for _, event in normalized_events]
    if failures:
        for event in events:
            event["timelineObservable"] = False
    return {
        "normalizerContractVersion": NORMALIZER_CONTRACT_VERSION,
        "status": (
            "normalized-observable"
            if not failures
            else "normalization-incomplete-or-boundary-failed"
        ),
        "timelineObservable": not failures,
        "failureCodes": failures,
        "events": events,
        "rawEnvelopeCount": len(raw_envelopes),
        "rawEventStreamSha256": canonical_sha256(raw_envelopes),
        "rawEnvelopes": raw_envelopes,
        "itemLifecycles": lifecycle_summaries,
        "knownNonCausalCounts": dict(sorted(known_noncausal.items())),
        "hookRuns": hook_runs,
        "boundaryViolations": _dedupe(boundary_violations),
        "unknownMethods": sorted(set(unknown_methods)),
        "unknownItemTypes": sorted(set(unknown_item_types)),
        "redGreenIdentityMatched": identity_match,
        "focusedGreenObserved": bool(green_commands),
        "fullVisibleSuiteGreenObserved": any(
            item["fullVisibleSuiteCommand"] and item["greenProved"]
            for item in command_diagnostics
        ),
        "provesNoUnobservedTransientWrite": False,
        "provesCrossHostSchemaStability": False,
    }


def main() -> int:
    raise SystemExit(
        "library-only normalizer; use the repository pilot or unit fixtures"
    )


if __name__ == "__main__":
    main()
