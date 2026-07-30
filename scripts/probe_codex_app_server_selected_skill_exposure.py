#!/usr/bin/env python3
"""Probe a single selected user Skill without invoking a model turn.

The current first target is the CC Switch-managed ``grill-me`` Skill. The probe
lists the control inventory, constructs a one-off ``skills.config`` array that
disables every other user Skill, verifies the effective selected inventory, and
starts an ephemeral Spark/low read-only thread. It intentionally does not send
``turn/start`` and therefore does not claim loader invocation or Skill value.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
from typing import Any

try:
    from .probe_codex_app_server_skill_exposure import (
        AppServerSession,
        EFFORT,
        MODEL,
        PLUGIN_FEATURES,
        STATIC_MCP_NAMES,
        _git_status_digest,
        _thread_id,
        build_command,
        build_skill_config_override,
        canonical_sha256,
        classify_stderr,
        file_observation,
        initialize,
        inventory_summary,
        request_skills,
        resolve_codex_executable,
    )
except ImportError:  # Direct script execution.
    from probe_codex_app_server_skill_exposure import (
        AppServerSession,
        EFFORT,
        MODEL,
        PLUGIN_FEATURES,
        STATIC_MCP_NAMES,
        _git_status_digest,
        _thread_id,
        build_command,
        build_skill_config_override,
        canonical_sha256,
        classify_stderr,
        file_observation,
        initialize,
        inventory_summary,
        request_skills,
        resolve_codex_executable,
    )


PROBE_ID = "codex-app-server-selected-skill-exposure-v1"
SELECTED_SKILL_NAME = "grill-me"
EXPECTED_SELECTED_PATH = (
    Path.home() / ".cc-switch" / "skills" / SELECTED_SKILL_NAME / "SKILL.md"
)
EXPECTED_SELECTED_SHA256 = (
    "c9df326c4ab635765ea884471d21f4e21d5b0ec85aec43a06c238307841eb4bc"
)


def _normalize(path: str) -> str:
    return path.replace("\\", "/").lower()


def select_exact_skill(
    skills: list[dict[str, Any]],
    *,
    name: str,
    expected_path: Path,
) -> dict[str, Any]:
    target = _normalize(expected_path.as_posix())
    matches = [
        skill
        for skill in skills
        if skill.get("scope") == "user"
        and skill.get("name") == name
        and _normalize(str(skill.get("path", ""))) == target
    ]
    if len(matches) != 1:
        hints = [
            {
                "name": skill.get("name"),
                "path": str(skill.get("path", "")).replace("\\", "/"),
                "scope": skill.get("scope"),
                "enabled": skill.get("enabled"),
            }
            for skill in skills
            if skill.get("name") == name
            or _normalize(str(skill.get("path", ""))) == target
            or Path(str(skill.get("path", ""))).parent.name == name
        ]
        raise RuntimeError(
            "control inventory did not contain one exact selected Skill; "
            f"same-name-or-path hints={json.dumps(hints, sort_keys=True)}"
        )
    return matches[0]


def compare_selected_inventory(
    control: list[dict[str, Any]],
    selected: list[dict[str, Any]],
    *,
    selected_path: str,
) -> dict[str, Any]:
    def keyed(rows: list[dict[str, Any]]) -> dict[tuple[str, str, str], bool]:
        return {
            (
                str(row["name"]),
                _normalize(str(row["path"])),
                str(row["scope"]),
            ): bool(row["enabled"])
            for row in rows
        }

    control_map = keyed(control)
    selected_map = keyed(selected)
    selected_key = next(
        (
            key
            for key in selected_map
            if key[1] == _normalize(selected_path) and key[2] == "user"
        ),
        None,
    )
    enabled_user_keys = [
        key
        for key, enabled in selected_map.items()
        if key[2] == "user" and enabled
    ]
    non_user_keys = [key for key in control_map if key[2] != "user"]
    return {
        "sameIdentitySet": set(control_map) == set(selected_map),
        "controlUserSkillCount": sum(
            key[2] == "user" for key in control_map
        ),
        "selectedEnabledUserSkillCount": len(enabled_user_keys),
        "onlySelectedUserSkillEnabled": (
            selected_key is not None and enabled_user_keys == [selected_key]
        ),
        "allOtherUserSkillsDisabled": all(
            not enabled
            for key, enabled in selected_map.items()
            if key[2] == "user" and key != selected_key
        ),
        "allNonUserStatesPreserved": all(
            selected_map.get(key) == control_map[key] for key in non_user_keys
        ),
    }


def validate_report(
    report: dict[str, Any],
    *,
    expected_name: str = SELECTED_SKILL_NAME,
    expected_path: Path = EXPECTED_SELECTED_PATH,
    expected_sha256: str = EXPECTED_SELECTED_SHA256,
    expected_control_user_skill_count: int = 105,
) -> list[str]:
    failures: list[str] = []
    comparison = report.get("exposureComparison", {})
    if not comparison.get("sameIdentitySet"):
        failures.append("fail-skill-identity-set-drift")
    if (
        comparison.get("controlUserSkillCount")
        != expected_control_user_skill_count
    ):
        failures.append("fail-control-user-skill-count")
    if comparison.get("selectedEnabledUserSkillCount") != 1:
        failures.append("fail-selected-user-skill-count")
    if not comparison.get("onlySelectedUserSkillEnabled"):
        failures.append("fail-selected-user-skill-state")
    if not comparison.get("allOtherUserSkillsDisabled"):
        failures.append("fail-unselected-user-skill-leak")
    if not comparison.get("allNonUserStatesPreserved"):
        failures.append("fail-non-user-skill-state-drift")

    selected = report.get("selectedSkill", {})
    if selected.get("name") != expected_name:
        failures.append("fail-selected-skill-name")
    if _normalize(str(selected.get("path", ""))) != _normalize(
        expected_path.as_posix()
    ):
        failures.append("fail-selected-skill-path")
    if selected.get("sha256") != expected_sha256:
        failures.append("fail-selected-skill-digest")
    if selected.get("prePostStable") is not True:
        failures.append("hard-fail-selected-skill-file-drift")

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

    mutation = report.get("mutationBoundary", {})
    if not mutation.get("configPrePostStable"):
        failures.append("hard-fail-global-config-drift")
    if not mutation.get("repositoryStatusPrePostStable"):
        failures.append("hard-fail-repository-posture-drift")

    claims = report.get("claimBoundary", {})
    expected_false = {
        "provesSkillLoaderInvocation",
        "provesSkillInstructionsReachedModel",
        "provesSkillBehavior",
        "provesSkillNetValueOrSuperiority",
        "provesFiveArmAblationOutcome",
        "provesCrossHostPortability",
        "provesProductionReadiness",
    }
    if any(claims.get(key) is not False for key in expected_false):
        failures.append("hard-fail-claim-boundary")
    return failures


def run_probe(
    cwd: Path,
    *,
    codex_executable: str | None,
    timeout_seconds: float,
    selected_skill_name: str = SELECTED_SKILL_NAME,
    expected_selected_path: Path = EXPECTED_SELECTED_PATH,
    expected_selected_sha256: str = EXPECTED_SELECTED_SHA256,
    expected_control_user_skill_count: int = 105,
    plugin_features_to_disable: tuple[str, ...] = PLUGIN_FEATURES,
) -> dict[str, Any]:
    cwd = cwd.resolve()
    executable = resolve_codex_executable(codex_executable)
    config_path = (Path.home() / ".codex" / "config.toml").resolve()
    config_before = file_observation(config_path)
    repository_before = _git_status_digest(cwd)
    expected_selected_path = expected_selected_path.expanduser().resolve()
    selected_file_before = file_observation(expected_selected_path)

    control_session = AppServerSession(
        build_command(
            executable,
            plugin_features_to_disable=plugin_features_to_disable,
        ),
        cwd,
        timeout_seconds,
    )
    try:
        control_initialize = initialize(control_session)
        control_skills = request_skills(control_session, cwd, request_id=1)
        selected_control = select_exact_skill(
            control_skills,
            name=selected_skill_name,
            expected_path=expected_selected_path,
        )
        control_session.close()
    except BaseException:
        control_session.abort()
        raise

    user_skills = [
        skill for skill in control_skills if skill["scope"] == "user"
    ]
    exposure_override = build_skill_config_override(
        user_skills,
        enabled_paths={str(selected_control["path"])},
    )
    selected_command = build_command(
        executable,
        disable_override=exposure_override,
        plugin_features_to_disable=plugin_features_to_disable,
    )
    selected_session = AppServerSession(
        selected_command,
        cwd,
        timeout_seconds,
    )
    try:
        selected_initialize = initialize(selected_session)
        selected_skills = request_skills(
            selected_session,
            cwd,
            request_id=1,
        )
        selected_session.send(
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
        thread_start = selected_session.wait_for_response(2)
        thread_id = _thread_id(thread_start)
        selected_session.close()
    except BaseException:
        selected_session.abort()
        raise

    config_after = file_observation(config_path)
    repository_after = _git_status_digest(cwd)
    selected_file_after = file_observation(expected_selected_path)
    comparison = compare_selected_inventory(
        control_skills,
        selected_skills,
        selected_path=str(selected_control["path"]),
    )
    selected_effective = select_exact_skill(
        selected_skills,
        name=selected_skill_name,
        expected_path=expected_selected_path,
    )
    report = {
        "schema": 1,
        "id": f"{PROBE_ID}:{selected_skill_name}",
        "status": "pending-validation",
        "host": {
            "controlUserAgent": control_initialize.get("userAgent"),
            "selectedUserAgent": selected_initialize.get("userAgent"),
            "platformFamily": selected_initialize.get("platformFamily"),
            "platformOs": selected_initialize.get("platformOs"),
        },
        "repository": {"path": cwd.as_posix()},
        "controlInventory": inventory_summary(control_skills),
        "selectedInventory": inventory_summary(selected_skills),
        "exposureComparison": comparison,
        "selectedSkill": {
            "name": selected_effective["name"],
            "path": str(selected_effective["path"]).replace("\\", "/"),
            "scope": selected_effective["scope"],
            "enabled": selected_effective["enabled"],
            "bytes": selected_file_after["bytes"],
            "sha256": selected_file_after["sha256"],
            "expectedSha256": expected_selected_sha256,
            "prePostStable": selected_file_before == selected_file_after,
            "preflightMode": "predeclared-candidate-specific-metadata-only",
            "preflightBoundary": "no-task-turn",
        },
        "threadTelemetry": {
            "threadId": thread_id,
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
        },
        "processBoundary": {
            "controlProcessReturnCode": control_session.process.returncode,
            "selectedProcessReturnCode": selected_session.process.returncode,
            "overrideEntryCount": len(user_skills),
            "selectedEnabledEntryCount": 1,
            "selectedCommandLineCharacterCount": len(
                subprocess.list2cmdline(selected_command)
            ),
            "pluginFeaturesDisabled": list(plugin_features_to_disable),
            "localPluginDiscoveryEnabled": (
                "plugins" not in plugin_features_to_disable
            ),
            "staticMcpServersDisabled": list(STATIC_MCP_NAMES),
            "turnStarted": False,
            "modelRequestSent": False,
            "globalConfigWritten": False,
            "applicationRestarted": False,
            "capabilityInstalled": False,
            "mcpToolInvoked": False,
        },
        "stderrClassification": {
            "control": classify_stderr(control_session.stderr_lines),
            "selected": classify_stderr(selected_session.stderr_lines),
        },
        "mutationBoundary": {
            "configPath": config_path.as_posix(),
            "configBefore": config_before,
            "configAfter": config_after,
            "configPrePostStable": config_before == config_after,
            "repositoryStatusBefore": repository_before,
            "repositoryStatusAfter": repository_after,
            "repositoryStatusPrePostStable": (
                repository_before == repository_after
            ),
            "rawConfigRecorded": False,
            "rawRepositoryStatusRecorded": False,
            "rawSkillContentRecorded": False,
        },
        "claimBoundary": {
            "provesCurrentHostSingleSelectedSkillExposure": True,
            "provesExactWeakModelThreadConfiguration": True,
            "provesSkillLoaderInvocation": False,
            "provesSkillInstructionsReachedModel": False,
            "provesSkillBehavior": False,
            "provesSkillNetValueOrSuperiority": False,
            "provesFiveArmAblationOutcome": False,
            "provesCrossHostPortability": False,
            "provesProductionReadiness": False,
        },
    }
    report["validationFailures"] = validate_report(
        report,
        expected_name=selected_skill_name,
        expected_path=expected_selected_path,
        expected_sha256=expected_selected_sha256,
        expected_control_user_skill_count=expected_control_user_skill_count,
    )
    report["status"] = (
        "pass-current-host-selected-skill-exposure-only"
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
    parser.add_argument("--timeout-seconds", type=float, default=45.0)
    parser.add_argument("--selected-skill-name", default=SELECTED_SKILL_NAME)
    parser.add_argument(
        "--selected-skill-path",
        type=Path,
        default=EXPECTED_SELECTED_PATH,
    )
    parser.add_argument(
        "--expected-selected-sha256",
        default=EXPECTED_SELECTED_SHA256,
    )
    parser.add_argument(
        "--expected-control-user-skill-count",
        type=int,
        default=105,
    )
    parser.add_argument(
        "--enable-local-plugin-discovery",
        action="store_true",
        help=(
            "Keep the local plugins feature enabled while remote_plugin, apps, "
            "and plugin_sharing remain disabled."
        ),
    )
    parser.add_argument(
        "--enable-installed-remote-plugin-discovery",
        action="store_true",
        help=(
            "Keep plugins and remote_plugin enabled for an already-installed "
            "curated plugin while apps and plugin_sharing remain disabled."
        ),
    )
    arguments = parser.parse_args()
    report = run_probe(
        arguments.cwd,
        codex_executable=arguments.codex_executable,
        timeout_seconds=arguments.timeout_seconds,
        selected_skill_name=arguments.selected_skill_name,
        expected_selected_path=arguments.selected_skill_path,
        expected_selected_sha256=arguments.expected_selected_sha256,
        expected_control_user_skill_count=(
            arguments.expected_control_user_skill_count
        ),
        plugin_features_to_disable=(
            tuple(
                feature
                for feature in PLUGIN_FEATURES
                if feature not in {"plugins", "remote_plugin"}
            )
            if arguments.enable_installed_remote_plugin_discovery
            else (
                tuple(
                    feature
                    for feature in PLUGIN_FEATURES
                    if feature != "plugins"
                )
                if arguments.enable_local_plugin_discovery
                else PLUGIN_FEATURES
            )
        ),
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if not report["validationFailures"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
