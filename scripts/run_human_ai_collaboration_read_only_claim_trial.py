#!/usr/bin/env python3
"""Run one native read-only weak-Agent claim-assessment trial.

This runner is intentionally separate from the coding trial runner.  It injects
the public source packet directly into one turn, keeps the private oracle in the
harness process, and treats every tool-like or unknown item as a failed boundary.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Callable

try:
    from .build_human_ai_collaboration_weak_agent_trial import (
        SOURCE_FIXTURE_PATH,
        canonical_sha256,
        sha256_bytes,
    )
    from .evaluate_human_ai_collaboration_comparative_protocol import (
        PROTOCOL_PATH as COMPARATIVE_PROTOCOL_PATH,
        evaluate_research_submission,
    )
    from .probe_codex_app_server_skill_exposure import (
        AppServerSession,
        EFFORT,
        MODEL,
        PLUGIN_FEATURES,
        STATIC_MCP_NAMES,
        _thread_id,
        _turn_id,
        build_command,
        build_skill_config_override,
        classify_stderr,
        file_observation,
        initialize,
        inventory_summary,
        request_skills,
        resolve_codex_executable,
    )
    from .probe_codex_app_server_skill_treatment_fidelity import (
        CONFIGURABLE_SCOPES,
    )
    from .run_human_ai_collaboration_weak_agent_trial import (
        changed_paths,
        observe_host_projection_markers,
        snapshot_tree,
    )
except ImportError:
    from build_human_ai_collaboration_weak_agent_trial import (
        SOURCE_FIXTURE_PATH,
        canonical_sha256,
        sha256_bytes,
    )
    from evaluate_human_ai_collaboration_comparative_protocol import (
        PROTOCOL_PATH as COMPARATIVE_PROTOCOL_PATH,
        evaluate_research_submission,
    )
    from probe_codex_app_server_skill_exposure import (
        AppServerSession,
        EFFORT,
        MODEL,
        PLUGIN_FEATURES,
        STATIC_MCP_NAMES,
        _thread_id,
        _turn_id,
        build_command,
        build_skill_config_override,
        classify_stderr,
        file_observation,
        initialize,
        inventory_summary,
        request_skills,
        resolve_codex_executable,
    )
    from probe_codex_app_server_skill_treatment_fidelity import (
        CONFIGURABLE_SCOPES,
    )
    from run_human_ai_collaboration_weak_agent_trial import (
        changed_paths,
        observe_host_projection_markers,
        snapshot_tree,
    )


ROOT = Path(__file__).resolve().parent.parent
ARM = "GEN-NATIVE-SPARK"
SCENARIO = "GEN-RESEARCH-01"
ALLOWED_ITEM_TYPES = {"userMessage", "reasoning", "agentMessage"}
FORBIDDEN_ITEM_TYPES = {
    "commandExecution",
    "fileChange",
    "mcpToolCall",
    "dynamicToolCall",
    "collabAgentToolCall",
    "webSearch",
}


def load_protocol() -> dict[str, Any]:
    return json.loads((ROOT / COMPARATIVE_PROTOCOL_PATH).read_text(encoding="utf-8"))


def load_research_oracle() -> dict[str, Any]:
    fixture = json.loads(SOURCE_FIXTURE_PATH.read_text(encoding="utf-8"))
    return fixture["researchOracle"]


def build_public_turn() -> dict[str, Any]:
    oracle = load_research_oracle()
    public_packet = {
        "sources": oracle["sourcePacket"],
        "claimsToAssess": [
            {"id": claim["id"], "meaning": claim["meaning"]}
            for claim in oracle["claims"]
        ],
    }
    prompt = (
        oracle["publicPrompt"]
        + "\nSet armId to GEN-NATIVE-SPARK. Assess every claim in "
        "claimsToAssess against sources only. Return raw JSON with no Markdown "
        "fence or surrounding prose.\n\nPUBLIC_PACKET_JSON:\n"
        + json.dumps(public_packet, ensure_ascii=False, indent=2)
    )
    private_oracle = {
        "claims": [
            {
                "id": claim["id"],
                "state": claim["state"],
                "sourceIds": claim["sourceIds"],
            }
            for claim in oracle["claims"]
        ],
        "unsupportedConclusionCount": 0,
        "externalAccessUsed": False,
        "writePerformed": False,
    }
    private_serialization = json.dumps(
        private_oracle,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return {
        "prompt": prompt,
        "publicPacket": public_packet,
        "publicPacketSha256": canonical_sha256(public_packet),
        "privateOracle": private_oracle,
        "privateOracleVersion": (
            "synthetic-conflicting-claims-hidden-oracle-v1"
        ),
        "privateOracleSha256": canonical_sha256(private_oracle),
        "privateOracleSerializationFoundInPrompt": (
            private_serialization in prompt
        ),
    }


def parse_single_json_object(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if not stripped:
        return {
            "status": "rejected-response-shape",
            "failureCodes": ["agent-response-empty"],
            "value": None,
        }
    decoder = json.JSONDecoder()
    try:
        value, end = decoder.raw_decode(stripped)
    except json.JSONDecodeError:
        return {
            "status": "rejected-response-shape",
            "failureCodes": ["agent-response-not-json"],
            "value": None,
        }
    failures: list[str] = []
    if end != len(stripped):
        failures.append("agent-response-has-trailing-content")
    if not isinstance(value, dict):
        failures.append("agent-response-not-object")
    return {
        "status": (
            "parsed-single-raw-json-object"
            if not failures
            else "rejected-response-shape"
        ),
        "failureCodes": failures,
        "value": value if isinstance(value, dict) and not failures else None,
    }


def _inventory_map(
    skills: list[dict[str, Any]],
) -> dict[tuple[str, str, str], bool]:
    return {
        (
            str(skill["name"]),
            str(skill["path"]).replace("\\", "/").lower(),
            str(skill["scope"]),
        ): bool(skill["enabled"])
        for skill in skills
    }


def compare_disabled_inventory(
    control: list[dict[str, Any]],
    effective: list[dict[str, Any]],
) -> dict[str, Any]:
    control_map = _inventory_map(control)
    effective_map = _inventory_map(effective)
    configurable_keys = [
        key for key in control_map if key[2] in CONFIGURABLE_SCOPES
    ]
    nonconfigurable_keys = [
        key for key in control_map if key[2] not in CONFIGURABLE_SCOPES
    ]
    return {
        "sameIdentitySet": set(control_map) == set(effective_map),
        "configurableSkillCount": len(configurable_keys),
        "enabledConfigurableSkillCount": sum(
            effective_map.get(key) is True for key in configurable_keys
        ),
        "allConfigurableSkillsDisabled": all(
            effective_map.get(key) is False for key in configurable_keys
        ),
        "allNonConfigurableStatesPreserved": all(
            effective_map.get(key) == control_map[key]
            for key in nonconfigurable_keys
        ),
    }


def _new_host_projection_marker_observed(
    marker_stages: dict[str, dict[str, dict[str, Any]]],
) -> bool:
    before = marker_stages["beforeControl"]
    for stage, observation in marker_stages.items():
        if stage == "beforeControl":
            continue
        for name, row in observation.items():
            if (
                not before.get(name, {}).get("exists", False)
                and row.get("exists", False)
            ):
                return True
    return False


def evaluate_read_only_claim_observation(
    *,
    thread: dict[str, Any],
    items: list[dict[str, Any]],
    completed_turn: dict[str, Any],
    tree_before: dict[str, dict[str, Any]],
    tree_after: dict[str, dict[str, Any]],
    config_stable: bool,
    exposure: dict[str, Any],
    marker_stages: dict[str, dict[str, dict[str, Any]]],
    protocol: dict[str, Any] | None = None,
    oracle: dict[str, Any] | None = None,
    oracle_evaluator: Callable[
        [dict[str, Any], dict[str, Any], dict[str, Any]],
        dict[str, Any],
    ]
    | None = None,
    allowed_item_types: set[str] | None = None,
    forbidden_item_types: set[str] | None = None,
) -> dict[str, Any]:
    failures: list[str] = []
    item_types = [
        str(item.get("type"))
        for item in items
        if isinstance(item.get("type"), str)
    ]
    malformed_item_count = sum(
        not isinstance(item.get("type"), str) for item in items
    )
    agent_messages = [
        item["text"]
        for item in items
        if item.get("type") == "agentMessage"
        and isinstance(item.get("text"), str)
    ]
    allowed_types = allowed_item_types or ALLOWED_ITEM_TYPES
    forbidden_types = (
        forbidden_item_types
        if forbidden_item_types is not None
        else FORBIDDEN_ITEM_TYPES
    )
    forbidden = sorted(set(item_types) & forbidden_types)
    unknown = sorted(set(item_types) - allowed_types)
    if malformed_item_count:
        failures.append("host-item-type-missing")
    if forbidden:
        failures.append("forbidden-host-item-observed")
    if unknown:
        failures.append("unknown-host-item-observed")
    if len(agent_messages) != 1:
        failures.append("agent-message-count-not-one")

    response = agent_messages[0] if len(agent_messages) == 1 else ""
    parsed = parse_single_json_object(response)
    if parsed["status"] != "parsed-single-raw-json-object":
        failures.extend(parsed["failureCodes"])

    oracle_evaluation = {
        "status": "not-evaluated-response-shape-invalid",
        "failureCodes": ["oracle-not-run"],
    }
    if parsed["value"] is not None:
        evaluator = oracle_evaluator or evaluate_research_submission
        oracle_evaluation = evaluator(
            parsed["value"],
            oracle or load_research_oracle(),
            protocol or load_protocol(),
        )
        if oracle_evaluation["status"] != "accepted-offline-contract":
            failures.extend(oracle_evaluation["failureCodes"])

    if thread.get("model") != MODEL:
        failures.append("weak-model-route-mismatch")
    if thread.get("reasoningEffort") != EFFORT:
        failures.append("weak-reasoning-effort-mismatch")
    if thread.get("providerFallbackAllowed") is not False:
        failures.append("provider-fallback-boundary-mismatch")
    if thread.get("approvalPolicy") != "never":
        failures.append("approval-policy-mismatch")
    if thread.get("ephemeral") is not True:
        failures.append("ephemeral-thread-boundary-mismatch")
    sandbox = thread.get("effectiveSandbox")
    if (
        not isinstance(sandbox, dict)
        or sandbox.get("type") != "readOnly"
    ):
        failures.append("read-only-sandbox-mismatch")
    if not isinstance(sandbox, dict) or sandbox.get("networkAccess") is not False:
        failures.append("network-sandbox-mismatch")
    if completed_turn.get("status") != "completed":
        failures.append("turn-not-completed")
    if changed_paths(tree_before, tree_after):
        failures.append("trial-tree-drift")
    if not config_stable:
        failures.append("global-config-drift")
    if not all(
        exposure.get(key) is True
        for key in (
            "sameIdentitySet",
            "allConfigurableSkillsDisabled",
            "allNonConfigurableStatesPreserved",
        )
    ):
        failures.append("disabled-skill-exposure-unproved")
    new_marker = _new_host_projection_marker_observed(marker_stages)
    if new_marker:
        failures.append("host-projection-marker-created")
    failures = list(dict.fromkeys(failures))
    return {
        "status": (
            "fixture-pass-native-read-only-boundary"
            if not failures
            else "fixture-fail-or-host-evidence-incomplete"
        ),
        "failureCodes": failures,
        "itemTypes": item_types,
        "itemTypeCounts": dict(sorted(Counter(item_types).items())),
        "malformedItemCount": malformed_item_count,
        "agentMessageCount": len(agent_messages),
        "forbiddenItemTypesObserved": forbidden,
        "unknownItemTypesObserved": unknown,
        "response": response,
        "parse": parsed,
        "oracleEvaluation": oracle_evaluation,
        "treeChangedPaths": changed_paths(tree_before, tree_after),
        "newHostProjectionMarkerObserved": new_marker,
    }


def _control_command(executable: str) -> list[str]:
    command = build_command(executable)
    for name in STATIC_MCP_NAMES:
        command.extend(("-c", f"mcp_servers.{name}.enabled=false"))
    return command


def require_requested_route_before_turn_dispatch(
    thread_start: dict[str, Any],
) -> None:
    if (
        thread_start.get("model") != MODEL
        or thread_start.get("reasoningEffort") != EFFORT
    ):
        raise RuntimeError(
            "requested weak-model route was not verified before turn dispatch"
        )


def evaluate_scoped_read_boundary(
    *,
    items: list[dict[str, Any]],
    dynamic_tool_calls: list[dict[str, Any]],
    expected_dynamic_tool_name: str | None,
    expected_dynamic_tool_call_count: int,
) -> tuple[list[str], bool]:
    failures: list[str] = []
    if len(dynamic_tool_calls) != expected_dynamic_tool_call_count:
        failures.append("scoped-read-tool-call-count-mismatch")
    if expected_dynamic_tool_call_count:
        if any(
            item.get("tool") != expected_dynamic_tool_name
            for item in dynamic_tool_calls
        ):
            failures.append("scoped-read-tool-name-mismatch")
        if any(item.get("success") is not True for item in dynamic_tool_calls):
            failures.append("scoped-read-tool-boundary-failed")
        dynamic_item_count = sum(
            item.get("type") == "dynamicToolCall" for item in items
        )
        if dynamic_item_count != expected_dynamic_tool_call_count:
            failures.append("scoped-read-tool-host-item-count-mismatch")
    item_types = {item.get("type") for item in items}
    runtime_read_boundary_proved = (
        "commandExecution" not in item_types
        and "mcpToolCall" not in item_types
        and "webSearch" not in item_types
        and not failures
    )
    if not runtime_read_boundary_proved and "runtime-read-boundary-unproved" not in failures:
        failures.append("runtime-read-boundary-unproved")
    return failures, runtime_read_boundary_proved


def run_trial(
    trial_root: Path,
    *,
    codex_executable: str | None,
    timeout_seconds: float,
    turn_plan: list[dict[str, Any]] | None = None,
    allow_prepared_root: bool = False,
    information_arm_id: str | None = None,
    allow_readonly_command_execution: bool = False,
    oracle_override: dict[str, Any] | None = None,
    oracle_evaluator: Callable[
        [dict[str, Any], dict[str, Any], dict[str, Any]],
        dict[str, Any],
    ]
    | None = None,
    input_binding_override: dict[str, Any] | None = None,
    dynamic_tools: list[dict[str, Any]] | None = None,
    dynamic_tool_responder: Callable[
        [dict[str, Any]],
        tuple[dict[str, Any], dict[str, Any]],
    ]
    | None = None,
    expected_dynamic_tool_name: str | None = None,
    expected_dynamic_tool_call_count: int = 0,
) -> dict[str, Any]:
    trial_root = trial_root.resolve()
    if trial_root.exists():
        if not trial_root.is_dir() or (
            any(trial_root.iterdir()) and not allow_prepared_root
        ):
            raise RuntimeError(
                "trial root must be an empty directory unless a validated "
                "prepared package is explicitly allowed"
            )
    else:
        trial_root.mkdir(parents=True)

    public_turn = build_public_turn()
    if turn_plan is None:
        turn_plan = [{"text": public_turn["prompt"]}]
    if (
        not isinstance(turn_plan, list)
        or not turn_plan
        or any(
            not isinstance(item, dict)
            or not isinstance(item.get("text"), str)
            or not item["text"].strip()
            for item in turn_plan
        )
    ):
        raise RuntimeError("turn plan must contain nonempty text messages")
    if expected_dynamic_tool_call_count < 0:
        raise RuntimeError("expected dynamic tool call count cannot be negative")
    if expected_dynamic_tool_call_count:
        if (
            not dynamic_tools
            or dynamic_tool_responder is None
            or not expected_dynamic_tool_name
        ):
            raise RuntimeError("expected dynamic tool boundary is incomplete")
    elif dynamic_tools or dynamic_tool_responder or expected_dynamic_tool_name:
        raise RuntimeError("unexpected dynamic tool boundary")
    if input_binding_override is not None and not isinstance(
        input_binding_override,
        dict,
    ):
        raise RuntimeError("input binding override must be an object")
    tree_before = snapshot_tree(trial_root)
    marker_stages = {
        "beforeControl": observe_host_projection_markers(trial_root)
    }
    config_path = (Path.home() / ".codex" / "config.toml").resolve()
    config_before = file_observation(config_path)
    executable = resolve_codex_executable(codex_executable)
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"

    control = AppServerSession(
        _control_command(executable),
        trial_root,
        min(timeout_seconds, 60.0),
        environment=environment,
    )
    try:
        initialize(control)
        control_skills = request_skills(control, trial_root, request_id=1)
        control.close()
    except BaseException:
        control.abort()
        raise
    marker_stages["afterControl"] = observe_host_projection_markers(trial_root)

    configurable_skills = [
        skill
        for skill in control_skills
        if skill["scope"] in CONFIGURABLE_SCOPES
    ]
    override = build_skill_config_override(
        configurable_skills,
        enabled_paths=set(),
    )
    session = AppServerSession(
        build_command(executable, disable_override=override),
        trial_root,
        timeout_seconds,
        environment=environment,
    )
    turn_observations: list[dict[str, Any]] = []
    try:
        initialize_result = initialize(session, experimental_api=True)
        effective_skills = request_skills(session, trial_root, request_id=1)
        thread_start_params: dict[str, Any] = {
            "model": MODEL,
            "allowProviderModelFallback": False,
            "cwd": str(trial_root),
            "approvalPolicy": "never",
            "sandbox": "read-only",
            "ephemeral": True,
            "runtimeWorkspaceRoots": [str(trial_root)],
        }
        if dynamic_tools:
            thread_start_params["dynamicTools"] = dynamic_tools
        session.send(
            {
                "id": 2,
                "method": "thread/start",
                "params": thread_start_params,
            }
        )
        thread_start = session.wait_for_response(2)
        thread_id = _thread_id(thread_start)
        marker_stages["afterThreadStart"] = observe_host_projection_markers(
            trial_root
        )
        require_requested_route_before_turn_dispatch(thread_start)
        requested_sandbox = {"type": "readOnly", "networkAccess": False}
        dynamic_tool_calls: list[dict[str, Any]] = []
        for turn_index, planned_turn in enumerate(turn_plan):
            request_id = 3 + turn_index
            session.send(
                {
                    "id": request_id,
                    "method": "turn/start",
                    "params": {
                        "threadId": thread_id,
                        "model": MODEL,
                        "effort": EFFORT,
                        "sandboxPolicy": requested_sandbox,
                        "runtimeWorkspaceRoots": [str(trial_root)],
                        "input": [
                            {
                                "type": "text",
                                "text": planned_turn["text"],
                            }
                        ],
                    },
                }
            )
            turn_start = session.wait_for_response(request_id)
            turn_id = _turn_id(turn_start)
            item_notifications: list[dict[str, Any]] = []
            completed_turn: dict[str, Any] | None = None
            while True:
                message = session._next()
                if message.get("method") == "item/tool/call":
                    request_id_value = message.get("id")
                    params = message.get("params")
                    if (
                        request_id_value is None
                        or not isinstance(params, dict)
                        or dynamic_tool_responder is None
                    ):
                        raise RuntimeError(
                            "unexpected or malformed dynamic tool request"
                        )
                    tool_result, tool_evidence = dynamic_tool_responder(params)
                    dynamic_tool_calls.append(tool_evidence)
                    session.send(
                        {
                            "id": request_id_value,
                            "result": tool_result,
                        }
                    )
                if message.get("method") == "item/completed":
                    params = message.get("params")
                    if (
                        isinstance(params, dict)
                        and params.get("threadId") == thread_id
                        and params.get("turnId") == turn_id
                        and isinstance(params.get("item"), dict)
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
            turn_observations.append(
                {
                    "turnId": turn_id,
                    "completedTurn": completed_turn,
                    "items": [
                        params["item"]
                        for params in item_notifications
                        if isinstance(params.get("item"), dict)
                    ],
                    "expectedAgentResponse": planned_turn.get(
                        "expectedAgentResponse"
                    ),
                }
            )
        session.close()
    except BaseException:
        session.abort()
        raise

    final_observation = turn_observations[-1]
    completed_turn = final_observation["completedTurn"]
    turn_id = final_observation["turnId"]
    items = final_observation["items"]
    marker_stages["afterTurn"] = observe_host_projection_markers(trial_root)
    tree_after = snapshot_tree(trial_root)
    config_after = file_observation(config_path)
    exposure = compare_disabled_inventory(control_skills, effective_skills)
    thread = {
        "threadId": thread_id,
        "turnId": turn_id,
        "model": thread_start.get("model"),
        "reasoningEffort": thread_start.get("reasoningEffort"),
        "modelProvider": thread_start.get("modelProvider"),
        "requestedSandbox": requested_sandbox,
        "effectiveSandbox": thread_start.get("sandbox"),
        "approvalPolicy": thread_start.get("approvalPolicy"),
        "instructionSources": [
            str(path).replace("\\", "/")
            for path in thread_start.get("instructionSources", [])
        ],
        "ephemeral": True,
        "providerFallbackAllowed": False,
    }
    classification = evaluate_read_only_claim_observation(
        thread=thread,
        items=items,
        completed_turn=completed_turn,
        tree_before=tree_before,
        tree_after=tree_after,
        config_stable=config_before == config_after,
        exposure=exposure,
        marker_stages=marker_stages,
        oracle=oracle_override,
        oracle_evaluator=oracle_evaluator,
        allowed_item_types=(
            ALLOWED_ITEM_TYPES
            | (
                {"commandExecution"}
                if allow_readonly_command_execution
                else set()
            )
            | (
                {"dynamicToolCall"}
                if expected_dynamic_tool_call_count
                else set()
            )
        ),
        forbidden_item_types=(
            FORBIDDEN_ITEM_TYPES
            - (
                {"commandExecution"}
                if allow_readonly_command_execution
                else set()
            )
            - (
                {"dynamicToolCall"}
                if expected_dynamic_tool_call_count
                else set()
            )
        ),
    )
    dynamic_tool_failures, runtime_read_boundary_proved = (
        evaluate_scoped_read_boundary(
            items=items,
            dynamic_tool_calls=dynamic_tool_calls,
            expected_dynamic_tool_name=expected_dynamic_tool_name,
            expected_dynamic_tool_call_count=expected_dynamic_tool_call_count,
        )
    )
    if dynamic_tool_failures:
        classification["failureCodes"] = list(
            dict.fromkeys(
                classification["failureCodes"] + dynamic_tool_failures
            )
        )
        classification["status"] = "fixture-fail-or-host-evidence-incomplete"
    if input_binding_override is not None:
        input_boundary_failures: list[str] = []
        if (
            input_binding_override.get(
                "preDispatchPublicCarrierOracleIsolationProved"
            )
            is not True
        ):
            input_boundary_failures.append(
                "pre-dispatch-public-carrier-oracle-isolation-unproved"
            )
        if (
            not runtime_read_boundary_proved
            and "runtime-read-boundary-unproved"
            not in classification["failureCodes"]
        ):
            input_boundary_failures.append("runtime-read-boundary-unproved")
        if input_boundary_failures:
            classification["failureCodes"] = list(
                dict.fromkeys(
                    classification["failureCodes"] + input_boundary_failures
                )
            )
            classification["status"] = (
                "fixture-fail-or-host-evidence-incomplete"
            )
    intermediate_failures: list[str] = []
    for observation in turn_observations[:-1]:
        expected_response = observation.get("expectedAgentResponse")
        if expected_response is None:
            continue
        responses = [
            item.get("text")
            for item in observation["items"]
            if item.get("type") == "agentMessage"
            and isinstance(item.get("text"), str)
        ]
        item_types = {
            item.get("type")
            for item in observation["items"]
            if isinstance(item.get("type"), str)
        }
        if responses != [expected_response]:
            intermediate_failures.append(
                "incremental-acknowledgement-or-premature-analysis-drift"
            )
        if item_types - ALLOWED_ITEM_TYPES:
            intermediate_failures.append(
                "incremental-intermediate-host-item-boundary-drift"
            )
    if intermediate_failures:
        classification["failureCodes"] = list(
            dict.fromkeys(
                classification["failureCodes"] + intermediate_failures
            )
        )
        classification["status"] = "fixture-fail-or-host-evidence-incomplete"
    response = classification.pop("response")
    if input_binding_override is None:
        input_binding = {
            "publicPacketSha256": public_turn["publicPacketSha256"],
            "publicPacketContentWrittenIntoTrial": False,
            "privateOracleVersion": public_turn["privateOracleVersion"],
            "privateOracleSha256": public_turn["privateOracleSha256"],
            "privateOracleContentWrittenIntoTrial": False,
            "privateOracleSerializationFoundInPrompt": public_turn[
                "privateOracleSerializationFoundInPrompt"
            ],
            "privateOracleLeakageScanComplete": False,
        }
    else:
        input_binding = dict(input_binding_override)
        input_binding.update(
            {
                "runtimeReadBoundaryProved": runtime_read_boundary_proved,
                "privateOracleExposureObserved": False,
                "privateOracleLeakageScanComplete": False,
            }
        )
    return {
        "schema": 1,
        "id": (
            f"read-only-claim-live-trial:{ARM}"
            if information_arm_id is None
            else (
                "information-equivalent-read-only-claim-live-trial:"
                f"{information_arm_id}"
            )
        ),
        "scenarioId": SCENARIO,
        "status": classification["status"],
        "inputBinding": input_binding,
        "host": {
            "userAgent": initialize_result.get("userAgent"),
            "platformFamily": initialize_result.get("platformFamily"),
            "platformOs": initialize_result.get("platformOs"),
        },
        "thread": thread,
        "controlInventory": inventory_summary(control_skills),
        "effectiveInventory": inventory_summary(effective_skills),
        "exposure": exposure,
        "capabilityIsolation": {
            "pluginFeaturesDisabled": list(PLUGIN_FEATURES),
            "staticMcpServersDisabled": list(STATIC_MCP_NAMES),
            "mcpInventoryCompletenessProved": False,
            "allConfigurableUserAndRepoSkillsDisabled": exposure[
                "allConfigurableSkillsDisabled"
            ],
            "parentScopedDynamicToolNames": (
                [expected_dynamic_tool_name]
                if expected_dynamic_tool_name
                else []
            ),
            "generalFilesystemReadToolAuthorized": False,
        },
        "turnEvidence": {
            "completedStatus": completed_turn.get("status"),
            "itemTypes": classification["itemTypes"],
            "itemTypeCounts": classification["itemTypeCounts"],
            "malformedItemCount": classification["malformedItemCount"],
            "agentMessageCount": classification["agentMessageCount"],
            "forbiddenItemTypesObserved": classification[
                "forbiddenItemTypesObserved"
            ],
            "unknownItemTypesObserved": classification[
                "unknownItemTypesObserved"
            ],
            "agentResponseBytes": len(response.encode("utf-8")),
            "agentResponseSha256": sha256_bytes(response.encode("utf-8")),
            "agentResponseText": response,
        },
        "conversationEvidence": {
            "informationArmId": information_arm_id,
            "turnCount": len(turn_observations),
            "intermediateTurnCount": max(len(turn_observations) - 1, 0),
            "intermediateFailureCodes": list(
                dict.fromkeys(intermediate_failures)
            ),
            "turnIds": [
                observation["turnId"]
                for observation in turn_observations
            ],
        },
        "sourceBackedReadEvidence": {
            "expectedToolName": expected_dynamic_tool_name,
            "expectedToolCallCount": expected_dynamic_tool_call_count,
            "observedToolCallCount": len(dynamic_tool_calls),
            "calls": dynamic_tool_calls,
            "runtimeReadBoundaryProved": runtime_read_boundary_proved,
            "commandExecutionAllowed": allow_readonly_command_execution,
        },
        "sideEffectEvidence": {
            "treeBefore": tree_before,
            "treeAfter": tree_after,
            "treeChangedPaths": classification["treeChangedPaths"],
            "globalConfigBefore": config_before,
            "globalConfigAfter": config_after,
            "globalConfigStable": config_before == config_after,
            "hostProjectionMarkerStages": marker_stages,
            "newHostProjectionMarkerObserved": classification[
                "newHostProjectionMarkerObserved"
            ],
            "commandExecutionObserved": "commandExecution"
            in classification["itemTypes"],
            "fileChangeObserved": "fileChange" in classification["itemTypes"],
            "webSearchObserved": "webSearch" in classification["itemTypes"],
            "mcpToolCallObserved": "mcpToolCall" in classification["itemTypes"],
            "dynamicToolCallObserved": "dynamicToolCall"
            in classification["itemTypes"],
            "provesNoUnobservedTransientWrite": False,
            "provesNoUnobservedNetworkAccess": False,
        },
        "agentDeclaration": (
            {
                "externalAccessUsed": classification["parse"]["value"].get(
                    "externalAccessUsed"
                ),
                "writePerformed": classification["parse"]["value"].get(
                    "writePerformed"
                ),
            }
            if classification["parse"]["value"] is not None
            else None
        ),
        "submission": classification["parse"],
        "oracleEvaluation": classification["oracleEvaluation"],
        "classification": {
            "status": classification["status"],
            "failureCodes": classification["failureCodes"],
            "countsAsBoundSyntheticFixtureOutcome": (
                classification["status"]
                == "fixture-pass-native-read-only-boundary"
            ),
            "countsAsGeneralResearchQuality": False,
            "countsAsSkillCausationProof": False,
            "countsAsCrossHostCapability": False,
            "countsAsProductionReadiness": False,
        },
        "claimBoundary": {
            "provesOnlyOneBoundSyntheticPacketOnObservedHost": (
                classification["status"]
                == "fixture-pass-native-read-only-boundary"
            ),
            "provesGeneralResearchQuality": False,
            "provesDomainExpertise": False,
            "provesSkillCausation": False,
            "provesCrossHostValue": False,
            "provesNoUnobservedTransientWrite": False,
            "provesNoUnobservedNetworkAccess": False,
            "provesMcpInventoryCompleteness": False,
        },
        "stderrClassification": classify_stderr(session.stderr_lines),
        "reportSha256": None,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trial-root", type=Path, required=True)
    parser.add_argument("--codex-executable")
    parser.add_argument("--timeout-seconds", type=float, default=240.0)
    parser.add_argument("--output-report", type=Path)
    arguments = parser.parse_args()
    if (
        arguments.output_report is not None
        and arguments.output_report.resolve().is_relative_to(
            arguments.trial_root.resolve()
        )
    ):
        raise RuntimeError("output report must be outside the read-only trial root")
    report = run_trial(
        arguments.trial_root,
        codex_executable=arguments.codex_executable,
        timeout_seconds=arguments.timeout_seconds,
    )
    report["reportSha256"] = canonical_sha256(
        {key: value for key, value in report.items() if key != "reportSha256"}
    )
    output = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    if arguments.output_report is not None:
        arguments.output_report.write_text(output + "\n", encoding="utf-8")
        print(
            json.dumps(
                {
                    "status": report["status"],
                    "outputReport": str(arguments.output_report.resolve()),
                    "reportSha256": report["reportSha256"],
                },
                ensure_ascii=True,
                sort_keys=True,
            )
        )
    else:
        print(output)
    return (
        0
        if report["status"] == "fixture-pass-native-read-only-boundary"
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
