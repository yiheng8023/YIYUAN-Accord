#!/usr/bin/env python3
"""Validate and recompute paired MCP thread-unsubscribe release evidence."""

from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
from typing import Any

try:
    from .probe_codex_app_server_mcp_idle_unload import (
        process_identity_complete,
        same_process_identity,
    )
    from .probe_codex_app_server_mcp_reload_release_attribution import (
        stop_events_in_window,
    )
    from .probe_codex_app_server_mcp_thread_unsubscribe_release_attribution import (
        ARM_CONTROL,
        ARM_NAMES,
        ARM_UNSUBSCRIBE,
        MAX_ACTION_SKEW_MILLISECONDS,
        MINIMAL_ENVIRONMENT_KEYS,
        PROBE_ID,
        classify_arm,
        classify_pair,
    )
except ImportError:  # pragma: no cover - direct script execution
    from probe_codex_app_server_mcp_idle_unload import (
        process_identity_complete,
        same_process_identity,
    )
    from probe_codex_app_server_mcp_reload_release_attribution import (
        stop_events_in_window,
    )
    from probe_codex_app_server_mcp_thread_unsubscribe_release_attribution import (
        ARM_CONTROL,
        ARM_NAMES,
        ARM_UNSUBSCRIBE,
        MAX_ACTION_SKEW_MILLISECONDS,
        MINIMAL_ENVIRONMENT_KEYS,
        PROBE_ID,
        classify_arm,
        classify_pair,
    )


ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_PATH = (
    "registry/mcp-app-server-0.145.0-thread-unsubscribe-release-"
    "attribution-evidence-2026-07-27.json"
)
DOC_PATH = (
    "docs/mcp-app-server-0.145.0-thread-unsubscribe-release-"
    "attribution-evidence-2026-07-27.md"
)
AUDIT_README_PATH = (
    "audits/mcp-thread-unsubscribe-release-attribution-0.145.0-"
    "2026-07-27/README.md"
)
DIRECT_EVIDENCE_PATH = (
    "registry/mcp-app-server-0.145.0-direct-tool-call-evidence-"
    "2026-07-23.json"
)
PROGRAM_ACCEPTANCE_PATH = "registry/program-acceptance-map.json"
PROGRAM_EVIDENCE_ID = (
    "evidence.mcp-app-server-thread-unsubscribe-release-attribution-"
    "2026-07-27"
)
PROGRAM_ACCEPTANCE_ID = "acceptance.dynamic-runtime-control-gap-research"
EXPECTED_CALIBRATION_PATH = (
    "audits/mcp-thread-unsubscribe-release-attribution-0.145.0-"
    "2026-07-27/calibration-01.json"
)
EXPECTED_FORMAL_PATHS = [
    (
        "audits/mcp-thread-unsubscribe-release-attribution-0.145.0-"
        f"2026-07-27/evidence-{index:02d}.json"
    )
    for index in range(1, 4)
]
EXPECTED_REQUEST_METHODS = {
    ARM_CONTROL: [
        "initialize",
        "initialized",
        "thread/start",
        "mcpServer/tool/call",
        "mcpServer/tool/call",
        "thread/unsubscribe",
    ],
    ARM_UNSUBSCRIBE: [
        "initialize",
        "initialized",
        "thread/start",
        "mcpServer/tool/call",
        "thread/unsubscribe",
        "mcpServer/tool/call",
    ],
}
EXPECTED_SCHEMA_BINDINGS = [
    {
        "path": (
            "C:/tmp/codex-app-server-schema-0.145.0-20260723/"
            "ClientRequest.json"
        ),
        "sha256": (
            "F3171526A137767AA9350838F441D79E2DC294EFECD32FAF7932B3B08D223136"
        ),
    },
    {
        "path": (
            "C:/tmp/codex-app-server-schema-0.145.0-20260723/v2/"
            "ThreadUnsubscribeParams.json"
        ),
        "sha256": (
            "A03DC3D6C5A2F77F164B6BF4250D29F0C81C10C6B5F484FAC0B05392DC9C936A"
        ),
    },
    {
        "path": (
            "C:/tmp/codex-app-server-schema-0.145.0-20260723/v2/"
            "ThreadUnsubscribeResponse.json"
        ),
        "sha256": (
            "14CD8BAAC4521C8101698DE3DF2D7A8E509ECE6BF9B8B5D11162D9391064B4AE"
        ),
    },
]


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_bound_json(
    root: Path,
    item: dict[str, Any],
    label: str,
) -> dict[str, Any]:
    path_value = item.get("path")
    _require(isinstance(path_value, str), f"{label} path is invalid")
    path = root / path_value
    _require(path.is_file(), f"{label} is missing: {path}")
    _require(
        _sha256(path).upper() == str(item.get("sha256", "")).upper(),
        f"{label} hash drifted: {path}",
    )
    document = json.loads(path.read_text(encoding="utf-8"))
    _require(isinstance(document, dict), f"{label} is not an object")
    return document


def _load_program_map(
    root: Path,
    program_map: dict[str, Any] | None,
) -> dict[str, Any]:
    if program_map is not None:
        return program_map
    document = json.loads(
        (root / PROGRAM_ACCEPTANCE_PATH).read_text(encoding="utf-8")
    )
    _require(isinstance(document, dict), "Program acceptance map is invalid")
    return document


def _validate_dependency_bindings(
    bindings: Any,
    *,
    root: Path,
    repetition: int,
) -> None:
    _require(
        isinstance(bindings, list)
        and len(bindings) == 5
        and all(isinstance(item, dict) for item in bindings),
        f"Formal pair {repetition} dependency bindings are invalid",
    )
    observed_paths: set[Path] = set()
    for binding in bindings:
        raw_path = binding.get("path")
        _require(
            isinstance(raw_path, str),
            f"Formal pair {repetition} dependency path is invalid",
        )
        path = Path(raw_path)
        if not path.is_absolute():
            path = root / path
        path = path.resolve()
        _require(
            path.is_file()
            and _sha256(path).lower()
            == str(binding.get("sha256", "")).lower(),
            f"Formal pair {repetition} dependency binding drifted",
        )
        _require(
            root.resolve() in path.parents,
            f"Formal pair {repetition} dependency escaped repository",
        )
        observed_paths.add(path)
    _require(
        len(observed_paths) == 5,
        f"Formal pair {repetition} dependency bindings are not unique",
    )


def _derive_in_window_methods(arm: dict[str, Any]) -> list[str]:
    ledger = arm.get("requestLedger")
    start = arm.get("windowStartMonotonic")
    _require(
        isinstance(ledger, list)
        and all(isinstance(item, dict) for item in ledger)
        and isinstance(start, (int, float)),
        "Arm request ledger or time window is invalid",
    )
    return [
        str(item["method"])
        for item in ledger
        if isinstance(item.get("sentMonotonic"), (int, float))
        and float(start)
        <= float(item["sentMonotonic"])
        <= float(start) + 5.0
    ]


def _recompute_arm(
    arm_name: str,
    arm: dict[str, Any],
    *,
    pair_design: dict[str, Any],
) -> tuple[dict[str, Any], int]:
    baseline_call = arm.get("baselineCall")
    baseline_process = arm.get("baselineProcess")
    app_server_process = arm.get("appServerProcess")
    process_samples = arm.get("processSamples")
    events = arm.get("eventsAtWindowEnd")
    post_window_call = arm.get("postWindowCall")
    ledger = arm.get("requestLedger")
    _require(
        isinstance(baseline_call, dict)
        and isinstance(baseline_process, dict)
        and isinstance(app_server_process, dict)
        and isinstance(process_samples, list)
        and all(isinstance(item, dict) for item in process_samples)
        and isinstance(events, list)
        and all(isinstance(item, dict) for item in events)
        and isinstance(post_window_call, dict)
        and isinstance(ledger, list)
        and all(isinstance(item, dict) for item in ledger),
        f"{arm_name} raw evidence omitted required surfaces",
    )
    baseline_instance = baseline_call.get("instanceId")
    baseline_pid = baseline_call.get("pid")
    _require(
        isinstance(baseline_instance, str)
        and isinstance(baseline_pid, int)
        and baseline_call.get("succeeded") is True
        and baseline_call.get("arguments", {}).get("probe") == PROBE_ID
        and baseline_call.get("arguments", {}).get("arm") == arm_name
        and baseline_call.get("arguments", {}).get("phase") == "baseline",
        f"{arm_name} baseline call identity drifted",
    )
    _require(
        process_identity_complete(baseline_process)
        and baseline_process.get("pid") == baseline_pid
        and baseline_process.get("parentPid") == app_server_process.get("pid")
        and isinstance(baseline_process.get("creationTime100ns"), int)
        and str(baseline_process.get("imagePath", "")).lower().endswith(
            "python.exe"
        ),
        f"{arm_name} exact Sentinel process binding drifted",
    )
    _require(
        process_identity_complete(app_server_process)
        and str(app_server_process.get("imagePath", "")).lower().endswith(
            "codex.exe"
        ),
        f"{arm_name} exact app-server process binding drifted",
    )
    for sample in process_samples:
        _require(
            isinstance(sample.get("sentinel"), dict)
            and same_process_identity(
                baseline_process,
                sample["sentinel"],
            )
            and isinstance(sample.get("appServer"), dict)
            and same_process_identity(
                app_server_process,
                sample["appServer"],
            ),
            f"{arm_name} exact process sample identity drifted",
        )

    start = datetime.fromisoformat(str(arm.get("windowStartAt")))
    end = datetime.fromisoformat(str(arm.get("windowEndAt")))
    recomputed_stop_events = stop_events_in_window(
        events,
        baseline_instance,
        start,
        end,
    )
    _require(
        recomputed_stop_events == arm.get("stopEventsInWindow"),
        f"{arm_name} stop-event derivation drifted",
    )
    in_window_methods = _derive_in_window_methods(arm)
    _require(
        in_window_methods == arm.get("inWindowHostMethods"),
        f"{arm_name} in-window request derivation drifted",
    )
    all_methods = [str(item.get("method")) for item in ledger]
    _require(
        all_methods == arm.get("requestMethodsDerivedFromLedger")
        and all_methods == EXPECTED_REQUEST_METHODS[arm_name],
        f"{arm_name} request ledger sequence drifted",
    )
    model_turn_count = sum(
        1 for item in ledger if item.get("method") == "turn/start"
    )
    start_monotonic = arm.get("windowStartMonotonic")
    action_monotonic = arm.get("actionMonotonic")
    _require(
        isinstance(start_monotonic, (int, float))
        and isinstance(action_monotonic, (int, float)),
        f"{arm_name} monotonic action binding is invalid",
    )
    action_skew = (
        float(action_monotonic) - float(start_monotonic)
    ) * 1000
    _require(
        math.isclose(
            action_skew,
            float(arm.get("actionSkewMilliseconds")),
            rel_tol=0.0,
            abs_tol=1e-6,
        ),
        f"{arm_name} action skew derivation drifted",
    )
    return (
        classify_arm(
            arm=arm_name,
            baseline_instance_id=baseline_instance,
            baseline_pid=baseline_pid,
            baseline_process=baseline_process,
            process_samples=process_samples,
            stop_events=recomputed_stop_events,
            post_window_call=post_window_call,
            in_window_host_methods=in_window_methods,
            unsubscribe_status=arm.get("unsubscribeStatus"),
            action_skew_milliseconds=action_skew,
            observation_seconds=float(pair_design["observationSeconds"]),
            sample_interval_seconds=float(
                pair_design["sampleIntervalSeconds"]
            ),
            model_turn_count=model_turn_count,
        ),
        model_turn_count,
    )


def _validate_arm_boundaries(
    arm_name: str,
    arm: dict[str, Any],
    *,
    repetition: int,
) -> None:
    environment = arm.get("environment")
    configuration = arm.get("configuration")
    thread = arm.get("thread")
    shutdown = arm.get("shutdownAndCleanup")
    claims = arm.get("classification")
    _require(
        isinstance(environment, dict)
        and environment.get("allowlistApplied") is True
        and environment.get("valuesRecorded") is False
        and environment.get("accountOrProxyKeysInherited") is False
        and isinstance(environment.get("inheritedKeyNames"), list),
        f"Formal pair {repetition} {arm_name} environment drifted",
    )
    allowed_keys = set(MINIMAL_ENVIRONMENT_KEYS) | {
        "CODEX_HOME",
        "RUST_LOG",
        "LOG_FORMAT",
    }
    inherited_keys = environment["inheritedKeyNames"]
    _require(
        set(inherited_keys) <= allowed_keys
        and {"CODEX_HOME", "RUST_LOG", "LOG_FORMAT"}
        <= set(inherited_keys),
        f"Formal pair {repetition} {arm_name} inherited environment drifted",
    )
    _require(
        isinstance(configuration, dict)
        and configuration.get("enabled") is True
        and configuration.get("unchangedDuringProbe") is True
        and configuration.get("currentUserConfigCopied") is False
        and isinstance(configuration.get("sha256"), str),
        f"Formal pair {repetition} {arm_name} configuration drifted",
    )
    _require(
        isinstance(thread, dict)
        and isinstance(thread.get("id"), str)
        and thread.get("ephemeralRequested") is True
        and thread.get("modelTurnStarted") is False,
        f"Formal pair {repetition} {arm_name} thread boundary drifted",
    )
    _require(
        isinstance(shutdown, dict)
        and shutdown.get("appServerReturnCode") == 0
        and shutdown.get("appServerKillSent") is False
        and shutdown.get("authStateProduced") is False
        and shutdown.get(
            "applicationLogExternalNetworkAttemptObserved"
        )
        is True
        and isinstance(shutdown.get("cleanup"), dict)
        and shutdown["cleanup"].get("cleanupVerified") is True
        and shutdown["cleanup"].get("pidSignalCleanupUsed") is False,
        f"Formal pair {repetition} {arm_name} lifecycle drifted",
    )
    _require(
        isinstance(claims, dict)
        and claims.get("valid") is True
        and claims.get("runtimeRetained") is True
        and claims.get("releaseObserved") is False
        and claims.get("actualSampleCount") == 11
        and claims.get("expectedSampleCount") == 11,
        f"Formal pair {repetition} {arm_name} classification boundary drifted",
    )
    if arm_name == ARM_CONTROL:
        _require(
            arm.get("unsubscribeResponse") is None
            and arm.get("unsubscribeStatus") is None,
            f"Formal pair {repetition} control unsubscribe boundary drifted",
        )
    else:
        response = arm.get("unsubscribeResponse")
        _require(
            isinstance(response, dict)
            and response.get("result", {}).get("status") == "unsubscribed"
            and arm.get("unsubscribeStatus") == "unsubscribed",
            f"Formal pair {repetition} unsubscribe acknowledgement drifted",
        )


def _validate_schema_metadata(document: dict[str, Any], root: Path) -> None:
    host = document["hostBinding"]
    _require(
        host.get("stableSchemaEvidence") == EXPECTED_SCHEMA_BINDINGS,
        "Stable thread-unsubscribe schema bindings drifted",
    )
    direct = json.loads(
        (root / DIRECT_EVIDENCE_PATH).read_text(encoding="utf-8")
    )
    files = direct.get("stableSchemaEvidence", {}).get("files", {})
    _require(
        isinstance(files, dict)
        and files.get("ClientRequest.json")
        == EXPECTED_SCHEMA_BINDINGS[0]["sha256"].lower()
        and files.get("v2/ThreadUnsubscribeParams.json")
        == EXPECTED_SCHEMA_BINDINGS[1]["sha256"].lower(),
        "Stable schema metadata no longer agrees with prior evidence",
    )


def _validate_program_mapping(
    program_map: dict[str, Any],
) -> None:
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
        "Thread-unsubscribe acceptance mapping drifted",
    )
    _require(
        matching_evidence
        == [
            {
                "id": PROGRAM_EVIDENCE_ID,
                "path": EVIDENCE_PATH,
                "kind": (
                    "observed-three-valid-paired-repetitions-unsubscribe-"
                    "runtime-retained-five-seconds-with-subscribed-controls-"
                    "no-host-model-turn"
                ),
                "asOf": "2026-07-27",
                "supports": [PROGRAM_ACCEPTANCE_ID],
            }
        ],
        "Thread-unsubscribe program evidence mapping drifted",
    )
    acceptance_references = {
        item["id"]
        for item in acceptances
        if PROGRAM_EVIDENCE_ID in item.get("evidenceIds", [])
    }
    _require(
        acceptance_references == {PROGRAM_ACCEPTANCE_ID},
        "Thread-unsubscribe evidence has an unauthorized acceptance reference",
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
            "mcp-app-server-0.145.0-thread-unsubscribe-release-"
            "attribution-evidence-2026-07-27"
        )
        and document.get("date") == "2026-07-27"
        and document.get("status")
        == (
            "observed-three-valid-paired-repetitions-unsubscribe-runtime-"
            "retained-five-seconds-with-subscribed-controls"
        ),
        "Thread-unsubscribe evidence identity drifted",
    )
    host = document.get("hostBinding")
    _require(
        isinstance(host, dict)
        and host.get("platform") == "Windows"
        and host.get("codexVersion") == "codex-cli 0.145.0"
        and host.get("probeId") == PROBE_ID
        and host.get("formalPairCount") == 3
        and host.get("formalAppServerCount") == 6
        and host.get("observationSecondsPerArm") == 5.0
        and host.get("sampleIntervalSeconds") == 0.5,
        "Thread-unsubscribe host binding drifted",
    )
    for key, label in (
        ("probeScript", "probe"),
        ("sentinel", "Sentinel"),
    ):
        binding = host.get(key)
        _require(isinstance(binding, dict), f"{label} binding is invalid")
        path = root / str(binding.get("path"))
        _require(
            path.is_file()
            and _sha256(path).upper()
            == str(binding.get("sha256", "")).upper(),
            f"{label} binding drifted",
        )
    _validate_schema_metadata(document, root)

    pair_design = document.get("pairDesign")
    _require(
        isinstance(pair_design, dict)
        and all(
            pair_design.get(key) is True
            for key in (
                "independentAppServers",
                "independentCodexHomes",
                "independentThreads",
                "independentSentinelInstances",
                "concurrentMonotonicBarrier",
            )
        )
        and pair_design.get("unsubscribeArmIntervention")
        == "one thread/unsubscribe request"
        and pair_design.get("subscribedControlIntervention")
        == "no host request"
        and pair_design.get("unsubscribeResponseStatusRequired")
        == "unsubscribed"
        and pair_design.get("maximumCrossArmActionSkewMilliseconds")
        == 100.0
        and pair_design.get("maximumPerSampleSkewMilliseconds") == 250.0
        and pair_design.get("unsubscribeIsTaskEnd") is False,
        "Thread-unsubscribe pair design drifted",
    )
    attribution = document.get("attributionBoundary")
    _require(
        isinstance(attribution, dict)
        and attribution.get("unsubscribeArmAllowedHostMethods")
        == ["thread/unsubscribe"]
        and attribution.get("controlArmAllowedHostMethods") == []
        and attribution.get("bothArmsAllowedParentActions")
        == [
            "exact-process-sampling",
            "sentinel-event-log-read",
            "app-server-liveness-sampling",
        ]
        and all(
            attribution.get(key) is False
            for key in (
                "reloadDuringWindow",
                "configWriteDuringWindow",
                "newThreadDuringWindow",
                "toolCallDuringWindow",
                "turnStartDuringWindow",
                "teardownDuringWindow",
                "cleanupDuringWindow",
                "pidSignalDuringWindow",
            )
        ),
        "Thread-unsubscribe attribution boundary drifted",
    )

    excluded = document.get("excludedCalibrationRuns")
    _require(
        isinstance(excluded, list)
        and len(excluded) == 1
        and excluded[0].get("path") == EXPECTED_CALIBRATION_PATH,
        "Excluded thread-unsubscribe calibration set drifted",
    )
    calibration = _load_bound_json(
        root,
        excluded[0],
        "Excluded thread-unsubscribe calibration",
    )
    _require(
        calibration.get("pairDesign", {}).get("observationSeconds") == 1.0,
        "Excluded calibration no longer has the one-second boundary",
    )

    formal = document.get("formalEvidence")
    _require(
        isinstance(formal, list)
        and [item.get("path") for item in formal] == EXPECTED_FORMAL_PATHS,
        "Formal thread-unsubscribe evidence set drifted",
    )
    raw_reports = [
        _load_bound_json(root, item, "Formal thread-unsubscribe evidence")
        for item in formal
    ]
    probe_hash = host["probeScript"]["sha256"]
    sentinel_hash = host["sentinel"]["sha256"]
    app_server_pids: set[int] = set()
    sentinel_pids: set[int] = set()
    instances: set[str] = set()
    threads: set[str] = set()
    homes: set[str] = set()
    total_samples = 0
    total_network_attempts = 0
    total_model_turns = 0

    for index, (binding, raw) in enumerate(
        zip(formal, raw_reports, strict=True),
        start=1,
    ):
        _require(
            raw.get("schema") == 1 and raw.get("id") == PROBE_ID,
            f"Formal pair {index} identity drifted",
        )
        raw_host = raw.get("hostBinding")
        _require(
            isinstance(raw_host, dict)
            and raw_host.get("codexVersion") == host["codexVersion"]
            and str(raw_host.get("probeScriptSha256", "")).upper()
            == probe_hash.upper()
            and str(raw_host.get("sentinelScriptSha256", "")).upper()
            == sentinel_hash.upper(),
            f"Formal pair {index} self-binding drifted",
        )
        _validate_dependency_bindings(
            raw_host.get("dependencyBindings"),
            root=root,
            repetition=index,
        )
        raw_pair_design = raw.get("pairDesign")
        raw_attribution = raw.get("attributionBoundary")
        _require(
            isinstance(raw_pair_design, dict)
            and raw_pair_design.get("observationSeconds") == 5.0
            and raw_pair_design.get("sampleIntervalSeconds") == 0.5
            and raw_pair_design.get("unsubscribeIsTaskEnd") is False
            and isinstance(raw_attribution, dict)
            and raw_attribution == attribution,
            f"Formal pair {index} design or attribution drifted",
        )
        arms = raw.get("arms")
        _require(
            isinstance(arms, dict)
            and list(arms) == list(ARM_NAMES),
            f"Formal pair {index} arm set drifted",
        )
        recomputed: dict[str, dict[str, Any]] = {}
        for arm_name in ARM_NAMES:
            arm = arms[arm_name]
            _require(
                isinstance(arm, dict),
                f"Formal pair {index} {arm_name} is invalid",
            )
            _validate_arm_boundaries(
                arm_name,
                arm,
                repetition=index,
            )
            recalculated, model_turn_count = _recompute_arm(
                arm_name,
                arm,
                pair_design=raw_pair_design,
            )
            _require(
                recalculated == arm.get("classification"),
                f"Formal pair {index} {arm_name} classification drifted",
            )
            expected_classification = (
                "subscribed-control-retained-five-seconds"
                if arm_name == ARM_CONTROL
                else "unsubscribe-runtime-retained-five-seconds"
            )
            _require(
                recalculated.get("classification")
                == expected_classification,
                f"Formal pair {index} {arm_name} result drifted",
            )
            arm_binding = (
                binding["control"]
                if arm_name == ARM_CONTROL
                else binding["unsubscribe"]
            )
            _require(
                arm["thread"]["id"] == arm_binding.get("threadId")
                and arm["baselineCall"]["pid"] == arm_binding.get("pid")
                and arm["baselineCall"]["instanceId"]
                == arm_binding.get("instanceId"),
                f"Formal pair {index} {arm_name} evidence binding drifted",
            )
            app_server_pids.add(arm["appServerProcess"]["pid"])
            sentinel_pids.add(arm["baselineCall"]["pid"])
            instances.add(arm["baselineCall"]["instanceId"])
            threads.add(arm["thread"]["id"])
            homes.add(arm["codexHome"])
            total_samples += len(arm["processSamples"])
            total_network_attempts += int(
                arm["shutdownAndCleanup"][
                    "applicationLogExternalNetworkAttemptObserved"
                ]
                is True
            )
            total_model_turns += model_turn_count
            recomputed[arm_name] = recalculated

        pair_recomputed = classify_pair(
            recomputed[ARM_CONTROL],
            recomputed[ARM_UNSUBSCRIBE],
        )
        pair_skew = abs(
            float(arms[ARM_CONTROL]["actionMonotonic"])
            - float(arms[ARM_UNSUBSCRIBE]["actionMonotonic"])
        ) * 1000
        pair_recomputed["crossArmActionSkewMilliseconds"] = pair_skew
        _require(
            pair_skew <= MAX_ACTION_SKEW_MILLISECONDS
            and pair_recomputed == raw.get("pairClassification")
            and pair_recomputed.get("classification")
            == "unsubscribe-immediate-release-falsified-bounded"
            and binding.get("pairClassification")
            == pair_recomputed.get("classification"),
            f"Formal pair {index} paired classification drifted",
        )
        isolation = raw.get("isolation")
        claims = raw.get("claimBoundary")
        _require(
            isinstance(isolation, dict)
            and isolation.get("currentAuthCopied") is False
            and isolation.get("currentPluginsCopied") is False
            and isolation.get("currentUserConfigCopied") is False
            and isolation.get("minimalEnvironmentAllowlistApplied") is True
            and isolation.get("accountOrProxyEnvironmentValuesRecorded")
            is False
            and isolation.get(
                "applicationLogExternalNetworkAttemptCount"
            )
            == 2
            and isinstance(claims, dict)
            and claims.get("provesUnsubscribeRequestAccepted") is True
            and claims.get("provesUnsubscribeIsTaskEnd") is False
            and claims.get("provesTaskEndImmediateRelease") is False
            and claims.get("provesNoNetworkTraffic") is False
            and claims.get("modelTurnStarted") is False
            and claims.get("modelRequestSent") is False,
            f"Formal pair {index} isolation or claim boundary drifted",
        )

    _require(
        len(app_server_pids)
        == len(sentinel_pids)
        == len(instances)
        == len(threads)
        == len(homes)
        == 6,
        "Formal paired runtimes are not independently isolated",
    )
    _require(total_model_turns == 0, "Formal evidence contains a model turn")
    aggregate = document.get("aggregateObservation")
    _require(
        isinstance(aggregate, dict)
        and aggregate
        == {
            "validPairCount": 3,
            "unsubscribeImmediateReleaseFalsifiedPairCount": 3,
            "unsubscribeReleaseAssociatedPairCount": 0,
            "formalAppServerCount": 6,
            "independentThreadCount": 6,
            "independentSentinelInstanceCount": 6,
            "subscribedControlRetainedCount": 3,
            "unsubscribeRuntimeRetainedCount": 3,
            "unsubscribeAcknowledgedCount": 3,
            "exactProcessIdentitySampleCount": total_samples,
            "sameIdentitySampleCount": total_samples,
            "attributionWindowStopEventCount": 0,
            "postWindowSameInstanceCallCount": 6,
            "verifiedCleanupCount": 6,
            "gracefulAppServerShutdownCount": 6,
            "appServerKillCount": 0,
            "applicationLogExternalNetworkAttemptCount": (
                total_network_attempts
            ),
            "modelTurnCount": total_model_turns,
            "modelRequestCount": 0,
        },
        "Thread-unsubscribe aggregate drifted",
    )
    _require(
        total_samples == 66 and total_network_attempts == 6,
        "Thread-unsubscribe aggregate source counts drifted",
    )
    decision = document.get("decision")
    _require(
        isinstance(decision, dict)
        and decision.get("unsubscribeRequestAcceptanceObserved") is True
        and decision.get(
            "unsubscribeImmediateReleaseInTestedWindowObserved"
        )
        is False
        and decision.get(
            "unsubscribeAsObservedImmediateReleaseMechanismFalsifiedForTestedBoundary"
        )
        is True
        and decision.get("subscribedControlRetainedForTestedWindow") is True
        and decision.get("nativeThirtyMinuteIdleFallbackRemainsSeparate")
        is True
        and decision.get("dynamicRuntimeControlAssessment") == "partial"
        and decision.get("residualSelfAuthoredControllerGapProved") is False
        and decision.get("nextBoundedGap")
        == (
            "Evaluate overlapping task or subscription ownership and final-"
            "release semantics separately before any lease or reference-count "
            "claim."
        ),
        "Thread-unsubscribe decision drifted",
    )
    claims = document.get("claimBoundary")
    _require(
        isinstance(claims, dict)
        and claims
        == {
            "unsubscribeIsTaskEndProved": False,
            "taskEndImmediateReleaseProved": False,
            "sameThreadHotEnableDisableForArbitraryMcpProved": False,
            "leaseOrReferenceCountProved": False,
            "stableResourceSavingsProved": False,
            "genericCrashRecoveryProved": False,
            "arbitraryMcpBehaviorProved": False,
            "crossHostParityProved": False,
            "crossVersionParityProved": False,
            "noNetworkTrafficProved": False,
            "residualNeedForSelfAuthoredControllerProved": False,
            "productionReadinessProved": False,
        },
        "Thread-unsubscribe claim boundary drifted",
    )
    program_acceptance = document.get("programAcceptance")
    cleanup = document.get("cleanupDisposition")
    _require(
        isinstance(program_acceptance, dict)
        and program_acceptance
        == {
            "acceptanceId": PROGRAM_ACCEPTANCE_ID,
            "assessment": "partial",
            "supportsResidualGapProof": False,
        },
        "Thread-unsubscribe program acceptance boundary drifted",
    )
    _require(
        isinstance(cleanup, dict)
        and cleanup
        == {
            "repositoryAudit": "retain-authoritative-host-evidence",
            "isolatedHostRoots": (
                "retain-temporary-process-evidence-pending-program-cleanup-gate"
            ),
            "deletionAuthorized": False,
        },
        "Thread-unsubscribe cleanup boundary drifted",
    )

    _validate_program_mapping(_load_program_map(root, program_map))
    normalized_doc = " ".join(
        (root / DOC_PATH).read_text(encoding="utf-8").split()
    )
    normalized_readme = " ".join(
        (root / AUDIT_README_PATH).read_text(encoding="utf-8").split()
    )
    for phrase in (
        "This is not a synonym for task end.",
        "all 66 process samples",
        "does not claim zero network traffic",
        "overlapping task or subscription ownership",
        "residual need for a self-authored controller",
    ):
        _require(
            phrase in normalized_doc,
            f"Thread-unsubscribe documentation boundary missing: {phrase}",
        )
    for phrase in (
        "complete formal set",
        "Mixed results are non-reproducible",
        "does not by itself prove thread closure",
        "authoritative host evidence",
        "separate cleanup decision",
    ):
        _require(
            phrase in normalized_readme,
            f"Thread-unsubscribe audit boundary missing: {phrase}",
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    arguments = parser.parse_args()
    root = arguments.root.resolve()
    document = json.loads((root / EVIDENCE_PATH).read_text(encoding="utf-8"))
    validate_evidence(document, root=root)
    print("MCP thread-unsubscribe release attribution evidence passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
