#!/usr/bin/env python3
"""Call a local MCP Sentinel through Codex app-server in an isolated home.

This probe starts no model turn and uses no account. It creates only an
explicitly supplied isolated CODEX_HOME, its config, an ephemeral thread, and a
local Sentinel process. Closing app-server is a harness shutdown observation,
not evidence of the 30-minute idle-unload contract.
"""

from __future__ import annotations

import argparse
import ctypes
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import queue
import signal
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
        resolve_codex_executable,
        wait_for_response,
    )
except ImportError:
    from probe_codex_app_server_mcp_status import (
        build_child_environment,
        build_command,
        decode_stdout_message,
        drain_stdout_queue,
        inventory_files,
        remaining_timeout,
        resolve_codex_executable,
        wait_for_response,
    )


PROBE_ID = "codex-app-server-isolated-mcp-tool-call-v1"
SERVER_NAME = "lifecycle_sentinel"


def toml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def build_isolated_config(
    python_executable: Path,
    sentinel_script: Path,
    event_log: Path,
    enabled: bool = True,
    cleanup_marker: Path | None = None,
) -> str:
    arguments = [
        "-B",
        str(sentinel_script.resolve()),
        "--event-log",
        str(event_log.resolve()),
    ]
    if cleanup_marker is not None:
        arguments.extend(("--cleanup-marker", str(cleanup_marker.resolve())))
    lines = [
        f"[mcp_servers.{SERVER_NAME}]",
        f"command = {toml_string(str(python_executable.resolve()))}",
        "args = [",
    ]
    lines.extend(
        f"  {toml_string(argument)}{',' if index < len(arguments) - 1 else ''}"
        for index, argument in enumerate(arguments)
    )
    lines.extend(
        (
            "]",
            "startup_timeout_sec = 10",
            "tool_timeout_sec = 15",
            f"enabled = {'true' if enabled else 'false'}",
            "",
        )
    )
    return "\n".join(lines)


def resolve_native_codex_executable(explicit: str | None) -> str:
    """Resolve the real Codex binary instead of a Windows command wrapper."""

    resolved = Path(resolve_codex_executable(explicit))
    if os.name != "nt" or resolved.suffix.lower() == ".exe":
        return str(resolved)
    if resolved.suffix.lower() not in {".cmd", ".bat"}:
        raise RuntimeError(
            f"Codex launcher is not a native executable: {resolved}"
        )
    package_root = (
        resolved.parent
        / "node_modules"
        / "@openai"
        / "codex"
        / "node_modules"
    )
    candidates = sorted(
        path.resolve()
        for path in package_root.glob(
            "@openai/codex-win32-*/vendor/*/bin/codex.exe"
        )
        if path.is_file()
    )
    if len(candidates) != 1:
        raise RuntimeError(
            "unable to resolve exactly one bundled native Codex executable "
            f"from wrapper {resolved}; found {len(candidates)}"
        )
    return str(candidates[0])


def build_initial_requests(workspace: Path) -> list[dict[str, Any]]:
    return [
        {
            "id": 0,
            "method": "initialize",
            "params": {
                "clientInfo": {
                    "name": "agent_autonomy_harness_mcp_lifecycle_probe",
                    "title": "Agent Autonomy Harness MCP Lifecycle Probe",
                    "version": "1.0.0",
                }
            },
        },
        {"method": "initialized"},
        {
            "id": 1,
            "method": "thread/start",
            "params": {
                "cwd": workspace.resolve().as_posix(),
                "ephemeral": True,
                "approvalPolicy": "never",
                "sandbox": "read-only",
            },
        },
    ]


def build_thread_requests(thread_id: str) -> list[dict[str, Any]]:
    return [
        {
            "id": 2,
            "method": "mcpServerStatus/list",
            "params": {"threadId": thread_id, "detail": "full", "limit": 100},
        },
        {
            "id": 3,
            "method": "mcpServer/tool/call",
            "params": {
                "threadId": thread_id,
                "server": SERVER_NAME,
                "tool": "identity",
                "arguments": {"probe": PROBE_ID},
            },
        },
        {
            "id": 4,
            "method": "thread/unsubscribe",
            "params": {"threadId": thread_id},
        },
    ]


def load_events(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    events: list[dict[str, Any]] = []
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise RuntimeError(f"sentinel event {line_number} is not an object")
        events.append(value)
    return events


def process_exists(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        process_query_limited_information = 0x1000
        handle = ctypes.windll.kernel32.OpenProcess(  # type: ignore[attr-defined]
            process_query_limited_information, False, pid
        )
        if not handle:
            return False
        ctypes.windll.kernel32.CloseHandle(handle)  # type: ignore[attr-defined]
        return True
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def wait_for_process_exit(pid: int, timeout_seconds: float) -> bool:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if not process_exists(pid):
            return True
        time.sleep(0.05)
    return not process_exists(pid)


def extract_thread_id(response: dict[str, Any]) -> str:
    result = response.get("result")
    thread = result.get("thread") if isinstance(result, dict) else None
    thread_id = thread.get("id") if isinstance(thread, dict) else None
    if not isinstance(thread_id, str) or not thread_id:
        raise RuntimeError("thread/start response omitted thread.id")
    return thread_id


def extract_tool_payload(response: dict[str, Any]) -> dict[str, Any]:
    if "error" in response:
        raise RuntimeError(f"mcpServer/tool/call failed: {response['error']}")
    result = response.get("result")
    if not isinstance(result, dict):
        raise RuntimeError("mcpServer/tool/call result is not an object")
    structured = result.get("structuredContent")
    if isinstance(structured, dict):
        return structured
    content = result.get("content")
    if (
        isinstance(content, list)
        and content
        and isinstance(content[0], dict)
        and isinstance(content[0].get("text"), str)
    ):
        value = json.loads(content[0]["text"])
        if isinstance(value, dict):
            return value
    raise RuntimeError("mcpServer/tool/call omitted Sentinel identity payload")


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
    config_path = codex_home / "config.toml"
    config_text = build_isolated_config(Path(sys.executable), sentinel_script, event_log)
    config_path.write_text(config_text, encoding="utf-8", newline="\n")
    config_hash_before = __import__("hashlib").sha256(config_path.read_bytes()).hexdigest()
    files_before = inventory_files(codex_home)

    executable = resolve_codex_executable(codex_executable)
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
    messages: list[dict[str, Any]] = []
    deadline = time.monotonic() + timeout_seconds
    sentinel_pid: int | None = None
    sentinel_alive_after_call = False
    app_server_graceful_shutdown_timed_out = False
    app_server_kill_sent = False
    try:
        assert process.stdin is not None
        initial = build_initial_requests(workspace)
        process.stdin.write(json.dumps(initial[0], separators=(",", ":")) + "\n")
        process.stdin.flush()
        initialize_response = wait_for_response(
            stdout_queue, 0, deadline, messages
        )
        if "error" in initialize_response:
            raise RuntimeError(f"initialize failed: {initialize_response['error']}")
        initialize_result = initialize_response.get("result")
        if not isinstance(initialize_result, dict):
            raise RuntimeError("initialize result is not an object")
        if os.path.normcase(
            str(Path(str(initialize_result.get("codexHome"))).resolve())
        ) != os.path.normcase(str(codex_home)):
            raise RuntimeError("app-server used an unexpected Codex home")

        for request in initial[1:]:
            process.stdin.write(json.dumps(request, separators=(",", ":")) + "\n")
        process.stdin.flush()
        thread_response = wait_for_response(stdout_queue, 1, deadline, messages)
        if "error" in thread_response:
            raise RuntimeError(f"thread/start failed: {thread_response['error']}")
        thread_id = extract_thread_id(thread_response)

        responses: dict[int, dict[str, Any]] = {}
        for request in build_thread_requests(thread_id):
            process.stdin.write(json.dumps(request, separators=(",", ":")) + "\n")
            process.stdin.flush()
            response = wait_for_response(
                stdout_queue, int(request["id"]), deadline, messages
            )
            responses[int(request["id"])] = response
            if "error" in response:
                raise RuntimeError(
                    f"{request['method']} failed: {response['error']}"
                )

        tool_payload = extract_tool_payload(responses[3])
        sentinel_pid_value = tool_payload.get("pid")
        if not isinstance(sentinel_pid_value, int):
            raise RuntimeError("Sentinel payload omitted integer pid")
        sentinel_pid = sentinel_pid_value
        sentinel_alive_after_call = process_exists(sentinel_pid)

        process.stdin.close()
        try:
            process.wait(timeout=remaining_timeout(deadline))
        except subprocess.TimeoutExpired:
            app_server_graceful_shutdown_timed_out = True
            app_server_kill_sent = True
            process.kill()
            process.wait(timeout=5)
    except BaseException:
        if process.stdin is not None and not process.stdin.closed:
            process.stdin.close()
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)
        stdout_thread.join(timeout=1)
        stderr_thread.join(timeout=1)
        raise
    stdout_thread.join(timeout=1)
    stderr_thread.join(timeout=1)
    drain_stdout_queue(stdout_queue, messages)
    if process.returncode != 0 and not app_server_graceful_shutdown_timed_out:
        raise RuntimeError(
            f"app-server exited {process.returncode}: {'; '.join(stderr_lines)}"
        )

    events = load_events(event_log)
    sentinel_pids = sorted(
        {
            event["pid"]
            for event in events
            if isinstance(event.get("pid"), int)
            and event.get("event") == "instance-start"
        }
    )
    sentinel_processes_alive_after_app_server_shutdown = [
        pid for pid in sentinel_pids if process_exists(pid)
    ]
    cleanup_signal_pids: list[int] = []
    for pid in sentinel_processes_alive_after_app_server_shutdown:
        cleanup_signal_pids.append(pid)
        os.kill(pid, signal.SIGTERM)
    sentinel_exit_after_cleanup = {
        pid: wait_for_process_exit(pid, 5) for pid in sentinel_pids
    }
    sentinel_processes_exited_after_cleanup = all(
        sentinel_exit_after_cleanup.values()
    )
    graceful_stop_pids = sorted(
        {
            event["pid"]
            for event in events
            if isinstance(event.get("pid"), int)
            and event.get("event") == "instance-stop"
        }
    )
    config_hash_after = __import__("hashlib").sha256(config_path.read_bytes()).hexdigest()
    files_after = inventory_files(codex_home)
    auth_paths = [
        item["path"]
        for item in files_after
        if str(item["path"]).lower().endswith("auth.json")
    ]
    if auth_paths:
        raise RuntimeError(f"isolated probe unexpectedly produced auth state: {auth_paths}")
    finished_at = datetime.now(timezone.utc)
    external_network_attempt_lines = [
        line
        for line in stderr_lines
        if "https://" in line or "http://" in line
    ]

    by_id = {message.get("id"): message for message in messages if "id" in message}
    tool_payload = extract_tool_payload(by_id[3])
    status_result = by_id[2].get("result")
    unsubscribe_result = by_id[4].get("result")
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
            "thread/start",
            "mcpServerStatus/list",
            "mcpServer/tool/call",
            "thread/unsubscribe",
        ],
        "thread": {
            "id": thread_id,
            "ephemeralRequested": True,
            "modelTurnStarted": False,
        },
        "mcpStatus": status_result,
        "toolCall": {
            "server": tool_payload.get("server"),
            "tool": tool_payload.get("tool"),
            "pid": sentinel_pid,
            "instanceId": tool_payload.get("instanceId"),
            "callId": tool_payload.get("callId"),
            "sentinelAliveAfterCall": sentinel_alive_after_call,
        },
        "unsubscribe": unsubscribe_result,
        "shutdownObservation": {
            "appServerReturnCode": process.returncode,
            "appServerGracefulShutdownTimedOut": (
                app_server_graceful_shutdown_timed_out
            ),
            "appServerKillSent": app_server_kill_sent,
            "sentinelInstanceCount": len(sentinel_pids),
            "sentinelPids": sentinel_pids,
            "toolCallSentinelPid": sentinel_pid,
            "auxiliarySentinelPids": [
                pid for pid in sentinel_pids if pid != sentinel_pid
            ],
            "sentinelProcessesAliveAfterAppServerShutdown": (
                sentinel_processes_alive_after_app_server_shutdown
            ),
            "sentinelCleanupSignalPids": cleanup_signal_pids,
            "allSentinelProcessesExitedAfterCleanup": (
                sentinel_processes_exited_after_cleanup
            ),
            "sentinelExitAfterCleanup": sentinel_exit_after_cleanup,
            "sentinelGracefulStopEventPids": graceful_stop_pids,
            "provesThirtyMinuteIdleUnload": False,
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
            "applicationLogExternalNetworkAttemptObserved": bool(
                external_network_attempt_lines
            ),
            "applicationLogExternalNetworkAttemptLines": (
                external_network_attempt_lines
            ),
            "configHashBefore": config_hash_before,
            "configHashAfter": config_hash_after,
            "configUnchangedDuringProbe": config_hash_before == config_hash_after,
            "filesBefore": files_before,
            "filesAfter": files_after,
        },
        "sentinelEvents": events,
        "stdoutMessageCount": len(messages),
        "stderrLines": stderr_lines,
        "claimBoundary": {
            "provesStableSchemaMethodExists": False,
            "provesDirectLocalMcpToolCall": True,
            "provesNoModelTurnRequiredForToolCall": True,
            "provesAccountLoginNotRequiredForThisLocalCall": True,
            "provesNoNetworkTraffic": False,
            "provesSameThreadHotEnableDisable": False,
            "provesTaskLevelLeaseOrReferenceCount": False,
            "provesThirtyMinuteIdleUnload": False,
            "provesCrashRecovery": False,
            "provesStableResourceSavings": False,
            "provesSingleRuntimeInstancePerConfiguredServer": False,
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
    parser.add_argument("--timeout-seconds", type=float, default=30)
    parser.add_argument(
        "--output",
        type=Path,
        help="Optionally write the normalized result to this explicit path.",
    )
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
