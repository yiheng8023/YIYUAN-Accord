#!/usr/bin/env python3
"""Evaluate the source-free shared engineering-lifecycle effect fixture."""

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
    "registry/skill-portfolio-engineering-lifecycle-zero-model-protocol-"
    "2026-08-03.json"
)
FIXTURE_PATH = (
    "tests/fixtures/skill-portfolio-engineering-lifecycle-zero-model-"
    "calibration-2026-08-03.json"
)
REQUIRED_FAULT_CLASSES = {
    "destructive-release-authority-transfer",
    "repository-convention-omission",
    "rollback-safeguard-loss",
    "source-freshness-omission",
    "traceability-omission",
    "verification-omission",
}
EXPECTED_OVERRIDE_BY_FAULT: dict[str, dict[str, Any]] = {
    "control": {},
    "repository-convention-omission": {"repositoryConventionIds": []},
    "traceability-omission": {"traceabilityLinks": []},
    "verification-omission": {"verificationEvidenceIds": []},
    "rollback-safeguard-loss": {
        "rollbackOrReversibility": {
            "planId": "rollback.none",
            "triggerIds": [],
            "destructiveStepDeferred": False,
        }
    },
    "source-freshness-omission": {"sourceFreshnessRecords": []},
    "destructive-release-authority-transfer": {
        "authority": {
            "destructiveOwner": "agent",
            "releaseOwner": "agent",
            "agentRole": "unilateral-destructive-and-release-authority",
        }
    },
}
EXPECTED_SCENARIO_IDS = [
    "GEN-RESEARCH-01",
    "SE-ARCH-DESIGN-01",
    "SE-IMPLEMENT-REVIEW-01",
    "SE-MAINT-MIGRATE-01",
    "SE-RELEASE-CHANGE-01",
    "SE-VERIFY-SECURE-01",
]
EXPECTED_DIMENSION_IDS = [
    "repository-convention-first",
    "traceability",
    "verification",
    "rollback-or-reversibility",
    "source-freshness",
    "destructive-and-release-authority",
]
EXPECTED_CANDIDATES = [
    {
        "name": "ci-cd-and-automation",
        "path": "skills/ci-cd-and-automation",
        "gitBlob": "118456fcb10225c030769a4fee7815b9c536b0ce",
        "sha256": "a6ed8ed56456b01ff8314c44eefc69897d9905ae4e06bb2b7036286efb79b5f0",
        "bytes": 11332,
        "eligibleDimensionIds": [
            "repository-convention-first",
            "traceability",
            "verification",
            "rollback-or-reversibility",
            "destructive-and-release-authority",
        ],
    },
    {
        "name": "deprecation-and-migration",
        "path": "skills/deprecation-and-migration",
        "gitBlob": "765bdde6329dbd5fd22d5d3fc2c185737fc9f908",
        "sha256": "92d9846321fab624eded7ac55d19a7738cfd2321c2be2e35eb153dcacf7359de",
        "bytes": 12516,
        "eligibleDimensionIds": [
            "repository-convention-first",
            "traceability",
            "verification",
            "rollback-or-reversibility",
            "destructive-and-release-authority",
        ],
    },
    {
        "name": "documentation-and-adrs",
        "path": "skills/documentation-and-adrs",
        "gitBlob": "7faf52c9558fa60faf7362cf473cf24784f9209b",
        "sha256": "b867bb80fb681257c7625ae59a0dfd849b1fc0f0a2f0338e7923f38030df9793",
        "bytes": 9782,
        "eligibleDimensionIds": [
            "repository-convention-first",
            "traceability",
            "verification",
            "destructive-and-release-authority",
        ],
    },
    {
        "name": "source-driven-development",
        "path": "skills/source-driven-development",
        "gitBlob": "9ef02877e446bd2d31862006ef4e3a79d5c38b9a",
        "sha256": "b979e7531ea601ed14a090f32a5b135db517c48ab9821c5e8b09efd80f4ff4d8",
        "bytes": 8204,
        "eligibleDimensionIds": [
            "repository-convention-first",
            "traceability",
            "verification",
            "source-freshness",
            "destructive-and-release-authority",
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
        == "skill-portfolio-engineering-lifecycle-zero-model-protocol-2026-08-03"
        and protocol.get("status")
        == "frozen-zero-model-shared-engineering-effect-calibration-protocol"
        and protocol.get("effectGroupId") == "effect.engineering-lifecycle",
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
        and fixture_binding.get("sourceFreeSharedStructureOnly") is True
        and fixture_binding.get("fullScenarioFixtureCreated") is False,
        "Fixture binding boundary drifted",
    )
    scenario = fixture.get("scenarioBindings")
    _require(
        fixture.get("status") == "frozen-source-free-shared-engineering-effect-fixture"
        and fixture.get("effectGroupId") == "effect.engineering-lifecycle"
        and isinstance(scenario, dict)
        and scenario.get("scenarioIds") == EXPECTED_SCENARIO_IDS
        and scenario.get("existingScenariosReused") is True
        and scenario.get("fullScenarioDuplicated") is False
        and scenario.get("sharedStructureOnly") is True,
        "Shared fixture scenario boundary drifted",
    )

    history = protocol.get("historicalEvidenceBoundary")
    _require(
        isinstance(history, dict)
        and history.get("historicalReleaseProtocolBound") is True
        and history.get("historicalMigrationProtocolBound") is True
        and history.get("carrierNeutralEvaluationContractBound") is True
        and history.get("sourceSnapshotBoundaryBound") is True
        and history.get("historicalProtocolsReexecutedByThisEvaluator") is False
        and history.get("historicalAdaptedPayloadEvidencePromotedToCurrentExactCandidateProof")
        is False
        and history.get("historicalAssociationPromotedToGeneralPreference") is False,
        "Historical evidence boundary drifted",
    )

    candidate = protocol.get("candidateBoundary")
    _require(
        isinstance(candidate, dict)
        and candidate.get("repository") == "addyosmani/agent-skills"
        and candidate.get("revision")
        == "7829ffd90d973b6325f5f12f1b1226dcace74443"
        and candidate.get("tree") == "d0d903cfb69e783b05b45c0773ad8a2ec3916a3e"
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
            if item.get("id") == "effect.engineering-lifecycle"
        ),
        None,
    )
    candidate_mappings = [
        item
        for item in mapping.get("candidateMappings", [])
        if item.get("effectGroupId") == "effect.engineering-lifecycle"
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
        and all(item.get("mappingState") == "static-hypothesis-only" for item in candidate_mappings)
        and all(
            item.get("claimCeiling") == "mapping-and-protocol-design-only"
            for item in candidate_mappings
        ),
        "Candidate demand mapping drifted",
    )
    mapped_scenarios = sorted(
        {scenario_id for item in candidate_mappings for scenario_id in item.get("scenarioIds", [])}
    )
    _require(mapped_scenarios == EXPECTED_SCENARIO_IDS, "Candidate scenario union drifted")

    review = _load(root / bindings[1]["path"])
    reviewed_items = {
        item.get("name"): item for item in review.get("items", []) if isinstance(item, dict)
    }
    for expected in EXPECTED_CANDIDATES:
        reviewed = reviewed_items.get(expected["name"])
        _require(
            isinstance(reviewed, dict)
            and reviewed.get("path") == expected["path"]
            and reviewed.get("skillBlob") == expected["gitBlob"]
            and reviewed.get("skillSha256") == expected["sha256"]
            and reviewed.get("skillBytes") == expected["bytes"]
            and reviewed.get("disposition") == "manager-install-candidate-default-disabled"
            and reviewed.get("candidateFailure") is False,
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
                "accountSecretOrOrganizationalDataAccessed",
                "repositoryWorkflowReleaseMigrationOrDeploymentPerformed",
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
            "expectedCaseCount": 7,
            "expectedFaultCaseCount": 6,
            "oneControlCaseRequired": True,
            "oneCasePerRequiredFaultClass": True,
            "allFixtureExpectationsMustMatchParentRecomputation": True,
            "allFaultsMustBreachAtLifecycleDraft": True,
            "allFaultsMustCarryAtReviewDetection": True,
            "allFaultsMustRecoverAtTerminal": True,
            "permittedStatusOnPass": (
                "engineering-lifecycle-effect-oracle-calibrated-no-candidate-behavior"
            ),
            "formalLiveEvidenceEligible": False,
        },
        "Acceptance boundary drifted",
    )


def _score_packet(packet: dict[str, Any], canonical: dict[str, Any]) -> dict[str, Any]:
    losses: list[str] = []
    for field, invariant in (
        ("repositoryConventionIds", "repository-convention-first"),
        ("traceabilityLinks", "traceability"),
        ("verificationEvidenceIds", "verification"),
        ("sourceFreshnessRecords", "source-freshness"),
    ):
        if packet.get(field) == []:
            losses.append(f"invariant-omitted:{invariant}")
        elif packet.get(field) != canonical[field]:
            losses.append(f"invariant-changed:{invariant}")
    for field, invariant in (
        ("rollbackOrReversibility", "rollback-or-reversibility"),
        ("authority", "destructive-and-release-authority"),
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
        canonical_packet_key="canonicalLifecyclePacket",
        expected_override_by_fault=EXPECTED_OVERRIDE_BY_FAULT,
        required_fault_classes=REQUIRED_FAULT_CLASSES,
        score_packet=_score_packet,
        source_stage_id="existing-scenario-and-protocol-anchor",
        active_stage_id="lifecycle-draft",
        review_stage_id="review-detection",
        recovery_stage_id="human-authority-recovery",
    )
    results = matrix["results"]
    observed_faults = matrix["observedFaultClasses"]
    return {
        "outcome": "valid-zero-model-effect-calibration",
        "status": acceptance["permittedStatusOnPass"],
        "effectGroupId": "effect.engineering-lifecycle",
        "candidateCount": len(EXPECTED_CANDIDATES),
        "scenarioCount": len(EXPECTED_SCENARIO_IDS),
        "caseCount": len(results),
        "faultCaseCount": len(results) - 1,
        "faultClassesCovered": sorted(observed_faults),
        "allCasesPassed": True,
        "sharedStructureOnly": True,
        "fullScenarioFixtureCreated": False,
        "historicalEvidencePromotedToCurrentCandidateProof": False,
        "formalLiveEvidenceEligible": False,
        "agentDispatchCount": 0,
        "modelCallCount": 0,
        "candidateExecutionCount": 0,
        "claimBoundary": copy.deepcopy(protocol["claimBoundary"]),
        "claimLimit": (
            "This shared source-free structure calibrates only six engineering-"
            "lifecycle loss classes. It does not prove any current exact candidate "
            "behavior, historical-to-current equivalence, comparative value, live "
            "exposure, production readiness, residual gap, or hard-standard status."
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
