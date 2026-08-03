#!/usr/bin/env python3
"""Validate the decision-challenge zero-model incremental effect protocol."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    from .evaluate_skill_portfolio_decision_challenge_zero_model_calibration import (
        REQUIRED_FAULT_CLASSES,
        ROOT,
        evaluate_repository_calibration,
    )
except ImportError:  # pragma: no cover - direct script execution
    from evaluate_skill_portfolio_decision_challenge_zero_model_calibration import (
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
        report.get("outcome") == "valid-zero-model-effect-calibration",
        "Decision-challenge evaluator outcome drifted",
    )
    _require(
        report.get("status")
        == "decision-challenge-effect-oracle-calibrated-no-candidate-behavior",
        "Decision-challenge evaluator status drifted",
    )
    _require(
        report.get("caseCount") == 7
        and report.get("faultCaseCount") == 6
        and report.get("faultClassesCovered") == sorted(REQUIRED_FAULT_CLASSES)
        and report.get("allCasesPassed") is True,
        "Decision-challenge calibration coverage drifted",
    )
    _require(
        report.get("parentOrgDecisionProtocolReused") is True
        and report.get("newFullScenarioFixtureCreated") is False,
        "Decision-challenge parent reuse boundary drifted",
    )
    _require(
        report.get("formalLiveEvidenceEligible") is False
        and report.get("agentDispatchCount") == 0
        and report.get("modelCallCount") == 0
        and report.get("candidateExecutionCount") == 0,
        "Decision-challenge execution boundary drifted",
    )
    claim = report.get("claimBoundary")
    _require(
        isinstance(claim, dict)
        and claim
        and all(value is False for value in claim.values()),
        "Decision-challenge claim boundary drifted",
    )
    return report


def main() -> int:
    report = validate_protocol(ROOT)
    print(
        json.dumps(
            {
                "status": "ok",
                "protocolStatus": report["status"],
                "caseCount": report["caseCount"],
                "faultCaseCount": report["faultCaseCount"],
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
