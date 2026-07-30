#!/usr/bin/env python3
"""Probe task-scoped Codex Skill exposure with a weak-model marker turn.

The probe uses two short-lived Codex app-server processes:

1. list the current user/system Skill inventory with plugin features disabled;
2. pass a one-off ``skills.config`` override that disables every observed user
   Skill, verify the effective inventory, start an ephemeral Spark/low thread,
   and run one marker-only turn.

The current ``config.toml`` is hashed before and after the probe. The script
does not write global config, install a capability, restart a host, invoke an
MCP tool, or retain raw stderr. The ephemeral thread is reconstructed from
``item/completed`` notifications because ``turn/completed`` may legitimately
carry an empty item view and ephemeral threads reject
``thread/read(includeTurns=true)``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import queue
import shutil
import subprocess
import threading
import time
from typing import Any


PROBE_ID = "codex-app-server-task-scoped-skill-exposure-v1"
MODEL = "gpt-5.3-codex-spark"
EFFORT = "low"
MARKER = "AAH_SPARK_LOW_DISABLED_EXPOSURE_OK"
PLUGIN_FEATURES = ("plugins", "remote_plugin", "apps", "plugin_sharing")
STATIC_MCP_NAMES = (
    "codegraph",
    "context7",
    "neo4j-graph",
    "node_repl",
    "playwright",
    "github",
)
FORBIDDEN_ITEM_TYPES = {
    "commandExecution",
    "fileChange",
    "mcpToolCall",
    "dynamicToolCall",
    "collabAgentToolCall",
    "webSearch",
}
SELF_AUTHORED_NAMES = {
    "intent-contract",
    "capability-router",
    "closure-contract",
}


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def canonical_sha256(value: Any) -> str:
    content = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256_bytes(content)


def file_observation(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"exists": False, "bytes": None, "sha256": None}
    content = path.read_bytes()
    return {
        "exists": True,
        "bytes": len(content),
        "sha256": sha256_bytes(content),
    }


def toml_string(value: str) -> str:
    """Encode a path/string as a TOML basic string."""

    return json.dumps(value.replace("\\", "/"), ensure_ascii=False)


def build_skill_config_override(
    user_skills: list[dict[str, Any]],
    *,
    enabled_paths: set[str] | None = None,
) -> str:
    enabled = {
        path.replace("\\", "/").lower()
        for path in (enabled_paths or set())
    }
    rows: list[str] = []
    seen_paths: set[str] = set()
    for skill in sorted(
        user_skills,
        key=lambda row: (
            str(row.get("name", "")).lower(),
            str(row.get("path", "")).lower(),
        ),
    ):
        path = skill.get("path")
        if not isinstance(path, str) or not path.strip():
            raise RuntimeError("user Skill inventory contains an unbound path")
        normalized = path.replace("\\", "/")
        if normalized.lower() in seen_paths:
            continue
        seen_paths.add(normalized.lower())
        state = "true" if normalized.lower() in enabled else "false"
        rows.append(f"{{path={toml_string(normalized)},enabled={state}}}")
    if not rows:
        raise RuntimeError("no user Skills were available for the exposure cohort")
    if not enabled.issubset(seen_paths):
        raise RuntimeError("an enabled Skill path was absent from the inventory")
    return f"skills.config=[{','.join(rows)}]"


def build_disable_override(user_skills: list[dict[str, Any]]) -> str:
    return build_skill_config_override(user_skills, enabled_paths=set())


def resolve_codex_executable(explicit: str | None) -> str:
    candidate = explicit
    if candidate is None:
        candidate = (
            shutil.which("codex.cmd")
            if os.name == "nt"
            else shutil.which("codex")
        )
    if not candidate:
        raise RuntimeError("unable to resolve Codex CLI")
    resolved = Path(candidate).resolve(strict=False)
    if not resolved.is_file():
        raise RuntimeError(f"Codex CLI does not exist: {resolved}")
    return str(resolved)


def build_command(
    executable: str,
    *,
    disable_override: str | None = None,
    plugin_features_to_disable: tuple[str, ...] = PLUGIN_FEATURES,
) -> list[str]:
    arguments = ["app-server", "--stdio"]
    for feature in plugin_features_to_disable:
        arguments.extend(("--disable", feature))
    arguments.extend(("-c", "analytics.enabled=false"))
    if disable_override is not None:
        arguments.extend(("-c", disable_override))
        arguments.extend(("-c", f"model_reasoning_effort={EFFORT}"))
        for name in STATIC_MCP_NAMES:
            arguments.extend(("-c", f"mcp_servers.{name}.enabled=false"))
    if os.name == "nt" and Path(executable).suffix.lower() in {".cmd", ".bat"}:
        launcher_root = Path(executable).resolve(strict=False).parent
        codex_js = (
            launcher_root
            / "node_modules"
            / "@openai"
            / "codex"
            / "bin"
            / "codex.js"
        )
        node = launcher_root / "node.exe"
        if not node.is_file():
            resolved_node = shutil.which("node.exe") or shutil.which("node")
            if not resolved_node:
                raise RuntimeError("unable to resolve Node.js for codex.cmd")
            node = Path(resolved_node)
        if not codex_js.is_file():
            raise RuntimeError("unable to resolve the Codex npm launcher")
        # Invoke the npm package entry point directly. Passing a large TOML
        # array through cmd.exe/codex.cmd can lose quoting before Codex parses
        # the one-off Skill override.
        return [str(node.resolve()), str(codex_js.resolve()), *arguments]
    return [executable, *arguments]


def _remaining(deadline: float) -> float:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise subprocess.TimeoutExpired("Codex Skill exposure probe", 0)
    return remaining


class AppServerSession:
    """Small newline-delimited JSON-RPC app-server client."""

    def __init__(
        self,
        command: list[str],
        cwd: Path,
        timeout_seconds: float,
        *,
        environment: dict[str, str] | None = None,
    ) -> None:
        self.command = command
        self.timeout_seconds = timeout_seconds
        self.deadline = time.monotonic() + timeout_seconds
        self.process = subprocess.Popen(
            command,
            cwd=cwd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=environment,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        self.stdout_queue: queue.Queue[str | None] = queue.Queue()
        self.stderr_lines: list[str] = []
        self.messages: list[dict[str, Any]] = []

        def read_stdout() -> None:
            assert self.process.stdout is not None
            for line in self.process.stdout:
                self.stdout_queue.put(line)
            self.stdout_queue.put(None)

        def read_stderr() -> None:
            assert self.process.stderr is not None
            for line in self.process.stderr:
                if line.strip():
                    self.stderr_lines.append(line.rstrip("\r\n"))

        self.stdout_thread = threading.Thread(target=read_stdout, daemon=True)
        self.stderr_thread = threading.Thread(target=read_stderr, daemon=True)
        self.stdout_thread.start()
        self.stderr_thread.start()

    def send(self, message: dict[str, Any]) -> None:
        if self.process.stdin is None or self.process.stdin.closed:
            raise RuntimeError("app-server stdin is not available")
        self.process.stdin.write(
            json.dumps(message, ensure_ascii=False, separators=(",", ":")) + "\n"
        )
        self.process.stdin.flush()

    def _next(self) -> dict[str, Any]:
        try:
            line = self.stdout_queue.get(timeout=_remaining(self.deadline))
        except queue.Empty as error:
            raise subprocess.TimeoutExpired(
                "Codex Skill exposure probe",
                self.timeout_seconds,
            ) from error
        if line is None:
            raise RuntimeError("app-server stdout closed before the probe completed")
        try:
            message = json.loads(line)
        except json.JSONDecodeError as error:
            raise RuntimeError("app-server emitted non-JSON stdout") from error
        if not isinstance(message, dict):
            raise RuntimeError("app-server emitted a non-object message")
        self.messages.append(message)
        return message

    def wait_for_response(self, request_id: int) -> dict[str, Any]:
        while True:
            message = self._next()
            if message.get("id") != request_id:
                continue
            if "error" in message:
                error = message["error"]
                code = error.get("code") if isinstance(error, dict) else None
                error_message = (
                    error.get("message") if isinstance(error, dict) else None
                )
                raise RuntimeError(
                    f"app-server request {request_id} failed with code {code}: "
                    f"{error_message}"
                )
            result = message.get("result")
            if not isinstance(result, dict):
                raise RuntimeError(
                    f"app-server response {request_id} omitted an object result"
                )
            return result

    def wait_for_notification(
        self,
        method: str,
        *,
        predicate: Any | None = None,
    ) -> dict[str, Any]:
        while True:
            message = self._next()
            if message.get("method") != method:
                continue
            params = message.get("params")
            if not isinstance(params, dict):
                continue
            if predicate is None or predicate(params):
                return params

    def close(self) -> None:
        if self.process.stdin is not None and not self.process.stdin.closed:
            self.process.stdin.close()
        try:
            self.process.wait(timeout=max(1.0, _remaining(self.deadline)))
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=5)
            raise RuntimeError("app-server did not exit after stdin closed")
        self.stdout_thread.join(timeout=1)
        self.stderr_thread.join(timeout=1)
        if self.process.returncode != 0:
            raise RuntimeError(
                f"app-server exited with code {self.process.returncode}"
            )

    def abort(self) -> None:
        if self.process.stdin is not None and not self.process.stdin.closed:
            self.process.stdin.close()
        if self.process.poll() is None:
            self.process.kill()
            self.process.wait(timeout=5)
        self.stdout_thread.join(timeout=1)
        self.stderr_thread.join(timeout=1)


def initialize(
    session: AppServerSession,
    *,
    experimental_api: bool = False,
) -> dict[str, Any]:
    params: dict[str, Any] = {
        "clientInfo": {
            "name": "agent_autonomy_harness_skill_exposure_probe",
            "title": "Agent Autonomy Harness Skill Exposure Probe",
            "version": "1.0.0",
        }
    }
    if experimental_api:
        params["capabilities"] = {"experimentalApi": True}
    session.send(
        {
            "id": 0,
            "method": "initialize",
            "params": params,
        }
    )
    result = session.wait_for_response(0)
    session.send({"method": "initialized"})
    return result


def request_skills(
    session: AppServerSession,
    cwd: Path,
    *,
    request_id: int,
) -> list[dict[str, Any]]:
    session.send(
        {
            "id": request_id,
            "method": "skills/list",
            "params": {"cwds": [str(cwd)], "forceReload": True},
        }
    )
    result = session.wait_for_response(request_id)
    data = result.get("data")
    if not isinstance(data, list) or len(data) != 1:
        raise RuntimeError("skills/list did not return exactly one cwd entry")
    entry = data[0]
    if not isinstance(entry, dict) or not isinstance(entry.get("skills"), list):
        raise RuntimeError("skills/list omitted the Skill array")
    if entry.get("errors") not in (None, []):
        raise RuntimeError("skills/list reported discovery errors")
    for skill in entry["skills"]:
        if (
            not isinstance(skill, dict)
            or not isinstance(skill.get("name"), str)
            or not isinstance(skill.get("path"), str)
            or skill.get("scope") not in {"user", "repo", "system", "admin"}
            or skill.get("enabled") not in {True, False}
        ):
            raise RuntimeError("skills/list returned an invalid Skill row")
    return entry["skills"]


def inventory_summary(skills: list[dict[str, Any]]) -> dict[str, Any]:
    scopes = sorted({str(skill["scope"]) for skill in skills})
    by_scope = {
        scope: sum(1 for skill in skills if skill["scope"] == scope)
        for scope in scopes
    }
    enabled_by_scope = {
        scope: sum(
            1
            for skill in skills
            if skill["scope"] == scope and skill["enabled"] is True
        )
        for scope in scopes
    }
    identities = sorted(
        (
            str(skill["name"]),
            str(skill["path"]).replace("\\", "/"),
            str(skill["scope"]),
        )
        for skill in skills
    )
    return {
        "skillCount": len(skills),
        "countsByScope": by_scope,
        "enabledCountsByScope": enabled_by_scope,
        "identityManifestSha256": canonical_sha256(identities),
    }


def self_authored_rows(skills: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "name": skill["name"],
            "path": str(skill["path"]).replace("\\", "/"),
            "scope": skill["scope"],
            "enabled": skill["enabled"],
        }
        for skill in skills
        if skill["name"] in SELF_AUTHORED_NAMES
    ]


def compare_inventories(
    control: list[dict[str, Any]],
    disabled: list[dict[str, Any]],
) -> dict[str, Any]:
    def keyed(rows: list[dict[str, Any]]) -> dict[tuple[str, str, str], bool]:
        return {
            (
                str(row["name"]),
                str(row["path"]).replace("\\", "/").lower(),
                str(row["scope"]),
            ): bool(row["enabled"])
            for row in rows
        }

    control_map = keyed(control)
    disabled_map = keyed(disabled)
    same_identity_set = set(control_map) == set(disabled_map)
    user_keys = [key for key in control_map if key[2] == "user"]
    non_user_keys = [key for key in control_map if key[2] != "user"]
    return {
        "sameIdentitySet": same_identity_set,
        "userSkillCount": len(user_keys),
        "allControlUserSkillsEnabled": all(control_map[key] for key in user_keys),
        "allDisabledUserSkillsDisabled": all(
            disabled_map.get(key) is False for key in user_keys
        ),
        "userStateTransitionCount": sum(
            control_map[key] is True and disabled_map.get(key) is False
            for key in user_keys
        ),
        "nonUserSkillCount": len(non_user_keys),
        "allNonUserStatesPreserved": all(
            disabled_map.get(key) == control_map[key] for key in non_user_keys
        ),
    }


def _thread_id(thread_start: dict[str, Any]) -> str:
    thread = thread_start.get("thread")
    if not isinstance(thread, dict) or not isinstance(thread.get("id"), str):
        raise RuntimeError("thread/start omitted thread id")
    return thread["id"]


def _turn_id(turn_start: dict[str, Any]) -> str:
    turn = turn_start.get("turn")
    if not isinstance(turn, dict) or not isinstance(turn.get("id"), str):
        raise RuntimeError("turn/start omitted turn id")
    return turn["id"]


def extract_turn(
    thread_read: dict[str, Any],
    turn_id: str,
) -> dict[str, Any]:
    thread = thread_read.get("thread")
    turns = thread.get("turns") if isinstance(thread, dict) else None
    if not isinstance(turns, list):
        raise RuntimeError("thread/read omitted turns")
    matches = [
        turn
        for turn in turns
        if isinstance(turn, dict) and turn.get("id") == turn_id
    ]
    if len(matches) != 1:
        raise RuntimeError("thread/read did not return exactly one target turn")
    return matches[0]


def summarize_turn(
    turn: dict[str, Any],
    item_notifications: list[dict[str, Any]],
) -> dict[str, Any]:
    items = turn.get("items")
    if not isinstance(items, list):
        raise RuntimeError("target turn omitted items")
    item_types = [
        item.get("type")
        for item in items
        if isinstance(item, dict) and isinstance(item.get("type"), str)
    ]
    agent_texts = [
        item.get("text")
        for item in items
        if isinstance(item, dict)
        and item.get("type") == "agentMessage"
        and isinstance(item.get("text"), str)
    ]
    notification_types = [
        params["item"].get("type")
        for params in item_notifications
        if isinstance(params.get("item"), dict)
        and isinstance(params["item"].get("type"), str)
    ]
    forbidden = sorted(
        (set(item_types) | set(notification_types)) & FORBIDDEN_ITEM_TYPES
    )
    return {
        "status": turn.get("status"),
        "itemsView": turn.get("itemsView"),
        "durationMilliseconds": turn.get("durationMs"),
        "itemTypes": item_types,
        "itemCompletedNotificationTypes": notification_types,
        "agentMessageCount": len(agent_texts),
        "exactMarkerMatch": agent_texts == [MARKER],
        "forbiddenItemTypesObserved": forbidden,
    }


def classify_stderr(lines: list[str]) -> dict[str, Any]:
    lowered = [line.lower() for line in lines]
    return {
        "lineCount": len(lines),
        "skillBudgetWarningCount": sum(
            "skill" in line and ("budget" in line or "truncat" in line)
            for line in lowered
        ),
        "mcpStartupFailureCount": sum(
            "mcp" in line and ("failed" in line or "incomplete" in line)
            for line in lowered
        ),
        "errorKeywordLineCount": sum(
            "error" in line or "failed" in line for line in lowered
        ),
        "rawStderrRecorded": False,
    }


def validate_probe_report(report: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    comparison = report.get("exposureComparison", {})
    if not comparison.get("sameIdentitySet"):
        failures.append("fail-skill-identity-set-drift")
    if not comparison.get("allControlUserSkillsEnabled"):
        failures.append("fail-control-user-skill-state")
    if not comparison.get("allDisabledUserSkillsDisabled"):
        failures.append("fail-disabled-user-skill-leak")
    if (
        comparison.get("userStateTransitionCount")
        != comparison.get("userSkillCount")
    ):
        failures.append("fail-user-skill-transition-count")
    if not comparison.get("allNonUserStatesPreserved"):
        failures.append("fail-non-user-skill-state-drift")

    thread = report.get("threadTelemetry", {})
    if thread.get("model") != MODEL:
        failures.append("fail-model-mismatch")
    if thread.get("reasoningEffort") != EFFORT:
        failures.append("fail-reasoning-effort-mismatch")
    if thread.get("modelProvider") != "openai":
        failures.append("fail-model-provider-mismatch")
    if thread.get("approvalPolicy") != "never":
        failures.append("fail-approval-policy-mismatch")
    sandbox = thread.get("sandbox")
    if not isinstance(sandbox, dict) or sandbox.get("type") != "readOnly":
        failures.append("fail-sandbox-mismatch")
    expected_sources = {
        str(Path.home() / ".codex" / "AGENTS.md").replace("\\", "/").lower(),
        str(
            Path(report.get("repository", {}).get("path", ""))
            / "AGENTS.md"
        ).replace("\\", "/").lower(),
    }
    observed_sources = {
        str(path).replace("\\", "/").lower()
        for path in thread.get("instructionSources", [])
    }
    if not expected_sources.issubset(observed_sources):
        failures.append("fail-instruction-source-binding")

    turn = report.get("markerTurn", {})
    if turn.get("status") != "completed":
        failures.append("fail-turn-status")
    if not turn.get("exactMarkerMatch"):
        failures.append("fail-marker-mismatch")
    if turn.get("forbiddenItemTypesObserved") != []:
        failures.append("hard-fail-forbidden-action-observed")

    mutation = report.get("mutationBoundary", {})
    if not mutation.get("configPrePostStable"):
        failures.append("hard-fail-global-config-drift")
    if not mutation.get("repositoryStatusPrePostStable"):
        failures.append("hard-fail-repository-posture-drift")
    claims = report.get("claimBoundary", {})
    required_false = {
        "provesCrossHostPortability",
        "provesMattOrSuperpowersBehavior",
        "provesFiveArmAblationOutcome",
        "provesDynamicMcpLifecycle",
        "provesAutomaticThreadCreation",
        "provesGlobalConfigTransaction",
        "provesProductionReadiness",
    }
    if any(claims.get(key) is not False for key in required_false):
        failures.append("hard-fail-claim-boundary")
    return failures


def _git_status_digest(cwd: Path) -> dict[str, Any]:
    completed = subprocess.run(
        ["git", "status", "--porcelain=v1"],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    encoded = completed.stdout.encode("utf-8")
    return {
        "lineCount": len(
            [line for line in completed.stdout.splitlines() if line.strip()]
        ),
        "sha256": sha256_bytes(encoded),
    }


def run_probe(
    cwd: Path,
    *,
    codex_executable: str | None,
    timeout_seconds: float,
) -> dict[str, Any]:
    cwd = cwd.resolve()
    config_path = (Path.home() / ".codex" / "config.toml").resolve()
    config_before = file_observation(config_path)
    status_before = _git_status_digest(cwd)
    executable = resolve_codex_executable(codex_executable)

    control_session = AppServerSession(
        build_command(executable),
        cwd,
        timeout_seconds,
    )
    try:
        control_initialize = initialize(control_session)
        control_skills = request_skills(control_session, cwd, request_id=1)
        control_stderr = classify_stderr(control_session.stderr_lines)
        control_session.close()
    except BaseException:
        control_session.abort()
        raise
    control_stderr = classify_stderr(control_session.stderr_lines)
    user_skills = [
        skill for skill in control_skills if skill["scope"] == "user"
    ]
    disable_override = build_disable_override(user_skills)
    disabled_command = build_command(
        executable,
        disable_override=disable_override,
    )

    disabled_session = AppServerSession(
        disabled_command,
        cwd,
        timeout_seconds,
    )
    item_notifications: list[dict[str, Any]] = []
    try:
        disabled_initialize = initialize(disabled_session)
        disabled_skills = request_skills(
            disabled_session,
            cwd,
            request_id=1,
        )
        disabled_session.send(
            {
                "id": 2,
                "method": "thread/start",
                "params": {
                    "model": MODEL,
                    "allowProviderModelFallback": False,
                    "cwd": str(cwd),
                    "approvalPolicy": "never",
                    "sandbox": "read-only",
                    "ephemeral": True,
                },
            }
        )
        thread_start = disabled_session.wait_for_response(2)
        thread_id = _thread_id(thread_start)
        disabled_session.send(
            {
                "id": 3,
                "method": "turn/start",
                "params": {
                    "threadId": thread_id,
                    "model": MODEL,
                    "effort": EFFORT,
                    "input": [
                        {
                            "type": "text",
                            "text": (
                                f"Return exactly {MARKER}. "
                                "Do not use tools, read files, or add any other text."
                            ),
                        }
                    ],
                },
            }
        )
        turn_start = disabled_session.wait_for_response(3)
        turn_id = _turn_id(turn_start)
        completed_turn: dict[str, Any] | None = None
        while True:
            message = disabled_session._next()
            if message.get("method") == "item/completed":
                params = message.get("params")
                if (
                    isinstance(params, dict)
                    and params.get("threadId") == thread_id
                    and params.get("turnId") == turn_id
                ):
                    item_notifications.append(params)
            if message.get("method") == "turn/completed":
                params = message.get("params")
                if (
                    isinstance(params, dict)
                    and params.get("threadId") == thread_id
                    and isinstance(params.get("turn"), dict)
                    and params["turn"].get("id") == turn_id
                ):
                    completed_turn = params["turn"]
                    break
        if completed_turn is None:
            raise RuntimeError("turn/completed omitted the target turn")
        target_turn = dict(completed_turn)
        target_turn["items"] = [
            params["item"]
            for params in item_notifications
            if isinstance(params.get("item"), dict)
        ]
        target_turn["itemsView"] = "eventStreamCompletedItems"
        disabled_session.close()
    except BaseException:
        disabled_session.abort()
        raise

    config_after = file_observation(config_path)
    status_after = _git_status_digest(cwd)
    comparison = compare_inventories(control_skills, disabled_skills)
    marker_turn = summarize_turn(target_turn, item_notifications)
    thread_telemetry = {
        "model": thread_start.get("model"),
        "reasoningEffort": thread_start.get("reasoningEffort"),
        "modelProvider": thread_start.get("modelProvider"),
        "cwd": str(thread_start.get("cwd", "")).replace("\\", "/"),
        "instructionSources": [
            str(path).replace("\\", "/")
            for path in thread_start.get("instructionSources", [])
        ],
        "sandbox": thread_start.get("sandbox"),
        "approvalPolicy": thread_start.get("approvalPolicy"),
        "ephemeral": True,
        "providerFallbackAllowed": False,
    }
    report = {
        "schema": 1,
        "id": PROBE_ID,
        "host": {
            "codexCliVersion": disabled_initialize.get("userAgent"),
            "platformFamily": disabled_initialize.get("platformFamily"),
            "platformOs": disabled_initialize.get("platformOs"),
            "controlUserAgent": control_initialize.get("userAgent"),
        },
        "repository": {
            "path": cwd.as_posix(),
        },
        "controlInventory": inventory_summary(control_skills),
        "disabledInventory": inventory_summary(disabled_skills),
        "exposureComparison": comparison,
        "selfAuthoredControlRows": self_authored_rows(control_skills),
        "selfAuthoredDisabledRows": self_authored_rows(disabled_skills),
        "threadTelemetry": thread_telemetry,
        "markerTurn": marker_turn,
        "turnEvidenceSource": {
            "threadIsEphemeral": True,
            "turnCompletedMayHaveEmptyItems": True,
            "itemCompletedNotificationsUsed": True,
            "threadReadIncludeTurnsAttempted": False,
            "reason": (
                "ephemeral threads reject thread/read(includeTurns=true) "
                "with JSON-RPC -32600"
            ),
        },
        "processBoundary": {
            "controlProcessReturnCode": control_session.process.returncode,
            "disabledProcessReturnCode": disabled_session.process.returncode,
            "pluginFeaturesDisabled": list(PLUGIN_FEATURES),
            "staticMcpServersDisabled": list(STATIC_MCP_NAMES),
            "disableOverrideEntryCount": len(user_skills),
            "disabledCommandLineCharacterCount": subprocess.list2cmdline(
                disabled_command
            ).__len__(),
            "globalConfigWritten": False,
            "applicationRestarted": False,
            "capabilityInstalled": False,
            "mcpToolInvoked": False,
        },
        "stderrClassification": {
            "control": control_stderr,
            "disabled": classify_stderr(disabled_session.stderr_lines),
        },
        "mutationBoundary": {
            "configPath": config_path.as_posix(),
            "configBefore": config_before,
            "configAfter": config_after,
            "configPrePostStable": config_before == config_after,
            "repositoryStatusBefore": status_before,
            "repositoryStatusAfter": status_after,
            "repositoryStatusPrePostStable": status_before == status_after,
            "rawConfigRecorded": False,
            "rawRepositoryStatusRecorded": False,
        },
        "claimBoundary": {
            "provesCurrentHostOneOffUserSkillDisablement": True,
            "provesCurrentHostExactWeakModelAndEffort": True,
            "provesMarkerOnlyTurnWithoutForbiddenActions": True,
            "provesCrossHostPortability": False,
            "provesMattOrSuperpowersBehavior": False,
            "provesFiveArmAblationOutcome": False,
            "provesDynamicMcpLifecycle": False,
            "provesAutomaticThreadCreation": False,
            "provesGlobalConfigTransaction": False,
            "provesProductionReadiness": False,
        },
    }
    report["validationFailures"] = validate_probe_report(report)
    report["status"] = (
        "pass-current-host-task-scoped-exposure"
        if not report["validationFailures"]
        else "fail-evidence-contract"
    )
    report["reportSha256"] = canonical_sha256(
        {
            key: value
            for key, value in report.items()
            if key != "reportSha256"
        }
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cwd", type=Path, default=Path.cwd())
    parser.add_argument("--codex-executable")
    parser.add_argument("--timeout-seconds", type=float, default=90.0)
    arguments = parser.parse_args()
    report = run_probe(
        arguments.cwd,
        codex_executable=arguments.codex_executable,
        timeout_seconds=arguments.timeout_seconds,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if not report["validationFailures"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
