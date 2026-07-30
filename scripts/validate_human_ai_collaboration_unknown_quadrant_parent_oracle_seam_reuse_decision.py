#!/usr/bin/env python3
"""Validate the parent-only oracle seam reuse decision."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DECISION_PATH = (
    "registry/human-ai-collaboration-unknown-quadrant-parent-oracle-"
    "seam-reuse-decision-2026-07-27.json"
)
DOCUMENTATION_PATH = (
    "docs/strategy/HUMAN-AI-COLLABORATION-UNKNOWN-QUADRANT-PARENT-"
    "ORACLE-SEAM-REUSE-DECISION-2026-07-27.md"
)
EXPECTED_SOURCE_PATHS = {
    "registry/human-ai-collaboration-unknown-quadrant-packet-overlay-poc-evidence-2026-07-27.json",
    "scripts/build_human_ai_collaboration_weak_agent_trial.py",
    "tests/test_human_ai_collaboration_weak_agent_trial_builder.py",
    "scripts/build_human_ai_collaboration_process_fidelity_information_equivalent_trial_packet.py",
    "tests/test_human_ai_collaboration_process_fidelity_information_equivalent_trial_packet.py",
    "scripts/build_context_continuation_trial_packet.py",
    "tests/test_context_continuation_trial_packet.py",
}
EXPECTED_SEAM_IDS = {
    "SEAM-WEAK-TRIAL-SPEC-PRIVATE-PAYLOAD",
    "SEAM-PROCESS-FIDELITY-AGENT-VISIBLE-PROJECTION",
    "SEAM-CONTEXT-DEFAULT-PUBLIC-PROJECTION",
}
NARRATIVE_PATHS = {
    "docs/curation-program-plan.md",
    "docs/strategy/RESEARCH-AND-POC-PLAN.md",
    "docs/strategy/POC-SCENARIO-EVIDENCE-MATRIX.md",
    "docs/operations/CONTINUATION.md",
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _load(root: Path, path: str) -> dict[str, Any]:
    return json.loads((root / path).read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_decision(
    document: dict[str, Any],
    *,
    root: Path = ROOT,
) -> None:
    _require(document.get("schema") == 1, "decision schema must be 1")
    _require(
        document.get("id")
        == "human-ai-collaboration-unknown-quadrant-parent-oracle-seam-"
        "reuse-decision-2026-07-27",
        "decision identity drifted",
    )
    _require(
        document.get("status")
        == "existing-parent-only-oracle-seams-sufficient-no-new-adapter-"
        "justified",
        "decision status drifted",
    )
    bindings = {
        item["path"]: item for item in document.get("sourceBindings", [])
    }
    _require(set(bindings) == EXPECTED_SOURCE_PATHS, "source binding set drifted")
    for path, binding in bindings.items():
        source = root / path
        _require(source.is_file(), f"source binding missing: {path}")
        _require(
            binding.get("bytes") == len(source.read_bytes()),
            f"source binding byte count drifted: {path}",
        )
        _require(
            binding.get("sha256") == _sha256(source),
            f"source binding digest drifted: {path}",
        )

    seams = {item["id"]: item for item in document.get("observedSeams", [])}
    _require(set(seams) == EXPECTED_SEAM_IDS, "observed seam set drifted")
    _require(
        all(item.get("arbitraryRuntimeOverrideExposed") is False for item in seams.values()),
        "generic runtime override was overclaimed",
    )
    weak_builder = (root / "scripts/build_human_ai_collaboration_weak_agent_trial.py").read_text(
        encoding="utf-8"
    )
    _require(
        '"privateOraclePayload"' in weak_builder
        and '"contentWrittenIntoTrial": False' in weak_builder
        and '"taskPrompt": spec.get("taskPrompt"' in weak_builder,
        "weak-Agent private-oracle seam drifted",
    )
    weak_tests = (
        root / "tests/test_human_ai_collaboration_weak_agent_trial_builder.py"
    ).read_text(encoding="utf-8")
    _require(
        "test_builds_read_only_research_packet_without_oracle_answers"
        in weak_tests
        and 'manifest["privateOracle"]["contentWrittenIntoTrial"]'
        in weak_tests,
        "weak-Agent seam regression drifted",
    )
    process_builder = (
        root
        / "scripts/build_human_ai_collaboration_process_fidelity_information_equivalent_trial_packet.py"
    ).read_text(encoding="utf-8")
    _require(
        '"agentVisibleProjection"' in process_builder
        and '"privateOracle"' in process_builder
        and '"privateOracleContentWritten": False' in process_builder,
        "process-fidelity private-oracle seam drifted",
    )
    context_builder = (
        root / "scripts/build_context_continuation_trial_packet.py"
    ).read_text(encoding="utf-8")
    _require(
        "--emit-parent-packet" in context_builder
        and "oraclePrivate" in context_builder,
        "context parent-only oracle seam drifted",
    )

    reuse = document.get("reuseDecision", {})
    _require(
        reuse.get("existingParentOnlyOraclePatternExists") is True
        and reuse.get("existingPatternSufficientForCurrentZeroModelPhase")
        is True
        and reuse.get("genericNewOracleAdapterNecessary") is False
        and reuse.get("genericArbitraryRuntimeOverrideDesirable") is False
        and reuse.get("unknownQuadrantOverlayPlacement")
        == "parent-evaluator-and-protocol-owned-private-payload"
        and reuse.get("publicTaskPacketPlacement")
        == "unchanged-agent-visible-projection"
        and reuse.get("liveProtocolSpecificIntegrationImplemented") is False
        and reuse.get("residualAdapterGapProved") is False
        and reuse.get("selfAuthoredSkillOrAdapterAuthorized") is False,
        "seam reuse decision drifted",
    )
    gate = document.get("futureIntegrationGate", {})
    _require(
        all(
            gate.get(key) is True
            for key in (
                "exactScenarioAndArmRequired",
                "exactPrivateOracleSchemaRequired",
                "agentVisibleProjectionHashRequired",
                "privateOracleCanonicalHashRequired",
                "oracleLeakageNegativeTestRequired",
                "hardStandardIdentityRequired",
                "freshWeakRouteAndDispatchAuthorityRequired",
                "ledgerReservationRequired",
            )
        )
        and "Do not add a global arbitrary oracle override"
        in gate.get("implementationRule", ""),
        "future integration gate drifted",
    )
    decision = document.get("decision", {})
    _require(
        all(
            decision.get(key) is False
            for key in (
                "newAdapterImplementationStarted",
                "weakAgentBuilderChanged",
                "processFidelityBuilderChanged",
                "contextBuilderChanged",
                "historicalTestsChanged",
            )
        ),
        "decision overclaimed implementation",
    )
    execution = document.get("executionBoundary", {})
    _require(
        execution.get("repositoryReadOnlySeamReview") is True
        and execution.get("modelRequestCount") == 0
        and execution.get("candidateDispatchCount") == 0
        and execution.get("candidateSkillInvocationCount") == 0
        and all(
            execution.get(key) is False
            for key in (
                "installationPerformed",
                "ccSwitchChanged",
                "globalConfigurationChanged",
                "gitMutationPerformed",
                "externalWritePerformed",
            )
        ),
        "decision execution boundary drifted",
    )
    _require(
        document.get("claimBoundary")
        and all(value is False for value in document["claimBoundary"].values()),
        "decision claim boundary was promoted",
    )
    _require(
        document.get("documentation") == DOCUMENTATION_PATH,
        "decision documentation pointer drifted",
    )
    documentation = (root / DOCUMENTATION_PATH).read_text(encoding="utf-8")
    for phrase in (
        "do not need a new generic renderer",
        "Why no generic override",
        "No builder or historical test was changed",
        "does not prove live integration",
    ):
        _require(
            phrase in documentation,
            f"decision documentation boundary missing: {phrase}",
        )
    for path in NARRATIVE_PATHS:
        narrative = (root / path).read_text(encoding="utf-8")
        _require(
            "parent-oracle seam reuse decision" in narrative,
            f"decision narrative pointer missing: {path}",
        )


def main() -> int:
    validate_decision(_load(ROOT, DECISION_PATH))
    print(
        "human-ai collaboration unknown-quadrant parent-oracle seam reuse "
        "decision validation passed"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
