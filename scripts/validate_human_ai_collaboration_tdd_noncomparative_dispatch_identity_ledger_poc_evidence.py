#!/usr/bin/env python3
"""Validate the offline TDD non-comparative dispatch-ledger PoC evidence."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_PATH = (
    "registry/"
    "human-ai-collaboration-tdd-noncomparative-dispatch-identity-ledger-"
    "poc-evidence-2026-07-26.json"
)
PROTOCOL_PATH = (
    "registry/"
    "human-ai-collaboration-tdd-noncomparative-treatment-diagnostic-"
    "protocol-2026-07-26.json"
)
DOCUMENTATION_PATH = (
    "docs/strategy/"
    "HUMAN-AI-COLLABORATION-TDD-NONCOMPARATIVE-DISPATCH-IDENTITY-LEDGER-"
    "POC-2026-07-26.md"
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def validate_evidence(
    document: dict[str, Any],
    *,
    root: Path = ROOT,
) -> None:
    _require(document.get("schema") == 1, "ledger PoC schema must be 1")
    _require(
        document.get("status")
        == "offline-ledger-construction-state-poc-validated-no-live-transition",
        "ledger PoC status drifted",
    )
    _require(
        document.get("parentProtocol") == PROTOCOL_PATH
        and (root / PROTOCOL_PATH).is_file(),
        "ledger PoC parent protocol binding drifted",
    )
    _require(
        document.get("routingBoundary")
        == {
            "implementation": "repository-local Python standard library",
            "externalSkillOrPluginExecution": False,
            "appServerOrModelUse": False,
            "candidateProjectionOrInstructionUse": False,
            "networkUse": False,
            "globalConfigurationOrCcSwitchMutation": False,
        },
        "ledger PoC routing boundary drifted",
    )
    artifacts = document.get("artifacts", [])
    expected_paths = {
        "scripts/human_ai_collaboration_tdd_noncomparative_dispatch_identity_ledger.py",
        "tests/test_human_ai_collaboration_tdd_noncomparative_dispatch_identity_ledger.py",
        "tests/test_human_ai_collaboration_tdd_noncomparative_resource_contract.py",
    }
    _require(
        isinstance(artifacts, list)
        and {item.get("path") for item in artifacts} == expected_paths,
        "ledger PoC artifact set drifted",
    )
    for artifact in artifacts:
        path = root / artifact["path"]
        _require(
            path.is_file()
            and artifact.get("bytes") == path.stat().st_size
            and artifact.get("sha256")
            == hashlib.sha256(path.read_bytes()).hexdigest(),
            f"ledger PoC artifact binding drifted: {artifact['path']}",
        )
    observation = document.get("testObservation", {})
    _require(
        observation
        == {
            "command": (
                "python -B -m unittest "
                "tests.test_human_ai_collaboration_tdd_noncomparative_"
                "dispatch_identity_ledger "
                "tests.test_human_ai_collaboration_tdd_noncomparative_"
                "resource_contract -v"
            ),
            "testsRun": 20,
            "failures": 0,
            "errors": 0,
            "result": "passed",
            "initialMissingModuleFailureObserved": True,
        },
        "ledger PoC test observation drifted",
    )
    _require(
        set(document.get("behaviors", []))
        == {
            "first reservation starts a SHA-256 event chain",
            "missing exact-candidate execution admission rejects before ledger creation",
            "stale source or toolchain identity rejects before ledger creation",
            "second candidate reservation and reservation-id replacement reject",
            "thread binding rejects until a construction-succeeded event exists, then thread and turn bindings are ordered and immutable",
            "event-content tampering fails hash validation",
            "a torn JSONL tail fails closed instead of being silently truncated",
            "two same-process threads racing for one candidate produce one reservation and one rejection",
            "a fresh reader classifies a reservation with no construction outcome as manual-recovery-required without automatic release or retry",
            "an exact manual missing-outcome reconciliation can only retain the consumed reservation and binds the reservation-event hash",
            "two distinct protocol-selected ledger authorities can each reserve the same candidate once, falsifying a system-global cap for the current PoC",
        },
        "ledger PoC behavior coverage drifted",
    )
    decision = document.get("decision", {})
    _require(
        decision
        == {
            "modulePocValidated": True,
            "appendOnlyHashChainUnitTested": True,
            "singleCandidateReservationCapUnitTested": True,
            "threadAndTurnIdentityImmutabilityUnitTested": True,
            "constructionSuccessBeforeThreadBindingUnitTested": True,
            "sameProcessThreadRaceUnitTested": True,
            "tornTailDetectionUnitTested": True,
            "missingConstructionOutcomeFreshReaderClassificationUnitTested": True,
            "missingOutcomeManualRetainConsumedReconciliationUnitTested": True,
            "twoAuthoritySameCandidateCounterexamplePinned": True,
            "dispatchCapScope": "protocol-selected-ledger-local",
            "currentPocSystemGlobalDispatchCapAbsent": True,
            "systemGlobalDispatchCapProved": False,
            "documentBoundPublicReservationEntryImplemented": True,
            "syntheticAdmissionRecordValidatedByGate": True,
            "unsafeBareBooleanPublicReservationEntryPresent": False,
            "currentRepositoryProtocolAuthorized": False,
            "formalRunnerIntegrationImplemented": False,
            "currentExactCandidateAdmissionSatisfied": False,
            "runtimeDispatchCapEnforcedForLiveRunner": False,
            "liveDiagnosticStarted": False,
            "nextBoundedAction": (
                "Keep construction success and manual retain-consumed "
                "reconciliation as offline lifecycle events. Before formal-"
                "runner integration, validate real app-server handle "
                "compatibility, real child-process or socket cleanup, cross-"
                "process exclusion, crash recovery, and live source-snapshot-"
                "to-factory freshness without weakening the ledger-local "
                "consumed dispatch cap."
            ),
        },
        "ledger PoC decision boundary drifted",
    )
    claims = document.get("claimBoundary", {})
    _require(
        set(claims)
        == {
            "candidateSkillInvoked",
            "modelRequestSent",
            "appServerProcessStarted",
            "currentProtocolConsumedAtRuntime",
            "currentExactCandidateExecutionEligible",
            "liveRunnerDispatchEnforcementProved",
            "crossProcessConcurrencyProved",
            "realAppServerHandleCompatibilityProved",
            "realChildProcessOrSocketCleanupProved",
            "crossProcessExactlyOnceCleanupProved",
            "crashRecoveryProved",
            "powerLossDurabilityProved",
            "hostThreadOrTurnIdentityObserved",
            "candidateBodyDeliveryProved",
            "candidateCausationOrValueProved",
            "productionReadinessProved",
            "crossHostPortabilityProved",
        }
        and all(value is False for value in claims.values()),
        "ledger PoC claim boundary was promoted",
    )
    _require(
        document.get("documentation") == DOCUMENTATION_PATH
        and (root / DOCUMENTATION_PATH).is_file(),
        "ledger PoC documentation binding drifted",
    )
    documentation = " ".join(
        (root / DOCUMENTATION_PATH).read_text(encoding="utf-8").split()
    )
    for phrase in (
        "Twenty ledger and resource-contract tests passed",
        "rejection of thread binding before an explicit `construction-succeeded` event",
        "proves detection and fail-closed behavior, not crash recovery",
        "does not prove cross-process exclusion",
        "not proof of power-loss durability",
        "public reservation entry now requires the document-bound authorization adapter",
        "raw boolean-bearing reservation core is private",
        "current repository protocol and dated preflight remain rejected",
        "not enforced for a live runner",
        "No candidate Skill was invoked",
        "protocol-selected-ledger-local",
        "two-authority same-candidate counterexample",
        "manual missing-outcome reconciliation",
        "real child-process or socket cleanup",
        "current candidate task turns remain blocked",
    ):
        _require(
            phrase in documentation,
            f"ledger PoC documentation boundary missing: {phrase}",
        )
    module_text = (
        root
        / "scripts/human_ai_collaboration_tdd_noncomparative_dispatch_identity_ledger.py"
    ).read_text(encoding="utf-8")
    _require(
        "def reserve_from_repository_documents(" in module_text
        and "def record_construction_success(" in module_text
        and "def reserve_candidate(" not in module_text
        and "def _reserve_candidate(" in module_text,
        "ledger public reservation surface drifted",
    )


def main() -> int:
    document = json.loads(
        (ROOT / EVIDENCE_PATH).read_text(encoding="utf-8")
    )
    validate_evidence(document)
    print("human-AI TDD noncomparative dispatch ledger PoC evidence: valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
