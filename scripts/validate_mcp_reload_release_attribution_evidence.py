#!/usr/bin/env python3
"""Validate and recompute the MCP reload-release attribution evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

try:
    from .probe_codex_app_server_mcp_reload_release_attribution import (
        PROBE_ID,
        classify_reload_window,
        status_reports_callable_sentinel_tools,
    )
except ImportError:  # pragma: no cover - direct script execution
    from probe_codex_app_server_mcp_reload_release_attribution import (
        PROBE_ID,
        classify_reload_window,
        status_reports_callable_sentinel_tools,
    )


ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_PATH = (
    "registry/mcp-app-server-0.145.0-reload-release-attribution-"
    "evidence-2026-07-27.json"
)
DOC_PATH = (
    "docs/mcp-app-server-0.145.0-reload-release-attribution-"
    "evidence-2026-07-27.md"
)
PROGRAM_ACCEPTANCE_PATH = "registry/program-acceptance-map.json"
PROGRAM_EVIDENCE_ID = (
    "evidence.mcp-app-server-reload-release-attribution-2026-07-27"
)
PROGRAM_ACCEPTANCE_ID = "acceptance.dynamic-runtime-control-gap-research"
EXPECTED_FORMAL_PATHS = [
    (
        "audits/mcp-reload-release-attribution-0.145.0-2026-07-27/"
        f"evidence-{index:02d}.json"
    )
    for index in range(1, 4)
]
EXPECTED_EXCLUDED_PATHS = [
    "audits/mcp-reload-release-attribution-0.145.0-2026-07-27/run-01.json",
    *[
        (
            "audits/mcp-reload-release-attribution-0.145.0-2026-07-27/"
            f"formal-{index:02d}.json"
        )
        for index in range(1, 4)
    ],
]


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_bound_json(
    root: Path, item: dict[str, Any], label: str
) -> dict[str, Any]:
    path_value = item.get("path")
    _require(isinstance(path_value, str), f"{label} path is invalid")
    path = root / path_value
    _require(path.is_file(), f"{label} is missing: {path}")
    _require(
        _sha256(path) == item.get("sha256"),
        f"{label} hash drifted: {path}",
    )
    document = json.loads(path.read_text(encoding="utf-8"))
    _require(isinstance(document, dict), f"{label} is not an object")
    return document


def _recompute_raw(raw: dict[str, Any]) -> dict[str, Any]:
    calls = raw.get("toolCalls")
    process = raw.get("processObservation")
    reload_observation = raw.get("reloadObservation")
    configuration = raw.get("configuration")
    _require(
        isinstance(calls, dict)
        and isinstance(process, dict)
        and isinstance(reload_observation, dict)
        and isinstance(configuration, dict),
        "Formal raw report omitted required surfaces",
    )
    baseline_call = calls.get("baseline")
    post_window_call = calls.get("postWindowSameThread")
    baseline_process = process.get("baseline")
    samples = process.get("samples")
    stop_events = process.get("stopEventsInAttributionWindow")
    _require(
        isinstance(baseline_call, dict)
        and isinstance(post_window_call, dict)
        and isinstance(baseline_process, dict)
        and isinstance(samples, list)
        and all(isinstance(item, dict) for item in samples)
        and isinstance(stop_events, list)
        and all(isinstance(item, dict) for item in stop_events),
        "Formal raw process or call surface is invalid",
    )
    baseline_instance = baseline_call.get("instanceId")
    baseline_pid = baseline_call.get("pid")
    _require(
        isinstance(baseline_instance, str)
        and isinstance(baseline_pid, int),
        "Formal raw baseline identity is invalid",
    )
    return classify_reload_window(
        baseline_instance_id=baseline_instance,
        baseline_pid=baseline_pid,
        baseline_process=baseline_process,
        process_samples=samples,
        stop_events=stop_events,
        post_window_call=post_window_call,
        app_server_alive_through_window=(
            process.get("appServerAliveThroughWindow") is True
        ),
        attribution_actions=reload_observation.get(
            "attributionWindowActions"
        ),
        config_restored_exactly=(
            configuration.get("restoredBytesEqualBefore") is True
        ),
    )


def validate_evidence(
    document: dict[str, Any],
    *,
    root: Path = ROOT,
    program_map: dict[str, Any] | None = None,
) -> None:
    _require(
        document.get("schema") == 1
        and document.get("id")
        == (
            "mcp-app-server-0.145.0-reload-release-attribution-"
            "evidence-2026-07-27"
        )
        and document.get("date") == "2026-07-27"
        and document.get("status")
        == (
            "observed-three-repetition-single-host-loaded-runtime-retained-"
            "after-reload-with-status-runtime-divergence"
        ),
        "Reload-release evidence identity drifted",
    )
    host = document.get("hostBinding")
    _require(
        isinstance(host, dict)
        and host.get("codexVersion") == "codex-cli 0.145.0"
        and host.get("probeId") == PROBE_ID
        and host.get("observationSecondsPerRepetition") == 5.0
        and host.get("sampleIntervalSeconds") == 0.5
        and host.get("formalRepetitionCount") == 3,
        "Reload-release host binding drifted",
    )
    probe_binding = host.get("probeScript")
    sentinel_binding = host.get("sentinel")
    for binding, label in (
        (probe_binding, "probe"),
        (sentinel_binding, "Sentinel"),
    ):
        _require(isinstance(binding, dict), f"{label} binding is invalid")
        path = root / str(binding.get("path"))
        _require(
            path.is_file() and _sha256(path) == binding.get("sha256"),
            f"{label} binding drifted",
        )

    attribution = document.get("attributionWindow")
    _require(
        isinstance(attribution, dict)
        and attribution.get("allowedActions")
        == [
            "config-write-disabled",
            "config/mcpServer/reload",
            "mcpServerStatus/list",
            "read-only-process-and-event-sampling",
        ]
        and all(
            attribution.get(key) is False
            for key in (
                "newThreadDuringWindow",
                "unsubscribeDuringWindow",
                "appServerTeardownDuringWindow",
                "harnessCleanupDuringWindow",
                "pidSignalDuringWindow",
                "reloadEmptyObjectTreatedAsCompletedActuation",
            )
        ),
        "Reload attribution boundary drifted",
    )

    excluded = document.get("excludedCalibrationRuns")
    _require(
        isinstance(excluded, list)
        and [item.get("path") for item in excluded]
        == EXPECTED_EXCLUDED_PATHS,
        "Excluded calibration set drifted",
    )
    excluded_raw = [
        _load_bound_json(root, item, "Excluded calibration") for item in excluded
    ]
    _require(
        excluded_raw[0]
        .get("toolCalls", {})
        .get("baseline", {})
        .get("arguments", {})
        .get("probe")
        != PROBE_ID,
        "First calibration no longer demonstrates the request-id defect",
    )
    _require(
        all("hostBinding" not in raw for raw in excluded_raw[1:]),
        "Pre-self-binding calibrations are no longer distinguishable",
    )

    formal = document.get("formalEvidence")
    _require(
        isinstance(formal, list)
        and [item.get("path") for item in formal] == EXPECTED_FORMAL_PATHS,
        "Formal reload-release evidence set drifted",
    )
    raw_reports = [
        _load_bound_json(root, item, "Formal reload-release evidence")
        for item in formal
    ]
    probe_hash = probe_binding["sha256"]
    sentinel_hash = sentinel_binding["sha256"]
    pids: set[int] = set()
    instances: set[str] = set()
    threads: set[str] = set()
    homes: set[str] = set()
    total_samples = 0
    for index, (binding, raw) in enumerate(
        zip(formal, raw_reports, strict=True),
        start=1,
    ):
        _require(
            raw.get("schema") == 1
            and raw.get("id") == PROBE_ID,
            f"Formal repetition {index} identity drifted",
        )
        raw_host = raw.get("hostBinding")
        _require(
            isinstance(raw_host, dict)
            and raw_host.get("codexVersion") == host["codexVersion"]
            and raw_host.get("probeScriptSha256") == probe_hash
            and raw_host.get("sentinelScriptSha256") == sentinel_hash,
            f"Formal repetition {index} self-binding drifted",
        )
        recomputed = _recompute_raw(raw)
        recorded = raw.get("classification")
        _require(
            isinstance(recorded, dict)
            and all(
                recorded.get(key) == recomputed.get(key)
                for key in (
                    "classification",
                    "valid",
                    "invalidReasons",
                    "reloadReleaseObserved",
                    "loadedRuntimeRetained",
                    "sameIdentityBySample",
                    "finalSameProcessIdentity",
                    "postWindowCallSameInstance",
                )
            )
            and recomputed["classification"]
            == "loaded-runtime-retained-after-reload",
            f"Formal repetition {index} classification drifted",
        )
        status = raw.get("statusAfterDisableReload")
        _require(
            isinstance(status, dict)
            and status.get("sentinelPresent") is True
            and not status_reports_callable_sentinel_tools(status)
            and recorded.get("statusRuntimeDivergenceReproduced") is True,
            f"Formal repetition {index} status/runtime boundary drifted",
        )
        calls = raw["toolCalls"]
        baseline = calls["baseline"]
        post = calls["postWindowSameThread"]
        recovery = calls["restoredNewThreadControl"]
        _require(
            baseline.get("arguments", {}).get("probe") == PROBE_ID
            and post.get("arguments", {}).get("probe") == PROBE_ID
            and recovery.get("arguments", {}).get("probe") == PROBE_ID
            and recovery.get("succeeded") is True,
            f"Formal repetition {index} request identity or control drifted",
        )
        process = raw["processObservation"]
        cleanup = process.get("cleanup")
        isolation = raw.get("isolation")
        claims = raw.get("claimBoundary")
        _require(
            len(process["samples"]) == 11
            and process.get("stopEventsInAttributionWindow") == []
            and process.get("appServerAliveThroughWindow") is True
            and process.get("appServerReturnCode") == 0
            and process.get("appServerKillSent") is False
            and isinstance(cleanup, dict)
            and cleanup.get("cleanupVerified") is True
            and cleanup.get("pidSignalCleanupUsed") is False
            and isinstance(isolation, dict)
            and isolation.get("applicationLogExternalNetworkAttemptObserved")
            is True
            and isolation.get("authStateProduced") is False
            and isinstance(claims, dict)
            and claims.get("modelTurnStarted") is False
            and claims.get("modelRequestSent") is False
            and claims.get("provesNoNetworkTraffic") is False,
            f"Formal repetition {index} isolation or lifecycle drifted",
        )
        pid = baseline.get("pid")
        instance = baseline.get("instanceId")
        thread_id = raw.get("threads", {}).get("a", {}).get("id")
        home = isolation.get("codexHome")
        _require(
            pid == binding.get("baselinePid")
            and instance == binding.get("baselineInstanceId")
            and thread_id == binding.get("threadId")
            and isinstance(pid, int)
            and isinstance(instance, str)
            and isinstance(thread_id, str)
            and isinstance(home, str),
            f"Formal repetition {index} evidence binding drifted",
        )
        pids.add(pid)
        instances.add(instance)
        threads.add(thread_id)
        homes.add(home)
        total_samples += len(process["samples"])

    _require(
        len(pids) == len(instances) == len(threads) == len(homes) == 3,
        "Formal repetitions are not independently isolated",
    )
    aggregate = document.get("aggregateObservation")
    _require(
        isinstance(aggregate, dict)
        and aggregate
        == {
            "validRepetitionCount": 3,
            "loadedRuntimeRetainedClassificationCount": 3,
            "reloadReleaseObservedCount": 0,
            "statusRuntimeDivergenceCount": 3,
            "exactProcessIdentitySampleCount": total_samples,
            "sameIdentitySampleCount": total_samples,
            "attributionWindowStopEventCount": 0,
            "postWindowSameThreadSameInstanceCount": 3,
            "exactConfigRestoreCount": 3,
            "restoredNewThreadControlSuccessCount": 3,
            "gracefulAppServerShutdownCount": 3,
            "verifiedCleanupCount": 3,
            "applicationLogExternalNetworkAttemptCount": 3,
        },
        "Reload-release aggregate drifted",
    )
    decision = document.get("decision")
    claims = document.get("claimBoundary")
    _require(
        isinstance(decision, dict)
        and decision.get("reloadRequestAcceptanceObserved") is True
        and decision.get("loadedRuntimeRetainedForFiveSecondWindowObserved")
        is True
        and decision.get("reloadCausedPriorRuntimeReleaseInTestedWindow")
        is False
        and decision.get(
            "statusProjectionAndLoadedRuntimeDivergenceReproduced"
        )
        is True
        and decision.get(
            "nativeReloadIsNotATestedImmediateReleaseMechanismForAlreadyLoadedRuntime"
        )
        is True
        and decision.get("dynamicRuntimeControlAssessment") == "partial"
        and decision.get("residualSelfAuthoredControllerGapProved") is False,
        "Reload-release decision drifted",
    )
    _require(
        isinstance(claims, dict)
        and claims
        == {
            "taskEndImmediateReleaseProved": False,
            "sameThreadHotEnableDisableForArbitraryMcpProved": False,
            "leaseOrReferenceCountProved": False,
            "stableResourceSavingsProved": False,
            "genericCrashRecoveryProved": False,
            "crossHostParityProved": False,
            "crossVersionParityProved": False,
            "noNetworkTrafficProved": False,
            "residualNeedForSelfAuthoredControllerProved": False,
            "productionReadinessProved": False,
        },
        "Reload-release claim boundary drifted",
    )
    cleanup = document.get("cleanupDisposition")
    _require(
        isinstance(cleanup, dict)
        and cleanup.get("repositoryAudit")
        == "retain-authoritative-host-evidence"
        and cleanup.get("deletionAuthorized") is False,
        "Reload-release cleanup boundary drifted",
    )
    _require((root / DOC_PATH).is_file(), "Reload-release documentation is missing")

    if program_map is None:
        program_map = json.loads(
            (root / PROGRAM_ACCEPTANCE_PATH).read_text(encoding="utf-8")
        )
    _require(
        isinstance(program_map, dict),
        "Program acceptance map is invalid",
    )
    acceptances = program_map.get("acceptanceCriteria")
    evidence_items = program_map.get("evidence")
    _require(
        isinstance(acceptances, list)
        and all(isinstance(item, dict) for item in acceptances)
        and isinstance(evidence_items, list)
        and all(isinstance(item, dict) for item in evidence_items),
        "Program acceptance map surfaces are invalid",
    )
    matching_acceptances = [
        item
        for item in acceptances
        if item.get("id") == PROGRAM_ACCEPTANCE_ID
    ]
    matching_evidence = [
        item
        for item in evidence_items
        if item.get("id") == PROGRAM_EVIDENCE_ID
    ]
    _require(
        len(matching_acceptances) == 1
        and matching_acceptances[0].get("assessment") == "partial"
        and PROGRAM_EVIDENCE_ID
        in matching_acceptances[0].get("evidenceIds", []),
        "Reload-release acceptance mapping drifted",
    )
    _require(
        matching_evidence
        == [
            {
                "id": PROGRAM_EVIDENCE_ID,
                "path": EVIDENCE_PATH,
                "kind": (
                    "observed-three-repetition-single-host-reload-retained-"
                    "loaded-runtime-status-runtime-divergence-no-model-turn"
                ),
                "asOf": "2026-07-27",
                "supports": [PROGRAM_ACCEPTANCE_ID],
            }
        ],
        "Reload-release program evidence mapping drifted",
    )
    acceptance_references = {
        item["id"]
        for item in acceptances
        if PROGRAM_EVIDENCE_ID in item.get("evidenceIds", [])
    }
    _require(
        acceptance_references == {PROGRAM_ACCEPTANCE_ID},
        "Reload-release evidence has an unauthorized acceptance reference",
    )
    normalized_doc = " ".join(
        (root / DOC_PATH).read_text(encoding="utf-8").split()
    )
    for phrase in (
        "already-loaded Sentinel",
        "tested five-second reload window",
        "task-end release",
        "residual need for a self-authored controller",
    ):
        _require(
            phrase in normalized_doc,
            f"Reload-release documentation boundary missing: {phrase}",
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    arguments = parser.parse_args()
    root = arguments.root.resolve()
    document = json.loads((root / EVIDENCE_PATH).read_text(encoding="utf-8"))
    validate_evidence(document, root=root)
    print("MCP reload-release attribution evidence passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
