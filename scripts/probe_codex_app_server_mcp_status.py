#!/usr/bin/env python3
"""Probe Codex app-server MCP status in an isolated CODEX_HOME.

The runner sends only initialize, initialized, and mcpServerStatus/list. It
does not copy auth/config/plugin state, start a thread, reload MCP config, or
call an MCP tool.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import queue
import shutil
import subprocess
import threading
import time
from typing import Any


PROBE_ID = "codex-app-server-isolated-mcp-status-probe-v1"
REMOVED_ACCOUNT_ENVIRONMENT_KEYS = (
    "CHATGPT_AUTH_TOKEN",
    "CODEX_API_KEY",
    "OPENAI_API_KEY",
    "OPENAI_BASE_URL",
)


def build_requests() -> list[dict[str, Any]]:
    return [
        {
            "id": 0,
            "method": "initialize",
            "params": {
                "clientInfo": {
                    "name": "agent_autonomy_harness_probe",
                    "title": "Agent Autonomy Harness MCP Status Probe",
                    "version": "1.0.0",
                }
            },
        },
        {"method": "initialized"},
        {
            "id": 1,
            "method": "mcpServerStatus/list",
            "params": {"detail": "full", "limit": 100},
        },
    ]


def build_child_environment(codex_home: Path) -> tuple[dict[str, str], list[str]]:
    environment = dict(os.environ)
    removed: list[str] = []
    for key in REMOVED_ACCOUNT_ENVIRONMENT_KEYS:
        if key in environment:
            removed.append(key)
            del environment[key]
    environment["CODEX_HOME"] = str(codex_home)
    environment["RUST_LOG"] = "warn"
    environment["LOG_FORMAT"] = "json"
    return environment, removed


def parse_json_lines(text: str) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as error:
            raise RuntimeError(f"stdout line {line_number} is not JSON: {error}") from error
        if not isinstance(value, dict):
            raise RuntimeError(f"stdout line {line_number} is not a JSON object")
        messages.append(value)
    return messages


def validate_responses(messages: list[dict[str, Any]], expected_home: Path) -> dict[str, Any]:
    by_id = {message.get("id"): message for message in messages if "id" in message}
    for request_id in (0, 1):
        if request_id not in by_id:
            raise RuntimeError(f"missing response id {request_id}")
        if "error" in by_id[request_id]:
            raise RuntimeError(f"response id {request_id} returned error: {by_id[request_id]['error']}")

    initialize_result = by_id[0].get("result")
    if not isinstance(initialize_result, dict):
        raise RuntimeError("initialize result is not an object")
    actual_home_value = initialize_result.get("codexHome")
    if not isinstance(actual_home_value, str):
        raise RuntimeError("initialize result omitted codexHome")
    actual_home = Path(actual_home_value).resolve()
    if os.path.normcase(str(actual_home)) != os.path.normcase(str(expected_home.resolve())):
        raise RuntimeError(f"app-server used unexpected CODEX_HOME: {actual_home}")

    status_result = by_id[1].get("result")
    if not isinstance(status_result, dict) or not isinstance(status_result.get("data"), list):
        raise RuntimeError("mcpServerStatus/list result omitted data array")
    servers = status_result["data"]
    names: list[str] = []
    for item in servers:
        if not isinstance(item, dict) or not isinstance(item.get("name"), str):
            raise RuntimeError("mcpServerStatus/list returned an invalid server item")
        names.append(item["name"])

    notifications = [
        message.get("method")
        for message in messages
        if "id" not in message and isinstance(message.get("method"), str)
    ]
    return {
        "initialize": {
            "codexHome": actual_home.as_posix(),
            "userAgent": initialize_result.get("userAgent"),
            "platformFamily": initialize_result.get("platformFamily"),
            "platformOs": initialize_result.get("platformOs"),
        },
        "mcpStatus": {
            "serverCount": len(servers),
            "serverNames": names,
            "nextCursor": status_result.get("nextCursor"),
            "data": servers,
        },
        "notificationMethods": notifications,
    }


def inventory_files(root: Path) -> list[dict[str, Any]]:
    if not root.exists():
        return []
    return [
        {
            "path": path.relative_to(root).as_posix(),
            "type": "directory" if path.is_dir() else "file",
            "bytes": None if path.is_dir() else path.stat().st_size,
        }
        for path in sorted(root.rglob("*"), key=lambda item: item.as_posix().lower())
    ]


def resolve_codex_executable(explicit: str | None) -> str:
    if explicit:
        resolved = shutil.which(explicit) or explicit
    else:
        if os.name == "nt":
            resolved = shutil.which("codex.cmd") or shutil.which("codex.exe") or shutil.which("codex")
        else:
            resolved = shutil.which("codex")
    if not resolved or not Path(resolved).exists():
        raise RuntimeError("unable to resolve a Codex executable")
    return str(Path(resolved).resolve())


def build_command(executable: str) -> list[str]:
    codex_arguments = [
        "app-server",
        "--stdio",
        "--strict-config",
        "-c",
        "analytics.enabled=false",
    ]
    if os.name == "nt" and Path(executable).suffix.lower() in {".cmd", ".bat"}:
        command_interpreter = os.environ.get("COMSPEC") or shutil.which("cmd.exe")
        if not command_interpreter:
            raise RuntimeError("unable to resolve cmd.exe for the Codex command wrapper")
        return [command_interpreter, "/d", "/s", "/c", executable, *codex_arguments]
    return [executable, *codex_arguments]


def decode_stdout_message(line: str, sequence: int) -> dict[str, Any]:
    try:
        value = json.loads(line)
    except json.JSONDecodeError as error:
        raise RuntimeError(f"stdout message {sequence} is not JSON: {error}") from error
    if not isinstance(value, dict):
        raise RuntimeError(f"stdout message {sequence} is not a JSON object")
    return value


def remaining_timeout(deadline: float) -> float:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise subprocess.TimeoutExpired("codex app-server status probe", 0)
    return remaining


def wait_for_response(
    stdout_queue: queue.Queue[str | None],
    request_id: int,
    deadline: float,
    messages: list[dict[str, Any]],
) -> dict[str, Any]:
    while True:
        try:
            line = stdout_queue.get(timeout=remaining_timeout(deadline))
        except queue.Empty as error:
            raise subprocess.TimeoutExpired("codex app-server status probe", 0) from error
        if line is None:
            raise RuntimeError(f"app-server stdout closed before response id {request_id}")
        if not line.strip():
            continue
        message = decode_stdout_message(line, len(messages) + 1)
        messages.append(message)
        if message.get("id") == request_id:
            return message


def drain_stdout_queue(
    stdout_queue: queue.Queue[str | None], messages: list[dict[str, Any]]
) -> None:
    while True:
        try:
            line = stdout_queue.get_nowait()
        except queue.Empty:
            return
        if line is None or not line.strip():
            continue
        messages.append(decode_stdout_message(line, len(messages) + 1))


def run_probe(codex_home: Path, codex_executable: str | None, timeout_seconds: float) -> dict[str, Any]:
    codex_home = codex_home.resolve()
    default_home = (Path.home() / ".codex").resolve()
    if os.path.normcase(str(codex_home)) == os.path.normcase(str(default_home)):
        raise RuntimeError("refusing to use the current default Codex home")
    if codex_home.exists() and any(codex_home.iterdir()):
        raise RuntimeError("isolated Codex home must be absent or empty before the probe")
    codex_home.mkdir(parents=True, exist_ok=True)

    files_before = inventory_files(codex_home)
    executable = resolve_codex_executable(codex_executable)
    environment, removed_keys = build_child_environment(codex_home)
    requests = build_requests()
    command = build_command(executable)
    creation_flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    started_at = datetime.now(timezone.utc)
    process = subprocess.Popen(
        command,
        cwd=codex_home,
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
    timed_out = False
    try:
        assert process.stdin is not None
        process.stdin.write(json.dumps(requests[0], separators=(",", ":")) + "\n")
        process.stdin.flush()
        wait_for_response(stdout_queue, 0, deadline, messages)

        for request in requests[1:]:
            process.stdin.write(json.dumps(request, separators=(",", ":")) + "\n")
        process.stdin.flush()
        wait_for_response(stdout_queue, 1, deadline, messages)

        process.stdin.close()
        process.wait(timeout=remaining_timeout(deadline))
    except subprocess.TimeoutExpired:
        timed_out = True
    except BaseException:
        if process.stdin is not None and not process.stdin.closed:
            process.stdin.close()
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)
        stdout_thread.join(timeout=1)
        stderr_thread.join(timeout=1)
        raise
    finally:
        if process.stdin is not None and not process.stdin.closed:
            process.stdin.close()
    if timed_out and process.poll() is None:
        process.kill()
        process.wait(timeout=5)
    stdout_thread.join(timeout=1)
    stderr_thread.join(timeout=1)
    drain_stdout_queue(stdout_queue, messages)
    finished_at = datetime.now(timezone.utc)
    if timed_out:
        raise RuntimeError(f"app-server probe timed out after {timeout_seconds} seconds")
    if process.returncode != 0:
        raise RuntimeError(
            f"app-server exited {process.returncode}: {'; '.join(stderr_lines).strip()}"
        )

    response_summary = validate_responses(messages, codex_home)
    files_after = inventory_files(codex_home)
    auth_paths = [item["path"] for item in files_after if item["path"].lower().endswith("auth.json")]
    if auth_paths:
        raise RuntimeError(f"isolated probe unexpectedly produced auth state: {auth_paths}")

    return {
        "schema": 1,
        "id": PROBE_ID,
        "startedAt": started_at.isoformat(),
        "finishedAt": finished_at.isoformat(),
        "durationMilliseconds": round((finished_at - started_at).total_seconds() * 1000),
        "command": command,
        "process": {
            "pid": process.pid,
            "returnCode": process.returncode,
            "timedOut": False,
            "stdinClosedAtCompletion": True,
        },
        "isolation": {
            "requestedCodexHome": codex_home.as_posix(),
            "defaultCodexHomeRejected": True,
            "workingDirectory": codex_home.as_posix(),
            "filesBefore": files_before,
            "filesAfter": files_after,
            "removedAccountEnvironmentKeysPresentBefore": removed_keys,
            "accountEnvironmentValuesRecorded": False,
            "currentConfigCopied": False,
            "currentAuthCopied": False,
            "currentPluginsCopied": False,
            "analyticsExplicitlyDisabled": True,
            "authStateProduced": False,
        },
        "requestMethods": [request["method"] for request in requests],
        "response": response_summary,
        "stdoutMessageCount": len(messages),
        "stderrLines": stderr_lines,
        "claimBoundary": {
            "provesIsolatedAppServerHandshake": True,
            "provesStatusListCallableWithoutThread": True,
            "provesEmptyHomeHasNoConfiguredMcpServers": response_summary["mcpStatus"]["serverCount"] == 0,
            "provesReload": False,
            "provesConfiguredServerStartup": False,
            "provesTaskEndRelease": False,
            "provesProcessRelease": False,
            "provesResourceSavings": False,
            "provesCurrentDesktopAccountOrPluginState": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--codex-home", type=Path, required=True)
    parser.add_argument("--codex-executable")
    parser.add_argument("--timeout-seconds", type=float, default=20.0)
    arguments = parser.parse_args()
    result = run_probe(arguments.codex_home, arguments.codex_executable, arguments.timeout_seconds)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
