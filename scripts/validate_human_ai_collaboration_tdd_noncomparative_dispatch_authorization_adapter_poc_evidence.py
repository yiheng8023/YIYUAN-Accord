#!/usr/bin/env python3
"""Validate the offline TDD dispatch-authorization adapter PoC evidence."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_PATH = (
    "registry/"
    "human-ai-collaboration-tdd-noncomparative-dispatch-authorization-"
    "adapter-poc-evidence-2026-07-26.json"
)
PROTOCOL_PATH = (
    "registry/"
    "human-ai-collaboration-tdd-noncomparative-treatment-diagnostic-"
    "protocol-2026-07-26.json"
)
LEDGER_EVIDENCE_PATH = (
    "registry/"
    "human-ai-collaboration-tdd-noncomparative-dispatch-identity-ledger-"
    "poc-evidence-2026-07-26.json"
)
DOCUMENTATION_PATH = (
    "docs/strategy/"
    "HUMAN-AI-COLLABORATION-TDD-NONCOMPARATIVE-DISPATCH-AUTHORIZATION-"
    "ADAPTER-POC-2026-07-26.md"
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def validate_evidence(
    document: dict[str, Any],
    *,
    root: Path = ROOT,
) -> None:
    _require(document.get("schema") == 1, "adapter PoC schema must be 1")
    _require(
        document.get("status")
        == "offline-immutable-authorization-envelope-poc-validated-current-documents-rejected-no-live-runner",
        "adapter PoC status drifted",
    )
    _require(
        document.get("parentProtocol") == PROTOCOL_PATH
        and document.get("parentLedgerPocEvidence") == LEDGER_EVIDENCE_PATH
        and (root / PROTOCOL_PATH).is_file()
        and (root / LEDGER_EVIDENCE_PATH).is_file(),
        "adapter PoC parent binding drifted",
    )
    artifacts = document.get("artifacts", [])
    expected_paths = {
        "scripts/human_ai_collaboration_tdd_noncomparative_dispatch_authorization_adapter.py",
        "tests/test_human_ai_collaboration_tdd_noncomparative_dispatch_authorization_adapter.py",
        "scripts/human_ai_collaboration_tdd_noncomparative_dispatch_identity_ledger.py",
        "tests/test_human_ai_collaboration_tdd_noncomparative_preconstruction_transaction.py",
    }
    _require(
        isinstance(artifacts, list)
        and {item.get("path") for item in artifacts} == expected_paths,
        "adapter PoC artifact set drifted",
    )
    for artifact in artifacts:
        path = root / artifact["path"]
        _require(
            path.is_file()
            and artifact.get("bytes") == path.stat().st_size
            and artifact.get("sha256")
            == hashlib.sha256(path.read_bytes()).hexdigest(),
            f"adapter PoC artifact binding drifted: {artifact['path']}",
        )
    _require(
        document.get("testObservation")
        == {
            "command": (
                "python -B -m unittest "
                "tests.test_human_ai_collaboration_tdd_noncomparative_"
                "dispatch_authorization_adapter "
                "tests.test_human_ai_collaboration_tdd_noncomparative_"
                "dispatch_identity_ledger "
                "tests.test_human_ai_collaboration_tdd_noncomparative_"
                "preconstruction_transaction -v"
            ),
            "testsRun": 23,
            "failures": 0,
            "errors": 0,
            "result": "passed",
            "initialMissingAdapterModuleFailureObserved": True,
        },
        "adapter PoC test observation drifted",
    )
    _require(
        set(document.get("behaviors", []))
        == {
            "a digest-bound synthetic protocol, preflight, audit, admission, and ledger-authority bundle is captured once into one immutable authorization envelope",
            "the current repository protocol and preflight remain dispatch-ineligible",
            "stale source preflight rejects",
            "protocol, preflight, audit, or admission byte-digest mismatch rejects",
            "expired diagnostic admission rejects",
            "candidate identity mismatch rejects",
            "comparison authority rejects",
            "the ledger public entry consumes the exact immutable envelope without rereading mutable document paths before reservation",
            "post-envelope path drift cannot alter the envelope bytes, authorization digest, or selected ledger path",
        },
        "adapter PoC behavior coverage drifted",
    )
    _require(
        document.get("decision")
        == {
            "adapterPocValidated": True,
            "syntheticBoundBundleAccepted": True,
            "currentRepositoryDocumentsRejected": True,
            "currentExactCandidateExecutionEligible": False,
            "repositoryAdmissionRecordCreated": False,
            "freshDispatchPreflightCreated": False,
            "ledgerPublicDocumentEntryImplemented": True,
            "immutableAuthorizationEnvelopeImplemented": True,
            "authorizationEnvelopeToReservationDocumentDriftUnitTested": True,
            "sourceSnapshotToFactoryMaterializationFreshnessProved": False,
            "formalRunnerIntegrationImplemented": False,
            "appServerProcessStarted": False,
            "candidateTaskTurnStarted": False,
            "nextBoundedAction": (
                "Keep the immutable envelope confined to the offline wrapper. "
                "Before formal-runner integration, validate a real app-server "
                "handle adapter and live source-snapshot-to-factory "
                "materialization freshness; do not promote envelope-to-"
                "reservation consistency or same-process synthetic cleanup "
                "into live runtime proof."
            ),
        },
        "adapter PoC decision boundary drifted",
    )
    claims = document.get("claimBoundary", {})
    _require(
        set(claims)
        == {
            "realCandidateAdmissionProved",
            "realSourceFreshnessProved",
            "currentCandidateDispatchAuthorized",
            "liveRunnerIntegrationProved",
            "appServerPreconstructionOrderingProved",
            "liveSourceToFactoryMaterializationFreshnessProved",
            "candidateSkillInvoked",
            "modelRequestSent",
            "candidateBodyDeliveryProved",
            "runtimeDispatchCapEnforcedForLiveRunner",
            "productionReadinessProved",
            "crossHostPortabilityProved",
        }
        and all(value is False for value in claims.values()),
        "adapter PoC claim boundary was promoted",
    )
    _require(
        document.get("documentation") == DOCUMENTATION_PATH
        and (root / DOCUMENTATION_PATH).is_file(),
        "adapter PoC documentation binding drifted",
    )
    documentation = " ".join(
        (root / DOCUMENTATION_PATH).read_text(encoding="utf-8").split()
    )
    for phrase in (
        "no longer accepts admission and source-freshness booleans or a ledger path directly",
        "exactly once as immutable bytes",
        "ledger consumes that exact envelope rather than rereading mutable document paths",
        "Twenty-three adapter, ledger, and preconstruction-transaction tests passed",
        "post-envelope path mutation cannot change the captured bytes",
        "synthetic fixture is not a repository admission decision",
        "actual current repository protocol and preflight are explicitly rejected",
        "No real diagnostic admission record or dispatch-fresh preflight was created",
        "formal runner does not",
        "does not prove live source-to-factory materialization freshness",
        "structured handle validator",
        "same-process registered resource cleanup",
        "real app-server handle adapter",
    ):
        _require(
            phrase in documentation,
            f"adapter PoC documentation boundary missing: {phrase}",
        )


def main() -> int:
    document = json.loads(
        (ROOT / EVIDENCE_PATH).read_text(encoding="utf-8")
    )
    validate_evidence(document)
    print("human-AI TDD dispatch authorization adapter PoC evidence: valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
