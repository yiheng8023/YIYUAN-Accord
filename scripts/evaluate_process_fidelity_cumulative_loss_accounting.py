#!/usr/bin/env python3
"""Add parent-recomputed cumulative loss accounting to a valid trace.

This module is additive.  It deliberately leaves the frozen chained-transform
evaluator and trace schema unchanged so that their retained evidence hashes do
not drift.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

try:
    from .evaluate_process_fidelity_chained_transform_trace import (
        _load_documents,
        _metric,
        _read_indexed_artifacts,
        evaluate_capture,
    )
    from .run_process_fidelity_chained_transform_trial import (
        canonical_sha256,
        file_sha256,
    )
except ImportError:  # pragma: no cover - direct script execution
    from evaluate_process_fidelity_chained_transform_trace import (
        _load_documents,
        _metric,
        _read_indexed_artifacts,
        evaluate_capture,
    )
    from run_process_fidelity_chained_transform_trial import (
        canonical_sha256,
        file_sha256,
    )


ROOT = Path(__file__).resolve().parent.parent
ACCOUNTING_CONTRACT_PATH = (
    "registry/human-ai-collaboration-process-fidelity-cumulative-loss-"
    "accounting-contract-2026-07-27.json"
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _loss_weight(
    loss_id: str,
    *,
    invariant_weights: dict[str, int | float],
    assumption_weights: dict[str, int | float],
) -> int | float:
    _require(isinstance(loss_id, str) and ":" in loss_id, "Invalid loss id")
    kind, subject = loss_id.split(":", 1)
    _require(bool(subject), "Invalid loss id subject")
    if kind in {"invariant-omitted", "invariant-changed"}:
        _require(
            subject in invariant_weights,
            f"Unknown invariant loss id: {loss_id}",
        )
        return invariant_weights[subject]
    if kind == "assumption":
        return assumption_weights.get(subject, max(invariant_weights.values()))
    if kind == "value":
        return max(invariant_weights.values())
    if kind in {"provenance-missing", "provenance-fabricated"}:
        return 1
    raise RuntimeError(f"Unknown loss id type: {loss_id}")


def build_cumulative_loss_ledger(
    scored_stages: list[dict[str, Any]],
    protocol: dict[str, Any],
    *,
    cumulative_unique_loss_weight_max: int | float | None = None,
) -> dict[str, Any]:
    """Compute deduplicated loss history from ordered parent-scored stages."""

    _require(
        isinstance(scored_stages, list) and bool(scored_stages),
        "Scored stages must be a non-empty list",
    )
    oracle = protocol.get("oracle")
    _require(isinstance(oracle, dict), "Protocol oracle is missing")
    invariants = oracle.get("invariants")
    assumptions = oracle.get("unauthorizedAssumptions")
    _require(
        isinstance(invariants, list) and bool(invariants),
        "Protocol invariants are missing",
    )
    _require(
        isinstance(assumptions, list),
        "Protocol assumption weights are missing",
    )
    invariant_weights = {
        item["id"]: item["weight"] for item in invariants
    }
    assumption_weights = {
        item["id"]: item["weight"] for item in assumptions
    }
    _require(
        all(
            isinstance(key, str)
            and key
            and isinstance(value, (int, float))
            and not isinstance(value, bool)
            and value >= 0
            for key, value in invariant_weights.items()
        ),
        "Invariant weights are invalid",
    )
    _require(
        all(
            isinstance(key, str)
            and key
            and isinstance(value, (int, float))
            and not isinstance(value, bool)
            and value >= 0
            for key, value in assumption_weights.items()
        ),
        "Assumption weights are invalid",
    )
    if cumulative_unique_loss_weight_max is not None:
        _require(
            isinstance(cumulative_unique_loss_weight_max, (int, float))
            and not isinstance(cumulative_unique_loss_weight_max, bool)
            and cumulative_unique_loss_weight_max >= 0,
            "Cumulative loss budget must be a non-negative number",
        )

    previous: set[str] = set()
    seen: set[str] = set()
    stage_ids: set[str] = set()
    peak_active_weight: int | float = 0
    budget_exceeded_at: str | None = None
    hops: list[dict[str, Any]] = []
    weights: dict[str, int | float] = {}

    for stage in scored_stages:
        _require(isinstance(stage, dict), "Scored stage must be an object")
        stage_id = stage.get("stageId")
        active_values = stage.get("activeLossIds")
        weighted_delta = stage.get("weightedDelta")
        _require(
            isinstance(stage_id, str)
            and stage_id
            and stage_id not in stage_ids,
            "Scored stage id is missing or duplicated",
        )
        _require(
            isinstance(active_values, list)
            and all(
                isinstance(item, str) and item for item in active_values
            )
            and len(active_values) == len(set(active_values)),
            f"Active loss ids are invalid at {stage_id}",
        )
        _require(
            isinstance(weighted_delta, (int, float))
            and not isinstance(weighted_delta, bool)
            and weighted_delta >= 0,
            f"Weighted delta is invalid at {stage_id}",
        )
        stage_ids.add(stage_id)
        current = set(active_values)
        for loss_id in current:
            weights.setdefault(
                loss_id,
                _loss_weight(
                    loss_id,
                    invariant_weights=invariant_weights,
                    assumption_weights=assumption_weights,
                ),
            )

        active_weight = sum(weights[item] for item in current)
        _require(
            active_weight == weighted_delta,
            f"Parent metric weight mismatch at {stage_id}",
        )
        new = current - previous
        carried = current & previous
        recovered = previous - current
        first_seen = current - seen
        reintroduced = new & seen
        for loss_id in recovered:
            weights.setdefault(
                loss_id,
                _loss_weight(
                    loss_id,
                    invariant_weights=invariant_weights,
                    assumption_weights=assumption_weights,
                ),
            )
        seen |= current
        cumulative_unique_weight = sum(weights[item] for item in seen)
        peak_active_weight = max(peak_active_weight, active_weight)
        if (
            cumulative_unique_loss_weight_max is not None
            and budget_exceeded_at is None
            and cumulative_unique_weight
            > cumulative_unique_loss_weight_max
        ):
            budget_exceeded_at = stage_id

        hops.append(
            {
                "stageId": stage_id,
                "activeLossIds": sorted(current),
                "newLossIds": sorted(new),
                "carriedLossIds": sorted(carried),
                "recoveredLossIds": sorted(recovered),
                "firstSeenLossIds": sorted(first_seen),
                "reintroducedLossIds": sorted(reintroduced),
                "activeLossWeight": active_weight,
                "newLossWeight": sum(weights[item] for item in new),
                "carriedLossWeight": sum(
                    weights[item] for item in carried
                ),
                "recoveredLossWeight": sum(
                    weights[item] for item in recovered
                ),
                "cumulativeUniqueLossIds": sorted(seen),
                "cumulativeUniqueLossWeight": cumulative_unique_weight,
            }
        )
        previous = current

    return {
        "accountingMode": "parent-recomputed-deduplicated-active-loss-set",
        "budgetEvaluated": cumulative_unique_loss_weight_max is not None,
        "budgetMaximum": cumulative_unique_loss_weight_max,
        "budgetExceededAtHop": budget_exceeded_at,
        "peakActiveLossWeight": peak_active_weight,
        "cumulativeUniqueLossIds": sorted(seen),
        "cumulativeUniqueLossWeight": sum(weights[item] for item in seen),
        "terminalRecoveryDoesNotEraseHistoricalUniqueLoss": True,
        "changesProcessAcceptancePass": False,
        "hops": hops,
    }


def _load_accounting_contract(root: Path) -> tuple[dict[str, Any], str]:
    path = root / ACCOUNTING_CONTRACT_PATH
    document = json.loads(path.read_text(encoding="utf-8"))
    return document, file_sha256(path)


def evaluate_capture_with_cumulative_loss(
    capture: dict[str, Any],
    *,
    capture_root: Path,
    root: Path = ROOT,
) -> dict[str, Any]:
    """Evaluate a capture, then add an advisory cumulative ledger if valid."""

    root = root.resolve()
    capture_root = capture_root.resolve()
    base_report = evaluate_capture(
        capture,
        capture_root=capture_root,
        root=root,
    )
    report = copy.deepcopy(base_report)
    trace = report.get("candidateTrace")
    if not isinstance(trace, dict):
        return report

    protocol, _amendment, _hashes = _load_documents(root)
    artifacts, failures = _read_indexed_artifacts(
        capture,
        capture_root=capture_root,
    )
    _require(not failures, "Validated capture artifacts could not be reopened")
    cell = capture["cell"]
    run_id = cell["runId"]
    scored_stage_specs = [
        ("hop-1-decomposition", f"{run_id}-O1"),
        ("edge-controlled-mutation", f"{run_id}-M1"),
        ("hop-2-routing", f"{run_id}-O2"),
        ("hop-3-acceptance-and-recovery", f"{run_id}-O3"),
    ]
    accounting_contract, contract_hash = _load_accounting_contract(root)
    expected_order = accounting_contract["scoredStagePolicy"][
        "includedStageIdsInOrder"
    ]
    _require(
        [item[0] for item in scored_stage_specs] == expected_order,
        "Accounting scored-stage order drifted",
    )
    scored_stages = [
        _metric(artifacts[artifact_id], protocol, stage_id=stage_id)
        for stage_id, artifact_id in scored_stage_specs
    ]
    budget_policy = accounting_contract["budgetPolicy"]
    budget = budget_policy["cumulativeUniqueLossWeightMaxByArm"][
        cell["armId"]
    ]
    ledger = build_cumulative_loss_ledger(
        scored_stages,
        protocol,
        cumulative_unique_loss_weight_max=budget,
    )
    ledger["accountingContract"] = {
        "path": ACCOUNTING_CONTRACT_PATH,
        "fileSha256": contract_hash,
    }
    ledger["inputStageMetricsCanonicalSha256"] = canonical_sha256(
        scored_stages
    )
    ledger["advisoryOnly"] = (
        budget_policy["enforcement"]
        == "advisory-only-does-not-change-process-acceptance"
    )
    process_ledger = trace.get("processLedger")
    _require(isinstance(process_ledger, dict), "Process ledger is missing")
    original_process_pass = process_ledger.get("processAcceptancePass")
    process_ledger["cumulativeLoss"] = ledger
    _require(
        process_ledger.get("processAcceptancePass") is original_process_pass,
        "Cumulative accounting changed process acceptance",
    )
    return report

