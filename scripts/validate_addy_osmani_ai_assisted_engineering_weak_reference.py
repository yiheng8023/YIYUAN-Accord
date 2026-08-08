#!/usr/bin/env python3
"""Validate the Addy Osmani AI-assisted engineering weak reference."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
RECORD_PATH = Path(
    "registry/addy-osmani-ai-assisted-engineering-weak-reference-2026-08-08.json"
)
DOCUMENTATION_PATH = Path(
    "docs/research/addy-osmani-ai-assisted-engineering-weak-reference-2026-08-08.md"
)
ACCEPTANCE_PATH = Path("registry/program-acceptance-map.json")
CONTINUATION_PATH = Path("docs/operations/CONTINUATION.md")


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    _require(isinstance(value, dict), f"Expected JSON object: {path}")
    return value


def validate_record(
    record: dict[str, Any],
    *,
    root: Path = ROOT,
    program_map: dict[str, Any] | None = None,
) -> None:
    _require(record.get("schema") == 1, "Weak-reference schema drifted")
    _require(
        record.get("id")
        == "addy-osmani-ai-assisted-engineering-weak-reference-2026-08-08"
        and record.get("asOf") == "2026-08-08"
        and record.get("status")
        == "retained-practitioner-weak-reference-no-promotion",
        "Weak-reference identity or status drifted",
    )

    supplied = record.get("userSuppliedLocator", {})
    _require(
        supplied.get("url") == "https://x.com/i/status/2085536770758996033"
        and supplied.get("acceptedAsOriginalSource") is False,
        "User-supplied secondary locator boundary drifted",
    )

    source = record.get("originalSource", {})
    expected_source_fields = {
        "url": "https://addyosmani.com/blog/ai-coding-workflow/",
        "publishedAt": "2026-01-04",
        "sourceKind": "PRACTITIONER-REFERENCE",
        "directness": "D1-indirect",
        "empiricalStrength": "ES0",
        "normativeAuthority": "NA0",
        "applicability": "bounded-analogy",
        "verificationState": "claim-checked",
        "adoptionState": "held",
    }
    for key, expected in expected_source_fields.items():
        _require(source.get(key) == expected, f"Source classification drifted: {key}")
    _require(source.get("declaredOpenLicenseObservedOnPage") is False, "Open license was overclaimed")
    _require(source.get("bodyRedistributionAuthorized") is False, "Body redistribution was authorized")

    reading = record.get("boundedReading", {})
    _require(
        len(reading.get("candidateInvariantHypotheses", [])) == 5
        and len(reading.get("adaptivePracticeExamples", [])) == 8,
        "Bounded reading inventory drifted",
    )
    _require(
        "does not define or measure" in reading.get("processLossRelevance", ""),
        "Process-loss limitation is missing",
    )

    impact = record.get("strategyImpact", {})
    _require(impact.get("disposition") == "weak-reference-only", "Weak disposition drifted")
    _require(impact.get("reinforcesExistingDirection") is True, "Existing-direction link was lost")
    for key in (
        "readmeChangeRequired",
        "programOrderChangeRequired",
        "acceptanceChangeRequired",
        "goalModePromptChangeRequired",
        "newStandardCandidateCreated",
        "hardStandardPromotionEligible",
        "githubActionsRequired",
    ):
        _require(impact.get(key) is False, f"Strategy impact was promoted: {key}")
    _require(
        "GitHub Actions is neither required nor sufficient" in impact.get("verificationCarrierBoundary", ""),
        "GitHub Actions boundary is missing",
    )

    claim_boundary = record.get("claimBoundary", {})
    _require(
        isinstance(claim_boundary, dict)
        and claim_boundary
        and all(value is False for value in claim_boundary.values()),
        "Weak reference expanded its claim boundary",
    )
    authority = record.get("authorityBoundary", {})
    _require(
        isinstance(authority, dict)
        and authority
        and all(value is False for value in authority.values()),
        "Weak reference expanded authority",
    )

    program_map = program_map or _load(root / ACCEPTANCE_PATH)
    counts = {"verified": 0, "partial": 0, "planned": 0}
    for criterion in program_map.get("acceptanceCriteria", []):
        assessment = criterion.get("assessment")
        if assessment in counts:
            counts[assessment] += 1
    _require(
        counts == record.get("acceptanceBoundary", {}).get("canonicalInventoryExpected"),
        "Canonical acceptance inventory drifted",
    )
    record_path = RECORD_PATH.as_posix()
    _require(
        all(item.get("path") != record_path for item in program_map.get("evidence", [])),
        "Weak reference was promoted into program acceptance evidence",
    )

    _require(
        record.get("documentation") == DOCUMENTATION_PATH.as_posix(),
        "Documentation path drifted",
    )
    documentation = (root / DOCUMENTATION_PATH).read_text(encoding="utf-8")
    normalized = " ".join(documentation.split())
    for phrase in (
        "weak reference, not primary empirical evidence",
        "cannot advance `acceptance.end-to-end-process-fidelity`",
        "GitHub Actions is neither required nor sufficient",
        "46 verified / 15 partial / 0 planned",
    ):
        _require(phrase in normalized, f"Documentation boundary missing: {phrase}")
    continuation = (root / CONTINUATION_PATH).read_text(encoding="utf-8")
    _require(record_path in continuation, "Continuation weak-reference checkpoint is missing")


def validate_repository_record(root: Path = ROOT) -> None:
    validate_record(_load(root / RECORD_PATH), root=root)


def main() -> int:
    validate_repository_record()
    print("Addy Osmani AI-assisted engineering weak reference: valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
