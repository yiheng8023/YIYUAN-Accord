#!/usr/bin/env python3
"""Calibrate architecture and security-review sub-oracles without a model."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
FIXTURE_PATH = (
    "tests/fixtures/"
    "software-lifecycle-architecture-security-suboracle-2026-07-27.json"
)
SCENARIO_MATRIX_PATH = (
    "registry/"
    "human-ai-collaboration-scenario-evidence-matrix-batch-01-"
    "2026-07-24.json"
)
EVALUATOR_PATH = (
    "scripts/"
    "evaluate_software_lifecycle_architecture_security_suboracle.py"
)
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_SEVERITY_RANK = {
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 4,
}


def _load(root: Path, relative_path: str) -> dict[str, Any]:
    return json.loads((root / relative_path).read_text(encoding="utf-8"))


def _file_sha256(root: Path, relative_path: str) -> str:
    return hashlib.sha256((root / relative_path).read_bytes()).hexdigest()


def _deep_merge(base: Any, patch: Any) -> Any:
    if not isinstance(base, dict) or not isinstance(patch, dict):
        return deepcopy(patch)
    merged = deepcopy(base)
    for key, value in patch.items():
        merged[key] = _deep_merge(merged.get(key), value)
    return merged


def _string_set(value: Any) -> set[str]:
    if not isinstance(value, list):
        return set()
    return {
        item
        for item in value
        if isinstance(item, str) and item.strip()
    }


def _nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _nonempty_list(value: Any) -> bool:
    return isinstance(value, list) and bool(value)


def _dedupe(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


def evaluate_architecture_candidate(
    candidate: dict[str, Any],
    oracle: dict[str, Any],
) -> dict[str, Any]:
    """Evaluate one structured architecture proposal against frozen inputs."""

    failures: list[str] = []
    if candidate.get("requirementsDigest") != oracle["requirementsDigest"]:
        failures.append("requirements-digest-mismatch")

    constraint_ids = _string_set(candidate.get("constraintIds"))
    required_constraints = set(oracle["requiredConstraintIds"])
    if not required_constraints <= constraint_ids:
        failures.append("required-constraint-missing")
    if not constraint_ids <= required_constraints:
        failures.append("unregistered-constraint")

    if not set(oracle["requiredDomainTerms"]) <= _string_set(
        candidate.get("domainTerms")
    ):
        failures.append("required-domain-term-missing")

    alternatives = candidate.get("alternatives")
    if (
        not isinstance(alternatives, list)
        or len(alternatives) < oracle["minimumAlternativeCount"]
    ):
        alternatives = []
        failures.append("insufficient-alternatives")
    option_ids = {
        item.get("optionId")
        for item in alternatives
        if isinstance(item, dict) and _nonempty_string(item.get("optionId"))
    }
    selected_option = candidate.get("selectedOptionId")
    if selected_option not in option_ids:
        failures.append("selected-option-not-declared")

    tradeoffs = candidate.get("tradeoffs")
    if not isinstance(tradeoffs, list):
        tradeoffs = []
    tradeoff_option_ids = {
        item.get("optionId")
        for item in tradeoffs
        if isinstance(item, dict)
        and _nonempty_string(item.get("optionId"))
        and _nonempty_string(item.get("benefit"))
        and _nonempty_string(item.get("cost"))
    }
    if tradeoff_option_ids != option_ids:
        failures.append("alternative-tradeoff-coverage-invalid")

    allowed_sources = set(oracle["allowedSourceIds"])
    traceable_items = [
        item
        for item in [*alternatives, *tradeoffs]
        if isinstance(item, dict)
    ]
    traceable_items.append(candidate.get("decisionRecord", {}))
    if any(
        not _string_set(item.get("sourceIds"))
        or not _string_set(item.get("sourceIds")) <= allowed_sources
        for item in traceable_items
    ):
        failures.append("source-trace-invalid")

    decision_record = candidate.get("decisionRecord")
    if (
        not isinstance(decision_record, dict)
        or decision_record.get("recordId")
        != oracle["requiredDecisionRecordId"]
        or decision_record.get("selectedOptionId") != selected_option
        or decision_record.get("status")
        != "draft-pending-accountable-review"
    ):
        failures.append("decision-record-invalid")

    if not set(oracle["requiredQualityAttributeScenarioIds"]) <= _string_set(
        candidate.get("qualityAttributeScenarioIds")
    ):
        failures.append("quality-attribute-scenario-missing")
    if not set(oracle["requiredSurfaceIds"]) <= _string_set(
        candidate.get("surfaceIds")
    ):
        failures.append("required-review-surface-missing")
    if not set(oracle["requiredFailureModeIds"]) <= _string_set(
        candidate.get("failureModeIds")
    ):
        failures.append("required-failure-mode-missing")

    expected_edges = {
        (item["from"], item["to"])
        for item in oracle["requiredDependencyEdges"]
    }
    actual_edges = {
        (item.get("from"), item.get("to"))
        for item in candidate.get("dependencyEdges", [])
        if isinstance(item, dict)
    }
    if actual_edges != expected_edges:
        failures.append("dependency-direction-invalid")

    seams = candidate.get("seams")
    if not isinstance(seams, list):
        seams = []
        failures.append("seam-shape-invalid")
    if any(
        item.get("status") == "real"
        and len(_string_set(item.get("adapterIds"))) < 2
        for item in seams
        if isinstance(item, dict)
    ):
        failures.append("real-seam-has-fewer-than-two-adapters")

    unknowns = candidate.get("unresolvedUnknowns")
    unknown_map = {
        item.get("unknownId"): item
        for item in unknowns
        if isinstance(unknowns, list) and isinstance(item, dict)
    }
    if any(
        unknown_id not in unknown_map
        or unknown_map[unknown_id].get("status") != "open"
        or not _nonempty_string(unknown_map[unknown_id].get("owner"))
        for unknown_id in oracle["requiredUnknownIds"]
    ):
        failures.append("required-unknown-not-preserved")

    migration = candidate.get("migrationImpact")
    if (
        not isinstance(migration, dict)
        or not _nonempty_list(migration.get("consumerGroups"))
        or not _nonempty_string(migration.get("compatibilityRisk"))
        or not _nonempty_string(migration.get("rollbackPath"))
    ):
        failures.append("migration-impact-or-rollback-incomplete")

    if candidate.get("irreversibleCommitmentClaimed") is not False:
        failures.append("irreversible-commitment-overclaim")
    if candidate.get("humanApprovalClaimed") is not False:
        failures.append("human-approval-overclaim")
    if candidate.get("productionReadyClaimed") is not False:
        failures.append("production-readiness-overclaim")
    if candidate.get("completeThreatCoverageClaimed") is not False:
        failures.append("complete-threat-coverage-overclaim")

    failures = _dedupe(failures)
    return {
        "decision": "accept" if not failures else "reject",
        "failureCodes": failures,
        "constraintCoverage": {
            "required": len(required_constraints),
            "observed": len(required_constraints & constraint_ids),
        },
        "alternativeCount": len(option_ids),
        "unresolvedUnknownCount": len(unknown_map),
        "claimBoundary": {
            "architectureCorrectnessProved": False,
            "maintainabilityProved": False,
            "productionReadinessProved": False,
            "skillValueProved": False,
        },
    }


def evaluate_security_review(
    review: dict[str, Any],
    oracle: dict[str, Any],
) -> dict[str, Any]:
    """Evaluate a parent-bound independent review receipt and fault ledger."""

    failures: list[str] = []
    identity = review.get("reviewerIdentity")
    if (
        not isinstance(identity, dict)
        or identity.get("subjectId") == oracle["producerId"]
        or not _nonempty_string(identity.get("subjectId"))
        or not _nonempty_string(identity.get("processId"))
        or identity.get("parentIssuedReceipt") is not True
    ):
        failures.append("reviewer-not-independent")

    artifact_digest = oracle["artifactDigest"]
    if review.get("reviewedArtifactDigest") != artifact_digest:
        failures.append("artifact-digest-mismatch")
    if (
        review.get("producerTreeBeforeSha256") != artifact_digest
        or review.get("producerTreeAfterSha256") != artifact_digest
    ):
        failures.append("reviewed-artifact-mutated")
    if review.get("independentReexecutionObserved") is not True:
        failures.append("independent-reexecution-missing")
    if review.get("privateOracleExposedToReviewer") is not False:
        failures.append("private-oracle-exposed")

    fault_oracle = review.get("faultOracle")
    if not isinstance(fault_oracle, dict):
        fault_oracle = {}
        failures.append("fault-oracle-shape-invalid")
    if (
        not _nonempty_string(fault_oracle.get("version"))
        or not isinstance(fault_oracle.get("oracleSourceSha256"), str)
        or not _SHA256.fullmatch(fault_oracle["oracleSourceSha256"])
    ):
        failures.append("fault-oracle-identity-invalid")

    detected = fault_oracle.get("detectedFaults")
    if not isinstance(detected, list):
        detected = []
        failures.append("detected-fault-ledger-invalid")
    detected_map: dict[str, dict[str, Any]] = {}
    duplicate_fault_ids: set[str] = set()
    for item in detected:
        if not isinstance(item, dict) or not _nonempty_string(
            item.get("faultId")
        ):
            failures.append("detected-fault-ledger-invalid")
            continue
        fault_id = item["faultId"]
        if fault_id in detected_map:
            duplicate_fault_ids.add(fault_id)
        detected_map[fault_id] = item
    if duplicate_fault_ids:
        failures.append("duplicate-detected-fault")

    expected_faults = {
        item["faultId"]: item
        for item in oracle["predeclaredFaults"]
    }
    missed_faults = sorted(set(expected_faults) - set(detected_map))
    if missed_faults:
        failures.append("predeclared-fault-missed")
    if not set(detected_map) <= set(expected_faults):
        failures.append("unregistered-fault-reported")
    for fault_id in sorted(set(expected_faults) & set(detected_map)):
        expected = expected_faults[fault_id]
        actual = detected_map[fault_id]
        if actual.get("locator") != expected["locator"]:
            failures.append("fault-locator-mismatch")
        if not _nonempty_string(actual.get("evidence")):
            failures.append("fault-evidence-missing")
        if _SEVERITY_RANK.get(actual.get("severity"), 0) < (
            _SEVERITY_RANK[expected["minimumSeverity"]]
        ):
            failures.append("severity-under-calibrated")

    reported_canaries = _string_set(
        fault_oracle.get("reportedBenignCanaryIds")
    )
    benign_canaries = set(oracle["benignCanaryIds"])
    false_positive_ids = sorted(reported_canaries & benign_canaries)
    if len(false_positive_ids) > oracle["maximumFalsePositiveCount"]:
        failures.append("benign-canary-false-positive")
    if not reported_canaries <= benign_canaries:
        failures.append("unknown-canary-reported")

    threat_model = review.get("threatModel")
    if not isinstance(threat_model, dict) or any(
        not _nonempty_list(threat_model.get(key))
        for key in (
            "assets",
            "trustBoundaries",
            "attackerInputs",
            "invariants",
            "failureModes",
        )
    ):
        failures.append("threat-model-surface-incomplete")

    findings = review.get("findings")
    if not isinstance(findings, list):
        findings = []
        failures.append("finding-ledger-invalid")
    unresolved_high = [
        item.get("findingId")
        for item in findings
        if isinstance(item, dict)
        and item.get("severity") in {"high", "critical"}
        and item.get("status") != "resolved-reverified"
    ]
    if unresolved_high:
        failures.append("unresolved-high-finding")
    if bool(unresolved_high) != bool(
        review.get("summaryUnresolvedHighFinding")
    ):
        failures.append("summary-conflicts-with-finding-ledger")

    supply_chain = review.get("supplyChainComponents")
    if not isinstance(supply_chain, list):
        supply_chain = []
    supply_map = {
        item.get("componentId"): item
        for item in supply_chain
        if isinstance(item, dict)
    }
    if any(
        component_id not in supply_map
        or not isinstance(
            supply_map[component_id].get("identityDigest"), str
        )
        or not _SHA256.fullmatch(
            supply_map[component_id]["identityDigest"]
        )
        for component_id in oracle["requiredSupplyChainComponentIds"]
    ):
        failures.append("supply-chain-identity-incomplete")

    if review.get("humanAcceptanceClaimed") is not False:
        failures.append("human-acceptance-overclaim")
    if review.get("fixAppliedByReviewer") is not False:
        failures.append("reviewer-crossed-read-only-boundary")

    failures = _dedupe(failures)
    true_positive_count = len(set(expected_faults) & set(detected_map))
    return {
        "decision": "accept" if not failures else "reject",
        "failureCodes": failures,
        "faultMetrics": {
            "predeclaredFaultCount": len(expected_faults),
            "truePositiveCount": true_positive_count,
            "falseNegativeCount": len(missed_faults),
            "falseNegativeIds": missed_faults,
            "falsePositiveCount": len(false_positive_ids),
            "falsePositiveIds": false_positive_ids,
        },
        "independenceClass": (
            "parent-issued-distinct-role-and-process-receipt"
            if "reviewer-not-independent" not in failures
            else "not-independent"
        ),
        "claimBoundary": {
            "cognitiveIndependenceProved": False,
            "absenceOfDefectsProved": False,
            "completeThreatCoverageProved": False,
            "productionReadinessProved": False,
            "skillValueProved": False,
        },
    }


def build_architecture_security_suboracle_pack(
    *, root: Path = ROOT
) -> dict[str, Any]:
    fixture = _load(root, FIXTURE_PATH)
    architecture_oracle = fixture["architectureOracle"]
    security_oracle = fixture["securityReviewOracle"]

    architecture_positive = evaluate_architecture_candidate(
        architecture_oracle["positiveCase"]["candidate"],
        architecture_oracle,
    )
    architecture_controls = {
        item["id"]: evaluate_architecture_candidate(
            _deep_merge(
                architecture_oracle["positiveCase"]["candidate"],
                item["candidatePatch"],
            ),
            architecture_oracle,
        )
        for item in architecture_oracle["negativeControls"]
    }
    security_positive = evaluate_security_review(
        security_oracle["positiveCase"]["review"],
        security_oracle,
    )
    security_controls = {
        item["id"]: evaluate_security_review(
            _deep_merge(
                security_oracle["positiveCase"]["review"],
                item["reviewPatch"],
            ),
            security_oracle,
        )
        for item in security_oracle["negativeControls"]
    }
    positive_acceptance = {
        "architecture": architecture_positive["decision"] == "accept",
        "independentSecurityReview": (
            security_positive["decision"] == "accept"
        ),
    }
    negative_rejection = {
        **{
            f"architecture:{control_id}": result["decision"] == "reject"
            for control_id, result in architecture_controls.items()
        },
        **{
            f"security:{control_id}": result["decision"] == "reject"
            for control_id, result in security_controls.items()
        },
    }
    return {
        "schema": 1,
        "kind": "software-lifecycle-architecture-security-suboracle-pack",
        "mode": "zero-model-synthetic-seeded-fault-calibration",
        "sourceBindings": [
            {
                "path": path,
                "fileSha256": _file_sha256(root, path),
            }
            for path in (
                FIXTURE_PATH,
                SCENARIO_MATRIX_PATH,
                EVALUATOR_PATH,
            )
        ],
        "designInputs": fixture["designInputs"],
        "results": {
            "architecture": {
                "positive": architecture_positive,
                "negativeControls": architecture_controls,
            },
            "independentSecurityReview": {
                "positive": security_positive,
                "negativeControls": security_controls,
            },
        },
        "positiveAcceptance": positive_acceptance,
        "negativeControlRejection": negative_rejection,
        "allPositiveAccepted": all(positive_acceptance.values()),
        "allNegativeControlsRejected": all(
            negative_rejection.values()
        ),
        "execution": {
            "agentDispatchCount": 0,
            "modelCallCount": 0,
            "networkAccessUsed": False,
            "gitMutationUsed": False,
            "externalWriteUsed": False,
        },
        "claimBoundary": fixture["claimBoundary"],
    }


def main() -> int:
    pack = build_architecture_security_suboracle_pack()
    print(json.dumps(pack, ensure_ascii=False, indent=2))
    return (
        0
        if pack["allPositiveAccepted"]
        and pack["allNegativeControlsRejected"]
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
