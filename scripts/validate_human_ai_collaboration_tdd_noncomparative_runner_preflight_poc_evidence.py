#!/usr/bin/env python3
"""Validate the offline TDD non-comparative runner-preflight PoC."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_PATH = (
    "registry/"
    "human-ai-collaboration-tdd-noncomparative-runner-preflight-"
    "poc-evidence-2026-07-26.json"
)
PROTOCOL_PATH = (
    "registry/"
    "human-ai-collaboration-tdd-noncomparative-treatment-diagnostic-"
    "protocol-2026-07-26.json"
)
ADAPTER_EVIDENCE_PATH = (
    "registry/"
    "human-ai-collaboration-tdd-noncomparative-dispatch-authorization-"
    "adapter-poc-evidence-2026-07-26.json"
)
DOCUMENTATION_PATH = (
    "docs/strategy/"
    "HUMAN-AI-COLLABORATION-TDD-NONCOMPARATIVE-RUNNER-PREFLIGHT-"
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
    _require(
        document.get("schema") == 1,
        "runner-preflight PoC schema must be 1",
    )
    _require(
        document.get("status")
        == "offline-immutable-authorization-and-construction-state-poc-validated-current-documents-rejected-no-live-app-server",
        "runner-preflight PoC status drifted",
    )
    _require(
        document.get("parentProtocol") == PROTOCOL_PATH
        and document.get("parentAuthorizationAdapterPocEvidence")
        == ADAPTER_EVIDENCE_PATH
        and document.get("parentAuthorizationAdapterPocEvidenceSha256")
        == hashlib.sha256(
            (root / ADAPTER_EVIDENCE_PATH).read_bytes()
        ).hexdigest()
        and (root / PROTOCOL_PATH).is_file()
        and (root / ADAPTER_EVIDENCE_PATH).is_file(),
        "runner-preflight PoC parent binding drifted",
    )
    _require(
        document.get("routingBoundary")
        == {
            "implementation": (
                "repository-local Python standard library and injected fake "
                "factory"
            ),
            "realAppServerFactoryUsed": False,
            "appServerOrModelUse": False,
            "candidateProjectionOrInstructionUse": False,
            "networkUse": False,
            "globalConfigurationOrCcSwitchMutation": False,
        },
        "runner-preflight PoC routing boundary drifted",
    )
    artifacts = document.get("artifacts", [])
    expected_paths = {
        "scripts/human_ai_collaboration_tdd_noncomparative_runner_preflight.py",
        "tests/test_human_ai_collaboration_tdd_noncomparative_runner_preflight.py",
        "scripts/human_ai_collaboration_tdd_noncomparative_dispatch_authorization_adapter.py",
        "scripts/human_ai_collaboration_tdd_noncomparative_dispatch_identity_ledger.py",
        "tests/test_human_ai_collaboration_tdd_noncomparative_ledger_authority_and_reconciliation.py",
        "tests/test_human_ai_collaboration_tdd_noncomparative_preconstruction_transaction.py",
        "tests/test_human_ai_collaboration_tdd_noncomparative_resource_contract.py",
    }
    _require(
        isinstance(artifacts, list)
        and {item.get("path") for item in artifacts} == expected_paths,
        "runner-preflight PoC artifact set drifted",
    )
    for artifact in artifacts:
        path = root / artifact["path"]
        _require(
            path.is_file()
            and artifact.get("bytes") == path.stat().st_size
            and artifact.get("sha256")
            == hashlib.sha256(path.read_bytes()).hexdigest(),
            (
                "runner-preflight PoC artifact binding drifted: "
                f"{artifact['path']}"
            ),
        )
    _require(
        document.get("testObservation")
        == {
            "command": (
                "python -B -m unittest "
                "tests.test_human_ai_collaboration_tdd_noncomparative_"
                "runner_preflight "
                "tests.test_human_ai_collaboration_tdd_noncomparative_"
                "ledger_authority_and_reconciliation "
                "tests.test_human_ai_collaboration_tdd_noncomparative_"
                "preconstruction_transaction "
                "tests.test_human_ai_collaboration_tdd_noncomparative_"
                "resource_contract -v"
            ),
            "testsRun": 29,
            "failures": 0,
            "errors": 0,
            "result": "passed",
            "initialMissingRunnerPreflightModuleFailureObserved": True,
        },
        "runner-preflight PoC test observation drifted",
    )
    _require(
        set(document.get("behaviors", []))
        == {
            "the admitted synthetic protocol digest-binds one contained ledger-authority document and the wrapper exposes no caller-selected ledger path",
            "ledger-authority byte drift rejects before ledger creation",
            "protocol, preflight, audit, admission, and ledger-authority bytes are captured once in an immutable envelope that the ledger consumes without path rereads",
            "post-envelope document-path drift cannot alter the authorization used by reservation",
            "a synthetic authorized document bundle records and file-fsyncs the protocol-selected reservation before the injected fake factory is called",
            "the actual current document bundle rejects at the protocol-eligibility gate before ledger-authority resolution, factory call, or ledger creation",
            "a non-callable factory fails before authorization or reservation",
            "a successful injected factory appends construction-succeeded before its handle is returned and thread binding rejects before that event",
            "when failure-event append succeeds, an injected factory exception appends construction-failed without persisting the error text",
            "when failure-event append and registered cleanup both fail, even a hostile original factory exception remains primary and exposes secondary errors best-effort",
            "one required structured validator checks the handle exactly once and explicitly rejects falsey synthetic handles",
            "factory or validation failure cleans same-process registered resources once in LIFO order before recording the bounded failure class",
            "a success append error reads the ledger back: durable success transfers resource ownership while no durable outcome cleans resources and remains manual-recovery-required",
            "a manual reconciliation document can only retain the consumed reservation without release or retry",
            "a second dispatch for the reconciled candidate rejects before the factory is called",
            "two protocol-selected ledger authorities can each reserve the same candidate once, so the current PoC cap is ledger-local rather than system-global",
        },
        "runner-preflight PoC behavior coverage drifted",
    )
    _require(
        document.get("decision")
        == {
            "runnerPreflightPocValidated": True,
            "injectedFactoryOnly": True,
            "reservationBeforeInjectedFactoryUnitTested": True,
            "currentRepositoryDocumentsRejectedBeforeFactory": True,
            "protocolBoundLedgerAuthorityUnitTested": True,
            "callerSelectedLedgerPathRemoved": True,
            "constructionFailureStateUnitTested": True,
            "manualRetainConsumedReconciliationUnitTested": True,
            "immutableAuthorizationEnvelopeUnitTested": True,
            "authorizationEnvelopeToReservationDocumentDriftClosed": True,
            "sourceSnapshotToFactoryMaterializationFreshnessProved": False,
            "constructionSuccessStateUnitTested": True,
            "threadBindingBeforeConstructionSuccessRejected": True,
            "factoryPrimaryErrorPreservedWhenFailureEventAppendFails": True,
            "hostilePrimaryErrorPreservedAcrossSecondaryFailures": True,
            "injectedStructuredHandleValidatorUnitTested": True,
            "falseyHandlesRejectedByInjectedContract": True,
            "reservationScopedOwnedResourceRegistrarUnitTested": True,
            "sameProcessRegisteredCleanupLifoUnitTested": True,
            "successAppendDurableReadbackUnitTested": True,
            "reservedWithoutConstructionOutcomeClassifiedByFreshReader": True,
            "missingOutcomeManualRetainConsumedReconciliationUnitTested": True,
            "twoAuthoritySameCandidateCounterexamplePinned": True,
            "dispatchCapScope": "protocol-selected-ledger-local",
            "currentPocSystemGlobalDispatchCapAbsent": True,
            "systemGlobalDispatchCapProved": False,
            "realAppServerHandleCompatibilityProved": False,
            "realChildProcessOrSocketCleanupProved": False,
            "cleanupAfterProcessCrashProved": False,
            "crossProcessExactlyOnceCleanupProved": False,
            "liveLedgerAuthorityConfigured": False,
            "automaticReservationReleaseOrRetryImplemented": False,
            "currentCandidateDispatchAuthorized": False,
            "formalRunnerIntegrationImplemented": False,
            "appServerProcessStarted": False,
            "candidateTaskTurnStarted": False,
            "nextBoundedAction": (
                "Before formal-runner integration, bind a real app-server "
                "handle adapter and real resource ownership contract, then "
                "test live source-snapshot-to-factory freshness, cross-process "
                "exclusion, and crash or kill recovery. Keep the current "
                "ledger-local cap and manual retain-consumed fallback explicit."
            ),
        },
        "runner-preflight PoC decision boundary drifted",
    )
    claims = document.get("claimBoundary", {})
    _require(
        set(claims)
        == {
            "realCandidateAdmissionProved",
            "realSourceFreshnessProved",
            "liveAppServerPreconstructionOrderingProved",
            "realAppServerFactoryCompatibilityProved",
            "candidateSkillInvoked",
            "modelRequestSent",
            "candidateBodyDeliveryProved",
            "threadOrTurnBindingProved",
            "liveLedgerAuthorityConfigurationProved",
            "crossProcessExclusionProved",
            "processCrashDurabilityProved",
            "powerLossDurabilityProved",
            "liveSourceSnapshotToFactoryMaterializationFreshnessProved",
            "realAppServerHandleCompatibilityProved",
            "realChildProcessOrSocketCleanupProved",
            "cleanupAfterProcessCrashProved",
            "crossProcessExactlyOnceCleanupProved",
            "systemGlobalDispatchCapProved",
            "automaticCrashRecoveryProved",
            "runtimeDispatchCapEnforcedForLiveRunner",
            "productionReadinessProved",
            "crossHostPortabilityProved",
        }
        and all(value is False for value in claims.values()),
        "runner-preflight PoC claim boundary was promoted",
    )
    _require(
        document.get("documentation") == DOCUMENTATION_PATH
        and (root / DOCUMENTATION_PATH).is_file(),
        "runner-preflight PoC documentation binding drifted",
    )
    documentation = " ".join(
        (root / DOCUMENTATION_PATH).read_text(encoding="utf-8").split()
    )
    for phrase in (
        "Twenty-nine wrapper, authority/reconciliation, preconstruction-transaction, and resource-contract tests passed",
        "no longer accepts a ledger path from its caller",
        "digest-binds one contained ledger-authority document",
        "freezes those exact bytes",
        "ledger consumes that exact envelope without rereading mutable source paths",
        "post-envelope path mutation",
        "fake factory reads the ledger and observes its own reservation already present",
        "`construction-succeeded` before its handle is returned",
        "thread binding rejects until that event exists",
        "same-process, protocol-selected-ledger and construction-state ordering",
        "actual current document bundle rejects at the protocol-eligibility gate",
        "does not dynamically reach the later preflight-freshness gate",
        "failure-event append succeeds",
        "original factory exception remains primary",
        "secondary errors best-effort",
        "retain-consumed-no-retry",
        "neither releases the reservation nor authorizes replacement",
        "Only an injected fake factory was used",
        "not integrated into the formal runner",
        "no live ledger authority is configured",
        "power-loss durability",
        "live source-snapshot-to-factory freshness",
        "structured handle validator",
        "same-process registered resources once in LIFO order",
        "durable success is confirmed by ledger readback",
        "reserved-without-construction-outcome",
        "manual-recovery-required",
        "Two protocol-selected ledger authorities",
        "protocol-selected-ledger-local",
        "system-global cap",
        "real child-process or socket cleanup",
    ):
        _require(
            phrase in documentation,
            (
                "runner-preflight PoC documentation boundary missing: "
                f"{phrase}"
            ),
        )


def main() -> int:
    document = json.loads(
        (ROOT / EVIDENCE_PATH).read_text(encoding="utf-8")
    )
    validate_evidence(document)
    print("human-AI TDD non-comparative runner-preflight PoC: valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
