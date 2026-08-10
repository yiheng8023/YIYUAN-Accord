#!/usr/bin/env python3
"""Validate the sparse evaluation and software-engineering coverage reconciliation."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
RECORD_PATH = Path(
    "registry/evaluation-software-engineering-standards-coverage-reconciliation-v1-2026-08-11.json"
)
SOURCE_PATHS = {
    "programAcceptanceMap": Path("registry/program-acceptance-map.json"),
    "programCloseout": Path(
        "registry/program-final-closeout-readiness-reconciliation-2026-07-28.json"
    ),
    "candidateCoverage": Path(
        "registry/human-ai-collaboration-current-candidate-capability-coverage-reconciliation-2026-08-01.json"
    ),
    "evaluationContract": Path(
        "registry/multidimensional-software-engineering-evaluation-contract-2026-07-31.json"
    ),
    "coverageRebaseline": Path(
        "registry/human-ai-collaboration-coverage-rebaseline-2026-07-24.json"
    ),
    "scenarioMatrix": Path(
        "registry/human-ai-collaboration-scenario-evidence-matrix-batch-01-2026-07-24.json"
    ),
}
ROUTE_IDS = ["N", "O", "E", "C", "H", "R"]
DISPOSITIONS = {
    "covered",
    "overlap",
    "conflict",
    "unassessed",
    "needs-real-task",
    "needs-human-judgment",
    "needs-separate-authorization",
    "not-applicable",
}
ROUTE_STATES = {
    "represented-bounded-evidence",
    "unassessed",
    "needs-real-task",
    "needs-human-judgment",
    "needs-separate-authorization",
    "not-applicable",
    "not-eligible-no-residual-gap",
}
CLAIM_KEYS = {
    "behaviorProved",
    "valueProved",
    "crossHostPortabilityProved",
    "productionReadinessProved",
    "releaseEligibilityProved",
    "overallCloseoutProved",
    "residualGapProved",
}
AUTHORITY_KEYS = {
    "liveV2MigrationAuthorized",
    "acceptanceAssessmentTransitionAuthorized",
    "modelDispatchAuthorized",
    "candidateExecutionAuthorized",
    "ccSwitchMutationAuthorized",
    "consumerMutationAuthorized",
    "cleanupAuthorized",
    "commitAuthorized",
    "pushAuthorized",
    "publicationAuthorized",
    "releaseAuthorized",
}
COUNTER_KEYS = {
    "modelRequestCount",
    "candidateExecutionCount",
    "accountConnectionCount",
    "installCount",
    "enableCount",
    "managerMutationCount",
    "consumerMutationCount",
    "cleanupCount",
    "publicationCount",
    "releaseCount",
}


def _load(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"expected object at {path}")
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _records_by_id(value: object, *, field: str) -> dict[str, dict[str, object]]:
    if not isinstance(value, list):
        raise RuntimeError(f"{field} must be a list")
    result: dict[str, dict[str, object]] = {}
    for row in value:
        if not isinstance(row, dict) or not isinstance(row.get("id"), str) or not row["id"]:
            raise RuntimeError(f"{field} contains an invalid record")
        if row["id"] in result:
            raise RuntimeError(f"{field} contains duplicate identities")
        result[row["id"]] = row
    return result


def _require_exact_string_list(value: object, *, field: str) -> list[str]:
    if (
        not isinstance(value, list)
        or any(not isinstance(item, str) or not item for item in value)
        or len(value) != len(set(value))
    ):
        raise RuntimeError(f"{field} must be a unique non-empty string list")
    return value


def _require_exact_inventory(
    inventory: dict[str, object],
    *,
    ids_field: str,
    count_field: str,
    expected: list[str],
    message: str,
) -> None:
    observed = _require_exact_string_list(inventory.get(ids_field), field=ids_field)
    count = inventory.get(count_field)
    if type(count) is not int or count != len(expected) or observed != expected:
        raise RuntimeError(message)


def _validate_source_bindings(
    document: dict[str, object], root: Path
) -> dict[str, dict[str, object]]:
    bindings = document.get("sourceBindings")
    if not isinstance(bindings, dict) or set(bindings) != set(SOURCE_PATHS):
        raise RuntimeError("source binding drifted")
    loaded: dict[str, dict[str, object]] = {}
    for key, relative in SOURCE_PATHS.items():
        binding = bindings.get(key)
        path = root / relative
        if (
            not isinstance(binding, dict)
            or binding.get("path") != relative.as_posix()
            or binding.get("sha256") != _sha256(path)
        ):
            raise RuntimeError("source binding drifted")
        loaded[key] = _load(path)
        if binding.get("id") != loaded[key].get("id"):
            raise RuntimeError("source binding drifted")
    return loaded


def validate_reconciliation(
    document: dict[str, object], *, root: Path = ROOT
) -> None:
    if (
        document.get("schema") != 1
        or document.get("id")
        != "evaluation-software-engineering-standards-coverage-reconciliation-v1-2026-08-11"
        or document.get("date") != "2026-08-11"
        or document.get("status")
        != "verified-sparse-zero-model-coverage-reconciliation-no-acceptance-promotion"
    ):
        raise RuntimeError("reconciliation identity drifted")

    sources = _validate_source_bindings(document, root)
    program = sources["programAcceptanceMap"]
    closeout = sources["programCloseout"]
    coverage = sources["candidateCoverage"]
    evaluation = sources["evaluationContract"]
    rebaseline = sources["coverageRebaseline"]
    scenario_matrix = sources["scenarioMatrix"]

    criteria = _records_by_id(program.get("acceptanceCriteria"), field="acceptanceCriteria")
    partial_ids = [
        row["id"]
        for row in program["acceptanceCriteria"]
        if row.get("assessment") == "partial"
    ]
    open_rows = _records_by_id(closeout.get("openCriteria"), field="openCriteria")
    expected_clusters = [row["id"] for row in closeout.get("gateClusters", [])]
    dimensions = [row["id"] for row in evaluation.get("dimensions", [])]
    lifecycle = rebaseline.get("coverageModel", {}).get(
        "softwareEngineeringSpecialization", {}
    ).get("lifecycleSlices", [])
    scenarios = [row["id"] for row in scenario_matrix.get("scenarios", [])]
    evidence_ids = set(_records_by_id(program.get("evidence"), field="evidence"))

    inventory = document.get("inputInventory")
    if not isinstance(inventory, dict):
        raise RuntimeError("input inventory drifted")
    _require_exact_inventory(
        inventory,
        ids_field="partialCriterionIds",
        count_field="partialCriterionCount",
        expected=partial_ids,
        message="partial criterion inventory drifted",
    )
    _require_exact_inventory(
        inventory,
        ids_field="clusterIds",
        count_field="clusterCount",
        expected=expected_clusters,
        message="cluster inventory drifted",
    )
    _require_exact_inventory(
        inventory,
        ids_field="evaluationDimensionIds",
        count_field="evaluationDimensionCount",
        expected=dimensions,
        message="evaluation dimension inventory drifted",
    )
    _require_exact_inventory(
        inventory,
        ids_field="lifecycleSliceIds",
        count_field="lifecycleSliceCount",
        expected=lifecycle,
        message="lifecycle slice inventory drifted",
    )
    _require_exact_inventory(
        inventory,
        ids_field="scenarioIds",
        count_field="scenarioCount",
        expected=scenarios,
        message="scenario inventory drifted",
    )

    route_classes = document.get("routeClasses")
    if (
        not isinstance(route_classes, list)
        or [row.get("id") for row in route_classes if isinstance(row, dict)]
        != ROUTE_IDS
    ):
        raise RuntimeError("route class inventory drifted")

    rows = document.get("criterionReconciliations")
    if not isinstance(rows, list):
        raise RuntimeError("partial criterion coverage drifted")
    row_ids = [row.get("criterionId") for row in rows if isinstance(row, dict)]
    if row_ids != partial_ids or len(row_ids) != len(set(row_ids)):
        raise RuntimeError("partial criterion coverage drifted")

    known_dimensions = set(dimensions)
    known_lifecycle = set(lifecycle)
    known_scenarios = set(scenarios)
    mapped_dimensions: set[str] = set()
    mapped_lifecycle: set[str] = set()
    mapped_scenarios: set[str] = set()
    for row in rows:
        criterion_id = row["criterionId"]
        if row.get("clusterId") != open_rows[criterion_id].get("cluster"):
            raise RuntimeError("cluster assignment drifted")
        coordinate_lists = {
            "dimensionIds": _require_exact_string_list(
                row.get("dimensionIds"), field="dimensionIds"
            ),
            "lifecycleSliceIds": _require_exact_string_list(
                row.get("lifecycleSliceIds"), field="lifecycleSliceIds"
            ),
            "scenarioIds": _require_exact_string_list(
                row.get("scenarioIds"), field="scenarioIds"
            ),
        }
        if not set(coordinate_lists["dimensionIds"]).issubset(known_dimensions):
            raise RuntimeError("unknown coordinate")
        if not set(coordinate_lists["lifecycleSliceIds"]).issubset(known_lifecycle):
            raise RuntimeError("unknown coordinate")
        if not set(coordinate_lists["scenarioIds"]).issubset(known_scenarios):
            raise RuntimeError("unknown coordinate")
        mapped_dimensions.update(coordinate_lists["dimensionIds"])
        mapped_lifecycle.update(coordinate_lists["lifecycleSliceIds"])
        mapped_scenarios.update(coordinate_lists["scenarioIds"])
        dispositions = _require_exact_string_list(
            row.get("dispositions"), field="dispositions"
        )
        if not set(dispositions).issubset(DISPOSITIONS):
            raise RuntimeError("disposition vocabulary drifted")
        if any(not values for values in coordinate_lists.values()) and not (
            row.get("coordinatePosture") in {"not-applicable", "cross-cut"}
            and "not-applicable" in dispositions
        ):
            raise RuntimeError("empty coordinate set is unexplained")
        route = row.get("routeComparison")
        if not isinstance(route, dict) or list(route) != ROUTE_IDS:
            raise RuntimeError("route comparison drifted")
        if any(value not in ROUTE_STATES for value in route.values()):
            if route.get("R") != "not-eligible-no-residual-gap":
                raise RuntimeError("residual route overclaimed")
            raise RuntimeError("route state vocabulary drifted")
        if route.get("R") != "not-eligible-no-residual-gap":
            raise RuntimeError("residual route overclaimed")
        row_evidence = _require_exact_string_list(
            row.get("evidenceIds"), field="evidenceIds"
        )
        if not set(row_evidence).issubset(evidence_ids) or not set(
            row_evidence
        ).issubset(set(criteria[criterion_id].get("evidenceIds", []))):
            raise RuntimeError("unknown evidence identity")
        if not isinstance(row.get("nextEvidenceClass"), str) or not row[
            "nextEvidenceClass"
        ]:
            raise RuntimeError("next evidence class missing")
        if not isinstance(row.get("claimCeiling"), str) or not row["claimCeiling"]:
            raise RuntimeError("claim ceiling missing")

    if (
        mapped_dimensions != known_dimensions
        or mapped_lifecycle != known_lifecycle
        or mapped_scenarios != known_scenarios
    ):
        raise RuntimeError("mapped coordinate coverage drifted")

    aggregate = document.get("aggregateCoverage")
    if not isinstance(aggregate, dict):
        raise RuntimeError("aggregate coverage drifted")
    for field, expected in (
        ("evaluationDimensionIds", dimensions),
        ("lifecycleSliceIds", lifecycle),
        ("scenarioIds", scenarios),
    ):
        if _require_exact_string_list(aggregate.get(field), field=field) != expected:
            raise RuntimeError("aggregate coverage drifted")

    if coverage.get("coverageSummary") != document.get("candidateCoverageSummary"):
        raise RuntimeError("candidate coverage summary drifted")

    claims = document.get("claimBoundary")
    if (
        not isinstance(claims, dict)
        or set(claims) != CLAIM_KEYS
        or any(value is not False for value in claims.values())
    ):
        raise RuntimeError("claim boundary overclaimed")
    authority = document.get("authorityBoundary")
    if (
        not isinstance(authority, dict)
        or set(authority) != AUTHORITY_KEYS
        or any(value is not False for value in authority.values())
    ):
        raise RuntimeError("authority expanded")
    counters = document.get("executionCounters")
    if (
        not isinstance(counters, dict)
        or set(counters) != COUNTER_KEYS
        or any(type(value) is not int or value != 0 for value in counters.values())
    ):
        raise RuntimeError("execution counter is nonzero")


def validate_repository_record(root: Path = ROOT) -> None:
    validate_reconciliation(_load(root / RECORD_PATH), root=root)


def main() -> int:
    validate_repository_record(ROOT)
    print(
        "Evaluation and software-engineering standards coverage reconciliation v1 verified."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
