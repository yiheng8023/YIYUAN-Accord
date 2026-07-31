#!/usr/bin/env python3
"""Validate the GEN-ORG-DECISION-01 zero-model protocol package."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    from evaluate_human_ai_collaboration_org_decision_zero_model_calibration import (
        evaluate_calibration,
    )
except ModuleNotFoundError:  # Imported as scripts.* from repository-root tests.
    from scripts.evaluate_human_ai_collaboration_org_decision_zero_model_calibration import (
        evaluate_calibration,
    )


ROOT = Path(__file__).resolve().parent.parent
PROTOCOL_PATH = ROOT / (
    "registry/human-ai-collaboration-org-decision-zero-model-protocol-2026-07-31.json"
)
FIXTURE_PATH = ROOT / (
    "tests/fixtures/human-ai-collaboration-org-decision-zero-model-calibration-2026-07-31.json"
)
DOCUMENT_PATH = ROOT / (
    "docs/strategy/HUMAN-AI-COLLABORATION-ORG-DECISION-ZERO-MODEL-CALIBRATION-2026-07-31.md"
)
PROGRAM_MAP_PATH = ROOT / "registry/program-acceptance-map.json"
PROGRAM_PLAN_PATH = ROOT / "registry/curation-program-plan.json"
EVIDENCE_ID = (
    "evidence.human-ai-collaboration-org-decision-zero-model-calibration-2026-07-31"
)
ACCEPTANCE_ID = "acceptance.end-to-end-process-fidelity"


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
    protocol = protocol or _load(
        root
        / "registry/human-ai-collaboration-org-decision-zero-model-protocol-2026-07-31.json"
    )
    fixture = fixture or _load(
        root
        / "tests/fixtures/human-ai-collaboration-org-decision-zero-model-calibration-2026-07-31.json"
    )
    program_map = program_map or _load(root / "registry/program-acceptance-map.json")
    program_plan = program_plan or _load(root / "registry/curation-program-plan.json")

    report = evaluate_calibration(protocol, fixture, root=root)
    _require(
        report.get("outcome") == "valid-zero-model-calibration"
        and report.get("status")
        == "zero-model-calibrated-no-live-agent-organization-or-participation"
        and report.get("caseCount") == 15
        and report.get("faultCaseCount") == 14
        and report.get("allCasesPassed") is True,
        "Organizational-decision calibration result drifted",
    )
    _require(
        report.get("formalLiveEvidenceEligible") is False
        and report.get("agentDispatchCount") == 0
        and report.get("modelCallCount") == 0
        and report.get("candidateExecutionCount") == 0,
        "Organizational-decision calibration crossed its execution boundary",
    )

    criteria = {
        item.get("id"): item for item in program_map.get("acceptanceCriteria", [])
    }
    _require(len(criteria) == 61, "Program acceptance count changed")
    _require(ACCEPTANCE_ID in criteria, "Process-fidelity acceptance is missing")
    _require(
        EVIDENCE_ID in criteria[ACCEPTANCE_ID].get("evidenceIds", []),
        "Organizational-decision evidence is not linked to process fidelity",
    )
    evidence = {item.get("id"): item for item in program_map.get("evidence", [])}
    _require(EVIDENCE_ID in evidence, "Organizational-decision evidence record is missing")
    _require(
        evidence[EVIDENCE_ID].get("path")
        == "registry/human-ai-collaboration-org-decision-zero-model-protocol-2026-07-31.json"
        and evidence[EVIDENCE_ID].get("supports") == [ACCEPTANCE_ID],
        "Organizational-decision evidence record drifted",
    )

    initiatives = {item.get("id"): item for item in program_plan.get("currentInitiatives", [])}
    coverage = initiatives.get("initiative.human-ai-collaboration-coverage-rebaseline")
    _require(coverage is not None, "Coverage initiative is missing")
    expected_path = (
        "registry/human-ai-collaboration-org-decision-zero-model-protocol-2026-07-31.json"
    )
    _require(
        coverage.get("currentOrgDecisionZeroModelProtocol") == expected_path,
        "Coverage initiative organizational-decision protocol pointer is missing",
    )

    document = (
        root
        / "docs/strategy/HUMAN-AI-COLLABORATION-ORG-DECISION-ZERO-MODEL-CALIBRATION-2026-07-31.md"
    ).read_text(encoding="utf-8")
    normalized = " ".join(document.split())
    for phrase in (
        "enough static candidate evidence to stop repeating ecosystem discovery",
        "facilitated human-only review",
        "low-power/high-impact riders",
        "Terminal recovery does not erase the historical loss ledger",
        "is not human review, affected-party participation, consultation, consent, consensus, or acceptance",
        "No current evidence makes self-authored work eligible",
    ):
        _require(phrase in normalized, f"Organizational-decision document missing: {phrase}")


def main() -> int:
    validate_protocol()
    print("Human-AI organizational-decision zero-model protocol validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
