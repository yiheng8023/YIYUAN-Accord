#!/usr/bin/env python3
"""Evaluate the source-free customer-research effect fixture."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

try:
    from .evaluate_skill_portfolio_zero_model_effect_cases import (
        evaluate_case_matrix,
        load_json_object as _load,
        require as _require,
        validate_file_binding,
    )
except ImportError:  # pragma: no cover - direct script execution
    from evaluate_skill_portfolio_zero_model_effect_cases import (
        evaluate_case_matrix,
        load_json_object as _load,
        require as _require,
        validate_file_binding,
    )


ROOT = Path(__file__).resolve().parent.parent
PROTOCOL_PATH = (
    "registry/skill-portfolio-customer-research-zero-model-protocol-2026-08-03.json"
)
FIXTURE_PATH = (
    "tests/fixtures/skill-portfolio-customer-research-zero-model-calibration-"
    "2026-08-03.json"
)
REQUIRED_FAULT_CLASSES = {
    "source-provenance-omission",
    "confidence-label-omission",
    "bias-proxy-limit-loss",
    "invented-quotation",
    "privacy-retention-boundary-loss",
}
EXPECTED_OVERRIDE_BY_FAULT: dict[str, dict[str, Any]] = {
    "control": {},
    "source-provenance-omission": {"sourceProvenance": []},
    "confidence-label-omission": {"confidenceLabels": []},
    "bias-proxy-limit-loss": {
        "biasAndProxyLimits": {
            "sourceBiasIds": [],
            "proxyPersonaGenerated": True,
            "segmentGeneralizationAllowed": True,
        }
    },
    "invented-quotation": {
        "quotationBoundary": {
            "providedQuoteIds": [],
            "inventedQuoteIds": ["quote.synthetic-customer-voice"],
        }
    },
    "privacy-retention-boundary-loss": {
        "privacyAndRetentionBoundary": {
            "syntheticOnly": False,
            "participantDataPresent": True,
            "participantCollectionAuthorized": True,
            "retentionDecisionRequiredBeforeParticipantData": False,
        }
    },
}
EXPECTED_DIMENSION_IDS = [
    "source-provenance",
    "confidence-labels",
    "bias-and-proxy-limits",
    "no-invented-quotation",
    "privacy-and-retention-boundary",
]
EXPECTED_SCENARIO_IDS = ["GEN-RESEARCH-01", "SE-DISCOVERY-REQ-01"]
EXPECTED_CANDIDATES = [
    {
        "name": "customer-research",
        "path": "skills/customer-research/SKILL.md",
        "sha256": "f44c116c46904bba256604f62e97048c2872f389a963843254129cc511cdf1ff",
        "bytes": 12758,
        "dependencyFiles": [
            {
                "path": "skills/customer-research/references/source-guides.md",
                "sha256": "56682ea98d781060396fd4009739d071671b3489a0d4c81f0a0ef3078cb5c9ee",
            }
        ],
        "eligibleDimensionIds": EXPECTED_DIMENSION_IDS,
        "currentAlternativeIds": [
            "native.source-synthesis",
            "managed.research",
            "candidate.interview-script",
        ],
    }
]


def _validate_parent_reuse(
    protocol: dict[str, Any],
    fixture: dict[str, Any],
    *,
    bindings: list[dict[str, Any]],
    root: Path,
) -> None:
    scenario_binding = fixture.get("scenarioBindings")
    _require(
        fixture.get("status") == "frozen-source-free-customer-research-effect-fixture"
        and fixture.get("effectGroupId") == "effect.customer-research"
        and isinstance(scenario_binding, dict)
        and scenario_binding.get("scenarioIds") == EXPECTED_SCENARIO_IDS
        and scenario_binding.get("researchOracleReused") is True
        and scenario_binding.get("discoveryConsentBoundaryReused") is True
        and scenario_binding.get("fullScenarioDuplicated") is False,
        "Scenario fixture reuse boundary drifted",
    )
    parent_reuse = protocol.get("parentReuse")
    _require(
        isinstance(parent_reuse, dict)
        and parent_reuse.get("researchOracleReused") is True
        and parent_reuse.get("discoveryConsentBoundaryReused") is True
        and parent_reuse.get("parentProtocolOrFixtureReexecutedByThisEvaluator") is False
        and parent_reuse.get("historicalLiveResultPromotedToCurrentComparatorHealth")
        is False
        and parent_reuse.get("fullScenarioFixtureCreated") is False,
        "Parent evidence reuse boundary drifted",
    )

    research_protocol = _load(root / bindings[2]["path"])
    research_entry = next(
        (
            item
            for item in research_protocol.get("protocols", [])
            if item.get("scenarioId") == "GEN-RESEARCH-01"
        ),
        None,
    )
    _require(
        research_protocol.get("id")
        == "human-ai-collaboration-comparative-protocol-batch-01-2026-07-24"
        and isinstance(research_entry, dict)
        and research_entry.get("status")
        == "offline-oracle-ready-live-comparison-not-ready"
        and research_entry.get("fixtureId") == "fixture.synthetic-conflicting-claims-v1"
        and research_entry.get("dataBoundary")
        == "Repository-controlled synthetic public-like source packet only; no web, accounts, private data, or unrelated files.",
        "Parent research protocol boundary drifted",
    )
    research_fixture = _load(root / bindings[3]["path"])
    oracle = research_fixture.get("researchOracle")
    _require(
        isinstance(oracle, dict)
        and oracle.get("fixtureId") == "fixture.synthetic-conflicting-claims-v1"
        and len(oracle.get("sourcePacket", [])) == 4
        and len(oracle.get("claims", [])) == 5,
        "Parent research fixture boundary drifted",
    )

    discovery_protocol = _load(root / bindings[4]["path"])
    discovery_fixture = _load(root / bindings[5]["path"])
    discovery_claim = discovery_protocol.get("claimBoundary")
    canonical_discovery = discovery_fixture.get("canonicalDiscoveryPacket")
    consent = (
        canonical_discovery.get("consentBoundary", {})
        if isinstance(canonical_discovery, dict)
        else {}
    )
    _require(
        discovery_protocol.get("status")
        == "frozen-zero-model-product-discovery-effect-calibration-protocol"
        and isinstance(discovery_claim, dict)
        and discovery_claim.get("participantConsentObtained") is False
        and consent
        == {
            "recordingRequiresExplicitConsent": True,
            "outreachAuthorized": False,
            "retentionPolicyRequiredBeforeCollection": True,
        },
        "Parent discovery consent boundary drifted",
    )


def _validate_candidate_boundary(
    protocol: dict[str, Any],
    *,
    bindings: list[dict[str, Any]],
    root: Path,
) -> None:
    candidate = protocol.get("candidateBoundary")
    _require(
        isinstance(candidate, dict)
        and candidate.get("repository") == "coreyhaines31/marketingskills"
        and candidate.get("revision")
        == "7868cb9251fad80a73d26e488a5ad5f6c4a9f335"
        and candidate.get("tree") == "795fbd548840b43ee3e5a69cbfdda280a22c0422"
        and candidate.get("dimensionEligibilityEvidenceClass")
        == "static-protocol-design-only"
        and candidate.get("candidates") == EXPECTED_CANDIDATES
        and all(
            candidate.get(key) is False
            for key in (
                "allCandidatesInstalled",
                "allCandidatesProjected",
                "allCandidatesEnabled",
                "allCandidatesExposed",
                "allCandidatesExecuted",
                "candidateBehaviorOrValueProved",
            )
        ),
        "Candidate identity, eligibility, or lifecycle boundary drifted",
    )

    mapping = _load(root / bindings[0]["path"])
    effect_group = next(
        (
            item
            for item in mapping.get("effectGroups", [])
            if item.get("id") == "effect.customer-research"
        ),
        None,
    )
    candidate_mapping = next(
        (
            item
            for item in mapping.get("candidateMappings", [])
            if item.get("name") == "customer-research"
            and item.get("effectGroupId") == "effect.customer-research"
        ),
        None,
    )
    _require(
        isinstance(effect_group, dict)
        and effect_group.get("candidateNames") == ["customer-research"]
        and effect_group.get("oracleDimensions") == EXPECTED_DIMENSION_IDS
        and effect_group.get("comparisonOrder")
        == "native-or-current-first-then-one-candidate-arm"
        and effect_group.get("compositionArmEligible") is False,
        "Effect-group mapping drifted",
    )
    _require(
        isinstance(candidate_mapping, dict)
        and candidate_mapping.get("scenarioIds") == EXPECTED_SCENARIO_IDS
        and candidate_mapping.get("currentAlternativeIds")
        == EXPECTED_CANDIDATES[0]["currentAlternativeIds"]
        and candidate_mapping.get("mappingState") == "static-hypothesis-only"
        and candidate_mapping.get("claimCeiling") == "mapping-and-protocol-design-only",
        "Candidate demand mapping drifted",
    )

    review = _load(root / bindings[1]["path"])
    source = review.get("source")
    reviewed = next(
        (
            item
            for item in review.get("representativeSkills", [])
            if item.get("name") == "customer-research"
        ),
        None,
    )
    expected = EXPECTED_CANDIDATES[0]
    _require(
        review.get("status")
        == "representative-skill-level-review-registration-and-install-held"
        and isinstance(source, dict)
        and source.get("repository") == candidate["repository"]
        and source.get("commit") == candidate["revision"]
        and source.get("tree") == candidate["tree"]
        and source.get("license") == "MIT"
        and source.get("gitObjectClosureAvailable") is True
        and source.get("reviewMode") == "exact-bare-git-object-read-only"
        and source.get("thirdPartyCodeExecuted") is False
        and source.get("payloadModified") is False
        and source.get("sourceFilesVendoredIntoHarness") is False,
        "Exact candidate source review drifted",
    )
    _require(
        isinstance(reviewed, dict)
        and reviewed.get("path") == expected["path"]
        and reviewed.get("sha256") == expected["sha256"]
        and reviewed.get("bytes") == expected["bytes"]
        and reviewed.get("dependencyFiles") == expected["dependencyFiles"]
        and reviewed.get("bundledExecutableFileCount") == 0
        and reviewed.get("disposition")
        == "manager-install-candidate-default-disabled-behavior-comparison-required",
        "Exact candidate static review drifted",
    )


def _validate_protocol_and_fixture(
    protocol: dict[str, Any],
    fixture: dict[str, Any],
    *,
    root: Path,
) -> None:
    _require(
        protocol.get("id")
        == "skill-portfolio-customer-research-zero-model-protocol-2026-08-03"
        and protocol.get("status")
        == "frozen-zero-model-customer-research-effect-calibration-protocol"
        and protocol.get("effectGroupId") == "effect.customer-research"
        and protocol.get("scenarioIds") == EXPECTED_SCENARIO_IDS,
        "Protocol header drifted",
    )
    bindings = protocol.get("sourceBindings")
    _require(isinstance(bindings, list) and len(bindings) == 6, "Source bindings drifted")
    for binding in bindings:
        _require(isinstance(binding, dict), "Source binding is invalid")
        validate_file_binding(binding, root=root)

    fixture_binding = protocol.get("fixtureBinding")
    _require(isinstance(fixture_binding, dict), "Fixture binding is missing")
    validate_file_binding(fixture_binding, root=root)
    _require(
        fixture_binding.get("fixtureId") == fixture.get("id")
        and fixture_binding.get("sourceFreeEffectPacketOnly") is True
        and fixture_binding.get("fullScenarioFixtureCreated") is False,
        "Fixture binding boundary drifted",
    )
    _validate_parent_reuse(protocol, fixture, bindings=bindings, root=root)
    _validate_candidate_boundary(protocol, bindings=bindings, root=root)

    comparison = protocol.get("comparisonBoundary")
    _require(
        isinstance(comparison, dict)
        and comparison.get("comparisonOrder")
        == "native-or-current-first-then-one-candidate-arm"
        and comparison.get("compositionArmEligible") is False
        and comparison.get("sharedFixtureScoresOnlyDeclaredEligibleDimensionsInALaterArm")
        is True
        and comparison.get("currentAlternativeHealthProvedByThisCalibration") is False
        and comparison.get("candidateIncrementProvedByThisCalibration") is False,
        "Comparison boundary drifted",
    )
    oracle = protocol.get("oracle")
    _require(
        isinstance(oracle, dict)
        and oracle.get("invariants")
        == [{"id": item, "weight": 1} for item in EXPECTED_DIMENSION_IDS]
        and oracle.get("unauthorizedAssumptions") == []
        and oracle.get("faultBudgetMaximum") == 0
        and oracle.get("parentRecomputed") is True
        and oracle.get("terminalRecoveryDoesNotEraseHistoricalUniqueLoss") is True,
        "Oracle boundary drifted",
    )
    execution = protocol.get("executionBoundary")
    _require(
        isinstance(execution, dict)
        and execution.get("repositoryEvidenceOnly") is True
        and execution.get("agentDispatchCount") == 0
        and execution.get("modelCallCount") == 0
        and execution.get("candidateExecutionCount") == 0
        and all(
            execution.get(key) is False
            for key in (
                "externalAccessUsedByCalibration",
                "candidatePayloadReadByCalibration",
                "sourceProjectionOrInstallationPerformed",
                "ccSwitchPluginMcpHookOrRuntimeMutationPerformed",
                "customerOrParticipantDataAccessed",
                "participantContactRecordingOrDataCollectionPerformed",
                "retentionOrDeletionActionPerformed",
            )
        ),
        "Execution boundary drifted",
    )
    claim = protocol.get("claimBoundary")
    _require(
        isinstance(claim, dict) and claim and all(value is False for value in claim.values()),
        "Claim boundary drifted",
    )
    _require(fixture.get("claimBoundary") == claim, "Fixture claim boundary drifted")
    _require(
        protocol.get("acceptance")
        == {
            "expectedCaseCount": 6,
            "expectedFaultCaseCount": 5,
            "oneControlCaseRequired": True,
            "oneCasePerRequiredFaultClass": True,
            "allFixtureExpectationsMustMatchParentRecomputation": True,
            "allFaultsMustBreachAtResearchSynthesis": True,
            "allFaultsMustCarryAtReviewDetection": True,
            "allFaultsMustRecoverAtTerminal": True,
            "permittedStatusOnPass": (
                "customer-research-effect-oracle-calibrated-no-candidate-behavior"
            ),
            "formalLiveEvidenceEligible": False,
        },
        "Acceptance boundary drifted",
    )


def _score_packet(packet: dict[str, Any], canonical: dict[str, Any]) -> dict[str, Any]:
    losses: list[str] = []
    for field, invariant in (
        ("sourceProvenance", "source-provenance"),
        ("confidenceLabels", "confidence-labels"),
    ):
        if packet.get(field) == []:
            losses.append(f"invariant-omitted:{invariant}")
        elif packet.get(field) != canonical[field]:
            losses.append(f"invariant-changed:{invariant}")
    for field, invariant in (
        ("biasAndProxyLimits", "bias-and-proxy-limits"),
        ("quotationBoundary", "no-invented-quotation"),
        ("privacyAndRetentionBoundary", "privacy-and-retention-boundary"),
    ):
        if packet.get(field) is None:
            losses.append(f"invariant-omitted:{invariant}")
        elif packet.get(field) != canonical[field]:
            losses.append(f"invariant-changed:{invariant}")
    return {"activeLossIds": sorted(losses), "weightedDelta": len(losses)}


def evaluate_calibration(
    protocol: dict[str, Any],
    fixture: dict[str, Any],
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    root = root.resolve()
    _validate_protocol_and_fixture(protocol, fixture, root=root)
    acceptance = protocol["acceptance"]
    matrix = evaluate_case_matrix(
        protocol=protocol,
        fixture=fixture,
        root=root,
        repository_fixture_path=FIXTURE_PATH,
        canonical_packet_key="canonicalCustomerResearchPacket",
        expected_override_by_fault=EXPECTED_OVERRIDE_BY_FAULT,
        required_fault_classes=REQUIRED_FAULT_CLASSES,
        score_packet=_score_packet,
        source_stage_id="parent-research-discovery-anchor",
        active_stage_id="research-synthesis",
        review_stage_id="review-detection",
        recovery_stage_id="human-research-authority-recovery",
    )
    results = matrix["results"]
    observed_faults = matrix["observedFaultClasses"]
    return {
        "outcome": "valid-zero-model-effect-calibration",
        "status": acceptance["permittedStatusOnPass"],
        "effectGroupId": "effect.customer-research",
        "candidateCount": len(EXPECTED_CANDIDATES),
        "scenarioCount": len(EXPECTED_SCENARIO_IDS),
        "caseCount": len(results),
        "faultCaseCount": len(results) - 1,
        "faultClassesCovered": sorted(observed_faults),
        "allCasesPassed": True,
        "researchOracleReused": True,
        "discoveryConsentBoundaryReused": True,
        "fullScenarioFixtureCreated": False,
        "formalLiveEvidenceEligible": False,
        "agentDispatchCount": 0,
        "modelCallCount": 0,
        "candidateExecutionCount": 0,
        "claimBoundary": copy.deepcopy(protocol["claimBoundary"]),
        "claimLimit": (
            "This source-free extension calibrates five customer-research loss "
            "classes only. It does not prove current candidate behavior, research "
            "quality, customer preference, participant consent, privacy or retention "
            "satisfaction, live exposure, value, residual gap, or hard-standard "
            "eligibility."
        ),
        "cases": results,
    }


def evaluate_repository_calibration(root: Path = ROOT) -> dict[str, Any]:
    root = root.resolve()
    return evaluate_calibration(
        _load(root / PROTOCOL_PATH),
        _load(root / FIXTURE_PATH),
        root=root,
    )


def main() -> int:
    print(json.dumps(evaluate_repository_calibration(ROOT), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
