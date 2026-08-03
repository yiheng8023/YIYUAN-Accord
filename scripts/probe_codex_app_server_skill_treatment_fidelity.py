#!/usr/bin/env python3
"""Probe body-only Skill treatment delivery with a disposable canary.

The probe never edits an installed Skill or global Codex configuration. Each
paired repetition creates one project-local Skill whose body contains a fresh
opaque token. The token is absent from every public and metadata surface.
Control and selected arms use separate ephemeral app-server threads.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import secrets
from typing import Any

try:
    from scripts.probe_codex_app_server_skill_exposure import (
        AppServerSession,
        EFFORT,
        FORBIDDEN_ITEM_TYPES,
        MODEL,
        _git_status_digest,
        _thread_id,
        _turn_id,
        build_command,
        build_skill_config_override,
        canonical_sha256,
        classify_stderr,
        file_observation,
        initialize,
        request_skills,
        resolve_codex_executable,
        sha256_bytes,
    )
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from probe_codex_app_server_skill_exposure import (
        AppServerSession,
        EFFORT,
        FORBIDDEN_ITEM_TYPES,
        MODEL,
        _git_status_digest,
        _thread_id,
        _turn_id,
        build_command,
        build_skill_config_override,
        canonical_sha256,
        classify_stderr,
        file_observation,
        initialize,
        request_skills,
        resolve_codex_executable,
        sha256_bytes,
    )


ROOT = Path(__file__).resolve().parent.parent
PROTOCOL_PATH = (
    ROOT
    / "registry"
    / "codex-app-server-skill-treatment-fidelity-protocol-2026-07-24.json"
)
PROBE_ID = "codex-app-server-skill-treatment-fidelity-v1"
SKILL_NAME = "treatment-fidelity-canary"
SKILL_DESCRIPTION = (
    "Synthetic local treatment-fidelity canary. Use only when explicitly selected."
)
FALLBACK = "NO_TREATMENT"
PUBLIC_PROMPT = (
    "A treatment may or may not be selected. If it supplies an opaque "
    "verification token, return exactly that token. Otherwise return exactly "
    "NO_TREATMENT. Do not use tools or add any other text."
)
ARM_ORDERS = (
    ("control-unselected", "selected-structured-skill"),
    ("selected-structured-skill", "control-unselected"),
    ("control-unselected", "selected-structured-skill"),
)
CONFIGURABLE_SCOPES = {"user", "repo"}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def render_canary_skill_body(token: str) -> str:
    return (
        "---\n"
        f"name: {SKILL_NAME}\n"
        f"description: {SKILL_DESCRIPTION}\n"
        "---\n\n"
        "# Treatment Fidelity Canary\n\n"
        "For the current task, return exactly this opaque verification token "
        "and nothing else:\n\n"
        f"`{token}`\n\n"
        "Do not call tools, read files, write files, or explain the token.\n"
    )


def build_canary_skill(pair_root: Path, token: str) -> dict[str, Any]:
    """Create one body-only token canary in a new disposable pair root."""

    pair_root = pair_root.resolve()
    if pair_root.exists() and any(pair_root.iterdir()):
        raise RuntimeError("pair root must not already contain files")
    pair_root.mkdir(parents=True, exist_ok=True)
    skill_path = (
        pair_root / ".agents" / "skills" / SKILL_NAME / "SKILL.md"
    )
    skill_path.parent.mkdir(parents=True, exist_ok=True)
    body = render_canary_skill_body(token)
    skill_path.write_text(body, encoding="utf-8", newline="\n")
    public_surfaces = {
        "skillName": SKILL_NAME,
        "description": SKILL_DESCRIPTION,
        "skillPath": skill_path.as_posix(),
        "publicPrompt": PUBLIC_PROMPT,
        "structuredInput": {
            "type": "skill",
            "name": SKILL_NAME,
            "path": skill_path.as_posix(),
        },
    }
    _require(
        token not in json.dumps(public_surfaces, ensure_ascii=False),
        "canary token leaked into a public or metadata surface",
    )
    return {
        "pairRoot": pair_root.as_posix(),
        "skillPath": skill_path.as_posix(),
        "skillBodySha256": sha256_bytes(body.encode("utf-8")),
        "skillBodyBytes": len(body.encode("utf-8")),
        "token": token,
        "tokenSha256": sha256_bytes(token.encode("utf-8")),
        "publicPromptSha256": sha256_bytes(PUBLIC_PROMPT.encode("utf-8")),
        "publicSurfaces": public_surfaces,
    }


def select_canary(
    skills: list[dict[str, Any]],
    *,
    expected_path: Path,
) -> dict[str, Any]:
    target = expected_path.resolve().as_posix().lower()

    def matches_expected_path(raw_path: object) -> bool:
        candidate = Path(str(raw_path))
        try:
            if os.path.samefile(candidate, expected_path):
                return True
        except OSError:
            pass
        return str(raw_path).replace("\\", "/").lower() == target

    matches = [
        row
        for row in skills
        if row.get("name") == SKILL_NAME
        and matches_expected_path(row.get("path", ""))
        and row.get("scope") in CONFIGURABLE_SCOPES
    ]
    if len(matches) != 1:
        hints = [
            {
                "name": row.get("name"),
                "path": str(row.get("path", "")).replace("\\", "/"),
                "scope": row.get("scope"),
                "enabled": row.get("enabled"),
            }
            for row in skills
            if row.get("name") == SKILL_NAME
        ]
        raise RuntimeError(
            "inventory did not contain exactly one project canary; "
            f"hints={json.dumps(hints, sort_keys=True)}"
        )
    return matches[0]


def compare_effective_inventory(
    control_inventory: list[dict[str, Any]],
    effective_inventory: list[dict[str, Any]],
    *,
    canary_path: str,
    selected: bool,
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

    before = keyed(control_inventory)
    after = keyed(effective_inventory)
    target_path = canary_path.replace("\\", "/").lower()
    canary_keys = [
        key
        for key in after
        if key[0] == SKILL_NAME
        and key[1] == target_path
        and key[2] in CONFIGURABLE_SCOPES
    ]
    configurable_enabled = [
        key
        for key, enabled in after.items()
        if key[2] in CONFIGURABLE_SCOPES and enabled
    ]
    expected_enabled = canary_keys if selected else []
    non_configurable = [
        key for key in before if key[2] not in CONFIGURABLE_SCOPES
    ]
    return {
        "sameIdentitySet": set(before) == set(after),
        "canaryIdentityCount": len(canary_keys),
        "enabledConfigurableSkillCount": len(configurable_enabled),
        "expectedOnlyCanaryEnabled": configurable_enabled == expected_enabled,
        "allNonConfigurableStatesPreserved": all(
            after.get(key) == before[key] for key in non_configurable
        ),
    }


def _collect_turn(
    session: AppServerSession,
    *,
    thread_id: str,
    input_items: list[dict[str, Any]],
) -> dict[str, Any]:
    session.send(
        {
            "id": 3,
            "method": "turn/start",
            "params": {
                "threadId": thread_id,
                "model": MODEL,
                "effort": EFFORT,
                "input": input_items,
            },
        }
    )
    turn_start = session.wait_for_response(3)
    turn_id = _turn_id(turn_start)
    items: list[dict[str, Any]] = []
    completed_turn: dict[str, Any] | None = None
    while True:
        message = session._next()
        if message.get("method") == "item/completed":
            params = message.get("params")
            if (
                isinstance(params, dict)
                and params.get("threadId") == thread_id
                and params.get("turnId") == turn_id
                and isinstance(params.get("item"), dict)
            ):
                items.append(params["item"])
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
    agent_messages = [
        str(item["text"])
        for item in items
        if item.get("type") == "agentMessage"
        and isinstance(item.get("text"), str)
    ]
    item_types = [
        str(item["type"])
        for item in items
        if isinstance(item.get("type"), str)
    ]
    return {
        "turnId": turn_id,
        "turnStatus": completed_turn.get("status"),
        "itemTypes": item_types,
        "agentMessages": agent_messages,
        "agentMessageSha256": canonical_sha256(agent_messages),
        "forbiddenItemTypesObserved": sorted(
            set(item_types) & FORBIDDEN_ITEM_TYPES
        ),
    }


def run_arm(
    *,
    executable: str,
    pair_root: Path,
    control_inventory: list[dict[str, Any]],
    canary: dict[str, Any],
    arm: str,
    timeout_seconds: float,
) -> dict[str, Any]:
    selected = arm == "selected-structured-skill"
    _require(
        selected or arm == "control-unselected",
        f"unknown treatment-fidelity arm: {arm}",
    )
    configurable = [
        row
        for row in control_inventory
        if row.get("scope") in CONFIGURABLE_SCOPES
    ]
    enabled_paths = {canary["skillPath"]} if selected else set()
    override = build_skill_config_override(
        configurable,
        enabled_paths=enabled_paths,
    )
    _require(
        canary["token"] not in override,
        "canary token leaked into process-scoped config",
    )
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    session = AppServerSession(
        build_command(executable, disable_override=override),
        pair_root,
        timeout_seconds,
        environment=environment,
    )
    try:
        initialize_result = initialize(session, experimental_api=True)
        effective_inventory = request_skills(
            session,
            pair_root,
            request_id=1,
        )
        inventory = compare_effective_inventory(
            control_inventory,
            effective_inventory,
            canary_path=canary["skillPath"],
            selected=selected,
        )
        session.send(
            {
                "id": 2,
                "method": "thread/start",
                "params": {
                    "model": MODEL,
                    "allowProviderModelFallback": False,
                    "cwd": str(pair_root),
                    "approvalPolicy": "never",
                    "sandbox": "read-only",
                    "ephemeral": True,
                    "runtimeWorkspaceRoots": [str(pair_root)],
                },
            }
        )
        thread_start = session.wait_for_response(2)
        thread_id = _thread_id(thread_start)
        input_items: list[dict[str, Any]] = []
        if selected:
            input_items.append(
                {
                    "type": "skill",
                    "name": SKILL_NAME,
                    "path": canary["skillPath"],
                }
            )
        input_items.append({"type": "text", "text": PUBLIC_PROMPT})
        _require(
            canary["token"]
            not in json.dumps(input_items, ensure_ascii=False),
            "canary token leaked into turn input",
        )
        turn = _collect_turn(
            session,
            thread_id=thread_id,
            input_items=input_items,
        )
        session.close()
    except BaseException:
        session.abort()
        raise

    expected = canary["token"] if selected else FALLBACK
    exact_response = turn["agentMessages"] == [expected]
    return {
        "arm": arm,
        "structuredSkillInputSent": selected,
        "expectedResponseClass": (
            "body-only-token" if selected else "public-fallback"
        ),
        "exactResponseMatched": exact_response,
        "thread": {
            "threadId": thread_id,
            "turnId": turn["turnId"],
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
        "inventory": inventory,
        "turn": {
            key: value
            for key, value in turn.items()
            if key != "agentMessages"
        },
        "host": {
            "userAgent": initialize_result.get("userAgent"),
        },
        "stderr": classify_stderr(session.stderr_lines),
    }


def classify_report(report: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    repetitions = report.get("repetitions", [])
    if len(repetitions) != 3:
        failures.append("fail-three-paired-repetitions")
    thread_ids: set[str] = set()
    tokens: set[str] = set()
    for repetition in repetitions:
        token = repetition.get("privateOracleRevealedAfterRun", {}).get("token")
        if not isinstance(token, str) or token in tokens:
            failures.append("fail-distinct-token")
        else:
            tokens.add(token)
        if repetition.get("tokenAbsentFromPublicSurfaces") is not True:
            failures.append("fail-token-public-surface-leak")
        arms = repetition.get("arms", [])
        if [arm.get("arm") for arm in arms] != repetition.get("armOrder"):
            failures.append("fail-arm-order")
        for arm in arms:
            thread = arm.get("thread", {})
            thread_id = thread.get("threadId")
            if not isinstance(thread_id, str) or thread_id in thread_ids:
                failures.append("fail-distinct-thread")
            else:
                thread_ids.add(thread_id)
            if (
                thread.get("model") != MODEL
                or thread.get("reasoningEffort") != EFFORT
                or thread.get("approvalPolicy") != "never"
                or thread.get("providerFallbackAllowed") is not False
            ):
                failures.append("fail-host-route-drift")
            inventory = arm.get("inventory", {})
            if (
                inventory.get("sameIdentitySet") is not True
                or inventory.get("canaryIdentityCount") != 1
                or inventory.get("expectedOnlyCanaryEnabled") is not True
                or inventory.get("allNonConfigurableStatesPreserved") is not True
            ):
                failures.append("fail-inventory-isolation")
            if arm.get("exactResponseMatched") is not True:
                failures.append("fail-exact-response")
            if arm.get("turn", {}).get("forbiddenItemTypesObserved") != []:
                failures.append("fail-forbidden-item")
    if len(thread_ids) != 6:
        failures.append("fail-six-distinct-threads")
    if report.get("globalConfigStable") is not True:
        failures.append("fail-global-config-drift")
    if report.get("repositoryStatusStable") is not True:
        failures.append("fail-repository-status-drift")
    if report.get("allCanaryBodiesStable") is not True:
        failures.append("fail-canary-body-drift")
    return sorted(set(failures))


def run_preflight(
    output_root: Path,
    *,
    codex_executable: str | None,
    timeout_seconds: float,
) -> dict[str, Any]:
    """Verify canary discovery and process-scoped isolation without a turn."""

    output_root = output_root.resolve()
    if output_root.exists() and any(output_root.iterdir()):
        raise RuntimeError("output root must not already contain files")
    output_root.mkdir(parents=True, exist_ok=True)
    executable = resolve_codex_executable(codex_executable)
    config_path = (Path.home() / ".codex" / "config.toml").resolve()
    config_before = file_observation(config_path)
    repository_before = _git_status_digest(ROOT)
    token = f"AAH_BODY_ONLY_{secrets.token_hex(16).upper()}"
    canary = build_canary_skill(output_root / "preflight", token)
    pair_root = Path(canary["pairRoot"])
    skill_path = Path(canary["skillPath"])
    body_before = file_observation(skill_path)
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"

    control_session = AppServerSession(
        build_command(executable),
        pair_root,
        timeout_seconds,
        environment=environment,
    )
    try:
        control_initialize = initialize(
            control_session,
            experimental_api=True,
        )
        control_inventory = request_skills(
            control_session,
            pair_root,
            request_id=1,
        )
        canary_row = select_canary(
            control_inventory,
            expected_path=skill_path,
        )
        control_session.close()
    except BaseException:
        control_session.abort()
        raise

    configurable = [
        row
        for row in control_inventory
        if row.get("scope") in CONFIGURABLE_SCOPES
    ]
    arm_reports: list[dict[str, Any]] = []
    for arm, enabled_paths in (
        ("control-unselected", set()),
        ("selected-structured-skill", {canary["skillPath"]}),
    ):
        override = build_skill_config_override(
            configurable,
            enabled_paths=enabled_paths,
        )
        _require(
            token not in override,
            "canary token leaked into process-scoped config",
        )
        session = AppServerSession(
            build_command(executable, disable_override=override),
            pair_root,
            timeout_seconds,
            environment=environment,
        )
        try:
            initialize_result = initialize(session, experimental_api=True)
            effective_inventory = request_skills(
                session,
                pair_root,
                request_id=1,
            )
            comparison = compare_effective_inventory(
                control_inventory,
                effective_inventory,
                canary_path=canary["skillPath"],
                selected=arm == "selected-structured-skill",
            )
            session.close()
        except BaseException:
            session.abort()
            raise
        arm_reports.append(
            {
                "arm": arm,
                "inventory": comparison,
                "host": {
                    "controlUserAgent": control_initialize.get("userAgent"),
                    "effectiveUserAgent": initialize_result.get("userAgent"),
                },
                "threadStarted": False,
                "turnStarted": False,
            }
        )

    config_after = file_observation(config_path)
    repository_after = _git_status_digest(ROOT)
    body_after = file_observation(skill_path)
    failures: list[str] = []
    for arm in arm_reports:
        inventory = arm["inventory"]
        if (
            inventory.get("sameIdentitySet") is not True
            or inventory.get("canaryIdentityCount") != 1
            or inventory.get("expectedOnlyCanaryEnabled") is not True
            or inventory.get("allNonConfigurableStatesPreserved") is not True
        ):
            failures.append(f"fail-inventory-isolation:{arm['arm']}")
    if config_before != config_after:
        failures.append("fail-global-config-drift")
    if repository_before != repository_after:
        failures.append("fail-repository-status-drift")
    if body_before != body_after:
        failures.append("fail-canary-body-drift")
    report = {
        "schema": 1,
        "id": f"{PROBE_ID}:preflight",
        "status": (
            "preflight-pass-no-turn"
            if not failures
            else "preflight-fail-no-turn"
        ),
        "protocol": PROTOCOL_PATH.relative_to(ROOT).as_posix(),
        "outputRoot": output_root.as_posix(),
        "canary": {
            "skillPath": canary["skillPath"],
            "skillBodySha256": canary["skillBodySha256"],
            "tokenSha256": canary["tokenSha256"],
            "inventoryScope": canary_row["scope"],
            "bodyStable": body_before == body_after,
        },
        "tokenAbsentFromPublicSurfaces": token not in json.dumps(
            canary["publicSurfaces"],
            ensure_ascii=False,
            sort_keys=True,
        ),
        "arms": arm_reports,
        "globalConfigStable": config_before == config_after,
        "repositoryStatusStable": repository_before == repository_after,
        "threadOrTurnStarted": False,
        "failureCodes": failures,
        "claimBoundary": {
            "provesCanaryInventoryAndProcessScopedIsolation": not failures,
            "provesBodyOnlyContentReachedModel": False,
            "provesLoaderInvocation": False,
            "provesInstalledCandidateDelivery": False,
        },
    }
    return report


def run_probe(
    output_root: Path,
    *,
    codex_executable: str | None,
    timeout_seconds: float,
) -> dict[str, Any]:
    output_root = output_root.resolve()
    if output_root.exists() and any(output_root.iterdir()):
        raise RuntimeError("output root must not already contain files")
    output_root.mkdir(parents=True, exist_ok=True)
    executable = resolve_codex_executable(codex_executable)
    config_path = (Path.home() / ".codex" / "config.toml").resolve()
    config_before = file_observation(config_path)
    repository_before = _git_status_digest(ROOT)
    repetitions: list[dict[str, Any]] = []

    for index, arm_order in enumerate(ARM_ORDERS, start=1):
        pair_root = output_root / f"pair-{index}"
        token = f"AAH_BODY_ONLY_{secrets.token_hex(16).upper()}"
        canary = build_canary_skill(pair_root, token)
        skill_path = Path(canary["skillPath"])
        body_before = file_observation(skill_path)

        environment = os.environ.copy()
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        control_session = AppServerSession(
            build_command(executable),
            pair_root,
            min(timeout_seconds, 60.0),
            environment=environment,
        )
        try:
            initialize(control_session, experimental_api=True)
            control_inventory = request_skills(
                control_session,
                pair_root,
                request_id=1,
            )
            canary_row = select_canary(
                control_inventory,
                expected_path=skill_path,
            )
            control_session.close()
        except BaseException:
            control_session.abort()
            raise

        arms = [
            run_arm(
                executable=executable,
                pair_root=pair_root,
                control_inventory=control_inventory,
                canary=canary,
                arm=arm,
                timeout_seconds=timeout_seconds,
            )
            for arm in arm_order
        ]
        body_after = file_observation(skill_path)
        public_blob = json.dumps(
            canary["publicSurfaces"],
            ensure_ascii=False,
            sort_keys=True,
        )
        repetitions.append(
            {
                "pairId": f"pair-{index}",
                "armOrder": list(arm_order),
                "canary": {
                    "skillPath": canary["skillPath"],
                    "skillBodySha256": canary["skillBodySha256"],
                    "skillBodyBytes": canary["skillBodyBytes"],
                    "tokenSha256": canary["tokenSha256"],
                    "publicPromptSha256": canary["publicPromptSha256"],
                    "inventoryScope": canary_row["scope"],
                    "bodyStableAcrossPair": body_before == body_after,
                },
                "tokenAbsentFromPublicSurfaces": token not in public_blob,
                "arms": arms,
                "privateOracleRevealedAfterRun": {
                    "token": token,
                    "tokenSha256": canary["tokenSha256"],
                },
            }
        )

    config_after = file_observation(config_path)
    repository_after = _git_status_digest(ROOT)
    report: dict[str, Any] = {
        "schema": 1,
        "id": PROBE_ID,
        "status": "pending-classification",
        "protocol": PROTOCOL_PATH.relative_to(ROOT).as_posix(),
        "outputRoot": output_root.as_posix(),
        "model": MODEL,
        "reasoningEffort": EFFORT,
        "repetitions": repetitions,
        "globalConfigStable": config_before == config_after,
        "repositoryStatusStable": repository_before == repository_after,
        "allCanaryBodiesStable": all(
            pair["canary"]["bodyStableAcrossPair"]
            for pair in repetitions
        ),
        "claimBoundary": {
            "provesBodyOnlyContentReachedModelForSyntheticCanaryOnBoundHost": False,
            "provesIndependentLoaderEvent": False,
            "provesInstalledDiagnoseBodyDelivery": False,
            "provesInstalledDiagnoseCausation": False,
            "provesCurrentMattValue": False,
            "provesSkillSuperiority": False,
            "provesPortfolioDecisionReadiness": False,
            "provesCrossHostBehavior": False,
        },
    }
    failures = classify_report(report)
    report["failureCodes"] = failures
    if not failures:
        report["status"] = (
            "synthetic-body-only-delivery-assay-pass-"
            "independent-loader-event-absent"
        )
        report["claimBoundary"][
            "provesBodyOnlyContentReachedModelForSyntheticCanaryOnBoundHost"
        ] = True
    else:
        report["status"] = "synthetic-body-only-delivery-assay-fail"
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--codex-executable")
    parser.add_argument("--timeout-seconds", type=float, default=120.0)
    parser.add_argument("--output-report", type=Path)
    parser.add_argument("--preflight-only", action="store_true")
    arguments = parser.parse_args()
    if arguments.preflight_only:
        report = run_preflight(
            arguments.output_root,
            codex_executable=arguments.codex_executable,
            timeout_seconds=arguments.timeout_seconds,
        )
    else:
        report = run_probe(
            arguments.output_root,
            codex_executable=arguments.codex_executable,
            timeout_seconds=arguments.timeout_seconds,
        )
    report["reportSha256"] = canonical_sha256(
        {key: value for key, value in report.items() if key != "reportSha256"}
    )
    output = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    if arguments.output_report is not None:
        if arguments.output_report.exists():
            raise RuntimeError("output report already exists")
        arguments.output_report.write_text(
            output + "\n",
            encoding="utf-8",
            newline="\n",
        )
    print(
        json.dumps(
            {
                "status": report["status"],
                "failureCodes": report["failureCodes"],
                "reportSha256": report["reportSha256"],
                "outputReport": (
                    str(arguments.output_report.resolve())
                    if arguments.output_report is not None
                    else None
                ),
            },
            sort_keys=True,
        )
    )
    return 0 if not report["failureCodes"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
