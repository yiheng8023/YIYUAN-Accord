#!/usr/bin/env python3
"""Compare isolated Codex app-server MCP startup profiles without a model turn.

Each profile gets a separate native app-server process, empty CODEX_HOME, and
ephemeral thread. The probe validates direct tool-call behavior only; it does
not call status discovery, reload config, or claim same-thread switching.
"""

from __future__ import annotations

import argparse
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
    from .probe_codex_app_server_mcp_idle_unload import (
        inventory_files,
        process_identity_complete,
        resolve_native_codex_executable,
        same_process_identity,
        snapshot_process,
        utc_now,
    )
    from .probe_codex_app_server_mcp_status import (
        build_child_environment,
        build_command,
        decode_stdout_message,
        drain_stdout_queue,
    )
    from .probe_codex_app_server_mcp_tool_call import (
        extract_thread_id,
        extract_tool_payload,
        toml_string,
    )
except ImportError:
    from probe_codex_app_server_mcp_idle_unload import (
        inventory_files,
        process_identity_complete,
        resolve_native_codex_executable,
        same_process_identity,
        snapshot_process,
        utc_now,
    )
    from probe_codex_app_server_mcp_status import (
        build_child_environment,
        build_command,
        decode_stdout_message,
        drain_stdout_queue,
    )
    from probe_codex_app_server_mcp_tool_call import (
        extract_thread_id,
        extract_tool_payload,
        toml_string,
    )


PROBE_ID = "codex-app-server-isolated-mcp-startup-profiles-v1"
SERVER_NAME = "lifecycle_sentinel"
PROFILES = {
    "full": {
        "enabled": True,
        "enabledTools": None,
        "disabledTools": None,
        "expectIdentity": True,
        "expectHold": True,
        "expectSentinel": True,
    },
    "filtered": {
        "enabled": True,
        "enabledTools": ["identity", "hold"],
        "disabledTools": ["hold"],
        "expectIdentity": True,
        "expectHold": False,
        "expectSentinel": True,
    },
    "disabled": {
        "enabled": False,
        "enabledTools": None,
        "disabledTools": None,
        "expectIdentity": False,
        "expectHold": False,
        "expectSentinel": False,
    },
}


def build_profile_config(
    python_executable: Path,
    sentinel_script: Path,
    event_log: Path,
    cleanup_marker: Path,
    profile: dict[str, Any],
) -> str:
    arguments = [
        "-B",
        str(sentinel_script.resolve()),
        "--event-log",
        str(event_log.resolve()),
        "--cleanup-marker",
        str(cleanup_marker.resolve()),
    ]
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
            f"enabled = {'true' if profile['enabled'] else 'false'}",
        )
    )
    if profile["enabledTools"] is not None:
        tools = ", ".join(toml_string(tool) for tool in profile["enabledTools"])
        lines.append(f"enabled_tools = [{tools}]")
    if profile["disabledTools"] is not None:
        tools = ", ".join(toml_string(tool) for tool in profile["disabledTools"])
        lines.append(f"disabled_tools = [{tools}]")
    lines.append("")
    return "\n".join(lines)


def _send(process: subprocess.Popen[str], request: dict[str, Any]) -> None:
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
    request_id = request.get("id")
    while time.monotonic() < deadline:
        remaining = deadline - time.monotonic()
        try:
            line = stdout_queue.get(timeout=max(0.01, remaining))
        except queue.Empty as exc:
            raise TimeoutError(f"request {request_id} timed out") from exc
        if line is None:
            raise RuntimeError("app-server stdout closed before response")
        if not line.strip():
            continue
        message = decode_stdout_message(line, len(messages) + 1)
        messages.append(message)
        if message.get("id") == request_id:
            return message
    raise TimeoutError(f"request {request_id} timed out")


def tool_call_succeeded(response: dict[str, Any]) -> bool:
    if "error" in response:
        return False
    result = response.get("result")
    return isinstance(result, dict) and result.get("isError") is not True


def event_log_rows(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            value = json.loads(line)
            if not isinstance(value, dict):
                raise RuntimeError("Sentinel event log row is not an object")
            rows.append(value)
    return rows


def sha256_file(path: Path) -> str | None:
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def classify_profile_result(
    profile_name: str,
    identity_succeeded: bool,
    hold_succeeded: bool,
    sentinel_bound: bool,
    config_unchanged: bool,
    auth_state_produced: bool,
    cleanup_safe: bool,
) -> bool:
    profile = PROFILES[profile_name]
    return (
        identity_succeeded is profile["expectIdentity"]
        and hold_succeeded is profile["expectHold"]
        and sentinel_bound is profile["expectSentinel"]
        and config_unchanged
        and not auth_state_produced
        and cleanup_safe
    )


def run_profile(
    profile_name: str,
    run_root: Path,
    sentinel_script: Path,
    codex_executable: str | None,
    request_timeout_seconds: float,
) -> dict[str, Any]:
    profile = PROFILES[profile_name]
    codex_home = (run_root / "codex-home").resolve()
    workspace = (run_root / "workspace").resolve()
    default_home = (Path.home() / ".codex").resolve()
    if os.path.normcase(str(codex_home)) == os.path.normcase(str(default_home)):
        raise RuntimeError("refusing to use the current default Codex home")
    if run_root.exists() and any(run_root.iterdir()):
        raise RuntimeError(f"profile root must be absent or empty: {run_root}")
    if not sentinel_script.is_file():
        raise RuntimeError(f"Sentinel script is missing: {sentinel_script}")
    codex_home.mkdir(parents=True, exist_ok=True)
    workspace.mkdir(parents=True, exist_ok=True)

    event_log = codex_home / "sentinel-events.jsonl"
    cleanup_marker = codex_home / "harness-cleanup.marker"
    config_path = codex_home / "config.toml"
    config_text = build_profile_config(
        Path(sys.executable),
        sentinel_script,
        event_log,
        cleanup_marker,
        profile,
    )
    config_path.write_text(config_text, encoding="utf-8", newline="\n")
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
    creation_flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    started_at = utc_now()
    started_mono = time.monotonic()
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
    app_identity = snapshot_process(process.pid)
    if not process_identity_complete(app_identity):
        process.kill()
        process.wait(timeout=5)
        raise RuntimeError("app-server exact process identity could not be bound")

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
    identity_response: dict[str, Any] = {}
    hold_response: dict[str, Any] = {}
    identity_payload: dict[str, Any] | None = None
    sentinel_identity: dict[str, Any] | None = None
    initialize_ms: int | None = None
    thread_start_ms: int | None = None
    first_call_ms: int | None = None
    thread_id: str | None = None
    app_server_kill_sent = False
    cleanup_marker_written = False
    try:
        deadline = time.monotonic() + request_timeout_seconds
        initialize = _request(
            process,
            stdout_queue,
            messages,
            {
                "id": 0,
                "method": "initialize",
                "params": {
                    "clientInfo": {"name": "agent-autonomy-harness", "version": "1"},
                    "capabilities": {},
                },
            },
            deadline,
        )
        if "error" in initialize:
            raise RuntimeError(f"initialize failed: {initialize['error']}")
        initialize_result = initialize.get("result")
        if not isinstance(initialize_result, dict):
            raise RuntimeError("initialize result is not an object")
        if os.path.normcase(
            str(Path(str(initialize_result.get("codexHome"))).resolve())
        ) != os.path.normcase(str(codex_home)):
            raise RuntimeError("app-server used an unexpected Codex home")
        initialize_ms = round((time.monotonic() - started_mono) * 1000)
        _send(process, {"method": "initialized", "params": {}})

        thread_response = _request(
            process,
            stdout_queue,
            messages,
            {
                "id": 1,
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
        thread_id = extract_thread_id(thread_response)
        thread_start_ms = round((time.monotonic() - started_mono) * 1000)

        identity_response = _request(
            process,
            stdout_queue,
            messages,
            {
                "id": 2,
                "method": "mcpServer/tool/call",
                "params": {
                    "threadId": thread_id,
                    "server": SERVER_NAME,
                    "tool": "identity",
                    "arguments": {"profile": profile_name},
                },
            },
            deadline,
        )
        first_call_ms = round((time.monotonic() - started_mono) * 1000)
        if tool_call_succeeded(identity_response):
            identity_payload = extract_tool_payload(identity_response)
            sentinel_identity = snapshot_process(int(identity_payload["pid"]))
            if (
                not process_identity_complete(sentinel_identity)
                or sentinel_identity.get("parentPid") != process.pid
                or os.path.normcase(str(sentinel_identity.get("imagePath")))
                != os.path.normcase(str(Path(sys.executable).resolve()))
            ):
                raise RuntimeError("Sentinel exact child identity could not be bound")

        hold_response = _request(
            process,
            stdout_queue,
            messages,
            {
                "id": 3,
                "method": "mcpServer/tool/call",
                "params": {
                    "threadId": thread_id,
                    "server": SERVER_NAME,
                    "tool": "hold",
                    "arguments": {"milliseconds": 0},
                },
            },
            deadline,
        )
        _request(
            process,
            stdout_queue,
            messages,
            {
                "id": 4,
                "method": "thread/unsubscribe",
                "params": {"threadId": thread_id},
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
        while (
            sentinel_identity is not None
            and time.monotonic() < cleanup_deadline
            and same_process_identity(
                sentinel_identity,
                snapshot_process(int(sentinel_identity["pid"])),
            )
        ):
            time.sleep(0.05)
        stdout_thread.join(timeout=1)
        stderr_thread.join(timeout=1)
        drain_stdout_queue(stdout_queue, messages)

    config_hash_after = hashlib.sha256(config_path.read_bytes()).hexdigest()
    files_after = inventory_files(codex_home)
    auth_state_produced = any(
        str(item["path"]).lower().endswith("auth.json") for item in files_after
    )
    events = event_log_rows(event_log)
    instance_ids = sorted(
        {
            str(event["instanceId"])
            for event in events
            if event.get("event") == "instance-start"
            and isinstance(event.get("instanceId"), str)
        }
    )
    sentinel_absent = (
        sentinel_identity is None
        or not same_process_identity(
            sentinel_identity,
            snapshot_process(int(sentinel_identity["pid"])),
        )
    )
    app_server_final = snapshot_process(process.pid)
    app_server_identity_absent = not same_process_identity(
        app_identity, app_server_final
    )
    identity_succeeded = tool_call_succeeded(identity_response)
    hold_succeeded = tool_call_succeeded(hold_response)
    sentinel_bound = sentinel_identity is not None
    cleanup_safe = (
        process.returncode is not None
        and sentinel_absent
        and app_server_identity_absent
    )
    accepted = classify_profile_result(
        profile_name,
        identity_succeeded,
        hold_succeeded,
        sentinel_bound,
        config_hash_before == config_hash_after,
        auth_state_produced,
        cleanup_safe,
    )
    return {
        "profile": profile_name,
        "accepted": accepted,
        "config": {
            "enabled": profile["enabled"],
            "enabledTools": profile["enabledTools"],
            "disabledTools": profile["disabledTools"],
            "sha256Before": config_hash_before,
            "sha256After": config_hash_after,
            "unchanged": config_hash_before == config_hash_after,
        },
        "timing": {
            "initializeMilliseconds": initialize_ms,
            "threadStartMilliseconds": thread_start_ms,
            "firstToolCallMilliseconds": first_call_ms,
        },
        "thread": {
            "id": thread_id,
            "ephemeralRequested": True,
            "approvalPolicy": "never",
            "sandbox": "read-only",
            "modelTurnStarted": False,
        },
        "calls": {
            "identity": {
                "succeeded": identity_succeeded,
                "error": identity_response.get("error"),
                "payload": identity_payload,
            },
            "hold": {
                "succeeded": hold_succeeded,
                "error": hold_response.get("error"),
            },
        },
        "process": {
            "appServerIdentity": app_identity,
            "sentinelIdentity": sentinel_identity,
            "sentinelEventInstanceIds": instance_ids,
            "sentinelEventInstanceCount": len(instance_ids),
            "sentinelExactIdentityAbsentAfterCleanup": sentinel_absent,
            "appServerExactIdentityAbsentAfterCleanup": app_server_identity_absent,
            "appServerReturnCode": process.returncode,
            "appServerKillSentThroughOwnedHandle": app_server_kill_sent,
            "pidOnlySignalUsed": False,
            "processNameScanOrTerminationUsed": False,
        },
        "isolation": {
            "codexHome": codex_home.as_posix(),
            "workspace": workspace.as_posix(),
            "currentConfigCopied": False,
            "currentAuthCopied": False,
            "currentPluginsCopied": False,
            "removedAccountEnvironmentKeysPresentBefore": removed_keys,
            "accountEnvironmentValuesRecorded": False,
            "authStateProduced": auth_state_produced,
            "filesBefore": files_before,
            "filesAfter": files_after,
        },
        "cleanup": {
            "markerWritten": cleanup_marker_written,
            "safe": cleanup_safe,
        },
        "eventLog": {
            "path": event_log.as_posix(),
            "sha256": sha256_file(event_log),
            "bytes": event_log.stat().st_size if event_log.is_file() else 0,
        },
        "externalNetworkAttemptLines": [
            line for line in stderr_lines if "http://" in line or "https://" in line
        ],
        "stdoutMessageCount": len(messages),
        "finishedAt": utc_now(),
        "startedAt": started_at,
    }


def run_probe(
    root: Path,
    sentinel_script: Path,
    codex_executable: str | None,
    repetitions: int,
    request_timeout_seconds: float,
) -> dict[str, Any]:
    root = root.resolve()
    if root.exists() and any(root.iterdir()):
        raise RuntimeError(f"probe root must be absent or empty: {root}")
    if repetitions < 2:
        raise RuntimeError("startup profile comparison requires at least two repetitions")
    root.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []
    for repetition in range(1, repetitions + 1):
        for profile_name in PROFILES:
            results.append(
                run_profile(
                    profile_name,
                    root / f"run-{repetition:02d}-{profile_name}",
                    sentinel_script.resolve(),
                    codex_executable,
                    request_timeout_seconds,
                )
            )
    accepted_count = sum(1 for result in results if result["accepted"])
    return {
        "schema": 1,
        "id": PROBE_ID,
        "root": root.as_posix(),
        "repetitions": repetitions,
        "profiles": list(PROFILES),
        "runs": results,
        "acceptedRunCount": accepted_count,
        "allRunsAccepted": accepted_count == len(results),
        "supportedConclusions": {
            "startupProfileDirectCallBoundaryObservedForThisHostAndSentinel": (
                accepted_count == len(results)
            ),
            "fullProfileExposedBothToolsInEveryRun": all(
                result["calls"]["identity"]["succeeded"]
                and result["calls"]["hold"]["succeeded"]
                for result in results
                if result["profile"] == "full"
            ),
            "filteredProfileKeptIdentityAndRejectedHoldInEveryRun": all(
                result["calls"]["identity"]["succeeded"]
                and not result["calls"]["hold"]["succeeded"]
                for result in results
                if result["profile"] == "filtered"
            ),
            "disabledProfileRejectedBothToolsWithoutBoundSentinelInEveryRun": all(
                not result["calls"]["identity"]["succeeded"]
                and not result["calls"]["hold"]["succeeded"]
                and result["process"]["sentinelIdentity"] is None
                for result in results
                if result["profile"] == "disabled"
            ),
        },
        "claimBoundary": {
            "sameThreadHotSwitchingProved": False,
            "reloadCompletionProved": False,
            "automaticTaskScopedOnDemandSwitchingProved": False,
            "statusEqualsLoadedRuntimeProved": False,
            "toolFilteringReducesContextOrTokensProved": False,
            "toolFilteringReducesStartupLatencyProved": False,
            "toolFilteringReducesResourceUseProved": False,
            "serverDisableReleasesEveryProcessProved": False,
            "stableResourceBenefitProved": False,
            "filteringCanAlwaysReplaceDisableProved": False,
            "disableAlwaysOutperformsFilteringProved": False,
            "leaseOrReferenceCountProved": False,
            "crashRecoveryProved": False,
            "desktopPluginOrCrossHostParityProved": False,
            "noNetworkTrafficProved": False,
            "noCredentialWasUsedProved": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument(
        "--sentinel",
        type=Path,
        default=Path(__file__).resolve().with_name("mcp_lifecycle_sentinel.py"),
    )
    parser.add_argument("--codex-executable")
    parser.add_argument("--repetitions", type=int, default=2)
    parser.add_argument("--request-timeout-seconds", type=float, default=60)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    result = run_probe(
        arguments.root,
        arguments.sentinel,
        arguments.codex_executable,
        arguments.repetitions,
        arguments.request_timeout_seconds,
    )
    serialized = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if arguments.output is not None:
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(serialized, encoding="utf-8", newline="\n")
    print(serialized, end="")
    return 0 if result["allRunsAccepted"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
