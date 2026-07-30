#!/usr/bin/env python3
"""Isolate whether Codex MCP reload releases one already-loaded runtime.

The probe uses an empty explicit CODEX_HOME, one local Sentinel, and no model
turn.  During the attribution window it keeps app-server and the original
thread alive while forbidding new threads, unsubscribe, teardown, and harness
cleanup.  Reload acceptance, status projection, exact process identity, the
Sentinel stop event, and the post-window same-thread call are separate facts.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import time
from typing import Any

try:
    from .probe_codex_app_server_mcp_idle_unload import (
        process_identity_complete,
        same_process_identity,
        snapshot_process,
    )
    from .probe_codex_app_server_mcp_reload_new_threads import (
        atomic_replace_bytes,
        build_status_request,
        sha256_bytes,
        summarize_status,
        summarize_tool_call,
    )
    from .probe_codex_app_server_mcp_status import (
        build_child_environment,
        build_command,
        drain_stdout_queue,
        inventory_files,
        wait_for_response,
    )
    from .probe_codex_app_server_mcp_tool_call import (
        build_isolated_config,
        extract_thread_id,
        load_events,
        process_exists,
        resolve_native_codex_executable,
        wait_for_process_exit,
    )
except ImportError:  # pragma: no cover - direct script execution
    from probe_codex_app_server_mcp_idle_unload import (
        process_identity_complete,
        same_process_identity,
        snapshot_process,
    )
    from probe_codex_app_server_mcp_reload_new_threads import (
        atomic_replace_bytes,
        build_status_request,
        sha256_bytes,
        summarize_status,
        summarize_tool_call,
    )
    from probe_codex_app_server_mcp_status import (
        build_child_environment,
        build_command,
        drain_stdout_queue,
        inventory_files,
        wait_for_response,
    )
    from probe_codex_app_server_mcp_tool_call import (
        build_isolated_config,
        extract_thread_id,
        load_events,
        process_exists,
        resolve_native_codex_executable,
        wait_for_process_exit,
    )


PROBE_ID = "codex-app-server-mcp-reload-release-attribution-v1"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_thread_start_request(
    request_id: int,
    workspace: Path,
    label: str,
) -> dict[str, Any]:
    return {
        "id": request_id,
        "method": "thread/start",
        "params": {
            "cwd": workspace.resolve().as_posix(),
            "ephemeral": True,
            "approvalPolicy": "never",
            "sandbox": "read-only",
            "name": f"{PROBE_ID}-{label}",
        },
    }


def build_tool_request(
    request_id: int,
    thread_id: str,
    phase: str,
) -> dict[str, Any]:
    return {
        "id": request_id,
        "method": "mcpServer/tool/call",
        "params": {
            "threadId": thread_id,
            "server": "lifecycle_sentinel",
            "tool": "identity",
            "arguments": {"probe": PROBE_ID, "phase": phase},
        },
    }


def status_reports_callable_sentinel_tools(
    status: dict[str, Any],
) -> bool:
    data = status.get("data")
    if not isinstance(data, list):
        return False
    for item in data:
        if not isinstance(item, dict) or item.get("name") != "lifecycle_sentinel":
            continue
        tools = item.get("tools")
        return (
            isinstance(tools, dict) and bool(tools)
        ) or (
            isinstance(tools, list) and bool(tools)
        )
    return False


def read_executable_version(executable: str) -> str:
    completed = subprocess.run(
        [executable, "--version"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=15,
        check=False,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"unable to read Codex version: {completed.stderr.strip()}"
        )
    version = completed.stdout.strip()
    if not version:
        raise RuntimeError("Codex version output is empty")
    return version


def _parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def events_for_instance(
    events: list[dict[str, Any]], instance_id: str
) -> list[dict[str, Any]]:
    return [
        event
        for event in events
        if event.get("instanceId") == instance_id
    ]


def stop_events_in_window(
    events: list[dict[str, Any]],
    instance_id: str,
    start: datetime,
    end: datetime,
) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    for event in events_for_instance(events, instance_id):
        if event.get("event") != "instance-stop":
            continue
        timestamp = _parse_timestamp(event.get("timestamp"))
        if timestamp is not None and start <= timestamp <= end:
            matches.append(event)
    return matches


def classify_reload_window(
    *,
    baseline_instance_id: str,
    baseline_pid: int,
    baseline_process: dict[str, Any],
    process_samples: list[dict[str, Any]],
    stop_events: list[dict[str, Any]],
    post_window_call: dict[str, Any],
    app_server_alive_through_window: bool,
    attribution_actions: list[str],
    config_restored_exactly: bool,
) -> dict[str, Any]:
    """Classify only facts that can be attributed to the pure reload window."""

    invalid_reasons: list[str] = []
    if not process_identity_complete(baseline_process):
        invalid_reasons.append("baseline-process-identity-incomplete")
    if not process_samples:
        invalid_reasons.append("no-process-samples")
    if not app_server_alive_through_window:
        invalid_reasons.append("app-server-exited-during-window")
    if attribution_actions != [
        "config-write-disabled",
        "config/mcpServer/reload",
        "mcpServerStatus/list",
        "read-only-process-and-event-sampling",
    ]:
        invalid_reasons.append("forbidden-or-missing-attribution-window-action")
    if not config_restored_exactly:
        invalid_reasons.append("config-not-restored-exactly")

    same_identity_samples = [
        same_process_identity(baseline_process, sample)
        for sample in process_samples
    ]
    final_sample = process_samples[-1] if process_samples else {}
    final_same_identity = (
        same_process_identity(baseline_process, final_sample)
        if process_samples
        else False
    )
    call_same_instance = (
        post_window_call.get("succeeded") is True
        and post_window_call.get("instanceId") == baseline_instance_id
        and post_window_call.get("pid") == baseline_pid
    )

    if invalid_reasons:
        classification = "measurement-invalid"
        reload_release_observed = False
        loaded_runtime_retained = False
    elif stop_events and final_sample.get("exists") is False:
        classification = "reload-release-observed-bounded"
        reload_release_observed = True
        loaded_runtime_retained = False
    elif (
        all(same_identity_samples)
        and not stop_events
        and final_same_identity
        and call_same_instance
    ):
        classification = "loaded-runtime-retained-after-reload"
        reload_release_observed = False
        loaded_runtime_retained = True
    else:
        classification = "measurement-invalid"
        reload_release_observed = False
        loaded_runtime_retained = False
        invalid_reasons.append("reload-window-outcome-ambiguous")

    return {
        "classification": classification,
        "valid": classification != "measurement-invalid",
        "invalidReasons": invalid_reasons,
        "reloadReleaseObserved": reload_release_observed,
        "loadedRuntimeRetained": loaded_runtime_retained,
        "sameIdentityBySample": same_identity_samples,
        "finalSameProcessIdentity": final_same_identity,
        "postWindowCallSameInstance": call_same_instance,
    }


def _cleanup_lingering_sentinels(
    event_log: Path,
    cleanup_marker: Path,
) -> dict[str, Any]:
    events_before = load_events(event_log)
    started = {
        str(event["instanceId"]): int(event["pid"])
        for event in events_before
        if event.get("event") == "instance-start"
        and isinstance(event.get("instanceId"), str)
        and isinstance(event.get("pid"), int)
    }
    stopped = {
        str(event["instanceId"])
        for event in events_before
        if event.get("event") == "instance-stop"
        and isinstance(event.get("instanceId"), str)
    }
    targets = sorted(
        instance_id
        for instance_id, pid in started.items()
        if instance_id not in stopped and process_exists(pid)
    )
    marker_created = False
    if targets:
        cleanup_marker.write_text(
            f"{PROBE_ID}\n",
            encoding="utf-8",
            newline="\n",
        )
        marker_created = True
    deadline = time.monotonic() + 5
    acknowledged: set[str] = set()
    while time.monotonic() < deadline:
        current = load_events(event_log)
        acknowledged = {
            str(event["instanceId"])
            for event in current
            if event.get("event") == "harness-cleanup-marker-observed"
            and isinstance(event.get("instanceId"), str)
        }
        if set(targets).issubset(acknowledged):
            break
        time.sleep(0.05)
    pid_absent = {
        started[instance_id]: wait_for_process_exit(started[instance_id], 5)
        for instance_id in started
    }
    return {
        "markerCreated": marker_created,
        "targetInstanceIds": targets,
        "acknowledgedInstanceIds": sorted(acknowledged),
        "allTargetsAcknowledged": set(targets).issubset(acknowledged),
        "pidAbsentAfterCleanup": pid_absent,
        "cleanupVerified": (
            set(targets).issubset(acknowledged)
            and all(pid_absent.values())
        ),
        "pidSignalCleanupUsed": False,
        "cleanupMarkerExitIsNaturalReleaseEvidence": False,
        "eventsAfterCleanup": load_events(event_log),
    }


def run_probe(
    codex_home: Path,
    workspace: Path,
    sentinel_script: Path,
    codex_executable: str | None,
    observation_seconds: float,
    sample_interval_seconds: float,
    timeout_seconds: float,
) -> dict[str, Any]:
    codex_home = codex_home.resolve()
    workspace = workspace.resolve()
    sentinel_script = sentinel_script.resolve()
    default_home = (Path.home() / ".codex").resolve()
    if os.name != "nt":
        raise RuntimeError("exact process attribution currently requires Windows")
    if os.path.normcase(str(codex_home)) == os.path.normcase(str(default_home)):
        raise RuntimeError("refusing to use the current default Codex home")
    if codex_home.exists() and any(codex_home.iterdir()):
        raise RuntimeError("isolated Codex home must be absent or empty")
    if not sentinel_script.is_file():
        raise RuntimeError(f"Sentinel script is missing: {sentinel_script}")
    if observation_seconds < 1:
        raise RuntimeError("observation window must be at least one second")
    if not 0 < sample_interval_seconds <= observation_seconds:
        raise RuntimeError("sample interval must be positive and within the window")
    codex_home.mkdir(parents=True, exist_ok=True)
    workspace.mkdir(parents=True, exist_ok=True)

    event_log = codex_home / "sentinel-events.jsonl"
    cleanup_marker = codex_home / "harness-cleanup.marker"
    config_path = codex_home / "config.toml"
    enabled_bytes = build_isolated_config(
        Path(sys.executable),
        sentinel_script,
        event_log,
        enabled=True,
        cleanup_marker=cleanup_marker,
    ).encode("utf-8")
    disabled_bytes = build_isolated_config(
        Path(sys.executable),
        sentinel_script,
        event_log,
        enabled=False,
        cleanup_marker=cleanup_marker,
    ).encode("utf-8")
    enabled_hash = sha256_bytes(enabled_bytes)
    disabled_hash = sha256_bytes(disabled_bytes)
    initial_write_at = utc_now()
    atomic_replace_bytes(config_path, enabled_bytes)
    files_before = inventory_files(codex_home)

    executable = resolve_native_codex_executable(codex_executable)
    codex_version = read_executable_version(executable)
    probe_script = Path(__file__).resolve()
    probe_script_hash = sha256_bytes(probe_script.read_bytes())
    sentinel_script_hash = sha256_bytes(sentinel_script.read_bytes())
    command = build_command(executable)
    command.extend(
        [
            "--disable",
            "plugins",
            "--disable",
            "remote_plugin",
            "--disable",
            "apps",
            "--disable",
            "plugin_sharing",
        ]
    )
    environment, removed_keys = build_child_environment(codex_home)
    process = subprocess.Popen(
        command,
        cwd=workspace,
        env=environment,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    stdout_queue: queue.Queue[str | None] = queue.Queue()
    stderr_lines: list[str] = []
    messages: list[dict[str, Any]] = []
    responses: dict[int, dict[str, Any]] = {}

    def read_stdout() -> None:
        assert process.stdout is not None
        for line in process.stdout:
            stdout_queue.put(line)
        stdout_queue.put(None)

    def read_stderr() -> None:
        assert process.stderr is not None
        stderr_lines.extend(line.rstrip("\r\n") for line in process.stderr)

    stdout_thread = threading.Thread(target=read_stdout, daemon=True)
    stderr_thread = threading.Thread(target=read_stderr, daemon=True)
    stdout_thread.start()
    stderr_thread.start()
    deadline = time.monotonic() + timeout_seconds

    def send(request: dict[str, Any]) -> dict[str, Any]:
        assert process.stdin is not None
        request_id = request.get("id")
        if not isinstance(request_id, int):
            raise RuntimeError("request omitted integer id")
        process.stdin.write(json.dumps(request, separators=(",", ":")) + "\n")
        process.stdin.flush()
        response = wait_for_response(
            stdout_queue, request_id, deadline, messages
        )
        responses[request_id] = response
        return response

    def require_success(
        response: dict[str, Any], method: str
    ) -> dict[str, Any]:
        if "error" in response:
            raise RuntimeError(f"{method} failed: {response['error']}")
        return response

    started_at = utc_now()
    thread_ids: dict[str, str] = {}
    disabled_write_at: str | None = None
    reload_response_at: datetime | None = None
    window_end_at: datetime | None = None
    baseline_call: dict[str, Any] = {}
    post_window_call: dict[str, Any] = {}
    recovery_call: dict[str, Any] = {}
    baseline_process: dict[str, Any] = {}
    process_samples: list[dict[str, Any]] = []
    status_after_reload: dict[str, Any] = {}
    attribution_events: list[dict[str, Any]] = []
    restoration_succeeded = False
    app_server_alive_through_window = False
    app_server_kill_sent = False
    failure: BaseException | None = None
    initialize_observation: dict[str, Any] = {}

    try:
        initialize = require_success(
            send(
                {
                    "id": 0,
                    "method": "initialize",
                    "params": {
                        "clientInfo": {
                            "name": PROBE_ID,
                            "title": "MCP Reload Release Attribution Probe",
                            "version": "1.0.0",
                        }
                    },
                }
            ),
            "initialize",
        )
        initialize_result = initialize.get("result")
        if not isinstance(initialize_result, dict):
            raise RuntimeError("initialize result is not an object")
        initialize_observation = {
            "codexHome": initialize_result.get("codexHome"),
            "userAgent": initialize_result.get("userAgent"),
            "platformFamily": initialize_result.get("platformFamily"),
            "platformOs": initialize_result.get("platformOs"),
        }
        actual_home = Path(str(initialize_result.get("codexHome"))).resolve()
        if os.path.normcase(str(actual_home)) != os.path.normcase(
            str(codex_home)
        ):
            raise RuntimeError("app-server used an unexpected Codex home")
        assert process.stdin is not None
        process.stdin.write(json.dumps({"method": "initialized"}) + "\n")
        process.stdin.flush()

        thread_a = require_success(
            send(build_thread_start_request(1, workspace, "reload-attribution")),
            "thread/start A",
        )
        thread_ids["a"] = extract_thread_id(thread_a)
        baseline_response = require_success(
            send(build_tool_request(2, thread_ids["a"], "baseline")),
            "baseline tool call",
        )
        baseline_call = summarize_tool_call(baseline_response)
        baseline_pid = baseline_call.get("pid")
        baseline_instance_id = baseline_call.get("instanceId")
        if not isinstance(baseline_pid, int) or not isinstance(
            baseline_instance_id, str
        ):
            raise RuntimeError("baseline call omitted exact Sentinel identity")
        baseline_process = snapshot_process(baseline_pid)
        if not process_identity_complete(baseline_process):
            raise RuntimeError("baseline process identity is incomplete")

        disabled_write_at = utc_now()
        if atomic_replace_bytes(config_path, disabled_bytes) != disabled_hash:
            raise RuntimeError("disabled config hash verification failed")
        require_success(
            send({"id": 3, "method": "config/mcpServer/reload", "params": None}),
            "disable reload",
        )
        reload_response_at = datetime.now(timezone.utc)
        status_after_reload = summarize_status(
            require_success(
                send(build_status_request(4, thread_ids["a"])),
                "status after reload",
            )
        )
        attribution_actions = [
            "config-write-disabled",
            "config/mcpServer/reload",
            "mcpServerStatus/list",
            "read-only-process-and-event-sampling",
        ]
        window_deadline = time.monotonic() + observation_seconds
        while True:
            process_samples.append(snapshot_process(baseline_pid))
            if process.poll() is not None:
                break
            remaining = window_deadline - time.monotonic()
            if remaining <= 0:
                break
            time.sleep(min(sample_interval_seconds, remaining))
        window_end_at = datetime.now(timezone.utc)
        app_server_alive_through_window = process.poll() is None
        attribution_events = load_events(event_log)
        post_window_response = send(
            build_tool_request(5, thread_ids["a"], "after-reload-window")
        )
        post_window_call = summarize_tool_call(post_window_response)

        if atomic_replace_bytes(config_path, enabled_bytes) != enabled_hash:
            raise RuntimeError("enabled config restoration hash verification failed")
        restoration_succeeded = True
        require_success(
            send({"id": 6, "method": "config/mcpServer/reload", "params": None}),
            "restore reload",
        )
        thread_b = require_success(
            send(build_thread_start_request(7, workspace, "restored-control")),
            "thread/start B",
        )
        thread_ids["b"] = extract_thread_id(thread_b)
        recovery_call = summarize_tool_call(
            require_success(
                send(build_tool_request(8, thread_ids["b"], "restored-control")),
                "restored control call",
            )
        )
        for request_id, label in ((9, "a"), (10, "b")):
            require_success(
                send(
                    {
                        "id": request_id,
                        "method": "thread/unsubscribe",
                        "params": {"threadId": thread_ids[label]},
                    }
                ),
                f"unsubscribe {label}",
            )
    except BaseException as error:
        failure = error
    finally:
        try:
            restoration_succeeded = (
                atomic_replace_bytes(config_path, enabled_bytes) == enabled_hash
            )
        except BaseException as error:
            if failure is None:
                failure = error
        if process.stdin is not None and not process.stdin.closed:
            process.stdin.close()
        if process.poll() is None:
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                app_server_kill_sent = True
                process.kill()
                process.wait(timeout=5)
        stdout_thread.join(timeout=1)
        stderr_thread.join(timeout=1)
        drain_stdout_queue(stdout_queue, messages)

    events_before_cleanup = load_events(event_log)
    cleanup = _cleanup_lingering_sentinels(event_log, cleanup_marker)
    config_restored_exactly = config_path.read_bytes() == enabled_bytes
    files_after = inventory_files(codex_home)
    if failure is not None:
        raise failure
    if reload_response_at is None or window_end_at is None:
        raise RuntimeError("reload attribution window timestamps are missing")

    baseline_pid = int(baseline_call["pid"])
    baseline_instance_id = str(baseline_call["instanceId"])
    window_stop_events = stop_events_in_window(
        attribution_events,
        baseline_instance_id,
        reload_response_at,
        window_end_at,
    )
    classification = classify_reload_window(
        baseline_instance_id=baseline_instance_id,
        baseline_pid=baseline_pid,
        baseline_process=baseline_process,
        process_samples=process_samples,
        stop_events=window_stop_events,
        post_window_call=post_window_call,
        app_server_alive_through_window=app_server_alive_through_window,
        attribution_actions=attribution_actions,
        config_restored_exactly=config_restored_exactly,
    )
    status_runtime_divergence = (
        not status_reports_callable_sentinel_tools(status_after_reload)
        and classification["loadedRuntimeRetained"] is True
    )
    external_network_attempt_lines = [
        line
        for line in stderr_lines
        if "https://" in line or "http://" in line or "wss://" in line
    ]
    finished_at = utc_now()
    return {
        "schema": 1,
        "id": PROBE_ID,
        "startedAt": started_at,
        "finishedAt": finished_at,
        "command": command,
        "hostBinding": {
            "codexVersion": codex_version,
            "nativeCodexExecutable": executable,
            "probeScript": probe_script.as_posix(),
            "probeScriptSha256": probe_script_hash,
            "sentinelScript": sentinel_script.as_posix(),
            "sentinelScriptSha256": sentinel_script_hash,
            "pythonVersion": sys.version,
            "initialize": initialize_observation,
        },
        "requestMethods": [
            "initialize",
            "initialized",
            "thread/start:a",
            "mcpServer/tool/call:a:baseline",
            "config/mcpServer/reload:disable",
            "mcpServerStatus/list:a:after-reload",
            "pure-observation-window",
            "mcpServer/tool/call:a:after-window",
            "config/mcpServer/reload:restore",
            "thread/start:b",
            "mcpServer/tool/call:b:restored-control",
            "thread/unsubscribe:a",
            "thread/unsubscribe:b",
        ],
        "threads": {
            label: {
                "id": thread_id,
                "ephemeralRequested": True,
                "modelTurnStarted": False,
            }
            for label, thread_id in thread_ids.items()
        },
        "configuration": {
            "before": {
                "sha256": enabled_hash,
                "bytes": len(enabled_bytes),
                "enabled": True,
                "atomicWriteAt": initial_write_at,
            },
            "disabled": {
                "sha256": disabled_hash,
                "bytes": len(disabled_bytes),
                "enabled": False,
                "atomicWriteAt": disabled_write_at,
            },
            "restored": {
                "sha256": sha256_bytes(config_path.read_bytes()),
                "bytes": len(config_path.read_bytes()),
                "enabled": True,
            },
            "disabledDiffersFromBefore": disabled_hash != enabled_hash,
            "restoredBytesEqualBefore": config_restored_exactly,
            "currentUserConfigCopied": False,
        },
        "reloadObservation": {
            "disableResponse": responses[3].get("result"),
            "restoreResponse": responses[6].get("result"),
            "responseProvesCompletedActuation": False,
            "reloadResponseAt": reload_response_at.isoformat(),
            "windowEndAt": window_end_at.isoformat(),
            "observationSeconds": observation_seconds,
            "sampleIntervalSeconds": sample_interval_seconds,
            "attributionWindowActions": attribution_actions,
            "newThreadDuringAttributionWindow": False,
            "unsubscribeDuringAttributionWindow": False,
            "teardownDuringAttributionWindow": False,
            "harnessCleanupDuringAttributionWindow": False,
            "pidSignalDuringAttributionWindow": False,
        },
        "statusAfterDisableReload": status_after_reload,
        "toolCalls": {
            "baseline": baseline_call,
            "postWindowSameThread": post_window_call,
            "restoredNewThreadControl": recovery_call,
        },
        "processObservation": {
            "baseline": baseline_process,
            "samples": process_samples,
            "stopEventsInAttributionWindow": window_stop_events,
            "eventsAtWindowEnd": attribution_events,
            "eventsBeforeHarnessCleanup": events_before_cleanup,
            "appServerAliveThroughWindow": app_server_alive_through_window,
            "appServerReturnCode": process.returncode,
            "appServerKillSent": app_server_kill_sent,
            "cleanup": cleanup,
        },
        "classification": {
            **classification,
            "statusRuntimeDivergenceReproduced": status_runtime_divergence,
        },
        "isolation": {
            "codexHome": codex_home.as_posix(),
            "workspace": workspace.as_posix(),
            "defaultCodexHomeRejected": True,
            "removedAccountEnvironmentKeysPresentBefore": removed_keys,
            "accountEnvironmentValuesRecorded": False,
            "currentAuthCopied": False,
            "currentPluginsCopied": False,
            "authStateProduced": any(
                str(item["path"]).lower().endswith("auth.json")
                for item in files_after
            ),
            "disabledDiscoveryFeatures": [
                "plugins",
                "remote_plugin",
                "apps",
                "plugin_sharing",
            ],
            "applicationLogExternalNetworkAttemptObserved": bool(
                external_network_attempt_lines
            ),
            "applicationLogExternalNetworkAttemptLines": (
                external_network_attempt_lines
            ),
            "packetLevelNetworkMonitorUsed": False,
            "filesBefore": files_before,
            "filesAfter": files_after,
        },
        "stderrLines": stderr_lines,
        "stdoutMessageCount": len(messages),
        "claimBoundary": {
            "provesReloadRequestAccepted": True,
            "provesReloadCausedOldRuntimeRelease": (
                classification["reloadReleaseObserved"]
            ),
            "provesLoadedRuntimeRetainedInBoundedWindow": (
                classification["loadedRuntimeRetained"]
            ),
            "provesTaskEndImmediateRelease": False,
            "provesSameThreadHotEnableDisableForArbitraryMcp": False,
            "provesLeaseOrReferenceCount": False,
            "provesStableResourceSavings": False,
            "provesCrashRecovery": False,
            "provesCrossHostOrCrossVersionParity": False,
            "provesResidualNeedForSelfAuthoredController": False,
            "provesNoNetworkTraffic": False,
            "modelTurnStarted": False,
            "modelRequestSent": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--codex-home", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument(
        "--sentinel-script",
        type=Path,
        default=Path(__file__).resolve().with_name("mcp_lifecycle_sentinel.py"),
    )
    parser.add_argument("--codex-executable")
    parser.add_argument("--observation-seconds", type=float, default=5)
    parser.add_argument("--sample-interval-seconds", type=float, default=0.5)
    parser.add_argument("--timeout-seconds", type=float, default=90)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    result = run_probe(
        arguments.codex_home,
        arguments.workspace,
        arguments.sentinel_script,
        arguments.codex_executable,
        arguments.observation_seconds,
        arguments.sample_interval_seconds,
        arguments.timeout_seconds,
    )
    serialized = json.dumps(result, indent=2, ensure_ascii=False)
    if arguments.output is not None:
        output = arguments.output.resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(serialized + "\n", encoding="utf-8", newline="\n")
    print(serialized)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
