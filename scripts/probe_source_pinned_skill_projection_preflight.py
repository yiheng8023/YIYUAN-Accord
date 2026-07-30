#!/usr/bin/env python3
"""Run a no-turn app-server inventory preflight for one disposable projection."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

try:
    from .build_source_pinned_skill_projection import canonical_sha256
    from .probe_codex_app_server_skill_exposure import (
        AppServerSession,
        build_command,
        build_skill_config_override,
        file_observation,
        initialize,
        inventory_summary,
        request_skills,
        resolve_codex_executable,
    )
    from .probe_codex_app_server_skill_treatment_fidelity import (
        CONFIGURABLE_SCOPES,
        _git_status_digest,
    )
except ImportError:
    from build_source_pinned_skill_projection import canonical_sha256
    from probe_codex_app_server_skill_exposure import (
        AppServerSession,
        build_command,
        build_skill_config_override,
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


ROOT = Path(__file__).resolve().parent.parent
PROBE_ID = "source-pinned-skill-projection-preflight-v1"


def _normalize(path: str) -> str:
    return path.replace("\\", "/").lower()


def load_projection_manifest(projection_root: Path) -> dict[str, Any]:
    path = projection_root / "SOURCE-PINNED-SKILL-PROJECTION.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    body = dict(document)
    expected = body.pop("manifestSha256", None)
    if expected != canonical_sha256(body):
        raise RuntimeError("projection manifest digest drifted")
    return document


def select_projected_skill(
    inventory: list[dict[str, Any]],
    *,
    name: str,
    expected_path: Path,
) -> dict[str, Any]:
    target = _normalize(expected_path.resolve().as_posix())
    matches = [
        row
        for row in inventory
        if row.get("name") == name
        and _normalize(str(row.get("path", ""))) == target
        and row.get("scope") in CONFIGURABLE_SCOPES
    ]
    if len(matches) != 1:
        raise RuntimeError(
            "inventory did not contain exactly one projected candidate path"
        )
    return matches[0]


def compare_inventory(
    control: list[dict[str, Any]],
    effective: list[dict[str, Any]],
    *,
    selected_path: str,
    selected: bool,
) -> dict[str, Any]:
    def keyed(
        rows: list[dict[str, Any]],
    ) -> dict[tuple[str, str, str], bool]:
        return {
            (
                str(row["name"]),
                _normalize(str(row["path"])),
                str(row["scope"]),
            ): bool(row["enabled"])
            for row in rows
        }

    before = keyed(control)
    after = keyed(effective)
    selected_key = next(
        (
            key
            for key in after
            if key[1] == _normalize(selected_path)
            and key[2] in CONFIGURABLE_SCOPES
        ),
        None,
    )
    enabled_configurable = [
        key
        for key, enabled in after.items()
        if key[2] in CONFIGURABLE_SCOPES and enabled
    ]
    expected_enabled = [selected_key] if selected and selected_key else []
    return {
        "sameIdentitySet": set(before) == set(after),
        "selectedIdentityPresent": selected_key is not None,
        "enabledConfigurableSkillCount": len(enabled_configurable),
        "onlyExpectedConfigurableSkillEnabled": (
            enabled_configurable == expected_enabled
        ),
        "allNonConfigurableStatesPreserved": all(
            after.get(key) == enabled
            for key, enabled in before.items()
            if key[2] not in CONFIGURABLE_SCOPES
        ),
    }


def validate_preflight_report(report: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    if (
        report.get("schema") != 1
        or report.get("probeId") != PROBE_ID
        or report.get("status") != "preflight-pass-no-turn"
    ):
        failures.append("fail-identity")
    if report.get("threadStarted") is not False:
        failures.append("hard-fail-thread-started")
    if report.get("turnStarted") is not False:
        failures.append("hard-fail-turn-started")
    for arm in report.get("arms", []):
        inventory = arm.get("inventory", {})
        for key in (
            "sameIdentitySet",
            "selectedIdentityPresent",
            "onlyExpectedConfigurableSkillEnabled",
            "allNonConfigurableStatesPreserved",
        ):
            if inventory.get(key) is not True:
                failures.append(f"fail-inventory:{arm.get('arm')}:{key}")
    stability = report.get("stability", {})
    for key in (
        "projectionTreeStable",
        "globalConfigStable",
        "repositoryStatusStable",
    ):
        if stability.get(key) is not True:
            failures.append(f"fail-stability:{key}")
    claims = report.get("claimBoundary", {})
    if not claims or any(value is not False for value in claims.values()):
        failures.append("hard-fail-claim-promotion")
    return list(dict.fromkeys(failures))


def run_preflight(
    projection_root: Path,
    *,
    codex_executable: str | None,
    timeout_seconds: float,
) -> dict[str, Any]:
    projection_root = projection_root.resolve()
    manifest = load_projection_manifest(projection_root)
    skill_path = Path(manifest["skillPath"]).resolve()
    if not skill_path.is_relative_to(projection_root) or not skill_path.is_file():
        raise RuntimeError("projected Skill path escaped or disappeared")
    projection_before = {
        row["path"]: file_observation(projection_root / row["path"])
        for row in manifest["projectedFiles"]
    }
    config_path = (Path.home() / ".codex" / "config.toml").resolve()
    config_before = file_observation(config_path)
    repository_before = _git_status_digest(ROOT)
    executable = resolve_codex_executable(codex_executable)
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"

    control = AppServerSession(
        build_command(executable, disable_override="skills.config=[]"),
        projection_root,
        timeout_seconds,
        environment=environment,
    )
    try:
        control_initialize = initialize(control, experimental_api=True)
        control_inventory = request_skills(
            control,
            projection_root,
            request_id=1,
        )
        projected = select_projected_skill(
            control_inventory,
            name=manifest["skillName"],
            expected_path=skill_path,
        )
        control.close()
    except BaseException:
        control.abort()
        raise

    configurable = [
        row
        for row in control_inventory
        if row.get("scope") in CONFIGURABLE_SCOPES
    ]
    arms: list[dict[str, Any]] = []
    for arm_name, enabled_paths in (
        ("control-unselected", set()),
        ("candidate-selected", {str(projected["path"])}),
    ):
        override = build_skill_config_override(
            configurable,
            enabled_paths=enabled_paths,
        )
        session = AppServerSession(
            build_command(executable, disable_override=override),
            projection_root,
            timeout_seconds,
            environment=environment,
        )
        try:
            effective_initialize = initialize(
                session,
                experimental_api=True,
            )
            effective_inventory = request_skills(
                session,
                projection_root,
                request_id=1,
            )
            comparison = compare_inventory(
                control_inventory,
                effective_inventory,
                selected_path=str(projected["path"]),
                selected=arm_name == "candidate-selected",
            )
            session.close()
        except BaseException:
            session.abort()
            raise
        arms.append(
            {
                "arm": arm_name,
                "inventory": comparison,
                "effectiveInventory": inventory_summary(effective_inventory),
                "host": {
                    "userAgent": effective_initialize.get("userAgent"),
                    "platformFamily": effective_initialize.get("platformFamily"),
                    "platformOs": effective_initialize.get("platformOs"),
                },
                "threadStarted": False,
                "turnStarted": False,
            }
        )

    projection_after = {
        row["path"]: file_observation(projection_root / row["path"])
        for row in manifest["projectedFiles"]
    }
    config_after = file_observation(config_path)
    repository_after = _git_status_digest(ROOT)
    report = {
        "schema": 1,
        "probeId": PROBE_ID,
        "status": "preflight-pass-no-turn",
        "candidateId": manifest["candidateId"],
        "projectionManifestSha256": manifest["manifestSha256"],
        "projectedTreeSha256": manifest["projectedTreeSha256"],
        "skillName": manifest["skillName"],
        "skillPath": skill_path.as_posix(),
        "controlInventory": inventory_summary(control_inventory),
        "controlHost": {
            "userAgent": control_initialize.get("userAgent"),
            "platformFamily": control_initialize.get("platformFamily"),
            "platformOs": control_initialize.get("platformOs"),
        },
        "arms": arms,
        "threadStarted": False,
        "turnStarted": False,
        "stability": {
            "projectionTreeStable": projection_before == projection_after,
            "globalConfigStable": config_before == config_after,
            "repositoryStatusStable": repository_before == repository_after,
        },
        "claimBoundary": {
            "bodyDeliveryProved": False,
            "independentLoaderEventProved": False,
            "behavioralCausationProved": False,
            "installedCandidateDeliveryProved": False,
            "candidateSuperiorityProved": False,
        },
    }
    failures = validate_preflight_report(report)
    if failures:
        report["status"] = "preflight-fail-closed"
        report["failureCodes"] = failures
    report["reportSha256"] = canonical_sha256(report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--projection-root", type=Path, required=True)
    parser.add_argument("--codex-executable")
    parser.add_argument("--timeout-seconds", type=float, default=60.0)
    parser.add_argument("--output-report", type=Path)
    arguments = parser.parse_args()
    report = run_preflight(
        arguments.projection_root,
        codex_executable=arguments.codex_executable,
        timeout_seconds=arguments.timeout_seconds,
    )
    content = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if arguments.output_report is not None:
        output = arguments.output_report.resolve()
        if output.exists():
            raise RuntimeError("preflight report already exists")
        output.write_text(content, encoding="utf-8", newline="\n")
    print(content, end="")
    return 0 if report["status"] == "preflight-pass-no-turn" else 1


if __name__ == "__main__":
    raise SystemExit(main())
