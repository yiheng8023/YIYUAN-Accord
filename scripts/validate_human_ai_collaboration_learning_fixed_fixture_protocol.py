#!/usr/bin/env python3
"""Validate the GEN-LEARNING-01 fixed-fixture protocol and simulation."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

try:
    from .evaluate_human_ai_collaboration_learning_protocol import (
        EXPECTED_ARMS,
        EXPECTED_MODEL,
        EXPECTED_PROTOCOL_ID,
        EXPECTED_REASONING,
        evaluate_fixture_document,
    )
except ImportError:  # Direct execution keeps the scripts directory on sys.path.
    from evaluate_human_ai_collaboration_learning_protocol import (
        EXPECTED_ARMS,
        EXPECTED_MODEL,
        EXPECTED_PROTOCOL_ID,
        EXPECTED_REASONING,
        evaluate_fixture_document,
    )


ROOT = Path(__file__).resolve().parent.parent
PROTOCOL_PATH = (
    ROOT / "registry/human-ai-collaboration-learning-fixed-fixture-protocol-2026-07-31.json"
)
FIXTURE_PATH = (
    ROOT / "tests/fixtures/human-ai-collaboration-learning-protocol-fixtures-2026-07-31.json"
)
PROGRAM_PLAN_PATH = ROOT / "registry/curation-program-plan.json"
EXPECTED_PHASES = [
    "phase.zero-model-mechanism-simulation",
    "phase.no-model-material-and-oracle-calibration",
    "phase.authorized-mechanism-pilot",
    "phase.preregistered-human-learning-trial",
]
EXPECTED_MEASUREMENT_KEYS = {
    "pretest",
    "immediateIndependentAssessment",
    "delayedUnaidedAssessment",
    "novelTransferTask",
    "misconceptionOracle",
    "learnerAutonomy",
    "accessibility",
    "teacherReview",
    "lifecycleCost",
    "nonCancellation",
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_protocol(
    protocol: dict[str, Any] | None = None,
    *,
    root: Path = ROOT,
    fixtures: dict[str, Any] | None = None,
    program_plan: dict[str, Any] | None = None,
) -> None:
    protocol = protocol or _load(
        root
        / "registry/human-ai-collaboration-learning-fixed-fixture-protocol-2026-07-31.json"
    )
    fixtures = fixtures or _load(
        root
        / "tests/fixtures/human-ai-collaboration-learning-protocol-fixtures-2026-07-31.json"
    )
    program_plan = program_plan or _load(root / "registry/curation-program-plan.json")

    _require(protocol.get("schema") == 1, "Learning protocol schema drifted")
    _require(protocol.get("id") == EXPECTED_PROTOCOL_ID, "Learning protocol identity drifted")
    _require(
        protocol.get("status")
        == "validated-zero-model-mechanism-protocol-no-live-human-model-candidate-or-account-trial",
        "Learning protocol status drifted",
    )
    scenario = protocol.get("scenarioBinding", {})
    _require(scenario.get("scenarioId") == "GEN-LEARNING-01", "Learning scenario drifted")
    _require(
        scenario.get("evidenceStateMustRemain") == "planned-no-live-domain-evidence",
        "Learning protocol promoted scenario evidence",
    )

    for source in protocol.get("sourceBindings", []):
        path = root / str(source.get("path", ""))
        _require(path.is_file(), f"Learning protocol source is missing: {source.get('path')}")
        _require(path.stat().st_size == source.get("bytes"), f"Learning protocol source size drifted: {source.get('path')}")
        _require(_sha256(path) == source.get("sha256"), f"Learning protocol source hash drifted: {source.get('path')}")

    phases = protocol.get("phaseOrder", [])
    _require([item.get("id") for item in phases] == EXPECTED_PHASES, "Learning phase order drifted")
    _require(
        [item.get("id") for item in phases if item.get("current") is True]
        == ["phase.zero-model-mechanism-simulation"],
        "Learning current phase drifted",
    )

    arms = {item.get("id"): item for item in protocol.get("arms", [])}
    _require(set(arms) == EXPECTED_ARMS, "Learning protocol arm set drifted")
    for arm_id in (
        "arm.native-codex-spark-low",
        "arm.matt-teach-codex-spark-low",
    ):
        _require(arms[arm_id].get("model") == EXPECTED_MODEL, f"Weak model drifted: {arm_id}")
        _require(arms[arm_id].get("reasoningEffort") == EXPECTED_REASONING, f"Weak reasoning drifted: {arm_id}")
        _require(arms[arm_id].get("routeMustBeVisible") is True, f"Weak route visibility drifted: {arm_id}")
    official = arms["arm.one-explicit-official-host-mode"]
    _require(official.get("selectionCountMustEqual") == 1, "Official-host selection boundary drifted")
    _require(len(official.get("selectionOptions", [])) == 3, "Official-host option set drifted")

    fixture_design = protocol.get("fixtureDesign", {})
    _require("between-subject" in fixture_design.get("contaminationBoundary", ""), "Between-subject contamination control is missing")
    _require("seven days" in fixture_design.get("delayedWindow", ""), "Delayed window drifted")
    _require("power analysis" in fixture_design.get("sampleSizeBoundary", ""), "Power-analysis boundary is missing")
    _require(
        set(protocol.get("measurementContract", {})) == EXPECTED_MEASUREMENT_KEYS,
        "Learning measurement contract drifted",
    )

    cleanup = protocol.get("cleanupContract", {})
    _require(
        cleanup
        and all(value is True for value in cleanup.values()),
        "Learning cleanup contract weakened",
    )
    simulation = protocol.get("zeroModelSimulation", {})
    _require(simulation.get("fixtureCount") == 10, "Learning fixture count drifted")
    for key in (
        "modelDispatchCount",
        "candidateExecutionCount",
        "officialAccountAccessCount",
        "humanParticipantCount",
    ):
        _require(simulation.get(key) == 0, f"Zero-model simulation executed a live surface: {key}")
    _require(
        simulation.get("formalRecordCeiling") == "eligible-for-analysis-no-effect-claim",
        "Formal-record claim ceiling drifted",
    )

    _require(fixtures.get("protocolId") == EXPECTED_PROTOCOL_ID, "Fixture protocol binding drifted")
    fixture_items = fixtures.get("fixtures", [])
    _require(len(fixture_items) == 10, "Fixture document count drifted")
    results = evaluate_fixture_document(fixtures)
    for fixture, result in zip(fixture_items, results):
        _require(
            result.get("actual") == fixture.get("expected"),
            f"Learning mechanism fixture drifted: {fixture.get('id')}",
        )

    claims = protocol.get("claimBoundary", {})
    _require(claims.get("simulationProvesProtocolMechanismOnly") is True, "Simulation claim boundary drifted")
    for key, value in claims.items():
        if key != "simulationProvesProtocolMechanismOnly":
            _require(value is False, f"Learning protocol promoted claim: {key}")
    authority = protocol.get("authorityBoundary", {})
    _require(authority.get("repositoryProtocolAndFixtureWritesAuthorized") is True, "Repository write boundary drifted")
    for key, value in authority.items():
        if key != "repositoryProtocolAndFixtureWritesAuthorized":
            _require(value is False, f"Learning protocol expanded authority: {key}")

    initiatives = {item.get("id"): item for item in program_plan.get("currentInitiatives", [])}
    survey = initiatives.get("initiative.capability-survey-gap-proof")
    coverage = initiatives.get("initiative.human-ai-collaboration-coverage-rebaseline")
    expected_path = "registry/human-ai-collaboration-learning-fixed-fixture-protocol-2026-07-31.json"
    _require(
        survey is not None and survey.get("currentLearningFixedFixtureProtocol") == expected_path,
        "Capability-survey learning protocol pointer is missing",
    )
    _require(
        coverage is not None and coverage.get("currentLearningFixedFixtureProtocol") == expected_path,
        "Coverage-rebaseline learning protocol pointer is missing",
    )

    document = (
        root
        / "docs/strategy/HUMAN-AI-COLLABORATION-LEARNING-FIXED-FIXTURE-PROTOCOL-2026-07-31.md"
    ).read_text(encoding="utf-8")
    normalized = " ".join(document.split())
    for phrase in (
        "Why this is a protocol, not a standard",
        "planned-no-live-domain-evidence",
        "may not be merged into one fictional official arm",
        "gpt-5.3-codex-spark",
        "Immediate correctness cannot cancel worse delayed competence",
        "The next action is offline material and oracle calibration",
    ):
        _require(phrase in normalized, f"Learning protocol document missing: {phrase}")


def main() -> int:
    validate_protocol()
    print("Human-AI learning fixed-fixture protocol validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
