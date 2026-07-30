#!/usr/bin/env python3
"""Validate the TDD non-comparative dispatch successor contract v2."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    from .build_human_ai_collaboration_tdd_noncomparative_dispatch_bundle_v2 import (
        CONTRACT_PATH,
        PARENT_PROTOCOL_PATH,
        ROOT,
        canonical_sha256,
        file_sha256,
        load_contract,
        validate_contract_source_bindings,
    )
except ImportError:  # pragma: no cover - direct script execution
    from build_human_ai_collaboration_tdd_noncomparative_dispatch_bundle_v2 import (
        CONTRACT_PATH,
        PARENT_PROTOCOL_PATH,
        ROOT,
        canonical_sha256,
        file_sha256,
        load_contract,
        validate_contract_source_bindings,
    )


DOCUMENTATION_PATH = Path(
    "docs/strategy/"
    "HUMAN-AI-COLLABORATION-TDD-NONCOMPARATIVE-DISPATCH-"
    "SUCCESSOR-CONTRACT-V2-2026-07-27.md"
)
EXPECTED_DOCUMENTATION_BYTES = 7490
EXPECTED_DOCUMENTATION_SHA256 = (
    "fdac53aa55b2015479af9e985dc329900e967722e2f283084f3227087d82494d"
)
EXPECTED_HEADER = {
    "schema": 1,
    "id": (
        "human-ai-collaboration-tdd-noncomparative-dispatch-"
        "successor-contract-v2-2026-07-27"
    ),
    "date": "2026-07-27",
    "status": "offline-successor-contract-preregistered-live-no-go",
}
EXPECTED_PURPOSE = (
    "Preregister a fail-closed successor boundary for one possible future "
    "non-comparative TDD diagnostic without rewriting historical evidence, "
    "materializing a candidate, creating a live ledger, starting Codex "
    "app-server, or sending a model request."
)
EXPECTED_TOP_LEVEL_KEYS = {
    "schema",
    "id",
    "date",
    "status",
    "purpose",
    "sourceBindings",
    "historicalEvidenceBoundary",
    "knownHistoricalIncompatibilities",
    "normalizedDispatchPolicy",
    "candidateBindings",
    "controlBundleContract",
    "sourceSnapshotContract",
    "freshPreflightContract",
    "separateAuthorityGrantContract",
    "authorizationEnvelopeContract",
    "ledgerAuthorityContract",
    "atomicTransitionOrder",
    "stateMachine",
    "failureAndRecoveryPolicy",
    "runnerPolicyBoundary",
    "authorityBoundary",
    "decision",
    "claimBoundary",
    "documentation",
}
EXPECTED_SOURCE_BINDINGS = {
    PARENT_PROTOCOL_PATH: (
        16323,
        "80086509febcf37665b301ed43d856ce087a30349ca85f7be81a1dfb47bf12f1",
        "historical-parent-noncomparative-protocol",
        True,
    ),
    (
        "registry/human-ai-collaboration-tdd-noncomparative-treatment-"
        "diagnostic-source-governance-preflight-2026-07-26.json"
    ): (
        9332,
        "cc6f265eeca164b3f26cfa020976776242a4f95a06deff9a9e88b4167f4866cd",
        "historical-dated-source-toolchain-observation",
        True,
    ),
    (
        "registry/human-ai-collaboration-tdd-exact-candidate-admission-"
        "gap-audit-2026-07-26.json"
    ): (
        18674,
        "7b9371ef23de7dce3e3c96ffc4595796e519c30736705012b05b467b3d7efef1",
        "historical-static-gap-audit",
        True,
    ),
    (
        "registry/human-ai-collaboration-tdd-matt-current-diagnostic-"
        "only-admission-decision-2026-07-27.json"
    ): (
        13359,
        "8b12683f86dcecffac5cfd398061f194ccc08578b04247e7631c03a922b131e4",
        "matt-static-identity-governance-admission",
        True,
    ),
    (
        "registry/human-ai-collaboration-tdd-superpowers-620-"
        "diagnostic-only-admission-decision-2026-07-27.json"
    ): (
        14016,
        "aa763b96a461b1f6a85d4d8329612eee536923c04bf7ba48ac057b75e83c2376",
        "superpowers-static-identity-governance-admission",
        True,
    ),
    (
        "registry/human-ai-collaboration-tdd-current-execution-"
        "readiness-reconciliation-2026-07-27.json"
    ): (
        17774,
        "af8ab74c690e86ce79d9a882603ed75e5765def60509afb1b072c332568a5a53",
        "current-blocked-readiness-reconciliation",
        False,
    ),
    (
        "scripts/human_ai_collaboration_tdd_noncomparative_dispatch_"
        "authorization_adapter.py"
    ): (
        14624,
        "a146a95c3e37827e9969cc0bcde2652c01547e19ad44ae2deadad398d5cc454c",
        "historical-authorization-adapter-poc",
        True,
    ),
    (
        "scripts/human_ai_collaboration_tdd_noncomparative_dispatch_"
        "identity_ledger.py"
    ): (
        49057,
        "c8625d78bd3ae93aea6c7a41eed5981670797f9d49be9a3e1d5124be7103e1e6",
        "historical-identity-ledger-poc",
        True,
    ),
    (
        "scripts/human_ai_collaboration_tdd_noncomparative_runner_"
        "preflight.py"
    ): (
        8640,
        "d3aeb2508b7214ce1786f88f79987b0d677e9d8f4c47166cfef453f5f90e6f15",
        "historical-runner-preflight-poc",
        True,
    ),
    "scripts/run_human_ai_collaboration_tdd_formal_trial.py": (
        24396,
        "e3550b937cfd301a0bd2468c21fe67582a0b3ebceef0f61fbbeccfa0de4e4f80",
        "excluded-formal-policy-shell",
        True,
    ),
}
EXPECTED_HISTORY_BOUNDARY = {
    "historyRewriteAllowed": False,
    "historicalProtocolAdapterLedgerRunnerRemainUnchanged": True,
    "historicalStaticGovernanceIsDispatchFreshness": False,
    "historicalStaticGovernanceIsCurrentAuthority": False,
    "historicalFormalRunnerIsDiagnosticPolicyShell": False,
    "successorConsumesHistoricalEvidenceAsBaselineOnly": True,
}
EXPECTED_POLICY = {
    "maximumDispatchesPerCandidate": 1,
    "maximumDispatchesTotal": 2,
    "replacementAllowed": False,
    "comparisonAllowed": False,
    "scoreProduced": False,
    "formalAcceptanceContribution": False,
    "candidateOrderHasMeaning": False,
    "automaticReleaseAllowed": False,
    "automaticRetryAllowed": False,
    "manualReconciliationRequired": True,
}
EXPECTED_CANDIDATES = {
    "tdd.matt.current": (
        "5d7376eefd8d581452778c637814065d309e07966faf998b575d54d7e6812f67",
        (
            "registry/human-ai-collaboration-tdd-matt-current-"
            "diagnostic-only-admission-decision-2026-07-27.json"
        ),
        "8b12683f86dcecffac5cfd398061f194ccc08578b04247e7631c03a922b131e4",
    ),
    "tdd.superpowers.6.2.0": (
        "005b8090affe1c685ce37325d2c7fb8509e97a537ee4b488f393473d6c079c51",
        (
            "registry/human-ai-collaboration-tdd-superpowers-620-"
            "diagnostic-only-admission-decision-2026-07-27.json"
        ),
        "aa763b96a461b1f6a85d4d8329612eee536923c04bf7ba48ac057b75e83c2376",
    ),
}
EXPECTED_INCOMPATIBILITIES = [
    {
        "id": "incompat.replacement-field",
        "historicalProtocolField": (
            "diagnosticDesign.replacementDispatchesAllowed"
        ),
        "historicalAdapterField": (
            "diagnosticDesign.replacementDispatchAllowed"
        ),
        "successorRule": (
            "replacementAllowed is the only normalized successor field; the "
            "singular historical alias is rejected."
        ),
    },
    {
        "id": "incompat.static-audit-versus-fresh-preflight",
        "historicalFact": (
            "The static gap audit permanently binds the dated preflight, "
            "while the historical adapter requires that audit binding to "
            "equal the dispatch-time fresh preflight."
        ),
        "successorRule": (
            "Static governance, dispatch-time freshness, and independent "
            "authority are separate evidence layers; the historical audit "
            "and adapter are not reused as current dispatch documents."
        ),
    },
    {
        "id": "incompat.post-response-ledger-binding",
        "historicalFact": (
            "The historical ledger binds host thread and turn identities "
            "only after host responses."
        ),
        "successorRule": (
            "Durable thread-start-intent and turn-start-intent events "
            "precede host calls; ambiguous outcomes remain consumed with no "
            "automatic retry."
        ),
    },
    {
        "id": "incompat.formal-policy-and-resource-owner",
        "historicalFact": (
            "The formal runner counts valid output toward weak-Agent "
            "acceptance, and the runner preflight transfers a raw successful "
            "handle without exposing its cleanup owner."
        ),
        "successorRule": (
            "The formal policy shell is excluded; a later diagnostic runner "
            "or shared transport must return an explicit closeable owner and "
            "persist resources-closed."
        ),
    },
]
EXPECTED_ATOMIC_ORDER = [
    "validate-static-contract-history-and-candidate-identity",
    "capture-one-control-bundle-and-ledger-authority",
    "capture-exact-source-snapshot-and-toolchain",
    "persist-and-revalidate-fresh-preflight",
    "wait-for-independent-authority-grant",
    "freeze-canonical-authorization-envelope",
    "atomically-write-candidate-reservation",
    "materialize-candidate-from-snapshot-only",
    "validate-projection-and-persist-materialization-succeeded",
    "construct-and-validate-closeable-app-server-owner",
    "persist-construction-succeeded",
    "persist-thread-start-intent-before-thread-start",
    "bind-host-thread-id-after-thread-start",
    "persist-turn-start-intent-before-turn-start",
    "bind-host-turn-id-after-turn-start",
    "persist-terminal-outcome",
    "close-or-abort-owner-and-persist-resources-closed",
]
EXPECTED_CONTROL_BUNDLE_CONTRACT = {
    "builderPath": (
        "scripts/build_human_ai_collaboration_tdd_"
        "noncomparative_dispatch_bundle_v2.py"
    ),
    "builderIsPureReadOnly": True,
    "builderMayIssueAuthorityGrant": False,
    "inputDocuments": [
        "sourceSnapshotManifest",
        "freshPreflight",
        "separateAuthorityGrant",
        "ledgerAuthority",
    ],
    "missingAuthorityGrantDecision": "NO-GO",
    "validOfflineBundleDecision": (
        "offline-structure-consistent-authority-unverified-live-no-go"
    ),
    "liveDispatchEligibleFromOfflineBundle": False,
    "forbiddenEffects": [
        "account-or-private-data-access",
        "app-server-start",
        "candidate-instruction-execution",
        "candidate-materialization",
        "cc-switch-read-or-mutation",
        "external-write",
        "git-operation",
        "global-configuration-read-or-change",
        "ledger-creation-or-append",
        "model-request",
        "network-or-source-fetch",
        "release-or-publication",
    ],
}
EXPECTED_SOURCE_SNAPSHOT_CONTRACT = {
    "schema": 1,
    "requiredFields": [
        "schema",
        "id",
        "candidateId",
        "candidateIdentitySha256",
        "capturedAt",
        "controlRoot",
        "trialRoot",
        "sourceFiles",
    ],
    "sourceFileFields": ["path", "bytes", "sha256"],
    "controlRootMustExist": True,
    "trialRootMustExist": True,
    "controlAndTrialRootsMustBeDisjoint": True,
    "linkOrPathEscapeAllowed": False,
    "sourceFilesMustExistAndMatchCandidateBytes": True,
    "sourceFileSetMustEqualParentCandidateFileSet": True,
    "materializerMayReadOnlySnapshotBytes": True,
    "remoteOrInstalledSourceRereadAfterFreezeAllowed": False,
}
EXPECTED_FRESH_PREFLIGHT_CONTRACT = {
    "schema": 1,
    "maximumAgeSeconds": 1200,
    "maximumSnapshotToPreflightSeconds": 1200,
    "requiredFields": [
        "schema",
        "id",
        "candidateId",
        "candidateIdentitySha256",
        "observedAt",
        "sourceSnapshotManifestSha256",
        "sourceFiles",
        "toolchain",
        "freshForDispatch",
        "freshRevalidationStillRequiredAtDispatch",
        "candidateMaterialized",
        "candidateInstructionExecuted",
        "appServerStarted",
        "threadStarted",
        "turnStarted",
        "modelRequestSent",
    ],
    "toolchainFields": [
        "codexExecutableSha256",
        "codexCliVersion",
        "expectedAppServerInterface",
        "projectionBuilderSha256",
        "normalizerSha256",
        "diagnosticRunnerCoreSha256",
    ],
    "freshForDispatchMustBeParentRecomputed": True,
    "toolchainAuthenticityVerifiedByBuilder": False,
    "freshRevalidationStillRequiredAtDispatch": False,
    "allExecutionFlagsBeforeGrant": False,
}
EXPECTED_GRANT_CONTRACT = {
    "schema": 1,
    "kind": "separate-user-runtime-authority-grant",
    "maximumTtlSeconds": 1200,
    "authorityEvidenceLocatorPrefixes": [
        "runtime-authority:",
        "user-confirmation:",
    ],
    "requiredFields": [
        "schema",
        "id",
        "kind",
        "authorityEvidenceLocator",
        "issuedAt",
        "validFrom",
        "validUntil",
        "sourceRevalidatedAt",
        "candidateId",
        "candidateIdentitySha256",
        "successorContractSha256",
        "parentProtocolSha256",
        "freshPreflightSha256",
        "sourceSnapshotManifestSha256",
        "staticAdmissionDecisionSha256",
        "ledgerAuthoritySha256",
        "authorizedEffects",
        "hostBinding",
        "maximumDispatches",
        "replacementAllowed",
        "comparisonAllowed",
        "formalAcceptanceContribution",
        "portfolioMutationAllowed",
    ],
    "authorizedEffects": [
        "app-server-construction",
        "candidate-materialization",
        "ledger-reservation",
        "one-ephemeral-thread",
        "one-model-turn",
    ],
    "hostBinding": {
        "interface": "Codex app-server",
        "model": "gpt-5.3-codex-spark",
        "effort": "low",
        "providerFallbackAllowed": False,
        "networkAllowed": False,
        "ephemeral": True,
    },
    "maximumDispatches": 1,
    "replacementAllowed": False,
    "comparisonAllowed": False,
    "formalAcceptanceContribution": False,
    "portfolioMutationAllowed": False,
    "grantMayBeSynthesizedByBuilder": False,
    "authorityAuthenticityVerifiedByBuilder": False,
    "clockAuthorityVerifiedByBuilder": False,
}
EXPECTED_AUTHORIZATION_ENVELOPE_CONTRACT = {
    "canonicalJsonSha256Required": True,
    "mustBindExactCandidate": True,
    "mustBindCurrentSuccessorContractBytes": True,
    "mustBindHistoricalParentProtocolBytes": True,
    "mustBindFreshPreflight": True,
    "mustBindSourceSnapshotManifest": True,
    "mustBindStaticAdmissionDecision": True,
    "mustBindSingleLedgerAuthority": True,
    "offlineBundleItselfAuthorizesLiveEffects": False,
}
EXPECTED_LEDGER_AUTHORITY_CONTRACT = {
    "schema": 1,
    "experimentId": (
        "human-ai-collaboration-tdd-noncomparative-diagnostic-v2"
    ),
    "candidateIds": [
        "tdd.matt.current",
        "tdd.superpowers.6.2.0",
    ],
    "authorityScope": "single-experiment-shared-two-candidate-authority",
    "maximumAuthorityAgeSeconds": 1200,
    "liveLedgerCreated": False,
    "reservationCreated": False,
    "authorityMustBeIndependentInput": True,
    "builderMayCreateOrAppendLedger": False,
    "authorityAuthenticityVerifiedByBuilder": False,
}
EXPECTED_STATE_MACHINE = {
    "statesInOrder": [
        "offline-no-go",
        "offline-structure-consistent-authority-unverified-live-no-go",
        "authority-envelope-frozen",
        "reservation-consumed",
        "materialization-succeeded",
        "construction-succeeded",
        "thread-start-intent",
        "thread-bound",
        "turn-start-intent",
        "turn-bound",
        "terminal-outcome",
        "resources-closed",
    ],
    "currentState": "offline-no-go",
    "offlineBuilderMaximumState": (
        "offline-structure-consistent-authority-unverified-live-no-go"
    ),
    "unknownHostOutcomeRetainsReservationConsumed": True,
}
EXPECTED_FAILURE_POLICY = {
    "failClosed": True,
    "automaticRetryAllowed": False,
    "automaticReservationReleaseAllowed": False,
    "unknownHostOutcome": (
        "retain-consumed-no-retry-manual-reconciliation"
    ),
    "projectionMismatch": (
        "retain-consumed-no-retry-manual-reconciliation"
    ),
    "cleanupErrorMayReplacePrimaryError": False,
    "resourcesClosedEventRequiredAfterSuccessOrFailure": True,
}
EXPECTED_RUNNER_POLICY_BOUNDARY = {
    "formalRunnerPath": "scripts/run_human_ai_collaboration_tdd_formal_trial.py",
    "formalRunnerPolicyShellExcluded": True,
    "formalRunnerCountsTowardWeakAcceptance": True,
    "noncomparativeDiagnosticCountsTowardWeakAcceptance": False,
    "futureAllowedShape": (
        "independent-diagnostic-runner-or-shared-transport-with-"
        "separate-policy-shell"
    ),
    "diagnosticScoreRankOrPreferenceAllowed": False,
}
EXPECTED_AUTHORITY_BOUNDARY = {
    "currentSeparateAuthorityGrantBound": False,
    "currentLiveLedgerAuthorityBound": False,
    "sourceSnapshotCapturedForDispatch": False,
    "freshDispatchPreflightCaptured": False,
    "candidateMaterializationAuthorized": False,
    "candidateExecutionAuthorized": False,
    "appServerStartAuthorized": False,
    "modelDispatchAuthorized": False,
    "networkSourceReadAuthorized": False,
    "portfolioMutationAuthorized": False,
    "liveReleaseAdmissionAuthorized": False,
    "separateLiveAuthorityStillRequired": True,
}
EXPECTED_DECISION = {
    "successorContractPreregistered": True,
    "pureOfflineBundleBuilderSpecified": True,
    "historicalEvidenceRewritten": False,
    "currentOfflineDecision": "NO-GO",
    "currentLiveDispatchEligible": False,
    "candidateMaterialized": False,
    "candidateInstructionExecuted": False,
    "appServerStarted": False,
    "modelRequestSent": False,
    "formalAcceptanceContribution": False,
    "nextBoundedAction": (
        "Validate this static successor contract and pure offline builder. "
        "Do not create a grant or live ledger. A later separately authorized "
        "slice may first establish one shared ledger authority, then capture "
        "a fresh source snapshot and preflight, accept one independent grant, "
        "and only then implement the diagnostic runner or shared transport "
        "controls."
    ),
}
EXPECTED_CLAIM_KEYS = {
    "realSourceFreshnessProved",
    "realToolchainFreshnessProved",
    "realAuthorityGrantObserved",
    "liveLedgerAuthorityObserved",
    "candidateMaterializationOccurred",
    "candidateSkillInvoked",
    "candidateBodyDeliveryProved",
    "modelRequestOccurred",
    "realAppServerOwnershipProved",
    "crashRecoveryProved",
    "crossProcessExclusionProved",
    "candidateValueProved",
    "candidatePreferenceProved",
    "candidateSuperiorityProved",
    "weakAgentAcceptanceAdvanced",
    "residualSelfAuthoredGapProved",
    "portfolioMutationAuthorized",
    "releaseAdmissionProved",
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _unique_rows(
    rows: Any,
    key: str,
    *,
    label: str,
) -> dict[str, dict[str, Any]]:
    _require(isinstance(rows, list), f"{label} must be a list")
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        _require(isinstance(row, dict), f"{label} row must be an object")
        value = row.get(key)
        _require(
            isinstance(value, str) and value and value not in result,
            f"{label} has an invalid or duplicate {key}",
        )
        result[value] = row
    return result


def _candidate_identity(candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        "candidateId": candidate["candidateId"],
        "sourceRevisionOrVersion": candidate["sourceRevisionOrVersion"],
        "licenseSha256": candidate["license"]["sha256"],
        "files": [
            {
                "path": item["path"],
                "sha256": item["sha256"],
            }
            for item in candidate["files"]
        ],
        "projectionTreeSha256": candidate["projectionTreeSha256"],
    }


def _validate_sources(contract: dict[str, Any], root: Path) -> None:
    validate_contract_source_bindings(contract, root=root)
    rows = _unique_rows(
        contract.get("sourceBindings"),
        "path",
        label="source bindings",
    )
    _require(
        set(rows) == set(EXPECTED_SOURCE_BINDINGS),
        "Source binding set drifted",
    )
    for path_text, (size, digest, role, immutable) in (
        EXPECTED_SOURCE_BINDINGS.items()
    ):
        row = rows[path_text]
        _require(
            row
            == {
                "path": path_text,
                "bytes": size,
                "sha256": digest,
                "role": role,
                "immutableHistoricalEvidence": immutable,
                "dispatchAuthority": False,
            },
            f"Source binding contract drifted: {path_text}",
        )


def _validate_candidates(contract: dict[str, Any], root: Path) -> None:
    parent = json.loads(
        (root / PARENT_PROTOCOL_PATH).read_text(encoding="utf-8")
    )
    parent_candidates = _unique_rows(
        parent.get("candidates"),
        "candidateId",
        label="parent candidates",
    )
    rows = _unique_rows(
        contract.get("candidateBindings"),
        "candidateId",
        label="candidate bindings",
    )
    _require(set(rows) == set(EXPECTED_CANDIDATES), "Candidate set drifted")
    for candidate_id, (
        identity_digest,
        admission_path,
        admission_digest,
    ) in EXPECTED_CANDIDATES.items():
        row = rows[candidate_id]
        _require(
            canonical_sha256(_candidate_identity(parent_candidates[candidate_id]))
            == identity_digest,
            f"Parent candidate identity drifted: {candidate_id}",
        )
        _require(
            row
            == {
                "candidateId": candidate_id,
                "candidateIdentitySha256": identity_digest,
                "staticAdmissionPath": admission_path,
                "staticAdmissionSha256": admission_digest,
                "staticDisposition": "admit-diagnostic-only",
                "currentMaterializationAuthorized": False,
                "currentExecutionAuthorized": False,
                "currentModelDispatchAuthorized": False,
            },
            f"Candidate binding drifted: {candidate_id}",
        )
        admission = json.loads(
            (root / admission_path).read_text(encoding="utf-8")
        )
        _require(
            file_sha256(root / admission_path) == admission_digest
            and admission.get("status")
            == "admit-diagnostic-only-current-dispatch-still-blocked"
            and admission.get("decision", {}).get("disposition")
            == "admit-diagnostic-only"
            and admission.get("decision", {}).get(
                "candidateMaterializationAuthorizedNow"
            )
            is False
            and admission.get("decision", {}).get(
                "candidateExecutionAuthorizedNow"
            )
            is False
            and admission.get("decision", {}).get(
                "modelDispatchAuthorizedNow"
            )
            is False,
            f"Static admission boundary drifted: {candidate_id}",
        )


def _validate_contract_shapes(contract: dict[str, Any]) -> None:
    _require(
        contract.get("historicalEvidenceBoundary")
        == EXPECTED_HISTORY_BOUNDARY,
        "Historical evidence boundary drifted",
    )
    _require(
        contract.get("knownHistoricalIncompatibilities")
        == EXPECTED_INCOMPATIBILITIES,
        "Historical incompatibility contract drifted",
    )
    _require(
        contract.get("normalizedDispatchPolicy") == EXPECTED_POLICY,
        "Normalized dispatch policy drifted",
    )
    _require(
        contract.get("controlBundleContract")
        == EXPECTED_CONTROL_BUNDLE_CONTRACT,
        "Control-bundle contract drifted",
    )
    _require(
        contract.get("sourceSnapshotContract")
        == EXPECTED_SOURCE_SNAPSHOT_CONTRACT,
        "Source-snapshot contract drifted",
    )
    _require(
        contract.get("freshPreflightContract")
        == EXPECTED_FRESH_PREFLIGHT_CONTRACT,
        "Fresh-preflight contract drifted",
    )
    _require(
        contract.get("separateAuthorityGrantContract")
        == EXPECTED_GRANT_CONTRACT,
        "Separate authority-grant contract drifted",
    )
    _require(
        contract.get("authorizationEnvelopeContract")
        == EXPECTED_AUTHORIZATION_ENVELOPE_CONTRACT,
        "Authorization-envelope contract drifted",
    )
    _require(
        contract.get("ledgerAuthorityContract")
        == EXPECTED_LEDGER_AUTHORITY_CONTRACT,
        "Ledger-authority contract drifted",
    )
    _require(
        contract.get("atomicTransitionOrder") == EXPECTED_ATOMIC_ORDER,
        "Atomic transition order drifted",
    )
    _require(
        contract.get("stateMachine") == EXPECTED_STATE_MACHINE,
        "State machine drifted",
    )
    _require(
        contract.get("failureAndRecoveryPolicy") == EXPECTED_FAILURE_POLICY,
        "Failure and recovery policy drifted",
    )
    _require(
        contract.get("runnerPolicyBoundary")
        == EXPECTED_RUNNER_POLICY_BOUNDARY,
        "Runner policy boundary drifted",
    )


def _validate_decision_and_claims(contract: dict[str, Any]) -> None:
    _require(
        contract.get("authorityBoundary") == EXPECTED_AUTHORITY_BOUNDARY,
        "Authority boundary drifted",
    )
    _require(
        contract.get("decision") == EXPECTED_DECISION,
        "Decision boundary drifted",
    )
    claims = contract.get("claimBoundary")
    _require(
        isinstance(claims, dict)
        and set(claims) == EXPECTED_CLAIM_KEYS
        and all(value is False for value in claims.values()),
        "Claim boundary drifted",
    )
    _require(
        contract.get("documentation") == DOCUMENTATION_PATH.as_posix(),
        "Documentation binding drifted",
    )


def _validate_documentation(root: Path) -> None:
    path = root / DOCUMENTATION_PATH
    _require(
        path.is_file(),
        "Documentation file is missing",
    )
    _require(
        path.stat().st_size == EXPECTED_DOCUMENTATION_BYTES,
        "Documentation bytes drifted",
    )
    _require(
        file_sha256(path) == EXPECTED_DOCUMENTATION_SHA256,
        "Documentation hash drifted",
    )
    text = path.read_text(encoding="utf-8")
    for marker in (
        "offline-successor-contract-preregistered-live-no-go",
        "three evidence layers",
        "thread-start-intent",
        "turn-start-intent",
        "formal weak-acceptance policy shell",
        "explicit closeable owner",
        "does not authorize",
    ):
        _require(marker in text, f"Documentation marker is missing: {marker}")


def validate_contract(
    contract: dict[str, Any],
    *,
    root: Path = ROOT,
) -> None:
    root = root.resolve()
    _require(
        {key: contract.get(key) for key in EXPECTED_HEADER}
        == EXPECTED_HEADER,
        "Contract header drifted",
    )
    _require(
        contract.get("purpose") == EXPECTED_PURPOSE,
        "Contract purpose drifted",
    )
    _require(
        set(contract) == EXPECTED_TOP_LEVEL_KEYS,
        "Contract top-level field set drifted",
    )
    _require(
        contract == load_contract(root),
        "Contract argument is not the repository-bound object",
    )
    _validate_sources(contract, root)
    _validate_candidates(contract, root)
    _validate_contract_shapes(contract)
    _validate_decision_and_claims(contract)
    _validate_documentation(root)


def main() -> int:
    validate_contract(load_contract(ROOT), root=ROOT)
    print("TDD non-comparative dispatch successor contract v2: valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
