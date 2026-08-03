#!/usr/bin/env python3
"""Validate the marketing-writing zero-model effect protocol."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    from .evaluate_skill_portfolio_marketing_writing_zero_model_calibration import (
        REQUIRED_FAULT_CLASSES,
        ROOT,
        evaluate_repository_calibration,
    )
except ImportError:  # pragma: no cover - direct script execution
    from evaluate_skill_portfolio_marketing_writing_zero_model_calibration import (
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
        == "marketing-writing-effect-oracle-calibrated-no-candidate-behavior",
        "Marketing-writing evaluator outcome drifted",
    )
    _require(
        report.get("candidateCount") == 2
        and report.get("scenarioCount") == 2
        and report.get("caseCount") == 6
        and report.get("faultCaseCount") == 5
        and report.get("faultClassesCovered") == sorted(REQUIRED_FAULT_CLASSES)
        and report.get("allCasesPassed") is True,
        "Marketing-writing calibration coverage drifted",
    )
    _require(
        report.get("creativePreferencePacketReused") is True
        and report.get("accessCommsBoundaryReused") is True
        and report.get("heuristicPanelTreatedAsIndependentEvidence") is False
        and report.get("fullScenarioFixtureCreated") is False,
        "Marketing-writing evidence reuse boundary drifted",
    )
    _require(
        report.get("formalLiveEvidenceEligible") is False
        and report.get("agentDispatchCount") == 0
        and report.get("modelCallCount") == 0
        and report.get("candidateExecutionCount") == 0,
        "Marketing-writing execution boundary drifted",
    )
    claim = report.get("claimBoundary")
    _require(
        isinstance(claim, dict) and claim and all(value is False for value in claim.values()),
        "Marketing-writing claim boundary drifted",
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
                "scenarioCount": report["scenarioCount"],
                "caseCount": report["caseCount"],
                "modelCallCount": report["modelCallCount"],
                "candidateExecutionCount": report["candidateExecutionCount"],
                "formalLiveEvidenceEligible": report["formalLiveEvidenceEligible"],
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
