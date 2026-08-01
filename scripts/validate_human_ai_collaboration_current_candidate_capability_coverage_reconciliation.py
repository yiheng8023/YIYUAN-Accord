#!/usr/bin/env python3
"""Validate the current zero-model candidate capability coverage reconciliation."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
RECONCILIATION_PATH = Path(
    "registry/human-ai-collaboration-current-candidate-capability-coverage-"
    "reconciliation-2026-08-01.json"
)
MATRIX_PATH = Path(
    "registry/human-ai-collaboration-scenario-evidence-matrix-batch-01-"
    "2026-07-24.json"
)
PROGRAM_ACCEPTANCE_PATH = Path("registry/program-acceptance-map.json")
ACCEPTANCE_EVIDENCE_ID = (
    "evidence.human-ai-collaboration-current-candidate-capability-coverage-"
    "reconciliation-2026-08-01"
)
CURRENT_CANDIDATE_COVERAGE_REQUIRED_FILES = (
    str(RECONCILIATION_PATH).replace("\\", "/"),
    "docs/strategy/HUMAN-AI-COLLABORATION-CURRENT-CANDIDATE-CAPABILITY-"
    "COVERAGE-RECONCILIATION-2026-08-01.md",
    "scripts/validate_human_ai_collaboration_current_candidate_capability_"
    "coverage_reconciliation.py",
    "tests/test_human_ai_collaboration_current_candidate_capability_coverage_"
    "reconciliation.py",
)
ROUTE_CLASSES = {"N", "O", "E", "C", "H", "R"}
ALLOWED_ROUTE_STATES = {
    "represented-contract-only",
    "represented-source-static",
    "conditional-source-static",
    "represented-no-model",
    "represented-bounded-synthetic-association",
    "mechanism-calibrated-no-candidate-value",
    "deferred-to-preserve-attribution",
    "required-human-control-unexecuted",
    "unassessed",
    "not-eligible-no-residual-gap",
}
EXPECTED_SOURCE_BINDINGS = [
    {
        "path": str(MATRIX_PATH).replace("\\", "/"),
        "bytes": 76246,
        "sha256": "5e0a91a0bcc2d32f56aeebce2d7ece63fc9c8386fddaf423f864496cd4c29cb9",
        "role": "authoritative-scenario-identities-and-inherited-evidence-states",
    },
    {
        "path": "registry/other-cc-and-external-skill-scenario-coverage-audit-2026-07-27.json",
        "bytes": 11712,
        "sha256": "9c7912d1b859274675b98d5622b091caf2bc2779ca416806c6629be849940d69",
        "role": "bounded-external-candidate-behavior-source-exposure-and-gap-classification",
    },
    {
        "path": "registry/human-ai-collaboration-learning-capability-baseline-2026-07-31.json",
        "bytes": 12120,
        "sha256": "d0bb1082647cb08be4ce91203b27e384d62ba1090b8724cc3c459ac90524c001",
        "role": "learning-native-official-external-human-representative-set",
    },
    {
        "path": "registry/human-ai-collaboration-creative-capability-baseline-2026-07-31.json",
        "bytes": 13136,
        "sha256": "4da4ac66da0c4577e05cbfe0968c1a139612084bfa2e632a09be25b106a5eea6",
        "role": "creative-native-official-conditional-composition-human-representative-set",
    },
    {
        "path": "registry/human-ai-collaboration-access-comms-capability-baseline-2026-07-31.json",
        "bytes": 12509,
        "sha256": "a141513ec71a8127fb37ee4803ccab4c3bdd7aca8be0e91755f87fa659ed4239",
        "role": "access-comms-ordered-native-official-external-composed-human-route",
    },
    {
        "path": "registry/human-ai-collaboration-org-decision-zero-model-protocol-2026-07-31.json",
        "bytes": 10894,
        "sha256": "2d9c4d1e0313e0de53dc91ae1f453828d0e2b017780c1ae1483ea253cc9578a6",
        "role": "organization-decision-five-arm-zero-model-route-boundary",
    },
    {
        "path": "registry/human-ai-collaboration-engineering-management-zero-model-protocol-2026-07-31.json",
        "bytes": 13766,
        "sha256": "34824b350d09a8c667723004f64af60b932be5b5dd3bd605816da3efc65a0330",
        "role": "engineering-management-five-arm-zero-model-route-boundary",
    },
    {
        "path": "registry/human-ai-collaboration-software-lifecycle-thin-slice-zero-model-calibration-evidence-2026-07-27.json",
        "bytes": 6048,
        "sha256": "822c87738914f81ae621f9591ed330ea4f877b20b610949e1ee17fff6a5fd57a",
        "role": "architecture-and-verify-secure-zero-model-mechanism-calibration",
    },
    {
        "path": "registry/human-ai-collaboration-release-change-current-cc-codex-no-model-preflight-2026-07-30.json",
        "bytes": 10210,
        "sha256": "98bc807ba4a37f7159116a7da67741180c869b92084c1ca849d492aaa671e2eb",
        "role": "release-change-current-cc-body-projection-and-task-listing-boundary",
    },
]
EXPECTED_CLAIM_BOUNDARY = {
    "instructionDeliveryProved": False,
    "candidateCausationProved": False,
    "liveDomainValueProved": False,
    "crossHostValueProved": False,
    "humanControlExecuted": False,
    "residualSelfAuthoredGapProved": False,
}
EXPECTED_COVERAGE_SUMMARY = {
    "scenarioCount": 13,
    "routeCellCount": 78,
    "mappedRouteCellCount": 50,
    "unassessedRouteCellCount": 15,
    "residualIneligibleCellCount": 13,
    "liveDomainValueScenarioCount": 0,
}
EXPECTED_COVERAGE_DECISION = {
    "representativeCoverageMapped": True,
    "widerUntargetedDiscoveryNeededNow": False,
    "unassessedCellIsResidualGap": False,
    "currentEvidenceSupportsPortfolioMutation": False,
    "liveComparisonReady": False,
    "selfAuthoredGapEligible": False,
}
EXPECTED_AUTHORITY_BOUNDARY = {
    "repositoryReconciliationWritesAuthorized": True,
    "externalDiscoveryAuthorized": False,
    "installationOrAccountConnectionAuthorized": False,
    "candidateExecutionAuthorized": False,
    "modelDispatchAuthorized": False,
    "ccSwitchOrGlobalConfigurationMutationAuthorized": False,
    "portfolioMutationAuthorized": False,
    "selfAuthoredCapabilityAuthorized": False,
    "hardStandardPromotionAuthorized": False,
}
EXPECTED_ACCEPTANCE_SUPPORTS = {
    "acceptance.solution-neutral-collaboration-rebaseline",
    "acceptance.residual-gap-proof",
}
EXPECTED_SECTION_SHA256 = {
    "scenarioCoverage": "47329dd42de1c7ab5d2d7157e616dce8c9e3a5ff058399281c89cbc1761e5b49",
    "overlapGroups": "0dff1ef3b25a3c0a26a4d68af20c46a017ca37ddc760b55b33f1a52fddd9751b",
    "conflictGroups": "ece98ac49f3aa63a2fcb1e908692242227f393e2b40b85d2d9c3bfee22383158",
    "unassessedCells": "38ab3c6ba97022213a4e389727ffe198993b43da4717b4c55cee63e2e39bc47b",
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_sha256(value: object) -> str:
    payload = json.dumps(
        value, ensure_ascii=True, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _index(rows: list[dict], key: str, label: str) -> dict[str, dict]:
    result = {str(row.get(key)): row for row in rows if isinstance(row, dict)}
    _require(len(result) == len(rows), f"{label} identities drifted")
    return result


def validate_reconciliation(document: dict, *, root: Path = ROOT) -> None:
    _require(
        document.get("schema") == 1
        and document.get("id")
        == (
            "human-ai-collaboration-current-candidate-capability-coverage-"
            "reconciliation-2026-08-01"
        )
        and document.get("date") == "2026-08-01"
        and document.get("status")
        == (
            "zero-model-current-coverage-mapped-overlap-conflict-fallback-and-"
            "unassessed-cells-no-evidence-promotion"
        ),
        "Current candidate coverage reconciliation identity drifted",
    )
    bindings = document.get("sourceBindings", [])
    _require(
        bindings == EXPECTED_SOURCE_BINDINGS,
        "Current candidate coverage source binding drifted",
    )
    for binding in bindings:
        path = root / binding["path"]
        _require(path.is_file(), f"Current candidate coverage source missing: {path}")
        _require(
            path.stat().st_size == binding["bytes"]
            and _sha256(path) == binding["sha256"],
            f"Current candidate coverage source identity drifted: {path}",
        )
    matrix = json.loads((root / MATRIX_PATH).read_text(encoding="utf-8"))
    expected = {
        row["id"]: row["evidenceState"] for row in matrix.get("scenarios", [])
    }
    coverage = _index(
        document.get("scenarioCoverage", []), "scenarioId", "Scenario coverage"
    )
    _require(
        {
            scenario_id: row.get("inheritedEvidenceState")
            for scenario_id, row in coverage.items()
        }
        == expected,
        "Current candidate coverage promoted or lost scenario evidence state",
    )
    for scenario_id, row in coverage.items():
        evidence_paths = row.get("evidenceSourcePaths", [])
        _require(
            isinstance(evidence_paths, list)
            and bool(evidence_paths)
            and set(evidence_paths).issubset(
                {binding["path"] for binding in EXPECTED_SOURCE_BINDINGS}
            ),
            f"Current candidate coverage evidence binding drifted: {scenario_id}",
        )
        route_coverage = row.get("routeCoverage", {})
        _require(
            set(route_coverage) == ROUTE_CLASSES,
            f"Current candidate coverage route classes drifted: {scenario_id}",
        )
        residual = route_coverage["R"]
        _require(
            residual
            == {
                "state": "not-eligible-no-residual-gap",
                "candidateIds": [],
                "evidenceCeiling": "none",
            },
            f"Current candidate coverage residual route promoted: {scenario_id}",
        )
        for route_class, route in route_coverage.items():
            state = route.get("state")
            candidate_ids = route.get("candidateIds")
            ceiling = route.get("evidenceCeiling")
            _require(
                state in ALLOWED_ROUTE_STATES,
                f"Current candidate coverage route state drifted: {scenario_id}/{route_class}",
            )
            _require(
                isinstance(candidate_ids, list)
                and len(candidate_ids) == len(set(candidate_ids))
                and isinstance(ceiling, str),
                f"Current candidate coverage route record drifted: {scenario_id}/{route_class}",
            )
            if state == "unassessed":
                _require(
                    candidate_ids == [] and ceiling == "none",
                    f"Current candidate coverage unassessed route promoted: {scenario_id}/{route_class}",
                )
            elif route_class not in {"R"}:
                _require(
                    bool(candidate_ids) and ceiling != "none",
                    f"Current candidate coverage represented route lost evidence: {scenario_id}/{route_class}",
                )
        fallback_order = row.get("fallbackOrder", [])
        _require(
            isinstance(fallback_order, list)
            and fallback_order
            and fallback_order[0] == "N"
            and fallback_order[-1] == "H"
            and "R" not in fallback_order
            and len(fallback_order) == len(set(fallback_order))
            and set(fallback_order).issubset(ROUTE_CLASSES)
            and all(route_coverage[item]["state"] != "unassessed" for item in fallback_order),
            f"Current candidate coverage fallback boundary drifted: {scenario_id}",
        )
    _require(
        _canonical_sha256(document.get("scenarioCoverage", []))
        == EXPECTED_SECTION_SHA256["scenarioCoverage"],
        "Current candidate coverage route projection drifted",
    )
    mapped_count = sum(
        1
        for row in coverage.values()
        for route_class, route in row["routeCoverage"].items()
        if route_class != "R" and route["state"] != "unassessed"
    )
    unassessed_count = sum(
        1
        for row in coverage.values()
        for route_class, route in row["routeCoverage"].items()
        if route_class != "R" and route["state"] == "unassessed"
    )
    derived_summary = {
        "scenarioCount": len(coverage),
        "routeCellCount": len(coverage) * len(ROUTE_CLASSES),
        "mappedRouteCellCount": mapped_count,
        "unassessedRouteCellCount": unassessed_count,
        "residualIneligibleCellCount": sum(
            row["routeCoverage"]["R"]["state"]
            == "not-eligible-no-residual-gap"
            for row in coverage.values()
        ),
        "liveDomainValueScenarioCount": 0,
    }
    _require(
        document.get("coverageSummary") == EXPECTED_COVERAGE_SUMMARY
        and derived_summary == EXPECTED_COVERAGE_SUMMARY,
        "Current candidate coverage summary drifted",
    )
    scenario_mapped_counts = {
        scenario_id: sum(
            route_class != "R" and route["state"] != "unassessed"
            for route_class, route in row["routeCoverage"].items()
        )
        for scenario_id, row in coverage.items()
    }
    dimension_rows = _index(
        document.get("dimensionCoverage", []), "axisId", "Dimension coverage"
    )
    expected_axis_ids = {
        axis_id
        for row in matrix["scenarios"]
        for axis_id in row.get("axisIds", [])
    }
    _require(
        set(dimension_rows) == expected_axis_ids,
        "Current candidate coverage dimension identities drifted",
    )
    for axis_id, projection in dimension_rows.items():
        scenario_ids = [
            row["id"]
            for row in matrix["scenarios"]
            if axis_id in row.get("axisIds", [])
        ]
        _require(
            projection
            == {
                "axisId": axis_id,
                "scenarioIds": scenario_ids,
                "mappedRouteCellCount": sum(
                    scenario_mapped_counts[scenario_id]
                    for scenario_id in scenario_ids
                ),
                "liveDomainValueProved": False,
            },
            f"Current candidate coverage dimension projection drifted: {axis_id}",
        )
    lifecycle_rows = _index(
        document.get("softwareLifecycleCoverage", []),
        "sliceId",
        "Software lifecycle coverage",
    )
    expected_slice_ids = {
        slice_id
        for row in matrix["scenarios"]
        for slice_id in row.get("softwareLifecycleSlices", [])
    }
    _require(
        set(lifecycle_rows) == expected_slice_ids,
        "Current candidate coverage lifecycle identities drifted",
    )
    for slice_id, projection in lifecycle_rows.items():
        scenario_ids = [
            row["id"]
            for row in matrix["scenarios"]
            if slice_id in row.get("softwareLifecycleSlices", [])
        ]
        _require(
            projection
            == {
                "sliceId": slice_id,
                "scenarioIds": scenario_ids,
                "mappedRouteCellCount": sum(
                    scenario_mapped_counts[scenario_id]
                    for scenario_id in scenario_ids
                ),
                "liveDomainValueProved": False,
            },
            f"Current candidate coverage lifecycle projection drifted: {slice_id}",
        )
    overlap_groups = _index(
        document.get("overlapGroups", []), "id", "Coverage overlap group"
    )
    _require(
        len(overlap_groups) == 6
        and _canonical_sha256(document.get("overlapGroups", []))
        == EXPECTED_SECTION_SHA256["overlapGroups"]
        and all(row.get("marginalValueProved") is False for row in overlap_groups.values()),
        "Current candidate coverage overlap boundary drifted",
    )
    conflict_groups = _index(
        document.get("conflictGroups", []), "id", "Coverage conflict group"
    )
    _require(
        len(conflict_groups) == 5
        and _canonical_sha256(document.get("conflictGroups", []))
        == EXPECTED_SECTION_SHA256["conflictGroups"]
        and all(
            row.get("conflict") and row.get("failClosedResolution")
            for row in conflict_groups.values()
        ),
        "Current candidate coverage conflict boundary drifted",
    )
    unassessed = _index(
        document.get("unassessedCells", []), "id", "Coverage unassessed cell"
    )
    _require(
        len(unassessed) == 7
        and _canonical_sha256(document.get("unassessedCells", []))
        == EXPECTED_SECTION_SHA256["unassessedCells"]
        and all(
            row.get("scenarioIds")
            and set(row["scenarioIds"]).issubset(set(coverage))
            and row.get("reason")
            and row.get("recheckTrigger")
            for row in unassessed.values()
        ),
        "Current candidate coverage unassessed boundary drifted",
    )
    for route_class, unassessed_id in {
        "O": "unassessed.official-route",
        "E": "unassessed.external-route",
        "C": "unassessed.composition-route",
    }.items():
        expected_scenarios = {
            scenario_id
            for scenario_id, row in coverage.items()
            if row["routeCoverage"][route_class]["state"] == "unassessed"
        }
        _require(
            set(unassessed[unassessed_id]["scenarioIds"]) == expected_scenarios,
            f"Current candidate coverage unassessed route drifted: {route_class}",
        )
    _require(
        document.get("claimBoundary") == EXPECTED_CLAIM_BOUNDARY,
        "Current candidate coverage claim boundary promoted",
    )
    _require(
        document.get("coverageDecision") == EXPECTED_COVERAGE_DECISION,
        "Current candidate coverage decision drifted",
    )
    _require(
        document.get("subtractionDecisions")
        == [
            "stop-untargeted-candidate-name-discovery",
            "do-not-install-to-fill-unassessed-cells",
            "do-not-compose-before-separate-arm-attribution",
            "do-not-retire-from-static-overlap-or-counts",
            "do-not-self-author-from-missing-behavioral-evidence",
        ],
        "Current candidate coverage subtraction decision drifted",
    )
    counters = document.get("executionCounters", {})
    _require(
        counters
        == {
            "externalDiscoveryCount": 0,
            "installationCount": 0,
            "candidateExecutionCount": 0,
            "modelRequestCount": 0,
            "ccSwitchMutationCount": 0,
            "globalConfigurationMutationCount": 0,
        },
        "Current candidate coverage execution boundary drifted",
    )
    _require(
        document.get("authorityBoundary") == EXPECTED_AUTHORITY_BOUNDARY,
        "Current candidate coverage authority boundary drifted",
    )
    program = json.loads(
        (root / PROGRAM_ACCEPTANCE_PATH).read_text(encoding="utf-8")
    )
    criteria = _index(
        program.get("acceptanceCriteria", []), "id", "Program acceptance criterion"
    )
    for acceptance_id in EXPECTED_ACCEPTANCE_SUPPORTS:
        criterion = criteria.get(acceptance_id, {})
        _require(
            criterion.get("assessment") == "partial"
            and ACCEPTANCE_EVIDENCE_ID in criterion.get("evidenceIds", []),
            f"Current candidate coverage acceptance mapping drifted: {acceptance_id}",
        )
    evidence = _index(program.get("evidence", []), "id", "Program evidence")
    _require(
        evidence.get(ACCEPTANCE_EVIDENCE_ID)
        == {
            "id": ACCEPTANCE_EVIDENCE_ID,
            "path": str(RECONCILIATION_PATH).replace("\\", "/"),
            "kind": (
                "zero-model-thirteen-scenario-six-route-current-coverage-"
                "overlap-conflict-fallback-unassessed-and-subtractive-"
                "decision-no-behavior-value-or-residual-gap-promotion"
            ),
            "asOf": "2026-08-01",
            "supports": [
                "acceptance.solution-neutral-collaboration-rebaseline",
                "acceptance.residual-gap-proof",
            ],
        },
        "Current candidate coverage acceptance evidence drifted",
    )


def main() -> int:
    document = json.loads((ROOT / RECONCILIATION_PATH).read_text(encoding="utf-8"))
    validate_reconciliation(document)
    print("Current candidate capability coverage reconciliation validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
