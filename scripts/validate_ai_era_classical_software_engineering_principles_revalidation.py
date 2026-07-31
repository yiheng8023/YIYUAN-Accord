#!/usr/bin/env python3
"""Validate the AI-era classical engineering-principles revalidation contract."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
CONTRACT_PATH = (
    ROOT
    / "registry/ai-era-classical-software-engineering-principles-revalidation-2026-07-31.json"
)
DOCUMENT_PATH = (
    ROOT
    / "docs/strategy/AI-ERA-CLASSICAL-SOFTWARE-ENGINEERING-PRINCIPLES-REVALIDATION-2026-07-31.md"
)
PROGRAM_MAP_PATH = ROOT / "registry/program-acceptance-map.json"
PROGRAM_PLAN_PATH = ROOT / "registry/curation-program-plan.json"
EVIDENCE_ID = (
    "evidence.ai-era-classical-software-engineering-principles-revalidation-2026-07-31"
)
EXPECTED_CLASSIFICATIONS = {
    "candidate-invariant",
    "adaptive-practice",
    "obsolete-ceremony",
    "insufficient-evidence",
}
EXPECTED_EVALUATION_DIMENSIONS = {
    "originalFailureMode",
    "aiEraEffect",
    "currentNativeOfficialReviewedExternalAndComposedCoverage",
    "deterministicVerification",
    "residualHumanOrDomainJudgment",
    "creativityContextLatencyOperationalAndMaintenanceCost",
    "scopeCounterexamplesFalsifiersAndFallback",
    "revalidationOrRetirementCondition",
}
EXPECTED_ACCEPTANCE_IDS = {
    "acceptance.software-engineering-lifecycle-specialization",
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
        / "registry/ai-era-classical-software-engineering-principles-revalidation-2026-07-31.json"
    )
    program_map = program_map or _load(root / "registry/program-acceptance-map.json")
    program_plan = program_plan or _load(root / "registry/curation-program-plan.json")

    _require(contract.get("schema") == 1, "Revalidation schema drifted")
    _require(
        contract.get("status")
        == "bounded-primary-source-research-contract-no-hard-standard-promotion",
        "Revalidation status drifted",
    )
    finding = contract.get("boundedFinding", {})
    for prohibited_claim in (
        "universalProductivityClaim",
        "universalQualityClaim",
        "legacyProcessRestorationClaim",
        "hardStandardPromotionClaim",
    ):
        _require(
            finding.get(prohibited_claim) is False,
            f"Bounded finding promoted {prohibited_claim}",
        )

    classification_ids = {
        item.get("id") for item in contract.get("classifications", [])
    }
    _require(
        classification_ids == EXPECTED_CLASSIFICATIONS,
        "Classification vocabulary drifted",
    )
    _require(
        set(contract.get("requiredEvaluationDimensions", []))
        == EXPECTED_EVALUATION_DIMENSIONS,
        "Evaluation dimensions drifted",
    )
    _require(
        len(contract.get("valueDimensions", [])) == 8,
        "Value-dimension inventory drifted",
    )

    sources = contract.get("primarySources", [])
    _require(len(sources) >= 7, "Primary-source coverage is too narrow")
    for source in sources:
        _require(source.get("id"), "Source id is missing")
        _require(
            str(source.get("locator", "")).startswith("https://"),
            f"Source locator is not HTTPS: {source.get('id')}",
        )
        _require(source.get("boundedFinding"), f"Source finding missing: {source.get('id')}")
        _require(source.get("limitation"), f"Source limitation missing: {source.get('id')}")

    projection = contract.get("acceptanceProjection", {})
    _require(
        set(projection.get("existingAcceptanceIds", []))
        == EXPECTED_ACCEPTANCE_IDS,
        "Acceptance projection drifted",
    )
    _require(
        projection.get("newAcceptanceIdCreated") is False,
        "Research lens created a new acceptance id",
    )
    _require(
        projection.get("acceptanceCountMustRemain") == 61,
        "Acceptance-count boundary drifted",
    )
    _require(
        len(program_map.get("acceptanceCriteria", [])) == 61,
        "Program acceptance count changed",
    )

    authority = contract.get("authorityBoundary", {})
    _require(
        isinstance(authority, dict)
        and authority
        and all(value is False for value in authority.values()),
        "Research contract expanded authority",
    )

    acceptances = {
        item.get("id"): item for item in program_map.get("acceptanceCriteria", [])
    }
    for acceptance_id in EXPECTED_ACCEPTANCE_IDS:
        _require(acceptance_id in acceptances, f"Acceptance is missing: {acceptance_id}")
    for acceptance_id in (
        "acceptance.software-engineering-lifecycle-specialization",
        "acceptance.ai-independent-hard-standard-boundary",
        "acceptance.standard-candidate-contract",
    ):
        _require(
            EVIDENCE_ID in acceptances[acceptance_id].get("evidenceIds", []),
            f"Research evidence is not linked to {acceptance_id}",
        )

    evidence = {item.get("id"): item for item in program_map.get("evidence", [])}
    _require(EVIDENCE_ID in evidence, "Program evidence record is missing")
    _require(
        evidence[EVIDENCE_ID].get("path")
        == "registry/ai-era-classical-software-engineering-principles-revalidation-2026-07-31.json",
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
        initiative.get("currentAiEraEngineeringPrinciplesRevalidation")
        == "registry/ai-era-classical-software-engineering-principles-revalidation-2026-07-31.json",
        "Program-plan research projection is missing",
    )

    document = (
        root
        / "docs/strategy/AI-ERA-CLASSICAL-SOFTWARE-ENGINEERING-PRINCIPLES-REVALIDATION-2026-07-31.md"
    ).read_text(encoding="utf-8")
    normalized_document = " ".join(document.split())
    for phrase in (
        "AI-era revalidation rather than blanket revival or dismissal",
        "candidate-invariant",
        "adaptive-practice",
        "obsolete-ceremony",
        "insufficient-evidence",
        "Classification is not admission",
        "does not add to",
        "Explicit non-authorizations",
    ):
        _require(phrase in normalized_document, f"Strategy document missing: {phrase}")


def main() -> int:
    validate_contract()
    print("AI-era engineering-principles revalidation validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
