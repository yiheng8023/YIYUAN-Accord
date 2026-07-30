#!/usr/bin/env python3
"""Probe disabled/selected migration Skill exposure without a task turn."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

try:
    from .build_human_ai_collaboration_weak_agent_trial import (
        ALLOWED_ARMS,
        canonical_sha256,
    )
    from .probe_codex_app_server_skill_exposure import (
        AppServerSession,
        EFFORT,
        MODEL,
        PLUGIN_FEATURES,
        STATIC_MCP_NAMES,
        _thread_id,
        build_command,
        build_skill_config_override,
        classify_stderr,
        file_observation,
        initialize,
        inventory_summary,
        request_skills,
        resolve_codex_executable,
    )
    from .probe_codex_app_server_selected_skill_exposure import (
        select_exact_skill,
    )
    from .probe_codex_app_server_skill_treatment_fidelity import (
        CONFIGURABLE_SCOPES,
    )
    from .run_human_ai_collaboration_weak_agent_trial import snapshot_tree
except ImportError:
    from build_human_ai_collaboration_weak_agent_trial import (
        ALLOWED_ARMS,
        canonical_sha256,
    )
    from probe_codex_app_server_skill_exposure import (
        AppServerSession,
        EFFORT,
        MODEL,
        PLUGIN_FEATURES,
        STATIC_MCP_NAMES,
        _thread_id,
        build_command,
        build_skill_config_override,
        classify_stderr,
        file_observation,
        initialize,
        inventory_summary,
        request_skills,
        resolve_codex_executable,
    )
    from probe_codex_app_server_selected_skill_exposure import (
        select_exact_skill,
    )
    from probe_codex_app_server_skill_treatment_fidelity import (
        CONFIGURABLE_SCOPES,
    )
    from run_human_ai_collaboration_weak_agent_trial import snapshot_tree


PROBE_ID = "maintenance-migration-exposure-preflight-2026-07-24"
CANDIDATE_ARM = "SE-MAINT-CC-DEPRECATION-MIGRATION"
NATIVE_ARM = "SE-MAINT-NATIVE-SPARK"
PRIVATE_SENTINELS = ("Mira", "Qin", "Archive", '"v0"')


def _normalize(path: str) -> str:
    return path.replace("\\", "/").lower()


def _keyed(rows: list[dict[str, Any]]) -> dict[tuple[str, str, str], bool]:
    return {
        (
            str(row["name"]),
            _normalize(str(row["path"])),
            str(row["scope"]),
        ): bool(row["enabled"])
        for row in rows
    }


def compare_profile(
    control: list[dict[str, Any]],
    effective: list[dict[str, Any]],
    *,
    selected_path: str | None,
) -> dict[str, Any]:
    control_map = _keyed(control)
    effective_map = _keyed(effective)
    selected_key = (
        next(
            (
                key
                for key in effective_map
                if key[1] == _normalize(selected_path or "")
                and key[2] in CONFIGURABLE_SCOPES
            ),
            None,
        )
        if selected_path
        else None
    )
    enabled_configurable = [
        key
        for key, enabled in effective_map.items()
        if key[2] in CONFIGURABLE_SCOPES and enabled
    ]
    non_configurable = [
        key for key in control_map if key[2] not in CONFIGURABLE_SCOPES
    ]
    return {
        "sameIdentitySet": set(control_map) == set(effective_map),
        "controlConfigurableSkillCount": sum(
            key[2] in CONFIGURABLE_SCOPES for key in control_map
        ),
        "enabledConfigurableSkillCount": len(enabled_configurable),
        "allConfigurableSkillsDisabled": not enabled_configurable,
        "onlyExpectedConfigurableSkillEnabled": (
            selected_key is not None
            and enabled_configurable == [selected_key]
        ),
        "allNonConfigurableStatesPreserved": all(
            effective_map.get(key) == control_map[key]
            for key in non_configurable
        ),
    }


def _start_profile(
    command: list[str],
    cwd: Path,
    timeout_seconds: float,
) -> tuple[
    dict[str, Any],
    list[dict[str, Any]],
    dict[str, Any],
    dict[str, Any],
]:
    session = AppServerSession(command, cwd, timeout_seconds)
    try:
        initialized = initialize(session)
        skills = request_skills(session, cwd, request_id=1)
        session.send(
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
        thread = session.wait_for_response(2)
        _thread_id(thread)
        session.close()
    except BaseException:
        session.abort()
        raise
    return (
        initialized,
        skills,
        thread,
        classify_stderr(session.stderr_lines),
    )


def _prompt_boundary(
    native_root: Path,
    candidate_root: Path,
) -> dict[str, Any]:
    native_task = json.loads(
        (native_root / "TASK.json").read_text(encoding="utf-8")
    )
    candidate_task = json.loads(
        (candidate_root / "TASK.json").read_text(encoding="utf-8")
    )
    native_text = "\n".join(
        path.read_text(encoding="utf-8", errors="replace")
        for path in sorted(native_root.rglob("*"))
        if path.is_file()
    )
    candidate_text = "\n".join(
        path.read_text(encoding="utf-8", errors="replace")
        for path in sorted(candidate_root.rglob("*"))
        if path.is_file()
    )
    leaked = [
        sentinel
        for sentinel in PRIVATE_SENTINELS
        if sentinel in native_text or sentinel in candidate_text
    ]
    return {
        "samePublicTaskPrompt": (
            native_task.get("taskPrompt") == candidate_task.get("taskPrompt")
        ),
        "nativeSelectedSkillAbsent": native_task.get("selectedSkill") is None,
        "candidateSelectedSkillName": candidate_task.get(
            "selectedSkill", {}
        ).get("name"),
        "privateSentinelsChecked": list(PRIVATE_SENTINELS),
        "privateSentinelsPresentInTrialFiles": leaked,
        "privateOracleFilePresent": any(
            "oracle" in path.name.lower()
            for root in (native_root, candidate_root)
            for path in root.rglob("*")
            if path.is_file()
        ),
        "publicTaskPromptSha256": hashlib.sha256(
            str(native_task.get("taskPrompt", "")).encode("utf-8")
        ).hexdigest(),
    }


def validate_report(report: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    candidate = report.get("candidate", {})
    if candidate.get("name") != "deprecation-and-migration":
        failures.append("fail-candidate-name")
    if (
        candidate.get("sha256")
        != "52ef07de05726292c0f5e9fe666cc30e6efbe580ed775621e785a49ec80bd4ea"
    ):
        failures.append("fail-candidate-digest")
    if candidate.get("prePostStable") is not True:
        failures.append("hard-fail-candidate-file-drift")

    native = report.get("nativeDisabledProfile", {})
    for key in (
        "sameIdentitySet",
        "allConfigurableSkillsDisabled",
        "allNonConfigurableStatesPreserved",
    ):
        if native.get(key) is not True:
            failures.append(f"fail-native-{key}")
    if native.get("enabledConfigurableSkillCount") != 0:
        failures.append("fail-native-enabled-count")

    selected = report.get("selectedProfile", {})
    for key in (
        "sameIdentitySet",
        "onlyExpectedConfigurableSkillEnabled",
        "allNonConfigurableStatesPreserved",
    ):
        if selected.get(key) is not True:
            failures.append(f"fail-selected-{key}")
    if selected.get("enabledConfigurableSkillCount") != 1:
        failures.append("fail-selected-enabled-count")

    for key in ("native", "selected"):
        thread = report.get("threadProfiles", {}).get(key, {})
        if (
            thread.get("model") != MODEL
            or thread.get("reasoningEffort") != EFFORT
            or thread.get("modelProvider") != "openai"
            or thread.get("approvalPolicy") != "never"
        ):
            failures.append(f"fail-{key}-thread-binding")
        sandbox = thread.get("sandbox")
        if (
            not isinstance(sandbox, dict)
            or sandbox.get("type") != "readOnly"
        ):
            failures.append(f"fail-{key}-sandbox")

    prompt = report.get("promptBoundary", {})
    if (
        prompt.get("samePublicTaskPrompt") is not True
        or prompt.get("nativeSelectedSkillAbsent") is not True
        or prompt.get("candidateSelectedSkillName")
        != "deprecation-and-migration"
        or prompt.get("privateSentinelsPresentInTrialFiles") != []
        or prompt.get("privateOracleFilePresent") is not False
    ):
        failures.append("hard-fail-prompt-or-oracle-boundary")

    mutation = report.get("mutationBoundary", {})
    for key in (
        "globalConfigStable",
        "candidateFileStable",
        "nativeFixtureFilesStable",
        "candidateFixtureFilesStable",
    ):
        if mutation.get(key) is not True:
            failures.append(f"hard-fail-mutation-{key}")
    if report.get("processBoundary", {}).get("turnStarted") is not False:
        failures.append("hard-fail-task-turn-started")
    if report.get("processBoundary", {}).get("modelRequestSent") is not False:
        failures.append("hard-fail-model-request-sent")
    if any(
        value is not False
        for value in report.get("claimBoundary", {}).values()
    ):
        failures.append("hard-fail-claim-boundary")
    return failures


def run_probe(
    native_root: Path,
    candidate_root: Path,
    *,
    codex_executable: str | None,
    timeout_seconds: float,
) -> dict[str, Any]:
    native_root = native_root.resolve()
    candidate_root = candidate_root.resolve()
    executable = resolve_codex_executable(codex_executable)
    definition = ALLOWED_ARMS[CANDIDATE_ARM]
    if not isinstance(definition, dict):
        raise RuntimeError("migration candidate arm definition is missing")
    candidate_path = Path(str(definition["path"])).resolve()
    candidate_before = file_observation(candidate_path)
    config_path = (Path.home() / ".codex" / "config.toml").resolve()
    config_before = file_observation(config_path)
    native_tree_before = snapshot_tree(native_root)
    candidate_tree_before = snapshot_tree(candidate_root)

    control_initialized, control_skills, _, control_stderr = _start_profile(
        build_command(executable),
        native_root,
        timeout_seconds,
    )
    selected_control = select_exact_skill(
        control_skills,
        name=str(definition["name"]),
        expected_path=candidate_path,
    )
    configurable = [
        skill
        for skill in control_skills
        if skill.get("scope") in CONFIGURABLE_SCOPES
    ]
    native_override = build_skill_config_override(
        configurable,
        enabled_paths=set(),
    )
    selected_override = build_skill_config_override(
        configurable,
        enabled_paths={str(selected_control["path"])},
    )
    native_initialized, native_skills, native_thread, native_stderr = (
        _start_profile(
            build_command(executable, disable_override=native_override),
            native_root,
            timeout_seconds,
        )
    )
    (
        selected_initialized,
        selected_skills,
        selected_thread,
        selected_stderr,
    ) = _start_profile(
        build_command(executable, disable_override=selected_override),
        candidate_root,
        timeout_seconds,
    )

    native_comparison = compare_profile(
        control_skills,
        native_skills,
        selected_path=None,
    )
    selected_comparison = compare_profile(
        control_skills,
        selected_skills,
        selected_path=str(selected_control["path"]),
    )
    prompt = _prompt_boundary(native_root, candidate_root)
    config_after = file_observation(config_path)
    candidate_after = file_observation(candidate_path)
    report = {
        "schema": 1,
        "id": PROBE_ID,
        "status": "pending-validation",
        "host": {
            "controlUserAgent": control_initialized.get("userAgent"),
            "nativeUserAgent": native_initialized.get("userAgent"),
            "selectedUserAgent": selected_initialized.get("userAgent"),
            "platformFamily": selected_initialized.get("platformFamily"),
            "platformOs": selected_initialized.get("platformOs"),
        },
        "arms": {
            "native": NATIVE_ARM,
            "selected": CANDIDATE_ARM,
        },
        "candidate": {
            "name": definition["name"],
            "path": candidate_path.as_posix(),
            "bytes": candidate_after["bytes"],
            "sha256": candidate_after["sha256"],
            "expectedSha256": definition["sha256"],
            "prePostStable": candidate_before == candidate_after,
        },
        "controlInventory": inventory_summary(control_skills),
        "nativeDisabledInventory": inventory_summary(native_skills),
        "selectedInventory": inventory_summary(selected_skills),
        "nativeDisabledProfile": native_comparison,
        "selectedProfile": selected_comparison,
        "threadProfiles": {
            "native": {
                "model": native_thread.get("model"),
                "reasoningEffort": native_thread.get("reasoningEffort"),
                "modelProvider": native_thread.get("modelProvider"),
                "sandbox": native_thread.get("sandbox"),
                "approvalPolicy": native_thread.get("approvalPolicy"),
                "ephemeral": True,
                "providerFallbackAllowed": False,
            },
            "selected": {
                "model": selected_thread.get("model"),
                "reasoningEffort": selected_thread.get("reasoningEffort"),
                "modelProvider": selected_thread.get("modelProvider"),
                "sandbox": selected_thread.get("sandbox"),
                "approvalPolicy": selected_thread.get("approvalPolicy"),
                "ephemeral": True,
                "providerFallbackAllowed": False,
            },
        },
        "promptBoundary": prompt,
        "processBoundary": {
            "turnStarted": False,
            "modelRequestSent": False,
            "globalConfigWritten": False,
            "pluginFeaturesDisabled": list(PLUGIN_FEATURES),
            "staticMcpServersDisabled": list(STATIC_MCP_NAMES),
            "capabilityInstalledUpdatedOrRemoved": False,
            "mcpToolInvoked": False,
        },
        "stderrClassification": {
            "control": control_stderr,
            "native": native_stderr,
            "selected": selected_stderr,
        },
        "mutationBoundary": {
            "globalConfigStable": config_before == config_after,
            "candidateFileStable": candidate_before == candidate_after,
            "nativeFixtureFilesStable": (
                native_tree_before == snapshot_tree(native_root)
            ),
            "candidateFixtureFilesStable": (
                candidate_tree_before == snapshot_tree(candidate_root)
            ),
            "rawConfigRecorded": False,
            "rawCandidateContentRecorded": False,
        },
        "claimBoundary": {
            "provesSkillLoaderInvocation": False,
            "provesSkillInstructionsReachedModel": False,
            "provesSkillBehavior": False,
            "provesSkillValueOrCausation": False,
            "provesProductionMigrationReadiness": False,
            "provesRemovalReadiness": False,
            "provesCrossHostPortability": False,
        },
        "validationFailures": [],
        "reportSha256": None,
    }
    report["validationFailures"] = validate_report(report)
    report["status"] = (
        "pass-current-host-exposure-and-prompt-boundary-only"
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
    parser.add_argument("--native-root", type=Path, required=True)
    parser.add_argument("--candidate-root", type=Path, required=True)
    parser.add_argument("--codex-executable")
    parser.add_argument("--timeout-seconds", type=float, default=45.0)
    arguments = parser.parse_args()
    report = run_probe(
        arguments.native_root,
        arguments.candidate_root,
        codex_executable=arguments.codex_executable,
        timeout_seconds=arguments.timeout_seconds,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if not report["validationFailures"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
