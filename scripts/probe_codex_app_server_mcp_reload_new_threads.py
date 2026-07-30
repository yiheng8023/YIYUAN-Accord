#!/usr/bin/env python3
"""Exercise isolated MCP disable/reload/re-enable behavior across new threads.

The probe uses one local stdio Sentinel, an explicit isolated CODEX_HOME, and
ephemeral read-only threads. It starts no model turn and never copies user
configuration, authentication, or Plugin state. Reload acceptance is recorded
separately from observed status, tool-call, instance, and process effects.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
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
    from .probe_codex_app_server_mcp_status import (
        build_child_environment,
        build_command,
        decode_stdout_message,
        drain_stdout_queue,
        inventory_files,
        wait_for_response,
    )
    from .probe_codex_app_server_mcp_tool_call import (
        SERVER_NAME,
        build_isolated_config,
        extract_thread_id,
        extract_tool_payload,
        load_events,
        process_exists,
        resolve_native_codex_executable,
        wait_for_process_exit,
    )
except ImportError:
    from probe_codex_app_server_mcp_status import (
        build_child_environment,
        build_command,
        decode_stdout_message,
        drain_stdout_queue,
        inventory_files,
        wait_for_response,
    )
    from probe_codex_app_server_mcp_tool_call import (
        SERVER_NAME,
        build_isolated_config,
        extract_thread_id,
        extract_tool_payload,
        load_events,
        process_exists,
        resolve_native_codex_executable,
        wait_for_process_exit,
    )


PROBE_ID = "codex-app-server-isolated-mcp-reload-new-threads-v1"


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def atomic_replace_bytes(path: Path, value: bytes) -> str:
    """Replace one explicit config file atomically and return the observed hash."""

    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        with temporary.open("wb") as stream:
            stream.write(value)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()
    observed = path.read_bytes()
    if observed != value:
        raise RuntimeError(f"atomic replacement verification failed: {path}")
    return sha256_bytes(observed)


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


def build_status_request(
    request_id: int,
    thread_id: str | None,
) -> dict[str, Any]:
    params: dict[str, Any] = {"detail": "toolsAndAuthOnly", "limit": 10}
    if thread_id is not None:
        params["threadId"] = thread_id
    return {
        "id": request_id,
        "method": "mcpServerStatus/list",
        "params": params,
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
            "server": SERVER_NAME,
            "tool": "identity",
            "arguments": {"probe": PROBE_ID, "phase": phase},
        },
    }


def summarize_status(response: dict[str, Any]) -> dict[str, Any]:
    if "error" in response:
        return {"succeeded": False, "error": response["error"]}
    result = response.get("result")
    data = result.get("data") if isinstance(result, dict) else None
    if not isinstance(data, list):
        raise RuntimeError("mcpServerStatus/list result omitted data array")
    names: list[str] = []
    for item in data:
        if not isinstance(item, dict) or not isinstance(item.get("name"), str):
            raise RuntimeError("mcpServerStatus/list returned an invalid server item")
        names.append(item["name"])
    return {
        "succeeded": True,
        "serverCount": len(data),
        "serverNames": names,
        "sentinelPresent": SERVER_NAME in names,
        "data": data,
    }


def summarize_tool_call(response: dict[str, Any]) -> dict[str, Any]:
    if "error" in response:
        return {"succeeded": False, "error": response["error"]}
    payload = extract_tool_payload(response)
    return {
        "succeeded": True,
        "server": payload.get("server"),
        "tool": payload.get("tool"),
        "pid": payload.get("pid"),
        "instanceId": payload.get("instanceId"),
        "callId": payload.get("callId"),
        "arguments": payload.get("arguments"),
    }


def run_probe(
    codex_home: Path,
    workspace: Path,
    sentinel_script: Path,
    codex_executable: str | None,
    timeout_seconds: float,
) -> dict[str, Any]:
    codex_home = codex_home.resolve()
    workspace = workspace.resolve()
    sentinel_script = sentinel_script.resolve()
    default_home = (Path.home() / ".codex").resolve()
    if os.path.normcase(str(codex_home)) == os.path.normcase(str(default_home)):
        raise RuntimeError("refusing to use the current default Codex home")
    if codex_home.exists() and any(codex_home.iterdir()):
        raise RuntimeError("isolated Codex home must be absent or empty before the probe")
    if not sentinel_script.is_file():
        raise RuntimeError(f"Sentinel script is missing: {sentinel_script}")
    codex_home.mkdir(parents=True, exist_ok=True)
    workspace.mkdir(parents=True, exist_ok=True)

    event_log = codex_home / "sentinel-events.jsonl"
    cleanup_marker = codex_home / "harness-cleanup.marker"
    config_path = codex_home / "config.toml"
    enabled_text = build_isolated_config(
        Path(sys.executable),
        sentinel_script,
        event_log,
        enabled=True,
        cleanup_marker=cleanup_marker,
    )
    disabled_text = build_isolated_config(
        Path(sys.executable),
        sentinel_script,
        event_log,
        enabled=False,
        cleanup_marker=cleanup_marker,
    )
    enabled_bytes = enabled_text.encode("utf-8")
    disabled_bytes = disabled_text.encode("utf-8")
    enabled_hash = sha256_bytes(enabled_bytes)
    disabled_hash = sha256_bytes(disabled_bytes)
    initial_write_at = datetime.now(timezone.utc)
    if atomic_replace_bytes(config_path, enabled_bytes) != enabled_hash:
        raise RuntimeError("initial enabled config hash verification failed")
    files_before = inventory_files(codex_home)

    executable = resolve_native_codex_executable(codex_executable)
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
    creation_flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    started_at = datetime.now(timezone.utc)
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
        creationflags=creation_flags,
    )
    stdout_queue: queue.Queue[str | None] = queue.Queue()
    stderr_lines: list[str] = []

    def read_stdout() -> None:
        assert process.stdout is not None
        for line in process.stdout:
            stdout_queue.put(line)
        stdout_queue.put(None)

    def read_stderr() -> None:
        assert process.stderr is not None
        for line in process.stderr:
            if line.strip():
                stderr_lines.append(line.rstrip("\r\n"))

    stdout_thread = threading.Thread(target=read_stdout, daemon=True)
    stderr_thread = threading.Thread(target=read_stderr, daemon=True)
    stdout_thread.start()
    stderr_thread.start()

    deadline = time.monotonic() + timeout_seconds
    messages: list[dict[str, Any]] = []
    responses: dict[int, dict[str, Any]] = {}
    thread_ids: dict[str, str] = {}
    failure: BaseException | None = None
    app_server_graceful_shutdown_timed_out = False
    app_server_kill_sent = False
    disabled_write_at: datetime | None = None
    restored_write_at: datetime | None = None
    restoration_attempted_in_finally = False
    restoration_succeeded = False
    restoration_failure: str | None = None

    def send(request: dict[str, Any]) -> dict[str, Any]:
        assert process.stdin is not None
        request_id = request.get("id")
        if not isinstance(request_id, int):
            raise RuntimeError("probe request omitted integer id")
        process.stdin.write(json.dumps(request, separators=(",", ":")) + "\n")
        process.stdin.flush()
        response = wait_for_response(stdout_queue, request_id, deadline, messages)
        responses[request_id] = response
        return response

    def require_success(
        response: dict[str, Any],
        method: str,
    ) -> dict[str, Any]:
        if "error" in response:
            raise RuntimeError(f"{method} failed: {response['error']}")
        return response

    try:
        initialize = send(
            {
                "id": 0,
                "method": "initialize",
                "params": {
                    "clientInfo": {
                        "name": "agent_autonomy_harness_mcp_reload_probe",
                        "title": "Agent Autonomy Harness MCP Reload Probe",
                        "version": "1.0.0",
                    }
                },
            }
        )
        require_success(initialize, "initialize")
        initialize_result = initialize.get("result")
        if not isinstance(initialize_result, dict):
            raise RuntimeError("initialize result is not an object")
        actual_home = Path(str(initialize_result.get("codexHome"))).resolve()
        if os.path.normcase(str(actual_home)) != os.path.normcase(str(codex_home)):
            raise RuntimeError("app-server used an unexpected Codex home")
        assert process.stdin is not None
        process.stdin.write(json.dumps({"method": "initialized"}) + "\n")
        process.stdin.flush()

        thread_a_response = require_success(
            send(build_thread_start_request(1, workspace, "a-enabled-baseline")),
            "thread/start A",
        )
        thread_ids["a"] = extract_thread_id(thread_a_response)
        require_success(send(build_status_request(2, thread_ids["a"])), "status A")
        require_success(
            send(build_tool_request(3, thread_ids["a"], "a-enabled-baseline")),
            "tool A baseline",
        )

        disabled_write_at = datetime.now(timezone.utc)
        if atomic_replace_bytes(config_path, disabled_bytes) != disabled_hash:
            raise RuntimeError("disabled config hash verification failed")
        require_success(
            send({"id": 4, "method": "config/mcpServer/reload", "params": None}),
            "disable reload",
        )
        require_success(
            send(build_status_request(5, thread_ids["a"])),
            "disabled status A",
        )
        send(build_tool_request(6, thread_ids["a"], "a-after-disable-reload"))

        thread_b_response = require_success(
            send(build_thread_start_request(7, workspace, "b-disabled-new-thread")),
            "thread/start B",
        )
        thread_ids["b"] = extract_thread_id(thread_b_response)
        require_success(
            send(build_status_request(8, thread_ids["b"])),
            "disabled status B",
        )
        send(build_tool_request(9, thread_ids["b"], "b-disabled-new-thread"))

        restored_write_at = datetime.now(timezone.utc)
        if atomic_replace_bytes(config_path, enabled_bytes) != enabled_hash:
            raise RuntimeError("enabled config restoration hash verification failed")
        require_success(
            send({"id": 10, "method": "config/mcpServer/reload", "params": None}),
            "re-enable reload",
        )
        require_success(
            send(build_status_request(11, thread_ids["b"])),
            "re-enabled status B",
        )
        send(build_tool_request(12, thread_ids["b"], "b-after-reenable-reload"))

        thread_c_response = require_success(
            send(build_thread_start_request(13, workspace, "c-reenabled-new-thread")),
            "thread/start C",
        )
        thread_ids["c"] = extract_thread_id(thread_c_response)
        require_success(
            send(build_status_request(14, thread_ids["c"])),
            "enabled status C",
        )
        require_success(
            send(build_tool_request(15, thread_ids["c"], "c-reenabled-new-thread")),
            "tool C re-enabled",
        )

        for request_id, label in ((16, "a"), (17, "b"), (18, "c")):
            require_success(
                send(
                    {
                        "id": request_id,
                        "method": "thread/unsubscribe",
                        "params": {"threadId": thread_ids[label]},
                    }
                ),
                f"unsubscribe {label.upper()}",
            )
    except BaseException as error:
        failure = error
    finally:
        restoration_attempted_in_finally = True
        try:
            restoration_succeeded = (
                atomic_replace_bytes(config_path, enabled_bytes) == enabled_hash
            )
        except BaseException as error:
            restoration_failure = f"{type(error).__name__}: {error}"
            if failure is None:
                failure = error
        if restored_write_at is None:
            restored_write_at = datetime.now(timezone.utc)
        if process.stdin is not None and not process.stdin.closed:
            process.stdin.close()
        if process.poll() is None:
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                app_server_graceful_shutdown_timed_out = True
                app_server_kill_sent = True
                process.kill()
                process.wait(timeout=5)
        stdout_thread.join(timeout=1)
        stderr_thread.join(timeout=1)
        drain_stdout_queue(stdout_queue, messages)

    events_before_cleanup = load_events(event_log)
    started_instances = {
        str(event["instanceId"]): int(event["pid"])
        for event in events_before_cleanup
        if event.get("event") == "instance-start"
        and isinstance(event.get("instanceId"), str)
        and isinstance(event.get("pid"), int)
    }
    naturally_stopped_instance_ids = sorted(
        {
            str(event["instanceId"])
            for event in events_before_cleanup
            if event.get("event") == "instance-stop"
            and isinstance(event.get("instanceId"), str)
        }
    )
    unclosed_instance_ids = sorted(
        set(started_instances) - set(naturally_stopped_instance_ids)
    )
    cleanup_target_instance_ids = sorted(
        instance_id
        for instance_id in unclosed_instance_ids
        if process_exists(started_instances[instance_id])
    )
    pids_present_before_harness_cleanup = sorted(
        {
            started_instances[instance_id]
            for instance_id in cleanup_target_instance_ids
            if process_exists(started_instances[instance_id])
        }
    )
    cleanup_marker_created = False
    if cleanup_target_instance_ids:
        cleanup_marker.write_text(
            f"{PROBE_ID}\n",
            encoding="utf-8",
            newline="\n",
        )
        cleanup_marker_created = True
    marker_deadline = time.monotonic() + 5
    cleanup_acknowledged_instance_ids: list[str] = []
    while time.monotonic() < marker_deadline:
        current_events = load_events(event_log)
        cleanup_acknowledged_instance_ids = sorted(
            {
                str(event["instanceId"])
                for event in current_events
                if event.get("event") == "harness-cleanup-marker-observed"
                and isinstance(event.get("instanceId"), str)
            }
        )
        if set(cleanup_target_instance_ids).issubset(
            cleanup_acknowledged_instance_ids
        ):
            break
        time.sleep(0.05)
    sentinel_pids = sorted(set(started_instances.values()))
    pid_absent_after_marker = {
        pid: wait_for_process_exit(pid, 5) for pid in sentinel_pids
    }
    events_after_cleanup = load_events(event_log)
    cleanup_verified = set(cleanup_target_instance_ids).issubset(
        cleanup_acknowledged_instance_ids
    ) and all(pid_absent_after_marker.values())
    if failure is None and not cleanup_verified:
        failure = RuntimeError(
            "Sentinel harness cleanup was not fully acknowledged and observed"
        )
    config_hash_after = sha256_bytes(config_path.read_bytes())
    files_after = inventory_files(codex_home)
    auth_paths = [
        item["path"]
        for item in files_after
        if str(item["path"]).lower().endswith("auth.json")
    ]
    external_network_attempt_lines = [
        line for line in stderr_lines if "https://" in line or "http://" in line
    ]

    if failure is not None:
        raise failure

    finished_at = datetime.now(timezone.utc)
    tool_calls_by_phase: dict[str, dict[str, Any]] = {}
    for request_id, phase in (
        (3, "aEnabledBaseline"),
        (6, "aAfterDisableReload"),
        (9, "bDisabledNewThread"),
        (12, "bAfterReenableReload"),
        (15, "cReenabledNewThread"),
    ):
        tool_calls_by_phase[phase] = summarize_tool_call(responses[request_id])

    return {
        "schema": 1,
        "id": PROBE_ID,
        "startedAt": started_at.isoformat(),
        "finishedAt": finished_at.isoformat(),
        "durationMilliseconds": round(
            (finished_at - started_at).total_seconds() * 1000
        ),
        "command": command,
        "requestMethods": [
            "initialize",
            "initialized",
            "thread/start:a",
            "mcpServerStatus/list:a:enabled",
            "mcpServer/tool/call:a:enabled",
            "config/mcpServer/reload:disable",
            "mcpServerStatus/list:a:after-disable-reload",
            "mcpServer/tool/call:a:after-disable-reload",
            "thread/start:b",
            "mcpServerStatus/list:b:disabled",
            "mcpServer/tool/call:b:disabled",
            "config/mcpServer/reload:reenable",
            "mcpServerStatus/list:b:after-reenable-reload",
            "mcpServer/tool/call:b:after-reenable-reload",
            "thread/start:c",
            "mcpServerStatus/list:c:reenabled",
            "mcpServer/tool/call:c:reenabled",
            "thread/unsubscribe:a",
            "thread/unsubscribe:b",
            "thread/unsubscribe:c",
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
                "atomicWriteAt": initial_write_at.isoformat(),
            },
            "disabled": {
                "sha256": disabled_hash,
                "bytes": len(disabled_bytes),
                "enabled": False,
                "atomicWriteAt": (
                    disabled_write_at.isoformat()
                    if disabled_write_at is not None
                    else None
                ),
            },
            "restored": {
                "sha256": config_hash_after,
                "bytes": len(config_path.read_bytes()),
                "enabled": True,
                "atomicWriteAt": (
                    restored_write_at.isoformat()
                    if restored_write_at is not None
                    else None
                ),
            },
            "disabledDiffersFromBefore": disabled_hash != enabled_hash,
            "restoredBytesEqualBefore": config_path.read_bytes() == enabled_bytes,
            "restorationAttemptedInFinally": restoration_attempted_in_finally,
            "restorationSucceeded": restoration_succeeded,
            "restorationFailure": restoration_failure,
            "currentUserConfigCopied": False,
        },
        "reloadResponses": {
            "disable": responses[4].get("result"),
            "reenable": responses[10].get("result"),
            "responseProvesCompletedActuation": False,
        },
        "statusByPhase": {
            "aEnabledBaseline": summarize_status(responses[2]),
            "aAfterDisableReload": summarize_status(responses[5]),
            "bDisabledNewThread": summarize_status(responses[8]),
            "bAfterReenableReload": summarize_status(responses[11]),
            "cReenabledNewThread": summarize_status(responses[14]),
        },
        "toolCallsByPhase": tool_calls_by_phase,
        "processObservation": {
            "sentinelInstanceCount": len(sentinel_pids),
            "sentinelPids": sentinel_pids,
            "naturalStopInstanceIdsBeforeHarnessCleanup": (
                naturally_stopped_instance_ids
            ),
            "instancesWithoutStopEventBeforeHarnessCleanup": (
                unclosed_instance_ids
            ),
            "harnessCleanupTargetInstanceIds": cleanup_target_instance_ids,
            "pidsPresentBeforeHarnessCleanup": (
                pids_present_before_harness_cleanup
            ),
            "cleanupMarkerCreated": cleanup_marker_created,
            "cleanupAcknowledgedInstanceIds": (
                cleanup_acknowledged_instance_ids
            ),
            "allCleanupTargetsAcknowledgedMarker": set(
                cleanup_target_instance_ids
            ).issubset(cleanup_acknowledged_instance_ids),
            "pidAbsentAfterMarker": pid_absent_after_marker,
            "cleanupVerified": cleanup_verified,
            "pidSignalCleanupUsed": False,
            "cleanupMarkerExitIsNaturalReleaseEvidence": False,
            "instanceAndCallEvents": events_after_cleanup,
        },
        "shutdownObservation": {
            "appServerReturnCode": process.returncode,
            "nativeAppServerExecutable": executable,
            "actualAppServerPidObserved": True,
            "actualAppServerPid": process.pid,
            "nativeAppServerGracefulShutdownTimedOut": (
                app_server_graceful_shutdown_timed_out
            ),
            "nativeAppServerHandleKillSent": app_server_kill_sent,
            "thirtyMinuteIdleUnloadExecuted": False,
        },
        "isolation": {
            "codexHome": codex_home.as_posix(),
            "workspace": workspace.as_posix(),
            "defaultCodexHomeRejected": True,
            "removedAccountEnvironmentKeysPresentBefore": removed_keys,
            "accountEnvironmentValuesRecorded": False,
            "authStateProduced": bool(auth_paths),
            "currentAuthCopied": False,
            "currentPluginsCopied": False,
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
            "provesNewThreadDisableIfBStatusAndCallAreAbsent": True,
            "provesNewThreadReenableIfCStatusAndCallSucceed": True,
            "provesSameThreadHotEnableDisable": False,
            "provesOldRuntimeRelease": False,
            "provesTaskLevelLeaseOrReferenceCount": False,
            "provesThirtyMinuteIdleUnload": False,
            "provesTaskEndImmediateRelease": False,
            "provesCrashRecovery": False,
            "provesStableResourceSavings": False,
            "provesNoNetworkTraffic": False,
            "provesDesktopOrCrossHostParity": False,
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
    parser.add_argument("--timeout-seconds", type=float, default=90)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    result = run_probe(
        arguments.codex_home,
        arguments.workspace,
        arguments.sentinel_script,
        arguments.codex_executable,
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
