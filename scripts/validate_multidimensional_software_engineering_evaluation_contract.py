#!/usr/bin/env python3
"""Validate the multidimensional software-engineering evaluation contract."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
CONTRACT_PATH = (
    ROOT
    / "registry/multidimensional-software-engineering-evaluation-contract-2026-07-31.json"
)
DOCUMENT_PATH = (
    ROOT
    / "docs/strategy/MULTIDIMENSIONAL-SOFTWARE-ENGINEERING-EVALUATION-CONTRACT-2026-07-31.md"
)
PROGRAM_MAP_PATH = ROOT / "registry/program-acceptance-map.json"
PROGRAM_PLAN_PATH = ROOT / "registry/curation-program-plan.json"
EVIDENCE_ID = (
    "evidence.multidimensional-software-engineering-evaluation-contract-2026-07-31"
)

EXPECTED_LAYERS = {
    "evaluation-ontology-and-contract",
    "candidate-hard-floors",
    "deterministic-validators",
    "adaptive-profiles",
    "optional-orchestration",
}
EXPECTED_DIMENSIONS = {
    "goal-value-and-requirement-fitness",
    "intent-and-acceptance-fidelity",
    "architecture-and-design-integrity",
    "implementation-and-code-quality",
    "verification-security-privacy-and-safety",
    "supply-chain-and-provenance",
    "delivery-change-and-rollback",
    "reliability-operability-and-observability",
    "maintainability-evolution-and-retirement",
    "collaboration-knowledge-and-accountability",
    "ai-process-loss-and-human-control",
    "efficiency-resource-stewardship-and-sustainability",
}
EXPECTED_EVIDENCE_GRADES = {
    "claim-only",
    "source-bound",
    "deterministic",
    "observed-live",
    "repeated-comparative",
    "longitudinal-or-cross-context",
}
EXPECTED_ASSESSMENTS = {
    "not-applicable",
    "unassessed",
    "insufficient-evidence",
    "blocked",
    "concerning",
    "adequate",
    "strong",
}
EXPECTED_ACCEPTANCE_IDS = {
    "acceptance.software-engineering-lifecycle-specialization",
    "acceptance.end-to-end-process-fidelity",
    "acceptance.ai-independent-hard-standard-boundary",
    "acceptance.standard-candidate-contract",
    "acceptance.adaptive-harness-proportionality",
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_contract(
    contract: dict[str, Any] | None = None,
    *,
    root: Path = ROOT,
    program_map: dict[str, Any] | None = None,
    program_plan: dict[str, Any] | None = None,
) -> None:
    contract = contract or _load(
        root
        / "registry/multidimensional-software-engineering-evaluation-contract-2026-07-31.json"
    )
    program_map = program_map or _load(root / "registry/program-acceptance-map.json")
    program_plan = program_plan or _load(root / "registry/curation-program-plan.json")

    _require(contract.get("schema") == 1, "Evaluation-contract schema drifted")
    _require(
        contract.get("status")
        == "carrier-neutral-bounded-evaluation-contract-no-hard-standard-or-skill-promotion",
        "Evaluation-contract status drifted",
    )

    layers = {item.get("id") for item in contract.get("architectureLayers", [])}
    _require(layers == EXPECTED_LAYERS, "Evaluation layers drifted")
    _require(
        all(
            item.get("mayOwnAcceptanceAuthority") is False
            for item in contract.get("architectureLayers", [])
        ),
        "An evaluation layer claimed acceptance authority",
    )

    dimensions = {item.get("id") for item in contract.get("dimensions", [])}
    _require(dimensions == EXPECTED_DIMENSIONS, "Evaluation dimensions drifted")
    for dimension in contract.get("dimensions", []):
        _require(dimension.get("question"), f"Dimension question missing: {dimension.get('id')}")
        _require(
            dimension.get("sourceAnchors"),
            f"Dimension source anchors missing: {dimension.get('id')}",
        )

    evidence_model = contract.get("evidenceModel", {})
    _require(
        set(evidence_model.get("grades", [])) == EXPECTED_EVIDENCE_GRADES,
        "Evidence grades drifted",
    )
    _require(
        set(evidence_model.get("confidenceLevels", [])) == {"low", "medium", "high"},
        "Confidence levels drifted",
    )

    assessment = contract.get("assessmentModel", {})
    _require(
        set(assessment.get("allowedDimensionAssessments", []))
        == EXPECTED_ASSESSMENTS,
        "Dimension assessments drifted",
    )
    for prohibited in (
        "scalarTotalScoreAllowed",
        "crossDimensionCancellationAllowed",
        "unknownCountsAsZero",
        "blockedFloorMayBeHiddenByPresentation",
    ):
        _require(
            assessment.get(prohibited) is False,
            f"Anti-gaming boundary drifted: {prohibited}",
        )

    profile_axes = contract.get("profileAxes", {})
    _require(
        set(profile_axes)
        == {
            "lifecycleStage",
            "criticality",
            "exposure",
            "reversibility",
            "dataSensitivity",
            "aiInvolvement",
        },
        "Profile axes drifted",
    )
    _require(
        all(isinstance(values, list) and values for values in profile_axes.values()),
        "A profile axis is empty",
    )

    floors = contract.get("candidateHardFloorBoundary", {})
    _require(
        floors.get("admittedHardStandardsCreated") is False,
        "Candidate floors were promoted",
    )
    _require(
        len(floors.get("candidateFloors", [])) == 6,
        "Candidate-floor inventory drifted",
    )
    for floor in floors.get("candidateFloors", []):
        _require(floor.get("id"), "Candidate-floor id missing")
        _require(floor.get("applicability"), f"Floor applicability missing: {floor.get('id')}")
        _require(floor.get("obligation"), f"Floor obligation missing: {floor.get('id')}")

    report_contract = contract.get("reportContract", {})
    _require(
        len(report_contract.get("requiredFields", [])) >= 12,
        "Report contract is incomplete",
    )
    _require(
        report_contract.get("independentReviewRecordedSeparately") is True
        and report_contract.get("acceptanceAuthorityRecordedSeparately") is True,
        "Review or acceptance authority was collapsed",
    )

    sources = contract.get("primarySources", [])
    _require(len(sources) >= 10, "Primary-source coverage is too narrow")
    source_ids = {source.get("id") for source in sources}
    for dimension in contract.get("dimensions", []):
        _require(
            set(dimension.get("sourceAnchors", [])).issubset(source_ids),
            f"Dimension has an unknown source anchor: {dimension.get('id')}",
        )
    for source in sources:
        _require(source.get("id"), "Source id missing")
        _require(
            str(source.get("locator", "")).startswith("https://"),
            f"Source locator is not HTTPS: {source.get('id')}",
        )
        _require(source.get("boundedUse"), f"Source use missing: {source.get('id')}")
        _require(source.get("limitation"), f"Source limitation missing: {source.get('id')}")

    capability = contract.get("capabilityBoundary", {})
    _require(
        capability.get("completeEvaluationCapabilityProved") is False,
        "Complete evaluation capability was overclaimed",
    )
    _require(
        capability.get("newEvaluationSkillNecessary") is False,
        "A new Skill was declared necessary without residual-gap proof",
    )
    _require(
        capability.get("nextImplementationPriority")
        == "apply deterministic report schema to one bounded repository target",
        "Next implementation priority drifted",
    )
    _require(
        capability.get("currentReportSchema")
        == "registry/multidimensional-software-engineering-evaluation-report-schema-2026-07-31.json"
        and capability.get("currentPositiveFixture")
        == "tests/fixtures/multidimensional-software-engineering-evaluation-report-positive-2026-07-31.json",
        "Current report-schema calibration projection is missing",
    )

    projection = contract.get("acceptanceProjection", {})
    _require(
        set(projection.get("existingAcceptanceIds", [])) == EXPECTED_ACCEPTANCE_IDS,
        "Acceptance projection drifted",
    )
    _require(
        projection.get("newAcceptanceIdCreated") is False
        and projection.get("assessmentChangesAuthorized") is False,
        "Evaluation contract changed acceptance authority",
    )
    _require(
        projection.get("acceptanceCountMustRemain") == 61
        and len(program_map.get("acceptanceCriteria", [])) == 61,
        "Acceptance-count boundary drifted",
    )

    authority = contract.get("authorityBoundary", {})
    _require(
        isinstance(authority, dict)
        and authority
        and all(value is False for value in authority.values()),
        "Evaluation contract expanded authority",
    )

    acceptances = {
        item.get("id"): item for item in program_map.get("acceptanceCriteria", [])
    }
    for acceptance_id in EXPECTED_ACCEPTANCE_IDS:
        _require(acceptance_id in acceptances, f"Acceptance missing: {acceptance_id}")
        _require(
            EVIDENCE_ID in acceptances[acceptance_id].get("evidenceIds", []),
            f"Evaluation evidence not linked to {acceptance_id}",
        )

    evidence = {item.get("id"): item for item in program_map.get("evidence", [])}
    _require(EVIDENCE_ID in evidence, "Program evidence record is missing")
    _require(
        evidence[EVIDENCE_ID].get("path")
        == "registry/multidimensional-software-engineering-evaluation-contract-2026-07-31.json",
        "Program evidence path drifted",
    )

    initiative = next(
        (
            item
            for item in program_plan.get("currentInitiatives", [])
            if item.get("id") == "initiative.human-ai-collaboration-coverage-rebaseline"
        ),
        None,
    )
    _require(initiative is not None, "Coverage-rebaseline initiative is missing")
    _require(
        initiative.get("currentMultidimensionalSoftwareEngineeringEvaluationContract")
        == "registry/multidimensional-software-engineering-evaluation-contract-2026-07-31.json",
        "Program-plan evaluation projection is missing",
    )

    document = (
        root
        / "docs/strategy/MULTIDIMENSIONAL-SOFTWARE-ENGINEERING-EVALUATION-CONTRACT-2026-07-31.md"
    ).read_text(encoding="utf-8")
    normalized = " ".join(document.split())
    for phrase in (
        "carrier-neutral research and evaluation contract",
        "One scalar total score is prohibited",
        "Unknown or unassessed is not zero",
        "Profiles are derived",
        "future Skill is justified only after repeated tasks",
        "authorizes no hard-standard promotion",
    ):
        _require(phrase in normalized, f"Strategy document missing: {phrase}")


def main() -> int:
    validate_contract()
    print("Multidimensional software-engineering evaluation contract validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
