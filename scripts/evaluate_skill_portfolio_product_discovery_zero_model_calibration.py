#!/usr/bin/env python3
"""Evaluate the source-free product-discovery effect fixture."""

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
    "registry/skill-portfolio-product-discovery-zero-model-protocol-2026-08-03.json"
)
FIXTURE_PATH = (
    "tests/fixtures/skill-portfolio-product-discovery-zero-model-calibration-"
    "2026-08-03.json"
)
REQUIRED_FAULT_CLASSES = {
    "consent-boundary-loss",
    "evidence-linkage-omission",
    "leading-language-introduction",
    "opportunity-solution-traceability-omission",
    "uncertainty-suppression",
}
EXPECTED_OVERRIDE_BY_FAULT: dict[str, dict[str, Any]] = {
    "control": {},
    "evidence-linkage-omission": {"evidenceLinks": []},
    "leading-language-introduction": {
        "interviewPrompts": [
            {
                "promptId": "prompt.confirm-partial-cancellation-demand",
                "mode": "future-hypothetical",
                "leading": True,
            }
        ]
    },
    "consent-boundary-loss": {
        "consentBoundary": {
            "recordingRequiresExplicitConsent": False,
            "outreachAuthorized": True,
            "retentionPolicyRequiredBeforeCollection": False,
        }
    },
    "opportunity-solution-traceability-omission": {
        "opportunitySolutionTrace": []
    },
    "uncertainty-suppression": {"uncertaintyIds": []},
}
EXPECTED_DIMENSION_IDS = [
    "evidence-linkage",
    "anti-leading-language",
    "consent-boundary",
    "outcome-opportunity-solution-traceability",
    "uncertainty-visibility",
]
EXPECTED_CANDIDATES = [
    {
        "name": "interview-script",
        "path": "pm-product-discovery/skills/interview-script/SKILL.md",
        "sha256": "892ca53da9852d4e6516d2305f0c0eb2db370bf39693c6c6797154b44bec9b4c",
        "bytes": 4817,
        "eligibleDimensionIds": [
            "evidence-linkage",
            "anti-leading-language",
            "consent-boundary",
            "uncertainty-visibility",
        ],
        "currentAlternativeIds": [
            "native.interview-planning",
            "managed.grilling",
        ],
    },
    {
        "name": "opportunity-solution-tree",
        "path": "pm-product-discovery/skills/opportunity-solution-tree/SKILL.md",
        "sha256": "6b23e44a5ace86aa20d64cc130322265ace6a53a29831cc403b974098a379bcc",
        "bytes": 4281,
        "eligibleDimensionIds": [
            "evidence-linkage",
            "outcome-opportunity-solution-traceability",
            "uncertainty-visibility",
        ],
        "currentAlternativeIds": [
            "native.structured-mapping",
            "official.figma-diagram-generation",
        ],
    },
]


def _validate_protocol_and_fixture(
    protocol: dict[str, Any],
    fixture: dict[str, Any],
    *,
    root: Path,
) -> None:
    _require(
        protocol.get("id")
        == "skill-portfolio-product-discovery-zero-model-protocol-2026-08-03"
        and protocol.get("status")
        == "frozen-zero-model-product-discovery-effect-calibration-protocol"
        and protocol.get("effectGroupId") == "effect.product-discovery"
        and protocol.get("scenarioId") == "SE-DISCOVERY-REQ-01",
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
    parent_fixture = fixture.get("parentScenarioBinding")
    _require(
        fixture.get("status") == "frozen-source-free-product-discovery-effect-fixture"
        and fixture.get("effectGroupId") == "effect.product-discovery"
        and isinstance(parent_fixture, dict)
        and parent_fixture.get("scenarioId") == "SE-DISCOVERY-REQ-01"
        and parent_fixture.get("protocolPath") == bindings[2]["path"]
        and parent_fixture.get("fixturePath") == bindings[3]["path"]
        and parent_fixture.get("parentProtocolReused") is True
        and parent_fixture.get("parentFixtureReused") is True
        and parent_fixture.get("fullScenarioDuplicated") is False,
        "Parent fixture reuse boundary drifted",
    )
    parent_reuse = protocol.get("parentReuse")
    _require(
        isinstance(parent_reuse, dict)
        and parent_reuse.get("parentScenarioId") == "SE-DISCOVERY-REQ-01"
        and parent_reuse.get("parentProtocolReused") is True
        and parent_reuse.get("parentFixtureReused") is True
        and parent_reuse.get("parentProtocolOrLiveComparisonReexecutedByThisEvaluator")
        is False
        and parent_reuse.get("fullScenarioFixtureCreated") is False,
        "Parent protocol reuse boundary drifted",
    )

    history = protocol.get("historicalEvidenceBoundary")
    _require(
        isinstance(history, dict)
        and history.get("historicalComparedCandidate") == "cc.grill-with-docs"
        and history.get("historicalComparedCandidateIsCurrentCandidate") is False
        and history.get("bothHistoricalArmsPassedHiddenContract") is False
        and history.get("historicalComparisonPromotedToCurrentExactCandidateProof")
        is False
        and history.get("historicalComparisonPromotedToProductDiscoveryCompetence")
        is False
        and history.get("historicalComparisonPromotedToPreference") is False,
        "Historical comparison boundary drifted",
    )
    parent_protocol = _load(root / bindings[2]["path"])
    candidate_arm = next(
        (
            arm
            for arm in parent_protocol.get("arms", [])
            if arm.get("id") == "SE-REQ-CC-GRILL-WITH-DOCS"
        ),
        None,
    )
    _require(
        parent_protocol.get("scenarioId") == "SE-DISCOVERY-REQ-01"
        and isinstance(candidate_arm, dict)
        and candidate_arm.get("selectedUserSkills") == ["cc.grill-with-docs"],
        "Historical compared candidate drifted",
    )
    live_comparison = _load(root / bindings[4]["path"])
    aggregate = live_comparison.get("aggregateResult")
    _require(
        live_comparison.get("scenarioId") == "SE-DISCOVERY-REQ-01"
        and live_comparison.get("status")
        == "three-valid-pairs-both-arms-fail-hidden-contract-no-preference-or-causation"
        and isinstance(aggregate, dict)
        and aggregate.get("fullHiddenContractPassCount")
        == {"native": 0, "candidate": 0}
        and aggregate.get("candidateDemonstratedBoundedAddedValue") is False
        and aggregate.get("associationSupportsGeneralNativePreference") is False
        and aggregate.get("associationSupportsCandidatePreference") is False
        and aggregate.get("candidateEffectOrCausationProved") is False,
        "Historical comparison evidence drifted",
    )

    candidate = protocol.get("candidateBoundary")
    _require(
        isinstance(candidate, dict)
        and candidate.get("repository") == "phuryn/pm-skills"
        and candidate.get("revision")
        == "18468a95b427e70e258b51389796367c6f684e7d"
        and candidate.get("tree") == "514548cbf646ce42fb9ea9a8cc901f05373ab2ff"
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
            if item.get("id") == "effect.product-discovery"
        ),
        None,
    )
    candidate_mappings = [
        item
        for item in mapping.get("candidateMappings", [])
        if item.get("effectGroupId") == "effect.product-discovery"
    ]
    _require(
        isinstance(effect_group, dict)
        and effect_group.get("candidateNames")
        == [item["name"] for item in EXPECTED_CANDIDATES]
        and effect_group.get("oracleDimensions") == EXPECTED_DIMENSION_IDS
        and effect_group.get("compositionArmEligible") is False,
        "Effect-group mapping drifted",
    )
    _require(
        [item.get("name") for item in candidate_mappings]
        == [item["name"] for item in EXPECTED_CANDIDATES]
        and all(item.get("scenarioIds") == ["SE-DISCOVERY-REQ-01"] for item in candidate_mappings)
        and all(item.get("mappingState") == "static-hypothesis-only" for item in candidate_mappings)
        and all(
            item.get("claimCeiling") == "mapping-and-protocol-design-only"
            for item in candidate_mappings
        ),
        "Candidate demand mapping drifted",
    )
    review = _load(root / bindings[1]["path"])
    reviewed_items = {
        item.get("name"): item
        for item in review.get("representativeSkills", [])
        if isinstance(item, dict)
    }
    for expected in EXPECTED_CANDIDATES:
        reviewed = reviewed_items.get(expected["name"])
        _require(
            isinstance(reviewed, dict)
            and reviewed.get("path") == expected["path"]
            and reviewed.get("sha256") == expected["sha256"]
            and reviewed.get("bytes") == expected["bytes"]
            and reviewed.get("disposition")
            == "manager-install-candidate-default-disabled-behavior-comparison-required",
            "Exact candidate static review drifted",
        )

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
                "participantContactRecordingOrDataCollectionPerformed",
                "localDiscoveryArtifactWrittenOutsideFixture",
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
            "allFaultsMustBreachAtDiscoveryDraft": True,
            "allFaultsMustCarryAtReviewDetection": True,
            "allFaultsMustRecoverAtTerminal": True,
            "permittedStatusOnPass": (
                "product-discovery-effect-oracle-calibrated-no-candidate-behavior"
            ),
            "formalLiveEvidenceEligible": False,
        },
        "Acceptance boundary drifted",
    )


def _score_packet(packet: dict[str, Any], canonical: dict[str, Any]) -> dict[str, Any]:
    losses: list[str] = []
    for field, invariant in (
        ("evidenceLinks", "evidence-linkage"),
        ("opportunitySolutionTrace", "outcome-opportunity-solution-traceability"),
        ("uncertaintyIds", "uncertainty-visibility"),
    ):
        if packet.get(field) == []:
            losses.append(f"invariant-omitted:{invariant}")
        elif packet.get(field) != canonical[field]:
            losses.append(f"invariant-changed:{invariant}")
    for field, invariant in (
        ("interviewPrompts", "anti-leading-language"),
        ("consentBoundary", "consent-boundary"),
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
        canonical_packet_key="canonicalDiscoveryPacket",
        expected_override_by_fault=EXPECTED_OVERRIDE_BY_FAULT,
        required_fault_classes=REQUIRED_FAULT_CLASSES,
        score_packet=_score_packet,
        source_stage_id="parent-requirements-fixture-anchor",
        active_stage_id="discovery-draft",
        review_stage_id="review-detection",
        recovery_stage_id="human-product-authority-recovery",
    )
    results = matrix["results"]
    observed_faults = matrix["observedFaultClasses"]
    return {
        "outcome": "valid-zero-model-effect-calibration",
        "status": acceptance["permittedStatusOnPass"],
        "effectGroupId": "effect.product-discovery",
        "candidateCount": len(EXPECTED_CANDIDATES),
        "scenarioCount": 1,
        "caseCount": len(results),
        "faultCaseCount": len(results) - 1,
        "faultClassesCovered": sorted(observed_faults),
        "allCasesPassed": True,
        "parentRequirementsFixtureReused": True,
        "fullScenarioFixtureCreated": False,
        "historicalComparisonPromotedToCurrentCandidateProof": False,
        "formalLiveEvidenceEligible": False,
        "agentDispatchCount": 0,
        "modelCallCount": 0,
        "candidateExecutionCount": 0,
        "claimBoundary": copy.deepcopy(protocol["claimBoundary"]),
        "claimLimit": (
            "This source-free extension calibrates five product-discovery loss "
            "classes only. It does not prove current candidate behavior, historical "
            "comparison equivalence, product discovery, requirements completeness, "
            "participant consent, live exposure, value, residual gap, or hard-standard "
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
