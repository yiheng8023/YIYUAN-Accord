#!/usr/bin/env python3
"""Probe connection-scoped subscriptions on one Codex app-server runtime.

The probe uses one isolated Codex home, one native Codex app-server process,
two independent loopback WebSocket connections, one loaded thread, and one
local MCP Sentinel process. It starts no model turn. The first connection starts
a non-ephemeral thread and waits for its isolated rollout to materialize. Only
then does the second connection initialize and join the already-running thread
with ``thread/resume``. The two connections then demonstrate connection-scoped
unsubscribe responses while direct Sentinel calls continue to bind to the same
exact child identity.

This is a topology and ownership preflight. It does not claim a public lease or
reference-count API, task-end semantics, final release, resource benefit, or
cross-host behavior.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import queue
import socket
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
        sha256_bytes,
        summarize_tool_call,
    )
    from .probe_codex_app_server_mcp_reload_release_attribution import (
        _cleanup_lingering_sentinels,
        read_executable_version,
    )
    from .probe_codex_app_server_mcp_status import (
        build_command,
        drain_stdout_queue,
        inventory_files,
        wait_for_response,
    )
    from .probe_codex_app_server_mcp_thread_unsubscribe_release_attribution import (
        bind_sentinel_process,
        build_minimal_child_environment,
    )
    from .probe_codex_app_server_mcp_tool_call import (
        SERVER_NAME,
        build_isolated_config,
        extract_thread_id,
        load_events,
        resolve_native_codex_executable,
    )
except ImportError:  # pragma: no cover - direct script execution
    from probe_codex_app_server_mcp_idle_unload import (
        process_identity_complete,
        same_process_identity,
        snapshot_process,
    )
    from probe_codex_app_server_mcp_reload_new_threads import (
        atomic_replace_bytes,
        sha256_bytes,
        summarize_tool_call,
    )
    from probe_codex_app_server_mcp_reload_release_attribution import (
        _cleanup_lingering_sentinels,
        read_executable_version,
    )
    from probe_codex_app_server_mcp_status import (
        build_command,
        drain_stdout_queue,
        inventory_files,
        wait_for_response,
    )
    from probe_codex_app_server_mcp_thread_unsubscribe_release_attribution import (
        bind_sentinel_process,
        build_minimal_child_environment,
    )
    from probe_codex_app_server_mcp_tool_call import (
        SERVER_NAME,
        build_isolated_config,
        extract_thread_id,
        load_events,
        resolve_native_codex_executable,
    )


PROBE_ID = "codex-app-server-mcp-multi-connection-subscription-v1"
EXPECTED_SEQUENCES = {
    "thread-created-auto-attach": {
        "owner-a": [
            "initialize",
            "initialized",
            "thread/start",
            "mcpServer/tool/call",
            "thread/unsubscribe",
            "thread/unsubscribe",
        ],
        "owner-b": [
            "initialize",
            "initialized",
            "config/read",
            "mcpServer/tool/call",
            "mcpServer/tool/call",
            "thread/unsubscribe",
            "thread/unsubscribe",
        ],
    },
    "thread-resume": {
        "owner-a": [
            "initialize",
            "initialized",
            "thread/start",
            "mcpServer/tool/call",
            "thread/unsubscribe",
            "thread/unsubscribe",
        ],
        "owner-b": [
            "initialize",
            "initialized",
            "config/read",
            "thread/resume",
            "mcpServer/tool/call",
            "mcpServer/tool/call",
            "thread/unsubscribe",
            "thread/unsubscribe",
        ],
    },
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_json_sha256(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest().upper()


def _normalized_image(value: Any) -> str:
    return os.path.normcase(str(Path(str(value)).resolve()))


def allocate_loopback_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def build_thread_start_params(workspace: Path) -> dict[str, Any]:
    return {
        "cwd": workspace.resolve().as_posix(),
        "ephemeral": False,
        "approvalPolicy": "never",
        "sandbox": "read-only",
        "name": PROBE_ID,
    }


def build_tool_params(
    thread_id: str,
    owner_id: str,
    phase: str,
) -> dict[str, Any]:
    return {
        "threadId": thread_id,
        "server": SERVER_NAME,
        "tool": "identity",
        "arguments": {
            "probe": PROBE_ID,
            "owner": owner_id,
            "phase": phase,
        },
    }


def response_status(response: dict[str, Any]) -> str | None:
    result = response.get("result")
    status = result.get("status") if isinstance(result, dict) else None
    return status if isinstance(status, str) else None


def extract_thread_path(response: dict[str, Any]) -> Path:
    result = response.get("result")
    thread = result.get("thread") if isinstance(result, dict) else None
    value = thread.get("path") if isinstance(thread, dict) else None
    if not isinstance(value, str) or not value:
        raise RuntimeError("thread/start response omitted thread.path")
    return Path(value).resolve()


def wait_for_rollout(
    path: Path,
    *,
    timeout_seconds: float,
) -> dict[str, Any]:
    started = time.monotonic()
    deadline = started + timeout_seconds
    while time.monotonic() < deadline:
        if path.is_file() and path.stat().st_size > 0:
            return {
                "path": path.as_posix(),
                "bytes": path.stat().st_size,
                "waitSeconds": time.monotonic() - started,
            }
        time.sleep(0.02)
    raise RuntimeError(f"thread rollout did not materialize: {path}")


class WebSocketJsonRpcConnection:
    def __init__(
        self,
        *,
        owner_id: str,
        url: str,
        bridge_script: Path,
        node_executable: str,
        timeout_seconds: float,
    ) -> None:
        self.owner_id = owner_id
        self.url = url
        self.bridge_script = bridge_script.resolve()
        self.node_executable = node_executable
        self.timeout_seconds = timeout_seconds
        self.process: subprocess.Popen[str] | None = None
        self.stdout_queue: queue.Queue[str | None] = queue.Queue()
        self.stderr_queue: queue.Queue[str | None] = queue.Queue()
        self.stderr_lines: list[str] = []
        self.messages: list[dict[str, Any]] = []
        self.ledger: list[dict[str, Any]] = []
        self.pending: dict[int, dict[str, Any]] = {}
        self.stdout_thread: threading.Thread | None = None
        self.stderr_thread: threading.Thread | None = None
        self.process_identity: dict[str, Any] = {}
        self.ready_line = ""
        self.kill_sent = False

    def _process(self) -> subprocess.Popen[str]:
        if self.process is None:
            raise RuntimeError(f"{self.owner_id} bridge has not started")
        return self.process

    def _read_stdout(self) -> None:
        process = self._process()
        assert process.stdout is not None
        for line in process.stdout:
            self.stdout_queue.put(line)
        self.stdout_queue.put(None)

    def _read_stderr(self) -> None:
        process = self._process()
        assert process.stderr is not None
        for line in process.stderr:
            value = line.rstrip("\r\n")
            self.stderr_lines.append(value)
            self.stderr_queue.put(value)
        self.stderr_queue.put(None)

    def start(self) -> None:
        creationflags = (
            subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        )
        self.process = subprocess.Popen(
            [
                self.node_executable,
                str(self.bridge_script),
                self.url,
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=creationflags,
        )
        self.process_identity = snapshot_process(self.process.pid)
        if not process_identity_complete(self.process_identity):
            raise RuntimeError(
                f"{self.owner_id} bridge process identity is incomplete"
            )
        self.stdout_thread = threading.Thread(
            target=self._read_stdout, daemon=True
        )
        self.stderr_thread = threading.Thread(
            target=self._read_stderr, daemon=True
        )
        self.stdout_thread.start()
        self.stderr_thread.start()
        deadline = time.monotonic() + self.timeout_seconds
        while time.monotonic() < deadline:
            remaining = max(0.01, deadline - time.monotonic())
            try:
                line = self.stderr_queue.get(timeout=min(0.25, remaining))
            except queue.Empty:
                if self.process.poll() is not None:
                    break
                continue
            if line is None:
                break
            if line.startswith("BRIDGE_READY "):
                self.ready_line = line
                return
            if line.startswith("BRIDGE_FATAL "):
                raise RuntimeError(f"{self.owner_id} {line}")
        raise RuntimeError(
            f"{self.owner_id} bridge did not become ready: "
            + " | ".join(self.stderr_lines[-5:])
        )

    def _write(self, message: dict[str, Any]) -> None:
        process = self._process()
        if process.stdin is None or process.stdin.closed:
            raise RuntimeError(f"{self.owner_id} bridge stdin is closed")
        process.stdin.write(
            json.dumps(message, ensure_ascii=False, separators=(",", ":"))
            + "\n"
        )
        process.stdin.flush()

    def notify(
        self,
        method: str,
        params: dict[str, Any] | None,
        *,
        phase: str,
        thread_id: str | None = None,
    ) -> None:
        message: dict[str, Any] = {"method": method}
        if params is not None:
            message["params"] = params
        entry = {
            "ownerId": self.owner_id,
            "bridgePid": self._process().pid,
            "transportUrl": self.url,
            "id": None,
            "method": method,
            "phase": phase,
            "threadId": thread_id,
            "requestSha256": canonical_json_sha256(message),
            "sentAt": utc_now(),
            "sentMonotonic": time.monotonic(),
            "responseExpected": False,
        }
        self._write(message)
        self.ledger.append(entry)

    def send_request(
        self,
        request_id: int,
        method: str,
        params: dict[str, Any] | None,
        *,
        phase: str,
        thread_id: str | None = None,
    ) -> None:
        message = {
            "id": request_id,
            "method": method,
            "params": params,
        }
        entry = {
            "ownerId": self.owner_id,
            "bridgePid": self._process().pid,
            "transportUrl": self.url,
            "id": request_id,
            "method": method,
            "phase": phase,
            "threadId": thread_id,
            "requestSha256": canonical_json_sha256(message),
            "sentAt": utc_now(),
            "sentMonotonic": time.monotonic(),
            "responseExpected": True,
        }
        self._write(message)
        self.ledger.append(entry)
        self.pending[request_id] = entry

    def wait_response(self, request_id: int) -> dict[str, Any]:
        entry = self.pending.get(request_id)
        if entry is None:
            raise RuntimeError(
                f"{self.owner_id} request {request_id} is not pending"
            )
        response = wait_for_response(
            self.stdout_queue,
            request_id,
            time.monotonic() + self.timeout_seconds,
            self.messages,
        )
        entry["responseAt"] = utc_now()
        entry["responseMonotonic"] = time.monotonic()
        entry["responseSha256"] = canonical_json_sha256(response)
        entry["succeeded"] = "error" not in response
        entry["error"] = response.get("error")
        self.pending.pop(request_id, None)
        return response

    def request(
        self,
        request_id: int,
        method: str,
        params: dict[str, Any] | None,
        *,
        phase: str,
        thread_id: str | None = None,
    ) -> dict[str, Any]:
        self.send_request(
            request_id,
            method,
            params,
            phase=phase,
            thread_id=thread_id,
        )
        response = self.wait_response(request_id)
        if "error" in response:
            raise RuntimeError(
                f"{self.owner_id} {method} failed: {response['error']}"
            )
        return response

    def initialize(self, expected_home: Path) -> dict[str, Any]:
        response = self.request(
            0,
            "initialize",
            {
                "clientInfo": {
                    "name": PROBE_ID,
                    "title": "MCP Multi-Connection Subscription Probe",
                    "version": "1.0.0",
                }
            },
            phase="initialize",
        )
        result = response.get("result")
        if not isinstance(result, dict):
            raise RuntimeError(
                f"{self.owner_id} initialize result is not an object"
            )
        actual_home = Path(str(result.get("codexHome"))).resolve()
        if os.path.normcase(str(actual_home)) != os.path.normcase(
            str(expected_home.resolve())
        ):
            raise RuntimeError(
                f"{self.owner_id} observed unexpected Codex home"
            )
        self.notify("initialized", None, phase="initialized")
        return response

    def close(self) -> dict[str, Any]:
        process = self._process()
        if process.stdin is not None and not process.stdin.closed:
            process.stdin.close()
        if process.poll() is None:
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.kill_sent = True
                process.kill()
                process.wait(timeout=3)
        if self.stdout_thread is not None:
            self.stdout_thread.join(timeout=1)
        if self.stderr_thread is not None:
            self.stderr_thread.join(timeout=1)
        drain_stdout_queue(self.stdout_queue, self.messages)
        return {
            "returnCode": process.returncode,
            "killSent": self.kill_sent,
            "stderrLines": self.stderr_lines,
        }


def classify_preflight(
    *,
    acquisition_path: str,
    app_server_process: dict[str, Any],
    executable: str,
    owner_a_bridge: dict[str, Any],
    owner_b_bridge: dict[str, Any],
    owner_a_ledger: list[dict[str, Any]],
    owner_b_ledger: list[dict[str, Any]],
    thread_id_a: str,
    thread_id_b: str,
    owner_a_baseline: dict[str, Any],
    owner_b_join_call: dict[str, Any],
    owner_b_after_a_release: dict[str, Any],
    sentinel_process: dict[str, Any],
    owner_a_statuses: list[str | None],
    owner_b_statuses: list[str | None],
    events_before_harness_shutdown: list[dict[str, Any]],
    app_server_alive_before_harness_shutdown: bool,
    messages: list[dict[str, Any]],
) -> dict[str, Any]:
    invalid_reasons: list[str] = []
    expected_sequences = EXPECTED_SEQUENCES.get(acquisition_path)
    if expected_sequences is None:
        invalid_reasons.append("unsupported-acquisition-path")
        expected_sequences = {"owner-a": [], "owner-b": []}
    if not process_identity_complete(app_server_process):
        invalid_reasons.append("app-server-identity-incomplete")
    elif _normalized_image(app_server_process.get("imagePath")) != (
        _normalized_image(executable)
    ):
        invalid_reasons.append("app-server-image-mismatch")
    if not process_identity_complete(owner_a_bridge) or not (
        process_identity_complete(owner_b_bridge)
    ):
        invalid_reasons.append("bridge-identity-incomplete")
    if owner_a_bridge.get("pid") == owner_b_bridge.get("pid"):
        invalid_reasons.append("connections-not-distinct")
    if thread_id_a != thread_id_b:
        invalid_reasons.append("thread-id-mismatch")
    if not same_process_identity(
        sentinel_process,
        snapshot_process(int(owner_a_baseline.get("pid", -1))),
    ):
        invalid_reasons.append("baseline-sentinel-process-drift")
    exact_calls = (
        owner_a_baseline,
        owner_b_join_call,
        owner_b_after_a_release,
    )
    instance_pairs = {
        (call.get("pid"), call.get("instanceId")) for call in exact_calls
    }
    if len(instance_pairs) != 1:
        invalid_reasons.append("sentinel-call-identity-mismatch")
    if owner_a_statuses != ["unsubscribed", "notSubscribed"]:
        invalid_reasons.append("owner-a-unsubscribe-sequence-mismatch")
    owner_b_subscription_observed = owner_b_statuses == [
        "unsubscribed",
        "notSubscribed",
    ]
    owner_b_subscription_not_observed = owner_b_statuses == [
        "notSubscribed",
        "notSubscribed",
    ]
    if not (
        owner_b_subscription_observed
        or owner_b_subscription_not_observed
    ):
        invalid_reasons.append("owner-b-unsubscribe-sequence-mismatch")
    ledgers = {
        "owner-a": owner_a_ledger,
        "owner-b": owner_b_ledger,
    }
    for owner_id, ledger in ledgers.items():
        methods = [str(entry.get("method")) for entry in ledger]
        if methods != expected_sequences[owner_id]:
            invalid_reasons.append(f"{owner_id}-method-sequence-mismatch")
        if any(
            entry.get("method")
            not in {"initialize", "initialized", "config/read"}
            and entry.get("threadId") != thread_id_a
            for entry in ledger
        ):
            invalid_reasons.append(f"{owner_id}-thread-binding-mismatch")
        if any(
            not isinstance(entry.get("requestSha256"), str)
            or (
                entry.get("responseExpected") is True
                and not isinstance(entry.get("responseSha256"), str)
            )
            for entry in ledger
        ):
            invalid_reasons.append(f"{owner_id}-ledger-hash-missing")
    all_methods = [
        str(entry.get("method"))
        for ledger in ledgers.values()
        for entry in ledger
    ]
    if "turn/start" in all_methods:
        invalid_reasons.append("model-turn-requested")
    if any(
        message.get("method") in {"turn/started", "turn/start"}
        for message in messages
    ):
        invalid_reasons.append("model-turn-notification-observed")
    instance_id = owner_a_baseline.get("instanceId")
    pid = owner_a_baseline.get("pid")
    starts = [
        event
        for event in events_before_harness_shutdown
        if event.get("event") == "instance-start"
        and event.get("instanceId") == instance_id
        and event.get("pid") == pid
    ]
    stops = [
        event
        for event in events_before_harness_shutdown
        if event.get("event") == "instance-stop"
        and event.get("instanceId") == instance_id
        and event.get("pid") == pid
    ]
    if len(starts) != 1:
        invalid_reasons.append("sentinel-start-binding-not-unique")
    if stops:
        invalid_reasons.append("sentinel-stopped-before-harness-shutdown")
    if not app_server_alive_before_harness_shutdown:
        invalid_reasons.append("app-server-exited-before-harness-shutdown")
    valid = not invalid_reasons
    overlap_observed = valid and owner_b_subscription_observed
    return {
        "classification": (
            "multi-connection-overlapping-subscription-observed-bounded"
            if overlap_observed
            else (
                "second-connection-subscription-not-observed-bounded"
                if valid
                else "multi-connection-subscription-preflight-invalid"
            )
        ),
        "valid": valid,
        "invalidReasons": sorted(set(invalid_reasons)),
        "distinctClientConnectionsObserved": (
            valid and owner_a_bridge.get("pid") != owner_b_bridge.get("pid")
        ),
        "sameLoadedThreadObserved": valid and thread_id_a == thread_id_b,
        "sameExactSentinelObservedAcrossConnections": (
            valid and len(instance_pairs) == 1
        ),
        "firstConnectionReleasePreservedSecondConnectionCall": valid,
        "secondConnectionSubscriptionObserved": overlap_observed,
        "overlappingSubscriptionObserved": overlap_observed,
        "connectionScopedUnsubscribeResponsesObserved": overlap_observed,
        "publicSubscriberCountObserved": False,
        "publicLeaseOrReferenceCountApiObserved": False,
        "finalReleaseObserved": False,
        "taskEndSemanticsObserved": False,
        "resourceBenefitMeasured": False,
        "modelTurnRequested": "turn/start" in all_methods,
    }


def run_probe(
    *,
    root: Path,
    workspace: Path,
    sentinel_script: Path,
    bridge_script: Path,
    codex_executable: str | None,
    node_executable: str,
    timeout_seconds: float,
    acquisition_path: str,
) -> dict[str, Any]:
    if os.name != "nt":
        raise RuntimeError("exact process attribution currently requires Windows")
    root = root.resolve()
    workspace = workspace.resolve()
    sentinel_script = sentinel_script.resolve()
    bridge_script = bridge_script.resolve()
    if root.exists() and any(root.iterdir()):
        raise RuntimeError("probe root must be absent or empty")
    if acquisition_path not in EXPECTED_SEQUENCES:
        raise RuntimeError(
            f"unsupported acquisition path: {acquisition_path}"
        )
    if not sentinel_script.is_file():
        raise RuntimeError(f"Sentinel script is missing: {sentinel_script}")
    if not bridge_script.is_file():
        raise RuntimeError(f"WebSocket bridge is missing: {bridge_script}")
    root.mkdir(parents=True, exist_ok=True)
    workspace.mkdir(parents=True, exist_ok=True)
    codex_home = root / "codex-home"
    codex_home.mkdir(parents=True, exist_ok=True)
    event_log = codex_home / "sentinel-events.jsonl"
    cleanup_marker = codex_home / "harness-cleanup.marker"
    config_path = codex_home / "config.toml"
    config_bytes = build_isolated_config(
        Path(sys.executable),
        sentinel_script,
        event_log,
        enabled=True,
        cleanup_marker=cleanup_marker,
    ).encode("utf-8")
    config_hash = sha256_bytes(config_bytes)
    if atomic_replace_bytes(config_path, config_bytes) != config_hash:
        raise RuntimeError("isolated config hash verification failed")
    files_before = inventory_files(codex_home)
    executable = resolve_native_codex_executable(codex_executable)
    codex_version = read_executable_version(executable)
    port = allocate_loopback_port()
    listen_url = f"ws://127.0.0.1:{port}"
    environment, environment_key_names = build_minimal_child_environment(
        codex_home
    )
    command = [
        executable,
        "app-server",
        "--listen",
        listen_url,
        "--strict-config",
        "-c",
        "analytics.enabled=false",
        "--disable",
        "plugins",
        "--disable",
        "remote_plugin",
        "--disable",
        "apps",
        "--disable",
        "plugin_sharing",
    ]
    creationflags = subprocess.CREATE_NO_WINDOW
    app_server = subprocess.Popen(
        command,
        cwd=workspace,
        env=environment,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=creationflags,
    )
    app_server_identity = snapshot_process(app_server.pid)
    if not process_identity_complete(app_server_identity):
        raise RuntimeError("app-server exact process identity is incomplete")
    if _normalized_image(app_server_identity.get("imagePath")) != (
        _normalized_image(executable)
    ):
        raise RuntimeError("app-server exact image does not match executable")
    app_stdout: list[str] = []
    app_stderr: list[str] = []

    def read_stream(stream: Any, destination: list[str]) -> None:
        for line in stream:
            destination.append(line.rstrip("\r\n"))

    assert app_server.stdout is not None
    assert app_server.stderr is not None
    app_stdout_thread = threading.Thread(
        target=read_stream, args=(app_server.stdout, app_stdout), daemon=True
    )
    app_stderr_thread = threading.Thread(
        target=read_stream, args=(app_server.stderr, app_stderr), daemon=True
    )
    app_stdout_thread.start()
    app_stderr_thread.start()
    connections = {
        owner_id: WebSocketJsonRpcConnection(
            owner_id=owner_id,
            url=listen_url,
            bridge_script=bridge_script,
            node_executable=node_executable,
            timeout_seconds=timeout_seconds,
        )
        for owner_id in ("owner-a", "owner-b")
    }
    thread_id = ""
    owner_a_baseline: dict[str, Any] = {}
    owner_b_join_call: dict[str, Any] = {}
    owner_b_after_a_release: dict[str, Any] = {}
    sentinel_process: dict[str, Any] = {}
    owner_a_statuses: list[str | None] = []
    owner_b_statuses: list[str | None] = []
    events_before_harness_shutdown: list[dict[str, Any]] = []
    rollout_materialization: dict[str, Any] = {}
    classification: dict[str, Any] = {}
    app_server_alive_before_harness_shutdown = False
    bridge_shutdown: dict[str, Any] = {}
    app_server_termination_by_harness = False
    app_server_kill_sent = False
    cleanup: dict[str, Any] = {}
    failure: BaseException | None = None
    started_at = utc_now()
    try:
        owner_a = connections["owner-a"]
        owner_a.start()
        owner_a.initialize(codex_home)
        owner_b = connections["owner-b"]
        if acquisition_path == "thread-created-auto-attach":
            owner_b.start()
            owner_b.initialize(codex_home)
            owner_b.request(
                1,
                "config/read",
                {
                    "cwd": workspace.as_posix(),
                    "includeLayers": False,
                },
                phase="owner-b-initialized-barrier",
            )
        start_response = owner_a.request(
            1,
            "thread/start",
            build_thread_start_params(workspace),
            phase="thread-start",
        )
        thread_id = extract_thread_id(start_response)
        owner_a.ledger[-1]["threadId"] = thread_id
        if acquisition_path == "thread-resume":
            rollout_materialization = wait_for_rollout(
                extract_thread_path(start_response),
                timeout_seconds=timeout_seconds,
            )
        baseline_response = owner_a.request(
            2,
            "mcpServer/tool/call",
            build_tool_params(thread_id, "owner-a", "baseline"),
            phase="owner-a-baseline-call",
            thread_id=thread_id,
        )
        owner_a_baseline = summarize_tool_call(baseline_response)
        sentinel_process = bind_sentinel_process(
            owner_a_baseline, app_server_pid=app_server.pid
        )

        if acquisition_path == "thread-resume":
            owner_b.start()
            owner_b.initialize(codex_home)
            owner_b.request(
                1,
                "config/read",
                {
                    "cwd": workspace.as_posix(),
                    "includeLayers": False,
                },
                phase="owner-b-initialized-barrier",
            )
            resume_response = owner_b.request(
                2,
                "thread/resume",
                {"threadId": thread_id},
                phase="thread-resume",
                thread_id=thread_id,
            )
            thread_id_b = extract_thread_id(resume_response)
            owner_b_next_id = 3
        else:
            thread_id_b = thread_id
            owner_b_next_id = 2
        joined_response = owner_b.request(
            owner_b_next_id,
            "mcpServer/tool/call",
            build_tool_params(thread_id, "owner-b", "joined"),
            phase="owner-b-joined-call",
            thread_id=thread_id,
        )
        owner_b_join_call = summarize_tool_call(joined_response)

        owner_a_statuses.append(
            response_status(
                owner_a.request(
                    3,
                    "thread/unsubscribe",
                    {"threadId": thread_id},
                    phase="owner-a-unsubscribe",
                    thread_id=thread_id,
                )
            )
        )
        owner_a_statuses.append(
            response_status(
                owner_a.request(
                    4,
                    "thread/unsubscribe",
                    {"threadId": thread_id},
                    phase="owner-a-second-unsubscribe",
                    thread_id=thread_id,
                )
            )
        )
        after_release_response = owner_b.request(
            owner_b_next_id + 1,
            "mcpServer/tool/call",
            build_tool_params(thread_id, "owner-b", "after-owner-a-release"),
            phase="owner-b-after-owner-a-release",
            thread_id=thread_id,
        )
        owner_b_after_a_release = summarize_tool_call(after_release_response)
        owner_b_statuses.append(
            response_status(
                owner_b.request(
                    owner_b_next_id + 2,
                    "thread/unsubscribe",
                    {"threadId": thread_id},
                    phase="owner-b-unsubscribe",
                    thread_id=thread_id,
                )
            )
        )
        owner_b_statuses.append(
            response_status(
                owner_b.request(
                    owner_b_next_id + 3,
                    "thread/unsubscribe",
                    {"threadId": thread_id},
                    phase="owner-b-second-unsubscribe",
                    thread_id=thread_id,
                )
            )
        )
        events_before_harness_shutdown = load_events(event_log)
        app_server_alive_before_harness_shutdown = app_server.poll() is None
        classification = classify_preflight(
            acquisition_path=acquisition_path,
            app_server_process=app_server_identity,
            executable=executable,
            owner_a_bridge=owner_a.process_identity,
            owner_b_bridge=owner_b.process_identity,
            owner_a_ledger=owner_a.ledger,
            owner_b_ledger=owner_b.ledger,
            thread_id_a=thread_id,
            thread_id_b=thread_id_b,
            owner_a_baseline=owner_a_baseline,
            owner_b_join_call=owner_b_join_call,
            owner_b_after_a_release=owner_b_after_a_release,
            sentinel_process=sentinel_process,
            owner_a_statuses=owner_a_statuses,
            owner_b_statuses=owner_b_statuses,
            events_before_harness_shutdown=events_before_harness_shutdown,
            app_server_alive_before_harness_shutdown=(
                app_server_alive_before_harness_shutdown
            ),
            messages=owner_a.messages + owner_b.messages,
        )
    except BaseException as error:
        failure = error
    finally:
        for owner_id in ("owner-b", "owner-a"):
            connection = connections[owner_id]
            if connection.process is not None:
                bridge_shutdown[owner_id] = connection.close()
        if app_server.poll() is None:
            app_server_termination_by_harness = True
            app_server.terminate()
            try:
                app_server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                app_server_kill_sent = True
                app_server.kill()
                app_server.wait(timeout=5)
        app_stdout_thread.join(timeout=1)
        app_stderr_thread.join(timeout=1)
        cleanup = _cleanup_lingering_sentinels(event_log, cleanup_marker)
    if failure is not None:
        detail = " | ".join(app_stderr[-20:])
        raise RuntimeError(
            f"{failure}; appServerReturnCode={app_server.returncode}; "
            f"appServerStderr={detail}"
        ) from failure
    if cleanup.get("cleanupVerified") is not True:
        raise RuntimeError("Sentinel cleanup was not verified")
    files_after = inventory_files(codex_home)
    if any(
        str(item.get("path", "")).lower().endswith("auth.json")
        for item in files_after
    ):
        raise RuntimeError("probe unexpectedly produced auth state")
    external_network_attempt_lines = [
        line
        for line in app_stderr
        if "https://" in line or "http://" in line or "wss://" in line
    ]
    all_messages = [
        message
        for connection in connections.values()
        for message in connection.messages
    ]
    report = {
        "schemaVersion": 1,
        "probeId": PROBE_ID,
        "startedAt": started_at,
        "finishedAt": utc_now(),
        "host": {
            "platform": sys.platform,
            "codexVersion": codex_version,
            "codexExecutable": executable,
            "appServerProcess": app_server_identity,
            "listenUrl": listen_url,
            "transport": "loopback-websocket",
            "singleAppServerProcess": True,
            "appServerAliveBeforeHarnessShutdown": (
                app_server_alive_before_harness_shutdown
            ),
            "appServerTerminationByHarness": app_server_termination_by_harness,
            "appServerKillSent": app_server_kill_sent,
            "applicationLogExternalNetworkAttemptObserved": bool(
                external_network_attempt_lines
            ),
            "applicationLogExternalNetworkAttemptLines": (
                external_network_attempt_lines
            ),
        },
        "isolation": {
            "root": root.as_posix(),
            "codexHome": codex_home.as_posix(),
            "workspace": workspace.as_posix(),
            "configSha256": config_hash,
            "filesBefore": files_before,
            "filesAfter": files_after,
            "environmentAllowlistApplied": True,
            "environmentKeyNames": environment_key_names,
            "environmentValuesRecorded": False,
            "authStateProduced": False,
            "pluginsAndAppsDisabled": True,
        },
        "bindings": {
            "probeScript": {
                "path": Path(__file__).resolve().as_posix(),
                "sha256": sha256_bytes(Path(__file__).read_bytes()),
            },
            "bridgeScript": {
                "path": bridge_script.as_posix(),
                "sha256": sha256_bytes(bridge_script.read_bytes()),
            },
            "sentinelScript": {
                "path": sentinel_script.as_posix(),
                "sha256": sha256_bytes(sentinel_script.read_bytes()),
            },
        },
        "thread": {
            "id": thread_id,
            "ephemeral": False,
            "subscriptionAcquisitionPath": acquisition_path,
            "rolloutMaterialization": rollout_materialization,
            "ownerBInitializedBarrier": "config/read",
            "modelTurnRequests": sum(
                1
                for connection in connections.values()
                for entry in connection.ledger
                if entry.get("method") == "turn/start"
            ),
            "turnStartedNotifications": sum(
                1
                for message in all_messages
                if message.get("method") in {"turn/started", "turn/start"}
            ),
        },
        "connections": {
            owner_id: {
                "bridgeProcess": connection.process_identity,
                "readyLine": connection.ready_line,
                "requestLedger": connection.ledger,
                "messages": connection.messages,
                "shutdown": bridge_shutdown.get(owner_id),
            }
            for owner_id, connection in connections.items()
        },
        "sentinel": {
            "baselineCall": owner_a_baseline,
            "ownerBJoinedCall": owner_b_join_call,
            "ownerBAfterOwnerAReleaseCall": owner_b_after_a_release,
            "process": sentinel_process,
            "eventsBeforeHarnessShutdown": events_before_harness_shutdown,
            "cleanup": cleanup,
        },
        "unsubscribe": {
            "ownerAStatuses": owner_a_statuses,
            "ownerBStatuses": owner_b_statuses,
        },
        "classification": classification,
        "claimBoundary": {
            "provesDistinctPublicConnectionIds": False,
            "provesPublicLeaseOrReferenceCountApi": False,
            "provesInternalReferenceCountCorrectness": False,
            "provesTaskEndRelease": False,
            "provesFinalSubscriberRelease": False,
            "provesResourceBenefit": False,
            "provesArbitraryMcpBehavior": False,
            "provesCrossHostOrVersionParity": False,
            "noModelTurnRequestProvesNoNetwork": False,
        },
    }
    report["reportSha256"] = canonical_json_sha256(report)
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument(
        "--sentinel-script",
        type=Path,
        default=Path(__file__).resolve().with_name(
            "mcp_lifecycle_sentinel.py"
        ),
    )
    parser.add_argument(
        "--bridge-script",
        type=Path,
        default=Path(__file__).resolve().with_name(
            "codex_app_server_websocket_bridge.mjs"
        ),
    )
    parser.add_argument("--codex-executable")
    parser.add_argument("--node-executable", default="node")
    parser.add_argument("--timeout-seconds", type=float, default=30.0)
    parser.add_argument(
        "--acquisition-path",
        choices=sorted(EXPECTED_SEQUENCES),
        default="thread-created-auto-attach",
    )
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run_probe(
        root=args.root,
        workspace=args.workspace,
        sentinel_script=args.sentinel_script,
        bridge_script=args.bridge_script,
        codex_executable=args.codex_executable,
        node_executable=args.node_executable,
        timeout_seconds=args.timeout_seconds,
        acquisition_path=args.acquisition_path,
    )
    encoded = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    else:
        print(encoded, end="")
    return 0 if report["classification"]["valid"] is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
