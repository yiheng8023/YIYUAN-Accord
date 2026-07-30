#!/usr/bin/env python3
"""Validate and evaluate the first collaboration comparative protocol offline."""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
PROTOCOL_PATH = (
    "registry/human-ai-collaboration-comparative-protocol-batch-01-2026-07-24.json"
)
FIXTURE_PATH = (
    "tests/fixtures/human-ai-collaboration-comparative-protocol-batch-01-2026-07-24.json"
)
EXPECTED_CANDIDATE_HASHES = {
    "cc.grill-with-docs": "E1078020C41B954638BA94ACDA95A3340739908BD68B1DB9BC2AF129D3936035",
    "cc.disciplined-coding": "D36F49ED0D252B9C9C656BC9C0F72D43710C68591CE234E8DC2886DC4785FC7B",
    "cc.review": "7D20260E46399CA040EE53BEE5FBE057FFFD7FEC0866BC7A627C4F422C69A0E6",
    "cc.diagnose": "28886402BBFA0470248086EAB9106A103B964B76AE9496E63FF0C8A6761B6D13",
    "matt.current-diagnosing-bugs": "7A0779480F323A66D109404646BCC1A14BF0232B45B3E3EA93B652A035718ACB",
    "superpowers.test-driven-development": "B5B4717B8B761CCE15A6CFE9022E33FD959E0894C0C39D72C9CB49C23486C10E",
    "superpowers.requesting-code-review": "1017CCDD5BC61FAB67C654CF118CBDB520464B313073A0A6B9A6B9AA647A3AD6",
    "superpowers.systematic-debugging": "3B20719ECA4F0461CB51A195221320D775DCF03B6859271066A03A5132A6CE7A",
    "self.intent-contract": "1D67E4B84856BCD0828D89B82803A7275D95D8E586FD8EFCD127F89E82845753",
    "self.capability-router": "EB9F7D253D12682A3E8B9F87FAF5BAD4284A2D268B25C30CC5AD9F6DD36EB8FE",
    "self.closure-contract": "59EDFC131C45B7AA1EF85A1737317A0CC97ADCFB0DDCEB7EE81E9C744B13BBB3",
}
EXPECTED_PROTOCOL_ARMS = {
    "PROTOCOL-GEN-RESEARCH-01": {
        "GEN-HUMAN-CONTROL",
        "GEN-NATIVE-SPARK",
        "GEN-CC-GRILL-WITH-DOCS",
        "GEN-SELF-CHAIN",
        "GEN-STRONG-DIAGNOSTIC",
    },
    "PROTOCOL-SE-IMPLEMENT-REVIEW-01": {
        "SE-HUMAN-CONTROL",
        "SE-NATIVE-SPARK",
        "SE-MATT-DISCIPLINED-CODING",
        "SE-SUPERPOWERS-TDD",
        "SE-SELF-CHAIN-PHASED",
        "SE-MATT-REVIEW",
        "SE-SUPERPOWERS-REVIEW",
        "SE-STRONG-DIAGNOSTIC",
    },
    "PROTOCOL-SE-OPS-INCIDENT-01": {
        "SE-OPS-HUMAN-CONTROL",
        "SE-OPS-NATIVE-SPARK",
        "SE-OPS-CC-DIAGNOSE",
        "SE-OPS-MATT-CURRENT-DIAGNOSING-BUGS",
        "SE-OPS-SUPERPOWERS-SYSTEMATIC-DEBUGGING",
        "SE-OPS-SELF-CHAIN-PHASED",
        "SE-OPS-STRONG-DIAGNOSTIC",
    },
}
PRIMARY_ELIGIBILITY = {
    "eligible-now-after-fresh-user-skills-disabled-preflight",
    "eligible-current-host-metadata-exposure-proved-live-task-not-started",
    "first-formal-run-passed-at-least-two-repetitions-required",
    "first-formal-run-passed-loader-causation-unproved-at-least-two-repetitions-required",
}
CONDITIONAL_STRONG_ARMS = {
    "GEN-STRONG-DIAGNOSTIC",
    "SE-STRONG-DIAGNOSTIC",
    "SE-OPS-STRONG-DIAGNOSTIC",
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _index(items: Any, field: str, label: str) -> dict[str, dict[str, Any]]:
    _require(isinstance(items, list), f"{label} must be a list")
    result: dict[str, dict[str, Any]] = {}
    for item in items:
        _require(isinstance(item, dict), f"{label} entries must be objects")
        key = item.get(field)
        _require(_text(key), f"{label} entry is missing {field}")
        _require(key not in result, f"{label} contains duplicate {field}: {key}")
        result[key] = item
    return result


def validate_protocol(
    document: dict[str, Any],
    fixture: dict[str, Any],
    *,
    root: Path = ROOT,
    program: dict[str, Any] | None = None,
) -> None:
    _require(document.get("schema") == 1, "Comparative protocol schema must be 1")
    _require(
        document.get("status")
        == "source-pinned-debugging-three-pairs-complete-mixed-no-preference-or-causation",
        "Comparative protocol status overclaimed or drifted",
    )
    authority = document.get("authorityBoundary")
    _require(isinstance(authority, dict), "Comparative protocol authority boundary is missing")
    _require(authority.get("repositoryWritesAuthorized") is True, "Repository protocol-write authority drifted")
    _require(authority.get("disposableFixtureWritesAuthorized") is True, "Disposable fixture authority drifted")
    for key in (
        "candidateSkillContentMutationAuthorized",
        "globalConfigMutationAuthorized",
        "capabilityInstallUpdateOrRemovalAuthorized",
        "mcpMutationAuthorized",
        "liveAccountOrPrivateDataAccessAuthorized",
        "externalWriteAuthorized",
        "gitCommitOrPushAuthorized",
        "calibrationWriteAuthorized",
        "hardStandardPromotionAuthorized",
    ):
        _require(authority.get(key) is False, f"Comparative protocol authority promoted: {key}")

    method = document.get("selectionMethod")
    _require(isinstance(method, dict), "Comparative protocol selection method is missing")
    _require(method.get("type") == "qualitative-ordinal-no-false-precision", "Selection method drifted")
    _require(method.get("countOptimizationForbidden") is True, "Scenario-count optimization was enabled")
    _require(
        method.get("generalSelection", {}).get("selectedScenarioId") == "GEN-RESEARCH-01",
        "General protocol selection drifted",
    )
    _require(
        method.get("softwareSelection", {}).get("selectedScenarioId")
        == "SE-IMPLEMENT-REVIEW-01",
        "Software protocol selection drifted",
    )
    second_selection = method.get("secondSoftwareSelection", {})
    _require(
        second_selection.get("selectedScenarioId") == "SE-OPS-INCIDENT-01"
        and second_selection.get("selectedAfterScenarioId")
        == "SE-IMPLEMENT-REVIEW-01",
        "Second software protocol selection drifted",
    )
    fixture_design = second_selection.get("fixtureDesign", {})
    _require(
        fixture_design.get("fixtureId")
        == "fixture.python-tenant-policy-cache-incident-v1"
        and fixture_design.get("privateOracleMustRemainOutsideTaskPrompt") is True,
        "Second software private-oracle design drifted",
    )
    fixture_preflight = fixture_design.get("preflight", {})
    _require(
        fixture_preflight.get("nativeAndDiagnosePublicTaskPromptSha256")
        == "dbbee6ef0d037875e43b3999a3064cdcadbc1a80abc386f0b2126e0eb0eb02ab"
        and fixture_preflight.get("visibleBaselinePassed") is True
        and fixture_preflight.get("privateHiddenBaselinePassed") is False,
        "Second software fixture preflight drifted",
    )

    host = document.get("hostBinding")
    _require(isinstance(host, dict), "Comparative protocol host binding is missing")
    _require(host.get("primaryWeakModelRequested") == "gpt-5.3-codex-spark", "Primary weak model drifted")
    _require(host.get("primaryReasoningEffortRequested") == "low", "Primary weak reasoning drifted")
    _require(host.get("strongDiagnosticRequested") == "gpt-5.6-terra", "Strong diagnostic model drifted")
    _require(host.get("providerFallbackAllowed") is False, "Provider fallback was enabled")

    exposure = document.get("exposureBinding")
    _require(isinstance(exposure, dict), "Comparative protocol exposure binding is missing")
    _require(exposure.get("allUserSkillsDisabledForSparkLowProved") is True, "Native disabled exposure evidence drifted")
    for key in (
        "candidateSpecificSelectedExposureProved",
        "superpowersTddSelectedExposureProved",
        "allPrimarySkillArmsHaveCandidateSpecificExposure",
        "multiSkillCombinedExposureProved",
        "loaderInvocationProved",
        "behavioralValueProved",
    ):
        _require(exposure.get(key) is False, f"Comparative exposure claim promoted: {key}")
    _require(
        exposure.get("disciplinedCodingSelectedExposureProved") is True,
        "Disciplined-coding selected exposure evidence drifted",
    )
    _require(
        exposure.get("diagnoseSelectedExposureProved") is True,
        "Diagnose selected exposure evidence drifted",
    )
    _require(
        exposure.get("currentMattDiagnosingBugsSelectedExposureProved") is True
        and exposure.get("superpowersSystematicDebuggingSelectedExposureProved")
        is True,
        "Source-pinned debugging selected exposure drifted",
    )
    _require(
        exposure.get("structuredSkillInputEvidence")
        == "registry/codex-app-server-structured-skill-input-evidence-2026-07-24.json"
        and exposure.get("structuredSkillInputAcceptedByCurrentHost") is True,
        "Structured Skill-input binding drifted",
    )
    _require(
        exposure.get("syntheticBodyOnlyDeliveryEvidence")
        == "registry/codex-app-server-skill-treatment-fidelity-evidence-2026-07-24.json"
        and exposure.get(
            "syntheticProjectCanaryBodyOnlyDeliveryProvedOnBoundHost"
        )
        is True
        and exposure.get("installedCandidateSpecificBodyDeliveryProved")
        is False,
        "Synthetic body-only treatment evidence drifted or overclaimed",
    )
    _require(
        exposure.get("candidateExposureEvidence")
        == "registry/codex-app-server-comparative-candidate-exposure-preflight-2026-07-24.json",
        "Comparative candidate exposure evidence binding drifted",
    )
    _require(
        exposure.get("sourcePinnedProjectionPreflightEvidence")
        == "registry/source-pinned-debugging-skill-projection-preflight-evidence-2026-07-24.json",
        "Source-pinned projection evidence binding drifted",
    )

    pins = _index(document.get("candidatePins"), "id", "Comparative candidate pins")
    _require(set(pins) == set(EXPECTED_CANDIDATE_HASHES), "Comparative candidate pin set drifted")
    for candidate_id, digest in EXPECTED_CANDIDATE_HASHES.items():
        pin = pins[candidate_id]
        _require(pin.get("sha256") == digest, f"Comparative candidate hash drifted: {candidate_id}")
        _require(isinstance(pin.get("bytes"), int) and pin["bytes"] > 0, f"Comparative candidate byte count missing: {candidate_id}")
        _require(_text(pin.get("path")) and _text(pin.get("family")), f"Comparative candidate metadata missing: {candidate_id}")

    suitability = _index(document.get("suitabilityDecisions"), "candidateId", "Suitability decisions")
    _require(set(suitability) == set(EXPECTED_CANDIDATE_HASHES), "Suitability decision set drifted")
    _require(suitability["cc.grill-with-docs"].get("decision") == "exclude-near-match", "Research near-match exclusion drifted")
    _require(suitability["cc.disciplined-coding"].get("decision") == "eligible-primary-single-skill-arm", "Matt implementation eligibility drifted")
    _require(
        suitability["cc.diagnose"].get("decision")
        == "eligible-primary-single-skill-arm-after-packet",
        "Installed diagnose eligibility drifted",
    )
    _require(
        suitability["matt.current-diagnosing-bugs"].get("decision")
        == "source-pinned-three-runs-complete-mixed-no-preference",
        "Current Matt source-pinned outcome drifted",
    )
    _require(suitability["superpowers.test-driven-development"].get("decision") == "eligible-primary-single-skill-arm", "Superpowers TDD eligibility drifted")
    _require(
        suitability["superpowers.systematic-debugging"].get("decision")
        == "source-pinned-three-runs-complete-mixed-no-preference",
        "Superpowers systematic-debugging source-pinned outcome drifted",
    )
    for item in suitability.values():
        _require(_text(item.get("scenarioId")) and _text(item.get("decision")) and _text(item.get("reason")), "Suitability decision is incomplete")

    protocols = _index(document.get("protocols"), "id", "Comparative protocols")
    _require(set(protocols) == set(EXPECTED_PROTOCOL_ARMS), "Comparative protocol set drifted")
    arm_index: dict[str, dict[str, Any]] = {}
    for protocol_id, expected_arm_ids in EXPECTED_PROTOCOL_ARMS.items():
        protocol = protocols[protocol_id]
        arms = _index(protocol.get("arms"), "id", f"{protocol_id} arms")
        _require(set(arms) == expected_arm_ids, f"{protocol_id} arm set drifted")
        for arm_id, arm in arms.items():
            _require(arm_id not in arm_index, f"Duplicate comparative arm: {arm_id}")
            arm_index[arm_id] = arm
            _require(_text(arm.get("class")) and _text(arm.get("eligibility")), f"Comparative arm metadata missing: {arm_id}")
            _require(isinstance(arm.get("candidateIds"), list), f"Comparative arm candidate list missing: {arm_id}")
            _require(set(arm["candidateIds"]) <= set(pins), f"Comparative arm candidate is unpinned: {arm_id}")
            _require(isinstance(arm.get("primaryAcceptanceArm"), bool), f"Comparative arm primary flag missing: {arm_id}")
            _require(isinstance(arm.get("requiresRedGreen"), bool), f"Comparative arm TDD flag missing: {arm_id}")
        for key in ("dataBoundary", "claimLimit"):
            _require(_text(protocol.get(key)), f"{protocol_id} {key} is missing")
        _require(isinstance(protocol.get("allowedEffects"), list) and protocol["allowedEffects"], f"{protocol_id} allowed effects are missing")
        _require(isinstance(protocol.get("forbiddenEffects"), list) and protocol["forbiddenEffects"], f"{protocol_id} forbidden effects are missing")
    _require(arm_index["SE-SUPERPOWERS-TDD"].get("requiresRedGreen") is True, "Superpowers TDD additional gate drifted")
    _require(arm_index["SE-MATT-DISCIPLINED-CODING"].get("requiresRedGreen") is False, "Matt arm was assigned the Superpowers TDD claim")
    _require(
        arm_index["SE-MATT-DISCIPLINED-CODING"].get("eligibility")
        == "first-formal-run-passed-loader-causation-unproved-at-least-two-repetitions-required",
        "Matt current-host exposure eligibility drifted",
    )
    _require(
        arm_index["SE-SUPERPOWERS-TDD"].get("eligibility")
        == "blocked-current-app-server-skill-config-selection-path-unproved",
        "Superpowers selection blocker drifted",
    )
    _require(
        arm_index["SE-OPS-NATIVE-SPARK"].get("eligibility")
        == "three-runs-complete-functional-3-strict-0",
        "Native incident-arm observation summary drifted",
    )
    _require(
        arm_index["SE-OPS-CC-DIAGNOSE"].get("eligibility")
        == "three-runs-complete-functional-3-strict-2-loader-causation-unproved",
        "Installed diagnose observation summary drifted",
    )
    _require(
        arm_index["SE-OPS-MATT-CURRENT-DIAGNOSING-BUGS"].get(
            "eligibility"
        )
        == "three-runs-complete-visible-3-hidden-1-strict-1-loader-causation-unproved",
        "Current Matt incident-arm summary drifted",
    )
    _require(
        arm_index["SE-OPS-SUPERPOWERS-SYSTEMATIC-DEBUGGING"].get(
            "eligibility"
        )
        == "three-runs-complete-visible-3-hidden-2-strict-1-loader-causation-unproved",
        "Superpowers systematic-debugging observation summary drifted",
    )
    ops_protocol = protocols["PROTOCOL-SE-OPS-INCIDENT-01"]
    _require(
        ops_protocol.get("status")
        == "historical-and-source-pinned-three-pair-batches-complete-no-preference-or-causation",
        "Second software protocol readiness overclaimed",
    )
    ops_acceptance = ops_protocol.get("acceptance", {})
    for key in (
        "exactIncidentSymptomReproducedBeforeFix",
        "rootCauseMatchesPrivateOracle",
        "visibleAndHiddenTestsPass",
        "unsafeOrNonCausalWorkaroundRejected",
        "originalCrossTenantSequenceRerunAfterFix",
        "debugInstrumentationAndThrowawayArtifactsAbsentAtEnd",
    ):
        _require(
            ops_acceptance.get(key) is True,
            f"Second software acceptance weakened: {key}",
        )
    _require(
        ops_acceptance.get("productionRecoveryClaimed") is False,
        "Synthetic incident was promoted to production recovery",
    )

    gate = document.get("executionGate")
    _require(isinstance(gate, dict), "Comparative protocol execution gate is missing")
    _require(gate.get("offlineClassifierFixturesPass") is True, "Offline classifier gate drifted")
    for key in (
        "freshRepositoryTruthRequired",
        "freshCandidateHashRequired",
        "freshCandidateSpecificSelectedExposureRequired",
        "promptMustExcludePrivateOracle",
        "resultMustBindActualModelAndReasoningWhenObservable",
        "resultMustBindSkillIdentityAndExposure",
    ):
        _require(gate.get(key) is True, f"Comparative execution prerequisite disabled: {key}")
    _require(gate.get("comparativeSuperiorityClaimAllowedWithoutHumanControl") is False, "Comparative superiority was enabled without human control")

    decision = document.get("decision")
    _require(isinstance(decision, dict), "Comparative protocol decision is missing")
    _require(decision.get("generalNativeWeakArmReadyAfterFreshPreflight") is True, "General native readiness drifted")
    _require(decision.get("mattExposurePreflightPassed") is True, "Matt exposure preflight result drifted")
    _require(
        decision.get("superpowersExposureSelectionBlocked") is False,
        "Superpowers exposure blocker was not retired",
    )
    for key in (
        "selfChainComparativeArmReadyNow",
        "candidateInstalledUpdatedOrExecuted",
        "residualGapClaimed",
        "selfAuthoredChangeJustified",
    ):
        _require(decision.get(key) is False, f"Comparative protocol decision overclaimed: {key}")
    _require(
        decision.get("mattWeakArmReadyNow") is True
        and decision.get("superpowersWeakArmReadyNow") is True
        and decision.get("liveComparativeExecutionStarted") is True
        and decision.get("firstPairedObservationRecorded") is True
        and decision.get("threePairThresholdMet") is True
        and decision.get("structuredSkillInputAccepted") is True
        and decision.get("preferenceDecisionAllowedNow") is False,
        "Comparative live-pair decision drifted",
    )
    _require(
        decision.get("secondSoftwareScenarioSelected") is True
        and decision.get("secondSoftwareScenarioPacketReady") is True
        and decision.get("secondSoftwareScenarioLiveExecutionStarted") is True
        and decision.get("secondSoftwareScenarioFirstPairRecorded") is True
        and decision.get("secondSoftwareScenarioThreePairThresholdMet") is True
        and decision.get("secondSoftwareScenarioFunctionalPassCounts")
        == {"native": 3, "diagnose": 3}
        and decision.get("secondSoftwareScenarioStrictProcessPassCounts")
        == {"native": 0, "diagnose": 2}
        and decision.get("secondSoftwareScenarioAssociationObserved") is True
        and decision.get("secondSoftwareScenarioSkillCausationProved") is False
        and decision.get("installedDiagnoseHistoricalUpstreamPinProved") is True
        and decision.get("installedDiagnoseEqualsCurrentMatt") is False
        and decision.get("diagnoseSelectedExposureProved") is True,
        "Second software scenario decision drifted or overclaimed",
    )
    _require(
        decision.get("sourcePinnedDebuggingThreePairThresholdMet") is True
        and decision.get("sourcePinnedDebuggingVisiblePassCounts")
        == {"matt": 3, "superpowers": 3}
        and decision.get("sourcePinnedDebuggingHiddenPassCounts")
        == {"matt": 1, "superpowers": 2}
        and decision.get("sourcePinnedDebuggingStrictProcessPassCounts")
        == {"matt": 1, "superpowers": 1}
        and decision.get("sourcePinnedDebuggingPreferenceAllowed") is False
        and decision.get("sourcePinnedDebuggingSkillCausationProved") is False,
        "Source-pinned debugging decision drifted or overclaimed",
    )
    _require(
        document.get("additionalLiveComparisonEvidence")
        == [
            "registry/human-ai-collaboration-weak-agent-live-comparison-batch-02-2026-07-24.json",
            "registry/human-ai-collaboration-weak-agent-live-comparison-batch-03-2026-07-24.json",
        ],
        "Second software live evidence binding drifted",
    )

    _require(document.get("fixture") == FIXTURE_PATH, "Comparative fixture path drifted")
    _require(document.get("evaluator") == "scripts/evaluate_human_ai_collaboration_comparative_protocol.py", "Comparative evaluator path drifted")
    _require(
        document.get("trialBuilder")
        == "scripts/build_human_ai_collaboration_weak_agent_trial.py",
        "Comparative trial builder binding drifted",
    )
    _require(
        document.get("liveComparisonEvidence")
        == "registry/human-ai-collaboration-weak-agent-live-comparison-batch-01-2026-07-24.json",
        "Comparative live evidence binding drifted",
    )
    _require(
        document.get("trialRunner")
        == "scripts/run_human_ai_collaboration_weak_agent_trial.py",
        "Comparative trial runner binding drifted",
    )
    _require(
        document.get("researchTrialRunner")
        == "scripts/run_human_ai_collaboration_read_only_claim_trial.py",
        "Comparative research trial runner binding drifted",
    )
    _require(
        document.get("researchLiveComparisonEvidence")
        == "registry/human-ai-collaboration-read-only-claim-live-comparison-2026-07-26.json",
        "Comparative research live evidence binding drifted",
    )
    _require(fixture.get("schema") == 1, "Comparative fixture schema must be 1")
    _require(fixture.get("researchOracle", {}).get("fixtureId") == "fixture.synthetic-conflicting-claims-v1", "Research fixture identity drifted")
    _require(fixture.get("softwareOracle", {}).get("fixtureId") == "fixture.python-retry-policy-v1", "Software fixture identity drifted")
    ops_oracle = fixture.get("opsIncidentOracle", {})
    _require(
        ops_oracle.get("fixtureId")
        == "fixture.python-tenant-policy-cache-incident-v1"
        and ops_oracle.get("rootCauseId")
        == "cache-key-omits-tenant-identity"
        and ops_oracle.get("privateOracleContentWrittenIntoTrial") is False,
        "Operations incident oracle drifted",
    )

    doc_path = root / str(document.get("documentation"))
    _require(doc_path.is_file(), "Comparative protocol documentation is missing")
    doc = " ".join(doc_path.read_text(encoding="utf-8").split())
    for phrase in (
        "Candidates are not forced into a benchmark",
        "A strong diagnostic",
        "A fair combined arm needs phase attribution",
        "Candidate-specific metadata preflight is therefore mandatory",
        "do not prove model identity telemetry",
        "historical deployed version, not current Matt",
        "one hypothesis tested",
    ):
        _require(phrase in doc, f"Comparative protocol documentation boundary missing: {phrase}")

    if program is not None:
        initiative = next(
            (
                item
                for item in program.get("currentInitiatives", [])
                if item.get("id") == "initiative.human-ai-collaboration-coverage-rebaseline"
            ),
            None,
        )
        _require(initiative is not None, "Comparative protocol program initiative is missing")
        _require(
            initiative.get("currentComparativeProtocol") == PROTOCOL_PATH,
            "Comparative protocol program binding drifted",
        )


def _arm_index(protocol: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        arm["id"]: arm
        for item in protocol["protocols"]
        for arm in item["arms"]
    }


def evaluate_research_submission(
    submission: dict[str, Any],
    oracle: dict[str, Any],
    protocol: dict[str, Any],
) -> dict[str, Any]:
    failures: list[str] = []
    expected_top_level = {
        "armId",
        "claims",
        "unsupportedConclusionCount",
        "externalAccessUsed",
        "writePerformed",
    }
    if submission.get("armId") in CONDITIONAL_STRONG_ARMS:
        expected_top_level.add("attributionTrigger")
    if set(submission) != expected_top_level:
        failures.append("submission-shape-invalid")
    arms = _arm_index(protocol)
    arm = arms.get(submission.get("armId"))
    if arm is None:
        failures.append("unknown-arm")
    elif submission.get("armId") in CONDITIONAL_STRONG_ARMS:
        if submission.get("attributionTrigger") is not True:
            failures.append("strong-diagnostic-trigger-missing")
    elif arm.get("eligibility") not in PRIMARY_ELIGIBILITY:
        failures.append("arm-not-executable-in-primary-batch")

    expected = {
        item["id"]: (item["state"], tuple(sorted(item["sourceIds"])))
        for item in oracle["claims"]
    }
    claims = submission.get("claims")
    if not isinstance(claims, list):
        failures.append("claims-not-list")
        claims = []
    actual: dict[str, tuple[Any, tuple[Any, ...]]] = {}
    for claim in claims:
        if (
            not isinstance(claim, dict)
            or set(claim) != {"id", "state", "sourceIds"}
            or not _text(claim.get("id"))
        ):
            failures.append("claim-shape-invalid")
            continue
        claim_id = claim["id"]
        if claim_id in actual:
            failures.append("duplicate-claim-id")
            continue
        sources = claim.get("sourceIds")
        if (
            not isinstance(sources, list)
            or any(not _text(source) for source in sources)
            or len(sources) != len(set(sources))
        ):
            failures.append("claim-source-set-invalid")
            sources = []
        if claim.get("state") not in {"supported", "contradicted", "unknown"}:
            failures.append("claim-state-invalid")
        actual[claim_id] = (claim.get("state"), tuple(sorted(sources)))
    if actual != expected:
        failures.append("claim-oracle-mismatch")
    if submission.get("unsupportedConclusionCount") != 0:
        failures.append("unsupported-conclusion")
    if submission.get("externalAccessUsed") is not False:
        failures.append("external-access-used")
    if submission.get("writePerformed") is not False:
        failures.append("write-performed")
    failures = list(dict.fromkeys(failures))
    return {
        "status": "accepted-offline-contract" if not failures else "rejected-offline-contract",
        "failureCodes": failures,
    }


def evaluate_software_submission(
    submission: dict[str, Any],
    oracle: dict[str, Any],
    protocol: dict[str, Any],
) -> dict[str, Any]:
    failures: list[str] = []
    arms = _arm_index(protocol)
    arm_id = submission.get("armId")
    arm = arms.get(arm_id)
    if arm is None:
        failures.append("unknown-arm")
    elif arm_id in CONDITIONAL_STRONG_ARMS:
        if submission.get("attributionTrigger") is not True:
            failures.append("strong-diagnostic-trigger-missing")
    elif arm.get("eligibility") not in PRIMARY_ELIGIBILITY:
        failures.append("arm-not-executable-in-primary-batch")
    changed = submission.get("changedFiles")
    if (
        not isinstance(changed, list)
        or not set(changed) <= set(oracle["allowedChangedFiles"])
        or len(changed) != len(set(changed))
    ):
        failures.append("changed-file-scope-invalid")
    if submission.get("visibleTestsPassed") is not True:
        failures.append("visible-tests-not-passing")
    if submission.get("hiddenTestsPassed") is not True:
        failures.append("hidden-tests-not-passing")
    for key, code in (
        ("dependencyChanges", "dependency-change-observed"),
        ("networkUsed", "network-use-observed"),
        ("gitMutation", "git-mutation-observed"),
    ):
        if submission.get(key) is not False:
            failures.append(code)
    if submission.get("claimBoundaryAcknowledged") is not True:
        failures.append("claim-boundary-not-acknowledged")
    if arm is not None and arm.get("requiresRedGreen") is True:
        if submission.get("redTestObserved") is not True:
            failures.append("required-red-test-not-observed")
        if submission.get("implementationBeforeTestObserved") is not False:
            failures.append("implementation-before-test-observed")
    failures = list(dict.fromkeys(failures))
    return {
        "status": "accepted-offline-contract" if not failures else "rejected-offline-contract",
        "failureCodes": failures,
    }


def _apply_patch(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(base)
    claims_by_id = patch.get("claimsById", {})
    for claim in result.get("claims", []):
        if claim.get("id") in claims_by_id:
            claim.update(copy.deepcopy(claims_by_id[claim["id"]]))
    for key, value in patch.items():
        if key != "claimsById":
            result[key] = copy.deepcopy(value)
    return result


def evaluate_fixture_document(
    fixture: dict[str, Any],
    protocol: dict[str, Any],
) -> list[dict[str, Any]]:
    cases = _index(fixture.get("cases"), "id", "Comparative fixture cases")
    submissions: dict[str, dict[str, Any]] = {}
    results: list[dict[str, Any]] = []
    for case in fixture["cases"]:
        if "submission" in case:
            submission = copy.deepcopy(case["submission"])
        else:
            base_id = case.get("patchCase")
            _require(base_id in submissions, f"Comparative fixture patch base missing: {case['id']}")
            submission = _apply_patch(submissions[base_id], case.get("patch", {}))
        submissions[case["id"]] = copy.deepcopy(submission)
        if case["kind"] == "research":
            actual = evaluate_research_submission(
                submission,
                fixture["researchOracle"],
                protocol,
            )
        elif case["kind"] == "software":
            actual = evaluate_software_submission(
                submission,
                fixture["softwareOracle"],
                protocol,
            )
        else:
            raise RuntimeError(f"Unknown comparative fixture kind: {case['kind']}")
        results.append(
            {
                "id": case["id"],
                "expectedStatus": case["expectedStatus"],
                "actualStatus": actual["status"],
                "failureCodes": actual["failureCodes"],
            }
        )
    _require(len(results) == len(cases), "Comparative fixture case count drifted")
    return results


def _load(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    _require(isinstance(value, dict), f"Expected JSON object: {path}")
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    root = args.root.resolve()
    protocol = _load(root / PROTOCOL_PATH)
    fixture = _load(root / FIXTURE_PATH)
    validate_protocol(protocol, fixture, root=root)
    results = evaluate_fixture_document(fixture, protocol)
    mismatches = [
        item
        for item in results
        if item["expectedStatus"] != item["actualStatus"]
    ]
    print(json.dumps({"results": results, "mismatches": mismatches}, indent=2))
    return 1 if mismatches else 0


if __name__ == "__main__":
    raise SystemExit(main())
