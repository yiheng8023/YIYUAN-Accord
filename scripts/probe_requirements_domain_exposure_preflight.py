#!/usr/bin/env python3
"""Probe requirements/domain disabled and selected exposure without a task turn."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

try:
    from .build_human_ai_collaboration_requirements_domain_trial import (
        ALLOWED_ARMS,
        canonical_sha256,
    )
    from .probe_codex_app_server_skill_exposure import (
        EFFORT,
        MODEL,
        PLUGIN_FEATURES,
        STATIC_MCP_NAMES,
        build_command,
        build_skill_config_override,
        file_observation,
        inventory_summary,
        resolve_codex_executable,
    )
    from .probe_codex_app_server_selected_skill_exposure import (
        select_exact_skill,
    )
    from .probe_codex_app_server_skill_treatment_fidelity import (
        CONFIGURABLE_SCOPES,
    )
    from .probe_maintenance_migration_exposure_preflight import (
        _start_profile,
        compare_profile,
    )
    from .run_human_ai_collaboration_weak_agent_trial import snapshot_tree
except ImportError:
    from build_human_ai_collaboration_requirements_domain_trial import (
        ALLOWED_ARMS,
        canonical_sha256,
    )
    from probe_codex_app_server_skill_exposure import (
        EFFORT,
        MODEL,
        PLUGIN_FEATURES,
        STATIC_MCP_NAMES,
        build_command,
        build_skill_config_override,
        file_observation,
        inventory_summary,
        resolve_codex_executable,
    )
    from probe_codex_app_server_selected_skill_exposure import select_exact_skill
    from probe_codex_app_server_skill_treatment_fidelity import CONFIGURABLE_SCOPES
    from probe_maintenance_migration_exposure_preflight import (
        _start_profile,
        compare_profile,
    )
    from run_human_ai_collaboration_weak_agent_trial import snapshot_tree


PROBE_ID = "requirements-domain-exposure-preflight-2026-07-24"
CANDIDATE_ARM = "SE-REQ-CC-GRILL-WITH-DOCS"
NATIVE_ARM = "SE-REQ-NATIVE-SPARK"
PRIVATE_SENTINELS = (
    "requiredQuestionTopicGroups",
    "negative-hidden-wording-pressure-guard",
    "example-mismatch:",
)


def _prompt_boundary(native_root: Path, candidate_root: Path) -> dict[str, Any]:
    native_task = json.loads((native_root / "TASK.json").read_text(encoding="utf-8"))
    candidate_task = json.loads(
        (candidate_root / "TASK.json").read_text(encoding="utf-8")
    )
    texts = [
        path.read_text(encoding="utf-8", errors="replace")
        for root in (native_root, candidate_root)
        for path in sorted(root.rglob("*"))
        if path.is_file()
    ]
    leaked = [sentinel for sentinel in PRIVATE_SENTINELS if any(sentinel in text for text in texts)]
    return {
        "samePublicTaskPrompt": native_task.get("taskPrompt")
        == candidate_task.get("taskPrompt"),
        "nativeSelectedSkillAbsent": native_task.get("selectedSkill") is None,
        "candidateSelectedSkillName": candidate_task.get("selectedSkill", {}).get(
            "name"
        ),
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
    if candidate.get("name") != "grill-with-docs":
        failures.append("fail-candidate-name")
    if candidate.get("sha256") != ALLOWED_ARMS[CANDIDATE_ARM]["sha256"]:
        failures.append("fail-candidate-digest")
    if candidate.get("prePostStable") is not True:
        failures.append("hard-fail-candidate-file-drift")
    native = report.get("nativeDisabledProfile", {})
    if not (
        native.get("sameIdentitySet") is True
        and native.get("allConfigurableSkillsDisabled") is True
        and native.get("enabledConfigurableSkillCount") == 0
        and native.get("allNonConfigurableStatesPreserved") is True
    ):
        failures.append("fail-native-disabled-profile")
    selected = report.get("selectedProfile", {})
    if not (
        selected.get("sameIdentitySet") is True
        and selected.get("onlyExpectedConfigurableSkillEnabled") is True
        and selected.get("enabledConfigurableSkillCount") == 1
        and selected.get("allNonConfigurableStatesPreserved") is True
    ):
        failures.append("fail-selected-profile")
    for arm in ("native", "selected"):
        thread = report.get("threadProfiles", {}).get(arm, {})
        if not (
            thread.get("model") == MODEL
            and thread.get("reasoningEffort") == EFFORT
            and thread.get("modelProvider") == "openai"
            and thread.get("approvalPolicy") == "never"
            and thread.get("sandbox", {}).get("type") == "readOnly"
            and thread.get("sandbox", {}).get("networkAccess") is False
        ):
            failures.append(f"fail-{arm}-thread-binding")
    prompt = report.get("promptBoundary", {})
    if not (
        prompt.get("samePublicTaskPrompt") is True
        and prompt.get("nativeSelectedSkillAbsent") is True
        and prompt.get("candidateSelectedSkillName") == "grill-with-docs"
        and prompt.get("privateSentinelsPresentInTrialFiles") == []
        and prompt.get("privateOracleFilePresent") is False
    ):
        failures.append("hard-fail-prompt-or-oracle-boundary")
    if not all(report.get("mutationBoundary", {}).values()):
        failures.append("hard-fail-mutation-boundary")
    process = report.get("processBoundary", {})
    if process.get("turnStarted") is not False or process.get("modelRequestSent") is not False:
        failures.append("hard-fail-task-turn-started")
    if any(value is not False for value in report.get("claimBoundary", {}).values()):
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
    definition = ALLOWED_ARMS[CANDIDATE_ARM]
    candidate_path = Path(str(definition["path"])).resolve()
    candidate_before = file_observation(candidate_path)
    config_path = (Path.home() / ".codex" / "config.toml").resolve()
    config_before = file_observation(config_path)
    native_tree_before = snapshot_tree(native_root)
    candidate_tree_before = snapshot_tree(candidate_root)
    executable = resolve_codex_executable(codex_executable)

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
    native_override = build_skill_config_override(configurable, enabled_paths=set())
    selected_override = build_skill_config_override(
        configurable,
        enabled_paths={str(selected_control["path"])},
    )
    native_initialized, native_skills, native_thread, native_stderr = _start_profile(
        build_command(executable, disable_override=native_override),
        native_root,
        timeout_seconds,
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
    candidate_after = file_observation(candidate_path)
    config_after = file_observation(config_path)
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
        "arms": {"native": NATIVE_ARM, "selected": CANDIDATE_ARM},
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
        "nativeDisabledProfile": compare_profile(
            control_skills,
            native_skills,
            selected_path=None,
        ),
        "selectedProfile": compare_profile(
            control_skills,
            selected_skills,
            selected_path=str(selected_control["path"]),
        ),
        "threadProfiles": {
            "native": {
                "model": native_thread.get("model"),
                "reasoningEffort": native_thread.get("reasoningEffort"),
                "modelProvider": native_thread.get("modelProvider"),
                "sandbox": native_thread.get("sandbox"),
                "approvalPolicy": native_thread.get("approvalPolicy"),
            },
            "selected": {
                "model": selected_thread.get("model"),
                "reasoningEffort": selected_thread.get("reasoningEffort"),
                "modelProvider": selected_thread.get("modelProvider"),
                "sandbox": selected_thread.get("sandbox"),
                "approvalPolicy": selected_thread.get("approvalPolicy"),
            },
        },
        "promptBoundary": _prompt_boundary(native_root, candidate_root),
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
            "nativeFixtureFilesStable": native_tree_before == snapshot_tree(native_root),
            "candidateFixtureFilesStable": candidate_tree_before
            == snapshot_tree(candidate_root),
        },
        "claimBoundary": {
            "provesSkillLoaderInvocation": False,
            "provesSkillInstructionsReachedModel": False,
            "provesSkillBehavior": False,
            "provesSkillValueOrCausation": False,
            "provesProductDiscovery": False,
            "provesRequirementsCompleteness": False,
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
        {key: value for key, value in report.items() if key != "reportSha256"}
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--native-root", type=Path, required=True)
    parser.add_argument("--candidate-root", type=Path, required=True)
    parser.add_argument("--codex-executable")
    parser.add_argument("--timeout-seconds", type=float, default=45.0)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    report = run_probe(
        args.native_root,
        args.candidate_root,
        codex_executable=args.codex_executable,
        timeout_seconds=args.timeout_seconds,
    )
    rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    if args.report is not None:
        args.report.write_text(rendered + "\n", encoding="utf-8", newline="\n")
    print(rendered)
    return 0 if not report["validationFailures"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
