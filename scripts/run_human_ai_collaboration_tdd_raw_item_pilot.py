#!/usr/bin/env python3
"""Run one non-scored native TDD raw app-server instrumentation pilot."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any

try:
    from .build_human_ai_collaboration_tdd_trial import (
        ALLOWED_MUTABLE_FILES,
        build_trial_package,
        canonical_sha256,
        evaluate_tdd_timeline,
        snapshot_trial_tree,
    )
    from .normalize_human_ai_collaboration_tdd_app_server_items import (
        normalize_tdd_app_server_event_stream,
    )
    from .probe_codex_app_server_skill_exposure import (
        AppServerSession,
        EFFORT,
        MODEL,
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
except ImportError:
    from build_human_ai_collaboration_tdd_trial import (
        ALLOWED_MUTABLE_FILES,
        build_trial_package,
        canonical_sha256,
        evaluate_tdd_timeline,
        snapshot_trial_tree,
    )
    from normalize_human_ai_collaboration_tdd_app_server_items import (
        normalize_tdd_app_server_event_stream,
    )
    from probe_codex_app_server_skill_exposure import (
        AppServerSession,
        EFFORT,
        MODEL,
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


ROOT = Path(__file__).resolve().parent.parent
PILOT_ID = "human-ai-collaboration-tdd-raw-item-pilot-v1"
ARM = "SE-TDD-NATIVE-SPARK"


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def changed_paths(
    before: dict[str, Any],
    after: dict[str, Any],
) -> list[str]:
    before_files = before.get("files", {})
    after_files = after.get("files", {})
    return sorted(
        path
        for path in set(before_files) | set(after_files)
        if before_files.get(path) != after_files.get(path)
    )


def observe_host_projection_markers(root: Path) -> dict[str, bool]:
    return {
        name: (root / name).exists()
        for name in (".agents", ".codex", ".git")
    }


def compare_disabled_inventory(
    before: list[dict[str, Any]],
    after: list[dict[str, Any]],
) -> dict[str, Any]:
    def keyed(
        rows: list[dict[str, Any]],
    ) -> dict[tuple[str, str, str], bool]:
        return {
            (
                str(row["name"]),
                str(row["path"]).replace("\\", "/").lower(),
                str(row["scope"]),
            ): bool(row["enabled"])
            for row in rows
        }

    control = keyed(before)
    effective = keyed(after)
    configurable = {
        key
        for key in control
        if key[2] in CONFIGURABLE_SCOPES
    }
    nonconfigurable = set(control) - configurable
    return {
        "sameIdentitySet": set(control) == set(effective),
        "configurableSkillCount": len(configurable),
        "allConfigurableSkillsDisabled": all(
            effective.get(key) is False for key in configurable
        ),
        "allNonConfigurableStatesPreserved": all(
            effective.get(key) == control[key] for key in nonconfigurable
        ),
    }


def evaluate_pilot(
    *,
    thread: dict[str, Any],
    exposure: dict[str, Any],
    normalization: dict[str, Any],
    offline_timeline: dict[str, Any],
    changed: list[str],
    config_stable: bool,
    turn_status: str | None,
) -> dict[str, Any]:
    failures: list[str] = []
    if thread.get("model") != MODEL:
        failures.append("requested-model-not-observed")
    if thread.get("reasoningEffort") != EFFORT:
        failures.append("requested-reasoning-effort-not-observed")
    if thread.get("providerFallbackAllowed") is not False:
        failures.append("provider-fallback-boundary-drifted")
    if thread.get("approvalPolicy") != "never":
        failures.append("approval-policy-drifted")
    if thread.get("requestedSandbox", {}).get("type") != "workspaceWrite":
        failures.append("workspace-write-sandbox-not-requested")
    if thread.get("requestedSandbox", {}).get("networkAccess") is not False:
        failures.append("network-boundary-drifted")
    for key in (
        "sameIdentitySet",
        "allConfigurableSkillsDisabled",
        "allNonConfigurableStatesPreserved",
    ):
        if exposure.get(key) is not True:
            failures.append(f"skill-exposure-{key}-not-proved")
    if normalization.get("status") != "normalized-observable":
        failures.append("raw-event-normalization-incomplete")
    if normalization.get("rawEnvelopeCount", 0) <= 0:
        failures.append("target-turn-raw-events-not-observed")
    if not set(changed) <= set(ALLOWED_MUTABLE_FILES):
        failures.append("trial-file-scope-drifted")
    if not config_stable:
        failures.append("global-config-drifted")
    if turn_status != "completed":
        failures.append("target-turn-not-completed")
    failures = list(dict.fromkeys(failures))
    passed = not failures
    return {
        "status": (
            "current-host-raw-item-normalization-pilot-pass"
            if passed
            else "current-host-raw-item-normalization-pilot-incomplete"
        ),
        "failureCodes": failures,
        "processInstrumentationPilotPassed": passed,
        "agentTddProcessAccepted": (
            offline_timeline.get("status")
            == "accepted-offline-tdd-timeline"
        ),
        "nonScored": True,
        "countsTowardWeakAcceptance": False,
        "formalRunCounted": False,
    }


def run_pilot(
    trial_root: Path,
    *,
    raw_report: Path,
    codex_executable: str | None,
    timeout_seconds: float,
) -> dict[str, Any]:
    trial_root = trial_root.resolve()
    raw_report = raw_report.resolve()
    if raw_report == trial_root or raw_report.is_relative_to(trial_root):
        raise RuntimeError("raw report must be outside the Agent trial root")
    raw_report.parent.mkdir(parents=True, exist_ok=True)
    package = build_trial_package(
        trial_root,
        ARM,
        materialize_treatment=False,
        project_root=ROOT,
    )
    tree_before = snapshot_trial_tree(trial_root)
    marker_stages = {
        "beforeControl": observe_host_projection_markers(trial_root)
    }
    config_path = (Path.home() / ".codex" / "config.toml").resolve()
    config_before = file_observation(config_path)
    executable = resolve_codex_executable(codex_executable)
    child_environment = os.environ.copy()
    child_environment["PYTHONDONTWRITEBYTECODE"] = "1"

    control = AppServerSession(
        build_command(executable),
        trial_root,
        min(timeout_seconds, 60.0),
        environment=child_environment,
    )
    try:
        initialize_result = initialize(control)
        control_skills = request_skills(control, trial_root, request_id=1)
        control.close()
    except BaseException:
        control.abort()
        raise
    marker_stages["afterControl"] = observe_host_projection_markers(
        trial_root
    )

    configurable = [
        row
        for row in control_skills
        if row["scope"] in CONFIGURABLE_SCOPES
    ]
    override = build_skill_config_override(configurable, enabled_paths=set())
    session = AppServerSession(
        build_command(executable, disable_override=override),
        trial_root,
        timeout_seconds,
        environment=child_environment,
    )
    raw_messages: list[dict[str, Any]] = []
    try:
        initialize(session, experimental_api=True)
        effective_skills = request_skills(
            session,
            trial_root,
            request_id=1,
        )
        session.send(
            {
                "id": 2,
                "method": "thread/start",
                "params": {
                    "model": MODEL,
                    "allowProviderModelFallback": False,
                    "cwd": str(trial_root),
                    "approvalPolicy": "never",
                    "sandbox": "read-only",
                    "ephemeral": True,
                    "runtimeWorkspaceRoots": [str(trial_root)],
                },
            }
        )
        thread_start = session.wait_for_response(2)
        thread_id = _thread_id(thread_start)
        requested_sandbox = {
            "type": "workspaceWrite",
            "writableRoots": [str(trial_root)],
            "networkAccess": False,
            "excludeSlashTmp": False,
            "excludeTmpdirEnvVar": False,
        }
        session.send(
            {
                "id": 3,
                "method": "thread/settings/update",
                "params": {
                    "threadId": thread_id,
                    "sandboxPolicy": requested_sandbox,
                },
            }
        )
        session.wait_for_response(3)
        settings = [
            message.get("params")
            for message in session.messages
            if message.get("method") == "thread/settings/updated"
            and isinstance(message.get("params"), dict)
            and message["params"].get("threadId") == thread_id
        ]
        if not settings:
            settings = [
                session.wait_for_notification(
                    "thread/settings/updated",
                    predicate=lambda params: params.get("threadId")
                    == thread_id,
                )
            ]
        effective_sandbox = settings[-1].get(
            "threadSettings",
            {},
        ).get("sandboxPolicy")
        task = json.loads(
            (trial_root / "TASK.json").read_text(encoding="utf-8")
        )
        capture_start = len(session.messages)
        session.send(
            {
                "id": 4,
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
                            "text": (
                                "Treat TASK.json as the bound public task "
                                "packet. " + task["taskPrompt"]
                            ),
                        }
                    ],
                },
            }
        )
        turn_start = session.wait_for_response(4)
        turn_id = _turn_id(turn_start)
        completed_turn: dict[str, Any] | None = None
        while True:
            message = session._next()
            if message.get("method") != "turn/completed":
                continue
            params = message.get("params")
            if (
                isinstance(params, dict)
                and params.get("threadId") == thread_id
                and isinstance(params.get("turn"), dict)
                and params["turn"].get("id") == turn_id
            ):
                completed_turn = params["turn"]
                break
        raw_messages = session.messages[capture_start:]
        session.close()
    except BaseException:
        raw_messages = session.messages
        session.abort()
        raise
    marker_stages["afterTurn"] = observe_host_projection_markers(trial_root)

    raw_payload = {
        "schema": 1,
        "id": f"{PILOT_ID}:raw",
        "threadId": thread_id,
        "turnId": turn_id,
        "messages": raw_messages,
    }
    raw_bytes = (
        json.dumps(
            raw_payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")
    raw_report.write_bytes(raw_bytes)
    raw_observation = {
        "path": raw_report.as_posix(),
        "bytes": len(raw_bytes),
        "sha256": hashlib.sha256(raw_bytes).hexdigest(),
        "vendoredIntoRepositoryEvidence": False,
    }
    normalization = normalize_tdd_app_server_event_stream(
        raw_messages,
        thread_id=thread_id,
        turn_id=turn_id,
        trial_root=trial_root,
    )
    offline_timeline = evaluate_tdd_timeline(normalization["events"])
    tree_after = snapshot_trial_tree(trial_root)
    changed = changed_paths(tree_before, tree_after)
    config_after = file_observation(config_path)
    exposure = compare_disabled_inventory(
        control_skills,
        effective_skills,
    )
    thread = {
        "threadId": thread_id,
        "turnId": turn_id,
        "model": thread_start.get("model"),
        "reasoningEffort": thread_start.get("reasoningEffort"),
        "modelProvider": thread_start.get("modelProvider"),
        "approvalPolicy": thread_start.get("approvalPolicy"),
        "initialSandbox": thread_start.get("sandbox"),
        "requestedSandbox": requested_sandbox,
        "effectiveSandbox": effective_sandbox,
        "ephemeral": True,
        "providerFallbackAllowed": False,
    }
    classification = evaluate_pilot(
        thread=thread,
        exposure=exposure,
        normalization=normalization,
        offline_timeline=offline_timeline,
        changed=changed,
        config_stable=config_before == config_after,
        turn_status=(
            completed_turn.get("status")
            if isinstance(completed_turn, dict)
            else None
        ),
    )
    return {
        "schema": 1,
        "id": PILOT_ID,
        "status": classification["status"],
        "arm": ARM,
        "selectedTreatment": None,
        "host": {
            "userAgent": initialize_result.get("userAgent"),
            "platformFamily": initialize_result.get("platformFamily"),
            "platformOs": initialize_result.get("platformOs"),
        },
        "build": package["build"],
        "thread": thread,
        "controlInventory": inventory_summary(control_skills),
        "effectiveInventory": inventory_summary(effective_skills),
        "exposure": exposure,
        "rawArtifact": raw_observation,
        "normalization": normalization,
        "offlineTimeline": offline_timeline,
        "treeBefore": tree_before,
        "treeAfter": tree_after,
        "changedFiles": changed,
        "hostProjectionMarkerStages": marker_stages,
        "globalConfigBefore": config_before,
        "globalConfigAfter": config_after,
        "globalConfigStable": config_before == config_after,
        "stderrClassification": classify_stderr(session.stderr_lines),
        "classification": classification,
        "lifecycleBoundary": {
            "pluginsDisabledForChild": True,
            "knownStaticMcpServersDisabledForChild": True,
            "mcpInventoryCompletenessProved": False,
            "taskScopedAutomaticMcpReleaseProved": False,
        },
        "claimBoundary": {
            "provesCurrentHostVersionRawEventCapture": (
                classification["processInstrumentationPilotPassed"]
            ),
            "provesCurrentHostVersionRawEventNormalization": (
                classification["processInstrumentationPilotPassed"]
            ),
            "provesTddSkillValue": False,
            "provesTreatmentDelivery": False,
            "provesSkillCausation": False,
            "provesWeakAgentAcceptance": False,
            "provesBoundFixtureTddOutcome": (
                classification["agentTddProcessAccepted"]
            ),
            "provesNoUnobservedTransientWrite": False,
            "provesCrossHostSchemaStability": False,
            "provesDynamicMcpLifecycle": False,
        },
        "nonScored": True,
        "countsTowardWeakAcceptance": False,
        "formalRunCounted": False,
        "reportSha256": None,
    }


def reanalyze_pilot(
    prior_report_path: Path,
    raw_report_path: Path,
) -> dict[str, Any]:
    prior_report_path = prior_report_path.resolve()
    raw_report_path = raw_report_path.resolve()
    prior = json.loads(prior_report_path.read_text(encoding="utf-8"))
    raw_bytes = raw_report_path.read_bytes()
    raw = json.loads(raw_bytes.decode("utf-8"))
    if not isinstance(raw.get("messages"), list):
        raise RuntimeError("raw pilot artifact omitted messages")
    thread_id = raw.get("threadId")
    turn_id = raw.get("turnId")
    if (
        not isinstance(thread_id, str)
        or not isinstance(turn_id, str)
        or prior.get("thread", {}).get("threadId") != thread_id
        or prior.get("thread", {}).get("turnId") != turn_id
    ):
        raise RuntimeError("raw pilot thread or turn does not match prior report")
    trial_root = Path(prior["build"]["output"]).resolve()
    normalization = normalize_tdd_app_server_event_stream(
        raw["messages"],
        thread_id=thread_id,
        turn_id=turn_id,
        trial_root=trial_root,
    )
    offline_timeline = evaluate_tdd_timeline(normalization["events"])
    classification = evaluate_pilot(
        thread=prior["thread"],
        exposure=prior["exposure"],
        normalization=normalization,
        offline_timeline=offline_timeline,
        changed=prior["changedFiles"],
        config_stable=prior["globalConfigStable"],
        turn_status="completed",
    )
    result = {
        **prior,
        "status": classification["status"],
        "rawArtifact": {
            "path": raw_report_path.as_posix(),
            "bytes": len(raw_bytes),
            "sha256": hashlib.sha256(raw_bytes).hexdigest(),
            "vendoredIntoRepositoryEvidence": False,
        },
        "normalization": normalization,
        "offlineTimeline": offline_timeline,
        "classification": classification,
        "claimBoundary": {
            **prior["claimBoundary"],
            "provesCurrentHostVersionRawEventCapture": (
                classification["processInstrumentationPilotPassed"]
            ),
            "provesCurrentHostVersionRawEventNormalization": (
                classification["processInstrumentationPilotPassed"]
            ),
            "provesBoundFixtureTddOutcome": (
                classification["agentTddProcessAccepted"]
            ),
        },
        "reanalysis": {
            "sourcePriorReport": prior_report_path.as_posix(),
            "sourcePriorReportSha256": hashlib.sha256(
                prior_report_path.read_bytes()
            ).hexdigest(),
            "sourceRawArtifactSha256Verified": (
                prior.get("rawArtifact", {}).get("sha256")
                == hashlib.sha256(raw_bytes).hexdigest()
            ),
            "agentRerun": False,
            "rawArtifactMutated": False,
            "normalizerScriptSha256": hashlib.sha256(
                Path(__file__).with_name(
                    "normalize_human_ai_collaboration_tdd_app_server_items.py"
                ).read_bytes()
            ).hexdigest(),
        },
        "reportSha256": None,
    }
    if result["reanalysis"]["sourceRawArtifactSha256Verified"] is not True:
        raise RuntimeError("raw pilot artifact hash drifted from prior report")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trial-root", type=Path)
    parser.add_argument("--raw-report", type=Path)
    parser.add_argument("--output-report", type=Path)
    parser.add_argument("--codex-executable")
    parser.add_argument("--timeout-seconds", type=float, default=300.0)
    parser.add_argument("--reanalyze-prior-report", type=Path)
    parser.add_argument("--reanalyze-raw-report", type=Path)
    arguments = parser.parse_args()
    reanalysis_requested = (
        arguments.reanalyze_prior_report is not None
        or arguments.reanalyze_raw_report is not None
    )
    if reanalysis_requested:
        if (
            arguments.reanalyze_prior_report is None
            or arguments.reanalyze_raw_report is None
            or arguments.trial_root is not None
            or arguments.raw_report is not None
        ):
            parser.error(
                "reanalysis requires both reanalysis paths and no live paths"
            )
        report = reanalyze_pilot(
            arguments.reanalyze_prior_report,
            arguments.reanalyze_raw_report,
        )
    else:
        if arguments.trial_root is None or arguments.raw_report is None:
            parser.error("--trial-root and --raw-report are required")
        report = run_pilot(
            arguments.trial_root,
            raw_report=arguments.raw_report,
            codex_executable=arguments.codex_executable,
            timeout_seconds=arguments.timeout_seconds,
        )
    report["reportSha256"] = canonical_sha256(
        {
            key: value
            for key, value in report.items()
            if key != "reportSha256"
        }
    )
    output = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    if arguments.output_report is not None:
        arguments.output_report.parent.mkdir(parents=True, exist_ok=True)
        arguments.output_report.write_text(output + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": report["status"],
                "rawArtifact": report["rawArtifact"],
                "reportSha256": report["reportSha256"],
                "outputReport": (
                    str(arguments.output_report.resolve())
                    if arguments.output_report is not None
                    else None
                ),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
