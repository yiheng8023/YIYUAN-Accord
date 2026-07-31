#!/usr/bin/env python3
"""Evaluate zero-model learning-protocol mechanism fixtures."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


EXPECTED_PROTOCOL_ID = (
    "human-ai-collaboration-learning-fixed-fixture-protocol-2026-07-31"
)
EXPECTED_SCENARIO_ID = "GEN-LEARNING-01"
EXPECTED_ARMS = {
    "arm.native-codex-spark-low",
    "arm.matt-teach-codex-spark-low",
    "arm.one-explicit-official-host-mode",
    "arm.human-instructor-control",
}
EXPECTED_MODEL = "gpt-5.3-codex-spark"
EXPECTED_REASONING = "low"
REQUIRED_MEASUREMENTS = {
    "immediateIndependentAssessment",
    "delayedUnaidedAssessment",
    "novelTransferTask",
    "misconceptionOracle",
    "teacherReview",
    "learnerAutonomyObservation",
    "accessibilityObservation",
}
REQUIRED_AUTHORITIES = {
    "modelDispatchAuthorized",
    "candidateExecutionAuthorized",
    "officialAccountAccessAuthorized",
    "humanParticipantTrialAuthorized",
}


def _result(decision: str, *failure_codes: str) -> dict[str, Any]:
    return {"decision": decision, "failureCodes": list(failure_codes)}


def evaluate_record(record: dict[str, Any]) -> dict[str, Any]:
    if record.get("protocolId") != EXPECTED_PROTOCOL_ID:
        return _result("invalid", "protocol-identity-mismatch")
    if record.get("scenarioId") != EXPECTED_SCENARIO_ID:
        return _result("invalid", "scenario-identity-mismatch")
    if set(record.get("armIds", [])) != EXPECTED_ARMS:
        return _result("invalid", "representative-arm-set-drift")
    if record.get("officialProductsMergedIntoOneArm") is not False:
        return _result("invalid", "official-products-merged")
    if record.get("privateOracleExposed") is not False:
        return _result("invalid", "private-oracle-exposed")
    if record.get("humanOnlyControlPresent") is not True:
        return _result("invalid", "human-only-control-missing")

    claim = record.get("claim", {})
    if claim.get("immediateCompletionUsedAsLearningProof") is not False:
        return _result("invalid", "immediate-completion-promoted-to-learning")

    phase = record.get("phase")
    authority = record.get("authorityEvidence", {})
    counts = record.get("executionCounts", {})
    if phase == "mechanism-simulation":
        if any(authority.get(key) is not False for key in REQUIRED_AUTHORITIES):
            return _result("invalid", "simulation-authority-must-remain-false")
        if any(counts.get(key) != 0 for key in (
            "modelDispatchCount",
            "candidateExecutionCount",
            "officialAccountAccessCount",
            "humanParticipantCount",
        )):
            return _result("invalid", "simulation-executed-live-surface")
        if claim.get("kind") != "mechanism-only":
            return _result("invalid", "simulation-learning-claim")
        return _result("valid-mechanism-simulation-no-learning-claim")

    if phase != "formal-human-learning-trial":
        return _result("invalid", "unknown-phase")

    missing_authority = sorted(
        key for key in REQUIRED_AUTHORITIES if authority.get(key) is not True
    )
    if missing_authority:
        return _result(
            "blocked-formal-trial-missing-authority",
            *[f"missing-authority:{key}" for key in missing_authority],
        )

    route = record.get("weakAgentRoute", {})
    if route.get("routeVisible") is not True:
        return _result("invalid", "weak-agent-route-not-visible")
    if (
        route.get("expectedModel") != EXPECTED_MODEL
        or route.get("actualModel") != EXPECTED_MODEL
        or route.get("expectedReasoningEffort") != EXPECTED_REASONING
        or route.get("actualReasoningEffort") != EXPECTED_REASONING
    ):
        return _result("invalid", "weak-agent-route-substituted")

    matt = record.get("mattTeachExposure", {})
    if matt.get("selected") is not True:
        return _result("invalid", "matt-teach-arm-not-selected")
    if (
        matt.get("installedOrProjectedOnly") is not False
        or matt.get("instructionDeliveryProved") is not True
    ):
        return _result("invalid", "matt-teach-delivery-unproved")

    cleanup = record.get("cleanup", {})
    if cleanup.get("required") is True and cleanup.get("complete") is not True:
        return _result("invalid", "treatment-workspace-cleanup-incomplete")

    measurements = record.get("measurements", {})
    missing_measurements = sorted(
        key for key in REQUIRED_MEASUREMENTS if measurements.get(key) is not True
    )
    if missing_measurements:
        return _result(
            "incomplete-formal-trial-measurement",
            *[f"missing-measurement:{key}" for key in missing_measurements],
        )

    if claim.get("kind") != "analysis-eligibility-only":
        return _result("invalid", "formal-trial-effect-claim-premature")
    return _result("eligible-for-analysis-no-effect-claim")


def evaluate_fixture_document(document: dict[str, Any]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for fixture in document.get("fixtures", []):
        actual = evaluate_record(fixture.get("record", {}))
        results.append({"id": fixture.get("id"), "actual": actual})
    return results


def main() -> int:
    fixture_path = (
        Path(__file__).resolve().parent.parent
        / "tests/fixtures/human-ai-collaboration-learning-protocol-fixtures-2026-07-31.json"
    )
    document = json.loads(fixture_path.read_text(encoding="utf-8"))
    failures = []
    for fixture, result in zip(document.get("fixtures", []), evaluate_fixture_document(document)):
        if result["actual"] != fixture.get("expected"):
            failures.append({"id": fixture.get("id"), "actual": result["actual"]})
    if failures:
        raise RuntimeError(f"Learning protocol fixtures failed: {failures}")
    print("Human-AI learning protocol mechanism fixtures passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
