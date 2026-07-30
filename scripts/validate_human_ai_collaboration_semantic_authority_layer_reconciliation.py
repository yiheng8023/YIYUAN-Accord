#!/usr/bin/env python3
"""Validate the semantic-authority layer reconciliation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_PATH = (
    "registry/human-ai-collaboration-semantic-authority-layer-"
    "reconciliation-2026-07-28.json"
)
DOCUMENTATION_PATH = (
    "docs/strategy/HUMAN-AI-COLLABORATION-SEMANTIC-AUTHORITY-"
    "LAYER-RECONCILIATION-2026-07-28.md"
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def validate_reconciliation(
    document: dict[str, Any],
    *,
    root: Path = ROOT,
) -> None:
    _require(
        document.get("schema") == 1
        and document.get("id")
        == (
            "human-ai-collaboration-semantic-authority-layer-"
            "reconciliation-2026-07-28"
        )
        and document.get("date") == "2026-07-28"
        and document.get("status")
        == (
            "read-only-source-reconciliation-and-cross-lifecycle-"
            "design-calibration"
        )
        and document.get("scenarioId") == "HAC-SEMANTIC-AUTHORITY-01",
        "Semantic-authority reconciliation identity drifted",
    )
    source = document.get("sourceObservation")
    _require(
        isinstance(source, dict)
        and source.get("upstreamHead")
        == "ed37663cc5fbef691ddfecd080dff42f7e7e350d",
        "Semantic-authority upstream binding drifted",
    )
    files = {
        item["path"]: item
        for item in source.get("files", [])
        if isinstance(item, dict) and isinstance(item.get("path"), str)
    }
    expected_files = {
        "skills/engineering/grill-with-docs/SKILL.md": (
            245,
            "610d091047bcfb9db0f75c057d15538481a721111579fc5ec7f83ad9131a2165",
            "user-invoked-thin-composition-entry",
        ),
        "skills/engineering/domain-modeling/SKILL.md": (
            3427,
            "152e2c97239affb12a60c5f4a7e74ab546a49ae169688c81f4e2ccc42dafa579",
            "model-invoked-semantic-authority-maintenance-primitive",
        ),
        "skills/productivity/grilling/SKILL.md": (
            843,
            "44331dda57f461db4fec3f2efb6ddabe7aaaa0a57ae0f88a883bc61aed8a0587",
            "model-invoked-human-decision-elicitation-primitive",
        ),
        "skills/productivity/grill-me/SKILL.md": (
            147,
            "6189dfceb7304a6e5558f75d87e68fa3bc7fcf7ba120e44f21f8a61fe01eba54",
            "user-invoked-grilling-only-entry",
        ),
    }
    _require(
        set(files) == set(expected_files),
        "Semantic-authority source set drifted",
    )
    for path, expected in expected_files.items():
        item = files[path]
        _require(
            (item.get("bytes"), item.get("sha256"), item.get("role"))
            == expected,
            f"Semantic-authority source binding drifted: {path}",
        )
    local = document.get("currentLocalCcObservation")
    _require(
        isinstance(local, dict)
        and local.get("grillWithDocs", {}).get("sha256")
        == "e1078020c41b954638ba94acda95a3340739908bd68b1db9bc2af129d3936035"
        and local.get("grillMe", {}).get("sha256")
        == "c9df326c4ab635765ea884471d21f4e21d5b0ec85aec43a06c238307841eb4bc"
        and local.get("grillingPrimitiveInstalled") is False
        and local.get("domainModelingPrimitiveInstalled") is False
        and local.get("currentUpstreamWrapperDependencyComplete") is False
        and local.get("localPayloadEqualsCurrentUpstream") is False,
        "Semantic-authority local CC boundary drifted",
    )
    plane = document.get("semanticAuthorityPlane")
    _require(
        isinstance(plane, dict)
        and plane.get("isCrossCuttingStateNotUniversalSkill") is True
        and plane.get("elicitationPrimitive") == "grilling"
        and plane.get("semanticMaintenancePrimitive") == "domain-modeling"
        and plane.get("compositionEntry") == "grill-with-docs"
        and plane.get("portableCarrierNameFixedToContextMd") is False
        and plane.get("existingGlossaryConsumptionRequiresSkillInvocation")
        is False
        and plane.get("glossaryContainsImplementationPlan") is False
        and plane.get("humanDecisionAuthorityPreserved") is True
        and plane.get("hardStandardsRemainIndependentAndMandatory") is True
        and len(plane.get("lifecycleConsumers", [])) == 7,
        "Semantic-authority plane drifted",
    )
    routing = document.get("routingBoundary")
    _require(
        isinstance(routing, dict)
        and routing.get("mandatoryForEveryCodeTask") is False
        and len(routing.get("triggerWhen", [])) == 4
        and len(routing.get("skipOrReadOnlyWhen", [])) == 3,
        "Semantic-authority routing boundary drifted",
    )
    decision = document.get("decision")
    _require(
        isinstance(decision, dict)
        and decision.get("coreViewAccepted") is True
        and decision.get("structuralAdjustmentRequired") is True
        and decision.get(
            "currentExactLocalCandidateRemainsBoundForExistingProtocol"
        )
        is True
        and decision.get("currentCcPayloadUpdated") is False
        and decision.get("missingUpstreamPrimitivesInstalled") is False
        and decision.get("silentWrapperReplacementAllowed") is False
        and decision.get("selfAuthoredSkillGapProved") is False,
        "Semantic-authority decision boundary drifted",
    )
    claims = document.get("claimBoundary")
    _require(
        isinstance(claims, dict)
        and claims
        and all(value is False for value in claims.values()),
        "Semantic-authority claim boundary drifted",
    )
    _require(
        document.get("documentation") == DOCUMENTATION_PATH,
        "Semantic-authority documentation binding drifted",
    )
    text = " ".join(
        (root / DOCUMENTATION_PATH).read_text(encoding="utf-8").split()
    )
    for phrase in (
        "cross-lifecycle semantic authority plane",
        "not a universal requirement",
        "silent update",
        "hard standards remain independent mandatory gates",
        "does not prove invocation",
    ):
        _require(
            phrase in text,
            f"Semantic-authority documentation missing: {phrase}",
        )
    surfaces = {
        "north star": root / "docs/strategy/PRODUCT-NORTH-STAR.md",
        "research plan": root / "docs/strategy/RESEARCH-AND-POC-PLAN.md",
        "matrix": root / "docs/strategy/POC-SCENARIO-EVIDENCE-MATRIX.md",
        "continuation": root / "docs/operations/CONTINUATION.md",
        "program plan": root / "docs/curation-program-plan.md",
    }
    for label, path in surfaces.items():
        _require(
            "semantic authority"
            in path.read_text(encoding="utf-8").lower(),
            f"Semantic-authority link missing from {label}",
        )
    acceptance = json.loads(
        (root / "registry/program-acceptance-map.json").read_text(
            encoding="utf-8"
        )
    )
    end_to_end = next(
        item
        for item in acceptance["acceptanceCriteria"]
        if item["id"] == "acceptance.end-to-end-process-fidelity"
    )
    subgate_ids = {
        item["id"] for item in end_to_end.get("graduationSubgates", [])
    }
    _require(
        "subgate.persistent-semantic-authority-continuity" in subgate_ids
        and (
            "evidence.human-ai-collaboration-semantic-authority-layer-"
            "reconciliation-2026-07-28"
        )
        in end_to_end.get("evidenceIds", []),
        "Semantic-authority acceptance binding drifted",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    root = args.root.resolve()
    document = json.loads((root / EVIDENCE_PATH).read_text(encoding="utf-8"))
    validate_reconciliation(document, root=root)
    print("Human-AI semantic-authority layer reconciliation verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
