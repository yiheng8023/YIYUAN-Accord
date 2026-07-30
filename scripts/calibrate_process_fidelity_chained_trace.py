#!/usr/bin/env python3
"""Calibrate observable chained process-fidelity traces without Agent calls."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from .evaluate_process_fidelity_multihop_injection_poc import (
        _evaluate_case,
        canonical_sha256,
    )
except ImportError:  # pragma: no cover - direct script execution
    from evaluate_process_fidelity_multihop_injection_poc import (
        _evaluate_case,
        canonical_sha256,
    )


ROOT = Path(__file__).resolve().parent.parent
FIXTURE_PATH = (
    "tests/fixtures/process-fidelity-chained-trace-calibration-2026-07-27.json"
)
EXPECTED_CASE_OUTCOMES = {
    "linked-control": "linked-control-pass",
    "predecessor-input-linkage-mismatch": (
        "hard-fail-predecessor-input-linkage"
    ),
    "local-loss-propagated-and-amplified": (
        "hard-fail-undetected-amplification"
    ),
    "terminal-restoration-does-not-erase-intermediate-loss": (
        "recorded-intermediate-loss-terminal-restored"
    ),
    "opaque-material-edge": "hard-fail-opaque-material-edge",
}
EXPECTED_EDGES = [
    "source-to-decomposition",
    "decomposition-to-routing",
    "routing-to-acceptance",
]


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _artifact_hop(
    hop_id: str,
    artifact: dict[str, Any],
    *,
    edge_id: str | None = None,
    recovery_from_anchor_id: str | None = None,
) -> dict[str, Any]:
    result = {
        "id": hop_id,
        "values": artifact.get("values", {}),
        "provenanceIds": artifact.get("provenanceIds", []),
        "assumptionIds": artifact.get("assumptionIds", []),
        "detectedLossIds": artifact.get("detectedLossIds", []),
    }
    if edge_id is not None:
        result["edgeId"] = edge_id
    if recovery_from_anchor_id is not None:
        result["recoveryFromHopId"] = recovery_from_anchor_id
    return result


def _compatibility_protocol(contract: dict[str, Any]) -> dict[str, Any]:
    return {
        "oracle": contract["oracle"],
        "thresholds": contract["thresholds"],
    }


def _evaluate_trace_case(
    case: dict[str, Any],
    contract: dict[str, Any],
) -> dict[str, Any]:
    artifacts = case["artifacts"]
    source_id = case["sourceArtifactId"]
    source = artifacts[source_id]
    prior_output_id = source_id
    legacy_hops = [_artifact_hop("source", source)]
    edge_ledgers: list[dict[str, Any]] = []
    linkage_failures: list[str] = []
    material_opaque_edges: list[str] = []

    contracts = {
        item["edgeId"]: item for item in contract["transformContracts"]
    }
    for hop in case["hops"]:
        edge_id = hop["edgeId"]
        transform = contracts[edge_id]
        input_id = hop["inputArtifactId"]
        input_artifact = artifacts[input_id]
        predecessor = artifacts[prior_output_id]
        input_hash = canonical_sha256(input_artifact)
        predecessor_hash = canonical_sha256(predecessor)
        linked = input_hash == predecessor_hash
        if not linked:
            linkage_failures.append(edge_id)

        opaque = hop.get("opaque") is True
        output_id = hop.get("outputArtifactId")
        output_hash = None
        if opaque:
            material_opaque_edges.append(edge_id)
            legacy_hops.append(
                {
                    "id": hop["id"],
                    "edgeId": edge_id,
                    "opaque": True,
                }
            )
        else:
            _require(
                isinstance(output_id, str) and output_id in artifacts,
                f"Trace output artifact is missing: {case['id']}:{edge_id}",
            )
            output = artifacts[output_id]
            output_hash = canonical_sha256(output)
            legacy_hops.append(
                _artifact_hop(
                    hop["id"],
                    output,
                    edge_id=edge_id,
                    recovery_from_anchor_id=hop.get(
                        "recoveryFromAnchorId"
                    ),
                )
            )
            prior_output_id = output_id

        edge_ledgers.append(
            {
                "edgeId": edge_id,
                "material": transform["material"],
                "transformContractSha256": canonical_sha256(transform),
                "predecessorOutputArtifactSha256": predecessor_hash,
                "inputArtifactSha256": input_hash,
                "inputEqualsPredecessorOutput": linked,
                "outputArtifactSha256": output_hash,
                "opaque": opaque,
            }
        )

    legacy = _evaluate_case(
        {"id": case["id"], "hops": legacy_hops},
        _compatibility_protocol(contract),
    )
    hop_results = legacy["hopResults"]
    weighted_deltas = [
        item["weightedDelta"]
        for item in hop_results
        if item["observable"] is True
    ]
    first_loss_index = next(
        (
            index
            for index, item in enumerate(hop_results)
            if item["observable"] is True and item["weightedDelta"] > 0
        ),
        None,
    )
    downstream_affected = (
        sum(
            1
            for item in hop_results[first_loss_index + 1 :]
            if item["observable"] is True and item["weightedDelta"] > 0
        )
        if first_loss_index is not None
        else 0
    )
    final_observable = hop_results[-1]["observable"] is True
    terminal_matches_source = (
        final_observable
        and hop_results[-1]["fingerprint"]
        == hop_results[0]["fingerprint"]
    )
    intermediate_loss_present = any(
        item["observable"] is True and item["weightedDelta"] > 0
        for item in hop_results[1:-1]
    )

    if linkage_failures:
        outcome = "hard-fail-predecessor-input-linkage"
    elif material_opaque_edges:
        outcome = "hard-fail-opaque-material-edge"
    elif intermediate_loss_present and terminal_matches_source:
        outcome = "recorded-intermediate-loss-terminal-restored"
    elif legacy["outcome"] == "control-preserved":
        outcome = "linked-control-pass"
    else:
        outcome = legacy["outcome"]

    return {
        "id": case["id"],
        "expectedOutcome": case["expectedOutcome"],
        "outcome": outcome,
        "matchesExpectedOutcome": outcome == case["expectedOutcome"],
        "absoluteLedger": {
            "terminalMatchesSourceAnchor": terminal_matches_source,
            "predecessorLinkageFailureEdgeIds": linkage_failures,
            "materialOpaqueEdgeIds": material_opaque_edges,
        },
        "processLedger": {
            "edgeLedgers": edge_ledgers,
            "intermediateLossPresent": intermediate_loss_present,
            "cumulativeWeightedDelta": sum(weighted_deltas),
            "downstreamAffectedHopCount": downstream_affected,
            "detectionLatencyHops": legacy["detectionLatencyHops"],
            "amplificationFactor": legacy["amplificationFactor"],
            "recoveryDistanceHops": legacy["recoveryDistanceHops"],
            "rollbackSuccessRate": legacy["rollbackSuccessRate"],
            "sourceBackedRecoveryValid": legacy[
                "sourceBackedRecoveryValid"
            ],
            "opaqueMetricsRemainUnknown": (
                bool(material_opaque_edges)
                and legacy["amplificationFactor"] is None
            ),
        },
        "legacyMetricEvaluatorOutcome": legacy["outcome"],
        "processAcceptancePass": outcome == "linked-control-pass",
    }


def evaluate_contract(contract: dict[str, Any]) -> dict[str, Any]:
    results = [
        _evaluate_trace_case(case, contract) for case in contract["cases"]
    ]
    return {
        "schema": 1,
        "id": (
            "process-fidelity-chained-trace-measurement-calibration-"
            "report-2026-07-27"
        ),
        "contractId": contract.get("id"),
        "status": (
            "zero-agent-measurement-calibration-passed"
            if all(item["matchesExpectedOutcome"] for item in results)
            else "zero-agent-measurement-calibration-failed"
        ),
        "agentDispatchCount": 0,
        "modelCallCount": 0,
        "caseResults": results,
        "decision": {
            "measurementCalibrationPassed": all(
                item["matchesExpectedOutcome"] for item in results
            ),
            "formalLiveCohortAuthorized": False,
            "existingTransportSmokeCountsAsProcessTrace": False,
            "nextBoundedResult": (
                "implement a raw-event trace adapter and prove deterministic "
                "rescore of the existing smoke without manual supplementation"
            ),
        },
        "claimBoundary": dict(contract["claimBoundary"]),
    }


def validate_contract(
    contract: dict[str, Any],
    report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    _require(contract.get("schema") == 1, "Trace calibration schema drifted")
    _require(
        contract.get("status")
        == "preregistered-zero-agent-controlled-transcription-calibration",
        "Trace calibration status drifted",
    )
    execution = contract.get("executionBoundary")
    _require(
        isinstance(execution, dict)
        and execution.get("agentDispatchCount") == 0
        and execution.get("modelCallCount") == 0
        and execution.get("externalAccessUsed") is False
        and execution.get("writeOutsideRepository") is False
        and execution.get("liveCohortAuthorized") is False,
        "Trace calibration execution boundary drifted",
    )
    estimand = contract.get("estimandBoundary")
    _require(
        isinstance(estimand, dict)
        and estimand.get("hiddenModelStateObservable") is False
        and estimand.get("acknowledgementProvesSemanticRetention") is False
        and estimand.get("opaqueMaterialEdgeMayBeScoredAsZero") is False,
        "Trace calibration estimand boundary drifted",
    )
    edges = contract.get("transformContracts")
    _require(
        isinstance(edges, list)
        and [item.get("edgeId") for item in edges] == EXPECTED_EDGES
        and all(item.get("material") is True for item in edges),
        "Trace calibration edge contract drifted",
    )
    cases = contract.get("cases")
    _require(
        isinstance(cases, list)
        and {item.get("id"): item.get("expectedOutcome") for item in cases}
        == EXPECTED_CASE_OUTCOMES,
        "Trace calibration case contract drifted",
    )
    _require(
        isinstance(contract.get("claimBoundary"), dict)
        and all(value is False for value in contract["claimBoundary"].values()),
        "Trace calibration claim boundary was promoted",
    )

    evaluated = report or evaluate_contract(contract)
    _require(
        evaluated.get("status")
        == "zero-agent-measurement-calibration-passed"
        and evaluated.get("agentDispatchCount") == 0
        and evaluated.get("modelCallCount") == 0,
        "Trace calibration report did not pass",
    )
    indexed = {item["id"]: item for item in evaluated["caseResults"]}
    _require(
        set(indexed) == set(EXPECTED_CASE_OUTCOMES)
        and all(
            indexed[case_id]["outcome"] == expected
            and indexed[case_id]["matchesExpectedOutcome"] is True
            for case_id, expected in EXPECTED_CASE_OUTCOMES.items()
        ),
        "Trace calibration expected outcomes drifted",
    )
    _require(
        indexed["predecessor-input-linkage-mismatch"]["absoluteLedger"][
            "predecessorLinkageFailureEdgeIds"
        ]
        == ["decomposition-to-routing"],
        "Trace calibration did not catch predecessor linkage drift",
    )
    amplified = indexed["local-loss-propagated-and-amplified"][
        "processLedger"
    ]
    _require(
        amplified["downstreamAffectedHopCount"] >= 1
        and amplified["amplificationFactor"] > 1.0,
        "Trace calibration did not catch cascading amplification",
    )
    restored = indexed[
        "terminal-restoration-does-not-erase-intermediate-loss"
    ]
    _require(
        restored["absoluteLedger"]["terminalMatchesSourceAnchor"] is True
        and restored["processLedger"]["intermediateLossPresent"] is True
        and restored["processAcceptancePass"] is False,
        "Trace calibration erased intermediate loss after terminal restoration",
    )
    opaque = indexed["opaque-material-edge"]
    _require(
        opaque["processLedger"]["opaqueMetricsRemainUnknown"] is True
        and opaque["processAcceptancePass"] is False,
        "Trace calibration treated an opaque material edge as zero loss",
    )
    decision = evaluated.get("decision")
    _require(
        isinstance(decision, dict)
        and decision.get("measurementCalibrationPassed") is True
        and decision.get("formalLiveCohortAuthorized") is False
        and decision.get("existingTransportSmokeCountsAsProcessTrace")
        is False,
        "Trace calibration decision boundary drifted",
    )
    return evaluated


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    root = args.root.resolve()
    contract = json.loads(
        (root / FIXTURE_PATH).read_text(encoding="utf-8")
    )
    report = validate_contract(contract)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
