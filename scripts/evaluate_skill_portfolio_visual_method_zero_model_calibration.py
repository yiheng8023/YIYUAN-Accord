#!/usr/bin/env python3
"""Evaluate the source-free visual-method effect fixture."""

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
PROTOCOL_PATH = "registry/skill-portfolio-visual-method-zero-model-protocol-2026-08-03.json"
FIXTURE_PATH = "tests/fixtures/skill-portfolio-visual-method-zero-model-calibration-2026-08-03.json"
REQUIRED_FAULT_CLASSES = {
    "source-faithfulness-loss",
    "visual-plan-omission",
    "confirmation-gate-bypass",
    "native-backend-preference-loss",
    "artifact-write-boundary-loss",
}
EXPECTED_OVERRIDE_BY_FAULT: dict[str, dict[str, Any]] = {
    "control": {},
    "source-faithfulness-loss": {
        "sourceFaithfulness": {"sourceIds": [], "preserved": False}
    },
    "visual-plan-omission": {
        "visualPlan": {"layoutId": "", "visualIntentIds": []}
    },
    "confirmation-gate-bypass": {
        "confirmationGate": {"requiredBeforeGeneration": False, "confirmed": True}
    },
    "native-backend-preference-loss": {
        "backendPreference": {
            "nativeFirst": False,
            "selectedBackend": "external-unbound",
            "externalBackendAuthorized": True,
        }
    },
    "artifact-write-boundary-loss": {
        "artifactManifestAndWriteBoundary": {
            "plannedArtifactIds": [],
            "manifestRequiredBeforeWrite": False,
            "writeAuthorized": True,
            "generatedArtifactIds": ["artifact.untracked-output"],
        }
    },
}
EXPECTED_DIMENSION_IDS = [
    "source-faithfulness",
    "layout-or-visual-plan",
    "confirmation-gate",
    "native-backend-preference",
    "artifact-manifest-and-write-boundary",
]
EXPECTED_CANDIDATES = [
    {
        "name": "baoyu-article-illustrator",
        "path": "skills/baoyu-article-illustrator",
        "skillBlob": "87e27e6d83f420605de2f6992454d71874d8dc44",
        "skillSha256": "ce1c7bfe9b93e5afac1dbeac95a03f8abf8c102aeecc34a33d8f13dc10e64acd",
        "skillBytes": 17179,
        "fileCount": 37,
        "scriptLikeFileCount": 0,
        "eligibleDimensionIds": EXPECTED_DIMENSION_IDS,
        "currentAlternativeIds": ["official.imagegen", "official.creative-production"],
    },
    {
        "name": "baoyu-cover-image",
        "path": "skills/baoyu-cover-image",
        "skillBlob": "abaa5497c2d4989c3ae188d73fa02d92ce68a91f",
        "skillSha256": "36804fce98bcb9ebe4a51c26f6f276a807805aab980ca4a0718daa40a5cc7fda",
        "skillBytes": 17931,
        "fileCount": 35,
        "scriptLikeFileCount": 0,
        "eligibleDimensionIds": EXPECTED_DIMENSION_IDS,
        "currentAlternativeIds": ["official.imagegen", "official.creative-production"],
    },
    {
        "name": "baoyu-infographic",
        "path": "skills/baoyu-infographic",
        "skillBlob": "8212eaa182e66bde7c7ceae7dd23e86d2dadda10",
        "skillSha256": "1572aaa294c5f7547889f520b6efeed979aeaaf58b4e7c4bcaaa26ace2ee3564",
        "skillBytes": 19957,
        "fileCount": 50,
        "scriptLikeFileCount": 0,
        "eligibleDimensionIds": EXPECTED_DIMENSION_IDS,
        "currentAlternativeIds": [
            "official.imagegen",
            "official.creative-production",
            "official.data-analytics",
        ],
    },
]


def _validate_protocol_and_fixture(
    protocol: dict[str, Any], fixture: dict[str, Any], *, root: Path
) -> None:
    _require(
        protocol.get("id") == "skill-portfolio-visual-method-zero-model-protocol-2026-08-03"
        and protocol.get("status")
        == "frozen-zero-model-visual-method-effect-calibration-protocol"
        and protocol.get("effectGroupId") == "effect.visual-method"
        and protocol.get("scenarioIds") == ["GEN-CREATIVE-01"],
        "Protocol header drifted",
    )
    bindings = protocol.get("sourceBindings")
    _require(isinstance(bindings, list) and len(bindings) == 4, "Source bindings drifted")
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
    scenario = fixture.get("scenarioBindings")
    reuse = protocol.get("parentReuse")
    _require(
        fixture.get("status") == "frozen-source-free-visual-method-effect-fixture"
        and fixture.get("effectGroupId") == "effect.visual-method"
        and isinstance(scenario, dict)
        and scenario.get("scenarioIds") == ["GEN-CREATIVE-01"]
        and scenario.get("creativePreferencePacketReused") is True
        and scenario.get("fullScenarioDuplicated") is False
        and isinstance(reuse, dict)
        and reuse.get("creativeCapabilityBaselineReused") is True
        and reuse.get("creativePreferencePacketReused") is True
        and reuse.get("parentBaselineOrFixtureReexecutedByThisEvaluator") is False
        and reuse.get("userPreferenceGeneralizedBeyondPacket") is False
        and reuse.get("fullScenarioFixtureCreated") is False,
        "Parent evidence reuse boundary drifted",
    )
    baseline = _load(root / bindings[2]["path"])
    preference = _load(root / bindings[3]["path"])
    _require(
        baseline.get("id") == "human-ai-collaboration-creative-capability-baseline-2026-07-31"
        and baseline.get("status")
        == "source-bound-static-capability-baseline-no-live-creative-rights-admission-or-standard-evidence"
        and preference.get("id")
        == "human-ai-collaboration-unknown-knowns-creative-preference-packet-2026-07-27",
        "Parent creative evidence boundary drifted",
    )

    candidate = protocol.get("candidateBoundary")
    _require(
        isinstance(candidate, dict)
        and candidate.get("repository") == "JimLiu/baoyu-skills"
        and candidate.get("revision") == "6b7a2e417500561a5ecdd0b168332f4142584617"
        and candidate.get("tree") == "22d34a6f2c157ea249a2e3d0c04b17cd023289b9"
        and candidate.get("dimensionEligibilityEvidenceClass") == "static-protocol-design-only"
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
        (item for item in mapping.get("effectGroups", []) if item.get("id") == "effect.visual-method"),
        None,
    )
    candidate_mappings = [
        item for item in mapping.get("candidateMappings", []) if item.get("effectGroupId") == "effect.visual-method"
    ]
    _require(
        isinstance(effect_group, dict)
        and effect_group.get("candidateNames") == [item["name"] for item in EXPECTED_CANDIDATES]
        and effect_group.get("oracleDimensions") == EXPECTED_DIMENSION_IDS
        and effect_group.get("compositionArmEligible") is False
        and [item.get("name") for item in candidate_mappings]
        == [item["name"] for item in EXPECTED_CANDIDATES]
        and all(item.get("scenarioIds") == ["GEN-CREATIVE-01"] for item in candidate_mappings)
        and all(item.get("mappingState") == "static-hypothesis-only" for item in candidate_mappings)
        and all(item.get("claimCeiling") == "mapping-and-protocol-design-only" for item in candidate_mappings),
        "Candidate demand mapping drifted",
    )
    review = _load(root / bindings[1]["path"])
    source = review.get("source")
    reviewed_by_name = {item.get("name"): item for item in review.get("items", [])}
    _require(
        review.get("status") == "exact-itemized-adjudication-no-live-admission"
        and isinstance(source, dict)
        and source.get("repository") == candidate["repository"]
        and source.get("commit") == candidate["revision"]
        and source.get("tree") == candidate["tree"]
        and source.get("remoteMainMatchesPin") is True
        and source.get("checkoutCreated") is False
        and source.get("thirdPartyCodeExecuted") is False
        and source.get("payloadModified") is False
        and source.get("payloadVendored") is False,
        "Exact candidate source review drifted",
    )
    for expected in EXPECTED_CANDIDATES:
        reviewed = reviewed_by_name.get(expected["name"])
        _require(
            isinstance(reviewed, dict)
            and reviewed.get("path") == expected["path"]
            and reviewed.get("skillBlob") == expected["skillBlob"]
            and reviewed.get("skillSha256") == expected["skillSha256"]
            and reviewed.get("skillBytes") == expected["skillBytes"]
            and reviewed.get("fileCount") == expected["fileCount"]
            and reviewed.get("scriptLikeFileCount") == 0
            and reviewed.get("disposition")
            == "manager-install-candidate-default-disabled-native-image-backend"
            and reviewed.get("candidateFailure") is False,
            "Exact candidate static review drifted",
        )
    comparison = protocol.get("comparisonBoundary")
    _require(
        isinstance(comparison, dict)
        and comparison.get("comparisonOrder") == "native-or-current-first-then-one-candidate-arm"
        and comparison.get("compositionArmEligible") is False
        and comparison.get("sharedFixtureScoresOnlyDeclaredEligibleDimensionsInALaterArm") is True
        and comparison.get("currentAlternativeHealthProvedByThisCalibration") is False
        and comparison.get("candidateIncrementProvedByThisCalibration") is False,
        "Comparison boundary drifted",
    )
    oracle = protocol.get("oracle")
    _require(
        isinstance(oracle, dict)
        and oracle.get("invariants") == [{"id": item, "weight": 1} for item in EXPECTED_DIMENSION_IDS]
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
                "imageOrVisualGenerationPerformed",
                "imageBackendOrCostAuthorized",
                "artifactWritePerformed",
            )
        ),
        "Execution boundary drifted",
    )
    claim = protocol.get("claimBoundary")
    _require(isinstance(claim, dict) and claim and all(value is False for value in claim.values()), "Claim boundary drifted")
    _require(fixture.get("claimBoundary") == claim, "Fixture claim boundary drifted")
    _require(
        protocol.get("acceptance")
        == {
            "expectedCaseCount": 6,
            "expectedFaultCaseCount": 5,
            "oneControlCaseRequired": True,
            "oneCasePerRequiredFaultClass": True,
            "allFixtureExpectationsMustMatchParentRecomputation": True,
            "allFaultsMustBreachAtVisualPlan": True,
            "allFaultsMustCarryAtReviewDetection": True,
            "allFaultsMustRecoverAtTerminal": True,
            "permittedStatusOnPass": "visual-method-effect-oracle-calibrated-no-candidate-behavior",
            "formalLiveEvidenceEligible": False,
        },
        "Acceptance boundary drifted",
    )


def _score_packet(packet: dict[str, Any], canonical: dict[str, Any]) -> dict[str, Any]:
    losses: list[str] = []
    for field, invariant in (
        ("sourceFaithfulness", "source-faithfulness"),
        ("visualPlan", "layout-or-visual-plan"),
        ("confirmationGate", "confirmation-gate"),
        ("backendPreference", "native-backend-preference"),
        ("artifactManifestAndWriteBoundary", "artifact-manifest-and-write-boundary"),
    ):
        if packet.get(field) is None:
            losses.append(f"invariant-omitted:{invariant}")
        elif packet.get(field) != canonical[field]:
            losses.append(f"invariant-changed:{invariant}")
    return {"activeLossIds": sorted(losses), "weightedDelta": len(losses)}


def evaluate_calibration(protocol: dict[str, Any], fixture: dict[str, Any], *, root: Path = ROOT) -> dict[str, Any]:
    root = root.resolve()
    _validate_protocol_and_fixture(protocol, fixture, root=root)
    matrix = evaluate_case_matrix(
        protocol=protocol,
        fixture=fixture,
        root=root,
        repository_fixture_path=FIXTURE_PATH,
        canonical_packet_key="canonicalVisualMethodPacket",
        expected_override_by_fault=EXPECTED_OVERRIDE_BY_FAULT,
        required_fault_classes=REQUIRED_FAULT_CLASSES,
        score_packet=_score_packet,
        source_stage_id="parent-creative-preference-anchor",
        active_stage_id="visual-plan",
        review_stage_id="review-detection",
        recovery_stage_id="human-visual-write-authority-recovery",
    )
    results = matrix["results"]
    return {
        "outcome": "valid-zero-model-effect-calibration",
        "status": protocol["acceptance"]["permittedStatusOnPass"],
        "effectGroupId": "effect.visual-method",
        "candidateCount": 3,
        "scenarioCount": 1,
        "caseCount": len(results),
        "faultCaseCount": len(results) - 1,
        "faultClassesCovered": sorted(matrix["observedFaultClasses"]),
        "allCasesPassed": True,
        "creativePreferencePacketReused": True,
        "fullScenarioFixtureCreated": False,
        "formalLiveEvidenceEligible": False,
        "agentDispatchCount": 0,
        "modelCallCount": 0,
        "candidateExecutionCount": 0,
        "claimBoundary": copy.deepcopy(protocol["claimBoundary"]),
        "claimLimit": "This source-free extension calibrates five visual-method loss classes only. It does not prove candidate behavior, visual quality, source faithfulness, generalized preference, backend or cost authority, artifact-write authority, live exposure, value, residual gap, or hard-standard eligibility.",
        "cases": results,
    }


def evaluate_repository_calibration(root: Path = ROOT) -> dict[str, Any]:
    root = root.resolve()
    return evaluate_calibration(_load(root / PROTOCOL_PATH), _load(root / FIXTURE_PATH), root=root)


def main() -> int:
    print(json.dumps(evaluate_repository_calibration(ROOT), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
