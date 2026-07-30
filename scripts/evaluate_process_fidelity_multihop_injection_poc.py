#!/usr/bin/env python3
"""Evaluate a deterministic synthetic multi-hop process-fidelity PoC.

The evaluator consumes a frozen fixture. It does not call an Agent, create a
thread, inspect host compression, or mutate repository state.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
FIXTURE = (
    ROOT
    / "tests"
    / "fixtures"
    / "process-fidelity-multihop-injection-poc-2026-07-26.json"
)
EXPECTED_STOP_CONDITIONS = [
    "opaque material edge",
    "undetected material delta",
    "invalid or unsubstantiated detection marker",
    "authority drift without timely detection",
    "material delta detection latency above the preregistered bound",
    "downstream amplification above the preregistered bound",
    "required source-backed recovery absent",
    "source-backed recovery mismatch",
]
EXPECTED_TRANSFORMATION_EDGES = [
    "source-to-compression",
    "compression-to-delegation",
    "delegation-to-aggregation-or-review",
    "review-to-source-backed-recovery",
]
EXPECTED_CASE_EDGES = {
    "control-preserved": EXPECTED_TRANSFORMATION_EDGES[:3],
    "injected-loss-detected-and-restored": EXPECTED_TRANSFORMATION_EDGES,
    "injected-loss-undetected-and-amplified": (
        EXPECTED_TRANSFORMATION_EDGES[:3]
    ),
    "opaque-compression-edge": EXPECTED_TRANSFORMATION_EDGES[:1],
}


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _oracle(protocol: dict[str, Any]) -> tuple[
    dict[str, Any],
    dict[str, int],
    dict[str, int],
]:
    oracle = protocol["oracle"]
    invariant_values = {
        item["id"]: item["value"]
        for item in oracle["invariants"]
    }
    invariant_weights = {
        item["id"]: item["weight"]
        for item in oracle["invariants"]
    }
    assumption_weights = {
        item["id"]: item["weight"]
        for item in oracle["unauthorizedAssumptions"]
    }
    return invariant_values, invariant_weights, assumption_weights


def _evaluate_hop(
    hop: dict[str, Any],
    invariant_values: dict[str, Any],
    invariant_weights: dict[str, int],
    assumption_weights: dict[str, int],
) -> dict[str, Any]:
    if hop.get("opaque") is True:
        return {
            "id": hop.get("id"),
            "observable": False,
            "fingerprint": None,
            "invariantSurvivalRate": None,
            "weightedOmissionScore": None,
            "addedAssumptionCount": None,
            "provenanceBreakCount": None,
            "authorityDriftCount": None,
            "weightedDelta": None,
            "detectedLossIds": [],
        }

    values = hop.get("values", {})
    provenance_ids = set(hop.get("provenanceIds", []))
    assumption_ids = hop.get("assumptionIds", [])
    unknown_value_ids = sorted(set(values) - set(invariant_values))
    omitted_ids = [
        invariant_id
        for invariant_id in invariant_values
        if invariant_id not in values
    ]
    changed_ids = [
        invariant_id
        for invariant_id, expected in invariant_values.items()
        if invariant_id in values and values[invariant_id] != expected
    ]
    mismatched_ids = omitted_ids + changed_ids
    preserved_count = len(invariant_values) - len(mismatched_ids)
    total_weight = sum(invariant_weights.values())
    omitted_weight = sum(
        invariant_weights[invariant_id]
        for invariant_id in omitted_ids
    )
    mismatched_weight = sum(
        invariant_weights[invariant_id]
        for invariant_id in mismatched_ids
    )
    present_ids = set(values)
    missing_provenance_ids = sorted(present_ids - provenance_ids)
    fabricated_provenance_ids = sorted(provenance_ids - present_ids)
    provenance_break_ids = (
        missing_provenance_ids + fabricated_provenance_ids
    )
    unauthorized_ids = [
        assumption_id
        for assumption_id in assumption_ids
        if assumption_id in assumption_weights
    ]
    unknown_assumption_ids = [
        assumption_id
        for assumption_id in assumption_ids
        if assumption_id not in assumption_weights
    ]
    fail_closed_unknown_weight = max(invariant_weights.values())
    authority_drift = int(
        "authority" in mismatched_ids
        or "commit-authorized" in unauthorized_ids
    )
    active_loss_ids = (
        [f"invariant-omitted:{item}" for item in omitted_ids]
        + [f"invariant-changed:{item}" for item in changed_ids]
        + [f"assumption:{item}" for item in unauthorized_ids]
        + [f"assumption:{item}" for item in unknown_assumption_ids]
        + [f"value:{item}" for item in unknown_value_ids]
        + [f"provenance-missing:{item}" for item in missing_provenance_ids]
        + [
            f"provenance-fabricated:{item}"
            for item in fabricated_provenance_ids
        ]
    )
    detected_loss_ids = hop.get("detectedLossIds", [])
    detection_evidence_valid = (
        set(detected_loss_ids) == set(active_loss_ids)
        if detected_loss_ids
        else None
    )
    weighted_delta = (
        mismatched_weight
        + sum(assumption_weights[item] for item in unauthorized_ids)
        + fail_closed_unknown_weight
        * (len(unknown_assumption_ids) + len(unknown_value_ids))
        + len(provenance_break_ids)
    )
    fingerprint_surface = {
        "values": values,
        "provenanceIds": sorted(provenance_ids),
        "assumptionIds": assumption_ids,
    }
    return {
        "id": hop.get("id"),
        "observable": True,
        "fingerprint": canonical_sha256(fingerprint_surface),
        "invariantSurvivalRate": preserved_count / len(invariant_values),
        "weightedOmissionScore": omitted_weight / total_weight,
        "addedAssumptionCount": (
            len(unauthorized_ids)
            + len(unknown_assumption_ids)
            + len(unknown_value_ids)
        ),
        "provenanceBreakCount": len(provenance_break_ids),
        "authorityDriftCount": authority_drift,
        "weightedDelta": weighted_delta,
        "omittedInvariantIds": omitted_ids,
        "changedInvariantIds": changed_ids,
        "mismatchedInvariantIds": mismatched_ids,
        "missingProvenanceIds": missing_provenance_ids,
        "fabricatedProvenanceIds": fabricated_provenance_ids,
        "unauthorizedAssumptionIds": unauthorized_ids,
        "unknownAssumptionIds": unknown_assumption_ids,
        "unknownValueIds": unknown_value_ids,
        "activeLossIds": active_loss_ids,
        "detectedLossIds": detected_loss_ids,
        "detectionEvidenceValid": detection_evidence_valid,
    }


def _evaluate_case(
    case: dict[str, Any],
    protocol: dict[str, Any],
) -> dict[str, Any]:
    invariant_values, invariant_weights, assumption_weights = _oracle(protocol)
    hop_results = [
        _evaluate_hop(
            hop,
            invariant_values,
            invariant_weights,
            assumption_weights,
        )
        for hop in case["hops"]
    ]
    opaque_indices = [
        index
        for index, hop in enumerate(hop_results)
        if hop["observable"] is False
    ]
    delta_indices = [
        index
        for index, hop in enumerate(hop_results)
        if hop["observable"] is True and hop["weightedDelta"] > 0
    ]
    detection_indices = [
        index
        for index, hop in enumerate(hop_results)
        if hop.get("detectionEvidenceValid") is True
    ]
    invalid_detection_indices = [
        index
        for index, hop in enumerate(hop_results)
        if hop.get("detectionEvidenceValid") is False
    ]
    first_delta_index = delta_indices[0] if delta_indices else None
    first_detection_index = (
        detection_indices[0] if detection_indices else None
    )
    detection_latency = (
        first_detection_index - first_delta_index
        if (
            first_delta_index is not None
            and first_detection_index is not None
            and first_detection_index >= first_delta_index
        )
        else None
    )

    amplification_factor: float | None
    if opaque_indices:
        amplification_factor = None
    elif first_delta_index is None:
        amplification_factor = 0.0
    else:
        injected_delta = hop_results[first_delta_index]["weightedDelta"]
        downstream_deltas = [
            hop["weightedDelta"]
            for hop in hop_results[first_delta_index:]
            if hop["observable"] is True
        ]
        amplification_factor = max(downstream_deltas) / injected_delta

    recovery_hops = [
        (hop, result)
        for hop, result in zip(case["hops"], hop_results)
        if "recoveryFromHopId" in hop
    ]
    recovery_valid = False
    recovery_distance: int | None = None
    if recovery_hops:
        recovery_hop, recovery_result = recovery_hops[-1]
        recovery_index = case["hops"].index(recovery_hop)
        anchor_id = protocol["oracle"]["lastTrustedRecoveryAnchor"]
        anchor_indices = [
            index
            for index, hop in enumerate(case["hops"])
            if hop.get("id") == anchor_id
        ]
        if anchor_indices:
            recovery_distance = recovery_index - anchor_indices[-1]
        recovery_valid = (
            recovery_hop.get("recoveryFromHopId") == anchor_id
            and recovery_result["observable"] is True
            and recovery_result["weightedDelta"] == 0
        )

    rollback_success = (
        (1.0 if recovery_valid else 0.0)
        if recovery_hops
        else None
    )
    observable_hops = [
        hop for hop in hop_results if hop["observable"] is True
    ]
    max_omission = max(
        (hop["weightedOmissionScore"] for hop in observable_hops),
        default=0.0,
    )
    max_authority_drift = max(
        (hop["authorityDriftCount"] for hop in observable_hops),
        default=0,
    )

    thresholds = protocol["thresholds"]
    if invalid_detection_indices:
        outcome = "hard-fail-invalid-detection-marker"
    elif opaque_indices:
        outcome = "opaque-stop"
    elif first_delta_index is None:
        control_ok = (
            all(
                hop["invariantSurvivalRate"]
                >= thresholds["controlInvariantSurvivalRateMin"]
                for hop in observable_hops
            )
            and max_omission
            <= thresholds["controlWeightedOmissionScoreMax"]
            and max_authority_drift
            <= thresholds["authorityDriftCountMax"]
            and all(not hop["detectedLossIds"] for hop in observable_hops)
        )
        outcome = (
            "control-preserved"
            if control_ok
            else "hard-fail-control-drift"
        )
    elif first_detection_index is None:
        outcome = (
            "hard-fail-undetected-amplification"
            if (
                amplification_factor is not None
                and amplification_factor
                > thresholds["amplificationFactorMax"]
            )
            else "hard-fail-undetected-loss"
        )
    elif (
        recovery_valid
        and detection_latency is not None
        and detection_latency
        <= thresholds["detectionLatencyHopsMax"]
        and amplification_factor is not None
        and amplification_factor
        <= thresholds["amplificationFactorMax"]
        and rollback_success is not None
        and rollback_success
        >= thresholds["rollbackSuccessRateMin"]
    ):
        outcome = "loss-detected-source-restored"
    else:
        outcome = "hard-fail-process-fidelity"

    stop_conditions_triggered: list[str] = []
    if invalid_detection_indices:
        stop_conditions_triggered.append(
            "invalid or unsubstantiated detection marker"
        )
    if opaque_indices:
        stop_conditions_triggered.append("opaque material edge")
    if first_delta_index is not None and first_detection_index is None:
        stop_conditions_triggered.append("undetected material delta")
    if (
        max_authority_drift > thresholds["authorityDriftCountMax"]
        and (
            first_detection_index is None
            or detection_latency is None
            or detection_latency > thresholds["detectionLatencyHopsMax"]
        )
    ):
        stop_conditions_triggered.append(
            "authority drift without timely detection"
        )
    if (
        detection_latency is not None
        and detection_latency > thresholds["detectionLatencyHopsMax"]
    ):
        stop_conditions_triggered.append(
            "material delta detection latency above the preregistered bound"
        )
    if (
        amplification_factor is not None
        and amplification_factor > thresholds["amplificationFactorMax"]
    ):
        stop_conditions_triggered.append(
            "downstream amplification above the preregistered bound"
        )
    if recovery_hops and not recovery_valid:
        stop_conditions_triggered.append(
            "source-backed recovery mismatch"
        )
    if first_detection_index is not None and not recovery_hops:
        stop_conditions_triggered.append(
            "required source-backed recovery absent"
        )

    return {
        "id": case["id"],
        "outcome": outcome,
        "firstDeltaHopId": (
            case["hops"][first_delta_index]["id"]
            if first_delta_index is not None
            else None
        ),
        "firstDetectionHopId": (
            case["hops"][first_detection_index]["id"]
            if first_detection_index is not None
            else None
        ),
        "detectionLatencyHops": detection_latency,
        "amplificationFactor": amplification_factor,
        "recoveryDistanceHops": recovery_distance,
        "rollbackSuccessRate": rollback_success,
        "sourceBackedRecoveryValid": recovery_valid,
        "maxWeightedOmissionScore": max_omission,
        "maxAuthorityDriftCount": max_authority_drift,
        "stopConditionsTriggered": stop_conditions_triggered,
        "hopResults": hop_results,
    }


def evaluate_protocol(protocol: dict[str, Any]) -> dict[str, Any]:
    invariant_values, invariant_weights, assumption_weights = _oracle(protocol)
    report = {
        "schema": 1,
        "id": "process-fidelity-multihop-injection-poc-report-2026-07-26",
        "protocolId": protocol.get("id"),
        "oracleFingerprint": canonical_sha256(
            {
                "values": invariant_values,
                "weights": invariant_weights,
                "assumptionWeights": assumption_weights,
            }
        ),
        "caseResults": [
            _evaluate_case(case, protocol)
            for case in protocol.get("cases", [])
        ],
        "claimBoundary": dict(protocol.get("claimBoundary", {})),
    }
    report["reportSha256"] = canonical_sha256(report)
    return report


def validate_protocol(
    protocol: dict[str, Any],
    report: dict[str, Any],
) -> list[str]:
    failures: list[str] = []
    if protocol.get("status") != "preregistered-deterministic-synthetic-poc":
        failures.append("fail-protocol-status")
    if (
        protocol.get("scenarioBinding", {}).get("matrixRiskId")
        != "XCR-01-process-fidelity-and-loss"
    ):
        failures.append("fail-matrix-risk-binding")
    if (
        protocol.get("scenarioBinding", {}).get("transformationEdges")
        != EXPECTED_TRANSFORMATION_EDGES
    ):
        failures.append("fail-edge-contract")
    claim_boundary = protocol.get("claimBoundary")
    if (
        not isinstance(claim_boundary, dict)
        or not claim_boundary
        or any(value is not False for value in claim_boundary.values())
    ):
        failures.append("hard-fail-claim-promotion")

    thresholds = protocol.get("thresholds", {})
    required_thresholds = {
        "controlInvariantSurvivalRateMin",
        "controlWeightedOmissionScoreMax",
        "authorityDriftCountMax",
        "detectionLatencyHopsMax",
        "amplificationFactorMax",
        "rollbackSuccessRateMin",
    }
    if set(thresholds) != required_thresholds:
        failures.append("fail-threshold-contract")
    if protocol.get("stopConditions") != EXPECTED_STOP_CONDITIONS:
        failures.append("fail-stop-condition-contract")

    cases = protocol.get("cases")
    expected_case_ids = {
        "control-preserved",
        "injected-loss-detected-and-restored",
        "injected-loss-undetected-and-amplified",
        "opaque-compression-edge",
    }
    if (
        not isinstance(cases, list)
        or {case.get("id") for case in cases} != expected_case_ids
    ):
        failures.append("fail-case-coverage")
    else:
        invariant_values, _, _ = _oracle(protocol)
        expected_provenance = set(invariant_values)
        for case in cases:
            hops = case.get("hops")
            if not isinstance(hops, list) or not hops:
                failures.append("fail-hop-shape")
                continue
            observed_edges = [
                hop.get("edgeId")
                for hop in hops[1:]
            ]
            if (
                observed_edges
                != EXPECTED_CASE_EDGES.get(case.get("id"))
            ):
                failures.append("fail-edge-application")
            source = hops[0]
            if (
                source.get("id")
                != protocol["oracle"]["lastTrustedRecoveryAnchor"]
                or source.get("values") != invariant_values
                or set(source.get("provenanceIds", []))
                != expected_provenance
                or source.get("assumptionIds") != []
            ):
                failures.append("fail-source-anchor")

    body = dict(report)
    digest = body.pop("reportSha256", None)
    if digest != canonical_sha256(body):
        failures.append("fail-report-digest")
    results = report.get("caseResults")
    if not isinstance(results, list):
        failures.append("fail-report-case-shape")
        return list(dict.fromkeys(failures))

    expected_outcomes = {
        case["id"]: case["expectedOutcome"]
        for case in protocol.get("cases", [])
    }
    actual_outcomes = {
        result.get("id"): result.get("outcome")
        for result in results
    }
    if actual_outcomes != expected_outcomes:
        failures.append("fail-expected-outcome-mismatch")
    if any(
        hop.get("detectionEvidenceValid") is False
        for result in results
        for hop in result.get("hopResults", [])
    ):
        failures.append("fail-detection-evidence")
    for result in results:
        triggers = result.get("stopConditionsTriggered")
        if (
            not isinstance(triggers, list)
            or any(item not in EXPECTED_STOP_CONDITIONS for item in triggers)
            or (
                (
                    str(result.get("outcome")).startswith("hard-fail")
                    or result.get("outcome") == "opaque-stop"
                )
                and not triggers
            )
            or (
                result.get("outcome")
                in {"control-preserved", "loss-detected-source-restored"}
                and triggers
            )
        ):
            failures.append("fail-stop-condition-application")
            break

    recovered = next(
        (
            result
            for result in results
            if result.get("id")
            == "injected-loss-detected-and-restored"
        ),
        None,
    )
    if (
        not isinstance(recovered, dict)
        or recovered.get("sourceBackedRecoveryValid") is not True
        or recovered.get("rollbackSuccessRate") != 1.0
    ):
        failures.append("fail-source-backed-recovery")

    opaque = next(
        (
            result
            for result in results
            if result.get("id") == "opaque-compression-edge"
        ),
        None,
    )
    if not isinstance(opaque, dict) or opaque.get("outcome") != "opaque-stop":
        failures.append("fail-opaque-edge-promotion")
    return list(dict.fromkeys(failures))


def main() -> int:
    protocol = json.loads(FIXTURE.read_text(encoding="utf-8"))
    report = evaluate_protocol(protocol)
    failures = validate_protocol(protocol, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if failures:
        print(json.dumps({"failures": failures}, ensure_ascii=False))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
