#!/usr/bin/env python3
"""Plan a synthetic graph-scoped standard revalidation cascade without writes."""

from __future__ import annotations

from collections import defaultdict, deque
import copy
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
POC_PATH = Path("registry/standard-revalidation-cascade-poc-2026-08-07.json")
ACCEPTANCE_PATH = Path("registry/program-acceptance-map.json")
DESIGN_PATH = Path(
    "docs/superpowers/specs/2026-07-15-production-capability-manager-design.md"
)
LAYERED_RECONCILIATION_PATH = Path(
    "registry/layered-reliability-projection-reconciliation-2026-07-18.json"
)
EVIDENCE_ID = "evidence.standard-revalidation-cascade-poc-2026-08-07"
MUTATION_CASE_IDS = (
    "synthetic-boundary",
    "standard-shape",
    "graph-shape",
    "planning-shape",
    "edges-shape",
    "direct-node-shape",
    "standard-status",
    "standard-receipt",
    "standard-evidence",
    "direct-node",
    "rewrite-all",
    "cross-repository",
    "batch-bound",
    "edge-target",
    "edge-kind",
    "node-kind",
    "authority",
    "identity",
    "migration",
    "duplicate-node",
    "cycle",
)
ALLOWED_EDGE_KINDS = frozenset(
    {"feeds", "projects-to", "consumed-by", "derived-from"}
)
ALLOWED_NODE_KINDS = frozenset({"governed-source", "projection", "consumer"})

def _nonempty_strings(value: Any) -> bool:
    return (
        isinstance(value, list)
        and bool(value)
        and all(isinstance(item, str) and item for item in value)
    )


def plan_cascade(request: dict[str, Any]) -> dict[str, Any]:
    """Return a bounded non-executing cascade plan or a fail-closed decision."""
    blockers: list[str] = []
    standard = request.get("standard", {})
    graph = request.get("graph", {})
    planning = request.get("planning", {})
    if not isinstance(standard, dict):
        standard = {}
    if not isinstance(graph, dict):
        blockers.append("graph-node-identity-invalid")
        graph = {}
    if not isinstance(planning, dict):
        planning = {}

    if not (
        request.get("declaredSynthetic") is True
        and request.get("realStandardRepresented") is False
    ):
        blockers.append("synthetic-boundary-missing")
    if not (
        isinstance(standard.get("id"), str)
        and standard.get("id")
        and isinstance(standard.get("version"), str)
        and standard.get("version")
        and standard.get("status") == "accepted"
        and isinstance(standard.get("ownerAdmissionReceiptId"), str)
        and standard.get("ownerAdmissionReceiptId")
        and isinstance(standard.get("restartBaselineId"), str)
        and standard.get("restartBaselineId")
        and _nonempty_strings(standard.get("evidenceIds"))
    ):
        blockers.append("accepted-standard-boundary-missing")

    node_rows = graph.get("nodes", [])
    if not isinstance(node_rows, list):
        blockers.append("graph-node-identity-invalid")
        node_rows = []
    valid_node_rows = [
        row
        for row in node_rows
        if isinstance(row, dict) and isinstance(row.get("id"), str) and row.get("id")
    ]
    node_ids = [row["id"] for row in valid_node_rows]
    if len(valid_node_rows) != len(node_rows) or len(set(node_ids)) != len(node_ids):
        blockers.append("graph-node-identity-invalid")
    nodes = {
        row.get("id"): row
        for row in valid_node_rows
    }
    direct = request.get("directlyAffectedNodeIds", [])
    if not (
        isinstance(direct, list)
        and direct
        and all(
            isinstance(node_id, str) and node_id and node_id in nodes
            for node_id in direct
        )
    ):
        blockers.append("directly-affected-node-invalid")
    if planning.get("rewriteAll") is not False:
        blockers.append("universal-rewrite-forbidden")
    if planning.get("crossRepositoryMutationAuthorized") is not False:
        blockers.append("cross-repository-mutation-forbidden")
    max_batch_size = planning.get("maxBatchSize")
    if not isinstance(max_batch_size, int) or isinstance(max_batch_size, bool) or max_batch_size < 1:
        blockers.append("batch-bound-invalid")

    adjacency: dict[str, list[str]] = defaultdict(list)
    edge_rows = graph.get("edges", [])
    if not isinstance(edge_rows, list):
        blockers.append("graph-edge-invalid")
        edge_rows = []
    for edge in edge_rows:
        if not isinstance(edge, dict):
            blockers.append("graph-edge-invalid")
            continue
        source = edge.get("from")
        target = edge.get("to")
        if source not in nodes or target not in nodes:
            blockers.append("graph-edge-invalid")
            continue
        if edge.get("kind") not in ALLOWED_EDGE_KINDS:
            blockers.append("graph-edge-kind-invalid")
            continue
        adjacency[source].append(target)

    if blockers:
        return {
            "decision": "blocked",
            "blockers": blockers,
            "affectedNodeIds": [],
            "unaffectedNodeIds": list(nodes),
            "batches": [],
            "nodePlans": [],
            "restartBaselineId": None,
            "oldProjectionDeprecation": "blocked",
            "executionAuthorized": False,
            "claimBoundary": "synthetic-planner-mechanism-only",
        }

    depth = {node_id: 0 for node_id in direct}
    queue = deque(direct)
    while queue:
        source = queue.popleft()
        for target in adjacency[source]:
            proposed = depth[source] + 1
            if target not in depth or proposed < depth[target]:
                depth[target] = proposed
                queue.append(target)

    affected_set = set(depth)
    affected_identity_blockers: list[str] = []
    for node_id in affected_set:
        node = nodes[node_id]
        if node.get("kind") not in ALLOWED_NODE_KINDS:
            affected_identity_blockers.append("affected-node-kind-invalid")
        if not (
            isinstance(node.get("authorityOwnerId"), str)
            and node.get("authorityOwnerId")
        ):
            affected_identity_blockers.append("affected-node-authority-missing")
        if not (
            isinstance(node.get("repositoryId"), str)
            and node.get("repositoryId")
            and isinstance(node.get("currentRevision"), str)
            and node.get("currentRevision")
        ):
            affected_identity_blockers.append("affected-node-identity-missing")
        if not (
            isinstance(node.get("targetRevision"), str)
            and node.get("targetRevision")
            and node.get("targetRevision") != node.get("currentRevision")
            and _nonempty_strings(node.get("historicalDebtIds"))
            and all(
                isinstance(node.get(field), str) and node.get(field)
                for field in (
                    "migrationFixtureId",
                    "verificationFixtureId",
                    "rollbackPlanId",
                )
            )
        ):
            affected_identity_blockers.append(
                "affected-node-migration-plan-incomplete"
            )
    if affected_identity_blockers:
        return {
            "decision": "blocked",
            "blockers": list(dict.fromkeys(affected_identity_blockers)),
            "affectedNodeIds": [],
            "unaffectedNodeIds": list(nodes),
            "batches": [],
            "nodePlans": [],
            "restartBaselineId": None,
            "oldProjectionDeprecation": "blocked",
            "executionAuthorized": False,
            "claimBoundary": "synthetic-planner-mechanism-only",
        }
    indegree = {node_id: 0 for node_id in affected_set}
    for source in affected_set:
        for target in adjacency[source]:
            if target in affected_set:
                indegree[target] += 1
    cycle_queue = deque(node_id for node_id, value in indegree.items() if value == 0)
    schedule_depth = {node_id: 0 for node_id in affected_set}
    visited = 0
    while cycle_queue:
        source = cycle_queue.popleft()
        visited += 1
        for target in adjacency[source]:
            if target not in indegree:
                continue
            schedule_depth[target] = max(
                schedule_depth[target], schedule_depth[source] + 1
            )
            indegree[target] -= 1
            if indegree[target] == 0:
                cycle_queue.append(target)
    if visited != len(affected_set):
        return {
            "decision": "blocked",
            "blockers": ["affected-graph-cycle"],
            "affectedNodeIds": [],
            "unaffectedNodeIds": list(nodes),
            "batches": [],
            "nodePlans": [],
            "restartBaselineId": None,
            "oldProjectionDeprecation": "blocked",
            "executionAuthorized": False,
            "claimBoundary": "synthetic-planner-mechanism-only",
        }
    depth = schedule_depth

    ordered_affected = [node_id for node_id in nodes if node_id in depth]
    unaffected = [node_id for node_id in nodes if node_id not in depth]
    node_plans = [
        {
            "nodeId": node_id,
            "fromRevision": nodes[node_id]["currentRevision"],
            "targetRevision": nodes[node_id]["targetRevision"],
            "historicalDebtIds": nodes[node_id]["historicalDebtIds"],
            "migrationFixtureId": nodes[node_id]["migrationFixtureId"],
            "verificationFixtureId": nodes[node_id]["verificationFixtureId"],
            "rollbackPlanId": nodes[node_id]["rollbackPlanId"],
        }
        for node_id in ordered_affected
    ]
    batches: list[dict[str, Any]] = []
    for level in sorted(set(depth.values())):
        level_ids = [node_id for node_id in ordered_affected if depth[node_id] == level]
        for start in range(0, len(level_ids), max_batch_size):
            batches.append(
                {
                    "index": len(batches) + 1,
                    "nodeIds": level_ids[start : start + max_batch_size],
                }
            )

    return {
        "decision": "plan-ready",
        "blockers": [],
        "affectedNodeIds": ordered_affected,
        "unaffectedNodeIds": unaffected,
        "batches": batches,
        "nodePlans": node_plans,
        "restartBaselineId": standard["restartBaselineId"],
        "oldProjectionDeprecation": "after-all-affected-verification",
        "executionAuthorized": False,
        "claimBoundary": "synthetic-planner-mechanism-only",
    }


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _mutation_cases(request: dict[str, Any]) -> list[tuple[str, dict[str, Any], str]]:
    specifications = (
        ("synthetic-boundary", ("declaredSynthetic",), False, "synthetic-boundary-missing"),
        ("standard-shape", ("standard",), None, "accepted-standard-boundary-missing"),
        ("graph-shape", ("graph",), None, "graph-node-identity-invalid"),
        ("planning-shape", ("planning",), None, "batch-bound-invalid"),
        ("edges-shape", ("graph", "edges"), {}, "graph-edge-invalid"),
        ("direct-node-shape", ("directlyAffectedNodeIds",), [{}], "directly-affected-node-invalid"),
        ("standard-status", ("standard", "status"), "candidate", "accepted-standard-boundary-missing"),
        ("standard-receipt", ("standard", "ownerAdmissionReceiptId"), "", "accepted-standard-boundary-missing"),
        ("standard-evidence", ("standard", "evidenceIds"), [], "accepted-standard-boundary-missing"),
        ("direct-node", ("directlyAffectedNodeIds",), ["missing"], "directly-affected-node-invalid"),
        ("rewrite-all", ("planning", "rewriteAll"), True, "universal-rewrite-forbidden"),
        ("cross-repository", ("planning", "crossRepositoryMutationAuthorized"), True, "cross-repository-mutation-forbidden"),
        ("batch-bound", ("planning", "maxBatchSize"), 0, "batch-bound-invalid"),
        ("edge-target", ("graph", "edges", 0, "to"), "missing", "graph-edge-invalid"),
        ("edge-kind", ("graph", "edges", 0, "kind"), "decorates", "graph-edge-kind-invalid"),
        ("node-kind", ("graph", "nodes", 0, "kind"), "mystery", "affected-node-kind-invalid"),
        ("authority", ("graph", "nodes", 0, "authorityOwnerId"), "", "affected-node-authority-missing"),
        ("identity", ("graph", "nodes", 0, "currentRevision"), "", "affected-node-identity-missing"),
        ("migration", ("graph", "nodes", 0, "migrationFixtureId"), "", "affected-node-migration-plan-incomplete"),
    )
    cases: list[tuple[str, dict[str, Any], str]] = []
    for case_id, path, replacement, blocker in specifications:
        mutated = copy.deepcopy(request)
        target: Any = mutated
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = replacement
        cases.append((case_id, mutated, blocker))
    mutated = copy.deepcopy(request)
    mutated["graph"]["nodes"].append(copy.deepcopy(mutated["graph"]["nodes"][0]))
    cases.append(("duplicate-node", mutated, "graph-node-identity-invalid"))
    mutated = copy.deepcopy(request)
    mutated["graph"]["edges"].append(
        {"from": "consumer-a", "to": "source-a", "kind": "feeds"}
    )
    cases.append(("cycle", mutated, "affected-graph-cycle"))
    return cases


def validate_poc_record(
    record: dict[str, Any],
    *,
    acceptance: dict[str, Any] | None = None,
    layered: dict[str, Any] | None = None,
    root: Path = ROOT,
) -> None:
    """Validate one in-memory synthetic cascade PoC record."""
    _require(
        record.get("schema") == 1
        and record.get("id") == "standard-revalidation-cascade-poc-v1"
        and record.get("status") == "verified-synthetic-poc-mechanism-only",
        "Standard revalidation cascade PoC identity drifted",
    )
    documentation = record.get("documentation")
    _require(
        documentation
        == "docs/strategy/STANDARD-REVALIDATION-CASCADE-POC-2026-08-07.md"
        and (root / documentation).is_file(),
        "Standard revalidation cascade documentation binding drifted",
    )
    _require(
        record.get("publicSeam")
        == {
            "planner": "scripts/plan_standard_revalidation_cascade.py",
            "test": "tests/test_standard_revalidation_cascade_poc.py",
            "mode": "pure-zero-model-no-mutation",
        },
        "Standard revalidation cascade public seam drifted",
    )
    source_bindings = record.get("sourceBindings", {})
    _require(
        source_bindings
        == {
            "programAcceptanceMap": str(ACCEPTANCE_PATH).replace("\\", "/"),
            "historicalDesign": str(DESIGN_PATH).replace("\\", "/"),
            "layeredReconciliation": str(LAYERED_RECONCILIATION_PATH).replace(
                "\\", "/"
            ),
        }
        and all((root / path).is_file() for path in source_bindings.values()),
        "Standard revalidation cascade source binding drifted",
    )
    design_text = (root / DESIGN_PATH).read_text(encoding="utf-8")
    for phrase in (
        "settle affected historical debt",
        "define the verified starting point for later evolution",
        "affected-source and projection query",
        "bounded remediation batches",
        "old projection deprecation",
        "Unaffected surfaces are not rewritten",
        "Cross-repository mutation and ASSETS admission remain separately authorized",
    ):
        _require(
            phrase in design_text,
            f"Standard revalidation cascade source design drifted: {phrase}",
        )
    if layered is None:
        layered = json.loads(
            (root / LAYERED_RECONCILIATION_PATH).read_text(encoding="utf-8")
        )
    kept_open = {
        row.get("acceptanceId"): row
        for row in layered.get("keptOpen", [])
        if isinstance(row, dict)
    }
    source_boundary = kept_open.get("acceptance.standard-revalidation-cascade", {})
    _require(
        source_boundary.get("assessment") == "partial"
        and "project admission evidence"
        in source_boundary.get("reason", ""),
        "Standard revalidation cascade source boundary drifted",
    )
    if acceptance is None:
        acceptance = json.loads(
            (root / ACCEPTANCE_PATH).read_text(encoding="utf-8")
        )
    criteria = {
        row.get("id"): row
        for row in acceptance.get("acceptanceCriteria", [])
        if isinstance(row, dict)
    }
    evidence = {
        row.get("id"): row
        for row in acceptance.get("evidence", [])
        if isinstance(row, dict)
    }
    criterion = criteria.get("acceptance.standard-revalidation-cascade", {})
    evidence_item = evidence.get(EVIDENCE_ID, {})
    _require(
        criterion.get("assessment") == "partial"
        and criterion.get("verificationIds")
        == ["verification.standard-revalidation-cascade"]
        and EVIDENCE_ID in criterion.get("evidenceIds", [])
        and evidence_item.get("path") == str(POC_PATH).replace("\\", "/")
        and evidence_item.get("supports")
        == ["acceptance.standard-revalidation-cascade"],
        "Standard revalidation cascade acceptance boundary drifted",
    )
    fixture = record.get("syntheticFixture", {})
    request = fixture.get("request", {})
    _require(
        request.get("declaredSynthetic") is True
        and request.get("realStandardRepresented") is False,
        "Standard revalidation cascade synthetic boundary drifted",
    )
    _require(
        plan_cascade(request) == fixture.get("expectedPlan"),
        "Standard revalidation cascade positive fixture drifted",
    )
    mutations = _mutation_cases(request)
    _require(
        tuple(record.get("failureInjectionCaseIds", [])) == MUTATION_CASE_IDS
        and tuple(case_id for case_id, _, _ in mutations) == MUTATION_CASE_IDS,
        "Standard revalidation cascade mutation ledger drifted",
    )
    for case_id, mutated, expected_blocker in mutations:
        decision = plan_cascade(mutated)
        _require(
            decision.get("decision") == "blocked"
            and decision.get("executionAuthorized") is False
            and expected_blocker in decision.get("blockers", []),
            f"Standard revalidation cascade mutation did not fail closed: {case_id}",
        )
    claims = record.get("claimBoundary", {})
    _require(
        claims.get("provesGraphScopedPlannerMechanism") is True
        and all(
            claims.get(key) is False
            for key in (
                "provesRealStandardAdmission",
                "provesEvidenceTruth",
                "provesMigrationExecution",
                "provesCrossRepositoryAuthority",
                "provesOperationalValue",
                "provesProductionReadiness",
            )
        ),
        "Standard revalidation cascade claim boundary drifted",
    )
    _require(
        record.get("authorityBoundary")
        and all(value is False for value in record["authorityBoundary"].values()),
        "Standard revalidation cascade authority boundary expanded",
    )


def validate_repository_poc(root: Path = ROOT) -> dict[str, Any]:
    """Validate the checked-in synthetic cascade PoC record."""
    record = json.loads((root / POC_PATH).read_text(encoding="utf-8"))
    validate_poc_record(
        record,
        acceptance=json.loads(
            (root / ACCEPTANCE_PATH).read_text(encoding="utf-8")
        ),
        layered=json.loads(
            (root / LAYERED_RECONCILIATION_PATH).read_text(encoding="utf-8")
        ),
        root=root,
    )
    return record


def main() -> int:
    validate_repository_poc()
    print("Standard revalidation cascade PoC validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
