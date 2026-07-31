#!/usr/bin/env python3
from __future__ import annotations

import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import shutil
import tempfile
from typing import Any, Iterator

try:
    from .build_source_pinned_skill_projection import canonical_sha256
    from .build_human_ai_collaboration_semantic_authority_continuity_trial import (
        build_packet,
        load_fixture,
        validate_public_packet_oracle_isolation,
    )
    from .probe_codex_app_server_skill_exposure import (
        AppServerSession,
        build_skill_config_override,
        initialize,
        inventory_summary,
        request_skills,
        resolve_codex_executable,
    )
    from .probe_codex_app_server_skill_treatment_fidelity import (
        _git_status_digest,
        file_observation,
    )
    from .probe_human_ai_collaboration_semantic_authority_composition_exposure import (
        CONFIGURABLE_SCOPES,
        build_no_turn_command,
        compare_inventory,
        isolated_codex_environment,
        select_projected_skills,
    )
except ImportError:
    from build_source_pinned_skill_projection import canonical_sha256
    from build_human_ai_collaboration_semantic_authority_continuity_trial import (
        build_packet,
        load_fixture,
        validate_public_packet_oracle_isolation,
    )
    from probe_codex_app_server_skill_exposure import (
        AppServerSession,
        build_skill_config_override,
        initialize,
        inventory_summary,
        request_skills,
        resolve_codex_executable,
    )
    from probe_codex_app_server_skill_treatment_fidelity import (
        _git_status_digest,
        file_observation,
    )
    from probe_human_ai_collaboration_semantic_authority_composition_exposure import (
        CONFIGURABLE_SCOPES,
        build_no_turn_command,
        compare_inventory,
        isolated_codex_environment,
        select_projected_skills,
    )


ROOT = Path(__file__).resolve().parent.parent
PROBE_ID = "semantic-authority-native-local-no-model-exposure-v1"
LOCAL_SKILL_SOURCE = ROOT / "skills" / "grill-with-docs" / "SKILL.md"
LOCAL_SKILL_SHA256 = (
    "e1078020c41b954638ba94acda95a3340739908bd68b1db9bc2af129d3936035"
)
LOCAL_SKILL_BYTES = 5340


def materialize_local_treatment(treatment_root: Path) -> dict[str, Any]:
    treatment_root = treatment_root.resolve()
    if treatment_root.exists():
        if not treatment_root.is_dir() or any(treatment_root.iterdir()):
            raise RuntimeError("treatment root must be an empty directory")
    else:
        treatment_root.mkdir(parents=True)

    source = LOCAL_SKILL_SOURCE.read_bytes()
    source_observation = file_observation(LOCAL_SKILL_SOURCE)
    if (
        len(source) != LOCAL_SKILL_BYTES
        or source_observation["sha256"] != LOCAL_SKILL_SHA256
    ):
        raise RuntimeError("frozen local adapted monolith bytes drifted")

    target = (
        treatment_root
        / ".agents"
        / "skills"
        / "grill-with-docs"
        / "SKILL.md"
    )
    target.parent.mkdir(parents=True)
    target.write_bytes(source)
    observed = file_observation(target)
    if (
        observed["bytes"] != LOCAL_SKILL_BYTES
        or observed["sha256"] != LOCAL_SKILL_SHA256
    ):
        raise RuntimeError("local adapted monolith projection drifted")
    return {
        "path": target.resolve().as_posix(),
        "bytes": observed["bytes"],
        "sha256": observed["sha256"],
    }


def validate_report(report: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    if (
        report.get("schema") != 1
        or report.get("probeId") != PROBE_ID
        or report.get("status") != "preflight-pass-no-turn"
    ):
        failures.append("fail-identity")
    for field, failure in (
        ("threadStarted", "hard-fail-thread-started"),
        ("turnStarted", "hard-fail-turn-started"),
        ("modelRequestSent", "hard-fail-model-request-sent"),
    ):
        if report.get(field) is not False:
            failures.append(failure)

    local = report.get("localTreatment", {})
    if (
        local.get("identity") != "cc.grill-with-docs"
        or local.get("skillName") != "grill-with-docs"
        or local.get("bytes") != LOCAL_SKILL_BYTES
        or local.get("sha256") != LOCAL_SKILL_SHA256
        or local.get("allRequiredExactPathsPresent") is not True
    ):
        failures.append("fail-local-treatment-identity")

    oracle = report.get("publicPacketOracleIsolation", {})
    if oracle != {
        "positivePacketFailureCodes": [],
        "fullOracleLeakFailureCodes": [
            "hard-fail-unmanifested-public-file",
            "hard-fail-private-oracle-leak",
        ],
        "partialCanaryLeakFailureCodes": [
            "hard-fail-private-oracle-leak",
            "hard-fail-public-file-digest-drift",
        ],
        "publicPacketPrivateOracleLeakageRejected": True,
    }:
        failures.append("hard-fail-public-packet-oracle-isolation")

    expected_counts = {
        "native-configurable-skills-disabled": 0,
        "local-adapted-monolith-selected": 1,
    }
    observed_arms: set[str] = set()
    for arm in report.get("arms", []):
        name = str(arm.get("arm"))
        observed_arms.add(name)
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
    if observed_arms != set(expected_counts):
        failures.append("fail-arm-identities")

    if report.get("runtimeIsolation") != {
        "codexHomeMode": "temporary-empty-under-treatment-root",
        "temporaryCodexHomeRetained": False,
        "treatmentRootMode": "temporary-under-repository-tmp",
        "temporaryTreatmentRootRetained": False,
        "mcpConfigurationMode": "empty-table-override",
        "inheritedGlobalConfigExecuted": False,
    }:
        failures.append("hard-fail-runtime-isolation")
    stability = report.get("stability", {})
    for key in (
        "localTreatmentBytesStable",
        "globalConfigStable",
        "repositoryStatusStable",
    ):
        if stability.get(key) is not True:
            failures.append(f"fail-stability:{key}")
    claims = report.get("claimBoundary", {})
    if not claims or any(value is not False for value in claims.values()):
        failures.append("hard-fail-claim-promotion")
    return list(dict.fromkeys(failures))


@contextmanager
def temporary_treatment_root() -> Iterator[Path]:
    temporary_parent = ROOT / ".tmp"
    parent_existed = temporary_parent.exists()
    temporary_parent.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.TemporaryDirectory(
            prefix="aah-sem03-native-local-",
            dir=temporary_parent,
        ) as temporary:
            yield Path(temporary).resolve()
    finally:
        if (
            not parent_existed
            and temporary_parent.is_dir()
            and not any(temporary_parent.iterdir())
        ):
            temporary_parent.rmdir()


def exercise_public_packet_oracle_isolation(
    treatment_root: Path,
) -> dict[str, Any]:
    fixture = load_fixture()
    packet = treatment_root / "public-packet"
    manifest = build_packet(packet, "SEM-NATIVE")
    positive_failures = validate_public_packet_oracle_isolation(
        packet,
        manifest,
        fixture=fixture,
    )

    full_leak = treatment_root / "full-oracle-leak-mutant"
    shutil.copytree(packet, full_leak)
    (full_leak / "PRIVATE_ORACLE.json").write_text(
        json.dumps(fixture["privateOracle"], ensure_ascii=False),
        encoding="utf-8",
        newline="\n",
    )
    full_leak_failures = validate_public_packet_oracle_isolation(
        full_leak,
        manifest,
        fixture=fixture,
    )

    partial_leak = treatment_root / "partial-oracle-leak-mutant"
    shutil.copytree(packet, partial_leak)
    with (partial_leak / "DRAFT_PITCH_PLAN.md").open(
        "a", encoding="utf-8", newline="\n"
    ) as handle:
        handle.write(
            f"\n{fixture['privateOracle']['nonPublicLeakageCanary']}\n"
        )
    partial_leak_failures = validate_public_packet_oracle_isolation(
        partial_leak,
        manifest,
        fixture=fixture,
    )
    return {
        "positivePacketFailureCodes": positive_failures,
        "fullOracleLeakFailureCodes": full_leak_failures,
        "partialCanaryLeakFailureCodes": partial_leak_failures,
        "publicPacketPrivateOracleLeakageRejected": (
            not positive_failures
            and full_leak_failures
            == [
                "hard-fail-unmanifested-public-file",
                "hard-fail-private-oracle-leak",
            ]
            and partial_leak_failures
            == [
                "hard-fail-private-oracle-leak",
                "hard-fail-public-file-digest-drift",
            ]
        ),
    }


def run_preflight(
    *,
    codex_executable: str | None,
    timeout_seconds: float,
) -> dict[str, Any]:
    config_path = (Path.home() / ".codex" / "config.toml").resolve()
    config_before = file_observation(config_path)
    repository_before = _git_status_digest(ROOT)
    executable = resolve_codex_executable(codex_executable)

    with temporary_treatment_root() as treatment_root:
        local = materialize_local_treatment(treatment_root)
        local_path = Path(local["path"])
        local_before = file_observation(local_path)
        with isolated_codex_environment(
            treatment_root,
            os.environ,
        ) as environment:
            control = AppServerSession(
                build_no_turn_command(executable, "skills.config=[]"),
                treatment_root,
                timeout_seconds,
                environment=environment,
            )
            try:
                control_initialize = initialize(control, experimental_api=True)
                control_inventory = request_skills(
                    control,
                    treatment_root,
                    request_id=1,
                )
                projected = select_projected_skills(
                    control_inventory,
                    {"grill-with-docs": local["path"]},
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
            projected_path = str(projected["grill-with-docs"]["path"])
            arms: list[dict[str, Any]] = []
            for arm_name, enabled_paths in (
                ("native-configurable-skills-disabled", set()),
                ("local-adapted-monolith-selected", {projected_path}),
            ):
                override = build_skill_config_override(
                    configurable,
                    enabled_paths=enabled_paths,
                )
                session = AppServerSession(
                    build_no_turn_command(executable, override),
                    treatment_root,
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
                        treatment_root,
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
                        "effectiveInventory": inventory_summary(
                            effective_inventory
                        ),
                        "host": {
                            "userAgent": effective_initialize.get("userAgent"),
                            "platformFamily": effective_initialize.get(
                                "platformFamily"
                            ),
                            "platformOs": effective_initialize.get("platformOs"),
                        },
                    }
                )
        local_after = file_observation(local_path)
        oracle_isolation = exercise_public_packet_oracle_isolation(
            treatment_root
        )
        treatment_root_path = treatment_root

    config_after = file_observation(config_path)
    repository_after = _git_status_digest(ROOT)
    report = {
        "schema": 1,
        "probeId": PROBE_ID,
        "status": "preflight-pass-no-turn",
        "host": {
            "userAgent": control_initialize.get("userAgent"),
            "platformFamily": control_initialize.get("platformFamily"),
            "platformOs": control_initialize.get("platformOs"),
        },
        "controlInventory": inventory_summary(control_inventory),
        "localTreatment": {
            "identity": "cc.grill-with-docs",
            "skillName": "grill-with-docs",
            "bytes": local["bytes"],
            "sha256": local["sha256"],
            "allRequiredExactPathsPresent": (
                Path(projected["grill-with-docs"]["path"]).resolve()
                == Path(local["path"]).resolve()
            ),
        },
        "publicPacketOracleIsolation": oracle_isolation,
        "arms": arms,
        "threadStarted": False,
        "turnStarted": False,
        "modelRequestSent": False,
        "runtimeIsolation": {
            "codexHomeMode": "temporary-empty-under-treatment-root",
            "temporaryCodexHomeRetained": False,
            "treatmentRootMode": "temporary-under-repository-tmp",
            "temporaryTreatmentRootRetained": treatment_root_path.exists(),
            "mcpConfigurationMode": "empty-table-override",
            "inheritedGlobalConfigExecuted": False,
        },
        "stability": {
            "localTreatmentBytesStable": local_before == local_after,
            "globalConfigStable": config_before == config_after,
            "repositoryStatusStable": repository_before == repository_after,
        },
        "claimBoundary": {
            "skillLoaderInvocationProved": False,
            "skillInstructionsReachedModelProved": False,
            "behavioralCausationProved": False,
            "semanticContinuityProved": False,
            "localMonolithValueProved": False,
            "nativeRouteValueProved": False,
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
    parser.add_argument("--codex-executable")
    parser.add_argument("--timeout-seconds", type=float, default=30.0)
    parser.add_argument("--output-report", type=Path)
    args = parser.parse_args()

    report = run_preflight(
        codex_executable=args.codex_executable,
        timeout_seconds=args.timeout_seconds,
    )
    content = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output_report is not None:
        output = args.output_report.resolve()
        if output.exists():
            raise RuntimeError("preflight report already exists")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(content, encoding="utf-8", newline="\n")
    else:
        print(content, end="")
    return 0 if report["status"] == "preflight-pass-no-turn" else 1


if __name__ == "__main__":
    raise SystemExit(main())
