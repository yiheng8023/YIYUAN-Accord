#!/usr/bin/env python3
"""Evaluate the source-free marketing-writing effect fixture."""

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
    "registry/skill-portfolio-marketing-writing-zero-model-protocol-2026-08-03.json"
)
FIXTURE_PATH = (
    "tests/fixtures/skill-portfolio-marketing-writing-zero-model-calibration-"
    "2026-08-03.json"
)
REQUIRED_FAULT_CLASSES = {
    "source-intent-distortion",
    "claim-support-omission",
    "audience-fit-loss",
    "alternative-cta-omission",
    "fabricated-testimonial",
}
EXPECTED_OVERRIDE_BY_FAULT: dict[str, dict[str, Any]] = {
    "control": {},
    "source-intent-distortion": {
        "sourceAndIntent": {
            "sourceIds": [],
            "intentId": "intent.guarantee-category-leadership",
            "preserved": False,
        }
    },
    "claim-support-omission": {"claims": []},
    "audience-fit-loss": {
        "audience": {
            "audienceId": "audience.everyone",
            "needIds": [],
            "assumedWithoutSource": True,
        }
    },
    "alternative-cta-omission": {"ctaAlternatives": []},
    "fabricated-testimonial": {
        "testimonialBoundary": {
            "providedTestimonialIds": [],
            "inventedTestimonialIds": ["testimonial.fictional-customer-quote"],
        }
    },
}
EXPECTED_DIMENSION_IDS = [
    "source-and-intent-preservation",
    "claim-support",
    "audience-fit",
    "alternative-cta-quality",
    "no-fabricated-testimonial",
]
EXPECTED_CANDIDATES = [
    {
        "name": "copywriting",
        "path": "skills/copywriting/SKILL.md",
        "sha256": "ecdaabca28863d1472f79ba637842fdf4ac2fd9acc92b215ab7f152e757b2a33",
        "bytes": 7627,
        "dependencyFiles": [
            {
                "path": "skills/copywriting/references/copy-frameworks.md",
                "sha256": "f387b6ed4b510efa9f0d3c459f4898971c8b0176e8c34185040cb264eca50186",
            },
            {
                "path": "skills/copywriting/references/natural-transitions.md",
                "sha256": "4ff23f8943af2f65b072f26f1c53ce55f19cc26d7be211c11cae8e34b43e859f",
            },
        ],
        "eligibleDimensionIds": EXPECTED_DIMENSION_IDS,
        "currentAlternativeIds": [
            "native.writing",
            "official.creative-production",
            "managed.edit-article",
        ],
    },
    {
        "name": "copy-editing",
        "path": "skills/copy-editing/SKILL.md",
        "sha256": "9b5a20be3dc5513c8f0b4f4c4960857e4d28ed83698a5b33c8dde9dc75a47bf6",
        "bytes": 15000,
        "dependencyFiles": [
            {
                "path": "skills/copy-editing/references/checklist.md",
                "sha256": "db143b969b45b0933fe6eb772992890d1472d036a6c887fc98665e4fb48da43c",
            },
            {
                "path": "skills/copy-editing/references/content-refresh.md",
                "sha256": "8a3a2d301bb2b8b2a780f5bef43093ab42295041b2fea2a9caeca2421ef3c79b",
            },
            {
                "path": "skills/copy-editing/references/plain-english-alternatives.md",
                "sha256": "df4f820d4c63ae8a517c64a243c101658352cd07d002355bf3c97de0a00f3775",
            },
        ],
        "eligibleDimensionIds": [
            "source-and-intent-preservation",
            "claim-support",
            "audience-fit",
            "no-fabricated-testimonial",
        ],
        "currentAlternativeIds": [
            "native.editing",
            "managed.edit-article",
            "candidate.copywriting",
        ],
    },
]
EXPECTED_SCENARIO_IDS = ["GEN-ACCESS-COMMS-01", "GEN-CREATIVE-01"]


def _validate_protocol_and_fixture(
    protocol: dict[str, Any],
    fixture: dict[str, Any],
    *,
    root: Path,
) -> None:
    _require(
        protocol.get("id")
        == "skill-portfolio-marketing-writing-zero-model-protocol-2026-08-03"
        and protocol.get("status")
        == "frozen-zero-model-marketing-writing-effect-calibration-protocol"
        and protocol.get("effectGroupId") == "effect.marketing-writing"
        and protocol.get("scenarioIds") == EXPECTED_SCENARIO_IDS,
        "Protocol header drifted",
    )
    bindings = protocol.get("sourceBindings")
    _require(isinstance(bindings, list) and len(bindings) == 7, "Source bindings drifted")
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
    scenario_binding = fixture.get("scenarioBindings")
    _require(
        fixture.get("status") == "frozen-source-free-marketing-writing-effect-fixture"
        and fixture.get("effectGroupId") == "effect.marketing-writing"
        and isinstance(scenario_binding, dict)
        and scenario_binding.get("scenarioIds") == EXPECTED_SCENARIO_IDS
        and scenario_binding.get("creativePreferencePacketReused") is True
        and scenario_binding.get("accessCommsBoundaryReused") is True
        and scenario_binding.get("fullScenarioDuplicated") is False,
        "Scenario fixture reuse boundary drifted",
    )
    parent_reuse = protocol.get("parentReuse")
    _require(
        isinstance(parent_reuse, dict)
        and parent_reuse.get("creativePreferencePacketReused") is True
        and parent_reuse.get("accessCommsBoundaryReused") is True
        and parent_reuse.get("parentBaselineProtocolOrFixtureReexecutedByThisEvaluator")
        is False
        and parent_reuse.get("userPreferenceGeneralizedBeyondPacket") is False
        and parent_reuse.get("fullScenarioFixtureCreated") is False,
        "Parent evidence reuse boundary drifted",
    )
    creative_baseline = _load(root / bindings[2]["path"])
    access_baseline = _load(root / bindings[4]["path"])
    _require(
        creative_baseline.get("id")
        == "human-ai-collaboration-creative-capability-baseline-2026-07-31"
        and creative_baseline.get("status")
        == "source-bound-static-capability-baseline-no-live-creative-rights-admission-or-standard-evidence",
        "Creative baseline boundary drifted",
    )
    _require(
        access_baseline.get("id")
        == "human-ai-collaboration-access-comms-capability-baseline-2026-07-31"
        and access_baseline.get("status")
        == "source-bound-static-capability-baseline-no-live-translation-accessibility-recipient-admission-or-standard-evidence",
        "Access and communications baseline boundary drifted",
    )

    heuristic = protocol.get("heuristicEvidenceBoundary")
    _require(
        isinstance(heuristic, dict)
        and heuristic.get("copyEditingSimulatedPanelMayExistUpstream") is True
        and heuristic.get("simulatedPanelTreatedAsIndependentExpertEvidence") is False
        and heuristic.get("simulatedPanelTreatedAsPublicationAcceptance") is False
        and heuristic.get("marketingCopyQualityScoreTreatedAsBusinessOutcome") is False,
        "Heuristic evidence boundary drifted",
    )

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
            if item.get("id") == "effect.marketing-writing"
        ),
        None,
    )
    candidate_mappings = [
        item
        for item in mapping.get("candidateMappings", [])
        if item.get("effectGroupId") == "effect.marketing-writing"
    ]
    _require(
        isinstance(effect_group, dict)
        and effect_group.get("candidateNames")
        == [item["name"] for item in EXPECTED_CANDIDATES]
        and effect_group.get("oracleDimensions") == EXPECTED_DIMENSION_IDS
        and effect_group.get("comparisonOrder")
        == "native-or-current-first-then-one-candidate-arm"
        and effect_group.get("compositionArmEligible") is False,
        "Effect-group mapping drifted",
    )
    _require(
        [item.get("name") for item in candidate_mappings]
        == [item["name"] for item in EXPECTED_CANDIDATES]
        and all(item.get("scenarioIds") == ["GEN-CREATIVE-01", "GEN-ACCESS-COMMS-01"] for item in candidate_mappings)
        and all(item.get("mappingState") == "static-hypothesis-only" for item in candidate_mappings)
        and all(
            item.get("claimCeiling") == "mapping-and-protocol-design-only"
            for item in candidate_mappings
        ),
        "Candidate demand mapping drifted",
    )
    review = _load(root / bindings[1]["path"])
    source = review.get("source")
    _require(
        review.get("id")
        == "skill-portfolio-coreyhaines-marketing-representative-adjudication-2026-08-03"
        and review.get("status")
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
            and reviewed.get("dependencyFiles") == expected["dependencyFiles"]
            and reviewed.get("bundledExecutableFileCount") == 0
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
                "customerDataOrLanguageAccessed",
                "copyPublishedSentOrExternallyWritten",
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
            "allFaultsMustBreachAtMarketingDraft": True,
            "allFaultsMustCarryAtReviewDetection": True,
            "allFaultsMustRecoverAtTerminal": True,
            "permittedStatusOnPass": (
                "marketing-writing-effect-oracle-calibrated-no-candidate-behavior"
            ),
            "formalLiveEvidenceEligible": False,
        },
        "Acceptance boundary drifted",
    )


def _score_packet(packet: dict[str, Any], canonical: dict[str, Any]) -> dict[str, Any]:
    losses: list[str] = []
    for field, invariant in (
        ("claims", "claim-support"),
        ("ctaAlternatives", "alternative-cta-quality"),
    ):
        if packet.get(field) == []:
            losses.append(f"invariant-omitted:{invariant}")
        elif packet.get(field) != canonical[field]:
            losses.append(f"invariant-changed:{invariant}")
    for field, invariant in (
        ("sourceAndIntent", "source-and-intent-preservation"),
        ("audience", "audience-fit"),
        ("testimonialBoundary", "no-fabricated-testimonial"),
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
        canonical_packet_key="canonicalMarketingPacket",
        expected_override_by_fault=EXPECTED_OVERRIDE_BY_FAULT,
        required_fault_classes=REQUIRED_FAULT_CLASSES,
        score_packet=_score_packet,
        source_stage_id="parent-creative-access-anchor",
        active_stage_id="marketing-draft",
        review_stage_id="review-detection",
        recovery_stage_id="human-publication-authority-recovery",
    )
    results = matrix["results"]
    observed_faults = matrix["observedFaultClasses"]
    return {
        "outcome": "valid-zero-model-effect-calibration",
        "status": acceptance["permittedStatusOnPass"],
        "effectGroupId": "effect.marketing-writing",
        "candidateCount": len(EXPECTED_CANDIDATES),
        "scenarioCount": len(EXPECTED_SCENARIO_IDS),
        "caseCount": len(results),
        "faultCaseCount": len(results) - 1,
        "faultClassesCovered": sorted(observed_faults),
        "allCasesPassed": True,
        "creativePreferencePacketReused": True,
        "accessCommsBoundaryReused": True,
        "heuristicPanelTreatedAsIndependentEvidence": False,
        "fullScenarioFixtureCreated": False,
        "formalLiveEvidenceEligible": False,
        "agentDispatchCount": 0,
        "modelCallCount": 0,
        "candidateExecutionCount": 0,
        "claimBoundary": copy.deepcopy(protocol["claimBoundary"]),
        "claimLimit": (
            "This source-free extension calibrates five marketing-writing loss "
            "classes only. It does not prove current candidate behavior, marketing "
            "effectiveness, generalized preference, independent expert evidence, "
            "publication authority, live exposure, value, residual gap, or hard-"
            "standard eligibility."
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
