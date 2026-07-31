#!/usr/bin/env python3
"""Run a no-turn exposure preflight for the semantic-authority composition."""

from __future__ import annotations

import argparse
from collections import Counter
from contextlib import contextmanager
import json
import os
from pathlib import Path
import tempfile
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
PROBE_ID = "semantic-authority-composition-exposure-preflight-v1"
MANIFEST_NAME = "SEMANTIC-AUTHORITY-COMPOSITION-PROJECTION.json"


def _normalize(path: str) -> str:
    return path.replace("\\", "/").lower()


def load_manifest(projection_root: Path) -> dict[str, Any]:
    document = json.loads(
        (projection_root / MANIFEST_NAME).read_text(encoding="utf-8")
    )
    body = dict(document)
    expected = body.pop("manifestSha256", None)
    if expected != canonical_sha256(body):
        raise RuntimeError("composition projection manifest digest drifted")
    return document


def build_no_turn_command(
    executable: str,
    disable_override: str,
) -> list[str]:
    command = build_command(executable, disable_override=None)
    command.extend(
        (
            "-c",
            disable_override,
            "-c",
            "model_reasoning_effort=low",
            "-c",
            "mcp_servers={}",
        )
    )
    return command


@contextmanager
def isolated_codex_environment(
    projection_root: Path,
    base_environment: dict[str, str],
):
    with tempfile.TemporaryDirectory(
        prefix=".aah-codex-home-",
        dir=projection_root.resolve(),
    ) as temporary_home:
        environment = base_environment.copy()
        environment["CODEX_HOME"] = str(Path(temporary_home).resolve())
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        yield environment


def select_projected_skills(
    inventory: list[dict[str, Any]],
    skill_paths: dict[str, str],
) -> dict[str, dict[str, Any]]:
    selected: dict[str, dict[str, Any]] = {}
    for name, expected_path in skill_paths.items():
        target = _normalize(Path(expected_path).resolve().as_posix())
        matches = [
            row
            for row in inventory
            if row.get("name") == name
            and _normalize(str(row.get("path", ""))) == target
            and row.get("scope") in CONFIGURABLE_SCOPES
        ]
        if len(matches) != 1:
            raise RuntimeError(
                f"inventory did not contain exactly one projected path: {name}"
            )
        selected[name] = matches[0]
    return selected


def compare_inventory(
    control: list[dict[str, Any]],
    effective: list[dict[str, Any]],
    *,
    expected_enabled_paths: set[str],
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
    normalized_expected = {_normalize(path) for path in expected_enabled_paths}
    enabled_configurable = {
        key[1]
        for key, enabled in after.items()
        if key[2] in CONFIGURABLE_SCOPES and enabled
    }
    return {
        "sameIdentitySet": set(before) == set(after),
        "enabledConfigurableSkillCount": len(enabled_configurable),
        "onlyExpectedConfigurableSkillsEnabled": (
            enabled_configurable == normalized_expected
        ),
        "allNonConfigurableStatesPreserved": all(
            after.get(key) == enabled
            for key, enabled in before.items()
            if key[2] not in CONFIGURABLE_SCOPES
        ),
    }


def validate_report(report: dict[str, Any]) -> list[str]:
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
    if report.get("runtimeIsolation") != {
        "codexHomeMode": "temporary-empty-under-projection",
        "temporaryCodexHomeRetained": False,
        "mcpConfigurationMode": "empty-table-override",
        "inheritedGlobalConfigExecuted": False,
    }:
        failures.append("hard-fail-runtime-isolation")
    exposure = report.get("exposure", {})
    if exposure.get("requiredSkillCount") != 3:
        failures.append("fail-required-skill-count")
    if exposure.get("requiredSkillNames") != [
        "domain-modeling",
        "grill-with-docs",
        "grilling",
    ]:
        failures.append("fail-required-skill-identities")
    if exposure.get("allRequiredExactPathsPresent") is not True:
        failures.append("fail-required-skill-paths")
    expected_counts = {
        "control-unselected": 0,
        "composition-selected": 3,
    }
    for arm in report.get("arms", []):
        name = arm.get("arm")
        inventory = arm.get("inventory", {})
        if inventory.get("enabledConfigurableSkillCount") != expected_counts.get(
            name
        ):
            failures.append(f"fail-enabled-count:{name}")
        for key in (
            "sameIdentitySet",
            "onlyExpectedConfigurableSkillsEnabled",
            "allNonConfigurableStatesPreserved",
        ):
            if inventory.get(key) is not True:
                failures.append(f"fail-inventory:{name}:{key}")
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
    manifest = load_manifest(projection_root)
    skill_paths = {
        name: Path(path).resolve().as_posix()
        for name, path in manifest["skillPaths"].items()
    }
    for path in skill_paths.values():
        resolved = Path(path)
        if not resolved.is_relative_to(projection_root) or not resolved.is_file():
            raise RuntimeError("projected composition Skill escaped or disappeared")
    projection_before = {
        row["path"]: file_observation(projection_root / row["path"])
        for row in manifest["projectedFiles"]
    }
    config_path = (Path.home() / ".codex" / "config.toml").resolve()
    config_before = file_observation(config_path)
    repository_before = _git_status_digest(ROOT)
    executable = resolve_codex_executable(codex_executable)
    with isolated_codex_environment(
        projection_root,
        os.environ,
    ) as environment:
        control = AppServerSession(
            build_no_turn_command(executable, "skills.config=[]"),
            projection_root,
            timeout_seconds,
            environment=environment,
        )
        try:
            control_initialize = initialize(control, experimental_api=True)
            control_inventory = request_skills(control, projection_root, request_id=1)
            projected = select_projected_skills(control_inventory, skill_paths)
            control.close()
        except BaseException:
            control.abort()
            raise

        configurable = [
            row
            for row in control_inventory
            if row.get("scope") in CONFIGURABLE_SCOPES
        ]
        projected_paths = {str(row["path"]) for row in projected.values()}
        arms: list[dict[str, Any]] = []
        for arm_name, enabled_paths in (
            ("control-unselected", set()),
            ("composition-selected", projected_paths),
        ):
            override = build_skill_config_override(
                configurable,
                enabled_paths=enabled_paths,
            )
            session = AppServerSession(
                build_no_turn_command(executable, override),
                projection_root,
                timeout_seconds,
                environment=environment,
            )
            try:
                effective_initialize = initialize(session, experimental_api=True)
                effective_inventory = request_skills(
                    session,
                    projection_root,
                    request_id=1,
                )
                comparison = compare_inventory(
                    control_inventory,
                    effective_inventory,
                    expected_enabled_paths=enabled_paths,
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
        "host": {
            "userAgent": control_initialize.get("userAgent"),
            "platformFamily": control_initialize.get("platformFamily"),
            "platformOs": control_initialize.get("platformOs"),
        },
        "controlInventory": inventory_summary(control_inventory),
        "exposure": {
            "requiredSkillCount": len(projected),
            "requiredSkillNames": sorted(projected),
            "allRequiredExactPathsPresent": set(projected)
            == set(manifest["requiredSkillNames"]),
            "exactPathSha256": {
                name: file_observation(Path(row["path"]))["sha256"]
                for name, row in sorted(projected.items())
            },
        },
        "arms": arms,
        "threadStarted": False,
        "turnStarted": False,
        "modelRequestSent": False,
        "runtimeIsolation": {
            "codexHomeMode": "temporary-empty-under-projection",
            "temporaryCodexHomeRetained": False,
            "mcpConfigurationMode": "empty-table-override",
            "inheritedGlobalConfigExecuted": False,
        },
        "stability": {
            "projectionTreeStable": projection_before == projection_after,
            "globalConfigStable": config_before == config_after,
            "repositoryStatusStable": repository_before == repository_after,
        },
        "claimBoundary": {
            "entryLoaderInvocationProved": False,
            "dependencyLoaderInvocationProved": False,
            "skillInstructionsReachedModelProved": False,
            "namedSlashCompositionWorksProved": False,
            "relativeFormatFileDeliveryProved": False,
            "behavioralCausationProved": False,
            "semanticContinuityProved": False,
            "candidateSuperiorityProved": False,
            "crossHostValueProved": False,
        },
    }
    failures = validate_report(report)
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
    args = parser.parse_args()
    report = run_preflight(
        args.projection_root,
        codex_executable=args.codex_executable,
        timeout_seconds=args.timeout_seconds,
    )
    content = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output_report is not None:
        output = args.output_report.resolve()
        if output.exists():
            raise RuntimeError("preflight report already exists")
        output.write_text(content, encoding="utf-8", newline="\n")
    print(content, end="")
    return 0 if report["status"] == "preflight-pass-no-turn" else 1


if __name__ == "__main__":
    raise SystemExit(main())
