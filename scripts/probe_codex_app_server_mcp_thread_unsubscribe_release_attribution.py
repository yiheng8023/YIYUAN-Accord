#!/usr/bin/env python3
"""Pair-isolate short-window MCP effects of ``thread/unsubscribe``.

The probe starts two independent app-servers with fresh explicit CODEX_HOME
directories.  Both load one exact local Sentinel runtime.  A shared monotonic
barrier opens two concurrent five-second windows: the unsubscribe arm sends
exactly one ``thread/unsubscribe`` request, while the subscribed control arm
sends no host request.  During the windows the parent only samples exact
process identities and Sentinel events.  No model turn, reload, config change,
new thread, teardown, cleanup marker, or PID signal is permitted in-window.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
import math
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
        sha256_bytes,
        summarize_tool_call,
    )
    from .probe_codex_app_server_mcp_reload_release_attribution import (
        _cleanup_lingering_sentinels,
        read_executable_version,
        stop_events_in_window,
    )
    from .probe_codex_app_server_mcp_status import (
        build_command,
        drain_stdout_queue,
        inventory_files,
        wait_for_response,
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
        stop_events_in_window,
    )
    from probe_codex_app_server_mcp_status import (
        build_command,
        drain_stdout_queue,
        inventory_files,
        wait_for_response,
    )
    from probe_codex_app_server_mcp_tool_call import (
        SERVER_NAME,
        build_isolated_config,
        extract_thread_id,
        load_events,
        resolve_native_codex_executable,
    )


PROBE_ID = "codex-app-server-mcp-thread-unsubscribe-release-attribution-v1"
ARM_CONTROL = "subscribed-control"
ARM_UNSUBSCRIBE = "thread-unsubscribe"
ARM_NAMES = (ARM_CONTROL, ARM_UNSUBSCRIBE)
MAX_ACTION_SKEW_MILLISECONDS = 100.0
MAX_SAMPLE_SKEW_MILLISECONDS = 250.0
MINIMAL_ENVIRONMENT_KEYS = (
    "APPDATA",
    "COMSPEC",
    "HOMEDRIVE",
    "HOMEPATH",
    "LOCALAPPDATA",
    "NUMBER_OF_PROCESSORS",
    "OS",
    "PATH",
    "PATHEXT",
    "PROCESSOR_ARCHITECTURE",
    "PROGRAMDATA",
    "PROGRAMFILES",
    "PROGRAMFILES(X86)",
    "SYSTEMDRIVE",
    "SYSTEMROOT",
    "TEMP",
    "TMP",
    "USERDOMAIN",
    "USERNAME",
    "USERPROFILE",
    "WINDIR",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_minimal_child_environment(
    codex_home: Path,
) -> tuple[dict[str, str], list[str]]:
    """Build a named allowlist without recording inherited values."""

    environment = {
        key: os.environ[key]
        for key in MINIMAL_ENVIRONMENT_KEYS
        if key in os.environ
    }
    environment["CODEX_HOME"] = str(codex_home)
    environment["RUST_LOG"] = "warn"
    environment["LOG_FORMAT"] = "json"
    return environment, sorted(environment)


def build_thread_start_request(
    request_id: int,
    workspace: Path,
    arm: str,
) -> dict[str, Any]:
    return {
        "id": request_id,
        "method": "thread/start",
        "params": {
            "cwd": workspace.resolve().as_posix(),
            "ephemeral": True,
            "approvalPolicy": "never",
            "sandbox": "read-only",
            "name": f"{PROBE_ID}-{arm}",
        },
    }


def build_tool_request(
    request_id: int,
    thread_id: str,
    arm: str,
    phase: str,
) -> dict[str, Any]:
    return {
        "id": request_id,
        "method": "mcpServer/tool/call",
        "params": {
            "threadId": thread_id,
            "server": SERVER_NAME,
            "tool": "identity",
            "arguments": {
                "probe": PROBE_ID,
                "arm": arm,
                "phase": phase,
            },
        },
    }


def _normalized_image(value: Any) -> str:
    return os.path.normcase(str(Path(str(value)).resolve()))


def bind_sentinel_process(
    payload: dict[str, Any],
    *,
    app_server_pid: int,
) -> dict[str, Any]:
    pid = payload.get("pid")
    instance_id = payload.get("instanceId")
    if not isinstance(pid, int) or not isinstance(instance_id, str):
        raise RuntimeError("Sentinel payload omitted exact identity")
    identity = snapshot_process(pid)
    if (
        not process_identity_complete(identity)
        or identity.get("parentPid") != app_server_pid
        or _normalized_image(identity.get("imagePath"))
        != _normalized_image(Path(sys.executable))
    ):
        raise RuntimeError("Sentinel exact child identity could not be bound")
    return identity


def _sample_count(
    observation_seconds: float,
    sample_interval_seconds: float,
) -> int:
    return math.floor(observation_seconds / sample_interval_seconds) + 1


def collect_process_samples(
    *,
    sentinel_pid: int,
    app_server_pid: int,
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
            }
        )
    return samples


def classify_arm(
    *,
    arm: str,
    baseline_instance_id: str,
    baseline_pid: int,
    baseline_process: dict[str, Any],
    process_samples: list[dict[str, Any]],
    stop_events: list[dict[str, Any]],
    post_window_call: dict[str, Any],
    in_window_host_methods: list[str],
    unsubscribe_status: str | None,
    action_skew_milliseconds: float,
    observation_seconds: float,
    sample_interval_seconds: float,
    model_turn_count: int,
) -> dict[str, Any]:
    invalid_reasons: list[str] = []
    if arm not in ARM_NAMES:
        invalid_reasons.append("unknown-arm")
    if not process_identity_complete(baseline_process):
        invalid_reasons.append("baseline-process-identity-incomplete")
    expected_count = _sample_count(
        observation_seconds, sample_interval_seconds
    )
    if len(process_samples) != expected_count:
        invalid_reasons.append("sample-count-mismatch")
    expected_methods = (
        ["thread/unsubscribe"] if arm == ARM_UNSUBSCRIBE else []
    )
    if in_window_host_methods != expected_methods:
        invalid_reasons.append("forbidden-or-missing-in-window-host-method")
    if (
        arm == ARM_UNSUBSCRIBE
        and unsubscribe_status != "unsubscribed"
    ):
        invalid_reasons.append("unsubscribe-not-acknowledged")
    if arm == ARM_CONTROL and unsubscribe_status is not None:
        invalid_reasons.append("control-arm-has-unsubscribe-response")
    if action_skew_milliseconds > MAX_ACTION_SKEW_MILLISECONDS:
        invalid_reasons.append("action-barrier-skew-too-large")
    if model_turn_count != 0:
        invalid_reasons.append("model-turn-observed")

    sentinel_samples = [
        item.get("sentinel", {}) for item in process_samples
    ]
    app_server_samples = [
        item.get("appServer", {}) for item in process_samples
    ]
    sample_skews = [
        float(item.get("sampleSkewMilliseconds", float("inf")))
        for item in process_samples
    ]
    same_identity_by_sample = [
        same_process_identity(baseline_process, sample)
        for sample in sentinel_samples
    ]
    app_server_alive_by_sample = [
        item.get("exists") is True for item in app_server_samples
    ]
    if not all(app_server_alive_by_sample):
        invalid_reasons.append("app-server-not-alive-through-window")
    if any(
        skew < 0 or skew > MAX_SAMPLE_SKEW_MILLISECONDS
        for skew in sample_skews
    ):
        invalid_reasons.append("sample-timing-skew")

    final_sample = sentinel_samples[-1] if sentinel_samples else {}
    final_same_identity = (
        same_process_identity(baseline_process, final_sample)
        if sentinel_samples
        else False
    )
    post_window_same_instance = (
        post_window_call.get("succeeded") is True
        and post_window_call.get("instanceId") == baseline_instance_id
        and post_window_call.get("pid") == baseline_pid
    )
    released = bool(stop_events) and final_sample.get("exists") is False
    retained = (
        bool(same_identity_by_sample)
        and all(same_identity_by_sample)
        and not stop_events
        and final_same_identity
        and post_window_same_instance
    )

    if invalid_reasons:
        classification = "measurement-invalid"
        valid = False
    elif released:
        classification = (
            "unsubscribe-release-observed-bounded"
            if arm == ARM_UNSUBSCRIBE
            else "subscribed-control-stopped"
        )
        valid = True
    elif retained:
        classification = (
            "unsubscribe-runtime-retained-five-seconds"
            if arm == ARM_UNSUBSCRIBE
            else "subscribed-control-retained-five-seconds"
        )
        valid = True
    else:
        classification = "measurement-ambiguous"
        valid = False
        invalid_reasons.append("process-and-stop-evidence-do-not-converge")

    return {
        "classification": classification,
        "valid": valid,
        "invalidReasons": invalid_reasons,
        "releaseObserved": released and valid,
        "runtimeRetained": retained and valid,
        "sameIdentityBySample": same_identity_by_sample,
        "appServerAliveBySample": app_server_alive_by_sample,
        "finalSameProcessIdentity": final_same_identity,
        "postWindowCallSameInstance": post_window_same_instance,
        "expectedSampleCount": expected_count,
        "actualSampleCount": len(process_samples),
        "maximumSampleSkewMilliseconds": (
            max(sample_skews) if sample_skews else None
        ),
    }


def classify_pair(
    control: dict[str, Any],
    unsubscribe: dict[str, Any],
) -> dict[str, Any]:
    control_classification = control.get("classification")
    unsubscribe_classification = unsubscribe.get("classification")
    if (
        control.get("valid") is True
        and unsubscribe.get("valid") is True
        and control_classification
        == "subscribed-control-retained-five-seconds"
        and unsubscribe_classification
        == "unsubscribe-runtime-retained-five-seconds"
    ):
        classification = (
            "unsubscribe-immediate-release-falsified-bounded"
        )
        valid = True
        release_associated = False
        immediate_release_falsified = True
    elif (
        control.get("valid") is True
        and unsubscribe.get("valid") is True
        and control_classification
        == "subscribed-control-retained-five-seconds"
        and unsubscribe_classification
        == "unsubscribe-release-observed-bounded"
    ):
        classification = "unsubscribe-release-associated-bounded"
        valid = True
        release_associated = True
        immediate_release_falsified = False
    else:
        classification = "pair-inconclusive"
        valid = False
        release_associated = False
        immediate_release_falsified = False
    return {
        "classification": classification,
        "valid": valid,
        "unsubscribeReleaseAssociated": release_associated,
        "unsubscribeImmediateReleaseFalsified": (
            immediate_release_falsified
        ),
        "controlClassification": control_classification,
        "unsubscribeClassification": unsubscribe_classification,
    }


class AppServerArm:
    def __init__(
        self,
        *,
        arm: str,
        codex_home: Path,
        workspace: Path,
        sentinel_script: Path,
        executable: str,
        timeout_seconds: float,
    ) -> None:
        self.arm = arm
        self.codex_home = codex_home.resolve()
        self.workspace = workspace.resolve()
        self.sentinel_script = sentinel_script.resolve()
        self.executable = executable
        self.timeout_seconds = timeout_seconds
        self.event_log = self.codex_home / "sentinel-events.jsonl"
        self.cleanup_marker = self.codex_home / "harness-cleanup.marker"
        self.config_path = self.codex_home / "config.toml"
        self.process: subprocess.Popen[str] | None = None
        self.stdout_queue: queue.Queue[str | None] = queue.Queue()
        self.stderr_lines: list[str] = []
        self.messages: list[dict[str, Any]] = []
        self.request_ledger: list[dict[str, Any]] = []
        self.pending: dict[int, dict[str, Any]] = {}
        self.stdout_thread: threading.Thread | None = None
        self.stderr_thread: threading.Thread | None = None
        self.thread_id = ""
        self.baseline_call: dict[str, Any] = {}
        self.baseline_process: dict[str, Any] = {}
        self.app_server_process: dict[str, Any] = {}
        self.config_bytes = b""
        self.config_hash = ""
        self.files_before: list[dict[str, Any]] = []
        self.environment_key_names: list[str] = []
        self.app_server_kill_sent = False

    def _process(self) -> subprocess.Popen[str]:
        if self.process is None:
            raise RuntimeError("app-server arm has not started")
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
        self.stderr_lines.extend(
            line.rstrip("\r\n") for line in process.stderr
        )

    def start(self) -> None:
        default_home = (Path.home() / ".codex").resolve()
        if os.path.normcase(str(self.codex_home)) == os.path.normcase(
            str(default_home)
        ):
            raise RuntimeError("refusing to use the current default Codex home")
        if self.codex_home.exists() and any(self.codex_home.iterdir()):
            raise RuntimeError("isolated Codex home must be absent or empty")
        self.codex_home.mkdir(parents=True, exist_ok=True)
        self.workspace.mkdir(parents=True, exist_ok=True)
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
        command = build_command(self.executable)
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
        environment, self.environment_key_names = (
            build_minimal_child_environment(self.codex_home)
        )
        self.process = subprocess.Popen(
            command,
            cwd=self.workspace,
            env=environment,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        self.app_server_process = snapshot_process(self.process.pid)
        if not process_identity_complete(self.app_server_process):
            raise RuntimeError("app-server exact process identity is incomplete")
        self.stdout_thread = threading.Thread(
            target=self._read_stdout, daemon=True
        )
        self.stderr_thread = threading.Thread(
            target=self._read_stderr, daemon=True
        )
        self.stdout_thread.start()
        self.stderr_thread.start()

        initialize = self.request(
            0,
            "initialize",
            {
                "clientInfo": {
                    "name": PROBE_ID,
                    "title": "MCP Thread Unsubscribe Attribution Probe",
                    "version": "1.0.0",
                }
            },
            phase="initialize",
        )
        result = initialize.get("result")
        if not isinstance(result, dict):
            raise RuntimeError("initialize result is not an object")
        actual_home = Path(str(result.get("codexHome"))).resolve()
        if os.path.normcase(str(actual_home)) != os.path.normcase(
            str(self.codex_home)
        ):
            raise RuntimeError("app-server used an unexpected Codex home")
        self.notify("initialized", None, phase="initialized")

        thread = self.request(
            1,
            "thread/start",
            build_thread_start_request(
                1, self.workspace, self.arm
            )["params"],
            phase="thread-start",
        )
        self.thread_id = extract_thread_id(thread)
        baseline = self.request(
            2,
            "mcpServer/tool/call",
            build_tool_request(
                2,
                self.thread_id,
                self.arm,
                "baseline",
            )["params"],
            phase="baseline",
        )
        self.baseline_call = summarize_tool_call(baseline)
        self.baseline_process = bind_sentinel_process(
            self.baseline_call,
            app_server_pid=self.process.pid,
        )
        instance_id = self.baseline_call.get("instanceId")
        matching_starts = [
            event
            for event in load_events(self.event_log)
            if event.get("event") == "instance-start"
            and event.get("instanceId") == instance_id
            and event.get("pid") == self.baseline_call.get("pid")
        ]
        if len(matching_starts) != 1:
            raise RuntimeError("Sentinel start event did not bind exactly once")

    def notify(
        self,
        method: str,
        params: dict[str, Any] | None,
        *,
        phase: str,
    ) -> None:
        process = self._process()
        if process.stdin is None or process.stdin.closed:
            raise RuntimeError("app-server stdin is closed")
        request: dict[str, Any] = {"method": method}
        if params is not None:
            request["params"] = params
        sent_monotonic = time.monotonic()
        sent_at = utc_now()
        process.stdin.write(json.dumps(request, separators=(",", ":")) + "\n")
        process.stdin.flush()
        self.request_ledger.append(
            {
                "id": None,
                "method": method,
                "phase": phase,
                "sentAt": sent_at,
                "sentMonotonic": sent_monotonic,
                "responseExpected": False,
            }
        )

    def send_request(
        self,
        request_id: int,
        method: str,
        params: dict[str, Any] | None,
        *,
        phase: str,
    ) -> dict[str, Any]:
        process = self._process()
        if process.stdin is None or process.stdin.closed:
            raise RuntimeError("app-server stdin is closed")
        request: dict[str, Any] = {
            "id": request_id,
            "method": method,
            "params": params,
        }
        entry = {
            "id": request_id,
            "method": method,
            "phase": phase,
            "sentAt": utc_now(),
            "sentMonotonic": time.monotonic(),
            "responseExpected": True,
        }
        process.stdin.write(json.dumps(request, separators=(",", ":")) + "\n")
        process.stdin.flush()
        self.request_ledger.append(entry)
        self.pending[request_id] = entry
        return entry

    def wait_response(
        self,
        request_id: int,
        *,
        timeout_seconds: float | None = None,
    ) -> dict[str, Any]:
        process = self._process()
        entry = self.pending.get(request_id)
        if entry is None:
            raise RuntimeError(f"request {request_id} is not pending")
        response = wait_for_response(
            self.stdout_queue,
            request_id,
            time.monotonic()
            + (
                self.timeout_seconds
                if timeout_seconds is None
                else timeout_seconds
            ),
            self.messages,
        )
        entry["responseAt"] = utc_now()
        entry["responseMonotonic"] = time.monotonic()
        entry["succeeded"] = "error" not in response
        entry["result"] = response.get("result")
        entry["error"] = response.get("error")
        self.pending.pop(request_id, None)
        if process.poll() is not None:
            entry["appServerExitedBeforeResponseRead"] = True
        return response

    def request(
        self,
        request_id: int,
        method: str,
        params: dict[str, Any] | None,
        *,
        phase: str,
    ) -> dict[str, Any]:
        self.send_request(
            request_id,
            method,
            params,
            phase=phase,
        )
        response = self.wait_response(request_id)
        if "error" in response:
            raise RuntimeError(f"{method} failed: {response['error']}")
        return response

    def shutdown_and_cleanup(self) -> dict[str, Any]:
        process = self._process()
        if process.stdin is not None and not process.stdin.closed:
            process.stdin.close()
        if process.poll() is None:
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                self.app_server_kill_sent = True
                process.kill()
                process.wait(timeout=5)
        if self.stdout_thread is not None:
            self.stdout_thread.join(timeout=1)
        if self.stderr_thread is not None:
            self.stderr_thread.join(timeout=1)
        drain_stdout_queue(self.stdout_queue, self.messages)
        events_before_cleanup = load_events(self.event_log)
        cleanup = _cleanup_lingering_sentinels(
            self.event_log, self.cleanup_marker
        )
        files_after = inventory_files(self.codex_home)
        external_network_attempt_lines = [
            line
            for line in self.stderr_lines
            if "https://" in line or "http://" in line or "wss://" in line
        ]
        return {
            "eventsBeforeHarnessCleanup": events_before_cleanup,
            "appServerReturnCode": process.returncode,
            "appServerKillSent": self.app_server_kill_sent,
            "cleanup": cleanup,
            "filesAfter": files_after,
            "authStateProduced": any(
                str(item.get("path", "")).lower().endswith("auth.json")
                for item in files_after
            ),
            "applicationLogExternalNetworkAttemptObserved": bool(
                external_network_attempt_lines
            ),
            "applicationLogExternalNetworkAttemptLines": (
                external_network_attempt_lines
            ),
        }


def _run_window_worker(
    *,
    session: AppServerArm,
    barrier: threading.Barrier,
    pair_clock: dict[str, Any],
    observation_seconds: float,
    sample_interval_seconds: float,
    result: dict[str, Any],
) -> None:
    barrier.wait(timeout=10)
    window_start_monotonic = float(pair_clock["monotonic"])
    window_start_utc = datetime.fromisoformat(str(pair_clock["utc"]))
    unsubscribe_response: dict[str, Any] | None = None
    unsubscribe_waiter: threading.Thread | None = None
    unsubscribe_error: list[BaseException] = []

    if session.arm == ARM_UNSUBSCRIBE:
        entry = session.send_request(
            3,
            "thread/unsubscribe",
            {"threadId": session.thread_id},
            phase="attribution-window-unsubscribe",
        )
        action_monotonic = float(entry["sentMonotonic"])

        def wait_unsubscribe() -> None:
            nonlocal unsubscribe_response
            try:
                unsubscribe_response = session.wait_response(
                    3,
                    timeout_seconds=observation_seconds + 10,
                )
            except BaseException as error:
                unsubscribe_error.append(error)

        unsubscribe_waiter = threading.Thread(
            target=wait_unsubscribe, daemon=True
        )
        unsubscribe_waiter.start()
    else:
        action_monotonic = time.monotonic()

    samples = collect_process_samples(
        sentinel_pid=int(session.baseline_call["pid"]),
        app_server_pid=session._process().pid,
        window_start_monotonic=window_start_monotonic,
        observation_seconds=observation_seconds,
        sample_interval_seconds=sample_interval_seconds,
    )
    window_end_utc = window_start_utc + timedelta(
        seconds=observation_seconds
    )
    events_at_window_end = load_events(session.event_log)
    if unsubscribe_waiter is not None:
        unsubscribe_waiter.join(timeout=1)
        if unsubscribe_waiter.is_alive():
            unsubscribe_error.append(
                RuntimeError("unsubscribe response exceeded bounded wait")
            )
    if unsubscribe_error:
        raise unsubscribe_error[0]

    post_window_response = session.request(
        4,
        "mcpServer/tool/call",
        build_tool_request(
            4,
            session.thread_id,
            session.arm,
            "post-window",
        )["params"],
        phase="post-window-control-call",
    )
    post_window_call = summarize_tool_call(post_window_response)
    if session.arm == ARM_CONTROL:
        session.request(
            5,
            "thread/unsubscribe",
            {"threadId": session.thread_id},
            phase="post-window-control-cleanup-unsubscribe",
        )

    instance_id = str(session.baseline_call["instanceId"])
    stop_events = stop_events_in_window(
        events_at_window_end,
        instance_id,
        window_start_utc,
        window_end_utc,
    )
    in_window_host_methods = [
        str(item["method"])
        for item in session.request_ledger
        if isinstance(item.get("sentMonotonic"), (int, float))
        and window_start_monotonic
        <= float(item["sentMonotonic"])
        <= window_start_monotonic + observation_seconds
    ]
    unsubscribe_status: str | None = None
    if isinstance(unsubscribe_response, dict):
        response_result = unsubscribe_response.get("result")
        if isinstance(response_result, dict):
            value = response_result.get("status")
            if isinstance(value, str):
                unsubscribe_status = value
    model_turn_count = sum(
        1
        for item in session.request_ledger
        if item.get("method") == "turn/start"
    )
    action_skew_milliseconds = (
        action_monotonic - window_start_monotonic
    ) * 1000
    classification = classify_arm(
        arm=session.arm,
        baseline_instance_id=instance_id,
        baseline_pid=int(session.baseline_call["pid"]),
        baseline_process=session.baseline_process,
        process_samples=samples,
        stop_events=stop_events,
        post_window_call=post_window_call,
        in_window_host_methods=in_window_host_methods,
        unsubscribe_status=unsubscribe_status,
        action_skew_milliseconds=action_skew_milliseconds,
        observation_seconds=observation_seconds,
        sample_interval_seconds=sample_interval_seconds,
        model_turn_count=model_turn_count,
    )
    result.update(
        {
            "windowStartAt": window_start_utc.isoformat(),
            "windowEndAt": window_end_utc.isoformat(),
            "windowStartMonotonic": window_start_monotonic,
            "actionMonotonic": action_monotonic,
            "actionSkewMilliseconds": action_skew_milliseconds,
            "inWindowHostMethods": in_window_host_methods,
            "unsubscribeResponse": unsubscribe_response,
            "unsubscribeStatus": unsubscribe_status,
            "processSamples": samples,
            "eventsAtWindowEnd": events_at_window_end,
            "stopEventsInWindow": stop_events,
            "postWindowCall": post_window_call,
            "classification": classification,
        }
    )


def run_probe(
    root: Path,
    workspace: Path,
    sentinel_script: Path,
    codex_executable: str | None,
    observation_seconds: float,
    sample_interval_seconds: float,
    timeout_seconds: float,
) -> dict[str, Any]:
    if os.name != "nt":
        raise RuntimeError("exact process attribution currently requires Windows")
    root = root.resolve()
    workspace = workspace.resolve()
    sentinel_script = sentinel_script.resolve()
    if root.exists() and any(root.iterdir()):
        raise RuntimeError("paired probe root must be absent or empty")
    if not sentinel_script.is_file():
        raise RuntimeError(f"Sentinel script is missing: {sentinel_script}")
    if observation_seconds < 1:
        raise RuntimeError("observation window must be at least one second")
    if not 0 < sample_interval_seconds <= observation_seconds:
        raise RuntimeError("sample interval must be positive and within window")
    root.mkdir(parents=True, exist_ok=True)
    workspace.mkdir(parents=True, exist_ok=True)

    executable = resolve_native_codex_executable(codex_executable)
    codex_version = read_executable_version(executable)
    probe_script = Path(__file__).resolve()
    dependency_names = [
        "probe_codex_app_server_mcp_idle_unload.py",
        "probe_codex_app_server_mcp_reload_new_threads.py",
        "probe_codex_app_server_mcp_reload_release_attribution.py",
        "probe_codex_app_server_mcp_status.py",
        "probe_codex_app_server_mcp_tool_call.py",
    ]
    dependency_bindings = [
        {
            "path": probe_script.with_name(name).as_posix(),
            "sha256": sha256_bytes(
                probe_script.with_name(name).read_bytes()
            ),
        }
        for name in dependency_names
    ]
    started_at = utc_now()
    sessions = {
        arm: AppServerArm(
            arm=arm,
            codex_home=root / arm / "codex-home",
            workspace=workspace,
            sentinel_script=sentinel_script,
            executable=executable,
            timeout_seconds=timeout_seconds,
        )
        for arm in ARM_NAMES
    }
    shutdown: dict[str, dict[str, Any]] = {}
    window_results = {arm: {} for arm in ARM_NAMES}
    worker_errors: dict[str, BaseException] = {}
    pair_clock: dict[str, Any] = {}

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
            details = "; ".join(
                f"{arm}: {error}"
                for arm, error in sorted(worker_errors.items())
            )
            raise RuntimeError(f"paired window failed: {details}")
    except BaseException as error:
        failure = error
    finally:
        for arm, session in sessions.items():
            if session.process is not None:
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
        if arm_shutdown.get("authStateProduced") is True:
            raise RuntimeError(f"{arm} unexpectedly produced auth state")
        arm_reports[arm] = {
            "codexHome": session.codex_home.as_posix(),
            "workspace": session.workspace.as_posix(),
            "command": build_command(executable)
            + [
                "--disable",
                "plugins",
                "--disable",
                "remote_plugin",
                "--disable",
                "apps",
                "--disable",
                "plugin_sharing",
            ],
            "environment": {
                "allowlistApplied": True,
                "inheritedKeyNames": session.environment_key_names,
                "valuesRecorded": False,
                "accountOrProxyKeysInherited": False,
            },
            "thread": {
                "id": session.thread_id,
                "ephemeralRequested": True,
                "modelTurnStarted": False,
            },
            "configuration": {
                "sha256": session.config_hash,
                "bytes": len(session.config_bytes),
                "enabled": True,
                "unchangedDuringProbe": (
                    session.config_path.read_bytes()
                    == session.config_bytes
                ),
                "currentUserConfigCopied": False,
            },
            "appServerProcess": session.app_server_process,
            "baselineCall": session.baseline_call,
            "baselineProcess": session.baseline_process,
            "requestLedger": session.request_ledger,
            "requestMethodsDerivedFromLedger": [
                str(item["method"]) for item in session.request_ledger
            ],
            "filesBefore": session.files_before,
            **window_results[arm],
            "shutdownAndCleanup": arm_shutdown,
            "stderrLines": session.stderr_lines,
            "stdoutMessageCount": len(session.messages),
        }

    pair_classification = classify_pair(
        arm_reports[ARM_CONTROL]["classification"],
        arm_reports[ARM_UNSUBSCRIBE]["classification"],
    )
    action_skew = abs(
        float(arm_reports[ARM_CONTROL]["actionMonotonic"])
        - float(arm_reports[ARM_UNSUBSCRIBE]["actionMonotonic"])
    ) * 1000
    pair_classification["crossArmActionSkewMilliseconds"] = action_skew
    if action_skew > MAX_ACTION_SKEW_MILLISECONDS:
        pair_classification["valid"] = False
        pair_classification["classification"] = "pair-inconclusive"
        pair_classification["invalidReason"] = (
            "cross-arm-action-skew-too-large"
        )

    finished_at = utc_now()
    network_attempt_count = sum(
        int(
            arm_reports[arm]["shutdownAndCleanup"].get(
                "applicationLogExternalNetworkAttemptObserved"
            )
            is True
        )
        for arm in ARM_NAMES
    )
    return {
        "schema": 1,
        "id": PROBE_ID,
        "startedAt": started_at,
        "finishedAt": finished_at,
        "hostBinding": {
            "codexVersion": codex_version,
            "nativeCodexExecutable": executable,
            "probeScript": probe_script.as_posix(),
            "probeScriptSha256": sha256_bytes(probe_script.read_bytes()),
            "sentinelScript": sentinel_script.as_posix(),
            "sentinelScriptSha256": sha256_bytes(
                sentinel_script.read_bytes()
            ),
            "dependencyBindings": dependency_bindings,
            "pythonVersion": sys.version,
        },
        "pairDesign": {
            "independentAppServers": True,
            "independentCodexHomes": True,
            "independentThreads": True,
            "independentSentinelInstances": True,
            "concurrentMonotonicBarrier": True,
            "observationSeconds": observation_seconds,
            "sampleIntervalSeconds": sample_interval_seconds,
            "maximumActionSkewMilliseconds": (
                MAX_ACTION_SKEW_MILLISECONDS
            ),
            "maximumSampleSkewMilliseconds": (
                MAX_SAMPLE_SKEW_MILLISECONDS
            ),
            "windowStartAt": pair_clock.get("utc"),
            "windowStartMonotonic": pair_clock.get("monotonic"),
            "unsubscribeIsTaskEnd": False,
        },
        "attributionBoundary": {
            "unsubscribeArmAllowedHostMethods": ["thread/unsubscribe"],
            "controlArmAllowedHostMethods": [],
            "bothArmsAllowedParentActions": [
                "exact-process-sampling",
                "sentinel-event-log-read",
                "app-server-liveness-sampling",
            ],
            "reloadDuringWindow": False,
            "configWriteDuringWindow": False,
            "newThreadDuringWindow": False,
            "toolCallDuringWindow": False,
            "turnStartDuringWindow": False,
            "teardownDuringWindow": False,
            "cleanupDuringWindow": False,
            "pidSignalDuringWindow": False,
        },
        "arms": arm_reports,
        "pairClassification": pair_classification,
        "isolation": {
            "currentAuthCopied": False,
            "currentPluginsCopied": False,
            "currentUserConfigCopied": False,
            "minimalEnvironmentAllowlistApplied": True,
            "accountOrProxyEnvironmentValuesRecorded": False,
            "applicationLogExternalNetworkAttemptCount": (
                network_attempt_count
            ),
            "packetLevelNetworkMonitorUsed": False,
        },
        "claimBoundary": {
            "provesUnsubscribeRequestAccepted": (
                arm_reports[ARM_UNSUBSCRIBE].get("unsubscribeStatus")
                == "unsubscribed"
            ),
            "provesUnsubscribeIsTaskEnd": False,
            "provesTaskEndImmediateRelease": False,
            "provesLeaseOrReferenceCountBehavior": False,
            "provesStableResourceBenefit": False,
            "provesGenericCrashRecovery": False,
            "provesArbitraryMcpBehavior": False,
            "provesCrossHostOrCrossVersionParity": False,
            "provesResidualNeedForSelfAuthoredController": False,
            "provesNoNetworkTraffic": False,
            "modelTurnStarted": False,
            "modelRequestSent": False,
        },
    }


def main() -> int:
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
    parser.add_argument("--codex-executable")
    parser.add_argument("--observation-seconds", type=float, default=5)
    parser.add_argument("--sample-interval-seconds", type=float, default=0.5)
    parser.add_argument("--timeout-seconds", type=float, default=90)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    result = run_probe(
        arguments.root,
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
