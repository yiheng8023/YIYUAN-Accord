#!/usr/bin/env python3
"""Dry-validate the dedicated SEM-03 app-server runtime adapter."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Callable

try:
    from .build_human_ai_collaboration_semantic_authority_composition_projection import (
        materialize_composition,
    )
    from .build_human_ai_collaboration_semantic_authority_execution_plan import (
        PHASE_ORDER,
        canonical_sha256,
        materialize_execution_plan,
        validate_execution_plan,
    )
    from .build_human_ai_collaboration_semantic_authority_continuity_trial import (
        ALLOWED_TREATMENTS,
        sha256_bytes,
    )
    from .probe_codex_app_server_skill_exposure import (
        AppServerSession,
        build_skill_config_override,
        initialize,
        request_skills,
        resolve_codex_executable,
    )
    from .probe_human_ai_collaboration_semantic_authority_composition_exposure import (
        CONFIGURABLE_SCOPES,
        build_no_turn_command,
        compare_inventory,
        isolated_codex_environment,
        select_projected_skills,
    )
    from .probe_human_ai_collaboration_semantic_authority_native_local_exposure import (
        LOCAL_SKILL_BYTES,
        LOCAL_SKILL_SHA256,
        LOCAL_SKILL_SOURCE,
    )
    from .run_human_ai_collaboration_weak_agent_trial import (
        build_turn_input,
        snapshot_tree,
    )
except ImportError:
    from build_human_ai_collaboration_semantic_authority_composition_projection import (
        materialize_composition,
    )
    from build_human_ai_collaboration_semantic_authority_execution_plan import (
        PHASE_ORDER,
        canonical_sha256,
        materialize_execution_plan,
        validate_execution_plan,
    )
    from build_human_ai_collaboration_semantic_authority_continuity_trial import (
        ALLOWED_TREATMENTS,
        sha256_bytes,
    )
    from probe_codex_app_server_skill_exposure import (
        AppServerSession,
        build_skill_config_override,
        initialize,
        request_skills,
        resolve_codex_executable,
    )
    from probe_human_ai_collaboration_semantic_authority_composition_exposure import (
        CONFIGURABLE_SCOPES,
        build_no_turn_command,
        compare_inventory,
        isolated_codex_environment,
        select_projected_skills,
    )
    from probe_human_ai_collaboration_semantic_authority_native_local_exposure import (
        LOCAL_SKILL_BYTES,
        LOCAL_SKILL_SHA256,
        LOCAL_SKILL_SOURCE,
    )
    from run_human_ai_collaboration_weak_agent_trial import (
        build_turn_input,
        snapshot_tree,
    )


ROOT = Path(__file__).resolve().parent.parent
REPORT_ID = "human-ai-collaboration-semantic-authority-runtime-adapter-preflight-v1"
EXPECTED_CLAIM_KEYS = {
    "dispatchReadinessProved",
    "loaderInvocationProved",
    "skillInstructionsReachedModelProved",
    "behavioralCausationProved",
    "semanticContinuityProved",
    "treatmentValueProved",
    "crossHostValueProved",
}
CURRENT_TREE_SHA256 = (
    "295c4f5819f38e49cd4955d81294a5da1ce3197d78fc52c24bfecaf92027daa5"
)
CURRENT_REVISION = "ed37663cc5fbef691ddfecd080dff42f7e7e350d"
CURRENT_LICENSE_SHA256 = (
    "0e7ac423bf2c6e223b7c5b156f8cf72da49d748e56a1641402c31f22ad07dbb5"
)
RUN_IDS = {
    "SEM-NATIVE": "SEM03-DRY-NATIVE-001",
    "SEM-LOCAL-ADAPTED-MONOLITH": "SEM03-DRY-LOCAL-001",
    "SEM-MATT-CURRENT-COMPOSITION": "SEM03-DRY-CURRENT-001",
}
ProjectionMaterializer = Callable[[str, Path], dict[str, Any]]
InventoryProbe = Callable[
    [Path, list[str], dict[str, str]],
    dict[str, Any],
]


def compile_phase_envelopes(
    plan: dict[str, Any],
    runtime_root: Path,
    *,
    selected_skill: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    failures = validate_execution_plan(plan)
    if failures:
        raise RuntimeError("invalid execution plan: " + ", ".join(failures))
    runtime_root = runtime_root.resolve()
    public_root = (runtime_root / "public").resolve()
    route = plan["requestedRoute"]
    sandbox_policy = {
        "type": "workspaceWrite",
        "writableRoots": [str(public_root)],
        "networkAccess": False,
        "excludeSlashTmp": True,
        "excludeTmpdirEnvVar": True,
    }
    envelopes: list[dict[str, Any]] = []
    for phase in plan["lifecyclePhases"]:
        sequence = int(phase["sequence"])
        turn_input = build_turn_input(
            phase["prompt"],
            selected_skill,
            selected_skill_input_mode="structured",
        )
        envelopes.append(
            {
                "phaseId": phase["id"],
                "sequence": sequence,
                "injectHumanDecisionsBeforePhase": phase[
                    "injectHumanDecisionsBeforePhase"
                ],
                "humanDecisionInjectionTarget": (
                    "public/HUMAN_DECISIONS.json"
                    if phase["injectHumanDecisionsBeforePhase"]
                    else None
                ),
                "threadStart": {
                    "id": sequence * 10 + 1,
                    "method": "thread/start",
                    "params": {
                        "model": route["model"],
                        "allowProviderModelFallback": False,
                        "cwd": str(runtime_root),
                        "approvalPolicy": "never",
                        "sandbox": "read-only",
                        "ephemeral": True,
                        "runtimeWorkspaceRoots": [str(runtime_root)],
                    },
                },
                "threadSettingsUpdate": {
                    "id": sequence * 10 + 2,
                    "method": "thread/settings/update",
                    "params": {
                        "threadId": "$THREAD_ID",
                        "sandboxPolicy": sandbox_policy,
                    },
                },
                "turnStart": {
                    "id": sequence * 10 + 3,
                    "method": "turn/start",
                    "params": {
                        "threadId": "$THREAD_ID",
                        "model": route["model"],
                        "effort": route["reasoningEffort"],
                        "sandboxPolicy": sandbox_policy,
                        "runtimeWorkspaceRoots": [str(runtime_root)],
                        "input": turn_input,
                    },
                },
                "closeThreadAfterPhase": phase["closeThreadAfterPhase"],
                "requestsTransmitted": False,
            }
        )
    return envelopes


def validate_phase_envelopes(
    plan: dict[str, Any],
    envelopes: list[dict[str, Any]],
    runtime_root: Path,
    *,
    selected_skill: dict[str, Any] | None,
) -> list[str]:
    failures: list[str] = []
    runtime_root = runtime_root.resolve()
    public_root = (runtime_root / "public").resolve()
    if (runtime_root / "parent").exists():
        failures.append("hard-fail-parent-control-inside-runtime")
    if [row.get("phaseId") for row in envelopes] != PHASE_ORDER:
        failures.append("hard-fail-runtime-phase-order")
    if len(envelopes) != 4:
        failures.append("hard-fail-runtime-phase-count")
    if any(row.get("requestsTransmitted") is not False for row in envelopes):
        failures.append("hard-fail-runtime-request-transmitted")
    expected_sandbox = {
        "type": "workspaceWrite",
        "writableRoots": [str(public_root)],
        "networkAccess": False,
        "excludeSlashTmp": True,
        "excludeTmpdirEnvVar": True,
    }
    for row in envelopes:
        thread_params = row.get("threadStart", {}).get("params", {})
        settings = row.get("threadSettingsUpdate", {}).get("params", {})
        turn_params = row.get("turnStart", {}).get("params", {})
        if (
            thread_params.get("model") != "gpt-5.3-codex-spark"
            or thread_params.get("allowProviderModelFallback") is not False
            or thread_params.get("cwd") != str(runtime_root)
            or thread_params.get("approvalPolicy") != "never"
            or thread_params.get("ephemeral") is not True
            or thread_params.get("runtimeWorkspaceRoots") != [str(runtime_root)]
        ):
            failures.append("hard-fail-runtime-thread-envelope")
        if (
            settings.get("threadId") != "$THREAD_ID"
            or settings.get("sandboxPolicy") != expected_sandbox
            or turn_params.get("threadId") != "$THREAD_ID"
            or turn_params.get("model") != "gpt-5.3-codex-spark"
            or turn_params.get("effort") != "low"
            or turn_params.get("sandboxPolicy") != expected_sandbox
        ):
            failures.append("hard-fail-runtime-turn-envelope")
        skill_inputs = [
            item
            for item in turn_params.get("input", [])
            if item.get("type") == "skill"
        ]
        if selected_skill is None:
            if skill_inputs:
                failures.append("hard-fail-native-structured-skill-input")
        elif skill_inputs != [
            {
                "type": "skill",
                "name": selected_skill["name"],
                "path": selected_skill["path"],
            }
        ]:
            failures.append("hard-fail-selected-structured-skill-input")
    return list(dict.fromkeys(failures))


def _project_runtime_instruction(runtime_root: Path) -> dict[str, Any]:
    public_instruction = runtime_root / "public" / "AGENTS.md"
    runtime_instruction = runtime_root / "AGENTS.md"
    if not public_instruction.is_file() or runtime_instruction.exists():
        raise RuntimeError("runtime instruction projection boundary drifted")
    content = public_instruction.read_bytes()
    runtime_instruction.write_bytes(content)
    return {
        "source": "public/AGENTS.md",
        "target": "AGENTS.md",
        "bytes": len(content),
        "sha256": sha256_bytes(content),
        "sourceAndTargetMatch": runtime_instruction.read_bytes() == content,
    }


def materialize_runtime_projection(
    treatment_id: str,
    runtime_root: Path,
) -> dict[str, Any]:
    runtime_root = runtime_root.resolve()
    if treatment_id == "SEM-NATIVE":
        return {
            "requiredSkillNames": [],
            "skillPaths": {},
            "selectedEntry": None,
            "sourceProjectionVerified": True,
            "sourceExternalReadPerformed": False,
        }
    if treatment_id == "SEM-LOCAL-ADAPTED-MONOLITH":
        content = LOCAL_SKILL_SOURCE.read_bytes()
        if len(content) != LOCAL_SKILL_BYTES or sha256_bytes(content) != LOCAL_SKILL_SHA256:
            raise RuntimeError("frozen local adapted monolith bytes drifted")
        target = runtime_root / ".agents" / "skills" / "grill-with-docs" / "SKILL.md"
        target.parent.mkdir(parents=True)
        target.write_bytes(content)
        if sha256_bytes(target.read_bytes()) != LOCAL_SKILL_SHA256:
            raise RuntimeError("local runtime projection drifted")
        resolved = str(target.resolve())
        return {
            "requiredSkillNames": ["grill-with-docs"],
            "skillPaths": {"grill-with-docs": resolved},
            "selectedEntry": {"name": "grill-with-docs", "path": resolved},
            "sourceProjectionVerified": True,
            "sourceExternalReadPerformed": False,
            "projectedTreeSha256": LOCAL_SKILL_SHA256,
        }
    if treatment_id == "SEM-MATT-CURRENT-COMPOSITION":
        manifest = materialize_composition(
            runtime_root,
            allow_existing=True,
            source_transport="git-object-exact-revision",
        )
        if manifest.get("projectedTreeSha256") != CURRENT_TREE_SHA256:
            raise RuntimeError("current composition runtime tree drifted")
        paths = {
            name: str(Path(path).resolve())
            for name, path in manifest["skillPaths"].items()
        }
        return {
            "requiredSkillNames": sorted(paths),
            "skillPaths": dict(sorted(paths.items())),
            "selectedEntry": {
                "name": "grill-with-docs",
                "path": paths["grill-with-docs"],
            },
            "sourceProjectionVerified": True,
            "sourceExternalReadPerformed": True,
            "projectedTreeSha256": manifest["projectedTreeSha256"],
            "sourceRevision": manifest["sourceLocator"]["revision"],
            "sourceTransport": manifest["sourceLocator"]["mode"],
            "licenseSha256": manifest["license"]["sha256"],
        }
    raise ValueError(f"unsupported semantic-authority treatment: {treatment_id}")


def _normalized_runtime_path(value: str, runtime_root: Path) -> str:
    path = Path(value).resolve()
    if path.is_relative_to(runtime_root):
        relative = path.relative_to(runtime_root)
        if relative.parts and relative.parts[0].startswith(".aah-codex-home-"):
            return "$CODEX_HOME/" + Path(*relative.parts[1:]).as_posix()
        return "runtime/" + relative.as_posix()
    return path.as_posix()


def _normalized_inventory_summary(
    skills: list[dict[str, Any]],
    runtime_root: Path,
) -> dict[str, Any]:
    scopes = sorted({str(skill["scope"]) for skill in skills})
    identities = sorted(
        (
            str(skill["name"]),
            _normalized_runtime_path(str(skill["path"]), runtime_root),
            str(skill["scope"]),
        )
        for skill in skills
    )
    return {
        "skillCount": len(skills),
        "countsByScope": {
            scope: sum(1 for skill in skills if skill["scope"] == scope)
            for scope in scopes
        },
        "enabledCountsByScope": {
            scope: sum(
                1
                for skill in skills
                if skill["scope"] == scope and skill["enabled"] is True
            )
            for scope in scopes
        },
        "identityManifestSha256": canonical_sha256(identities),
        "runtimePathsNormalized": True,
    }


def _projection_evidence(
    projection: dict[str, Any],
    runtime_root: Path,
) -> dict[str, Any]:
    evidence = dict(projection)
    evidence["skillPaths"] = {
        name: _normalized_runtime_path(path, runtime_root)
        for name, path in projection.get("skillPaths", {}).items()
    }
    selected = projection.get("selectedEntry")
    if selected is not None:
        evidence["selectedEntry"] = {
            "name": selected["name"],
            "path": _normalized_runtime_path(selected["path"], runtime_root),
        }
    return evidence


def _inventory_evidence(
    inventory: dict[str, Any],
    runtime_root: Path,
) -> dict[str, Any]:
    evidence = dict(inventory)
    evidence["requiredSkillPaths"] = {
        name: _normalized_runtime_path(path, runtime_root)
        for name, path in inventory.get("requiredSkillPaths", {}).items()
    }
    return evidence


def build_runtime_skill_override(
    configurable_skills: list[dict[str, Any]],
    *,
    enabled_paths: set[str],
) -> str:
    if configurable_skills:
        return build_skill_config_override(
            configurable_skills,
            enabled_paths=enabled_paths,
        )
    if enabled_paths:
        raise RuntimeError("an enabled Skill path was absent from the inventory")
    return "skills.config=[]"


def probe_runtime_inventory(
    runtime_root: Path,
    required_skill_names: list[str],
    skill_paths: dict[str, str],
    *,
    codex_executable: str | None,
    timeout_seconds: float,
) -> dict[str, Any]:
    executable = resolve_codex_executable(codex_executable)
    runtime_root = runtime_root.resolve()
    with isolated_codex_environment(runtime_root, os.environ) as environment:
        control = AppServerSession(
            build_no_turn_command(executable, "skills.config=[]"),
            runtime_root,
            timeout_seconds,
            environment=environment,
        )
        try:
            control_initialize = initialize(control, experimental_api=True)
            control_inventory = request_skills(control, runtime_root, request_id=1)
            projected = (
                select_projected_skills(control_inventory, skill_paths)
                if required_skill_names
                else {}
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
        enabled_paths = {str(row["path"]) for row in projected.values()}
        override = build_runtime_skill_override(
            configurable,
            enabled_paths=enabled_paths,
        )
        session = AppServerSession(
            build_no_turn_command(executable, override),
            runtime_root,
            timeout_seconds,
            environment=environment,
        )
        try:
            effective_initialize = initialize(session, experimental_api=True)
            effective_inventory = request_skills(
                session,
                runtime_root,
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
    exact = (
        set(projected) == set(required_skill_names)
        and comparison.get("sameIdentitySet") is True
        and comparison.get("onlyExpectedConfigurableSkillsEnabled") is True
        and comparison.get("allNonConfigurableStatesPreserved") is True
    )
    return {
        "status": "pass-no-turn" if exact else "fail-closed",
        "requiredSkillNames": required_skill_names,
        "requiredSkillPaths": dict(sorted(skill_paths.items())),
        "allRequiredExactPathsPresent": set(projected) == set(required_skill_names),
        "onlyExpectedConfigurableSkillsEnabled": comparison.get(
            "onlyExpectedConfigurableSkillsEnabled"
        ),
        "allNonConfigurableStatesPreserved": comparison.get(
            "allNonConfigurableStatesPreserved"
        ),
        "controlInventory": _normalized_inventory_summary(
            control_inventory,
            runtime_root,
        ),
        "effectiveInventory": _normalized_inventory_summary(
            effective_inventory,
            runtime_root,
        ),
        "host": {
            "userAgent": effective_initialize.get("userAgent"),
            "platformFamily": effective_initialize.get("platformFamily"),
            "platformOs": effective_initialize.get("platformOs"),
            "controlUserAgent": control_initialize.get("userAgent"),
        },
        "appServerSessionCount": 2,
        "appServerRequestCount": 4,
        "appServerInventoryRequestsTransmitted": True,
        "threadStarted": False,
        "turnStarted": False,
        "modelRequestSent": False,
    }


def validate_runtime_adapter_report(report: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    body = dict(report)
    expected_digest = body.pop("reportSha256", None)
    if expected_digest != canonical_sha256(body):
        failures.append("hard-fail-runtime-report-digest")
    if (
        report.get("schema") != 1
        or report.get("id") != REPORT_ID
        or report.get("status") != "preflight-pass-no-dispatch"
    ):
        failures.append("fail-runtime-report-identity")
    if (
        report.get("modelRequestSent") is not False
        or report.get("threadStarted") is not False
        or report.get("turnStarted") is not False
        or report.get("phaseRequestsTransmitted") is not False
    ):
        failures.append("hard-fail-runtime-dispatch")
    if report.get("temporaryProcessRootRetained") is not False:
        failures.append("hard-fail-runtime-process-root-retained")
    treatments = report.get("treatments", [])
    host_inventory_baseline = report.get("hostInventoryBaselineCounts")
    if (
        not isinstance(host_inventory_baseline, dict)
        or set(host_inventory_baseline) != {"system", "user"}
        or any(
            not isinstance(value, int) or value < 0
            for value in host_inventory_baseline.values()
        )
    ):
        failures.append("hard-fail-runtime-inventory-baseline")
    if (
        {row.get("treatmentId") for row in treatments} != set(ALLOWED_TREATMENTS)
        or len(treatments) != 3
        or any(row.get("status") != "preflight-pass-no-dispatch" for row in treatments)
        or any(row.get("failureCodes") != [] for row in treatments)
        or any(row.get("phaseEnvelopeCount") != 4 for row in treatments)
        or any(row.get("publicPacketStable") is not True for row in treatments)
        or any(row.get("parentControlOutsideRuntime") is not True for row in treatments)
        or any(row.get("instructionProjectionStable") is not True for row in treatments)
        or any(row.get("inventory", {}).get("status") != "pass-no-turn" for row in treatments)
    ):
        failures.append("hard-fail-runtime-treatment-matrix")
    if any(row.get("phaseRequestsTransmitted") is not False for row in treatments):
        failures.append("hard-fail-phase-request-transmitted")
    if (
        report.get("appServerSessionCount") != 6
        or report.get("appServerRequestCount") != 12
        or any(
            row.get("inventory", {}).get("appServerSessionCount") != 2
            for row in treatments
        )
        or any(
            row.get("inventory", {}).get("appServerRequestCount") != 4
            or row.get("inventory", {}).get(
                "appServerInventoryRequestsTransmitted"
            )
            is not True
            for row in treatments
        )
    ):
        failures.append("hard-fail-runtime-session-boundary")
    if any(
        row.get("inventory", {}).get(key) is not True
        for row in treatments
        for key in (
            "allRequiredExactPathsPresent",
            "onlyExpectedConfigurableSkillsEnabled",
            "allNonConfigurableStatesPreserved",
        )
    ):
        failures.append("hard-fail-runtime-inventory-boundary")
    expected_skills = {
        "SEM-NATIVE": [],
        "SEM-LOCAL-ADAPTED-MONOLITH": ["grill-with-docs"],
        "SEM-MATT-CURRENT-COMPOSITION": [
            "domain-modeling",
            "grill-with-docs",
            "grilling",
        ],
    }
    for row in treatments:
        treatment_id = row.get("treatmentId")
        if treatment_id not in expected_skills:
            continue
        projection = row.get("projection", {})
        names = projection.get("requiredSkillNames")
        paths = projection.get("skillPaths")
        selected = projection.get("selectedEntry")
        expected = expected_skills[treatment_id]
        projection_valid = (
            names == expected
            and isinstance(paths, dict)
            and sorted(paths) == expected
        )
        if treatment_id == "SEM-NATIVE":
            projection_valid = (
                projection_valid
                and selected is None
                and projection.get("sourceExternalReadPerformed") is False
            )
        else:
            projection_valid = (
                projection_valid
                and selected
                == {
                    "name": "grill-with-docs",
                    "path": paths.get("grill-with-docs"),
                }
            )
        if treatment_id == "SEM-LOCAL-ADAPTED-MONOLITH":
            projection_valid = (
                projection_valid
                and projection.get("sourceExternalReadPerformed") is False
                and projection.get("projectedTreeSha256") == LOCAL_SKILL_SHA256
            )
        if treatment_id == "SEM-MATT-CURRENT-COMPOSITION":
            projection_valid = (
                projection_valid
                and projection.get("sourceExternalReadPerformed") is True
                and projection.get("projectedTreeSha256") == CURRENT_TREE_SHA256
                and projection.get("sourceRevision") == CURRENT_REVISION
                and projection.get("sourceTransport")
                == "git-object-exact-revision"
                and projection.get("licenseSha256") == CURRENT_LICENSE_SHA256
            )
        inventory = row.get("inventory", {})
        projection_valid = (
            projection_valid
            and inventory.get("requiredSkillNames") == expected
            and inventory.get("requiredSkillPaths") == paths
        )
        if not projection_valid:
            failures.append("hard-fail-runtime-treatment-projection")
        control = inventory.get("controlInventory", {})
        effective = inventory.get("effectiveInventory", {})
        control_counts = control.get("countsByScope", {})
        effective_counts = effective.get("countsByScope", {})
        control_enabled = control.get("enabledCountsByScope", {})
        effective_enabled = effective.get("enabledCountsByScope", {})
        expected_repo_count = len(expected)
        expected_counts = {
            **({"repo": expected_repo_count} if expected_repo_count else {}),
            **(
                host_inventory_baseline
                if isinstance(host_inventory_baseline, dict)
                else {}
            ),
        }
        inventory_valid = (
            control_counts == effective_counts == expected_counts
            and control_enabled.get("system") == control_counts.get("system")
            and effective_enabled.get("system") == control_enabled.get("system")
            and effective_enabled.get("user") == 0
            and effective_enabled.get("repo", 0) == expected_repo_count
        )
        if not inventory_valid:
            failures.append("hard-fail-runtime-inventory-boundary")
    claims = report.get("claimBoundary", {})
    if (
        set(claims) != EXPECTED_CLAIM_KEYS
        or any(value is not False for value in claims.values())
    ):
        failures.append("hard-fail-runtime-claim-promotion")
    return list(dict.fromkeys(failures))


def run_runtime_adapter_preflight(
    temporary_parent: Path,
    *,
    projection_materializer: ProjectionMaterializer | None = None,
    inventory_probe: InventoryProbe | None = None,
    codex_executable: str | None = None,
    timeout_seconds: float = 60.0,
) -> dict[str, Any]:
    temporary_parent = temporary_parent.resolve()
    parent_existed = temporary_parent.exists()
    temporary_parent.mkdir(parents=True, exist_ok=True)
    projection_materializer = projection_materializer or materialize_runtime_projection
    if inventory_probe is None:
        def inventory_probe(
            runtime_root: Path,
            required_skill_names: list[str],
            skill_paths: dict[str, str],
        ) -> dict[str, Any]:
            return probe_runtime_inventory(
                runtime_root,
                required_skill_names,
                skill_paths,
                codex_executable=codex_executable,
                timeout_seconds=timeout_seconds,
            )
    process_root_path: Path | None = None
    receipts: list[dict[str, Any]] = []
    try:
        with tempfile.TemporaryDirectory(
            prefix="aah-sem03-runtime-adapter-",
            dir=temporary_parent,
        ) as temporary:
            process_root_path = Path(temporary).resolve()
            for treatment_id in sorted(ALLOWED_TREATMENTS):
                bundle_root = process_root_path / treatment_id.lower()
                plan_receipt = materialize_execution_plan(
                    bundle_root,
                    treatment_id,
                    RUN_IDS[treatment_id],
                )
                runtime_root = bundle_root / "runtime"
                public_root = runtime_root / "public"
                public_before = snapshot_tree(public_root)
                instruction = _project_runtime_instruction(runtime_root)
                projection = projection_materializer(treatment_id, runtime_root)
                selected = projection.get("selectedEntry")
                plan = json.loads(
                    (bundle_root / "parent" / "EXECUTION_PLAN.json").read_text(
                        encoding="utf-8"
                    )
                )
                envelopes = compile_phase_envelopes(
                    plan,
                    runtime_root,
                    selected_skill=selected,
                )
                envelope_failures = validate_phase_envelopes(
                    plan,
                    envelopes,
                    runtime_root,
                    selected_skill=selected,
                )
                inventory = inventory_probe(
                    runtime_root,
                    list(projection.get("requiredSkillNames", [])),
                    dict(projection.get("skillPaths", {})),
                )
                public_after = snapshot_tree(public_root)
                failures = list(envelope_failures)
                if plan_receipt.get("status") != "compiled-no-dispatch":
                    failures.append("hard-fail-runtime-plan-materialization")
                if projection.get("sourceProjectionVerified") is not True:
                    failures.append("hard-fail-runtime-source-projection")
                if inventory.get("status") != "pass-no-turn":
                    failures.append("hard-fail-runtime-inventory")
                if public_before != public_after:
                    failures.append("hard-fail-runtime-public-packet-drift")
                if not instruction["sourceAndTargetMatch"]:
                    failures.append("hard-fail-runtime-instruction-projection")
                if (runtime_root / "parent").exists():
                    failures.append("hard-fail-parent-control-inside-runtime")
                projection_receipt = _projection_evidence(
                    projection,
                    runtime_root,
                )
                inventory_receipt = _inventory_evidence(
                    inventory,
                    runtime_root,
                )
                receipts.append(
                    {
                        "treatmentId": treatment_id,
                        "runId": RUN_IDS[treatment_id],
                        "status": (
                            "preflight-pass-no-dispatch"
                            if not failures
                            else "preflight-fail-closed"
                        ),
                        "planSha256": plan_receipt["planSha256"],
                        "phaseEnvelopeCount": len(envelopes),
                        "phaseRequestsTransmitted": False,
                        "publicPacketStable": public_before == public_after,
                        "parentControlOutsideRuntime": not (
                            runtime_root / "parent"
                        ).exists(),
                        "instructionProjectionStable": instruction[
                            "sourceAndTargetMatch"
                        ],
                        "projection": projection_receipt,
                        "inventory": inventory_receipt,
                        "failureCodes": list(dict.fromkeys(failures)),
                    }
                )
    finally:
        if (
            not parent_existed
            and temporary_parent.is_dir()
            and not any(temporary_parent.iterdir())
        ):
            temporary_parent.rmdir()

    native_inventory = next(
        (
            row.get("inventory", {}).get("controlInventory", {})
            for row in receipts
            if row.get("treatmentId") == "SEM-NATIVE"
        ),
        {},
    )
    native_counts = native_inventory.get("countsByScope", {})
    report = {
        "schema": 1,
        "id": REPORT_ID,
        "status": (
            "preflight-pass-no-dispatch"
            if all(row["status"] == "preflight-pass-no-dispatch" for row in receipts)
            else "preflight-fail-closed"
        ),
        "treatments": receipts,
        "appServerSessionCount": sum(
            int(row.get("inventory", {}).get("appServerSessionCount", 0))
            for row in receipts
        ),
        "hostInventoryBaselineCounts": {
            scope: native_counts.get(scope)
            for scope in ("system", "user")
        },
        "appServerRequestCount": sum(
            int(row.get("inventory", {}).get("appServerRequestCount", 0))
            for row in receipts
        ),
        "phaseRequestsTransmitted": False,
        "temporaryProcessRootRetained": bool(
            process_root_path and process_root_path.exists()
        ),
        "modelRequestSent": False,
        "threadStarted": False,
        "turnStarted": False,
        "claimBoundary": {
            "dispatchReadinessProved": False,
            "loaderInvocationProved": False,
            "skillInstructionsReachedModelProved": False,
            "behavioralCausationProved": False,
            "semanticContinuityProved": False,
            "treatmentValueProved": False,
            "crossHostValueProved": False,
        },
    }
    report["reportSha256"] = canonical_sha256(report)
    validation_failures = validate_runtime_adapter_report(report)
    if validation_failures:
        report["status"] = "preflight-fail-closed"
        report["failureCodes"] = validation_failures
        report["reportSha256"] = canonical_sha256(
            {key: value for key, value in report.items() if key != "reportSha256"}
        )
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight-output-report", type=Path, required=True)
    parser.add_argument("--temporary-parent", type=Path, default=ROOT / ".tmp")
    parser.add_argument("--codex-executable")
    parser.add_argument("--timeout-seconds", type=float, default=60.0)
    args = parser.parse_args()
    report = run_runtime_adapter_preflight(
        args.temporary_parent,
        codex_executable=args.codex_executable,
        timeout_seconds=args.timeout_seconds,
    )
    output = args.preflight_output_report.resolve()
    if output.exists():
        raise RuntimeError("runtime adapter report already exists")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["status"] == "preflight-pass-no-dispatch" else 1


if __name__ == "__main__":
    raise SystemExit(main())
