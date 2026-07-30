#!/usr/bin/env python3
"""Validate the preregistered new-feature TDD comparative protocol."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
PROTOCOL_PATH = (
    "registry/"
    "human-ai-collaboration-new-feature-tdd-protocol-2026-07-26.json"
)
DOCUMENTATION_PATH = (
    "docs/strategy/"
    "HUMAN-AI-COLLABORATION-NEW-FEATURE-TDD-PROTOCOL-2026-07-26.md"
)
EXPECTED_ARMS = {
    "SE-TDD-NATIVE-SPARK",
    "SE-TDD-MATT-CURRENT",
    "SE-TDD-SUPERPOWERS-6.2.0",
    "SE-TDD-STRONG-DIAGNOSTIC",
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _digest(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def validate_protocol(
    document: dict[str, Any],
    *,
    root: Path = ROOT,
) -> None:
    _require(document.get("schema") == 1, "TDD protocol schema must be 1")
    _require(
        document.get("status")
        == "native-attempt-cap-reached-zero-valid-formal-treatment-comparison-blocked",
        "TDD protocol status was promoted or drifted",
    )
    _require(
        document.get("parentScenarioId") == "SE-IMPLEMENT-REVIEW-01"
        and document.get("sliceId") == "SE-IMPLEMENT-TDD-NEW-FEATURE-01",
        "TDD protocol scenario binding drifted",
    )

    authority = document.get("authority", {})
    _require(
        authority.get("liveExecutionAuthorizedByThisRecord") is False
        and "global Skill or Plugin configuration mutation"
        in authority.get("blocked", [])
        and "full Superpowers orchestration attribution"
        in authority.get("blocked", [])
        and "portfolio preference or self-authored-chain change from preregistration"
        in authority.get("blocked", []),
        "TDD protocol authority boundary drifted",
    )

    sources = {
        item.get("id"): item
        for item in document.get("sourceBindings", [])
        if isinstance(item, dict)
    }
    _require(
        set(sources)
        == {
            "matt.current-tdd",
            "superpowers.6.2.0-test-driven-development",
        },
        "TDD protocol source set drifted",
    )
    matt = sources["matt.current-tdd"]
    _require(
        matt.get("revision")
        == "ed37663cc5fbef691ddfecd080dff42f7e7e350d"
        and matt.get("localNavigationCheckoutRevision")
        == "9603c1cc8118d08bc1b3bf34cf714f62178dea3b"
        and matt.get("localNavigationCheckoutIsCurrent") is False
        and matt.get("license") == "MIT"
        and _digest(matt.get("licenseSha256"))
        and matt.get("exactSourceMaterializedForTrial") is False
        and matt.get("candidateSuitability")
        == "eligible-after-exact-materialization-and-exposure-preflight",
        "Matt TDD source boundary drifted",
    )
    _require(
        {
            item.get("path")
            for item in matt.get("files", [])
            if isinstance(item, dict)
        }
        == {
            "skills/engineering/tdd/SKILL.md",
            "skills/engineering/tdd/tests.md",
            "skills/engineering/tdd/mocking.md",
        }
        and all(
            _digest(item.get("sha256"))
            and isinstance(item.get("gitBlobSha"), str)
            and len(item["gitBlobSha"]) == 40
            for item in matt.get("files", [])
        ),
        "Matt TDD exact file set drifted",
    )

    superpowers = sources["superpowers.6.2.0-test-driven-development"]
    _require(
        superpowers.get("version") == "6.2.0"
        and superpowers.get("sourceClass")
        == "openai-curated-plugin-cache-observation"
        and _digest(superpowers.get("pluginManifestSha256"))
        and superpowers.get("license") == "MIT"
        and _digest(superpowers.get("licenseSha256"))
        and superpowers.get("exactSourceMaterializedForTrial") is False
        and superpowers.get("candidateSuitability")
        == "eligible-after-source-pinned-project-projection-and-exposure-preflight",
        "Superpowers TDD source boundary drifted",
    )
    _require(
        {
            item.get("path")
            for item in superpowers.get("files", [])
            if isinstance(item, dict)
        }
        == {
            "skills/test-driven-development/SKILL.md",
            "skills/test-driven-development/writing-good-tests.md",
        }
        and all(
            _digest(item.get("sha256"))
            for item in superpowers.get("files", [])
        ),
        "Superpowers TDD exact file set drifted",
    )

    projections = {
        item.get("candidateId"): item
        for item in document.get("projectionCandidates", [])
        if isinstance(item, dict)
    }
    _require(
        set(projections)
        == {"tdd.matt.current", "tdd.superpowers.6.2.0"},
        "TDD protocol projection candidate set drifted",
    )
    matt_projection = projections["tdd.matt.current"]
    superpowers_projection = projections["tdd.superpowers.6.2.0"]
    _require(
        matt_projection.get("skillName") == "tdd"
        and matt_projection.get("sourceClass")
        == "reviewed-maintained-external-public-github-api"
        and matt_projection.get("source", {}).get("revision")
        == matt["revision"]
        and superpowers_projection.get("skillName")
        == "test-driven-development"
        and superpowers_projection.get("sourceClass")
        == "openai-curated-runtime-distributed-third-party"
        and superpowers_projection.get("source", {}).get("packageVersion")
        == "6.2.0",
        "TDD protocol projection source binding drifted",
    )
    for candidate, expected_count in (
        (matt_projection, 3),
        (superpowers_projection, 2),
    ):
        records = [candidate.get("license"), *candidate.get("files", [])]
        _require(
            len(candidate.get("files", [])) == expected_count
            and all(
                isinstance(record, dict)
                and isinstance(record.get("bytes"), int)
                and record["bytes"] > 0
                and _digest(record.get("sha256"))
                and isinstance(record.get("gitBlobSha1"), str)
                and len(record["gitBlobSha1"]) == 40
                and record.get("publicUpstreamMatch") is True
                for record in records
            ),
            f"TDD protocol projection file contract drifted: {candidate.get('candidateId')}",
        )

    comparison = document.get("contentComparison", {})
    _require(
        len(comparison.get("sharedClaims", [])) >= 7
        and "the public test seam must be pre-agreed with the user"
        in comparison.get("mattDistinctives", [])
        and "the RED observation is an iron law and a wrong failure must be corrected before GREEN"
        in comparison.get("superpowersDistinctives", [])
        and comparison.get("materialConflict", {}).get("id")
        == "refactor-phase-placement"
        and "pre-accepts the one public seam"
        in str(comparison.get("interactionConfoundControl"))
        and "No complete Matt or Superpowers workflow"
        in str(comparison.get("fullFrameworkConfoundControl")),
        "TDD protocol overlap or conflict control drifted",
    )

    arms = {
        arm.get("id"): arm
        for arm in document.get("arms", [])
        if isinstance(arm, dict)
    }
    _require(set(arms) == EXPECTED_ARMS, "TDD protocol arm set drifted")
    _require(
        arms["SE-TDD-NATIVE-SPARK"].get("selectedTreatment") is None
        and arms["SE-TDD-MATT-CURRENT"].get("selectedTreatment")
        == "matt.current-tdd"
        and arms["SE-TDD-SUPERPOWERS-6.2.0"].get("selectedTreatment")
        == "superpowers.6.2.0-test-driven-development"
        and arms["SE-TDD-STRONG-DIAGNOSTIC"].get(
            "countsTowardWeakAcceptance"
        )
        is False,
        "TDD protocol treatment binding drifted",
    )
    _require(
        arms["SE-TDD-NATIVE-SPARK"].get("eligibility")
        == "stopped-after-three-capped-attempts-valid-repetitions-zero"
        and "formal-comparison-blocked-zero-valid-native-baseline"
        in arms["SE-TDD-MATT-CURRENT"].get("eligibility", "")
        and "formal-comparison-blocked-zero-valid-native-baseline"
        in arms["SE-TDD-SUPERPOWERS-6.2.0"].get("eligibility", ""),
        "TDD protocol formal-run eligibility drifted",
    )

    artifacts = document.get("fixtureArtifacts", {})
    _require(
        artifacts.get("builder")
        == "scripts/build_human_ai_collaboration_tdd_trial.py"
        and _digest(artifacts.get("builderSha256"))
        and artifacts.get("timelineFixtures")
        == "tests/fixtures/human-ai-collaboration-tdd-timeline-fixtures-2026-07-26.json"
        and _digest(artifacts.get("timelineFixturesSha256"))
        and artifacts.get("privateOracleVersion")
        == "capped-backoff-hidden-oracle-v1"
        and _digest(artifacts.get("privateOracleSha256"))
        and artifacts.get("privateOracleContentWrittenIntoTrial") is False
        and artifacts.get("offlineTimelineCaseCount") == 7
        and artifacts.get("offlineTimelineCasesMatched") == 7
        and artifacts.get("rawItemCaseCount") == 15
        and artifacts.get("rawItemCasesMatched") == 15
        and artifacts.get("rawItemNormalizerContractVersion")
        == "codex-app-server-tdd-normalizer-v2",
        "TDD protocol fixture artifact binding drifted",
    )
    for path in (
        artifacts.get("builder"),
        artifacts.get("timelineFixtures"),
        artifacts.get("rawItemNormalizer"),
        artifacts.get("rawItemFixtures"),
        artifacts.get("parentOutcomeEvaluator"),
        artifacts.get("formalRunner"),
    ):
        _require(
            isinstance(path, str) and (root / path).is_file(),
            f"TDD protocol fixture artifact is missing: {path}",
        )
    _require(
        hashlib.sha256(
            (root / artifacts["builder"]).read_bytes()
        ).hexdigest()
        == artifacts["builderSha256"]
        and hashlib.sha256(
            (root / artifacts["timelineFixtures"]).read_bytes()
        ).hexdigest()
        == artifacts["timelineFixturesSha256"]
        and hashlib.sha256(
            (root / artifacts["rawItemNormalizer"]).read_bytes()
        ).hexdigest()
        == artifacts["rawItemNormalizerSha256"]
        and hashlib.sha256(
            (root / artifacts["rawItemFixtures"]).read_bytes()
        ).hexdigest()
        == artifacts["rawItemFixturesSha256"]
        and hashlib.sha256(
            (root / artifacts["parentOutcomeEvaluator"]).read_bytes()
        ).hexdigest()
        == artifacts["parentOutcomeEvaluatorSha256"]
        and hashlib.sha256(
            (root / artifacts["formalRunner"]).read_bytes()
        ).hexdigest()
        == artifacts["formalRunnerSha256"],
        "TDD protocol fixture artifact content hash drifted",
    )
    exposure_path = document.get("exposurePreflightEvidence")
    _require(
        exposure_path
        == "registry/human-ai-collaboration-new-feature-tdd-exposure-preflight-2026-07-26.json"
        and (root / exposure_path).is_file(),
        "TDD protocol exposure preflight binding drifted",
    )
    pilot_path = document.get("rawItemPilotEvidence")
    _require(
        pilot_path
        == "registry/human-ai-collaboration-tdd-raw-item-pilot-evidence-2026-07-26.json"
        and (root / pilot_path).is_file(),
        "TDD protocol raw-item pilot binding drifted",
    )
    formal_attempt_path = document.get("formalRunnerFirstAttemptEvidence")
    _require(
        formal_attempt_path
        == "registry/human-ai-collaboration-tdd-formal-runner-first-attempt-evidence-2026-07-26.json"
        and (root / formal_attempt_path).is_file(),
        "TDD protocol formal first-attempt binding drifted",
    )
    native_batch_path = document.get("nativeFormalAttemptBatchEvidence")
    _require(
        native_batch_path
        == "registry/human-ai-collaboration-tdd-native-formal-attempt-batch-2026-07-26.json"
        and (root / native_batch_path).is_file(),
        "TDD protocol native formal batch binding drifted",
    )

    fixture = document.get("fixtureContract", {})
    _require(
        fixture.get("status")
        == "materialized-by-builder-native-attempt-cap-reached-zero-valid"
        and fixture.get("language") == "Python standard library only"
        and len(fixture.get("requiredBehaviorClasses", [])) == 4
        and fixture.get("allowedMutableFiles")
        == ["feature.py", "test_feature.py", "PROCESS_EVIDENCE.json"]
        and "implementation before the first valid RED observation"
        in fixture.get("forbiddenImplementationPatterns", []),
        "TDD protocol fixture boundary drifted",
    )

    instrumentation = document.get("processInstrumentationGate", {})
    _require(
        instrumentation.get("status")
        == "current-host-raw-normalization-oracle-mutants-and-formal-runner-integrated"
        and len(instrumentation.get("mustObserve", [])) >= 6
        and "timeline cannot order RED and production mutation"
        in instrumentation.get("invalidRunConditions", [])
        and "measurement-invalid"
        in str(instrumentation.get("claimLimit"))
        and instrumentation.get("pilotSeparation", {}).get(
            "currentHostRawEventNormalizationReady"
        )
        is True
        and instrumentation.get("pilotSeparation", {}).get(
            "positiveTraceAgentTddProcessAccepted"
        )
        is False
        and instrumentation.get("pilotSeparation", {}).get(
            "opaqueWriteTraceFailedClosed"
        )
        is True
        and instrumentation.get("pilotSeparation", {}).get(
            "formalScoredRunnerReady"
        )
        is True,
        "TDD protocol process instrumentation boundary drifted",
    )

    control = document.get("commonControlPlane", {})
    _require(
        control.get("model") == "gpt-5.3-codex-spark"
        and control.get("reasoningEffort") == "low"
        and control.get("providerFallbackAllowed") is False
        and control.get("approvalPolicy") == "never"
        and control.get("sandboxType") == "workspaceWrite"
        and control.get("networkAccess") is False
        and control.get("allNonselectedConfigurableSkillsDisabled") is True
        and control.get("mcpInventoryCompletenessProved") is False
        and control.get("samePromptFixtureOracleAndHardAcceptanceAcrossPrimaryArms")
        is True,
        "TDD protocol common control plane drifted",
    )

    acceptance = document.get("acceptance", {})
    _require(
        len(acceptance.get("hardGates", [])) >= 7
        and "Run three valid repetitions per primary arm"
        in str(acceptance.get("repetitionRule"))
        and "No candidate preference from one run"
        in str(acceptance.get("preferenceRule"))
        and "do not prove exact candidate delivery or causation"
        in str(acceptance.get("causationRule"))
        and "Stop an arm after three invalid attempts"
        in str(acceptance.get("invalidRunStopRule")),
        "TDD protocol acceptance boundary drifted",
    )

    decision = document.get("decisionBoundary", {})
    _require(
        decision.get("fixtureReady") is True
        and decision.get("offlineProcessClassifierReady") is True
        and decision.get("mattCurrentProjectionPreflightProved") is True
        and decision.get("superpowers620ProjectionPreflightProved") is True
        and decision.get("candidateSpecificSelectedMetadataExposureProved")
        is True,
        "TDD protocol preflight readiness drifted",
    )
    for key in (
        "candidateSpecificTreatmentDeliveryProved",
        "candidatePreferenceProved",
        "skillCausationProved",
        "selfAuthoredGapProved",
        "selfAuthoredChainChangeAuthorized",
        "portfolioMutationAuthorized",
        "nonComparativeDiagnosticRuntimeEnforcementProved",
    ):
        _require(
            decision.get(key) is False,
            f"TDD protocol decision boundary was promoted: {key}",
        )
    diagnostic_protocol_path = decision.get(
        "nonComparativeTreatmentDiagnosticProtocol"
    )
    audit_path = decision.get("exactCandidateAdmissionGapAuditEvidence")
    diagnostic_protocol = (
        json.loads(
            (root / diagnostic_protocol_path).read_text(encoding="utf-8")
        )
        if isinstance(diagnostic_protocol_path, str)
        and (root / diagnostic_protocol_path).is_file()
        else {}
    )
    diagnostic_decision = diagnostic_protocol.get("decision", {})
    _require(
        isinstance(audit_path, str)
        and (root / audit_path).is_file()
        and diagnostic_decision.get(
            "exactCandidateAdmissionGapAuditEvidence"
        )
        == audit_path
        and diagnostic_decision.get(
            "exactCandidateAdmissionGapAuditFileSha256"
        )
        == hashlib.sha256((root / audit_path).read_bytes()).hexdigest(),
        "TDD protocol exact-candidate audit binding drifted",
    )
    _require(
        decision.get("processInstrumentationReady") is True
        and decision.get("currentHostRawEventNormalizationReady") is True
        and decision.get("executableHiddenOracleReady") is True
        and decision.get("executableMutantSuiteReady") is True
        and decision.get("formalScoredRunnerReady") is True
        and decision.get("liveDiagnosticPilotStarted") is True
        and decision.get("formalLiveRunStarted") is True
        and decision.get("formalAttemptCount") == 3
        and decision.get("validFormalRepetitionCount") == 0
        and decision.get("nativeAttemptCapReached") is True
        and decision.get("nativeValidComparisonBaselineAvailable") is False
        and decision.get("formalTreatmentComparisonBlocked") is True
        and decision.get(
            "nonComparativeTreatmentDiagnosticEligibleAfterPreregistration"
        )
        is True
        and decision.get(
            "nonComparativeTreatmentDiagnosticProtocolPreregistered"
        )
        is True
        and decision.get("nonComparativeTreatmentDiagnosticProtocol")
        == (
            "registry/"
            "human-ai-collaboration-tdd-noncomparative-treatment-"
            "diagnostic-protocol-2026-07-26.json"
        )
        and (
            root / decision["nonComparativeTreatmentDiagnosticProtocol"]
        ).is_file()
        and decision.get("exactCandidateAdmissionGapAuditCompleted") is True
        and decision.get("exactCandidateAdmissionGapAuditEvidence")
        == (
            "registry/"
            "human-ai-collaboration-tdd-exact-candidate-admission-gap-audit-"
            "2026-07-26.json"
        )
        and (root / decision["exactCandidateAdmissionGapAuditEvidence"]).is_file()
        and decision.get("candidateAdmissionDecisionMade") is False
        and decision.get("exactCandidateExecutionAdmissionSatisfied") is False
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
        and decision.get("nonComparativeLiveTransitionBlocked") is True
        and "non-scored, non-comparative"
        in str(decision.get("nextBoundedAction"))
        and "execution admission"
        in str(decision.get("nextBoundedAction"))
        and "synthetic authorization envelope"
        in str(decision.get("nextBoundedAction"))
        and "manual retain-consumed-no-retry reconciliation"
        in str(decision.get("nextBoundedAction"))
        and "source-snapshot-to-factory materialization freshness"
        in str(decision.get("nextBoundedAction"))
        and "real child-process or socket cleanup"
        in str(decision.get("nextBoundedAction"))
        and "two-authority same-candidate counterexample"
        in str(decision.get("nextBoundedAction"))
        and "rematerialized and reverified"
        in str(decision.get("nextBoundedAction"))
        and "without automatic release or retry"
        in str(decision.get("nextBoundedAction")),
        "TDD protocol next action drifted",
    )

    _require(
        document.get("documentation") == DOCUMENTATION_PATH
        and (root / DOCUMENTATION_PATH).is_file(),
        "TDD protocol documentation binding drifted",
    )
    documentation = " ".join(
        (root / DOCUMENTATION_PATH).read_text(encoding="utf-8").split()
    )
    for phrase in (
        "does not compare the complete Matt or Superpowers development systems",
        "local Matt navigation checkout remains at",
        "Final green tests without an ordered RED-to-production timeline are measurement-invalid",
        "Seven normalized timeline fixtures now distinguish",
        "One sealed trace normalized successfully while its Agent TDD behavior was rejected",
        "records two non-scored native task turns",
        "native attempt cap reached",
        "There is no valid native comparison baseline",
        "must not be run as formal comparative treatment arms",
        "killed only five of seven predeclared mutants",
        "proves no candidate value",
        "single-dispatch cap is likewise preregistered",
        "admits or rejects neither exact candidate",
        "offline dispatch identity ledger PoC",
        "document-bound adapter",
        "reservation-before-callback ordering only with an injected fake factory",
        "not integrated with the formal runner or a real app-server factory",
        "no longer accepts a caller-selected ledger path",
        "synthetic protocol-bound ledger authority",
        "authorization envelope",
        "Post-envelope document-path drift",
        "`construction-succeeded` before returning the handle",
        "thread binding rejects before that event",
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
        "Automatic release, retry, and crash recovery remain absent",
        "Live transition remains blocked",
    ):
        _require(
            phrase in documentation,
            f"TDD protocol documentation boundary missing: {phrase}",
        )


def main() -> int:
    document = json.loads((ROOT / PROTOCOL_PATH).read_text(encoding="utf-8"))
    validate_protocol(document)
    print("human-ai collaboration new-feature TDD protocol: valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
