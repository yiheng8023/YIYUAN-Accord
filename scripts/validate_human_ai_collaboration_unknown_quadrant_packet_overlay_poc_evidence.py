#!/usr/bin/env python3
"""Validate the zero-model unknown-quadrant packet-overlay PoC evidence."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

try:
    from scripts.evaluate_human_ai_collaboration_unknown_knowns_creative_preference_packet import (
        evaluate_packet_document,
    )
    from scripts.evaluate_human_ai_collaboration_unknown_quadrant_packet_overlay import (
        EXPECTED_CLASSES,
        evaluate_document,
    )
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from evaluate_human_ai_collaboration_unknown_knowns_creative_preference_packet import (
        evaluate_packet_document,
    )
    from evaluate_human_ai_collaboration_unknown_quadrant_packet_overlay import (
        EXPECTED_CLASSES,
        evaluate_document,
    )


ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_PATH = (
    "registry/human-ai-collaboration-unknown-quadrant-packet-overlay-"
    "poc-evidence-2026-07-27.json"
)
DOCUMENTATION_PATH = (
    "docs/strategy/HUMAN-AI-COLLABORATION-UNKNOWN-QUADRANT-PACKET-"
    "OVERLAY-POC-EVIDENCE-2026-07-27.md"
)
CREATIVE_PACKET_PATH = (
    "tests/fixtures/human-ai-collaboration-unknown-knowns-creative-"
    "preference-packet-2026-07-27.json"
)
OVERLAY_FIXTURE_PATH = (
    "tests/fixtures/human-ai-collaboration-unknown-quadrant-packet-"
    "overlay-2026-07-27.json"
)
EXPECTED_SOURCE_PATHS = {
    "registry/human-ai-collaboration-unknown-quadrant-attribution-oracle-poc-evidence-2026-07-27.json",
    CREATIVE_PACKET_PATH,
    "scripts/evaluate_human_ai_collaboration_unknown_knowns_creative_preference_packet.py",
    OVERLAY_FIXTURE_PATH,
    "scripts/evaluate_human_ai_collaboration_unknown_quadrant_packet_overlay.py",
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


def validate_evidence(
    document: dict[str, Any],
    *,
    root: Path = ROOT,
) -> None:
    _require(document.get("schema") == 1, "evidence schema must be 1")
    _require(
        document.get("id")
        == "human-ai-collaboration-unknown-quadrant-packet-overlay-poc-"
        "evidence-2026-07-27",
        "evidence identity drifted",
    )
    _require(
        document.get("status")
        == "zero-model-private-overlay-compatible-faults-fail-closed-no-"
        "live-evidence",
        "evidence status drifted",
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

    overlay_fixture = _load(root, OVERLAY_FIXTURE_PATH)
    overlay_result = evaluate_document(overlay_fixture, root=root)
    base_results = overlay_result["baseResults"]
    fault_results = overlay_result["faultResults"]
    compatibility = document.get("compatibilityResult", {})
    _require(
        len(base_results) == 5
        and all(
            item["actual"] == "compatible-zero-model-private-overlay"
            for item in base_results
        )
        and compatibility.get("baseOverlayCount") == 5
        and compatibility.get("compatibleBaseOverlayCount") == 5
        and compatibility.get("baseMismatchCount") == 0,
        "base overlay compatibility drifted",
    )
    _require(
        len(fault_results) == 5
        and all(item["actual"] == item["expected"] for item in fault_results)
        and compatibility.get("faultInjectionCount") == 5
        and compatibility.get("expectedFaultRejectionCount") == 5
        and compatibility.get("faultMismatchCount") == 0,
        "overlay fault rejection drifted",
    )
    _require(
        set(compatibility.get("coveredClasses", [])) == EXPECTED_CLASSES
        and set(overlay_result["unknownClasses"]) == EXPECTED_CLASSES,
        "overlay class coverage drifted",
    )

    creative = _load(root, CREATIVE_PACKET_PATH)
    creative_results = evaluate_packet_document(creative)
    creative_summary = document.get("unknownKnownsPacketResult", {})
    _require(
        len(creative_results) == 6
        and all(item["actual"] == item["expected"] for item in creative_results)
        and creative_summary.get("offlineExampleCount") == 6
        and creative_summary.get("matchedExpectedCount") == 6
        and creative_summary.get("mismatchCount") == 0
        and creative_summary.get("positiveExampleCount") == 1
        and creative_summary.get("negativeControlCount") == 5
        and creative_summary.get(
            "historicalExecutablePacketPreviouslyPresent"
        )
        is False
        and creative_summary.get("derivedFromExistingPlannedScenario") is True
        and creative_summary.get("fixtureCoverageGapClosed") is True
        and creative_summary.get("productCapabilityResidualGapProved") is False,
        "Unknown Knowns packet result drifted",
    )

    firewall = document.get("faultFirewall", {})
    _require(
        firewall
        == {
            "privateOracleExposureRejected": True,
            "hardStandardDriftRejected": True,
            "sourcePacketMutationRejected": True,
            "sourceIdentityUnverifiedRejected": True,
            "liveAuthorityExpansionRejected": True,
        },
        "overlay firewall drifted",
    )
    decision = document.get("decision", {})
    _require(
        decision.get("privateOverlayCompatibilityPocValidated") is True
        and decision.get("historicalPacketsMutated") is False
        and decision.get("publicTaskInputsChangedByOverlay") is False
        and decision.get("hardStandardsChangedByOverlay") is False
        and decision.get("modelDispatchAuthorized") is False
        and decision.get("readyForRendererAndPacketBuilderIntegrationReview")
        is True
        and decision.get("readyForLiveWeakDispatch") is False
        and decision.get("newSkillNecessary") is False
        and decision.get("selfAuthoringAuthorized") is False,
        "evidence decision promoted an unproved live or self-build state",
    )
    execution = document.get("executionBoundary", {})
    _require(
        execution.get("repositoryLocalDeterministicEvaluationOnly") is True
        and execution.get("modelRequestCount") == 0
        and execution.get("candidateDispatchCount") == 0
        and execution.get("candidateSkillInvocationCount") == 0
        and execution.get("assetGenerationCount") == 0
        and all(
            execution.get(key) is False
            for key in (
                "externalAccessUsed",
                "installationPerformed",
                "ccSwitchChanged",
                "globalConfigurationChanged",
                "gitMutationPerformed",
                "externalWritePerformed",
            )
        ),
        "evidence execution boundary drifted",
    )
    _require(
        document.get("claimBoundary")
        and all(value is False for value in document["claimBoundary"].values()),
        "evidence claim boundary was promoted",
    )
    _require(
        document.get("documentation") == DOCUMENTATION_PATH,
        "evidence documentation pointer drifted",
    )
    documentation = (root / DOCUMENTATION_PATH).read_text(encoding="utf-8")
    for phrase in (
        "All five",
        "five negative",
        "fixture-coverage gap",
        "not a product capability residual gap",
        "does not authorize oracle exposure",
    ):
        _require(
            phrase in documentation,
            f"evidence documentation boundary missing: {phrase}",
        )
    for path in NARRATIVE_PATHS:
        narrative = (root / path).read_text(encoding="utf-8")
        _require(
            "unknown-quadrant packet-overlay PoC" in narrative,
            f"evidence narrative pointer missing: {path}",
        )


def main() -> int:
    validate_evidence(_load(ROOT, EVIDENCE_PATH))
    print(
        "human-ai collaboration unknown-quadrant packet-overlay PoC "
        "evidence validation passed"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
