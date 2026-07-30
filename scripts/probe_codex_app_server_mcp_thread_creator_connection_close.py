#!/usr/bin/env python3
"""Pair-isolate closing the WebSocket connection that created a thread.

Each arm owns one isolated Codex app-server, two independent loopback
WebSocket bridge processes, one loaded thread, and one exact local Sentinel
process.  The treatment closes only creator connection A; observer connection
B and the app-server remain alive.  The control performs no transport action.
During the five-second window the parent samples exact process identities and
reads local Sentinel events.  It sends no host RPC in either arm.

This probe deliberately calls the treatment a creator-connection close, not a
lease release or task end.  It does not establish public subscription counts,
reference-count semantics, resource benefit, cross-version parity, or
arbitrary MCP behavior.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
import os
from pathlib import Path
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
    from .probe_codex_app_server_mcp_multi_connection_subscription import (
        WebSocketJsonRpcConnection,
        allocate_loopback_port,
        build_thread_start_params,
        canonical_json_sha256,
        extract_thread_path,
    )
    from .probe_codex_app_server_mcp_reload_new_threads import (
        atomic_replace_bytes,
        sha256_bytes,
        summarize_tool_call,
    )
    from .probe_codex_app_server_mcp_reload_release_attribution import (
        _cleanup_lingering_sentinels,
        read_executable_version,
        stop_events_in_window,
    )
    from .probe_codex_app_server_mcp_status import inventory_files
    from .probe_codex_app_server_mcp_thread_unsubscribe_release_attribution import (
        MAX_SAMPLE_SKEW_MILLISECONDS,
        bind_sentinel_process,
        build_minimal_child_environment,
    )
    from .probe_codex_app_server_mcp_tool_call import (
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
    from probe_codex_app_server_mcp_multi_connection_subscription import (
        WebSocketJsonRpcConnection,
        allocate_loopback_port,
        build_thread_start_params,
        canonical_json_sha256,
        extract_thread_path,
    )
    from probe_codex_app_server_mcp_reload_new_threads import (
        atomic_replace_bytes,
        sha256_bytes,
        summarize_tool_call,
    )
    from probe_codex_app_server_mcp_reload_release_attribution import (
        _cleanup_lingering_sentinels,
        read_executable_version,
        stop_events_in_window,
    )
    from probe_codex_app_server_mcp_status import inventory_files
    from probe_codex_app_server_mcp_thread_unsubscribe_release_attribution import (
        MAX_SAMPLE_SKEW_MILLISECONDS,
        bind_sentinel_process,
        build_minimal_child_environment,
    )
    from probe_codex_app_server_mcp_tool_call import (
        build_isolated_config,
        extract_thread_id,
        load_events,
        resolve_native_codex_executable,
    )


PROBE_ID = "codex-app-server-mcp-thread-creator-connection-close-v1"
ARM_CONTROL = "connected-control"
ARM_CREATOR_CLOSE = "creator-connection-close"
ARM_NAMES = (ARM_CONTROL, ARM_CREATOR_CLOSE)
MAX_ACTION_SKEW_MILLISECONDS = 100.0


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def observe_rollout_materialization(path: Path) -> dict[str, Any]:
    """Record rollout presence without making zero-turn persistence a gate."""
    path = path.resolve()
    observed = path.is_file() and path.stat().st_size > 0
    return {
        "path": path.as_posix(),
        "observed": observed,
        "bytes": path.stat().st_size if observed else None,
    }


def _sample_count(
    observation_seconds: float,
    sample_interval_seconds: float,
) -> int:
    return math.floor(observation_seconds / sample_interval_seconds) + 1


def _exact_call_pair(call: dict[str, Any]) -> tuple[Any, Any]:
    return call.get("pid"), call.get("instanceId")


def build_identity_tool_params(
    thread_id: str,
    owner: str,
    phase: str,
) -> dict[str, Any]:
    return {
        "threadId": thread_id,
        "server": "lifecycle_sentinel",
        "tool": "identity",
        "arguments": {
            "probe": PROBE_ID,
            "owner": owner,
            "phase": phase,
        },
    }


def initialize_connection(
    connection: WebSocketJsonRpcConnection,
    expected_home: Path,
) -> dict[str, Any]:
    response = connection.request(
        0,
        "initialize",
        {
            "clientInfo": {
                "name": PROBE_ID,
                "title": "MCP Thread Creator Connection Close Probe",
                "version": "1.0.0",
            }
        },
        phase="initialize",
    )
    result = response.get("result")
    if not isinstance(result, dict):
        raise RuntimeError("initialize result is not an object")
    actual_home = Path(str(result.get("codexHome"))).resolve()
    if os.path.normcase(str(actual_home)) != os.path.normcase(
        str(expected_home.resolve())
    ):
        raise RuntimeError("connection observed unexpected Codex home")
    connection.notify("initialized", None, phase="initialized")
    return response


def _clean_bridge_close(close: dict[str, Any] | None) -> bool:
    if not isinstance(close, dict):
        return False
    stderr_lines = close.get("stderrLines")
    return (
        close.get("returnCode") == 0
        and close.get("killSent") is False
        and isinstance(stderr_lines, list)
        and any(
            isinstance(line, str)
            and line.startswith("BRIDGE_CLOSED ")
            and "code=1000" in line
            and "clean=true" in line
            for line in stderr_lines
        )
    )


def collect_process_samples(
    *,
    sentinel_pid: int,
    app_server_pid: int,
    creator_bridge_pid: int,
    observer_bridge_pid: int,
    window_start_monotonic: float,
    observation_seconds: float,
    sample_interval_seconds: float,
) -> list[dict[str, Any]]:
    samples: list[dict[str, Any]] = []
    for index in range(
        _sample_count(observation_seconds, sample_interval_seconds)
    ):
        target = window_start_monotonic + index * sample_interval_seconds
        remaining = target - time.monotonic()
        if remaining > 0:
            time.sleep(remaining)
        captured = time.monotonic()
        samples.append(
            {
                "index": index,
                "targetOffsetSeconds": index * sample_interval_seconds,
                "capturedAt": utc_now(),
                "capturedMonotonic": captured,
                "sampleSkewMilliseconds": (captured - target) * 1000,
                "sentinel": snapshot_process(sentinel_pid),
                "appServer": snapshot_process(app_server_pid),
                "creatorBridge": snapshot_process(creator_bridge_pid),
                "observerBridge": snapshot_process(observer_bridge_pid),
            }
        )
    return samples


def classify_arm(
    *,
    arm: str,
    app_server_process: dict[str, Any],
    creator_bridge_process: dict[str, Any],
    observer_bridge_process: dict[str, Any],
    thread_id_a: str,
    thread_id_b: str,
    creator_baseline_call: dict[str, Any],
    observer_baseline_call: dict[str, Any],
    sentinel_process: dict[str, Any],
    start_events: list[dict[str, Any]],
    process_samples: list[dict[str, Any]],
    stop_events: list[dict[str, Any]],
    post_window_call: dict[str, Any],
    in_window_host_methods: list[str],
    transport_actions: list[dict[str, Any]],
    creator_close: dict[str, Any] | None,
    action_skew_milliseconds: float,
    observation_seconds: float,
    sample_interval_seconds: float,
    model_turn_count: int,
    turn_started_notification_count: int,
    configuration_unchanged: bool,
    auth_state_produced: bool,
    evidence_sealed_before_post_window_call: bool,
) -> dict[str, Any]:
    invalid_reasons: list[str] = []
    if arm not in ARM_NAMES:
        invalid_reasons.append("unknown-arm")
    for label, identity in (
        ("app-server", app_server_process),
        ("creator-bridge", creator_bridge_process),
        ("observer-bridge", observer_bridge_process),
        ("sentinel", sentinel_process),
    ):
        if not process_identity_complete(identity):
            invalid_reasons.append(f"{label}-identity-incomplete")
    if creator_bridge_process.get("pid") == observer_bridge_process.get("pid"):
        invalid_reasons.append("baseline-connections-not-distinct")
    if thread_id_a != thread_id_b:
        invalid_reasons.append("baseline-thread-id-mismatch")
    call_pairs = {
        _exact_call_pair(creator_baseline_call),
        _exact_call_pair(observer_baseline_call),
    }
    if len(call_pairs) != 1:
        invalid_reasons.append("baseline-sentinel-call-identity-mismatch")
    expected_pair = _exact_call_pair(creator_baseline_call)
    if (
        sentinel_process.get("pid"),
        creator_baseline_call.get("instanceId"),
    ) != expected_pair:
        invalid_reasons.append("baseline-sentinel-process-drift")
    matching_starts = [
        event
        for event in start_events
        if event.get("event") == "instance-start"
        and event.get("pid") == creator_baseline_call.get("pid")
        and event.get("instanceId")
        == creator_baseline_call.get("instanceId")
    ]
    if len(matching_starts) != 1:
        invalid_reasons.append("sentinel-start-binding-not-unique")

    expected_sample_count = _sample_count(
        observation_seconds, sample_interval_seconds
    )
    if len(process_samples) != expected_sample_count:
        invalid_reasons.append("sample-count-mismatch")
    sample_skews = [
        float(sample.get("sampleSkewMilliseconds", float("inf")))
        for sample in process_samples
    ]
    if any(
        skew < 0 or skew > MAX_SAMPLE_SKEW_MILLISECONDS
        for skew in sample_skews
    ):
        invalid_reasons.append("sample-timing-skew")

    app_server_alive = [
        sample.get("appServer", {}).get("exists") is True
        for sample in process_samples
    ]
    observer_alive = [
        sample.get("observerBridge", {}).get("exists") is True
        for sample in process_samples
    ]
    creator_alive = [
        sample.get("creatorBridge", {}).get("exists") is True
        for sample in process_samples
    ]
    if not app_server_alive or not all(app_server_alive):
        invalid_reasons.append("app-server-not-alive-through-window")
    if not observer_alive or not all(observer_alive):
        invalid_reasons.append("observer-bridge-not-alive-through-window")
    if arm == ARM_CONTROL:
        if not creator_alive or not all(creator_alive):
            invalid_reasons.append(
                "control-creator-bridge-not-alive-through-window"
            )
        if transport_actions or creator_close is not None:
            invalid_reasons.append("transport-action-ledger-mismatch")
    else:
        expected_actions = ["creator-connection-close"]
        actual_actions = [
            str(action.get("action")) for action in transport_actions
        ]
        if actual_actions != expected_actions:
            invalid_reasons.append("transport-action-ledger-mismatch")
        if (
            creator_alive
            and creator_alive[-1]
        ):
            invalid_reasons.append(
                "treatment-creator-bridge-still-alive-at-window-end"
            )
        action_process = (
            transport_actions[0].get("processIdentity")
            if len(transport_actions) == 1
            else {}
        )
        if (
            not same_process_identity(
                creator_bridge_process,
                action_process if isinstance(action_process, dict) else {},
            )
            or not same_process_identity(
                creator_bridge_process,
                (
                    creator_close.get("processIdentity", {})
                    if isinstance(creator_close, dict)
                    else {}
                ),
            )
            or not _clean_bridge_close(creator_close)
        ):
            invalid_reasons.append("creator-close-not-exactly-bound")

    if action_skew_milliseconds < 0 or (
        action_skew_milliseconds > MAX_ACTION_SKEW_MILLISECONDS
    ):
        invalid_reasons.append("action-barrier-skew-too-large")
    if in_window_host_methods:
        invalid_reasons.append("in-window-host-rpc-observed")
    if model_turn_count != 0 or turn_started_notification_count != 0:
        invalid_reasons.append("model-turn-observed")
    if configuration_unchanged is not True:
        invalid_reasons.append("configuration-drift")
    if auth_state_produced is True:
        invalid_reasons.append("auth-state-produced")
    if evidence_sealed_before_post_window_call is not True:
        invalid_reasons.append(
            "post-window-call-precedes-evidence-seal"
        )

    sentinel_samples = [
        sample.get("sentinel", {}) for sample in process_samples
    ]
    same_sentinel_by_sample = [
        same_process_identity(sentinel_process, sample)
        for sample in sentinel_samples
    ]
    final_sentinel = sentinel_samples[-1] if sentinel_samples else {}
    final_same_sentinel = (
        same_process_identity(sentinel_process, final_sentinel)
        if sentinel_samples
        else False
    )
    post_window_same_instance = (
        post_window_call.get("succeeded") is True
        and _exact_call_pair(post_window_call)
        == _exact_call_pair(creator_baseline_call)
    )
    released = bool(stop_events) and final_sentinel.get("exists") is False
    retained = (
        bool(same_sentinel_by_sample)
        and all(same_sentinel_by_sample)
        and not stop_events
        and final_same_sentinel
        and post_window_same_instance
    )

    if invalid_reasons:
        classification = "invalid"
        valid = False
    elif released:
        classification = (
            "creator-connection-close-release-observed-bounded"
            if arm == ARM_CREATOR_CLOSE
            else "connected-control-runtime-stopped-bounded"
        )
        valid = True
    elif retained:
        classification = (
            "creator-connection-close-runtime-retained-five-seconds"
            if arm == ARM_CREATOR_CLOSE
            else "connected-control-runtime-retained-five-seconds"
        )
        valid = True
    else:
        classification = "invalid"
        valid = False
        invalid_reasons.append(
            "process-and-stop-evidence-do-not-converge"
        )

    return {
        "classification": classification,
        "valid": valid,
        "invalidReasons": sorted(set(invalid_reasons)),
        "releaseObserved": released and valid,
        "runtimeRetained": retained and valid,
        "sameSentinelIdentityBySample": same_sentinel_by_sample,
        "appServerAliveBySample": app_server_alive,
        "observerBridgeAliveBySample": observer_alive,
        "creatorBridgeAliveBySample": creator_alive,
        "postWindowCallSameInstance": post_window_same_instance,
        "expectedSampleCount": expected_sample_count,
        "actualSampleCount": len(process_samples),
        "maximumSampleSkewMilliseconds": (
            max(sample_skews) if sample_skews else None
        ),
        "creatorConnectionCloseIsTaskEnd": False,
        "publicLeaseOrReferenceCountObserved": False,
    }


def classify_pair(
    control: dict[str, Any],
    treatment: dict[str, Any],
) -> dict[str, Any]:
    control_classification = control.get("classification")
    treatment_classification = treatment.get("classification")
    both_valid = (
        control.get("valid") is True
        and treatment.get("valid") is True
    )
    if (
        both_valid
        and control_classification
        == "connected-control-runtime-retained-five-seconds"
        and treatment_classification
        == "creator-connection-close-release-observed-bounded"
    ):
        classification = (
            "creator-connection-close-release-associated-bounded"
        )
        conclusive = True
        release_associated = True
        immediate_release_falsified = False
    elif (
        both_valid
        and control_classification
        == "connected-control-runtime-retained-five-seconds"
        and treatment_classification
        == "creator-connection-close-runtime-retained-five-seconds"
    ):
        classification = (
            "creator-connection-close-immediate-release-falsified-bounded"
        )
        conclusive = True
        release_associated = False
        immediate_release_falsified = True
    elif both_valid:
        classification = "inconclusive-valid-bounded"
        conclusive = False
        release_associated = False
        immediate_release_falsified = False
    else:
        classification = "invalid"
        conclusive = False
        release_associated = False
        immediate_release_falsified = False
    return {
        "classification": classification,
        "valid": both_valid,
        "conclusive": conclusive,
        "creatorConnectionCloseReleaseAssociated": release_associated,
        "creatorConnectionCloseImmediateReleaseFalsified": (
            immediate_release_falsified
        ),
        "controlClassification": control_classification,
        "treatmentClassification": treatment_classification,
    }


class AppServerConnectionArm:
    def __init__(
        self,
        *,
        arm: str,
        root: Path,
        workspace: Path,
        sentinel_script: Path,
        bridge_script: Path,
        executable: str,
        node_executable: str,
        timeout_seconds: float,
    ) -> None:
        self.arm = arm
        self.root = root.resolve()
        self.workspace = workspace.resolve()
        self.codex_home = self.root / "codex-home"
        self.sentinel_script = sentinel_script.resolve()
        self.bridge_script = bridge_script.resolve()
        self.executable = executable
        self.node_executable = node_executable
        self.timeout_seconds = timeout_seconds
        self.event_log = self.codex_home / "sentinel-events.jsonl"
        self.cleanup_marker = self.codex_home / "harness-cleanup.marker"
        self.config_path = self.codex_home / "config.toml"
        self.config_bytes = b""
        self.config_hash = ""
        self.environment_key_names: list[str] = []
        self.files_before: list[dict[str, Any]] = []
        self.app_server: subprocess.Popen[str] | None = None
        self.app_server_process: dict[str, Any] = {}
        self.app_stdout: list[str] = []
        self.app_stderr: list[str] = []
        self.app_stdout_thread: threading.Thread | None = None
        self.app_stderr_thread: threading.Thread | None = None
        self.connections: dict[str, WebSocketJsonRpcConnection] = {}
        self.thread_id = ""
        self.observer_thread_id = ""
        self.creator_baseline_call: dict[str, Any] = {}
        self.observer_baseline_call: dict[str, Any] = {}
        self.sentinel_process: dict[str, Any] = {}
        self.start_events: list[dict[str, Any]] = []
        self.rollout_path: Path | None = None
        self.rollout_materialization: dict[str, Any] = {}
        self.creator_close: dict[str, Any] | None = None

    def _app_server(self) -> subprocess.Popen[str]:
        if self.app_server is None:
            raise RuntimeError(f"{self.arm} app-server is not started")
        return self.app_server

    @staticmethod
    def _read_stream(stream: Any, destination: list[str]) -> None:
        for line in stream:
            destination.append(line.rstrip("\r\n"))

    def start(self) -> None:
        if self.root.exists() and any(self.root.iterdir()):
            raise RuntimeError(f"{self.arm} root must be absent or empty")
        self.root.mkdir(parents=True, exist_ok=True)
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.codex_home.mkdir(parents=True, exist_ok=True)
        self.config_bytes = build_isolated_config(
            Path(sys.executable),
            self.sentinel_script,
            self.event_log,
            enabled=True,
            cleanup_marker=self.cleanup_marker,
        ).encode("utf-8")
        self.config_hash = sha256_bytes(self.config_bytes)
        if (
            atomic_replace_bytes(self.config_path, self.config_bytes)
            != self.config_hash
        ):
            raise RuntimeError("isolated config hash verification failed")
        self.files_before = inventory_files(self.codex_home)
        environment, self.environment_key_names = (
            build_minimal_child_environment(self.codex_home)
        )
        port = allocate_loopback_port()
        listen_url = f"ws://127.0.0.1:{port}"
        command = [
            self.executable,
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
        self.app_server = subprocess.Popen(
            command,
            cwd=self.workspace,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        self.app_server_process = snapshot_process(self.app_server.pid)
        if not process_identity_complete(self.app_server_process):
            raise RuntimeError("app-server exact identity is incomplete")
        if os.path.normcase(
            str(Path(str(self.app_server_process["imagePath"])).resolve())
        ) != os.path.normcase(str(Path(self.executable).resolve())):
            raise RuntimeError("app-server exact image does not match executable")
        assert self.app_server.stdout is not None
        assert self.app_server.stderr is not None
        self.app_stdout_thread = threading.Thread(
            target=self._read_stream,
            args=(self.app_server.stdout, self.app_stdout),
            daemon=True,
        )
        self.app_stderr_thread = threading.Thread(
            target=self._read_stream,
            args=(self.app_server.stderr, self.app_stderr),
            daemon=True,
        )
        self.app_stdout_thread.start()
        self.app_stderr_thread.start()
        self.connections = {
            owner: WebSocketJsonRpcConnection(
                owner_id=owner,
                url=listen_url,
                bridge_script=self.bridge_script,
                node_executable=self.node_executable,
                timeout_seconds=self.timeout_seconds,
            )
            for owner in ("creator-a", "observer-b")
        }
        creator = self.connections["creator-a"]
        observer = self.connections["observer-b"]
        creator.start()
        initialize_connection(creator, self.codex_home)
        start_response = creator.request(
            1,
            "thread/start",
            {
                **build_thread_start_params(self.workspace),
                "name": f"{PROBE_ID}-{self.arm}",
            },
            phase="thread-start",
        )
        self.thread_id = extract_thread_id(start_response)
        creator.ledger[-1]["threadId"] = self.thread_id
        self.rollout_path = extract_thread_path(start_response)
        creator_response = creator.request(
            2,
            "mcpServer/tool/call",
            build_identity_tool_params(
                self.thread_id, "creator-a", "baseline"
            ),
            phase="creator-baseline",
            thread_id=self.thread_id,
        )
        self.creator_baseline_call = summarize_tool_call(creator_response)
        self.sentinel_process = bind_sentinel_process(
            self.creator_baseline_call,
            app_server_pid=self.app_server.pid,
        )
        observer.start()
        initialize_connection(observer, self.codex_home)
        observer.request(
            1,
            "config/read",
            {
                "cwd": self.workspace.as_posix(),
                "includeLayers": False,
            },
            phase="observer-initialized-barrier",
        )
        self.rollout_materialization = observe_rollout_materialization(
            self.rollout_path
        )
        resume_response = observer.request(
            2,
            "thread/resume",
            {"threadId": self.thread_id},
            phase="observer-thread-resume",
            thread_id=self.thread_id,
        )
        resumed_thread_id = extract_thread_id(resume_response)
        if resumed_thread_id != self.thread_id:
            raise RuntimeError("observer resumed a different thread")
        self.observer_thread_id = resumed_thread_id
        observer_response = observer.request(
            3,
            "mcpServer/tool/call",
            build_identity_tool_params(
                self.thread_id, "observer-b", "baseline"
            ),
            phase="observer-baseline",
            thread_id=self.thread_id,
        )
        self.observer_baseline_call = summarize_tool_call(observer_response)
        if (
            _exact_call_pair(self.creator_baseline_call)
            != _exact_call_pair(self.observer_baseline_call)
        ):
            raise RuntimeError("baseline connections saw different Sentinel")
        if not same_process_identity(
            self.sentinel_process,
            snapshot_process(int(self.creator_baseline_call["pid"])),
        ):
            raise RuntimeError("baseline Sentinel exact process drifted")
        self.start_events = load_events(self.event_log)

    def close_creator(self) -> dict[str, Any]:
        creator = self.connections["creator-a"]
        result = creator.close()
        result["processIdentity"] = creator.process_identity
        result["completedAt"] = utc_now()
        result["completedMonotonic"] = time.monotonic()
        self.creator_close = result
        return result

    def observer_post_window_call(self) -> dict[str, Any]:
        observer = self.connections["observer-b"]
        request_id = 4
        try:
            observer.send_request(
                request_id,
                "mcpServer/tool/call",
                build_identity_tool_params(
                    self.thread_id, "observer-b", "post-window"
                ),
                phase="post-window-observer-call",
                thread_id=self.thread_id,
            )
            response = observer.wait_response(request_id)
            if "error" in response:
                return {
                    "succeeded": False,
                    "error": response.get("error"),
                }
            return {
                "succeeded": True,
                **summarize_tool_call(response),
            }
        except BaseException as error:
            return {"succeeded": False, "error": str(error)}

    def shutdown_and_cleanup(self) -> dict[str, Any]:
        bridge_shutdown: dict[str, Any] = {}
        for owner in ("observer-b", "creator-a"):
            connection = self.connections.get(owner)
            if connection is None or connection.process is None:
                continue
            if owner == "creator-a" and self.creator_close is not None:
                bridge_shutdown[owner] = self.creator_close
            else:
                bridge_shutdown[owner] = connection.close()
        process = self._app_server()
        app_server_termination_by_harness = False
        app_server_kill_sent = False
        if process.poll() is None:
            app_server_termination_by_harness = True
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                app_server_kill_sent = True
                process.kill()
                process.wait(timeout=5)
        if self.app_stdout_thread is not None:
            self.app_stdout_thread.join(timeout=1)
        if self.app_stderr_thread is not None:
            self.app_stderr_thread.join(timeout=1)
        events_before_cleanup = load_events(self.event_log)
        cleanup = _cleanup_lingering_sentinels(
            self.event_log, self.cleanup_marker
        )
        files_after = inventory_files(self.codex_home)
        return {
            "bridgeShutdown": bridge_shutdown,
            "appServerReturnCode": process.returncode,
            "appServerTerminationByHarness": (
                app_server_termination_by_harness
            ),
            "appServerKillSent": app_server_kill_sent,
            "eventsBeforeHarnessCleanup": events_before_cleanup,
            "cleanup": cleanup,
            "filesAfter": files_after,
            "authStateProduced": any(
                str(item.get("path", "")).lower().endswith("auth.json")
                for item in files_after
            ),
        }


def _run_window_worker(
    *,
    session: AppServerConnectionArm,
    barrier: threading.Barrier,
    pair_clock: dict[str, Any],
    observation_seconds: float,
    sample_interval_seconds: float,
    result: dict[str, Any],
) -> None:
    barrier.wait(timeout=10)
    window_start_monotonic = float(pair_clock["monotonic"])
    window_start_utc = datetime.fromisoformat(str(pair_clock["utc"]))
    transport_actions: list[dict[str, Any]] = []
    close_result: dict[str, Any] | None = None
    close_errors: list[BaseException] = []
    close_thread: threading.Thread | None = None
    action_monotonic = time.monotonic()
    if session.arm == ARM_CREATOR_CLOSE:
        creator = session.connections["creator-a"]
        action_monotonic = time.monotonic()
        transport_actions.append(
            {
                "action": "creator-connection-close",
                "startedAt": utc_now(),
                "startedMonotonic": action_monotonic,
                "processIdentity": creator.process_identity,
                "hostRpc": False,
            }
        )

        def close_creator() -> None:
            nonlocal close_result
            try:
                close_result = session.close_creator()
            except BaseException as error:
                close_errors.append(error)

        close_thread = threading.Thread(
            target=close_creator,
            daemon=True,
        )
        close_thread.start()

    samples = collect_process_samples(
        sentinel_pid=int(session.creator_baseline_call["pid"]),
        app_server_pid=session._app_server().pid,
        creator_bridge_pid=int(
            session.connections["creator-a"].process_identity["pid"]
        ),
        observer_bridge_pid=int(
            session.connections["observer-b"].process_identity["pid"]
        ),
        window_start_monotonic=window_start_monotonic,
        observation_seconds=observation_seconds,
        sample_interval_seconds=sample_interval_seconds,
    )
    if close_thread is not None:
        close_thread.join(timeout=1)
        if close_thread.is_alive():
            close_errors.append(
                RuntimeError("creator bridge close exceeded window")
            )
    if close_errors:
        raise close_errors[0]
    window_end_utc = window_start_utc + timedelta(
        seconds=observation_seconds
    )
    events_at_window_end = load_events(session.event_log)
    stop_events = stop_events_in_window(
        events_at_window_end,
        str(session.creator_baseline_call["instanceId"]),
        window_start_utc,
        window_end_utc,
    )
    ledgers = [
        *session.connections["creator-a"].ledger,
        *session.connections["observer-b"].ledger,
    ]
    in_window_host_methods = [
        str(entry["method"])
        for entry in ledgers
        if isinstance(entry.get("sentMonotonic"), (int, float))
        and window_start_monotonic
        <= float(entry["sentMonotonic"])
        <= window_start_monotonic + observation_seconds
    ]
    configuration_unchanged = (
        session.config_path.read_bytes() == session.config_bytes
    )
    rpc_ledger_at_seal = json.loads(
        json.dumps(
            {
                owner: connection.ledger
                for owner, connection in session.connections.items()
            },
            ensure_ascii=False,
        )
    )
    seal_payload = {
        "processSamples": samples,
        "sentinelEvents": events_at_window_end,
        "rpcLedgers": rpc_ledger_at_seal,
        "transportActions": transport_actions,
        "creatorClose": close_result,
        "configSha256": sha256_bytes(session.config_path.read_bytes()),
    }
    evidence_seal = {
        "sealedAt": utc_now(),
        "sealedMonotonic": time.monotonic(),
        "sha256": canonical_json_sha256(seal_payload),
        "postWindowCallStarted": False,
    }
    post_window_call = session.observer_post_window_call()
    post_entry = session.connections["observer-b"].ledger[-1]
    post_sent_monotonic = post_entry.get("sentMonotonic")
    evidence_sealed_before_post = (
        isinstance(post_sent_monotonic, (int, float))
        and float(post_sent_monotonic)
        > float(evidence_seal["sealedMonotonic"])
    )
    evidence_seal["postWindowCallStarted"] = True
    evidence_seal["postWindowCallSentMonotonic"] = post_sent_monotonic
    result.update(
        {
            "windowStartAt": window_start_utc.isoformat(),
            "windowEndAt": window_end_utc.isoformat(),
            "windowStartMonotonic": window_start_monotonic,
            "actionMonotonic": action_monotonic,
            "actionSkewMilliseconds": (
                action_monotonic - window_start_monotonic
            )
            * 1000,
            "processSamples": samples,
            "eventsAtWindowEnd": events_at_window_end,
            "stopEventsInWindow": stop_events,
            "inWindowHostMethods": in_window_host_methods,
            "transportActions": transport_actions,
            "creatorClose": close_result,
            "configurationUnchangedAtWindowEnd": (
                configuration_unchanged
            ),
            "evidenceSeal": evidence_seal,
            "rpcLedgerAtSeal": rpc_ledger_at_seal,
            "evidenceSealedBeforePostWindowCall": (
                evidence_sealed_before_post
            ),
            "postWindowCall": post_window_call,
        }
    )


def run_probe(
    *,
    root: Path,
    workspace: Path,
    sentinel_script: Path,
    bridge_script: Path,
    codex_executable: str | None,
    node_executable: str,
    observation_seconds: float,
    sample_interval_seconds: float,
    timeout_seconds: float,
) -> dict[str, Any]:
    if os.name != "nt":
        raise RuntimeError("exact process attribution currently requires Windows")
    root = root.resolve()
    workspace = workspace.resolve()
    sentinel_script = sentinel_script.resolve()
    bridge_script = bridge_script.resolve()
    if root.exists() and any(root.iterdir()):
        raise RuntimeError("paired probe root must be absent or empty")
    if not sentinel_script.is_file():
        raise RuntimeError(f"Sentinel script is missing: {sentinel_script}")
    if not bridge_script.is_file():
        raise RuntimeError(f"WebSocket bridge is missing: {bridge_script}")
    if observation_seconds < 1:
        raise RuntimeError("observation window must be at least one second")
    if not 0 < sample_interval_seconds <= observation_seconds:
        raise RuntimeError("sample interval must be positive and within window")
    root.mkdir(parents=True, exist_ok=True)
    workspace.mkdir(parents=True, exist_ok=True)
    executable = resolve_native_codex_executable(codex_executable)
    codex_version = read_executable_version(executable)
    sessions = {
        arm: AppServerConnectionArm(
            arm=arm,
            root=root / arm,
            workspace=workspace,
            sentinel_script=sentinel_script,
            bridge_script=bridge_script,
            executable=executable,
            node_executable=node_executable,
            timeout_seconds=timeout_seconds,
        )
        for arm in ARM_NAMES
    }
    pair_clock: dict[str, Any] = {}
    window_results = {arm: {} for arm in ARM_NAMES}
    worker_errors: dict[str, BaseException] = {}
    shutdown: dict[str, dict[str, Any]] = {}
    started_at = utc_now()

    def open_barrier() -> None:
        pair_clock["monotonic"] = time.monotonic()
        pair_clock["utc"] = utc_now()

    barrier = threading.Barrier(3, action=open_barrier)
    workers: dict[str, threading.Thread] = {}
    failure: BaseException | None = None
    try:
        for session in sessions.values():
            session.start()

        def worker(arm: str) -> None:
            try:
                _run_window_worker(
                    session=sessions[arm],
                    barrier=barrier,
                    pair_clock=pair_clock,
                    observation_seconds=observation_seconds,
                    sample_interval_seconds=sample_interval_seconds,
                    result=window_results[arm],
                )
            except BaseException as error:
                worker_errors[arm] = error

        for arm in ARM_NAMES:
            workers[arm] = threading.Thread(
                target=worker, args=(arm,), daemon=True
            )
            workers[arm].start()
        barrier.wait(timeout=10)
        for thread in workers.values():
            thread.join(timeout=observation_seconds + timeout_seconds)
        if any(thread.is_alive() for thread in workers.values()):
            raise RuntimeError("paired window worker did not finish")
        if worker_errors:
            detail = "; ".join(
                f"{arm}: {error}"
                for arm, error in sorted(worker_errors.items())
            )
            raise RuntimeError(f"paired window failed: {detail}")
    except BaseException as error:
        failure = error
    finally:
        for arm, session in sessions.items():
            if session.app_server is not None:
                shutdown[arm] = session.shutdown_and_cleanup()
    if failure is not None:
        raise failure

    arm_reports: dict[str, dict[str, Any]] = {}
    for arm, session in sessions.items():
        arm_shutdown = shutdown[arm]
        cleanup = arm_shutdown.get("cleanup")
        if (
            not isinstance(cleanup, dict)
            or cleanup.get("cleanupVerified") is not True
        ):
            raise RuntimeError(f"{arm} Sentinel cleanup was not verified")
        messages = [
            message
            for connection in session.connections.values()
            for message in connection.messages
        ]
        model_turn_count = sum(
            1
            for connection in session.connections.values()
            for entry in connection.ledger
            if entry.get("method") == "turn/start"
        )
        turn_started_count = sum(
            1
            for message in messages
            if message.get("method") in {"turn/started", "turn/start"}
        )
        raw = window_results[arm]
        classification = classify_arm(
            arm=arm,
            app_server_process=session.app_server_process,
            creator_bridge_process=(
                session.connections["creator-a"].process_identity
            ),
            observer_bridge_process=(
                session.connections["observer-b"].process_identity
            ),
            thread_id_a=session.thread_id,
            thread_id_b=session.observer_thread_id,
            creator_baseline_call=session.creator_baseline_call,
            observer_baseline_call=session.observer_baseline_call,
            sentinel_process=session.sentinel_process,
            start_events=session.start_events,
            process_samples=raw["processSamples"],
            stop_events=raw["stopEventsInWindow"],
            post_window_call=raw["postWindowCall"],
            in_window_host_methods=raw["inWindowHostMethods"],
            transport_actions=raw["transportActions"],
            creator_close=raw["creatorClose"],
            action_skew_milliseconds=raw["actionSkewMilliseconds"],
            observation_seconds=observation_seconds,
            sample_interval_seconds=sample_interval_seconds,
            model_turn_count=model_turn_count,
            turn_started_notification_count=turn_started_count,
            configuration_unchanged=raw[
                "configurationUnchangedAtWindowEnd"
            ],
            auth_state_produced=bool(
                arm_shutdown.get("authStateProduced")
            ),
            evidence_sealed_before_post_window_call=raw[
                "evidenceSealedBeforePostWindowCall"
            ],
        )
        arm_reports[arm] = {
            "arm": arm,
            "codexHome": session.codex_home.as_posix(),
            "workspace": session.workspace.as_posix(),
            "configuration": {
                "sha256": session.config_hash,
                "bytes": len(session.config_bytes),
                "unchangedDuringWindow": raw[
                    "configurationUnchangedAtWindowEnd"
                ],
                "currentUserConfigCopied": False,
            },
            "environment": {
                "allowlistApplied": True,
                "keyNames": session.environment_key_names,
                "valuesRecorded": False,
                "accountOrProxyKeysInherited": False,
            },
            "thread": {
                "id": session.thread_id,
                "observerId": session.observer_thread_id,
                "ephemeral": False,
                "rolloutMaterialization": (
                    session.rollout_materialization
                ),
                "modelTurnRequests": model_turn_count,
                "turnStartedNotifications": turn_started_count,
            },
            "appServerProcess": session.app_server_process,
            "connections": {
                owner: {
                    "bridgeProcess": connection.process_identity,
                    "readyLine": connection.ready_line,
                    "rpcLedger": connection.ledger,
                    "messages": connection.messages,
                    "stderrLines": connection.stderr_lines,
                }
                for owner, connection in session.connections.items()
            },
            "sentinel": {
                "creatorBaselineCall": session.creator_baseline_call,
                "observerBaselineCall": session.observer_baseline_call,
                "process": session.sentinel_process,
                "startEvents": session.start_events,
            },
            **raw,
            "classification": classification,
            "shutdownAndCleanup": arm_shutdown,
            "appServerStdout": session.app_stdout,
            "appServerStderr": session.app_stderr,
        }

    pair_classification = classify_pair(
        arm_reports[ARM_CONTROL]["classification"],
        arm_reports[ARM_CREATOR_CLOSE]["classification"],
    )
    cross_arm_action_skew = abs(
        float(arm_reports[ARM_CONTROL]["actionMonotonic"])
        - float(arm_reports[ARM_CREATOR_CLOSE]["actionMonotonic"])
    ) * 1000
    pair_classification["crossArmActionSkewMilliseconds"] = (
        cross_arm_action_skew
    )
    if cross_arm_action_skew > MAX_ACTION_SKEW_MILLISECONDS:
        pair_classification.update(
            {
                "classification": "invalid",
                "valid": False,
                "conclusive": False,
                "invalidReason": "cross-arm-action-skew-too-large",
            }
        )
    probe_script = Path(__file__).resolve()
    dependency_names = [
        "codex_app_server_websocket_bridge.mjs",
        "mcp_lifecycle_sentinel.py",
        "probe_codex_app_server_mcp_idle_unload.py",
        "probe_codex_app_server_mcp_multi_connection_subscription.py",
        "probe_codex_app_server_mcp_reload_new_threads.py",
        "probe_codex_app_server_mcp_reload_release_attribution.py",
        "probe_codex_app_server_mcp_status.py",
        "probe_codex_app_server_mcp_thread_unsubscribe_release_attribution.py",
        "probe_codex_app_server_mcp_tool_call.py",
    ]
    report = {
        "schemaVersion": 1,
        "probeId": PROBE_ID,
        "startedAt": started_at,
        "finishedAt": utc_now(),
        "hostBinding": {
            "platform": sys.platform,
            "codexVersion": codex_version,
            "nativeCodexExecutable": executable,
            "probeScript": probe_script.as_posix(),
            "probeScriptSha256": sha256_bytes(probe_script.read_bytes()),
            "dependencyBindings": [
                {
                    "path": probe_script.with_name(name).as_posix(),
                    "sha256": sha256_bytes(
                        probe_script.with_name(name).read_bytes()
                    ),
                }
                for name in dependency_names
            ],
        },
        "pairDesign": {
            "independentAppServers": True,
            "independentCodexHomes": True,
            "twoConnectionsPerArm": True,
            "singleLoadedThreadPerArm": True,
            "observationSeconds": observation_seconds,
            "sampleIntervalSeconds": sample_interval_seconds,
            "expectedSamplesPerArm": _sample_count(
                observation_seconds, sample_interval_seconds
            ),
            "maximumActionSkewMilliseconds": (
                MAX_ACTION_SKEW_MILLISECONDS
            ),
            "maximumSampleSkewMilliseconds": (
                MAX_SAMPLE_SKEW_MILLISECONDS
            ),
            "windowStartAt": pair_clock.get("utc"),
            "windowStartMonotonic": pair_clock.get("monotonic"),
        },
        "attributionBoundary": {
            "controlTransportActions": [],
            "treatmentTransportActions": [
                "creator-connection-close"
            ],
            "allowedInWindowHostMethods": [],
            "observerConnectionRemainsOpen": True,
            "appServerRemainsOpen": True,
            "creatorConnectionCloseIsTaskEnd": False,
            "reloadDuringWindow": False,
            "configWriteDuringWindow": False,
            "newThreadDuringWindow": False,
            "toolCallDuringWindow": False,
            "unsubscribeDuringWindow": False,
            "turnStartDuringWindow": False,
            "teardownDuringWindow": False,
            "cleanupDuringWindow": False,
            "pidSignalDuringWindow": False,
        },
        "arms": arm_reports,
        "pairClassification": pair_classification,
        "claimBoundary": {
            "provesCreatorConnectionCloseReleaseAssociation": (
                pair_classification.get(
                    "creatorConnectionCloseReleaseAssociated"
                )
                is True
            ),
            "provesCreatorConnectionIsLeaseOwner": False,
            "provesPublicLeaseOrReferenceCountApi": False,
            "provesTaskEndImmediateRelease": False,
            "provesStableResourceBenefit": False,
            "provesGenericCrashRecovery": False,
            "provesArbitraryMcpBehavior": False,
            "provesCrossHostOrCrossVersionParity": False,
            "provesResidualNeedForSelfAuthoredController": False,
            "provesNoNetworkTraffic": False,
            "modelTurnStarted": False,
            "modelRequestSent": False,
            "accountStateCopied": False,
        },
    }
    report["reportSha256"] = canonical_json_sha256(report)
    return report


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _write_jsonl(path: Path, values: list[dict[str, Any]]) -> None:
    path.write_text(
        "".join(
            json.dumps(value, ensure_ascii=False, separators=(",", ":"))
            + "\n"
            for value in values
        ),
        encoding="utf-8",
    )


def write_artifacts(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(output_dir / "pair-report.json", report)
    for arm in ARM_NAMES:
        arm_dir = output_dir / arm
        arm_dir.mkdir(parents=True, exist_ok=True)
        arm_report = report["arms"][arm]
        _write_json(arm_dir / "report.json", arm_report)
        _write_jsonl(
            arm_dir / "process-samples.jsonl",
            arm_report["processSamples"],
        )
        _write_jsonl(
            arm_dir / "sentinel-events.jsonl",
            arm_report["eventsAtWindowEnd"],
        )
        _write_json(
            arm_dir / "rpc-ledger.json",
            {
                "atEvidenceSeal": arm_report["rpcLedgerAtSeal"],
                "final": {
                    owner: data["rpcLedger"]
                    for owner, data in arm_report["connections"].items()
                },
            },
        )
        _write_json(
            arm_dir / "transport-actions.json",
            arm_report["transportActions"],
        )
        bridge_events = [
            {"bridge": owner, "line": line}
            for owner, data in arm_report["connections"].items()
            for line in data["stderrLines"]
            if line.startswith("BRIDGE_")
        ]
        _write_jsonl(arm_dir / "bridge-events.jsonl", bridge_events)
        stderr_lines = [
            *(f"app-server {line}" for line in arm_report["appServerStderr"]),
            *(
                f"{owner} {line}"
                for owner, data in arm_report["connections"].items()
                for line in data["stderrLines"]
            ),
        ]
        (arm_dir / "stderr.log").write_text(
            "".join(f"{line}\n" for line in stderr_lines),
            encoding="utf-8",
        )
        _write_json(
            arm_dir / "config-manifest.json",
            arm_report["configuration"],
        )


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
    parser.add_argument("--observation-seconds", type=float, default=5.0)
    parser.add_argument("--sample-interval-seconds", type=float, default=0.5)
    parser.add_argument("--timeout-seconds", type=float, default=30.0)
    parser.add_argument("--output-dir", type=Path)
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
        observation_seconds=args.observation_seconds,
        sample_interval_seconds=args.sample_interval_seconds,
        timeout_seconds=args.timeout_seconds,
    )
    if args.output_dir is not None:
        write_artifacts(args.output_dir, report)
    else:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["pairClassification"]["valid"] is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
