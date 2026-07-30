#!/usr/bin/env python3
"""Build and score the offline new-feature TDD fixture boundary."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Callable

try:
    from .build_source_pinned_skill_projection import (
        candidate_by_id,
        materialize_candidate,
    )
except ImportError:
    from build_source_pinned_skill_projection import (
        candidate_by_id,
        materialize_candidate,
    )


ROOT = Path(__file__).resolve().parent.parent
FIXTURE_PATH = (
    ROOT
    / "tests"
    / "fixtures"
    / "human-ai-collaboration-tdd-timeline-fixtures-2026-07-26.json"
)
PROTOCOL_PATH = (
    ROOT
    / "registry"
    / "human-ai-collaboration-new-feature-tdd-protocol-2026-07-26.json"
)
ALLOWED_ARMS = {
    "SE-TDD-NATIVE-SPARK",
    "SE-TDD-MATT-CURRENT",
    "SE-TDD-SUPERPOWERS-6.2.0",
}
ALLOWED_MUTABLE_FILES = (
    "feature.py",
    "test_feature.py",
    "PROCESS_EVIDENCE.json",
)
TREATMENT_CANDIDATES = {
    "SE-TDD-MATT-CURRENT": "tdd.matt.current",
    "SE-TDD-SUPERPOWERS-6.2.0": "tdd.superpowers.6.2.0",
}
INITIAL_FEATURE = '''"""Capped backoff public seam used by the TDD fixture."""


def capped_backoff_delay(attempt, schedule):
    """Return the one-indexed delay, capped at the final schedule entry."""
    return None
'''
INITIAL_PROCESS_EVIDENCE = {
    "schema": 1,
    "status": "not-evaluated",
    "cycles": [],
    "claimBoundaryAcknowledged": False,
}
TASK_PROMPT = """Implement capped_backoff_delay(attempt, schedule) in feature.py.

The public seam is already agreed: call only this module-level function.
`attempt` must be a positive integer, excluding bool. `schedule` must be a
non-empty list or tuple of positive integers, excluding bool entries. Invalid
input raises ValueError. Return the one-indexed schedule entry and cap attempts
beyond the schedule length at the final entry.

Work test-first through the public seam. Add focused unittest tests in
test_feature.py. Run a focused test and observe an assertion failure caused by
the missing behavior before changing feature.py, then make it green and run
the complete test file. Use independent literal expected values; do not mock,
install dependencies, use network access, mutate Git/configuration, or touch
files other than feature.py, test_feature.py, and PROCESS_EVIDENCE.json.
PROCESS_EVIDENCE.json is an Agent declaration only; the parent timeline is
authoritative. Do not claim production readiness, Skill causation, or
candidate superiority."""

PRIVATE_ORACLE = {
    "functionalCases": [
        {"attempt": 1, "schedule": [3, 7, 15], "expected": 3},
        {"attempt": 2, "schedule": [3, 7, 15], "expected": 7},
        {"attempt": 3, "schedule": [3, 7, 15], "expected": 15},
        {"attempt": 8, "schedule": [3, 7, 15], "expected": 15},
    ],
    "invalidCases": [
        {"attempt": 0, "schedule": [3]},
        {"attempt": True, "schedule": [3]},
        {"attempt": 1.5, "schedule": [3]},
        {"attempt": 1, "schedule": []},
        {"attempt": 1, "schedule": "3,7"},
        {"attempt": 1, "schedule": [0, 3]},
        {"attempt": 1, "schedule": [True, 3]},
    ],
    "mutants": [
        "off-by-one-attempt-index",
        "no-cap-after-final-entry",
        "bool-attempt-accepted",
        "empty-schedule-accepted",
        "nonpositive-delay-accepted",
        "string-schedule-accepted",
        "bool-delay-accepted",
    ],
}


def canonical_sha256(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def file_observation(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"exists": False, "bytes": None, "sha256": None}
    payload = path.read_bytes()
    return {
        "exists": True,
        "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def snapshot_trial_tree(root: Path) -> dict[str, Any]:
    files: dict[str, dict[str, Any]] = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise RuntimeError("TDD trial tree must not contain symlinks")
        if path.is_file():
            relative = path.relative_to(root).as_posix()
            files[relative] = file_observation(path)
    return {
        "fileCount": len(files),
        "files": files,
        "treeSha256": canonical_sha256(files),
    }


def build_packet(
    output: Path,
    arm: str,
    *,
    project_root: Path = ROOT,
) -> dict[str, Any]:
    if arm not in ALLOWED_ARMS:
        raise ValueError(f"unsupported TDD trial arm: {arm}")
    output = output.resolve()
    if output.exists():
        if not output.is_dir() or any(output.iterdir()):
            raise RuntimeError("TDD trial output must be an empty directory")
    else:
        output.mkdir(parents=True)
    source_agents = (project_root / "AGENTS.md").resolve()
    if not source_agents.is_file():
        raise RuntimeError("project AGENTS.md is missing")
    task = {
        "schema": 1,
        "packetId": f"new-feature-tdd-v1:{arm}",
        "scenarioId": "SE-IMPLEMENT-REVIEW-01",
        "sliceId": "SE-IMPLEMENT-TDD-NEW-FEATURE-01",
        "armId": arm,
        "requestedModel": "gpt-5.3-codex-spark",
        "requestedReasoningEffort": "low",
        "providerFallbackAllowed": False,
        "taskPrompt": TASK_PROMPT,
        "preAgreedPublicSeam": "feature.capped_backoff_delay",
        "allowedMutableFiles": list(ALLOWED_MUTABLE_FILES),
        "visibleTestCommand": [
            "python",
            "-B",
            "-m",
            "unittest",
            "-v",
            "test_feature.py",
        ],
        "networkAllowed": False,
        "dependencyChangeAllowed": False,
        "gitMutationAllowed": False,
        "externalWriteAllowed": False,
        "executionSandbox": "workspaceWrite",
        "privateOracleContentWrittenIntoTrial": False,
    }
    (output / "AGENTS.md").write_bytes(source_agents.read_bytes())
    (output / "TASK.json").write_text(
        json.dumps(task, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (output / "feature.py").write_text(INITIAL_FEATURE, encoding="utf-8")
    (output / "PROCESS_EVIDENCE.json").write_text(
        json.dumps(INITIAL_PROCESS_EVIDENCE, ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )
    baseline = {
        name: file_observation(output / name)
        for name in (
            "AGENTS.md",
            "TASK.json",
            "feature.py",
            "test_feature.py",
            "PROCESS_EVIDENCE.json",
        )
    }
    return {
        "schema": 1,
        "id": f"new-feature-tdd-trial-build:{arm}",
        "status": "prepared-no-agent-run",
        "output": output.as_posix(),
        "armId": arm,
        "taskSha256": canonical_sha256(task),
        "privateOracle": {
            "version": "capped-backoff-hidden-oracle-v1",
            "sha256": canonical_sha256(PRIVATE_ORACLE),
            "contentWrittenIntoTrial": False,
        },
        "preAgreedPublicSeam": "feature.capped_backoff_delay",
        "baseline": baseline,
        "preProjectionTree": snapshot_trial_tree(output),
        "treatmentProjectionMaterialized": False,
        "liveExecutionStarted": False,
    }


def materialize_treatment_projection(
    output: Path,
    arm: str,
    *,
    superpowers_package_root: Path | None = None,
    github_reader: Callable[[str, str, str], bytes] | None = None,
) -> dict[str, Any]:
    candidate_id = TREATMENT_CANDIDATES.get(arm)
    if candidate_id is None:
        raise ValueError(f"arm has no candidate projection: {arm}")
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    candidate = candidate_by_id(protocol, candidate_id)
    return materialize_candidate(
        candidate,
        output,
        superpowers_package_root=superpowers_package_root,
        allow_existing=True,
        github_reader=github_reader,
    )


def build_trial_package(
    output: Path,
    arm: str,
    *,
    materialize_treatment: bool = False,
    project_root: Path = ROOT,
    superpowers_package_root: Path | None = None,
    projection_builder: Callable[..., dict[str, Any]] = (
        materialize_treatment_projection
    ),
) -> dict[str, Any]:
    build = build_packet(output, arm, project_root=project_root)
    projection = None
    if materialize_treatment:
        projection = projection_builder(
            output,
            arm,
            superpowers_package_root=superpowers_package_root,
        )
    build["treatmentProjectionMaterialized"] = projection is not None
    build["postProjectionTree"] = snapshot_trial_tree(output)
    return {"build": build, "projection": projection}


def evaluate_tdd_timeline(events: list[dict[str, Any]]) -> dict[str, Any]:
    failures: list[str] = []
    allowed_types = {"fileMutation", "commandExecution"}
    unknown = sorted(
        {
            str(event.get("type"))
            for event in events
            if event.get("type") not in allowed_types
        }
    )
    if unknown:
        failures.append("unknown-normalized-event")

    mutation_events: list[tuple[int, set[str]]] = []
    commands: list[tuple[int, dict[str, Any]]] = []
    for index, event in enumerate(events):
        if event.get("type") == "fileMutation":
            paths = event.get("paths")
            if (
                not isinstance(paths, list)
                or any(not isinstance(path, str) for path in paths)
            ):
                failures.append("mutation-path-shape-invalid")
                continue
            mutation_events.append((index, set(paths)))
            if not set(paths) <= set(ALLOWED_MUTABLE_FILES):
                failures.append("out-of-scope-mutation")
        elif event.get("type") == "commandExecution":
            commands.append((index, event))

    test_mutation_indices = [
        index
        for index, paths in mutation_events
        if "test_feature.py" in paths
    ]
    production_mutation_indices = [
        index
        for index, paths in mutation_events
        if "feature.py" in paths
    ]
    first_production = (
        min(production_mutation_indices)
        if production_mutation_indices
        else None
    )
    if not test_mutation_indices:
        failures.append("test-mutation-not-observed")
    if first_production is None:
        failures.append("production-mutation-not-observed")

    focused_test_commands = [
        (index, event)
        for index, event in commands
        if event.get("focusedTestCommand") is True
    ]
    valid_reds = [
        (index, event)
        for index, event in focused_test_commands
        if isinstance(event.get("exitCode"), int)
        and event["exitCode"] != 0
        and event.get("failureClass") == "expected-behavior-assertion"
        and any(test_index < index for test_index in test_mutation_indices)
        and (first_production is None or index < first_production)
    ]
    if not valid_reds:
        failures.append("valid-red-before-production-not-observed")

    wrong_reds = [
        event
        for index, event in focused_test_commands
        if isinstance(event.get("exitCode"), int)
        and event["exitCode"] != 0
        and event.get("failureClass") != "expected-behavior-assertion"
        and (first_production is None or index < first_production)
    ]
    if wrong_reds and not valid_reds:
        failures.append("only-wrong-error-red-observed")

    preproduction_green = any(
        event.get("exitCode") == 0
        and (first_production is None or index < first_production)
        for index, event in focused_test_commands
    )
    if preproduction_green:
        failures.append("test-green-before-production")

    final_greens = [
        (index, event)
        for index, event in focused_test_commands
        if event.get("exitCode") == 0
        and first_production is not None
        and index > first_production
    ]
    if not final_greens:
        failures.append("green-after-production-not-observed")

    if any(
        event.get("timelineObservable") is not True
        for event in events
    ):
        failures.append("timeline-observability-incomplete")
    failures = list(dict.fromkeys(failures))
    return {
        "status": (
            "accepted-offline-tdd-timeline"
            if not failures
            else "rejected-offline-tdd-timeline"
        ),
        "failureCodes": failures,
        "eventCount": len(events),
        "validRedCount": len(valid_reds),
        "finalGreenCount": len(final_greens),
        "firstProductionMutationIndex": first_production,
        "unknownNormalizedEventTypes": unknown,
    }


def evaluate_fixture_document(document: dict[str, Any]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for case in document.get("cases", []):
        actual = evaluate_tdd_timeline(case["events"])
        results.append(
            {
                "id": case["id"],
                "expectedStatus": case["expectedStatus"],
                "actualStatus": actual["status"],
                "failureCodes": actual["failureCodes"],
            }
        )
    return results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    parser.add_argument("--arm", choices=sorted(ALLOWED_ARMS))
    parser.add_argument("--evaluate-fixtures", action="store_true")
    parser.add_argument("--materialize-treatment", action="store_true")
    parser.add_argument("--superpowers-package-root", type=Path)
    arguments = parser.parse_args()
    if arguments.evaluate_fixtures:
        fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        results = evaluate_fixture_document(fixture)
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return 0 if all(
            row["actualStatus"] == row["expectedStatus"] for row in results
        ) else 1
    if arguments.output is None or arguments.arm is None:
        parser.error("--output and --arm are required unless evaluating fixtures")
    result = build_trial_package(
        arguments.output,
        arguments.arm,
        materialize_treatment=arguments.materialize_treatment,
        superpowers_package_root=arguments.superpowers_package_root,
    )
    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
