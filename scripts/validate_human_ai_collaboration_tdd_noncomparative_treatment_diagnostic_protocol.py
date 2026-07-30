#!/usr/bin/env python3
"""Validate the bounded non-comparative TDD treatment diagnostic protocol."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
PROTOCOL_PATH = (
    "registry/"
    "human-ai-collaboration-tdd-noncomparative-treatment-diagnostic-"
    "protocol-2026-07-26.json"
)
DOCUMENTATION_PATH = (
    "docs/strategy/"
    "HUMAN-AI-COLLABORATION-TDD-NONCOMPARATIVE-TREATMENT-DIAGNOSTIC-"
    "PROTOCOL-2026-07-26.md"
)
PARENT_PATH = (
    "registry/human-ai-collaboration-new-feature-tdd-protocol-2026-07-26.json"
)
PREFLIGHT_PATH = (
    "registry/"
    "human-ai-collaboration-new-feature-tdd-exposure-preflight-2026-07-26.json"
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _digest(value: Any, *, size: int = 64) -> bool:
    return (
        isinstance(value, str)
        and len(value) == size
        and all(character in "0123456789abcdef" for character in value)
    )


def _load(root: Path, path: str) -> dict[str, Any]:
    return json.loads((root / path).read_text(encoding="utf-8"))


def validate_protocol(
    document: dict[str, Any],
    *,
    root: Path = ROOT,
) -> None:
    _require(document.get("schema") == 1, "diagnostic schema must be 1")
    _require(
        document.get("status")
        == "preregistered-no-live-diagnostic-started-governance-gate-unsatisfied",
        "diagnostic status drifted or was promoted",
    )
    _require(
        document.get("parentProtocol") == PARENT_PATH
        and document.get("exposurePreflight") == PREFLIGHT_PATH
        and document.get("scenarioId") == "SE-IMPLEMENT-TDD-NEW-FEATURE-01",
        "parent protocol or scenario binding drifted",
    )
    parent = _load(root, PARENT_PATH)
    preflight = _load(root, PREFLIGHT_PATH)

    routing = document.get("routingDecision", {})
    _require(
        routing
        == {
            "shape": "parallel-independent-order-invariant",
            "currentPhase": "protocol-and-governance-preflight-only",
            "selectedCapabilities": [
                "repository-native validation",
                "existing source-pinned projection builder",
                "existing Codex app-server inventory and structured Skill input substrate",
                "existing raw-item normalizer v2",
            ],
            "excludedCapabilities": [
                "formal comparative runner",
                "full Matt workflow",
                "full Superpowers orchestration",
                "CC Switch mutation",
                "global Skill or Plugin configuration mutation",
                "MCP, App, Hook, browser, network, or external write execution",
            ],
        },
        "diagnostic routing decision drifted",
    )

    authority = document.get("authorityBoundary", {})
    _require(
        authority
        == {
            "repositoryProtocolWritesAuthorized": True,
            "readOnlyCandidateAndRegistryInspectionAuthorized": True,
            "projectLocalDisposableProjectionPreflightAuthorized": True,
            "liveThreadOrTurnAuthorizedByThisRecord": False,
            "candidateInstructionExecutionAuthorizedByThisRecord": False,
            "modelRequestAuthorizedByThisRecord": False,
            "installedCandidateMutationAuthorized": False,
            "globalSkillOrPluginConfigurationMutationAuthorized": False,
            "ccSwitchMutationAuthorized": False,
            "mcpAppHookOrBrowserUseAuthorized": False,
            "networkUseDuringDiagnosticAuthorized": False,
            "dependencyInstallAuthorized": False,
            "gitMutationAuthorized": False,
            "commitOrPushAuthorized": False,
            "portfolioMutationAuthorized": False,
        },
        "diagnostic authority boundary drifted",
    )

    host = document.get("hostBinding", {})
    _require(
        host.get("interface") == "Codex app-server"
        and host.get("runtimeVersion") == "0.145.0"
        and host.get("model") == "gpt-5.3-codex-spark"
        and host.get("reasoningEffort") == "low"
        and host.get("providerFallbackAllowed") is False
        and host.get("approvalPolicy") == "never"
        and host.get("sandbox") == "workspaceWrite"
        and host.get("networkAllowed") is False
        and host.get("ephemeralThreadRequired") is True
        and host.get("allNonselectedConfigurableSkillsDisabled") is True
        and host.get("pluginFeaturesDisabled") is True
        and host.get("staticMcpStartupDisabled") is True,
        "diagnostic host binding drifted",
    )

    design = document.get("diagnosticDesign", {})
    _require(
        design.get("maximumDispatchesPerCandidate") == 1
        and design.get("maximumDispatchesTotal") == 2
        and design.get("replacementDispatchesAllowed") is False,
        "diagnostic dispatch cap drifted",
    )
    _require(
        design
        == {
            "candidateCount": 2,
            "maximumDispatchesPerCandidate": 1,
            "maximumDispatchesTotal": 2,
            "replacementDispatchesAllowed": False,
            "controlArmPresent": False,
            "scoreProduced": False,
            "pairwiseComparisonAllowed": False,
            "rankingAllowed": False,
            "winnerSelectionAllowed": False,
            "formalAcceptanceContribution": False,
            "candidateOrderHasMeaning": False,
            "candidateDiagnosticsIndependent": True,
            "sharedFixtureAndHardAcceptanceFrozen": True,
            "abortBothOnSharedControlPlaneDrift": True,
        },
        "diagnostic noncomparative design drifted",
    )

    runtime = document.get("runtimeEnforcement", {})
    _require(
        runtime.get("runnerConsumesThisProtocol") is False
        and runtime.get("dispatchLedgerExists") is False
        and runtime.get("singleDispatchCapRuntimeEnforced") is False
        and runtime.get("replacementDispatchRuntimeBlocked") is False
        and runtime.get("sharedControlPlaneAbortRuntimeEnforced") is False
        and runtime.get("currentSafetyDependsOnLiveAuthorityRemainingFalse")
        is True
        and runtime.get(
            "liveTransitionRequiresTestedRunnerAndAppendOnlyIdentityLedger"
        )
        is True
        and "not current runtime enforcement"
        in str(runtime.get("claimLimit")),
        "diagnostic runtime enforcement boundary drifted",
    )

    parent_candidates = {
        candidate.get("candidateId"): candidate
        for candidate in parent.get("projectionCandidates", [])
        if isinstance(candidate, dict)
    }
    preflight_candidates = {
        candidate.get("candidateId"): candidate
        for candidate in preflight.get("candidateEvidence", [])
        if isinstance(candidate, dict)
    }
    candidates = {
        candidate.get("candidateId"): candidate
        for candidate in document.get("candidates", [])
        if isinstance(candidate, dict)
    }
    _require(
        set(candidates)
        == {"tdd.matt.current", "tdd.superpowers.6.2.0"}
        == set(parent_candidates)
        == set(preflight_candidates),
        "diagnostic candidate set drifted",
    )
    for candidate_id, candidate in candidates.items():
        parent_candidate = parent_candidates[candidate_id]
        preflight_candidate = preflight_candidates[candidate_id]
        expected_files = preflight_candidate.get("projectedFiles")
        _require(
            candidate.get("armId") == preflight_candidate.get("armId")
            and candidate.get("skillName")
            == preflight_candidate.get("skillName")
            and candidate.get("sourceClass")
            == preflight_candidate.get("sourceClass")
            and candidate.get("sourceRevisionOrVersion")
            == preflight_candidate.get("sourceRevisionOrVersion")
            and candidate.get("files") == expected_files
            and candidate.get("license") == preflight_candidate.get("license")
            and candidate.get("projectionTreeSha256")
            == preflight_candidate.get("projection", {}).get(
                "projectedTreeSha256"
            )
            and candidate.get("selectionPreflightFileSha256")
            == preflight_candidate.get("preflight", {}).get(
                "reportFileSha256"
            ),
            f"diagnostic candidate source binding drifted: {candidate_id}",
        )
        _require(
            _digest(candidate.get("projectionTreeSha256"))
            and _digest(candidate.get("selectionPreflightFileSha256"))
            and all(
                _digest(item.get("sha256"))
                and _digest(item.get("gitBlobSha1"), size=40)
                and isinstance(item.get("bytes"), int)
                and item["bytes"] > 0
                for item in candidate.get("files", [])
            )
            and parent_candidate.get("skillName") == candidate.get("skillName"),
            f"diagnostic candidate source binding malformed: {candidate_id}",
        )

    matt_governance = candidates["tdd.matt.current"].get("governance", {})
    superpowers_governance = candidates[
        "tdd.superpowers.6.2.0"
    ].get("governance", {})
    _require(
        matt_governance.get("relatedApprovedHistoricalOrAdaptedEntryExists")
        is True
        and matt_governance.get("repositoryApprovedReleaseEntry") is False
        and matt_governance.get("exactProjectionIsApprovedReleasePayload")
        is False
        and matt_governance.get("executionEligibleAtPreregistration") is False
        and "different bytes" in str(matt_governance.get("blockingReason"))
        and superpowers_governance.get(
            "relatedApprovedHistoricalOrAdaptedEntryExists"
        )
        is False
        and superpowers_governance.get("repositoryApprovedReleaseEntry")
        is False
        and superpowers_governance.get(
            "exactProjectionIsApprovedReleasePayload"
        )
        is False
        and superpowers_governance.get("executionEligibleAtPreregistration")
        is False
        and "not this repository's approved release admission"
        in str(superpowers_governance.get("blockingReason")),
        "diagnostic governance boundary drifted",
    )

    skills = _load(root, "registry/skills.json").get("skills", [])
    admissions = _load(root, "registry/admissions.json").get("admissions", [])
    release_files = _load(root, "release-manifest.json").get("files", [])
    approved_tdd = next(
        (
            skill
            for skill in skills
            if skill.get("id") == "skill.curated.tdd"
        ),
        None,
    )
    admitted_tdd = next(
        (
            admission
            for admission in admissions
            if admission.get("skill") == "skill.curated.tdd"
        ),
        None,
    )
    release_tdd = next(
        (
            item
            for item in release_files
            if item.get("path") == "skills/tdd/SKILL.md"
        ),
        None,
    )
    current_matt_skill = candidates["tdd.matt.current"]["files"][0]
    _require(
        isinstance(approved_tdd, dict)
        and approved_tdd.get("status") == "approved"
        and approved_tdd.get("source") == "github:mattpocock/skills"
        and isinstance(admitted_tdd, dict)
        and admitted_tdd.get("disposition") == "approve"
        and admitted_tdd.get("validated") is True
        and isinstance(release_tdd, dict)
        and _digest(release_tdd.get("sha256"))
        and release_tdd.get("sha256") != current_matt_skill.get("sha256"),
        "diagnostic Matt release-lineage distinction drifted",
    )
    _require(
        not any(
            skill.get("name") == "test-driven-development"
            or "superpowers" in str(skill.get("source", "")).lower()
            for skill in skills
        )
        and not any(
            "superpowers" in str(admission.get("source", "")).lower()
            or "test-driven-development"
            in str(admission.get("skill", "")).lower()
            for admission in admissions
        )
        and not any(
            str(item.get("path", "")).startswith(
                "skills/test-driven-development/"
            )
            for item in release_files
        ),
        "diagnostic Superpowers release admission unexpectedly appeared",
    )

    gates = document.get("preDispatchGates", {})
    for key in (
        "exactProjectionRematerializedAndReverifiedAtDispatch",
        "licenseProvenanceSecurityPortabilityOverlapAndValidationReviewRequired",
        "exactCandidateExecutionAdmissionRequired",
        "candidateSpecificSelectedMetadataReprovedInFreshProcess",
        "onlySelectedStructuredSkillInputContainsExactNameAndPath",
        "fixtureOracleHardAcceptanceAndNormalizerDigestsReverified",
        "modelEffortFallbackSandboxNetworkAndEphemeralSettingsReverified",
        "repositoryAndGlobalConfigurationBaselineCaptured",
        "rawItemCaptureEnabledBeforeTurn",
        "testedRunnerAndAppendOnlyIdentityLedgerRequired",
    ):
        _require(
            gates.get(key) is True,
            f"diagnostic pre-dispatch gate drifted: {key}",
        )
    _require(
        gates.get("currentExactCandidateExecutionAdmissionSatisfied") is False,
        "diagnostic pre-dispatch gate was prematurely satisfied",
    )

    observation = document.get("observationContract", {})
    _require(
        observation.get("normalizer")
        == "scripts/normalize_human_ai_collaboration_tdd_app_server_items.py"
        and observation.get("normalizerContractVersion")
        == "codex-app-server-tdd-normalizer-v2"
        and len(observation.get("absoluteCategoricalObservations", [])) >= 9
        and observation.get("taskOutcomeUse")
        == (
            "record absolute categorical feasibility only; never score, rank, "
            "compare, prefer, admit, reject, or mutate the portfolio"
        )
        and observation.get("bodyDeliveryInferenceFromMetadataAllowed")
        is False
        and observation.get(
            "independentLoaderInferenceFromStructuredInputAllowed"
        )
        is False,
        "diagnostic observation contract drifted",
    )

    stop_conditions = set(document.get("stopConditions", []))
    expected_stop_conditions = {
        "exact source, license, projected file, or projected-tree digest drift",
        "candidate-specific selected metadata is absent or ambiguous",
        "more than one configurable candidate Skill is enabled",
        "structured Skill input name or path does not match the exact selected projection",
        "model, effort, fallback, sandbox, network, ephemeral, plugin, or MCP setting drift",
        "fixture, private oracle, hard acceptance, or normalizer digest drift",
        "private oracle content reaches the task turn",
        "repository status or global configuration changes outside the disposable root",
        "unknown raw item type or opaque write prevents an ordered trace claim",
        "candidate exceeds its single-dispatch cap or a replacement dispatch is attempted",
        "candidate lacks exact execution-path admission at dispatch",
        "any result is converted into a score, ranking, pairwise comparison, preference, admission, rejection, or portfolio mutation",
    }
    _require(
        stop_conditions == expected_stop_conditions
        and len(document.get("stopConditions", []))
        == len(expected_stop_conditions),
        "diagnostic stop condition set drifted",
    )

    claims = document.get("claimBoundary", {})
    _require(
        len(claims) >= 13 and all(value is False for value in claims.values()),
        "diagnostic claim boundary was promoted",
    )
    decision = document.get("decision", {})
    _require(
        decision.get("protocolPreregistered") is True
        and decision.get("candidateCount") == 2
        and decision.get("maximumPossibleDispatches") == 2
        and decision.get("liveDiagnosticStarted") is False
        and decision.get("candidateExecutionAuthorizedByThisRecord") is False
        and decision.get("anyExactCandidateExecutionEligibleNow") is False
        and decision.get("governanceAdmissionStillRequired") is True
        and decision.get("sourceGovernancePreflightObserved") is True
        and decision.get("sourceGovernancePreflightEvidence")
        == (
            "registry/"
            "human-ai-collaboration-tdd-noncomparative-treatment-diagnostic-"
            "source-governance-preflight-2026-07-26.json"
        )
        and (root / decision["sourceGovernancePreflightEvidence"]).is_file()
        and _digest(decision.get("sourceGovernancePreflightFileSha256"))
        and hashlib.sha256(
            (
                root / decision["sourceGovernancePreflightEvidence"]
            ).read_bytes()
        ).hexdigest()
        == decision["sourceGovernancePreflightFileSha256"]
        and decision.get("exactCandidateAdmissionGapAuditCompleted") is True
        and decision.get("exactCandidateAdmissionGapAuditEvidence")
        == (
            "registry/"
            "human-ai-collaboration-tdd-exact-candidate-admission-gap-audit-"
            "2026-07-26.json"
        )
        and (root / decision["exactCandidateAdmissionGapAuditEvidence"]).is_file()
        and _digest(decision.get("exactCandidateAdmissionGapAuditFileSha256"))
        and hashlib.sha256(
            (
                root / decision["exactCandidateAdmissionGapAuditEvidence"]
            ).read_bytes()
        ).hexdigest()
        == decision["exactCandidateAdmissionGapAuditFileSha256"]
        and decision.get("candidateAdmissionDecisionMade") is False
        and decision.get("dispatchIdentityLedgerPocValidated") is True
        and decision.get("dispatchIdentityLedgerPocEvidence")
        == (
            "registry/"
            "human-ai-collaboration-tdd-noncomparative-dispatch-identity-"
            "ledger-poc-evidence-2026-07-26.json"
        )
        and (root / decision["dispatchIdentityLedgerPocEvidence"]).is_file()
        and decision.get("dispatchIdentityLedgerIntegratedWithRunner") is False
        and decision.get("dispatchAuthorizationAdapterPocValidated") is True
        and decision.get("dispatchAuthorizationAdapterPocEvidence")
        == (
            "registry/"
            "human-ai-collaboration-tdd-noncomparative-dispatch-"
            "authorization-adapter-poc-evidence-2026-07-26.json"
        )
        and (root / decision["dispatchAuthorizationAdapterPocEvidence"]).is_file()
        and decision.get("currentRepositoryDocumentsRejectedByAdapter") is True
        and decision.get(
            "dispatchAuthorizationAdapterIntegratedWithFormalRunner"
        )
        is False
        and decision.get("runnerPreflightPocValidated") is True
        and decision.get("runnerPreflightPocEvidence")
        == (
            "registry/"
            "human-ai-collaboration-tdd-noncomparative-runner-preflight-"
            "poc-evidence-2026-07-26.json"
        )
        and (root / decision["runnerPreflightPocEvidence"]).is_file()
        and _digest(decision.get("runnerPreflightPocEvidenceFileSha256"))
        and hashlib.sha256(
            (root / decision["runnerPreflightPocEvidence"]).read_bytes()
        ).hexdigest()
        == decision["runnerPreflightPocEvidenceFileSha256"]
        and decision.get("reservationBeforeInjectedFactoryUnitTested") is True
        and decision.get(
            "currentRepositoryDocumentsRejectedBeforeInjectedFactory"
        )
        is True
        and decision.get(
            "runnerPreflightProtocolBoundLedgerAuthorityPocValidated"
        )
        is True
        and decision.get(
            "callerSelectedLedgerPathRemovedInOfflineWrapper"
        )
        is True
        and decision.get("constructionFailureStatePocValidated") is True
        and decision.get("constructionSuccessStatePocValidated") is True
        and decision.get(
            "threadBindingBeforeConstructionSuccessRejected"
        )
        is True
        and decision.get(
            "factoryPrimaryErrorPreservedWhenFailureEventAppendFails"
        )
        is True
        and decision.get(
            "hostilePrimaryErrorPreservedAcrossSecondaryFailures"
        )
        is True
        and decision.get(
            "manualRetainConsumedReconciliationPocValidated"
        )
        is True
        and decision.get(
            "missingOutcomeManualRetainConsumedReconciliationPocValidated"
        )
        is True
        and decision.get("liveLedgerAuthorityConfigured") is False
        and decision.get(
            "authorizationEnvelopeToReservationDocumentDriftClosed"
        )
        is True
        and decision.get(
            "sourceSnapshotToFactoryMaterializationFreshnessClosed"
        )
        is False
        and decision.get("failureEventAppendRecoveryImplemented") is False
        and decision.get("handleValidationBeyondNoneImplemented") is True
        and decision.get("injectedStructuredHandleValidatorUnitTested")
        is True
        and decision.get("sameProcessRegisteredCleanupLifoUnitTested")
        is True
        and decision.get("successAppendDurableReadbackUnitTested") is True
        and decision.get(
            "reservedWithoutConstructionOutcomeClassifiedByFreshReader"
        )
        is True
        and decision.get(
            "automaticFactoryResourceCleanupImplemented"
        )
        is False
        and decision.get("dispatchCapScope")
        == "protocol-selected-ledger-local"
        and decision.get("twoAuthoritySameCandidateCounterexamplePinned")
        is True
        and decision.get("currentPocSystemGlobalDispatchCapAbsent") is True
        and decision.get("systemGlobalDispatchCapProved") is False
        and decision.get("realAppServerHandleCompatibilityProved") is False
        and decision.get("realChildProcessOrSocketCleanupProved") is False
        and decision.get("cleanupAfterProcessCrashProved") is False
        and decision.get("crossProcessExactlyOnceCleanupProved") is False
        and decision.get("runnerPreflightIntegratedWithFormalRunner") is False
        and decision.get(
            "automaticReservationReleaseOrRetryImplemented"
        )
        is False
        and decision.get("runtimeDispatchCapEnforced") is False
        and decision.get(
            "liveTransitionBlockedUntilRunnerAndLedgerValidated"
        )
        is True
        and decision.get("formalComparisonRemainsBlocked") is True
        and "exact-candidate execution admission"
        in str(decision.get("nextBoundedAction"))
        and "synthetic authorization envelope"
        in str(decision.get("nextBoundedAction"))
        and "retain-consumed-no-retry reconciliation"
        in str(decision.get("nextBoundedAction"))
        and "source-snapshot-to-factory materialization freshness"
        in str(decision.get("nextBoundedAction"))
        and "real child-process or socket cleanup"
        in str(decision.get("nextBoundedAction"))
        and "two-authority same-candidate counterexample"
        in str(decision.get("nextBoundedAction"))
        and "do not add automatic release or retry"
        in str(decision.get("nextBoundedAction")),
        "diagnostic decision boundary drifted",
    )

    _require(
        document.get("documentation") == DOCUMENTATION_PATH
        and (root / DOCUMENTATION_PATH).is_file(),
        "diagnostic documentation binding drifted",
    )
    documentation = " ".join(
        (root / DOCUMENTATION_PATH).read_text(encoding="utf-8").split()
    )
    for phrase in (
        "No candidate task turn has started",
        "at most one dispatch per exact candidate",
        "does not produce a score, ranking, winner, preference, or comparative result",
        "metadata selection does not prove Skill-body delivery",
        "The current Matt projection is not the approved release payload",
        "Superpowers 6.2.0 is not a repository-approved release entry",
        "Exact-candidate execution admission remains unsatisfied",
        "The static admission-gap audit admits or rejects neither candidate",
        "The offline ledger PoC is not integrated with the formal runner",
        "The document-bound adapter rejects the current protocol and preflight",
        "writes and file-fsyncs the reservation",
        "then calls the injected fake factory",
        "not integrated with the formal runner or a real app-server factory",
        "no longer accepts a caller-selected ledger path",
        "synthetic protocol-bound ledger authority",
        "authorization envelope",
        "Post-envelope document-path drift",
        "`construction-succeeded` before returning its handle",
        "thread binding rejects until that event exists",
        "`construction-failed` event",
        "original factory exception remains primary",
        "secondary errors are attached best-effort",
        "retain-consumed-no-retry",
        "authorization-envelope-to-reservation document-drift window",
        "source-snapshot-to-factory materialization freshness",
        "structured handle validator",
        "same-process registered resources",
        "reserved-without-construction-outcome",
        "protocol-selected-ledger-local",
        "real child-process or socket cleanup",
        "there is no automatic release or retry",
        "not current runtime enforcement",
        "No runner consumes this protocol",
        "live transition must stay blocked",
    ):
        _require(
            phrase in documentation,
            f"diagnostic documentation boundary missing: {phrase}",
        )


def main() -> int:
    validate_protocol(_load(ROOT, PROTOCOL_PATH))
    print("human-AI collaboration TDD noncomparative diagnostic protocol: valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
