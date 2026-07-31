#!/usr/bin/env python3
"""Validate the SE-MGMT-PRACTICE-01 zero-model protocol package."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    from evaluate_human_ai_collaboration_engineering_management_zero_model_calibration import (
        evaluate_calibration,
    )
except ModuleNotFoundError:  # Imported as scripts.* from repository-root tests.
    from scripts.evaluate_human_ai_collaboration_engineering_management_zero_model_calibration import (
        evaluate_calibration,
    )


ROOT = Path(__file__).resolve().parent.parent
PROTOCOL_RELATIVE_PATH = (
    "registry/human-ai-collaboration-engineering-management-zero-model-"
    "protocol-2026-07-31.json"
)
FIXTURE_RELATIVE_PATH = (
    "tests/fixtures/human-ai-collaboration-engineering-management-zero-model-"
    "calibration-2026-07-31.json"
)
DOCUMENT_RELATIVE_PATH = (
    "docs/strategy/HUMAN-AI-COLLABORATION-ENGINEERING-MANAGEMENT-ZERO-MODEL-"
    "CALIBRATION-2026-07-31.md"
)
EVIDENCE_ID = (
    "evidence.human-ai-collaboration-engineering-management-zero-model-"
    "calibration-2026-07-31"
)
ACCEPTANCE_IDS = [
    "acceptance.software-engineering-lifecycle-specialization",
    "acceptance.end-to-end-process-fidelity",
]


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_protocol(
    protocol: dict[str, Any] | None = None,
    *,
    root: Path = ROOT,
    fixture: dict[str, Any] | None = None,
    program_map: dict[str, Any] | None = None,
    program_plan: dict[str, Any] | None = None,
) -> None:
    protocol = protocol or _load(root / PROTOCOL_RELATIVE_PATH)
    fixture = fixture or _load(root / FIXTURE_RELATIVE_PATH)
    program_map = program_map or _load(root / "registry/program-acceptance-map.json")
    program_plan = program_plan or _load(root / "registry/curation-program-plan.json")

    report = evaluate_calibration(protocol, fixture, root=root)
    _require(
        report.get("outcome") == "valid-zero-model-calibration"
        and report.get("status")
        == "zero-model-calibrated-no-live-agent-team-management-or-outcome-evidence"
        and report.get("caseCount") == 18
        and report.get("faultCaseCount") == 17
        and report.get("allCasesPassed") is True
        and report.get("forecastCalibration")
        == {
            "sampleCount": 4,
            "intervalHitCount": 3,
            "absoluteMidpointErrorDoubleSum": 13,
        },
        "Engineering-management calibration result drifted",
    )
    _require(
        report.get("formalLiveEvidenceEligible") is False
        and report.get("agentDispatchCount") == 0
        and report.get("modelCallCount") == 0
        and report.get("candidateExecutionCount") == 0,
        "Engineering-management calibration crossed its execution boundary",
    )

    criteria = {
        item.get("id"): item for item in program_map.get("acceptanceCriteria", [])
    }
    _require(len(criteria) == 61, "Program acceptance count changed")
    for acceptance_id in ACCEPTANCE_IDS:
        _require(acceptance_id in criteria, f"Acceptance is missing: {acceptance_id}")
        _require(
            EVIDENCE_ID in criteria[acceptance_id].get("evidenceIds", []),
            f"Engineering-management evidence is not linked: {acceptance_id}",
        )
    evidence = {item.get("id"): item for item in program_map.get("evidence", [])}
    _require(EVIDENCE_ID in evidence, "Engineering-management evidence is missing")
    _require(
        evidence[EVIDENCE_ID].get("path") == PROTOCOL_RELATIVE_PATH
        and evidence[EVIDENCE_ID].get("supports") == ACCEPTANCE_IDS,
        "Engineering-management evidence record drifted",
    )

    initiatives = {
        item.get("id"): item
        for item in program_plan.get("currentInitiatives", [])
    }
    coverage = initiatives.get("initiative.human-ai-collaboration-coverage-rebaseline")
    _require(coverage is not None, "Coverage initiative is missing")
    _require(
        coverage.get("currentEngineeringManagementZeroModelProtocol")
        == PROTOCOL_RELATIVE_PATH
        and coverage.get("currentEngineeringManagementZeroModelProtocolState")
        == (
            "parent-recomputed-forecast-outcome-and-management-boundary-"
            "calibration-passed-no-live-team-candidate-or-outcome-evidence"
        ),
        "Coverage initiative engineering-management pointer drifted",
    )

    document = (root / DOCUMENT_RELATIVE_PATH).read_text(encoding="utf-8")
    normalized = " ".join(document.split())
    for phrase in (
        "does not need another broad candidate search",
        "The project remains neutral",
        "Current `wayfinder` is a real shared-pool near match, not garbage",
        "organizational-decision calibration therefore is necessary but not sufficient",
        "parent evaluator recomputes a sample count of `4`",
        "Terminal recovery does not erase historical cumulative loss",
        "is not team participation, worker review, management acceptance, professional sign-off, or human-only evidence",
        "No current evidence makes self-authored work or hard-standard promotion eligible",
    ):
        _require(phrase in normalized, f"Engineering-management document missing: {phrase}")


def main() -> int:
    validate_protocol()
    print("Human-AI engineering-management zero-model protocol validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
