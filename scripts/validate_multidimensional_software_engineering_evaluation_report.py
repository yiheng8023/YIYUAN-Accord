#!/usr/bin/env python3
"""Validate the multidimensional evaluation report schema and bounded report."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    from .validate_multidimensional_software_engineering_evaluation_contract import (
        CONTRACT_PATH,
    )
except ImportError:
    from validate_multidimensional_software_engineering_evaluation_contract import (
        CONTRACT_PATH,
    )


ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = (
    ROOT
    / "registry/multidimensional-software-engineering-evaluation-report-schema-2026-07-31.json"
)
FIXTURE_PATH = (
    ROOT
    / "tests/fixtures/multidimensional-software-engineering-evaluation-report-positive-2026-07-31.json"
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_schema(
    schema: dict[str, Any] | None = None,
    contract: dict[str, Any] | None = None,
) -> None:
    schema = schema or _load(SCHEMA_PATH)
    contract = contract or _load(CONTRACT_PATH)

    _require(
        schema.get("$schema") == "https://json-schema.org/draft/2020-12/schema",
        "Report schema dialect drifted",
    )
    _require(schema.get("additionalProperties") is False, "Report permits hidden fields")
    required = set(schema.get("required", []))
    _require(
        set(contract["reportContract"]["requiredFields"]).issubset(required),
        "Report schema omitted a contract field",
    )
    _require(
        {"independentReview", "acceptanceAuthority", "statusClaim"}.issubset(required),
        "Report authority fields are missing",
    )
    definitions = schema.get("$defs", {})
    _require(
        set(definitions["dimensionId"]["enum"])
        == {item["id"] for item in contract["dimensions"]},
        "Report dimension vocabulary drifted",
    )
    _require(
        set(definitions["floorId"]["enum"])
        == {
            item["id"]
            for item in contract["candidateHardFloorBoundary"]["candidateFloors"]
        },
        "Report floor vocabulary drifted",
    )
    _require(
        set(definitions["evidenceGrade"]["enum"])
        == set(contract["evidenceModel"]["grades"]),
        "Report evidence vocabulary drifted",
    )
    _require(
        set(definitions["dimensionAssessment"]["enum"])
        == set(contract["assessmentModel"]["allowedDimensionAssessments"]),
        "Report assessment vocabulary drifted",
    )
    for axis, values in contract["profileAxes"].items():
        _require(
            set(schema["properties"]["profileAxes"]["properties"][axis]["enum"])
            == set(values),
            f"Report profile axis drifted: {axis}",
        )


def validate_report(
    report: dict[str, Any] | None = None,
    *,
    schema: dict[str, Any] | None = None,
    contract: dict[str, Any] | None = None,
) -> None:
    report = report or _load(FIXTURE_PATH)
    schema = schema or _load(SCHEMA_PATH)
    contract = contract or _load(CONTRACT_PATH)
    validate_schema(schema, contract)

    allowed_top_level = set(schema["properties"])
    _require(
        set(report) == set(schema["required"]),
        "Report fields are missing or hidden fields were added",
    )
    _require(set(report).issubset(allowed_top_level), "Report contains an unknown field")
    _require(report.get("schemaVersion") == 1, "Report schema version drifted")

    for object_name in ("targetIdentity", "evaluationContext", "profileAxes"):
        _require(
            set(report[object_name])
            == set(schema["properties"][object_name]["required"]),
            f"Report object fields drifted: {object_name}",
        )

    for axis, value in report["profileAxes"].items():
        _require(
            value in contract["profileAxes"][axis],
            f"Report profile value is invalid: {axis}",
        )

    dimension_ids = report["applicableDimensions"]
    result_dimension_ids = [item["dimensionId"] for item in report["dimensionResults"]]
    _require(
        len(dimension_ids) == len(set(dimension_ids))
        and set(dimension_ids) == set(result_dimension_ids)
        and len(result_dimension_ids) == len(set(result_dimension_ids)),
        "Applicable dimensions and results do not form one exact set",
    )

    floor_ids = report["applicableCandidateFloors"]
    result_floor_ids = [item["floorId"] for item in report["floorResults"]]
    _require(
        len(floor_ids) == len(set(floor_ids))
        and set(floor_ids) == set(result_floor_ids)
        and len(result_floor_ids) == len(set(result_floor_ids)),
        "Applicable floors and results do not form one exact set",
    )

    evidence = {item.get("id"): item for item in report["evidence"]}
    _require(
        len(evidence) == len(report["evidence"]) and all(evidence),
        "Report evidence ids are missing or duplicated",
    )
    for item in report["evidence"]:
        _require(
            item.get("grade") in contract["evidenceModel"]["grades"],
            f"Report evidence grade is invalid: {item.get('id')}",
        )
        _require(item.get("source") and item.get("scope"), "Evidence source or scope is missing")
        _require(
            isinstance(item.get("limitations"), list),
            f"Evidence limitations are missing: {item.get('id')}",
        )

    for result in report["dimensionResults"]:
        _require(
            result["assessment"]
            in contract["assessmentModel"]["allowedDimensionAssessments"],
            f"Dimension assessment is invalid: {result['dimensionId']}",
        )
        _require(
            set(result["evidenceIds"]).issubset(evidence),
            f"Dimension references unknown evidence: {result['dimensionId']}",
        )
        _require(
            isinstance(result["unknowns"], list)
            and isinstance(result["limitations"], list),
            f"Dimension uncertainty is missing: {result['dimensionId']}",
        )

    for result in report["floorResults"]:
        _require(
            result["result"] in {"not-applicable", "unassessed", "pass", "blocked"},
            f"Floor result is invalid: {result['floorId']}",
        )
        _require(
            set(result["evidenceIds"]).issubset(evidence),
            f"Floor references unknown evidence: {result['floorId']}",
        )

    _require(report["unknownsAndLimitations"], "Report hides all unknowns and limitations")
    _require(report["claimBoundary"], "Report claim boundary is missing")

    blocked_or_unassessed_floor = any(
        item["result"] in {"blocked", "unassessed"} for item in report["floorResults"]
    )
    incomplete_dimension = any(
        item["assessment"]
        in {"unassessed", "insufficient-evidence", "blocked", "concerning"}
        for item in report["dimensionResults"]
    )
    if report["statusClaim"] == "accepted":
        _require(
            not blocked_or_unassessed_floor and not incomplete_dimension,
            "Accepted status hides an incomplete dimension or floor",
        )
        _require(
            report["independentReview"]["status"] == "performed",
            "Accepted status lacks independent review",
        )
        _require(
            report["acceptanceAuthority"]["status"] == "accepted",
            "Accepted status lacks acceptance authority",
        )


def main() -> int:
    validate_report()
    print("Multidimensional software-engineering evaluation report validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
