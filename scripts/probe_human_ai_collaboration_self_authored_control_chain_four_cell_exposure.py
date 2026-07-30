#!/usr/bin/env python3
"""Run a no-turn four-cell exposure preflight for the exact current chain."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import tempfile
from typing import Any

try:
    from scripts.build_human_ai_collaboration_self_authored_control_chain_projection import (
        MANIFEST_NAME,
        materialize_current_chain,
    )
    from scripts.probe_codex_app_server_skill_exposure import (
        AppServerSession,
        build_command,
        build_skill_config_override,
        canonical_sha256,
        file_observation,
        initialize,
        inventory_summary,
        request_skills,
        resolve_codex_executable,
    )
    from scripts.probe_codex_app_server_skill_treatment_fidelity import (
        CONFIGURABLE_SCOPES,
        _git_status_digest,
    )
    from scripts.probe_human_ai_collaboration_semantic_authority_composition_exposure import (
        compare_inventory,
        select_projected_skills,
    )
    from scripts.probe_human_ai_collaboration_self_authored_control_chain_hook_modes import (
        AUDIT_PATH,
        SCENARIO_FIXTURE_PATH,
        _run_handler,
    )
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from build_human_ai_collaboration_self_authored_control_chain_projection import (
        MANIFEST_NAME,
        materialize_current_chain,
    )
    from probe_codex_app_server_skill_exposure import (
        AppServerSession,
        build_command,
        build_skill_config_override,
        canonical_sha256,
        file_observation,
        initialize,
        inventory_summary,
        request_skills,
        resolve_codex_executable,
    )
    from probe_codex_app_server_skill_treatment_fidelity import (
        CONFIGURABLE_SCOPES,
        _git_status_digest,
    )
    from probe_human_ai_collaboration_semantic_authority_composition_exposure import (
        compare_inventory,
        select_projected_skills,
    )
    from probe_human_ai_collaboration_self_authored_control_chain_hook_modes import (
        AUDIT_PATH,
        SCENARIO_FIXTURE_PATH,
        _run_handler,
    )


ROOT = Path(__file__).resolve().parent.parent
PROBE_ID = "self-authored-control-chain-four-cell-exposure-v1"
CELL_FACTORS = {
    "CHAIN-HARD-HOOK-OFF": ("hard-only", "off"),
    "CHAIN-HARD-HOOK-AUTO": ("hard-only", "auto"),
    "CHAIN-EXACT-HOOK-OFF": ("exact-current-three-skill-chain", "off"),
    "CHAIN-EXACT-HOOK-AUTO": ("exact-current-three-skill-chain", "auto"),
}


def _isolated_strict_command(command: list[str]) -> list[str]:
    result: list[str] = []
    index = 0
    while index < len(command):
        if (
            command[index] == "-c"
            and index + 1 < len(command)
            and command[index + 1].startswith("mcp_servers.")
            and command[index + 1].endswith(".enabled=false")
        ):
            index += 2
            continue
        result.append(command[index])
        index += 1
    if "--strict-config" in result:
        return result
    try:
        position = result.index("--stdio") + 1
    except ValueError as error:
        raise RuntimeError("app-server command omitted --stdio") from error
    result.insert(position, "--strict-config")
    return result


def load_manifest(projection_root: Path) -> dict[str, Any]:
    document = json.loads(
        (projection_root / MANIFEST_NAME).read_text(encoding="utf-8")
    )
    body = dict(document)
    digest = body.pop("manifestSha256", None)
    if digest != canonical_sha256(body):
        raise RuntimeError("control-chain projection manifest digest drifted")
    return document


def _route_prompt() -> bytes:
    fixture = json.loads(SCENARIO_FIXTURE_PATH.read_text(encoding="utf-8"))
    route = next(
        row
        for row in fixture["fixtures"]
        if row.get("scenarioId") == "ROUTE-MIN-01"
        and row.get("arm") == "hard-only"
    )
    prompt = json.dumps(
        route["input"],
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return json.dumps(
        {"prompt": prompt},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def validate_report(report: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    if (
        report.get("schema") != 1
        or report.get("probeId") != PROBE_ID
        or report.get("status") != "preflight-pass-no-turn"
    ):
        failures.append("fail-identity")
    for key in ("threadStarted", "turnStarted", "modelRequestSent"):
        if report.get(key) is not False:
            failures.append(f"hard-fail-{key}")
    if report.get("projection", {}).get("requiredFileCount") != 5:
        failures.append("fail-dependency-complete-projection")
    if report.get("projection", {}).get("requiredSkillCount") != 3:
        failures.append("fail-skill-count")
    cells = {
        row.get("cellId"): row
        for row in report.get("cells", [])
        if isinstance(row, dict)
    }
    if set(cells) != set(CELL_FACTORS) or len(cells) != 4:
        failures.append("fail-cell-coverage")
    for cell_id, (chain, hook_mode) in CELL_FACTORS.items():
        row = cells.get(cell_id, {})
        if (
            row.get("chainFactor") != chain
            or row.get("hookFactor") != hook_mode
        ):
            failures.append(f"fail-cell-factor:{cell_id}")
            continue
        inventory = row.get("inventory", {})
        expected_count = 0 if chain == "hard-only" else 3
        if inventory.get("enabledConfigurableSkillCount") != expected_count:
            failures.append(f"fail-enabled-count:{cell_id}")
        for key in (
            "sameIdentitySet",
            "onlyExpectedConfigurableSkillsEnabled",
            "allNonConfigurableStatesPreserved",
        ):
            if inventory.get(key) is not True:
                failures.append(f"fail-inventory:{cell_id}:{key}")
        hook = row.get("hookDirectEvidence", {})
        if hook.get("returnCode") != 0 or hook.get("stderrBytes") != 0:
            failures.append(f"fail-hook-process:{cell_id}")
        if hook_mode == "off" and hook.get("stdoutBytes") != 0:
            failures.append(f"fail-hook-off-output:{cell_id}")
        if hook_mode == "auto" and hook.get("stdoutBytes") != 428:
            failures.append(f"fail-hook-auto-output:{cell_id}")
    stability = report.get("stability", {})
    for key in (
        "projectionTreeStable",
        "globalConfigStable",
        "liveHookRegistrationStable",
        "repositoryStatusStableDuringProbe",
        "projectionRemovedAfterEvidenceCapture",
        "isolatedCodexHomeRemovedAfterEvidenceCapture",
    ):
        if stability.get(key) is not True:
            failures.append(f"fail-stability:{key}")
    decision = report.get("decision", {})
    if decision.get("dependencyCompleteFourCellExposureProved") is not True:
        failures.append("fail-exposure-decision")
    for key in (
        "loaderInvocationProved",
        "skillInstructionsReachedModelProved",
        "hookHostConsumptionProved",
        "behavioralCausationProved",
        "hookNetValueProved",
        "selfAuthoredChainValueProved",
        "weakModelRunAuthorized",
        "programCloseoutSupported",
    ):
        if decision.get(key) is not False:
            failures.append(f"hard-fail-claim-promotion:{key}")
    return list(dict.fromkeys(failures))


def run_preflight(
    projection_root: Path,
    *,
    isolated_codex_home: Path,
    codex_executable: str | None,
    timeout_seconds: float,
) -> dict[str, Any]:
    projection_root = projection_root.resolve()
    manifest = load_manifest(projection_root)
    skill_paths = {
        name: Path(path).resolve().as_posix()
        for name, path in manifest["skillPaths"].items()
    }
    projection_before = {
        row["path"]: file_observation(projection_root / row["path"])
        for row in manifest["projectedFiles"]
    }
    config_path = (Path.home() / ".codex" / "config.toml").resolve()
    config_before = file_observation(config_path)
    audit = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
    hook_registration = Path(audit["hookObservation"]["registrationPath"])
    hook_before = file_observation(hook_registration)
    repository_before = _git_status_digest(ROOT)
    executable = resolve_codex_executable(codex_executable)
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["CODEX_HOME"] = str(isolated_codex_home.resolve())

    control = AppServerSession(
        _isolated_strict_command(
            build_command(executable, disable_override="skills.config=[]")
        ),
        projection_root,
        timeout_seconds,
        environment=environment,
    )
    try:
        control_initialize = initialize(control, experimental_api=True)
        control_inventory = request_skills(control, projection_root, request_id=1)
        projected = select_projected_skills(control_inventory, skill_paths)
        control.close()
    except BaseException as error:
        control.abort()
        detail = " | ".join(control.stderr_lines[-20:])
        raise RuntimeError(
            f"control app-server preflight failed; stderr={detail or '<empty>'}"
        ) from error

    configurable = [
        row for row in control_inventory if row.get("scope") in CONFIGURABLE_SCOPES
    ]
    projected_paths = {str(row["path"]) for row in projected.values()}
    route_payload = _route_prompt()
    handler_path = Path(audit["hookObservation"]["handlerPath"])
    cells: list[dict[str, Any]] = []
    for cell_id, (chain, hook_mode) in CELL_FACTORS.items():
        enabled_paths = (
            set() if chain == "hard-only" else projected_paths
        )
        override = build_skill_config_override(
            configurable,
            enabled_paths=enabled_paths,
        )
        cell_environment = environment.copy()
        cell_environment["CAPABILITY_ROUTER_HOOK_MODE"] = hook_mode
        session = AppServerSession(
            _isolated_strict_command(
                build_command(executable, disable_override=override)
            ),
            projection_root,
            timeout_seconds,
            environment=cell_environment,
        )
        try:
            initialized = initialize(session, experimental_api=True)
            inventory = request_skills(session, projection_root, request_id=1)
            comparison = compare_inventory(
                control_inventory,
                inventory,
                expected_enabled_paths=enabled_paths,
            )
            session.close()
        except BaseException as error:
            session.abort()
            detail = " | ".join(session.stderr_lines[-20:])
            raise RuntimeError(
                f"cell app-server preflight failed: {cell_id}; "
                f"stderr={detail or '<empty>'}"
            ) from error
        hook_result = _run_handler(
            handler_path,
            stdin_bytes=route_payload,
            mode=hook_mode,
        )
        cells.append(
            {
                "cellId": cell_id,
                "chainFactor": chain,
                "hookFactor": hook_mode,
                "inventory": comparison,
                "effectiveInventory": inventory_summary(inventory),
                "hookDirectEvidence": hook_result,
                "host": {
                    "userAgent": initialized.get("userAgent"),
                    "platformFamily": initialized.get("platformFamily"),
                    "platformOs": initialized.get("platformOs"),
                },
            }
        )

    projection_after = {
        row["path"]: file_observation(projection_root / row["path"])
        for row in manifest["projectedFiles"]
    }
    report = {
        "schema": 1,
        "probeId": PROBE_ID,
        "status": "preflight-pass-no-turn",
        "protocol": manifest["protocol"],
        "projectionManifestSha256": manifest["manifestSha256"],
        "projection": {
            "requiredFileCount": manifest["requiredFileCount"],
            "requiredSkillCount": len(projected),
            "requiredSkillNames": sorted(projected),
            "projectedTreeSha256": manifest["projectedTreeSha256"],
            "projectedFiles": manifest["projectedFiles"],
            "exactSkillPathSha256": {
                name: file_observation(Path(row["path"]))["sha256"]
                for name, row in sorted(projected.items())
            },
        },
        "host": {
            "userAgent": control_initialize.get("userAgent"),
            "platformFamily": control_initialize.get("platformFamily"),
            "platformOs": control_initialize.get("platformOs"),
            "isolatedCodexHome": isolated_codex_home.resolve().as_posix(),
        },
        "controlInventory": inventory_summary(control_inventory),
        "cells": cells,
        "threadStarted": False,
        "turnStarted": False,
        "modelRequestSent": False,
        "stability": {
            "projectionTreeStable": projection_before == projection_after,
            "globalConfigStable": config_before == file_observation(config_path),
            "liveHookRegistrationStable": hook_before
            == file_observation(hook_registration),
            "repositoryStatusStableDuringProbe": repository_before
            == _git_status_digest(ROOT),
            "projectionRemovedAfterEvidenceCapture": False,
            "isolatedCodexHomeRemovedAfterEvidenceCapture": False,
        },
        "decision": {
            "dependencyCompleteFourCellExposureProved": False,
            "loaderInvocationProved": False,
            "skillInstructionsReachedModelProved": False,
            "hookHostConsumptionProved": False,
            "behavioralCausationProved": False,
            "hookNetValueProved": False,
            "selfAuthoredChainValueProved": False,
            "weakModelRunAuthorized": False,
            "programCloseoutSupported": False,
        },
        "claimBoundary": (
            "This no-turn preflight proves only dependency-complete isolated "
            "Skill inventory exposure for four process-scoped cells plus direct "
            "Hook-mode evidence. It does not prove loader invocation, host Hook "
            "consumption, instruction delivery, behavioral causation, value, "
            "stable latency, cross-host behavior, or weak-Agent acceptance."
        ),
    }
    report["decision"]["dependencyCompleteFourCellExposureProved"] = (
        report["projection"]["requiredFileCount"] == 5
        and report["projection"]["requiredSkillCount"] == 3
        and all(
            row["inventory"]["enabledConfigurableSkillCount"]
            == (
                0
                if row["chainFactor"] == "hard-only"
                else 3
            )
            and row["inventory"]["sameIdentitySet"]
            and row["inventory"]["onlyExpectedConfigurableSkillsEnabled"]
            and row["inventory"]["allNonConfigurableStatesPreserved"]
            for row in cells
        )
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--codex-executable")
    parser.add_argument("--timeout-seconds", type=float, default=60.0)
    parser.add_argument("--output-report", type=Path, required=True)
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()
    output = args.output_report.resolve()
    if output.exists():
        raise RuntimeError("four-cell exposure report already exists")

    projection_path: Path | None = None
    isolated_codex_home: Path | None = None
    with tempfile.TemporaryDirectory(
        prefix="aah-control-chain-four-cell-"
    ) as temporary:
        projection_path = Path(temporary) / "projection"
        isolated_codex_home = Path(temporary) / "codex-home"
        isolated_codex_home.mkdir()
        materialize_current_chain(projection_path)
        report = run_preflight(
            projection_path,
            isolated_codex_home=isolated_codex_home,
            codex_executable=args.codex_executable,
            timeout_seconds=args.timeout_seconds,
        )
    report["stability"]["projectionRemovedAfterEvidenceCapture"] = (
        projection_path is not None and not projection_path.exists()
    )
    report["stability"]["isolatedCodexHomeRemovedAfterEvidenceCapture"] = (
        isolated_codex_home is not None and not isolated_codex_home.exists()
    )
    report["decision"]["dependencyCompleteFourCellExposureProved"] = (
        report["decision"]["dependencyCompleteFourCellExposureProved"]
        and report["stability"]["projectionRemovedAfterEvidenceCapture"]
        and report["stability"]["isolatedCodexHomeRemovedAfterEvidenceCapture"]
    )
    failures = validate_report(report)
    if failures:
        report["status"] = "preflight-fail-closed"
        report["failureCodes"] = failures
    report["reportSha256"] = canonical_sha256(report)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary_output = output.with_name(output.name + ".partial")
    try:
        temporary_output.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        temporary_output.replace(output)
    finally:
        temporary_output.unlink(missing_ok=True)
    if not args.quiet:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "preflight-pass-no-turn" else 1


if __name__ == "__main__":
    raise SystemExit(main())
