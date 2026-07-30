#!/usr/bin/env python3
"""Probe isolated MCP child-exit containment and next-call recovery.

The probe uses one native Codex app-server, an empty explicit CODEX_HOME, one
ephemeral read-only thread, and two aliases of the repository-local Sentinel.
Only the victim alias receives a one-process crash token. No model turn,
status discovery, config reload, account state, or current user config is used.

The injected fault is an abrupt local stdio child exit before its tool response.
It is not an operating-system crash signal, hang, OOM, network fault, host
crash, wrapper crash, or lease-controller failure.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import queue
import secrets
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
        utc_now,
    )
    from .probe_codex_app_server_mcp_startup_profiles import (
        event_log_rows,
        sha256_file,
        tool_call_succeeded,
    )
    from .probe_codex_app_server_mcp_status import (
        build_child_environment,
        build_command,
        decode_stdout_message,
        drain_stdout_queue,
        inventory_files,
    )
    from .probe_codex_app_server_mcp_tool_call import (
        extract_thread_id,
        extract_tool_payload,
        resolve_native_codex_executable,
        toml_string,
    )
except ImportError:
    from probe_codex_app_server_mcp_idle_unload import (
        process_identity_complete,
        same_process_identity,
        snapshot_process,
        utc_now,
    )
    from probe_codex_app_server_mcp_startup_profiles import (
        event_log_rows,
        sha256_file,
        tool_call_succeeded,
    )
    from probe_codex_app_server_mcp_status import (
        build_child_environment,
        build_command,
        decode_stdout_message,
        drain_stdout_queue,
        inventory_files,
    )
    from probe_codex_app_server_mcp_tool_call import (
        extract_thread_id,
        extract_tool_payload,
        resolve_native_codex_executable,
        toml_string,
    )


PROBE_ID = "codex-app-server-isolated-mcp-child-exit-recovery-v1"
CONTROL_SERVER = "lifecycle_control"
VICTIM_SERVER = "lifecycle_victim"
CRASH_EXIT_CODE = 86


def _server_stanza(
    server_name: str,
    python_executable: Path,
    sentinel_script: Path,
    event_log: Path,
    cleanup_marker: Path,
    crash_token: str | None,
) -> list[str]:
    arguments = [
        "-B",
        str(sentinel_script.resolve()),
        "--event-log",
        str(event_log.resolve()),
        "--cleanup-marker",
        str(cleanup_marker.resolve()),
    ]
    if crash_token is not None:
        arguments.extend(("--allow-crash-token", crash_token))
    lines = [
        f"[mcp_servers.{server_name}]",
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
            "tool_timeout_sec = 5",
            "enabled = true",
            "",
        )
    )
    return lines


def build_dual_server_config(
    python_executable: Path,
    sentinel_script: Path,
    control_event_log: Path,
    victim_event_log: Path,
    control_cleanup_marker: Path,
    victim_cleanup_marker: Path,
    crash_token: str,
) -> str:
    if not crash_token:
        raise ValueError("crash token must be non-empty")
    lines = _server_stanza(
        CONTROL_SERVER,
        python_executable,
        sentinel_script,
        control_event_log,
        control_cleanup_marker,
        None,
    )
    lines.extend(
        _server_stanza(
            VICTIM_SERVER,
            python_executable,
            sentinel_script,
            victim_event_log,
            victim_cleanup_marker,
            crash_token,
        )
    )
    return "\n".join(lines)


def build_initial_requests(workspace: Path) -> list[dict[str, Any]]:
    return [
        {
            "id": 0,
            "method": "initialize",
            "params": {
                "clientInfo": {
                    "name": "agent-autonomy-harness",
                    "version": "1",
                },
                "capabilities": {},
            },
        },
        {"method": "initialized", "params": {}},
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


def build_tool_call_request(
    request_id: int,
    thread_id: str,
    server: str,
    tool: str,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    return {
        "id": request_id,
        "method": "mcpServer/tool/call",
        "params": {
            "threadId": thread_id,
            "server": server,
            "tool": tool,
            "arguments": arguments,
        },
    }


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
    timeout_seconds: float,
) -> dict[str, Any]:
    _send(process, request)
    request_id = request.get("id")
    deadline = time.monotonic() + timeout_seconds
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


def _capture_request(
    process: subprocess.Popen[str],
    stdout_queue: queue.Queue[str | None],
    messages: list[dict[str, Any]],
    request: dict[str, Any],
    timeout_seconds: float,
) -> dict[str, Any]:
    try:
        response = _request(
            process,
            stdout_queue,
            messages,
            request,
            timeout_seconds,
        )
    except TimeoutError as error:
        return {"outcome": "timeout", "error": str(error)}
    except (RuntimeError, OSError) as error:
        return {"outcome": "transport-closed", "error": str(error)}
    return {"outcome": "response", "response": response}


def _captured_tool_succeeded(capture: dict[str, Any]) -> bool:
    response = capture.get("response")
    return isinstance(response, dict) and tool_call_succeeded(response)


def _captured_payload(capture: dict[str, Any]) -> dict[str, Any] | None:
    response = capture.get("response")
    if not isinstance(response, dict) or not tool_call_succeeded(response):
        return None
    return extract_tool_payload(response)


def _bind_sentinel_identity(
    payload: dict[str, Any],
    app_server_pid: int,
    expected_python: Path,
) -> dict[str, Any]:
    pid = payload.get("pid")
    if not isinstance(pid, int):
        raise RuntimeError("Sentinel payload omitted integer pid")
    identity = snapshot_process(pid)
    if (
        not process_identity_complete(identity)
        or identity.get("parentPid") != app_server_pid
        or os.path.normcase(str(identity.get("imagePath")))
        != os.path.normcase(str(expected_python.resolve()))
    ):
        raise RuntimeError("Sentinel exact child identity could not be bound")
    return identity


def _wait_for_exact_identity_absence(
    identity: dict[str, Any],
    timeout_seconds: float,
) -> tuple[bool, dict[str, Any]]:
    deadline = time.monotonic() + timeout_seconds
    observed = snapshot_process(int(identity["pid"]))
    while (
        time.monotonic() < deadline
        and same_process_identity(identity, observed)
    ):
        time.sleep(0.05)
        observed = snapshot_process(int(identity["pid"]))
    return not same_process_identity(identity, observed), observed


def _instance_start_ids(events: list[dict[str, Any]]) -> list[str]:
    return [
        str(event["instanceId"])
        for event in events
        if event.get("event") == "instance-start"
        and isinstance(event.get("instanceId"), str)
    ]


def _bind_unseen_logged_identities(
    events: list[dict[str, Any]],
    known: dict[str, dict[str, Any]],
    app_server_pid: int,
    expected_python: Path,
) -> list[str]:
    unbound: list[str] = []
    for event in events:
        if event.get("event") != "instance-start":
            continue
        instance_id = event.get("instanceId")
        pid = event.get("pid")
        if (
            not isinstance(instance_id, str)
            or instance_id in known
            or not isinstance(pid, int)
        ):
            continue
        identity = snapshot_process(pid)
        if (
            process_identity_complete(identity)
            and identity.get("parentPid") == app_server_pid
            and os.path.normcase(str(identity.get("imagePath")))
            == os.path.normcase(str(expected_python.resolve()))
        ):
            known[instance_id] = identity
        else:
            unbound.append(instance_id)
    return unbound


def _live_exact_identity_count(
    identities: dict[str, dict[str, Any]],
) -> int:
    return sum(
        same_process_identity(identity, snapshot_process(int(identity["pid"])))
        for identity in identities.values()
    )


def classify_child_exit_result(facts: dict[str, Any]) -> dict[str, Any]:
    if not facts.get("crashAttempted"):
        injection = "not-assessed"
    elif facts.get("crashCallSucceeded"):
        injection = "success-response-instead-of-exit"
    elif not facts.get("crashRequestEventObserved"):
        injection = "event-missing"
    elif facts.get("originalVictimNaturalStopEventObserved"):
        injection = "graceful-stop-observed"
    elif not facts.get("originalVictimExactIdentityAbsent"):
        injection = "process-remained"
    else:
        injection = "observed"

    if injection == "not-assessed":
        host_survival = "not-assessed"
    elif (
        facts.get("appServerSameExactIdentityAfterCrash")
        and facts.get("appServerSameExactIdentityAfterCalls")
    ):
        host_survival = "same-exact-instance"
    elif facts.get("appServerExistsAfterCrash"):
        host_survival = "restarted-or-identity-changed"
    else:
        host_survival = "exited"

    if host_survival != "same-exact-instance":
        control_isolation = "not-assessed"
    elif not facts.get("controlPostCrashSucceeded"):
        control_isolation = "unavailable"
    elif (
        facts.get("controlSameInstanceId")
        and facts.get("controlSameExactIdentity")
    ):
        control_isolation = "same-instance"
    else:
        control_isolation = "restarted-or-instance-changed"

    if (
        facts.get("sameThreadRecoverySucceeded")
        and facts.get("recoveryNewInstanceId")
        and facts.get("recoveryExactIdentityBound")
    ):
        victim_recovery = "same-thread-new-instance"
    elif facts.get("sameThreadRecoverySucceeded"):
        victim_recovery = "invalid-old-or-unbound-instance"
    elif (
        facts.get("fallbackRecoverySucceeded")
        and facts.get("fallbackNewInstanceId")
        and facts.get("fallbackExactIdentityBound")
    ):
        victim_recovery = "new-thread-only"
    elif facts.get("crashAttempted"):
        victim_recovery = "failed"
    else:
        victim_recovery = "not-assessed"

    if facts.get("simultaneousLiveVictimExactIdentityCount", 0) > 1:
        duplicate_or_leak = "detected"
    elif (
        facts.get("allLoggedInstancesExactlyBound")
        and facts.get("loggedTopologyMatchesExpected")
        and facts.get("originalVictimExactIdentityAbsent")
    ):
        duplicate_or_leak = "none-among-logged-and-bound"
    else:
        duplicate_or_leak = "unverifiable"

    cleanup = "safe" if facts.get("cleanupSafe") else "incomplete"
    dimensions = {
        "injection": injection,
        "hostSurvival": host_survival,
        "controlIsolation": control_isolation,
        "victimRecovery": victim_recovery,
        "duplicateOrLeak": duplicate_or_leak,
        "cleanup": cleanup,
    }

    if not facts.get("baselineControlSucceeded"):
        result_class = "blocked-baseline-control-call-failed"
    elif not facts.get("baselineVictimSucceeded"):
        result_class = "blocked-baseline-victim-call-failed"
    elif not facts.get("configUnchanged") or facts.get("authStateProduced"):
        result_class = "invalid-isolation-boundary-config-or-auth-drift"
    elif facts.get("crashTokenLeakedInEventLogs"):
        result_class = "invalid-isolation-boundary-crash-token-leaked"
    elif injection != "observed":
        result_class = f"falsified-crash-injection-{injection}"
    elif host_survival != "same-exact-instance":
        result_class = "falsified-app-server-did-not-survive-exactly"
    elif control_isolation != "same-instance":
        result_class = "falsified-control-mcp-restarted-or-unavailable"
    elif duplicate_or_leak == "detected":
        result_class = "falsified-duplicate-victim-or-leak-observed"
    elif cleanup != "safe":
        result_class = "cleanup-incomplete-result-not-admissible"
    elif (
        victim_recovery == "same-thread-new-instance"
        and duplicate_or_leak == "none-among-logged-and-bound"
    ):
        result_class = (
            "observed-single-host-abrupt-child-exit-isolated-and-"
            "same-thread-next-call-recovery"
        )
    elif victim_recovery == "new-thread-only":
        result_class = "partial-new-thread-recovery-only"
    elif victim_recovery == "invalid-old-or-unbound-instance":
        result_class = "falsified-victim-recovery-returned-old-or-unbound-instance"
    elif victim_recovery == "same-thread-new-instance":
        result_class = "partial-same-thread-recovery-topology-unverifiable"
    else:
        result_class = (
            "partial-fault-isolation-observed-victim-same-thread-recovery-failed"
        )

    return {
        "dimensions": dimensions,
        "resultClass": result_class,
        "accepted": result_class.startswith(
            "observed-single-host-abrupt-child-exit-isolated"
        ),
    }


def run_probe(
    root: Path,
    sentinel_script: Path,
    codex_executable: str | None,
    request_timeout_seconds: float,
    crash_response_timeout_seconds: float,
    exit_observation_timeout_seconds: float,
) -> dict[str, Any]:
    if os.name != "nt":
        raise RuntimeError("the exact child-exit recovery probe currently requires Windows")
    if request_timeout_seconds <= 0:
        raise ValueError("request timeout must be positive")
    if crash_response_timeout_seconds <= 0:
        raise ValueError("crash response timeout must be positive")
    if exit_observation_timeout_seconds <= 0:
        raise ValueError("exit observation timeout must be positive")

    root = root.resolve()
    sentinel_script = sentinel_script.resolve()
    if root.exists() and any(root.iterdir()):
        raise RuntimeError(f"probe root must be absent or empty: {root}")
    if not sentinel_script.is_file():
        raise RuntimeError(f"Sentinel script is missing: {sentinel_script}")

    codex_home = (root / "codex-home").resolve()
    workspace = (root / "workspace").resolve()
    default_home = (Path.home() / ".codex").resolve()
    if os.path.normcase(str(codex_home)) == os.path.normcase(str(default_home)):
        raise RuntimeError("refusing to use the current default Codex home")
    codex_home.mkdir(parents=True, exist_ok=True)
    workspace.mkdir(parents=True, exist_ok=True)

    control_event_log = codex_home / "control-events.jsonl"
    victim_event_log = codex_home / "victim-events.jsonl"
    control_cleanup_marker = codex_home / "control-cleanup.marker"
    victim_cleanup_marker = codex_home / "victim-cleanup.marker"
    config_path = codex_home / "config.toml"
    crash_token = secrets.token_urlsafe(24)
    config_path.write_text(
        build_dual_server_config(
            Path(sys.executable),
            sentinel_script,
            control_event_log,
            victim_event_log,
            control_cleanup_marker,
            victim_cleanup_marker,
            crash_token,
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
    started_at = utc_now()
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
    if (
        not process_identity_complete(app_server_identity)
        or os.path.normcase(str(app_server_identity.get("imagePath")))
        != os.path.normcase(str(Path(executable).resolve()))
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
    request_methods: list[str] = []
    thread_ids: list[str] = []
    control_identities: dict[str, dict[str, Any]] = {}
    victim_identities: dict[str, dict[str, Any]] = {}
    control_pre_capture: dict[str, Any] = {"outcome": "not-attempted"}
    victim_pre_capture: dict[str, Any] = {"outcome": "not-attempted"}
    crash_capture: dict[str, Any] = {"outcome": "not-attempted"}
    control_post_capture: dict[str, Any] = {"outcome": "not-attempted"}
    same_thread_recovery_capture: dict[str, Any] = {"outcome": "not-attempted"}
    fallback_recovery_capture: dict[str, Any] = {"outcome": "not-attempted"}
    control_pre_payload: dict[str, Any] | None = None
    victim_pre_payload: dict[str, Any] | None = None
    control_post_payload: dict[str, Any] | None = None
    same_thread_recovery_payload: dict[str, Any] | None = None
    fallback_recovery_payload: dict[str, Any] | None = None
    original_victim_absent = False
    original_victim_after_crash: dict[str, Any] | None = None
    crash_request_event_observed = False
    app_server_after_crash: dict[str, Any] | None = None
    app_server_after_calls: dict[str, Any] | None = None
    control_post_identity: dict[str, Any] | None = None
    same_thread_recovery_identity: dict[str, Any] | None = None
    fallback_recovery_identity: dict[str, Any] | None = None
    cleanup_marker_written = False
    app_server_kill_sent = False
    control_events_before_cleanup: list[dict[str, Any]] = []
    victim_events_before_cleanup: list[dict[str, Any]] = []
    unbound_control_before_cleanup: list[str] = []
    unbound_victim_before_cleanup: list[str] = []
    control_start_ids_before_cleanup: list[str] = []
    victim_start_ids_before_cleanup: list[str] = []
    simultaneous_live_victim_count = 0
    logged_topology_matches_expected = False

    try:
        initial = build_initial_requests(workspace)
        request_methods.append(initial[0]["method"])
        initialize = _request(
            process,
            stdout_queue,
            messages,
            initial[0],
            request_timeout_seconds,
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

        request_methods.append(initial[1]["method"])
        _send(process, initial[1])
        request_methods.append(initial[2]["method"])
        thread_response = _request(
            process,
            stdout_queue,
            messages,
            initial[2],
            request_timeout_seconds,
        )
        thread_id = extract_thread_id(thread_response)
        thread_ids.append(thread_id)

        control_request = build_tool_call_request(
            2,
            thread_id,
            CONTROL_SERVER,
            "identity",
            {"probe": PROBE_ID, "role": "control", "phase": "before-exit"},
        )
        request_methods.append(control_request["method"])
        control_pre_capture = _capture_request(
            process,
            stdout_queue,
            messages,
            control_request,
            request_timeout_seconds,
        )
        control_pre_payload = _captured_payload(control_pre_capture)
        if control_pre_payload is not None:
            control_identity = _bind_sentinel_identity(
                control_pre_payload, process.pid, Path(sys.executable)
            )
            control_identities[str(control_pre_payload["instanceId"])] = (
                control_identity
            )

        victim_request = build_tool_call_request(
            3,
            thread_id,
            VICTIM_SERVER,
            "identity",
            {"probe": PROBE_ID, "role": "victim", "phase": "before-exit"},
        )
        request_methods.append(victim_request["method"])
        victim_pre_capture = _capture_request(
            process,
            stdout_queue,
            messages,
            victim_request,
            request_timeout_seconds,
        )
        victim_pre_payload = _captured_payload(victim_pre_capture)
        if victim_pre_payload is not None:
            victim_identity = _bind_sentinel_identity(
                victim_pre_payload, process.pid, Path(sys.executable)
            )
            victim_identities[str(victim_pre_payload["instanceId"])] = victim_identity

        if control_pre_payload is not None and victim_pre_payload is not None:
            crash_request = build_tool_call_request(
                4,
                thread_id,
                VICTIM_SERVER,
                "crash",
                {"token": crash_token},
            )
            request_methods.append(crash_request["method"])
            crash_capture = _capture_request(
                process,
                stdout_queue,
                messages,
                crash_request,
                crash_response_timeout_seconds,
            )

            original_victim = victim_identities[str(victim_pre_payload["instanceId"])]
            (
                original_victim_absent,
                original_victim_after_crash,
            ) = _wait_for_exact_identity_absence(
                original_victim,
                exit_observation_timeout_seconds,
            )
            victim_events_after_crash = event_log_rows(victim_event_log)
            crash_request_event_observed = any(
                event.get("event") == "crash-requested"
                and event.get("instanceId") == victim_pre_payload.get("instanceId")
                and event.get("tokenMatched") is True
                and event.get("exitCode") == CRASH_EXIT_CODE
                for event in victim_events_after_crash
            )
            app_server_after_crash = snapshot_process(process.pid)

            if same_process_identity(app_server_identity, app_server_after_crash):
                control_post_request = build_tool_call_request(
                    5,
                    thread_id,
                    CONTROL_SERVER,
                    "identity",
                    {"probe": PROBE_ID, "role": "control", "phase": "after-exit"},
                )
                request_methods.append(control_post_request["method"])
                control_post_capture = _capture_request(
                    process,
                    stdout_queue,
                    messages,
                    control_post_request,
                    request_timeout_seconds,
                )
                control_post_payload = _captured_payload(control_post_capture)
                if control_post_payload is not None:
                    control_post_identity = _bind_sentinel_identity(
                        control_post_payload, process.pid, Path(sys.executable)
                    )
                    control_identities.setdefault(
                        str(control_post_payload["instanceId"]),
                        control_post_identity,
                    )

                recovery_request = build_tool_call_request(
                    6,
                    thread_id,
                    VICTIM_SERVER,
                    "identity",
                    {"probe": PROBE_ID, "role": "victim", "phase": "same-thread"},
                )
                request_methods.append(recovery_request["method"])
                same_thread_recovery_capture = _capture_request(
                    process,
                    stdout_queue,
                    messages,
                    recovery_request,
                    request_timeout_seconds,
                )
                same_thread_recovery_payload = _captured_payload(
                    same_thread_recovery_capture
                )
                if same_thread_recovery_payload is not None:
                    same_thread_recovery_identity = _bind_sentinel_identity(
                        same_thread_recovery_payload,
                        process.pid,
                        Path(sys.executable),
                    )
                    victim_identities[
                        str(same_thread_recovery_payload["instanceId"])
                    ] = same_thread_recovery_identity
                else:
                    fallback_start = {
                        "id": 7,
                        "method": "thread/start",
                        "params": {
                            "cwd": workspace.as_posix(),
                            "ephemeral": True,
                            "approvalPolicy": "never",
                            "sandbox": "read-only",
                        },
                    }
                    request_methods.append(fallback_start["method"])
                    fallback_start_capture = _capture_request(
                        process,
                        stdout_queue,
                        messages,
                        fallback_start,
                        request_timeout_seconds,
                    )
                    fallback_start_response = fallback_start_capture.get("response")
                    if isinstance(fallback_start_response, dict):
                        try:
                            fallback_thread_id = extract_thread_id(
                                fallback_start_response
                            )
                        except RuntimeError:
                            fallback_thread_id = None
                        if fallback_thread_id is not None:
                            thread_ids.append(fallback_thread_id)
                            fallback_request = build_tool_call_request(
                                8,
                                fallback_thread_id,
                                VICTIM_SERVER,
                                "identity",
                                {
                                    "probe": PROBE_ID,
                                    "role": "victim",
                                    "phase": "new-thread-fallback",
                                },
                            )
                            request_methods.append(fallback_request["method"])
                            fallback_recovery_capture = _capture_request(
                                process,
                                stdout_queue,
                                messages,
                                fallback_request,
                                request_timeout_seconds,
                            )
                            fallback_recovery_payload = _captured_payload(
                                fallback_recovery_capture
                            )
                            if fallback_recovery_payload is not None:
                                fallback_recovery_identity = _bind_sentinel_identity(
                                    fallback_recovery_payload,
                                    process.pid,
                                    Path(sys.executable),
                                )
                                victim_identities[
                                    str(fallback_recovery_payload["instanceId"])
                                ] = fallback_recovery_identity

            app_server_after_calls = snapshot_process(process.pid)

        next_request_id = 9
        for active_thread_id in thread_ids:
            unsubscribe = {
                "id": next_request_id,
                "method": "thread/unsubscribe",
                "params": {"threadId": active_thread_id},
            }
            next_request_id += 1
            request_methods.append(unsubscribe["method"])
            _capture_request(
                process,
                stdout_queue,
                messages,
                unsubscribe,
                request_timeout_seconds,
            )

        control_events_before_cleanup = event_log_rows(control_event_log)
        victim_events_before_cleanup = event_log_rows(victim_event_log)
        unbound_control_before_cleanup = _bind_unseen_logged_identities(
            control_events_before_cleanup,
            control_identities,
            process.pid,
            Path(sys.executable),
        )
        unbound_victim_before_cleanup = _bind_unseen_logged_identities(
            victim_events_before_cleanup,
            victim_identities,
            process.pid,
            Path(sys.executable),
        )
        control_start_ids_before_cleanup = _instance_start_ids(
            control_events_before_cleanup
        )
        victim_start_ids_before_cleanup = _instance_start_ids(
            victim_events_before_cleanup
        )
        simultaneous_live_victim_count = _live_exact_identity_count(
            victim_identities
        )
        logged_topology_matches_expected = (
            control_start_ids_before_cleanup
            == (
                [str(control_pre_payload["instanceId"])]
                if isinstance(control_pre_payload, dict)
                else []
            )
            and isinstance(victim_pre_payload, dict)
            and isinstance(same_thread_recovery_payload, dict)
            and victim_start_ids_before_cleanup
            == [
                str(victim_pre_payload["instanceId"]),
                str(same_thread_recovery_payload["instanceId"]),
            ]
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
        control_cleanup_marker.write_text(
            "harness cleanup\n", encoding="utf-8", newline="\n"
        )
        victim_cleanup_marker.write_text(
            "harness cleanup\n", encoding="utf-8", newline="\n"
        )
        cleanup_marker_written = True
        cleanup_deadline = time.monotonic() + 10
        while time.monotonic() < cleanup_deadline:
            if all(
                not same_process_identity(
                    identity, snapshot_process(int(identity["pid"]))
                )
                for identity in [
                    *control_identities.values(),
                    *victim_identities.values(),
                ]
            ):
                break
            time.sleep(0.05)
        stdout_thread.join(timeout=1)
        stderr_thread.join(timeout=1)
        drain_stdout_queue(stdout_queue, messages)

    control_events = event_log_rows(control_event_log)
    victim_events = event_log_rows(victim_event_log)
    control_start_ids = _instance_start_ids(control_events)
    victim_start_ids = _instance_start_ids(victim_events)

    config_hash_after = hashlib.sha256(config_path.read_bytes()).hexdigest()
    files_after = inventory_files(codex_home)
    auth_state_produced = any(
        str(item["path"]).lower().endswith("auth.json") for item in files_after
    )

    baseline_control_succeeded = control_pre_payload is not None
    baseline_victim_succeeded = victim_pre_payload is not None
    crash_attempted = crash_capture.get("outcome") != "not-attempted"
    crash_call_succeeded = _captured_tool_succeeded(crash_capture)
    control_post_succeeded = control_post_payload is not None
    control_same_instance_id = (
        isinstance(control_pre_payload, dict)
        and isinstance(control_post_payload, dict)
        and control_pre_payload.get("instanceId")
        == control_post_payload.get("instanceId")
    )
    control_pre_identity = (
        control_identities.get(str(control_pre_payload.get("instanceId")))
        if isinstance(control_pre_payload, dict)
        else None
    )
    control_same_exact_identity = (
        isinstance(control_pre_identity, dict)
        and isinstance(control_post_identity, dict)
        and same_process_identity(control_pre_identity, control_post_identity)
    )
    same_thread_recovery_succeeded = same_thread_recovery_payload is not None
    fallback_recovery_succeeded = fallback_recovery_payload is not None
    recovery_new_instance_id = (
        isinstance(victim_pre_payload, dict)
        and isinstance(same_thread_recovery_payload, dict)
        and victim_pre_payload.get("instanceId")
        != same_thread_recovery_payload.get("instanceId")
    )
    fallback_new_instance_id = (
        isinstance(victim_pre_payload, dict)
        and isinstance(fallback_recovery_payload, dict)
        and victim_pre_payload.get("instanceId")
        != fallback_recovery_payload.get("instanceId")
    )
    app_server_after_crash_value = app_server_after_crash or snapshot_process(
        process.pid
    )
    app_server_after_calls_value = app_server_after_calls or app_server_after_crash_value
    original_victim_natural_stop_observed = (
        isinstance(victim_pre_payload, dict)
        and any(
            event.get("event") == "instance-stop"
            and event.get("instanceId") == victim_pre_payload.get("instanceId")
            for event in victim_events_before_cleanup
        )
    )
    crash_token_leaked_in_event_logs = crash_token in (
        json.dumps(
            [*control_events, *victim_events],
            separators=(",", ":"),
            ensure_ascii=False,
        )
    )

    final_sentinel_checks = {
        role: {
            instance_id: {
                "expected": identity,
                "observedAfterCleanup": snapshot_process(int(identity["pid"])),
            }
            for instance_id, identity in identities.items()
        }
        for role, identities in (
            ("control", control_identities),
            ("victim", victim_identities),
        )
    }
    all_sentinel_exact_identities_absent = all(
        not same_process_identity(
            value["expected"], value["observedAfterCleanup"]
        )
        for role_checks in final_sentinel_checks.values()
        for value in role_checks.values()
    )
    app_server_after_cleanup = snapshot_process(process.pid)
    app_server_exact_identity_absent = not same_process_identity(
        app_server_identity, app_server_after_cleanup
    )
    cleanup_safe = (
        process.returncode is not None
        and app_server_exact_identity_absent
        and all_sentinel_exact_identities_absent
        and not unbound_control_before_cleanup
        and not unbound_victim_before_cleanup
    )

    facts = {
        "baselineControlSucceeded": baseline_control_succeeded,
        "baselineVictimSucceeded": baseline_victim_succeeded,
        "crashAttempted": crash_attempted,
        "crashCallSucceeded": crash_call_succeeded,
        "crashRequestEventObserved": crash_request_event_observed,
        "originalVictimNaturalStopEventObserved": (
            original_victim_natural_stop_observed
        ),
        "originalVictimExactIdentityAbsent": original_victim_absent,
        "appServerExistsAfterCrash": app_server_after_crash_value.get("exists") is True,
        "appServerSameExactIdentityAfterCrash": same_process_identity(
            app_server_identity, app_server_after_crash_value
        ),
        "appServerSameExactIdentityAfterCalls": same_process_identity(
            app_server_identity, app_server_after_calls_value
        ),
        "controlPostCrashSucceeded": control_post_succeeded,
        "controlSameInstanceId": control_same_instance_id,
        "controlSameExactIdentity": control_same_exact_identity,
        "sameThreadRecoverySucceeded": same_thread_recovery_succeeded,
        "recoveryNewInstanceId": recovery_new_instance_id,
        "recoveryExactIdentityBound": same_thread_recovery_identity is not None,
        "fallbackRecoverySucceeded": fallback_recovery_succeeded,
        "fallbackNewInstanceId": fallback_new_instance_id,
        "fallbackExactIdentityBound": fallback_recovery_identity is not None,
        "simultaneousLiveVictimExactIdentityCount": simultaneous_live_victim_count,
        "allLoggedInstancesExactlyBound": (
            not unbound_control_before_cleanup
            and not unbound_victim_before_cleanup
            and set(control_start_ids_before_cleanup).issubset(control_identities)
            and set(victim_start_ids_before_cleanup).issubset(victim_identities)
        ),
        "loggedTopologyMatchesExpected": logged_topology_matches_expected,
        "configUnchanged": config_hash_before == config_hash_after,
        "authStateProduced": auth_state_produced,
        "crashTokenLeakedInEventLogs": crash_token_leaked_in_event_logs,
        "cleanupSafe": cleanup_safe,
    }
    classification = classify_child_exit_result(facts)
    dimensions = classification["dimensions"]

    return {
        "schema": 1,
        "id": PROBE_ID,
        "startedAt": started_at,
        "finishedAt": utc_now(),
        "resultClass": classification["resultClass"],
        "accepted": classification["accepted"],
        "dimensions": dimensions,
        "facts": facts,
        "requestMethods": request_methods,
        "threadIds": thread_ids,
        "calls": {
            "controlBeforeExit": {
                "capture": control_pre_capture,
                "payload": control_pre_payload,
            },
            "victimBeforeExit": {
                "capture": victim_pre_capture,
                "payload": victim_pre_payload,
            },
            "victimCrash": {
                "capture": crash_capture,
                "successfulToolResult": crash_call_succeeded,
                "hostReturnedExplicitFailure": (
                    crash_capture.get("outcome") == "response"
                    and not crash_call_succeeded
                ),
                "tokenRecordedInResult": False,
            },
            "controlAfterExit": {
                "capture": control_post_capture,
                "payload": control_post_payload,
            },
            "victimSameThreadRecovery": {
                "capture": same_thread_recovery_capture,
                "payload": same_thread_recovery_payload,
            },
            "victimNewThreadFallback": {
                "capture": fallback_recovery_capture,
                "payload": fallback_recovery_payload,
            },
        },
        "processes": {
            "appServerBefore": app_server_identity,
            "appServerAfterCrash": app_server_after_crash_value,
            "appServerAfterCalls": app_server_after_calls_value,
            "appServerAfterCleanup": app_server_after_cleanup,
            "originalVictimAfterCrash": original_victim_after_crash,
            "controlIdentities": control_identities,
            "victimIdentities": victim_identities,
            "finalSentinelChecks": final_sentinel_checks,
            "appServerKillSentThroughOwnedHandle": app_server_kill_sent,
            "pidOnlySignalUsed": False,
            "processNameScanOrTerminationUsed": False,
        },
        "eventLogs": {
            "control": {
                "path": control_event_log.as_posix(),
                "sha256": sha256_file(control_event_log),
                "bytes": (
                    control_event_log.stat().st_size
                    if control_event_log.is_file()
                    else 0
                ),
                "events": control_events,
                "instanceStartIds": control_start_ids,
                "unboundInstanceIdsBeforeCleanup": (
                    unbound_control_before_cleanup
                ),
            },
            "victim": {
                "path": victim_event_log.as_posix(),
                "sha256": sha256_file(victim_event_log),
                "bytes": (
                    victim_event_log.stat().st_size
                    if victim_event_log.is_file()
                    else 0
                ),
                "events": victim_events,
                "instanceStartIds": victim_start_ids,
                "unboundInstanceIdsBeforeCleanup": (
                    unbound_victim_before_cleanup
                ),
            },
        },
        "isolation": {
            "root": root.as_posix(),
            "codexHome": codex_home.as_posix(),
            "workspace": workspace.as_posix(),
            "currentConfigCopied": False,
            "currentAuthCopied": False,
            "currentPluginsCopied": False,
            "removedAccountEnvironmentKeysPresentBefore": removed_keys,
            "accountEnvironmentValuesRecorded": False,
            "randomOneProcessCrashTokenGenerated": True,
            "crashTokenRecordedInResult": False,
            "authStateProduced": auth_state_produced,
            "configHashBefore": config_hash_before,
            "configHashAfter": config_hash_after,
            "configUnchangedDuringProbe": config_hash_before == config_hash_after,
            "filesBefore": files_before,
            "filesAfter": files_after,
        },
        "cleanup": {
            "markersWritten": cleanup_marker_written,
            "appServerReturnCode": process.returncode,
            "appServerExactIdentityAbsent": app_server_exact_identity_absent,
            "allBoundSentinelExactIdentitiesAbsent": (
                all_sentinel_exact_identities_absent
            ),
            "safe": cleanup_safe,
        },
        "externalNetworkAttemptLines": [
            line for line in stderr_lines if "http://" in line or "https://" in line
        ],
        "stdoutMessageCount": len(messages),
        "claimBoundary": {
            "abruptLocalStdioChildExitInjectedForThisRun": (
                dimensions["injection"] == "observed"
            ),
            "postExitSeparateMcpIsolationObservedForThisRun": (
                dimensions["controlIsolation"] == "same-instance"
            ),
            "sameThreadNextCallRecoveryObservedForThisRun": (
                dimensions["victimRecovery"] == "same-thread-new-instance"
            ),
            "newThreadFallbackRecoveryObservedForThisRun": (
                dimensions["victimRecovery"] == "new-thread-only"
            ),
            "proactiveAutomaticRestartProved": False,
            "operatingSystemCrashSignalOomOrHangRecoveryProved": False,
            "networkOrHalfOpenTransportRecoveryProved": False,
            "hostWrapperPluginOrLeaseControllerCrashRecoveryProved": False,
            "concurrentOrInFlightCallIsolationProved": False,
            "taskLeaseOrReferenceCountCorrectnessProved": False,
            "priorEnabledDisabledStateRestorationProved": False,
            "sameThreadHotEnableDisableProved": False,
            "reloadCompletionProved": False,
            "processDuplicateFreedomBeyondLoggedAndBoundInstancesProved": False,
            "stableResourceBenefitProved": False,
            "noNetworkTrafficProved": False,
            "noCredentialWasUsedProved": False,
            "desktopPluginClaudeOrCrossHostParityProved": False,
            "universalMcpCrashRecoveryOrFaultIsolationProved": False,
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
    parser.add_argument("--request-timeout-seconds", type=float, default=30)
    parser.add_argument("--crash-response-timeout-seconds", type=float, default=8)
    parser.add_argument("--exit-observation-timeout-seconds", type=float, default=10)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    result = run_probe(
        arguments.root,
        arguments.sentinel,
        arguments.codex_executable,
        arguments.request_timeout_seconds,
        arguments.crash_response_timeout_seconds,
        arguments.exit_observation_timeout_seconds,
    )
    serialized = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if arguments.output is not None:
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(serialized, encoding="utf-8", newline="\n")
    print(serialized, end="")
    return 0 if result["accepted"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
