#!/usr/bin/env python3
"""Validate Context, Git, and MCP program-acceptance reconciliation."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
RECONCILIATION_PATH = (
    "registry/harness-three-lane-program-acceptance-reconciliation-"
    "2026-07-27.json"
)
PROGRAM_PATH = "registry/program-acceptance-map.json"
CLEANUP_PATH = "registry/closeout-cleanup-debt-preview-2026-07-24.json"
CREATOR_CLOSE_CALIBRATION_PATH = (
    "registry/mcp-thread-creator-connection-close-calibration-attempt-"
    "2026-07-27.json"
)
CONTEXT_RECEIVER_DELTA_LEDGER_PATH = (
    "registry/context-handoff-receiver-delta-ledger-evidence-2026-07-27.json"
)
OBSERVER_ACQUISITION_GATE_PATH = (
    "registry/mcp-thread-creator-close-observer-acquisition-path-admission-"
    "2026-07-27.json"
)
AUTO_ATTACH_V2_AMENDMENT_PATH = (
    "registry/mcp-thread-creator-connection-close-auto-attach-offline-"
    "amendment-v2-2026-07-27.json"
)
AUTO_ATTACH_V2_PROTOCOL_PATH = (
    "registry/mcp-thread-creator-connection-close-auto-attach-protocol-v2-"
    "2026-07-27.json"
)
DOC_PATH = (
    "docs/strategy/HARNESS-THREE-LANE-PROGRAM-ACCEPTANCE-"
    "RECONCILIATION-2026-07-27.md"
)
EVIDENCE_ID = (
    "evidence.harness-three-lane-program-acceptance-"
    "reconciliation-2026-07-27"
)
EXPECTED_LANE_IDS = [
    "context-lifecycle",
    "git-topology",
    "mcp-lifecycle",
]
EXPECTED_PATHS = {
    "context-lifecycle": [
        "registry/context-evidence-envelope-2026-07-23.json",
        (
            "registry/context-pressure-provenance-evidence-envelope-"
            "2026-07-24.json"
        ),
        "registry/context-handoff-packet-freshness-2026-07-24.json",
        "registry/context-git-snapshot-projection-contract-2026-07-27.json",
        (
            "registry/context-handoff-receiver-delta-ledger-evidence-"
            "2026-07-27.json"
        ),
        "registry/handoff-loader-trial-preflight-contract-2026-07-24.json",
        (
            "registry/instruction-carrier-trial-preflight-contract-"
            "2026-07-23.json"
        ),
    ],
    "git-topology": [
        "registry/git-host-preflight-evidence-contract-2026-07-23.json",
        "registry/git-host-authorization-trial-contract-2026-07-23.json",
        "registry/git-readonly-preflight-envelope-contract-2026-07-24.json",
    ],
    "mcp-lifecycle": [
        (
            "registry/mcp-app-server-0.145.0-direct-tool-call-evidence-"
            "2026-07-23.json"
        ),
        (
            "registry/mcp-app-server-0.145.0-startup-profile-evidence-"
            "2026-07-23.json"
        ),
        (
            "registry/mcp-app-server-0.145.0-new-thread-reload-evidence-"
            "2026-07-23.json"
        ),
        (
            "registry/mcp-app-server-0.145.0-reload-release-attribution-"
            "evidence-2026-07-27.json"
        ),
        (
            "registry/mcp-app-server-0.145.0-thread-unsubscribe-release-"
            "attribution-evidence-2026-07-27.json"
        ),
        (
            "registry/mcp-app-server-0.145.0-multi-connection-subscription-"
            "preflight-evidence-2026-07-27.json"
        ),
        (
            "registry/mcp-thread-creator-connection-close-attribution-"
            "protocol-2026-07-27.json"
        ),
        CREATOR_CLOSE_CALIBRATION_PATH,
        (
            "registry/mcp-thread-creator-close-observer-acquisition-path-"
            "admission-2026-07-27.json"
        ),
        (
            "registry/mcp-thread-creator-connection-close-auto-attach-"
            "offline-amendment-v2-2026-07-27.json"
        ),
        (
            "registry/mcp-thread-creator-connection-close-auto-attach-"
            "protocol-v2-2026-07-27.json"
        ),
        (
            "registry/mcp-app-server-0.145.0-idle-unload-evidence-"
            "2026-07-23.json"
        ),
        (
            "registry/mcp-app-server-0.145.0-child-exit-recovery-evidence-"
            "2026-07-23.json"
        ),
        "registry/mcp-task-selection-decision-contract-2026-07-23.json",
        "registry/mcp-task-lifecycle-evidence-contract-2026-07-23.json",
        "registry/mcp-lifecycle-trial-skeleton-contract-2026-07-24.json",
        "registry/mcp-same-thread-refresh-evidence-contract-2026-07-24.json",
    ],
}
EXPECTED_ACCEPTANCE = {
    "acceptance.dynamic-runtime-control-gap-research": "partial",
    "acceptance.native-task-orchestration-boundary": "partial",
    "acceptance.residual-gap-proof": "partial",
}
EXPECTED_ADDITIVE_PROGRAM_EVIDENCE = {
    "evidence.context-handoff-receiver-delta-ledger-2026-07-27": {
        "path": CONTEXT_RECEIVER_DELTA_LEDGER_PATH,
        "acceptanceId": "acceptance.end-to-end-process-fidelity",
    },
    (
        "evidence.mcp-thread-creator-close-observer-acquisition-path-"
        "admission-2026-07-27"
    ): {
        "path": OBSERVER_ACQUISITION_GATE_PATH,
        "acceptanceId": "acceptance.dynamic-runtime-control-gap-research",
    },
    (
        "evidence.mcp-thread-creator-connection-close-auto-attach-v2-"
        "offline-amendment-2026-07-27"
    ): {
        "path": AUTO_ATTACH_V2_AMENDMENT_PATH,
        "acceptanceId": "acceptance.dynamic-runtime-control-gap-research",
    },
}
FORBIDDEN_ADDITIVE_ACCEPTANCE_IDS = {
    "acceptance.native-task-orchestration-boundary",
    "acceptance.residual-gap-proof",
    "acceptance.agent-neutral-release",
    "acceptance.evidence-backed-release-evolution",
    "acceptance.public-source-next-gate-triage",
}
EXPECTED_UNPROVED = {
    "context-lifecycle": [
        "live context telemetry or a universal efficiency interval",
        "automatic compression quality",
        "automatic new-thread creation",
        "fresh-session handoff Skill invocation",
        "receiver recovery",
        "lossless handoff",
        "atomic build/create snapshot",
        "dirty-path ownership",
        "cross-Agent instruction adherence",
        "weak-Agent receiver behavior or cross-host receiver behavior",
    ],
    "git-topology": [
        "safe creation or mutation in a bound user repository",
        "native approval-dialog enforcement",
        "filesystem zero-write observation",
        "live remote freshness",
        "interruption or crash recovery",
        "cross-host parity",
    ],
    "mcp-lifecycle": [
        "same-thread live enable or disable",
        "task-end immediate release",
        (
            "reload-caused prior-process release beyond the tested five-"
            "second Sentinel window or on other hosts"
        ),
        (
            "unsubscribe-associated release beyond the tested five-second "
            "paired Sentinel windows or on other hosts"
        ),
        (
            "creator-connection-close formal paired execution, validity, or "
            "release association"
        ),
        (
            "auto-attach as a second independently releasable subscription "
            "or owner"
        ),
        "auto-attach v2 live readiness, execution, or outcome",
        (
            "overlapping task or subscription ownership and final-release "
            "semantics"
        ),
        "live leases or reference counts",
        "stable resource or response-latency benefit",
        "generic crash recovery",
        "cross-host parity",
    ],
}
EXPECTED_SUPPORTED_BOUNDARY = {
    "context-lifecycle": (
        "Local envelope, freshness, provenance, shared Context-Git snapshot "
        "projection, additive parent-recomputed receiver delta ledger, "
        "instruction-carrier, and fail-closed preflight contracts are "
        "machine-verifiable."
    ),
    "git-topology": (
        "Offline decisions, disposable repositories, exact attempted-command "
        "records, denial handling, and read-only preflight envelopes have "
        "bounded evidence."
    ),
    "mcp-lifecycle": (
        "On Codex app-server 0.145.0, three isolated reload repetitions "
        "retained one exact loaded Sentinel, three concurrent paired "
        "unsubscribe repetitions retained all six exact Sentinel runtimes for "
        "five seconds, and three multi-connection preflights did not observe a "
        "second independently releasable subscription; startup-profile, "
        "new-thread, idle-unload, and child-exit observations remain bounded. "
        "One creator-connection-close calibration failed before either paired "
        "window on an invalid zero-turn rollout prerequisite and records an "
        "authority conflict. The observer-acquisition gate admits only an "
        "offline amendment, and the auto-attach v2 protocol has 16 injected "
        "in-memory deterministic scenarios but zero formal live runs."
    ),
}
EXPECTED_FORBIDDEN_PROMOTION = {
    "context-lifecycle": (
        "A parent-created source-backed transport run, shared Git-observer "
        "projection, and deterministic receiver delta ledger are not automatic "
        "thread creation, atomic build/create, dirty-path ownership, receiver "
        "recovery, automatic handoff invocation, weak-Agent behavior, "
        "cross-host behavior, or context-lifecycle completion."
    ),
    "git-topology": (
        "Disposable-repository and fixture evidence is not user-repository "
        "safety, live authorization, or universal recovery proof."
    ),
    "mcp-lifecycle": (
        "Reload and unsubscribe retention, multi-connection callability "
        "without a second subscription, the offline observer-acquisition gate, "
        "the injected-fake auto-attach v2 protocol, and a creator-connection-"
        "close calibration that failed before its paired window are not task-"
        "end release, creator-close release or retention, a second subscription "
        "or independent owner, final-owner release, arbitrary-MCP behavior, "
        "lease or reference-count semantics, resource benefit, controller "
        "need, live readiness, or task-scoped same-thread lifecycle control."
    ),
}
EXPECTED_CLAIM_LIMIT = (
    "This reconciliation incorporates a local shared Context-Git projection "
    "contract, an additive deterministic receiver delta ledger, bounded Codex "
    "app-server 0.145.0 reload and paired thread-unsubscribe observations, a "
    "three-run multi-connection subscription preflight, an offline observer-"
    "acquisition admission gate, an injected-fake auto-attach v2 amendment and "
    "unexecuted protocol, the historical unexecuted creator-connection-close "
    "protocol, and one invalid pre-window calibration. That calibration records "
    "a zero-turn rollout-prerequisite failure and authority conflict, not "
    "release or retention. The delta ledger does not prove receiver recovery, "
    "weak-Agent behavior, or cross-host behavior; the observer gate and v2 "
    "amendment do not prove a second subscription, an independent owner, live "
    "readiness, or any live creator-close outcome. This record proves only "
    "deterministic local mechanisms and the stated bounded host observations. "
    "It does not prove atomic thread creation, receiver recovery, dirty-path "
    "ownership, task-end release, creator-connection-close release or "
    "retention, longer-window or arbitrary-MCP behavior, overlapping "
    "ownership, lease or reference-count semantics, cross-host behavior, "
    "stable resource benefit, or a residual need for a self-authored runtime "
    "controller. The calibration roots were originally cleanup debt and were "
    "removed only by the separately authorized 2026-07-30 exact cleanup "
    "transaction; that stage checkpoint is not program closeout."
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _index(items: Any, key: str, label: str) -> dict[str, dict[str, Any]]:
    _require(isinstance(items, list), f"{label} is not a list")
    result: dict[str, dict[str, Any]] = {}
    for item in items:
        _require(
            isinstance(item, dict) and isinstance(item.get(key), str),
            f"{label} item is invalid",
        )
        _require(item[key] not in result, f"{label} contains a duplicate")
        result[item[key]] = item
    return result


def validate_reconciliation(
    document: dict[str, Any],
    *,
    root: Path = ROOT,
    program: dict[str, Any] | None = None,
) -> None:
    _require(
        document.get("schema") == 1
        and document.get("id")
        == "harness-three-lane-program-acceptance-reconciliation-2026-07-27"
        and document.get("date") == "2026-07-27"
        and document.get("status")
        == (
            "verified-reconciliation-including-context-delta-ledger-and-mcp-"
            "observer-auto-attach-v2-offline-boundaries-all-runtime-"
            "assessments-partial"
        ),
        "Three-lane reconciliation identity drifted",
    )
    execution = document.get("executionBoundary")
    _require(
        isinstance(execution, dict)
        and execution.get("agentDispatchCount") == 3
        and execution.get("modelCallCount") == 3
        and execution.get("hostProbeModelTurnCount") == 0
        and execution.get("hostProbeModelRequestCount") == 0
        and execution.get("externalAccessUsed") is True
        and execution.get("applicationLogExternalNetworkAttemptObserved")
        is True
        and execution.get("hostProbeModelRequestSent") is False
        and execution.get("isolatedTemporaryHostConfigChanged") is True
        and execution.get("hostConfigurationChanged") is False
        and execution.get("gitMutationPerformed") is False
        and execution.get("cleanupPerformed") is False
        and execution.get("invalidCreatorClosePreWindowCalibrationCount") == 1
        and execution.get("formalCreatorClosePairedRunCount") == 0
        and execution.get("creatorCloseAuthorityConflictRecorded") is True
        and execution.get("creatorCloseOfflineProbeRemediated") is True
        and execution.get("creatorCloseLiveRerunPerformed") is False
        and execution.get("contextReceiverDeltaLedgerAgentDispatchCount") == 0
        and execution.get("contextReceiverDeltaLedgerModelCallCount") == 0
        and execution.get("mcpObserverAcquisitionGateLiveProbeCount") == 0
        and execution.get("mcpAutoAttachV2DeterministicScenarioCount") == 16
        and execution.get("mcpAutoAttachV2FormalLiveRunCount") == 0,
        "Three-lane reconciliation execution boundary drifted",
    )

    lanes = _index(document.get("lanes"), "laneId", "Reconciliation lanes")
    _require(
        list(lanes) == EXPECTED_LANE_IDS,
        "Three-lane reconciliation lane set drifted",
    )
    for lane_id, lane in lanes.items():
        evidence = lane.get("evidence")
        _require(
            isinstance(evidence, list)
            and [item.get("path") for item in evidence]
            == EXPECTED_PATHS[lane_id],
            f"Three-lane evidence set drifted: {lane_id}",
        )
        for item in evidence:
            path = root / item["path"]
            _require(
                path.is_file(),
                f"Three-lane evidence file is missing: {path}",
            )
            _require(
                _file_sha256(path).lower() == item.get("sha256", "").lower(),
                f"Three-lane evidence hash drifted: {path}",
            )
            source = json.loads(path.read_text(encoding="utf-8"))
            _require(
                source.get("status") == item.get("status"),
                f"Three-lane evidence status drifted: {path}",
            )
        _require(
            isinstance(lane.get("evidenceClass"), str)
            and bool(lane["evidenceClass"])
            and lane.get("supportedBoundary")
            == EXPECTED_SUPPORTED_BOUNDARY[lane_id]
            and lane.get("unproved") == EXPECTED_UNPROVED[lane_id]
            and lane.get("forbiddenPromotion")
            == EXPECTED_FORBIDDEN_PROMOTION[lane_id],
            f"Three-lane claim boundary is incomplete: {lane_id}",
        )

    context_ledger = json.loads(
        (root / CONTEXT_RECEIVER_DELTA_LEDGER_PATH).read_text(encoding="utf-8")
    )
    _require(
        context_ledger.get("mode") == "additive-parent-recomputed"
        and context_ledger.get("canonicalVerdictChanged") is False
        and context_ledger.get("deterministicCoverage", {}).get(
            "fixtureCaseCount"
        )
        == 16
        and context_ledger.get("executionBoundary", {}).get(
            "agentDispatchCount"
        )
        == 0
        and context_ledger.get("executionBoundary", {}).get("modelCallCount")
        == 0
        and all(
            value is False
            for value in context_ledger.get("claimBoundary", {}).values()
        ),
        "Context receiver delta-ledger offline boundary drifted",
    )

    observer_gate = json.loads(
        (root / OBSERVER_ACQUISITION_GATE_PATH).read_text(encoding="utf-8")
    )
    _require(
        observer_gate.get("admissionDecision", {}).get("conclusion")
        == "offline-amendment-required-before-live"
        and observer_gate.get("admissionDecision", {}).get(
            "currentProtocolProbePairAdmittedForLiveExecution"
        )
        is False
        and observer_gate.get("admissionDecision", {}).get(
            "autoAttachAcquisitionPathAdmittedAsSecondSubscription"
        )
        is False
        and observer_gate.get("admissionDecision", {}).get(
            "liveRerunAuthorized"
        )
        is False
        and observer_gate.get("machineVerifiedObservation", {}).get(
            "formalRunCount"
        )
        == 3
        and observer_gate.get("machineVerifiedObservation", {}).get(
            "modelTurnRequestCount"
        )
        == 0
        and observer_gate.get("machineVerifiedObservation", {}).get(
            "secondIndependentlyReleasableSubscriptionObserved"
        )
        is False
        and all(
            value is False
            for value in observer_gate.get("claimBoundary", {}).values()
        ),
        "MCP observer-acquisition admission boundary drifted",
    )

    auto_attach_amendment = json.loads(
        (root / AUTO_ATTACH_V2_AMENDMENT_PATH).read_text(encoding="utf-8")
    )
    auto_attach_protocol = json.loads(
        (root / AUTO_ATTACH_V2_PROTOCOL_PATH).read_text(encoding="utf-8")
    )
    _require(
        auto_attach_amendment.get("offlineAmendment", {}).get(
            "acquisitionPath"
        )
        == "thread-created-auto-attach"
        and auto_attach_amendment.get("offlineAmendment", {}).get(
            "observerThreadResumeCalls"
        )
        == 0
        and auto_attach_amendment.get("deterministicValidation", {}).get(
            "transport"
        )
        == "injected-in-memory-fake-only"
        and auto_attach_amendment.get("deterministicValidation", {}).get(
            "scenarioCount"
        )
        == 16
        and auto_attach_amendment.get("formalEvidenceBoundary", {}).get(
            "formalLiveRunCount"
        )
        == 0
        and auto_attach_amendment.get("formalEvidenceBoundary", {}).get(
            "liveHostOutcomeObserved"
        )
        is False
        and auto_attach_amendment.get("nextGate", {}).get(
            "liveExecutionAuthorizedByThisRecord"
        )
        is False
        and all(
            value is False
            for value in auto_attach_amendment.get(
                "claimBoundary", {}
            ).values()
        )
        and auto_attach_protocol.get("status")
        == "offline-amendment-not-live-executed"
        and auto_attach_protocol.get("formalRunCount") == 0
        and auto_attach_protocol.get("executionBoundary", {}).get(
            "formalLivePairedRunsExecuted"
        )
        is False
        and auto_attach_protocol.get("executionBoundary", {}).get(
            "liveProtocolExecutionAuthorized"
        )
        is False
        and all(
            value is False
            for value in auto_attach_protocol.get(
                "claimBoundary", {}
            ).values()
        ),
        "MCP auto-attach v2 offline mechanism boundary drifted",
    )

    creator_close_calibration = json.loads(
        (root / CREATOR_CLOSE_CALIBRATION_PATH).read_text(encoding="utf-8")
    )
    _require(
        creator_close_calibration.get("attempt", {}).get(
            "failedBeforePairedWindow"
        )
        is True
        and creator_close_calibration.get("attempt", {}).get(
            "pairedWindowEntered"
        )
        is False
        and creator_close_calibration.get("attempt", {}).get(
            "formalLivePairedRunCount"
        )
        == 0
        and creator_close_calibration.get("attempt", {}).get(
            "failureClass"
        )
        == "runner-prerequisite-invalid-for-zero-turn-thread"
        and creator_close_calibration.get("attempt", {}).get(
            "failureIsHostReleaseOutcome"
        )
        is False
        and creator_close_calibration.get("authorityIncident", {}).get(
            "protocolLoopbackBoundaryWasFalse"
        )
        is True
        and creator_close_calibration.get("authorityIncident", {}).get(
            "rerunRequiresExplicitLoopbackExecutionAuthorization"
        )
        is True
        and creator_close_calibration.get("remediation", {}).get(
            "zeroTurnRolloutAbsenceIsNowObservationNotGate"
        )
        is True
        and creator_close_calibration.get("remediation", {}).get(
            "liveRerunPerformed"
        )
        is False
        and all(
            value is False
            for value in creator_close_calibration.get(
                "claimBoundary", {}
            ).values()
        ),
        "Creator-close invalid calibration boundary drifted",
    )

    acceptance_bindings = _index(
        document.get("programAcceptanceBindings"),
        "acceptanceId",
        "Program acceptance bindings",
    )
    _require(
        {
            key: item.get("requiredAssessment")
            for key, item in acceptance_bindings.items()
        }
        == EXPECTED_ACCEPTANCE,
        "Three-lane acceptance binding drifted",
    )
    loaded_program = program or json.loads(
        (root / PROGRAM_PATH).read_text(encoding="utf-8")
    )
    criteria = _index(
        loaded_program.get("acceptanceCriteria"),
        "id",
        "Program acceptance criteria",
    )
    for acceptance_id, assessment in EXPECTED_ACCEPTANCE.items():
        criterion = criteria.get(acceptance_id)
        _require(
            isinstance(criterion, dict)
            and criterion.get("assessment") == assessment
            and EVIDENCE_ID in criterion.get("evidenceIds", []),
            f"Three-lane program acceptance projection drifted: {acceptance_id}",
        )
    evidence_index = _index(
        loaded_program.get("evidence"),
        "id",
        "Program evidence",
    )
    for evidence_id, expected in EXPECTED_ADDITIVE_PROGRAM_EVIDENCE.items():
        target_acceptance = expected["acceptanceId"]
        mapped = evidence_index.get(evidence_id)
        _require(
            isinstance(mapped, dict)
            and mapped.get("path") == expected["path"]
            and mapped.get("supports") == [target_acceptance]
            and not (
                set(mapped.get("supports", []))
                & FORBIDDEN_ADDITIVE_ACCEPTANCE_IDS
            ),
            f"Additive evidence program mapping drifted: {evidence_id}",
        )
        target = criteria.get(target_acceptance)
        _require(
            isinstance(target, dict)
            and target.get("assessment") == "partial"
            and target.get("evidenceIds", []).count(evidence_id) == 1,
            f"Additive evidence target must remain partial: {evidence_id}",
        )
        criterion_occurrences = [
            criterion_id
            for criterion_id, criterion in criteria.items()
            if evidence_id in criterion.get("evidenceIds", [])
        ]
        _require(
            criterion_occurrences == [target_acceptance],
            f"Additive evidence reverse mapping is not unique: {evidence_id}",
        )

    projected = evidence_index.get(EVIDENCE_ID)
    _require(
        isinstance(projected, dict)
        and projected.get("path") == RECONCILIATION_PATH
        and projected.get("kind")
        == (
            "verified-three-lane-reconciliation-including-context-delta-ledger-"
            "and-mcp-observer-auto-attach-v2-offline-boundaries-all-runtime-"
            "assessments-remain-partial"
        )
        and set(projected.get("supports", []))
        == set(EXPECTED_ACCEPTANCE),
        "Three-lane program evidence projection drifted",
    )

    decision = document.get("decision")
    _require(
        isinstance(decision, dict)
        and decision.get("dynamicRuntimeControlAssessmentRemainsPartial")
        is True
        and decision.get("nativeTaskOrchestrationAssessmentRemainsPartial")
        is True
        and decision.get("residualGapAssessmentRemainsPartial") is True
        and decision.get("selfAuthoredRuntimeControllerJustified") is False
        and decision.get("newOfflineSimulatorNeeded") is False
        and decision.get("nextEvidenceMustTargetANamedRemainingLiveGap")
        is True,
        "Three-lane decision boundary drifted",
    )
    cleanup = document.get("cleanupBoundary")
    _require(
        isinstance(cleanup, dict)
        and set(cleanup)
        == {
            "temporaryPreviewScopeUnchanged",
            "durableHostAndProcessFidelityAuditClassification",
            "cleanupAuthorityGrantedByThisReconciliation",
            "invalidCreatorCloseCalibrationRootsClassifiedAsCleanupDebt",
            "invalidCreatorCloseCalibrationDeletionAuthorizedByThisReconciliation",
            "cleanupInventoryMutationPerformedByThisReconciliation",
            "currentCleanupExecution",
        },
        "Three-lane cleanup boundary keys drifted",
    )
    cleanup_preview = json.loads(
        (root / CLEANUP_PATH).read_text(encoding="utf-8")
    )
    durable_audit = (
        root / "audits/process-fidelity-v2-source-backed-r2-2026-07-27"
    )
    reload_audit = (
        root
        / "audits/mcp-reload-release-attribution-0.145.0-2026-07-27"
    )
    unsubscribe_audit = (
        root
        / (
            "audits/mcp-thread-unsubscribe-release-attribution-0.145.0-"
            "2026-07-27"
        )
    )
    _require(
        isinstance(cleanup, dict)
        and cleanup.get("temporaryPreviewScopeUnchanged")
        == cleanup_preview.get("scope")
        == "repository-local-.tmp-top-level-roots-only"
        and cleanup.get("durableHostAndProcessFidelityAuditClassification")
        == "authoritative-evidence-retain"
        and cleanup.get("cleanupAuthorityGrantedByThisReconciliation")
        is False
        and cleanup.get(
            "invalidCreatorCloseCalibrationRootsClassifiedAsCleanupDebt"
        )
        == [
            ".tmp/mcp-creator-close-calibration-20260727-01",
            ".tmp/mcp-creator-close-calibration-workspace-20260727-01",
        ]
        and cleanup.get(
            "invalidCreatorCloseCalibrationDeletionAuthorizedByThisReconciliation"
        )
        is False
        and cleanup.get(
            "cleanupInventoryMutationPerformedByThisReconciliation"
        )
        is False
        and cleanup.get("currentCleanupExecution")
        == {
            "path": "registry/closeout-cleanup-execution-2026-07-30.json",
            "status": (
                "repository-local-temporary-debt-cleaned-stage-checkpoint"
            ),
            "exactTargetCount": 35,
            "creatorCloseCalibrationRootsAbsent": True,
            "programCloseoutProved": False,
        }
        and (root / "registry/closeout-cleanup-execution-2026-07-30.json").is_file()
        and all(
            not (root / relative).exists()
            for relative in cleanup.get(
                "invalidCreatorCloseCalibrationRootsClassifiedAsCleanupDebt",
                [],
            )
        )
        and durable_audit.is_dir()
        and {
            item.name for item in durable_audit.iterdir() if item.is_file()
        }
        == {
            "RAW-REPORT.json",
            "TRIAL-PACKET.json",
            "BUILD-MANIFEST.json",
            "PUBLIC-SOURCE-BUNDLE.json",
        },
        "Three-lane cleanup boundary drifted",
    )
    _require(
        unsubscribe_audit.is_dir()
        and {
            item.name
            for item in unsubscribe_audit.iterdir()
            if item.is_file()
        }
        == {
            "README.md",
            "calibration-01.json",
            "evidence-01.json",
            "evidence-02.json",
            "evidence-03.json",
        },
        "Three-lane cleanup boundary drifted",
    )
    _require(
        reload_audit.is_dir()
        and {
            item.name for item in reload_audit.iterdir() if item.is_file()
        }
        == {
            "README.md",
            "run-01.json",
            "formal-01.json",
            "formal-02.json",
            "formal-03.json",
            "evidence-01.json",
            "evidence-02.json",
            "evidence-03.json",
        },
        "Three-lane cleanup boundary drifted",
    )
    _require(
        document.get("documentation") == DOC_PATH
        and (root / DOC_PATH).is_file()
        and document.get("claimLimit") == EXPECTED_CLAIM_LIMIT,
        "Three-lane documentation binding drifted",
    )
    normalized = " ".join(
        (root / DOC_PATH).read_text(encoding="utf-8").split()
    )
    for phrase in (
        "acceptance criteria remain `partial`",
        "receiver delta ledger only to `acceptance.end-to-end-process-fidelity`",
        "observer-acquisition admission plus auto-attach v2 amendment only to `acceptance.dynamic-runtime-control-gap-research`",
        "no support edge to residual-gap, native-orchestration, value, or release acceptance",
        "automatic new-thread creation",
        "Disposable-repository evidence cannot be promoted",
        "not task-scoped same-thread lifecycle control",
        "all 33 exact process samples matched",
        "all 66 samples across six independent runtimes",
        "paired unsubscribe retention",
        "shared Context-Git projection",
        "not atomic build/create",
        "deterministic receiver delta ledger",
        "zero Agent dispatches and zero model calls",
        "not live receiver or weak-Agent evidence",
        "multi-connection preflight",
        "observer-acquisition gate",
        "Auto-attach callability is not admitted as a second subscription",
        "injected in-memory fake transports",
        "zero formal live runs",
        "does not prove live readiness",
        "creator-connection-close formal paired protocol therefore has not executed",
        "invalid pre-window prerequisite",
        "authority conflict",
        "no live rerun followed",
        "separate explicit user authorization",
        "cleanup debt and retained",
        "does not justify a self-authored runtime controller",
        "authoritative evidence to retain",
        "No cleanup authority is granted",
    ):
        _require(
            phrase in normalized,
            f"Three-lane documentation boundary missing: {phrase}",
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    root = args.root.resolve()
    document = json.loads(
        (root / RECONCILIATION_PATH).read_text(encoding="utf-8")
    )
    program = json.loads((root / PROGRAM_PATH).read_text(encoding="utf-8"))
    validate_reconciliation(document, root=root, program=program)
    print("Harness three-lane acceptance reconciliation validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
