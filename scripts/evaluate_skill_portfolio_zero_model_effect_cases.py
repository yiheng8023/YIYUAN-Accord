#!/usr/bin/env python3
"""Shared case runner for source-free Skill portfolio effect calibrations."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Callable

try:
    from .evaluate_process_fidelity_cumulative_loss_accounting import (
        build_cumulative_loss_ledger,
    )
except ImportError:  # pragma: no cover - direct script execution
    from evaluate_process_fidelity_cumulative_loss_accounting import (
        build_cumulative_loss_ledger,
    )


PacketScorer = Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def load_json_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"Expected JSON object: {path}")
    return value


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def validate_file_binding(binding: dict[str, Any], *, root: Path) -> None:
    path = root / binding["path"]
    require(path.is_file(), f"Bound source is missing: {binding['path']}")
    require(path.stat().st_size == binding["bytes"], "Bound source byte count drifted")
    require(file_sha256(path) == binding["sha256"], "Bound source digest drifted")


def apply_overrides(
    canonical: dict[str, Any],
    overrides: dict[str, Any],
) -> dict[str, Any]:
    require(set(overrides).issubset(canonical), "Fault mutation shape drifted")
    packet = copy.deepcopy(canonical)
    for key, value in overrides.items():
        packet[key] = copy.deepcopy(value)
    return packet


def evaluate_case_matrix(
    *,
    protocol: dict[str, Any],
    fixture: dict[str, Any],
    root: Path,
    repository_fixture_path: str,
    canonical_packet_key: str,
    expected_override_by_fault: dict[str, dict[str, Any]],
    required_fault_classes: set[str],
    score_packet: PacketScorer,
    active_stage_id: str,
    review_stage_id: str,
    recovery_stage_id: str,
    source_stage_id: str,
) -> dict[str, Any]:
    """Recompute one-control/single-fault cases through a shared loss ledger."""

    canonical = fixture.get(canonical_packet_key)
    require(isinstance(canonical, dict), "Canonical effect packet is missing")
    require(
        score_packet(canonical, canonical)
        == {"activeLossIds": [], "weightedDelta": 0},
        "Canonical effect packet is not lossless",
    )
    cases = fixture.get("cases")
    acceptance = protocol.get("acceptance")
    require(isinstance(cases, list), "Fixture cases are missing")
    require(isinstance(acceptance, dict), "Protocol acceptance is missing")
    require(len(cases) == acceptance.get("expectedCaseCount"), "Fixture case count drifted")

    results: list[dict[str, Any]] = []
    case_ids: set[str] = set()
    fault_classes: list[str] = []
    for case in cases:
        require(isinstance(case, dict), "Fixture case must be an object")
        case_id = case.get("id")
        fault_class = case.get("faultClass")
        require(
            isinstance(case_id, str) and case_id and case_id not in case_ids,
            "Fixture case identities drifted",
        )
        require(
            fault_class in expected_override_by_fault,
            "Fixture fault class is unknown",
        )
        case_ids.add(case_id)
        fault_classes.append(fault_class)
        overrides = case.get("overrides")
        require(
            overrides == expected_override_by_fault[fault_class],
            "Fault mutation shape drifted",
        )
        score = score_packet(apply_overrides(canonical, overrides), canonical)
        expected_active = sorted(case.get("expectedActiveLossIds", []))
        expected_unique = sorted(case.get("expectedCumulativeUniqueLossIds", []))
        require(score["activeLossIds"] == expected_active, "Expected active loss set drifted")
        stages = [
            {"stageId": source_stage_id, "activeLossIds": [], "weightedDelta": 0},
            {"stageId": active_stage_id, **score},
            {"stageId": review_stage_id, **score},
            {"stageId": recovery_stage_id, "activeLossIds": [], "weightedDelta": 0},
        ]
        ledger = build_cumulative_loss_ledger(
            stages,
            protocol,
            cumulative_unique_loss_weight_max=protocol["oracle"]["faultBudgetMaximum"],
        )
        require(
            ledger["cumulativeUniqueLossIds"] == expected_unique,
            "Expected cumulative unique loss set drifted",
        )
        if fault_class == "control":
            require(ledger["budgetExceededAtHop"] is None, "Control breached the loss budget")
        else:
            require(
                ledger["budgetExceededAtHop"] == active_stage_id,
                f"Fault did not breach at {active_stage_id}",
            )
        require(
            ledger["hops"][-1]["activeLossIds"] == []
            and ledger["terminalRecoveryDoesNotEraseHistoricalUniqueLoss"] is True,
            "Terminal recovery semantics drifted",
        )
        results.append(
            {
                "id": case_id,
                "faultClass": fault_class,
                "activeLossIds": score["activeLossIds"],
                "stages": stages,
                "cumulativeLoss": ledger,
            }
        )

    require(fault_classes.count("control") == 1, "Exactly one control is required")
    observed_faults = {value for value in fault_classes if value != "control"}
    require(
        observed_faults == required_fault_classes
        and len(fault_classes) - 1 == len(required_fault_classes),
        "Fixture fault-class coverage drifted",
    )
    require(
        len(results) - 1 == acceptance.get("expectedFaultCaseCount"),
        "Fixture fault case count drifted",
    )
    repository_fixture = load_json_object(root / repository_fixture_path)
    require(
        canonical_sha256(fixture) == canonical_sha256(repository_fixture),
        "Passed fixture must equal the hash-bound repository object",
    )
    return {
        "results": results,
        "observedFaultClasses": observed_faults,
    }
