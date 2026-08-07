#!/usr/bin/env python3
"""Evaluate the synthetic LongHorizon-Harness execution preflight."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
RECORD_PATH = Path(
    "registry/process-loss-longhorizon-harness-execution-preflight-2026-08-07.json"
)
DOCUMENTATION_PATH = Path(
    "docs/strategy/PROCESS-LOSS-LONGHORIZON-HARNESS-EXECUTION-PREFLIGHT-2026-08-07.md"
)
ACCEPTANCE_PATH = Path("registry/program-acceptance-map.json")
STATIC_ASSESSMENT_PATH = Path(
    "registry/process-loss-longhorizon-harness-static-reuse-assessment-2026-08-07.json"
)
INTERFACE_MAPPING_PATH = Path(
    "registry/process-loss-longhorizon-harness-interface-gap-mapping-2026-08-07.json"
)
EVIDENCE_ID = (
    "evidence.process-loss-longhorizon-harness-execution-preflight-2026-08-07"
)
SUPPORTED_ACCEPTANCE_ASSESSMENTS = {
    "acceptance.end-to-end-process-fidelity": "partial",
    "acceptance.residual-gap-proof": "partial",
    "acceptance.discovery-reuse-before-authoring": "verified",
}
CANDIDATE_REVISION = "b49ebf9654c1ee75eaf56dfe9eec1745fddcfa58"
EXCLUDED_ROOT_CLASSES = (
    "harness-repository",
    "user-project-workspace",
    "agent-skill-root",
    "plugin-app-mcp-hook-root",
    "consumer-configuration-root",
    "credential-session-or-cache-root",
)
STOP_RULES = (
    "stop-on-native-approval-or-sandbox-bypass",
    "stop-on-dangerous-command-flag",
    "stop-on-workspace-identity-or-boundary-ambiguity",
    "stop-on-reparse-or-symlink-escape",
    "stop-on-missing-parent-derived-route-or-artifact-receipt",
    "stop-on-auditor-write-capability",
    "stop-on-outside-workspace-mutation",
    "stop-on-missing-or-failed-rollback-proof",
    "stop-on-crash-resume-overclaim",
    "stop-before-acquisition-install-model-account-or-consumer-boundary",
)
MUTATION_CASE_IDS = (
    "synthetic-boundary",
    "candidate-revision",
    "workspace-class",
    "existing-workspace",
    "resolved-workspace",
    "workspace-exclusions",
    "reparse-escape",
    "pre-state-snapshot",
    "post-state-snapshot",
    "native-approval-bypass",
    "native-sandbox-bypass",
    "dangerous-flags",
    "manager-profile",
    "executor-profile",
    "auditor-profile",
    "effective-route-receipts",
    "parent-derived-hashes",
    "transaction-journal",
    "outside-workspace-mutation",
    "rollback-proof",
    "recovery-separation",
    "crash-resume-evidence",
    "external-access",
    "verification-surface",
    "stop-rules",
)


def _blocked(blockers: list[str]) -> dict[str, Any]:
    return {
        "decision": "blocked",
        "blockers": list(dict.fromkeys(blockers)),
        "executionAuthorized": False,
        "installationAuthorized": False,
        "modelDispatchAuthorized": False,
        "claimBoundary": "synthetic-preflight-mechanism-only",
    }


def evaluate_preflight(request: dict[str, Any]) -> dict[str, Any]:
    """Evaluate one synthetic request and never authorize live execution."""
    blockers: list[str] = []
    candidate = request.get("candidate", {})
    workspace = request.get("workspace", {})
    permission = request.get("hostPermission", {})
    receipts = request.get("receipts", {})
    mutation = request.get("mutationAndRollback", {})
    recovery = request.get("recovery", {})
    external = request.get("externalBoundary", {})
    verification = request.get("verification", {})
    stop_rules = request.get("stopRules", [])
    containers = (
        candidate,
        workspace,
        permission,
        receipts,
        mutation,
        recovery,
        external,
        verification,
    )
    if not all(isinstance(value, dict) for value in containers):
        return _blocked(["preflight-container-invalid"])

    if not (
        request.get("declaredSynthetic") is True
        and request.get("realExecutionAuthorityRepresented") is False
    ):
        blockers.append("synthetic-boundary-missing")
    if not (
        candidate.get("id") == "github:AMAP-ML/LongHorizon-Harness"
        and candidate.get("revision") == CANDIDATE_REVISION
        and candidate.get("interfaceMappingId")
        == "process-loss-longhorizon-harness-interface-gap-mapping-v1"
    ):
        blockers.append("candidate-identity-invalid")

    if workspace.get("rootClass") != "newly-created-os-temp-disposable-root":
        blockers.append("workspace-class-invalid")
    if workspace.get("existingUserWorkspaceAllowed") is not False:
        blockers.append("existing-workspace-forbidden")
    if workspace.get("resolvedAbsolutePathRequired") is not True:
        blockers.append("resolved-workspace-required")
    if workspace.get("excludedRootClasses") != list(EXCLUDED_ROOT_CLASSES):
        blockers.append("workspace-exclusions-incomplete")
    if workspace.get("reparseOrSymlinkEscapeAllowed") is not False:
        blockers.append("workspace-escape-forbidden")
    if workspace.get("preStateSnapshotRequired") is not True:
        blockers.append("pre-state-snapshot-required")
    if workspace.get("postStateSnapshotRequired") is not True:
        blockers.append("post-state-snapshot-required")

    if permission.get("nativeApprovalBypassAllowed") is not False:
        blockers.append("native-approval-bypass-forbidden")
    if permission.get("nativeSandboxBypassAllowed") is not False:
        blockers.append("native-sandbox-bypass-forbidden")
    if permission.get("dangerousFlagFragmentsAllowed") != []:
        blockers.append("dangerous-flags-forbidden")
    if permission.get("manager") != {
        "filesystemMode": "read-contract-and-receipts-only",
        "processExecutionAllowed": False,
        "networkAccessAllowed": False,
        "workspaceWriteAllowed": False,
    }:
        blockers.append("manager-profile-invalid")
    if permission.get("executor") != {
        "filesystemMode": "write-disposable-workspace-only",
        "processExecutionAllowed": True,
        "networkAccessAllowed": False,
        "outsideWorkspaceWriteAllowed": False,
    }:
        blockers.append("executor-profile-invalid")
    if permission.get("auditor") != {
        "filesystemMode": "preventive-readonly-disposable-workspace",
        "processExecutionAllowed": False,
        "networkAccessAllowed": False,
        "workspaceWriteAllowed": False,
        "postHocMutationDetectionIsSufficient": False,
    }:
        blockers.append("auditor-profile-invalid")

    if not (
        receipts.get("threadAndTurnIdentityRequired") is True
        and receipts.get("effectiveHostRouteRequired") is True
        and receipts.get("requestedRouteIsEffectiveRouteEvidence") is False
        and receipts.get("unknownReceiptFieldsFailClosed") is True
    ):
        blockers.append("effective-route-receipts-invalid")
    if not all(
        receipts.get(field) is True
        for field in (
            "inputArtifactHashParentComputed",
            "outputArtifactHashParentComputed",
            "stageContractHashParentComputed",
        )
    ):
        blockers.append("parent-derived-hashes-incomplete")

    if mutation.get("transactionJournalRequired") is not True:
        blockers.append("transaction-journal-required")
    if mutation.get("outsideWorkspaceMutationDisposition") != "halt-and-fail":
        blockers.append("outside-workspace-mutation-must-halt")
    if not (
        mutation.get("restoreOnDetectedMutationRequired") is True
        and mutation.get("preAndPostDigestRequired") is True
        and mutation.get("rollbackReceiptRequired") is True
        and mutation.get("rollbackFailureDisposition")
        == "halt-preserve-evidence-and-require-human"
    ):
        blockers.append("rollback-proof-incomplete")

    if recovery.get("withinProcessRepairSeparatedFromCrashResume") is not True:
        blockers.append("recovery-separation-required")
    if not (
        recovery.get("processCrashResumeClaimRequiresReloadedState") is True
        and recovery.get("resumeSourceRunIdRequired") is True
        and recovery.get("resumeCheckpointDigestRequired") is True
        and recovery.get("replayOrContinuationReceiptRequired") is True
        and recovery.get("unknownResumeStateDisposition")
        == "blocked-no-substitution"
    ):
        blockers.append("crash-resume-evidence-incomplete")

    if any(value is not False for value in external.values()):
        blockers.append("external-boundary-crossed")
    if verification != {
        "resultPath": "registry/process-loss-longhorizon-harness-live-comparison-YYYY-MM-DD.json",
        "acceptanceAssessmentMustRemain": "partial",
        "syntheticEligibilityIsExecutionAuthority": False,
        "behaviorValueAndPortabilityClaimsRequireLiveEvidence": True,
    }:
        blockers.append("verification-surface-invalid")
    if stop_rules != list(STOP_RULES):
        blockers.append("stop-rules-incomplete")

    if blockers:
        return _blocked(blockers)
    return {
        "decision": "eligible-synthetic-preflight-only",
        "blockers": [],
        "executionAuthorized": False,
        "installationAuthorized": False,
        "modelDispatchAuthorized": False,
        "claimBoundary": "synthetic-preflight-mechanism-only",
    }


def _mutation_cases(request: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    specifications = (
        ("synthetic-boundary", ("declaredSynthetic",), False),
        ("candidate-revision", ("candidate", "revision"), "main"),
        ("workspace-class", ("workspace", "rootClass"), "current-repository"),
        ("existing-workspace", ("workspace", "existingUserWorkspaceAllowed"), True),
        ("resolved-workspace", ("workspace", "resolvedAbsolutePathRequired"), False),
        ("workspace-exclusions", ("workspace", "excludedRootClasses"), []),
        ("reparse-escape", ("workspace", "reparseOrSymlinkEscapeAllowed"), True),
        ("pre-state-snapshot", ("workspace", "preStateSnapshotRequired"), False),
        ("post-state-snapshot", ("workspace", "postStateSnapshotRequired"), False),
        ("native-approval-bypass", ("hostPermission", "nativeApprovalBypassAllowed"), True),
        ("native-sandbox-bypass", ("hostPermission", "nativeSandboxBypassAllowed"), True),
        ("dangerous-flags", ("hostPermission", "dangerousFlagFragmentsAllowed"), ["--dangerously-bypass-approvals-and-sandbox"]),
        ("manager-profile", ("hostPermission", "manager", "workspaceWriteAllowed"), True),
        ("executor-profile", ("hostPermission", "executor", "outsideWorkspaceWriteAllowed"), True),
        ("auditor-profile", ("hostPermission", "auditor", "workspaceWriteAllowed"), True),
        ("effective-route-receipts", ("receipts", "effectiveHostRouteRequired"), False),
        ("parent-derived-hashes", ("receipts", "inputArtifactHashParentComputed"), False),
        ("transaction-journal", ("mutationAndRollback", "transactionJournalRequired"), False),
        ("outside-workspace-mutation", ("mutationAndRollback", "outsideWorkspaceMutationDisposition"), "warn-and-continue"),
        ("rollback-proof", ("mutationAndRollback", "rollbackReceiptRequired"), False),
        ("recovery-separation", ("recovery", "withinProcessRepairSeparatedFromCrashResume"), False),
        ("crash-resume-evidence", ("recovery", "resumeCheckpointDigestRequired"), False),
        ("external-access", ("externalBoundary", "modelDispatchAllowed"), True),
        ("verification-surface", ("verification", "syntheticEligibilityIsExecutionAuthority"), True),
        ("stop-rules", ("stopRules",), []),
    )
    cases: list[tuple[str, dict[str, Any]]] = []
    for case_id, path, replacement in specifications:
        mutated = copy.deepcopy(request)
        target: Any = mutated
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = replacement
        cases.append((case_id, mutated))
    return cases


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def validate_preflight_record(
    record: dict[str, Any],
    *,
    acceptance: dict[str, Any] | None = None,
    root: Path = ROOT,
) -> None:
    _require(
        record.get("schema") == 1
        and record.get("id")
        == "process-loss-longhorizon-harness-execution-preflight-v1"
        and record.get("asOf") == "2026-08-07"
        and record.get("status")
        == "verified-synthetic-fail-closed-preflight-no-live-execution",
        "LongHorizon execution preflight identity drifted",
    )
    _require(
        record.get("documentation") == str(DOCUMENTATION_PATH).replace("\\", "/")
        and (root / DOCUMENTATION_PATH).is_file(),
        "LongHorizon execution preflight documentation binding drifted",
    )
    expected_bindings = {
        "staticAssessment": str(STATIC_ASSESSMENT_PATH).replace("\\", "/"),
        "interfaceGapMapping": str(INTERFACE_MAPPING_PATH).replace("\\", "/"),
        "dispatchGateContract": "registry/human-ai-collaboration-process-fidelity-chained-transform-dispatch-gate-contract-2026-07-27.json",
        "processProtocolV2Amendment": "registry/human-ai-collaboration-process-fidelity-chained-transform-trial-protocol-v2-amendment-2026-07-27.json",
        "programAcceptanceMap": str(ACCEPTANCE_PATH).replace("\\", "/"),
    }
    _require(
        record.get("sourceBindings") == expected_bindings
        and all((root / path).is_file() for path in expected_bindings.values()),
        "LongHorizon execution preflight source binding drifted",
    )
    request = record.get("syntheticFixture", {}).get("request", {})
    _require(
        evaluate_preflight(request)
        == {
            "decision": "eligible-synthetic-preflight-only",
            "blockers": [],
            "executionAuthorized": False,
            "installationAuthorized": False,
            "modelDispatchAuthorized": False,
            "claimBoundary": "synthetic-preflight-mechanism-only",
        },
        "LongHorizon execution preflight positive fixture drifted",
    )
    mutations = _mutation_cases(request)
    _require(
        record.get("failureInjectionCaseIds") == list(MUTATION_CASE_IDS)
        and [case_id for case_id, _ in mutations] == list(MUTATION_CASE_IDS),
        "LongHorizon execution preflight mutation ledger drifted",
    )
    for case_id, mutated in mutations:
        result = evaluate_preflight(mutated)
        _require(
            result.get("decision") == "blocked"
            and result.get("executionAuthorized") is False
            and result.get("installationAuthorized") is False
            and result.get("modelDispatchAuthorized") is False,
            f"LongHorizon execution preflight mutation did not fail closed: {case_id}",
        )

    decision = record.get("currentDecision", {})
    _require(
        decision.get("syntheticPreflightMechanismPassed") is True
        and all(
            decision.get(key) is False
            for key in (
                "liveComparisonAuthorized",
                "candidateAcquisitionAuthorized",
                "installationAuthorized",
                "adapterImplementationAuthorized",
                "modelDispatchAuthorized",
                "realTaskBound",
            )
        )
        and isinstance(decision.get("nextGate"), str)
        and decision["nextGate"].startswith("Pause before candidate acquisition"),
        "LongHorizon execution preflight current decision drifted",
    )
    claims = record.get("claimBoundary", {})
    _require(
        claims.get("provesSyntheticPreflightMechanism") is True
        and all(
            claims.get(key) is False
            for key in (
                "provesLivePermissionEnforcement",
                "provesDisposableWorkspaceImplementation",
                "provesRollbackImplementation",
                "provesEffectiveRouteReceipts",
                "provesCrashResume",
                "provesRuntimeBehavior",
                "provesIndependentValue",
                "provesCrossHostPortability",
                "provesResidualGap",
                "provesProductionReadiness",
                "advancesProcessFidelityAcceptance",
            )
        ),
        "LongHorizon execution preflight claim boundary drifted",
    )
    authority = record.get("authorityBoundary", {})
    _require(
        authority.get("repositoryLocalSyntheticPreflightAuthorized") is True
        and all(
            authority.get(key) is False
            for key in authority
            if key != "repositoryLocalSyntheticPreflightAuthorized"
        ),
        "LongHorizon execution preflight authority boundary drifted",
    )

    acceptance = acceptance or json.loads(
        (root / ACCEPTANCE_PATH).read_text(encoding="utf-8")
    )
    criteria = {
        row.get("id"): row
        for row in acceptance.get("acceptanceCriteria", [])
        if isinstance(row, dict)
    }
    evidence = {
        row.get("id"): row
        for row in acceptance.get("evidence", [])
        if isinstance(row, dict)
    }
    _require(
        all(
            criteria.get(acceptance_id, {}).get("assessment") == assessment
            and EVIDENCE_ID
            in criteria.get(acceptance_id, {}).get("evidenceIds", [])
            for acceptance_id, assessment in SUPPORTED_ACCEPTANCE_ASSESSMENTS.items()
        ),
        "LongHorizon execution preflight acceptance boundary drifted",
    )
    evidence_record = evidence.get(EVIDENCE_ID, {})
    _require(
        evidence_record.get("path") == str(RECORD_PATH).replace("\\", "/")
        and evidence_record.get("asOf") == "2026-08-07"
        and set(evidence_record.get("supports", []))
        == set(SUPPORTED_ACCEPTANCE_ASSESSMENTS),
        "LongHorizon execution preflight evidence binding drifted",
    )
    documentation = " ".join(
        (root / DOCUMENTATION_PATH).read_text(encoding="utf-8").split()
    )
    for phrase in (
        "does not execute LongHorizon-Harness",
        "Synthetic eligibility is never execution authority",
        "A real Claude task is still not required",
        "the next state transition crosses a new trust boundary",
    ):
        _require(
            phrase in documentation,
            f"LongHorizon execution preflight documentation boundary missing: {phrase}",
        )


def validate_repository_preflight(root: Path = ROOT) -> dict[str, Any]:
    record = json.loads((root / RECORD_PATH).read_text(encoding="utf-8"))
    validate_preflight_record(record, root=root)
    return record


def main() -> int:
    record = validate_repository_preflight()
    print(
        "PASS: LongHorizon-Harness synthetic execution preflight "
        f"({len(record['failureInjectionCaseIds'])} fail-closed cases)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
