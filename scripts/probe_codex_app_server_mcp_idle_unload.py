#!/usr/bin/env python3
"""Observe Codex app-server's documented inactive-thread unload path.

The probe uses an empty, explicitly supplied CODEX_HOME and one local Sentinel.
It starts no model turn and copies no account, Plugin, App, or user config state.
The default observation is intentionally short; a 30-minute claim requires an
explicit observation of at least 1,800 seconds plus the expected lifecycle
events. Cleanup uses the exact Popen handle and a probe-private Sentinel marker,
never a process-name scan or a PID-only signal.
"""

from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
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
        remaining_timeout,
        wait_for_response,
    )
    from .probe_codex_app_server_mcp_tool_call import (
        SERVER_NAME,
        build_initial_requests,
        build_isolated_config,
        extract_thread_id,
        extract_tool_payload,
        load_events,
        resolve_native_codex_executable,
    )
except ImportError:
    from probe_codex_app_server_mcp_status import (
        build_child_environment,
        build_command,
        decode_stdout_message,
        drain_stdout_queue,
        inventory_files,
        remaining_timeout,
        wait_for_response,
    )
    from probe_codex_app_server_mcp_tool_call import (
        SERVER_NAME,
        build_initial_requests,
        build_isolated_config,
        extract_thread_id,
        extract_tool_payload,
        load_events,
        resolve_native_codex_executable,
    )


PROBE_ID = "codex-app-server-isolated-mcp-idle-unload-v1"
DOCUMENTED_IDLE_SECONDS = 1_800.0

PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010
TH32CS_SNAPPROCESS = 0x00000002
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value


class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("cntUsage", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("th32DefaultHeapID", ctypes.c_size_t),
        ("th32ModuleID", wintypes.DWORD),
        ("cntThreads", wintypes.DWORD),
        ("th32ParentProcessID", wintypes.DWORD),
        ("pcPriClassBase", wintypes.LONG),
        ("dwFlags", wintypes.DWORD),
        ("szExeFile", wintypes.WCHAR * 260),
    ]


class PROCESS_MEMORY_COUNTERS_EX(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD),
        ("PageFaultCount", wintypes.DWORD),
        ("PeakWorkingSetSize", ctypes.c_size_t),
        ("WorkingSetSize", ctypes.c_size_t),
        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
        ("PagefileUsage", ctypes.c_size_t),
        ("PeakPagefileUsage", ctypes.c_size_t),
        ("PrivateUsage", ctypes.c_size_t),
    ]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _filetime_value(value: wintypes.FILETIME) -> int:
    return (int(value.dwHighDateTime) << 32) | int(value.dwLowDateTime)


def _parent_pid_windows(pid: int) -> int | None:
    kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
    snapshot = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if snapshot == INVALID_HANDLE_VALUE:
        return None
    entry = PROCESSENTRY32W()
    entry.dwSize = ctypes.sizeof(entry)
    try:
        if not kernel32.Process32FirstW(snapshot, ctypes.byref(entry)):
            return None
        while True:
            if int(entry.th32ProcessID) == pid:
                return int(entry.th32ParentProcessID)
            if not kernel32.Process32NextW(snapshot, ctypes.byref(entry)):
                return None
    finally:
        kernel32.CloseHandle(snapshot)


def snapshot_process(pid: int) -> dict[str, Any]:
    """Capture a read-only process identity and bounded resource sample."""

    observed_at = utc_now()
    if pid <= 0:
        return {"pid": pid, "observedAt": observed_at, "exists": False}
    if os.name != "nt":
        raise RuntimeError("the exact process identity probe currently requires Windows")

    kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return {"pid": pid, "observedAt": observed_at, "exists": False}
    image_path: str | None = None
    creation_time: int | None = None
    kernel_time: int | None = None
    user_time: int | None = None
    try:
        buffer = ctypes.create_unicode_buffer(32768)
        size = wintypes.DWORD(len(buffer))
        if kernel32.QueryFullProcessImageNameW(
            handle, 0, buffer, ctypes.byref(size)
        ):
            image_path = buffer.value
        created = wintypes.FILETIME()
        exited = wintypes.FILETIME()
        kernel = wintypes.FILETIME()
        user = wintypes.FILETIME()
        if kernel32.GetProcessTimes(
            handle,
            ctypes.byref(created),
            ctypes.byref(exited),
            ctypes.byref(kernel),
            ctypes.byref(user),
        ):
            creation_time = _filetime_value(created)
            kernel_time = _filetime_value(kernel)
            user_time = _filetime_value(user)
    finally:
        kernel32.CloseHandle(handle)

    working_set: int | None = None
    private_usage: int | None = None
    memory_handle = kernel32.OpenProcess(
        PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid
    )
    if memory_handle:
        counters = PROCESS_MEMORY_COUNTERS_EX()
        counters.cb = ctypes.sizeof(counters)
        try:
            if ctypes.windll.psapi.GetProcessMemoryInfo(  # type: ignore[attr-defined]
                memory_handle,
                ctypes.byref(counters),
                counters.cb,
            ):
                working_set = int(counters.WorkingSetSize)
                private_usage = int(counters.PrivateUsage)
        finally:
            kernel32.CloseHandle(memory_handle)

    return {
        "pid": pid,
        "observedAt": observed_at,
        "exists": True,
        "imagePath": image_path,
        "creationTime100ns": creation_time,
        "parentPid": _parent_pid_windows(pid),
        "workingSetBytes": working_set,
        "privateUsageBytes": private_usage,
        "kernelTime100ns": kernel_time,
        "userTime100ns": user_time,
    }


def process_identity_complete(snapshot: dict[str, Any]) -> bool:
    return (
        snapshot.get("exists") is True
        and isinstance(snapshot.get("pid"), int)
        and isinstance(snapshot.get("creationTime100ns"), int)
        and isinstance(snapshot.get("imagePath"), str)
        and bool(snapshot["imagePath"])
        and isinstance(snapshot.get("parentPid"), int)
    )


def same_process_identity(
    expected: dict[str, Any], observed: dict[str, Any]
) -> bool:
    if not process_identity_complete(expected) or not process_identity_complete(
        observed
    ):
        return False
    return (
        expected["pid"] == observed["pid"]
        and expected["creationTime100ns"] == observed["creationTime100ns"]
        and os.path.normcase(expected["imagePath"])
        == os.path.normcase(observed["imagePath"])
        and expected["parentPid"] == observed["parentPid"]
    )


def notification_thread_id(message: dict[str, Any]) -> str | None:
    params = message.get("params")
    if not isinstance(params, dict):
        return None
    direct = params.get("threadId")
    if isinstance(direct, str):
        return direct
    thread = params.get("thread")
    if isinstance(thread, dict) and isinstance(thread.get("id"), str):
        return thread["id"]
    return None


def collect_idle_observation(
    stdout_queue: queue.Queue[str | None],
    messages: list[dict[str, Any]],
    thread_id: str,
    sentinel_identity: dict[str, Any],
    observation_seconds: float,
    poll_seconds: float,
) -> dict[str, Any]:
    started_at = datetime.now(timezone.utc)
    started_mono = time.monotonic()
    deadline = started_mono + observation_seconds
    thread_closed_at: str | None = None
    sentinel_exit_at: str | None = None
    stdout_closed = False
    last_snapshot = sentinel_identity

    while time.monotonic() < deadline:
        timeout = min(poll_seconds, max(0.01, deadline - time.monotonic()))
        try:
            line = stdout_queue.get(timeout=timeout)
        except queue.Empty:
            line = ""
        if line is None:
            stdout_closed = True
            break
        if line and line.strip():
            message = decode_stdout_message(line, len(messages) + 1)
            messages.append(message)
            if (
                message.get("method") == "thread/closed"
                and notification_thread_id(message) == thread_id
                and thread_closed_at is None
            ):
                thread_closed_at = utc_now()

        observed = snapshot_process(int(sentinel_identity["pid"]))
        last_snapshot = observed
        if (
            observed.get("exists") is not True
            or not same_process_identity(sentinel_identity, observed)
        ):
            if sentinel_exit_at is None:
                sentinel_exit_at = utc_now()
            if thread_closed_at is not None:
                break

    finished_at = datetime.now(timezone.utc)
    return {
        "startedAt": started_at.isoformat(),
        "finishedAt": finished_at.isoformat(),
        "durationMilliseconds": round(
            (finished_at - started_at).total_seconds() * 1000
        ),
        "requestedObservationSeconds": observation_seconds,
        "pollSeconds": poll_seconds,
        "threadClosedObserved": thread_closed_at is not None,
        "threadClosedAt": thread_closed_at,
        "sentinelExactIdentityAbsentObserved": sentinel_exit_at is not None,
        "sentinelExactIdentityAbsentAt": sentinel_exit_at,
        "stdoutClosedBeforeObservationFinished": stdout_closed,
        "finalSentinelSnapshot": last_snapshot,
    }


def classify_idle_observation(
    observation: dict[str, Any],
    natural_instance_stop_observed: bool,
    recovery_call_succeeded: bool,
) -> str:
    if observation.get("requestedObservationSeconds", 0) < DOCUMENTED_IDLE_SECONDS:
        return "short-preflight-does-not-test-thirty-minute-idle-unload"
    if observation.get("durationMilliseconds", 0) < DOCUMENTED_IDLE_SECONDS * 1000:
        return "blocked-observation-ended-before-thirty-minute-threshold"
    if observation.get("stdoutClosedBeforeObservationFinished") is True:
        return "blocked-app-server-exited-before-idle-observation"
    if observation.get("threadClosedObserved") is not True:
        return "not-observed-thread-remained-loaded-after-idle-window"
    if observation.get("sentinelExactIdentityAbsentObserved") is not True:
        return "partial-thread-closed-sentinel-exit-unproved"
    if not natural_instance_stop_observed:
        return "partial-process-absent-natural-sentinel-stop-event-missing"
    if not recovery_call_succeeded:
        return "partial-idle-unload-observed-recovery-call-failed"
    return "observed-single-host-sentinel-idle-unload-and-new-thread-recovery"


def _send(
    process: subprocess.Popen[str],
    request: dict[str, Any],
) -> None:
    if process.stdin is None or process.stdin.closed:
        raise RuntimeError("app-server stdin is unavailable")
    process.stdin.write(json.dumps(request, separators=(",", ":")) + "\n")
    process.stdin.flush()


def _request(
    process: subprocess.Popen[str],
    stdout_queue: queue.Queue[str | None],
    messages: list[dict[str, Any]],
    request: dict[str, Any],
    deadline: float,
) -> dict[str, Any]:
    _send(process, request)
    response = wait_for_response(
        stdout_queue, int(request["id"]), deadline, messages
    )
    if "error" in response:
        raise RuntimeError(f"{request['method']} failed: {response['error']}")
    return response


def _event_log_sha256(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def run_probe(
    codex_home: Path,
    workspace: Path,
    sentinel_script: Path,
    codex_executable: str | None,
    idle_observation_seconds: float,
    poll_seconds: float,
    request_timeout_seconds: float,
) -> dict[str, Any]:
    if os.name != "nt":
        raise RuntimeError("the idle-unload lifecycle probe currently requires Windows")
    if idle_observation_seconds < 0:
        raise ValueError("idle observation seconds must be non-negative")
    if poll_seconds <= 0:
        raise ValueError("poll seconds must be positive")

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
    config_path.write_text(
        build_isolated_config(
            Path(sys.executable),
            sentinel_script,
            event_log,
            cleanup_marker=cleanup_marker,
        ),
        encoding="utf-8",
        newline="\n",
    )
    config_hash_before = hashlib.sha256(config_path.read_bytes()).hexdigest()
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
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    app_server_identity = snapshot_process(process.pid)
    expected_executable = str(Path(executable).resolve())
    if (
        not process_identity_complete(app_server_identity)
        or os.path.normcase(str(app_server_identity.get("imagePath")))
        != os.path.normcase(expected_executable)
    ):
        process.kill()
        process.wait(timeout=5)
        raise RuntimeError("native app-server exact process identity could not be bound")

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

    messages: list[dict[str, Any]] = []
    sentinel_identities: dict[str, dict[str, Any]] = {}
    cleanup_marker_written = False
    app_server_kill_sent = False
    recovery_call_succeeded = False
    idle_observation: dict[str, Any] | None = None
    natural_first_stop_during_idle = False
    first_thread_id: str | None = None
    second_thread_id: str | None = None
    first_payload: dict[str, Any] | None = None
    second_payload: dict[str, Any] | None = None
    try:
        deadline = time.monotonic() + request_timeout_seconds
        initial = build_initial_requests(workspace)
        initialize_response = _request(
            process, stdout_queue, messages, initial[0], deadline
        )
        initialize_result = initialize_response.get("result")
        if not isinstance(initialize_result, dict):
            raise RuntimeError("initialize result is not an object")
        if os.path.normcase(
            str(Path(str(initialize_result.get("codexHome"))).resolve())
        ) != os.path.normcase(str(codex_home)):
            raise RuntimeError("app-server used an unexpected Codex home")
        _send(process, initial[1])
        first_thread_response = _request(
            process, stdout_queue, messages, initial[2], deadline
        )
        first_thread_id = extract_thread_id(first_thread_response)

        first_call = _request(
            process,
            stdout_queue,
            messages,
            {
                "id": 2,
                "method": "mcpServer/tool/call",
                "params": {
                    "threadId": first_thread_id,
                    "server": SERVER_NAME,
                    "tool": "identity",
                    "arguments": {"probe": PROBE_ID, "phase": "before-idle"},
                },
            },
            deadline,
        )
        first_payload = extract_tool_payload(first_call)
        first_sentinel = snapshot_process(int(first_payload["pid"]))
        if (
            not process_identity_complete(first_sentinel)
            or first_sentinel.get("parentPid") != process.pid
            or os.path.normcase(str(first_sentinel.get("imagePath")))
            != os.path.normcase(str(Path(sys.executable).resolve()))
        ):
            raise RuntimeError("first Sentinel exact child identity could not be bound")
        sentinel_identities[str(first_payload["instanceId"])] = first_sentinel

        _request(
            process,
            stdout_queue,
            messages,
            {
                "id": 3,
                "method": "thread/unsubscribe",
                "params": {"threadId": first_thread_id},
            },
            deadline,
        )
        idle_observation = collect_idle_observation(
            stdout_queue,
            messages,
            first_thread_id,
            first_sentinel,
            idle_observation_seconds,
            poll_seconds,
        )
        natural_first_stop_during_idle = any(
            event.get("event") == "instance-stop"
            and event.get("instanceId") == str(first_payload["instanceId"])
            for event in load_events(event_log)
        )

        deadline = time.monotonic() + request_timeout_seconds
        second_thread_response = _request(
            process,
            stdout_queue,
            messages,
            {
                "id": 4,
                "method": "thread/start",
                "params": {
                    "cwd": workspace.as_posix(),
                    "ephemeral": True,
                    "approvalPolicy": "never",
                    "sandbox": "read-only",
                },
            },
            deadline,
        )
        second_thread_id = extract_thread_id(second_thread_response)
        second_call = _request(
            process,
            stdout_queue,
            messages,
            {
                "id": 5,
                "method": "mcpServer/tool/call",
                "params": {
                    "threadId": second_thread_id,
                    "server": SERVER_NAME,
                    "tool": "identity",
                    "arguments": {"probe": PROBE_ID, "phase": "after-idle"},
                },
            },
            deadline,
        )
        second_payload = extract_tool_payload(second_call)
        second_sentinel = snapshot_process(int(second_payload["pid"]))
        if (
            not process_identity_complete(second_sentinel)
            or second_sentinel.get("parentPid") != process.pid
            or os.path.normcase(str(second_sentinel.get("imagePath")))
            != os.path.normcase(str(Path(sys.executable).resolve()))
        ):
            raise RuntimeError("recovery Sentinel exact child identity could not be bound")
        sentinel_identities[str(second_payload["instanceId"])] = second_sentinel
        recovery_call_succeeded = True
        _request(
            process,
            stdout_queue,
            messages,
            {
                "id": 6,
                "method": "thread/unsubscribe",
                "params": {"threadId": second_thread_id},
            },
            deadline,
        )
    finally:
        if process.stdin is not None and not process.stdin.closed:
            process.stdin.close()
        if process.poll() is None:
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                app_server_kill_sent = True
                process.kill()
                process.wait(timeout=5)
        cleanup_marker.write_text("harness cleanup\n", encoding="utf-8")
        cleanup_marker_written = True
        cleanup_deadline = time.monotonic() + 10
        while time.monotonic() < cleanup_deadline:
            if all(
                not same_process_identity(identity, snapshot_process(int(identity["pid"])))
                for identity in sentinel_identities.values()
            ):
                break
            time.sleep(0.05)
        stdout_thread.join(timeout=1)
        stderr_thread.join(timeout=1)
        drain_stdout_queue(stdout_queue, messages)

    events = load_events(event_log)
    first_instance_id = (
        str(first_payload.get("instanceId")) if isinstance(first_payload, dict) else None
    )
    natural_first_stop_by_end_of_probe = any(
        event.get("event") == "instance-stop"
        and event.get("instanceId") == first_instance_id
        for event in events
    )
    result_class = classify_idle_observation(
        idle_observation or {},
        natural_first_stop_during_idle,
        recovery_call_succeeded,
    )
    config_hash_after = hashlib.sha256(config_path.read_bytes()).hexdigest()
    files_after = inventory_files(codex_home)
    auth_paths = [
        item["path"]
        for item in files_after
        if str(item["path"]).lower().endswith("auth.json")
    ]
    if auth_paths:
        raise RuntimeError(f"isolated probe unexpectedly produced auth state: {auth_paths}")
    finished_at = datetime.now(timezone.utc)

    final_identity_checks = {
        instance_id: {
            "expected": identity,
            "observedAfterCleanup": snapshot_process(int(identity["pid"])),
        }
        for instance_id, identity in sentinel_identities.items()
    }
    all_owned_sentinels_absent = all(
        not same_process_identity(
            value["expected"], value["observedAfterCleanup"]
        )
        for value in final_identity_checks.values()
    )
    app_server_final = snapshot_process(process.pid)
    app_server_exact_identity_absent = not same_process_identity(
        app_server_identity, app_server_final
    )

    return {
        "schema": 1,
        "id": PROBE_ID,
        "startedAt": started_at.isoformat(),
        "finishedAt": finished_at.isoformat(),
        "durationMilliseconds": round(
            (finished_at - started_at).total_seconds() * 1000
        ),
        "resultClass": result_class,
        "command": command,
        "requestMethods": [
            "initialize",
            "initialized",
            "thread/start",
            "mcpServer/tool/call",
            "thread/unsubscribe",
            "thread/start",
            "mcpServer/tool/call",
            "thread/unsubscribe",
        ],
        "appServer": {
            "identityBefore": app_server_identity,
            "identityAfter": app_server_final,
            "exactIdentityAbsentAfterCleanup": app_server_exact_identity_absent,
            "returnCode": process.returncode,
            "killSentThroughOwnedPopenHandle": app_server_kill_sent,
        },
        "firstThread": {
            "id": first_thread_id,
            "ephemeralRequested": True,
            "modelTurnStarted": False,
            "toolPayload": first_payload,
            "sentinelIdentity": (
                sentinel_identities.get(first_instance_id)
                if first_instance_id is not None
                else None
            ),
            "idleObservation": idle_observation,
            "naturalInstanceStopEventObservedDuringIdleObservation": (
                natural_first_stop_during_idle
            ),
        },
        "recoveryThread": {
            "id": second_thread_id,
            "ephemeralRequested": True,
            "modelTurnStarted": False,
            "toolPayload": second_payload,
            "callSucceeded": recovery_call_succeeded,
            "newInstanceIdObserved": (
                isinstance(first_payload, dict)
                and isinstance(second_payload, dict)
                and first_payload.get("instanceId") != second_payload.get("instanceId")
            ),
        },
        "cleanup": {
            "marker": cleanup_marker.as_posix(),
            "markerWritten": cleanup_marker_written,
            "pidOnlySignalUsed": False,
            "processNameScanOrTerminationUsed": False,
            "firstInstanceStopEventObservedByEndOfProbe": (
                natural_first_stop_by_end_of_probe
            ),
            "sentinelIdentityChecks": final_identity_checks,
            "allOwnedSentinelExactIdentitiesAbsent": all_owned_sentinels_absent,
        },
        "isolation": {
            "codexHome": codex_home.as_posix(),
            "workspace": workspace.as_posix(),
            "defaultCodexHomeRejected": True,
            "removedAccountEnvironmentKeysPresentBefore": removed_keys,
            "accountEnvironmentValuesRecorded": False,
            "currentConfigCopied": False,
            "currentAuthCopied": False,
            "currentPluginsCopied": False,
            "disabledDiscoveryFeatures": [
                "plugins",
                "remote_plugin",
                "apps",
                "plugin_sharing",
            ],
            "authStateProduced": False,
            "configHashBefore": config_hash_before,
            "configHashAfter": config_hash_after,
            "configUnchangedDuringProbe": config_hash_before == config_hash_after,
            "filesBefore": files_before,
            "filesAfter": files_after,
        },
        "eventLog": {
            "path": event_log.as_posix(),
            "sha256": _event_log_sha256(event_log),
            "events": events,
        },
        "stdoutMessageCount": len(messages),
        "stderrLines": stderr_lines,
        "claimBoundary": {
            "provesSameThreadHotEnableDisable": False,
            "provesTaskEndImmediateRelease": False,
            "provesPublicLeaseOrReferenceCountApi": False,
            "provesThirtyMinuteIdleUnload": (
                result_class
                == "observed-single-host-sentinel-idle-unload-and-new-thread-recovery"
            ),
            "provesNewThreadRecoveryForThisSentinelRun": recovery_call_succeeded,
            "provesStableResourceSavings": False,
            "provesCrashRecovery": False,
            "provesDesktopPluginOrCrossHostParity": False,
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
    parser.add_argument("--codex", dest="codex_executable")
    parser.add_argument(
        "--idle-observation-seconds",
        type=float,
        default=5.0,
        help=(
            "Keep app-server alive without thread activity for this duration. "
            "A 30-minute claim requires at least 1800 seconds."
        ),
    )
    parser.add_argument("--poll-seconds", type=float, default=1.0)
    parser.add_argument("--request-timeout-seconds", type=float, default=60.0)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    result = run_probe(
        arguments.codex_home,
        arguments.workspace,
        arguments.sentinel_script,
        arguments.codex_executable,
        arguments.idle_observation_seconds,
        arguments.poll_seconds,
        arguments.request_timeout_seconds,
    )
    text = json.dumps(result, indent=2, ensure_ascii=False)
    if arguments.output is not None:
        output = arguments.output.resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text + "\n", encoding="utf-8", newline="\n")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
