#!/usr/bin/env python3
"""Validate the product-discovery zero-model effect protocol."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    from .evaluate_skill_portfolio_product_discovery_zero_model_calibration import (
        REQUIRED_FAULT_CLASSES,
        ROOT,
        evaluate_repository_calibration,
    )
except ImportError:  # pragma: no cover - direct script execution
    from evaluate_skill_portfolio_product_discovery_zero_model_calibration import (
        REQUIRED_FAULT_CLASSES,
        ROOT,
        evaluate_repository_calibration,
    )


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def validate_protocol(root: Path = ROOT) -> dict[str, Any]:
    report = evaluate_repository_calibration(root)
    _require(
        report.get("outcome") == "valid-zero-model-effect-calibration"
        and report.get("status")
        == "product-discovery-effect-oracle-calibrated-no-candidate-behavior",
        "Product-discovery evaluator outcome drifted",
    )
    _require(
        report.get("candidateCount") == 2
        and report.get("scenarioCount") == 1
        and report.get("caseCount") == 6
        and report.get("faultCaseCount") == 5
        and report.get("faultClassesCovered") == sorted(REQUIRED_FAULT_CLASSES)
        and report.get("allCasesPassed") is True,
        "Product-discovery calibration coverage drifted",
    )
    _require(
        report.get("parentRequirementsFixtureReused") is True
        and report.get("fullScenarioFixtureCreated") is False
        and report.get("historicalComparisonPromotedToCurrentCandidateProof") is False,
        "Product-discovery reuse boundary drifted",
    )
    _require(
        report.get("formalLiveEvidenceEligible") is False
        and report.get("agentDispatchCount") == 0
        and report.get("modelCallCount") == 0
        and report.get("candidateExecutionCount") == 0,
        "Product-discovery execution boundary drifted",
    )
    claim = report.get("claimBoundary")
    _require(
        isinstance(claim, dict) and claim and all(value is False for value in claim.values()),
        "Product-discovery claim boundary drifted",
    )
    return report


def main() -> int:
    report = validate_protocol(ROOT)
    print(
        json.dumps(
            {
                "status": "ok",
                "protocolStatus": report["status"],
                "candidateCount": report["candidateCount"],
                "caseCount": report["caseCount"],
                "modelCallCount": report["modelCallCount"],
                "candidateExecutionCount": report["candidateExecutionCount"],
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
