#!/usr/bin/env python3
"""Compile a parent-owned, zero-dispatch execution plan for SEM-03."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import tempfile
from typing import Any

try:
    from .build_human_ai_collaboration_semantic_authority_continuity_trial import (
        ALLOWED_TREATMENTS,
        PHASE_MUTABLE_FILES,
        build_packet,
        canonical_sha256,
        validate_public_packet_oracle_isolation,
    )
except ImportError:
    from build_human_ai_collaboration_semantic_authority_continuity_trial import (
        ALLOWED_TREATMENTS,
        PHASE_MUTABLE_FILES,
        build_packet,
        canonical_sha256,
        validate_public_packet_oracle_isolation,
    )


ROOT = Path(__file__).resolve().parent.parent
PLAN_ID = "human-ai-collaboration-semantic-authority-execution-plan-v1"
RUN_ID = re.compile(r"^[A-Z0-9][A-Z0-9-]{2,63}$")
LOCAL_SHA256 = "e1078020c41b954638ba94acda95a3340739908bd68b1db9bc2af129d3936035"
CURRENT_REVISION = "ed37663cc5fbef691ddfecd080dff42f7e7e350d"
CURRENT_TREE_SHA256 = (
    "295c4f5819f38e49cd4955d81294a5da1ce3197d78fc52c24bfecaf92027daa5"
)
PHASE_ORDER = list(PHASE_MUTABLE_FILES)
PHASE_PROMPTS = {
    "SEM-PHASE-1-ELICIT": (
        "Read public/TASK.json, public/DRAFT_PITCH_PLAN.md, and "
        "public/src/video_models.py. Update only public/SEMANTIC_REVIEW.json. "
        "Identify the highest-priority unresolved "
        "domain decision without inventing human acceptance."
    ),
    "SEM-PHASE-2-MODEL": (
        "public/HUMAN_DECISIONS.json has now been injected by the parent. "
        "Read it with public/SEMANTIC_REVIEW.json and update only "
        "public/SEMANTIC_AUTHORITY.json. "
        "Preserve term and decision identities without adding an implementation plan."
    ),
    "SEM-PHASE-3-SPEC": (
        "Read public/SEMANTIC_AUTHORITY.json and update only "
        "public/SPECIFICATION.json. "
        "Consume the accepted terms and decisions without promoting implementation authority."
    ),
    "SEM-PHASE-4-REVIEW-HANDOFF": (
        "Read the public source, semantic authority, and specification. Update "
        "only public/IMPLEMENTATION_REVIEW.json, public/HANDOFF.json, and "
        "public/MEASUREMENTS.json. "
        "Detect unresolved source conflicts and do not promote release or closure readiness."
    ),
}
PHASE_INPUTS = {
    "SEM-PHASE-1-ELICIT": [
        "public/TASK.json",
        "public/DRAFT_PITCH_PLAN.md",
        "public/src/video_models.py",
    ],
    "SEM-PHASE-2-MODEL": [
        "public/TASK.json",
        "public/SEMANTIC_REVIEW.json",
        "public/HUMAN_DECISIONS.json",
    ],
    "SEM-PHASE-3-SPEC": [
        "public/TASK.json",
        "public/SEMANTIC_AUTHORITY.json",
    ],
    "SEM-PHASE-4-REVIEW-HANDOFF": [
        "public/TASK.json",
        "public/src/video_models.py",
        "public/SEMANTIC_AUTHORITY.json",
        "public/SPECIFICATION.json",
    ],
}


def treatment_projection(treatment_id: str) -> dict[str, Any]:
    if treatment_id == "SEM-NATIVE":
        return {
            "materializationMode": "none",
            "materializedByThisPlan": True,
            "requiredSkillNames": [],
            "selectedSkillInputs": [],
            "exposureEvidence": (
                "audits/human-ai-collaboration-semantic-authority-native-local-"
                "no-model-exposure-2026-08-01/REPORT.json"
            ),
        }
    if treatment_id == "SEM-LOCAL-ADAPTED-MONOLITH":
        return {
            "materializationMode": "repository-pinned-copy",
            "materializedByThisPlan": False,
            "sourcePath": "skills/grill-with-docs/SKILL.md",
            "requiredSkillNames": ["grill-with-docs"],
            "selectedSkillInputs": [
                {
                    "type": "skill",
                    "name": "grill-with-docs",
                    "runtimePath": ".agents/skills/grill-with-docs/SKILL.md",
                    "sha256": LOCAL_SHA256,
                }
            ],
            "exposureEvidence": (
                "audits/human-ai-collaboration-semantic-authority-native-local-"
                "no-model-exposure-2026-08-01/REPORT.json"
            ),
        }
    if treatment_id == "SEM-MATT-CURRENT-COMPOSITION":
        return {
            "materializationMode": "source-pinned-atomic-builder",
            "materializedByThisPlan": False,
            "revision": CURRENT_REVISION,
            "projectedTreeSha256": CURRENT_TREE_SHA256,
            "requiredSkillNames": [
                "domain-modeling",
                "grill-with-docs",
                "grilling",
            ],
            "selectedSkillInputs": [
                {
                    "type": "skill",
                    "name": "grill-with-docs",
                    "runtimePath": ".agents/skills/grill-with-docs/SKILL.md",
                    "sha256": (
                        "610d091047bcfb9db0f75c057d15538481a721111579fc5ec7f83ad9131a2165"
                    ),
                }
            ],
            "exposureEvidence": (
                "audits/human-ai-collaboration-semantic-authority-current-matt-"
                "no-model-exposure-2026-07-31/REPORT.json"
            ),
        }
    raise ValueError(f"unsupported semantic-authority treatment: {treatment_id}")


def compile_execution_plan(treatment_id: str, run_id: str) -> dict[str, Any]:
    if treatment_id not in ALLOWED_TREATMENTS:
        raise ValueError(f"unsupported semantic-authority treatment: {treatment_id}")
    if not RUN_ID.fullmatch(run_id):
        raise ValueError("run id must be 3-64 uppercase letters, digits, or hyphens")

    phases = [
        {
            "id": phase_id,
            "sequence": index,
            "freshThreadRequired": True,
            "closeThreadAfterPhase": True,
            "injectHumanDecisionsBeforePhase": phase_id == "SEM-PHASE-2-MODEL",
            "inputFiles": PHASE_INPUTS[phase_id],
            "mutableFiles": list(PHASE_MUTABLE_FILES[phase_id]),
            "prompt": PHASE_PROMPTS[phase_id],
        }
        for index, phase_id in enumerate(PHASE_ORDER, start=1)
    ]
    plan = {
        "schema": 1,
        "id": PLAN_ID,
        "status": "compiled-no-dispatch",
        "scenarioId": "HAC-SEMANTIC-AUTHORITY-01",
        "runId": run_id,
        "treatmentId": treatment_id,
        "requestedRoute": {
            "model": "gpt-5.3-codex-spark",
            "reasoningEffort": "low",
            "allowProviderModelFallback": False,
        },
        "authority": {
            "modelDispatchAuthorized": False,
            "modelRequestBudget": 0,
            "separateDispatchAuthorityRequired": True,
        },
        "sandboxBoundary": {
            "type": "workspaceWrite",
            "networkAccess": False,
            "approvalPolicy": "never",
            "writableRoot": "public",
            "externalWritesAllowed": False,
        },
        "workspaceLayout": {
            "runtimeRoot": "runtime",
            "publicPacketRoot": "runtime/public",
            "skillProjectionRoot": "runtime/.agents/skills",
            "parentControlRoot": "parent",
        },
        "candidateRunnerAssessment": {
            "path": "scripts/run_human_ai_collaboration_weak_agent_trial.py",
            "acceptsSemanticTreatmentIds": False,
            "independentLoaderEventAvailable": False,
            "instructionDeliveryProved": False,
            "reuseScope": "app-server-session-inventory-route-sandbox-and-process-boundary-primitives",
        },
        "treatmentProjection": treatment_projection(treatment_id),
        "lifecyclePhases": phases,
        "evidenceCeiling": {
            "taskScopedExposurePreviouslyProved": True,
            "structuredSkillInputMayProvideBoundedAssociation": (
                treatment_id != "SEM-NATIVE"
            ),
            "loaderInvocationProvedByPlan": False,
            "skillInstructionsReachedModelProvedByPlan": False,
            "behavioralCausationProvedByPlan": False,
            "semanticContinuityProvedByPlan": False,
            "treatmentValueProvedByPlan": False,
        },
        "stopConditions": [
            "route-model-or-reasoning-mismatch",
            "provider-fallback-observed",
            "task-scoped-exposure-mismatch",
            "private-oracle-leak-observed",
            "human-decisions-present-before-phase-2",
            "thread-reused-across-phases",
            "network-or-forbidden-tool-call-observed",
            "write-outside-public-root-observed",
            "loader-or-instruction-delivery-claim-upgraded-without-independent-event",
        ],
    }
    plan["planSha256"] = canonical_sha256(plan)
    return plan


def validate_execution_plan(plan: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    body = dict(plan)
    expected_digest = body.pop("planSha256", None)
    if expected_digest != canonical_sha256(body):
        failures.append("hard-fail-plan-digest")
    if (
        plan.get("schema") != 1
        or plan.get("id") != PLAN_ID
        or plan.get("status") != "compiled-no-dispatch"
        or plan.get("scenarioId") != "HAC-SEMANTIC-AUTHORITY-01"
        or plan.get("treatmentId") not in ALLOWED_TREATMENTS
        or not isinstance(plan.get("runId"), str)
        or not RUN_ID.fullmatch(plan["runId"])
    ):
        failures.append("fail-plan-identity")
    if plan.get("requestedRoute") != {
        "model": "gpt-5.3-codex-spark",
        "reasoningEffort": "low",
        "allowProviderModelFallback": False,
    }:
        failures.append("hard-fail-route-boundary")
    if plan.get("authority") != {
        "modelDispatchAuthorized": False,
        "modelRequestBudget": 0,
        "separateDispatchAuthorityRequired": True,
    }:
        failures.append("hard-fail-dispatch-authority-promotion")
    if plan.get("sandboxBoundary") != {
        "type": "workspaceWrite",
        "networkAccess": False,
        "approvalPolicy": "never",
        "writableRoot": "public",
        "externalWritesAllowed": False,
    }:
        failures.append("hard-fail-sandbox-boundary")
    if plan.get("workspaceLayout") != {
        "runtimeRoot": "runtime",
        "publicPacketRoot": "runtime/public",
        "skillProjectionRoot": "runtime/.agents/skills",
        "parentControlRoot": "parent",
    }:
        failures.append("hard-fail-workspace-layout")

    candidate = plan.get("candidateRunnerAssessment", {})
    if (
        candidate.get("acceptsSemanticTreatmentIds") is not False
        or candidate.get("independentLoaderEventAvailable") is not False
        or candidate.get("instructionDeliveryProved") is not False
    ):
        failures.append("hard-fail-runner-capability-promotion")
    ceiling = plan.get("evidenceCeiling", {})
    for key in (
        "loaderInvocationProvedByPlan",
        "skillInstructionsReachedModelProvedByPlan",
        "behavioralCausationProvedByPlan",
        "semanticContinuityProvedByPlan",
        "treatmentValueProvedByPlan",
    ):
        if ceiling.get(key) is not False:
            failures.append("hard-fail-evidence-ceiling-promotion")

    phases = plan.get("lifecyclePhases", [])
    if (
        [phase.get("id") for phase in phases] != PHASE_ORDER
        or [phase.get("sequence") for phase in phases] != [1, 2, 3, 4]
        or any(phase.get("freshThreadRequired") is not True for phase in phases)
        or any(phase.get("closeThreadAfterPhase") is not True for phase in phases)
        or [phase.get("injectHumanDecisionsBeforePhase") for phase in phases]
        != [False, True, False, False]
        or any(
            not path.startswith("public/")
            for phase in phases
            for path in phase.get("inputFiles", [])
        )
        or any(
            phase.get("mutableFiles") != list(PHASE_MUTABLE_FILES[phase["id"]])
            for phase in phases
            if phase.get("id") in PHASE_MUTABLE_FILES
        )
    ):
        failures.append("hard-fail-lifecycle-boundary")

    projection = plan.get("treatmentProjection", {})
    treatment_id = plan.get("treatmentId")
    if treatment_id == "SEM-NATIVE":
        if (
            projection.get("materializationMode") != "none"
            or projection.get("selectedSkillInputs") != []
            or projection.get("requiredSkillNames") != []
        ):
            failures.append("fail-native-treatment-projection")
    elif treatment_id == "SEM-LOCAL-ADAPTED-MONOLITH":
        inputs = projection.get("selectedSkillInputs", [])
        if (
            projection.get("materializationMode") != "repository-pinned-copy"
            or len(inputs) != 1
            or inputs[0].get("name") != "grill-with-docs"
            or inputs[0].get("sha256") != LOCAL_SHA256
        ):
            failures.append("fail-local-treatment-projection")
    elif treatment_id == "SEM-MATT-CURRENT-COMPOSITION":
        if (
            projection.get("materializationMode")
            != "source-pinned-atomic-builder"
            or projection.get("revision") != CURRENT_REVISION
            or projection.get("projectedTreeSha256") != CURRENT_TREE_SHA256
            or projection.get("requiredSkillNames")
            != ["domain-modeling", "grill-with-docs", "grilling"]
        ):
            failures.append("fail-current-treatment-projection")
    required_stops = {
        "route-model-or-reasoning-mismatch",
        "private-oracle-leak-observed",
        "thread-reused-across-phases",
        "write-outside-public-root-observed",
        "loader-or-instruction-delivery-claim-upgraded-without-independent-event",
    }
    if not required_stops <= set(plan.get("stopConditions", [])):
        failures.append("hard-fail-stop-conditions")
    return list(dict.fromkeys(failures))


def materialize_execution_plan(
    output: Path,
    treatment_id: str,
    run_id: str,
) -> dict[str, Any]:
    output = output.resolve()
    if output.exists():
        if not output.is_dir() or any(output.iterdir()):
            raise RuntimeError("execution-plan output must be empty")
    else:
        output.mkdir(parents=True)
    runtime_root = output / "runtime"
    public_root = runtime_root / "public"
    parent_root = output / "parent"
    parent_root.mkdir()
    public_manifest = build_packet(public_root, treatment_id)
    plan = compile_execution_plan(treatment_id, run_id)
    plan_failures = validate_execution_plan(plan)
    packet_failures = validate_public_packet_oracle_isolation(
        public_root,
        public_manifest,
    )
    failures = list(dict.fromkeys(plan_failures + packet_failures))
    (parent_root / "EXECUTION_PLAN.json").write_text(
        json.dumps(plan, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return {
        "schema": 1,
        "status": "compiled-no-dispatch" if not failures else "invalid",
        "runId": run_id,
        "treatmentId": treatment_id,
        "planSha256": plan["planSha256"],
        "publicPacketManifestSha256": public_manifest["manifestSha256"],
        "failureCodes": failures,
        "modelRequestSent": False,
        "threadStarted": False,
        "turnStarted": False,
    }


def validate_preflight_report(report: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    body = dict(report)
    expected_digest = body.pop("reportSha256", None)
    if expected_digest != canonical_sha256(body):
        failures.append("hard-fail-report-digest")
    if (
        report.get("schema") != 1
        or report.get("id")
        != "human-ai-collaboration-semantic-authority-execution-plan-preflight-v1"
        or report.get("status") != "preflight-pass-no-dispatch"
    ):
        failures.append("fail-report-identity")
    if (
        report.get("modelRequestSent") is not False
        or report.get("threadStarted") is not False
        or report.get("turnStarted") is not False
    ):
        failures.append("hard-fail-model-dispatch")
    if report.get("temporaryProcessRootRetained") is not False:
        failures.append("hard-fail-process-root-retained")
    candidate = report.get("candidateRunnerAssessment", {})
    if candidate != {
        "acceptsSemanticTreatmentIds": False,
        "loaderInvocationProved": False,
        "instructionDeliveryProved": False,
        "dedicatedAdapterRequired": True,
    }:
        failures.append("hard-fail-runner-assessment")
    treatments = report.get("treatments", [])
    if (
        {item.get("treatmentId") for item in treatments}
        != set(ALLOWED_TREATMENTS)
        or len(treatments) != 3
        or any(item.get("status") != "compiled-no-dispatch" for item in treatments)
        or any(item.get("failureCodes") != [] for item in treatments)
        or any(item.get("modelRequestSent") is not False for item in treatments)
        or any(item.get("threadStarted") is not False for item in treatments)
        or any(item.get("turnStarted") is not False for item in treatments)
    ):
        failures.append("hard-fail-treatment-plan-matrix")
    claims = report.get("claimBoundary", {})
    if not claims or any(value is not False for value in claims.values()):
        failures.append("hard-fail-claim-promotion")
    return list(dict.fromkeys(failures))


def run_execution_plan_preflight(temporary_parent: Path) -> dict[str, Any]:
    temporary_parent = temporary_parent.resolve()
    parent_existed = temporary_parent.exists()
    temporary_parent.mkdir(parents=True, exist_ok=True)
    run_ids = {
        "SEM-NATIVE": "SEM03-ADMISSION-NATIVE-001",
        "SEM-LOCAL-ADAPTED-MONOLITH": "SEM03-ADMISSION-LOCAL-001",
        "SEM-MATT-CURRENT-COMPOSITION": "SEM03-ADMISSION-CURRENT-001",
    }
    process_root_path: Path | None = None
    try:
        with tempfile.TemporaryDirectory(
            prefix="aah-sem03-execution-plan-",
            dir=temporary_parent,
        ) as temporary:
            process_root_path = Path(temporary).resolve()
            receipts = [
                materialize_execution_plan(
                    process_root_path / treatment_id.lower(),
                    treatment_id,
                    run_ids[treatment_id],
                )
                for treatment_id in sorted(ALLOWED_TREATMENTS)
            ]
    finally:
        if (
            not parent_existed
            and temporary_parent.is_dir()
            and not any(temporary_parent.iterdir())
        ):
            temporary_parent.rmdir()

    report = {
        "schema": 1,
        "id": (
            "human-ai-collaboration-semantic-authority-"
            "execution-plan-preflight-v1"
        ),
        "status": "preflight-pass-no-dispatch",
        "candidateRunnerAssessment": {
            "acceptsSemanticTreatmentIds": False,
            "loaderInvocationProved": False,
            "instructionDeliveryProved": False,
            "dedicatedAdapterRequired": True,
        },
        "treatments": receipts,
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
        },
    }
    failures = validate_preflight_report(
        {**report, "reportSha256": canonical_sha256(report)}
    )
    if failures:
        report["status"] = "preflight-fail-closed"
        report["failureCodes"] = failures
    report["reportSha256"] = canonical_sha256(report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    parser.add_argument("--treatment", choices=sorted(ALLOWED_TREATMENTS))
    parser.add_argument("--run-id")
    parser.add_argument("--preflight-output-report", type=Path)
    parser.add_argument("--temporary-parent", type=Path, default=ROOT / ".tmp")
    args = parser.parse_args()
    if args.preflight_output_report is not None:
        report = run_execution_plan_preflight(args.temporary_parent)
        output = args.preflight_output_report.resolve()
        if output.exists():
            raise RuntimeError("preflight report already exists")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if report["status"] == "preflight-pass-no-dispatch" else 1
    if args.output is None or args.treatment is None or args.run_id is None:
        parser.error(
            "--output, --treatment, and --run-id are required unless "
            "--preflight-output-report is used"
        )
    receipt = materialize_execution_plan(args.output, args.treatment, args.run_id)
    print(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if receipt["status"] == "compiled-no-dispatch" else 1


if __name__ == "__main__":
    raise SystemExit(main())
