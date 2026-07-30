#!/usr/bin/env python3
"""Fail closed on drift in the unknown-quadrant process-fidelity mapping."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
MAPPING_PATH = (
    "registry/human-ai-collaboration-unknown-quadrant-process-fidelity-"
    "mapping-2026-07-27.json"
)
DOCUMENTATION_PATH = (
    "docs/strategy/HUMAN-AI-COLLABORATION-UNKNOWN-QUADRANT-PROCESS-"
    "FIDELITY-MAPPING-2026-07-27.md"
)
EXPECTED_SOURCE_PATHS = {
    "registry/skill-ecosystem-current-evidence-reconciliation-2026-07-27.json",
    "registry/human-ai-collaboration-tdd-current-self-authored-treatment-gap-audit-2026-07-27.json",
    "registry/human-ai-collaboration-tdd-noncomparative-dispatch-successor-contract-v2-2026-07-27.json",
    "registry/human-ai-collaboration-process-fidelity-cumulative-loss-accounting-contract-2026-07-27.json",
    "registry/human-ai-collaboration-process-fidelity-chained-transform-trial-protocol-2026-07-27.json",
    "registry/cc-switch-lark-seven-skill-update-event-2026-07-27.json",
}
EXPECTED_QUADRANTS = {
    "UNK-KK-01": "known-knowns",
    "UNK-KU-01": "known-unknowns",
    "UNK-UK-01": "unknown-knowns",
    "UNK-UU-01": "unknown-unknowns",
}
EXPECTED_SCENARIOS = set(EXPECTED_QUADRANTS) | {"UNK-LIFE-01"}
EXPECTED_PHASES = {
    "pre-implementation",
    "during-implementation",
    "post-implementation",
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


def validate_mapping(
    document: dict[str, Any],
    *,
    root: Path = ROOT,
) -> None:
    _require(document.get("schema") == 1, "mapping schema must be 1")
    _require(
        document.get("id")
        == "human-ai-collaboration-unknown-quadrant-process-fidelity-"
        "mapping-2026-07-27",
        "mapping identity drifted",
    )
    _require(
        document.get("status")
        == "research-mapping-validated-no-method-promotion-no-live-execution",
        "mapping status drifted",
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

    external = {
        item["kind"]: item for item in document.get("externalMethodSources", [])
    }
    _require(
        set(external) == {"primary", "secondary-user-provided"},
        "external method source set drifted",
    )
    _require(
        external["primary"].get("publisher") == "Anthropic"
        and external["primary"].get("published") == "2026-07-06"
        and external["primary"].get("contentByteBound") is False
        and external["primary"].get("recheckBeforeMaterialReuse") is True,
        "primary method source boundary drifted",
    )

    layers = document.get("systemLayerBoundary", {})
    _require(
        layers.get("hardStandards", {}).get("role")
        == "mandatory-controls-that-every-arm-must-pass"
        and layers["hardStandards"].get("skillTreatment") is False
        and layers["hardStandards"].get("candidateCreditAllowed") is False,
        "hard standards were promoted to a Skill treatment",
    )
    _require(
        layers.get("unknownQuadrantMapping", {}).get("role")
        == "research-and-task-framing-lens"
        and layers["unknownQuadrantMapping"].get("hardStandard") is False
        and layers["unknownQuadrantMapping"].get("defaultMandatoryWorkflow")
        is False
        and layers["unknownQuadrantMapping"].get("newSkill") is False,
        "unknown-quadrant lens was promoted",
    )
    _require(
        layers.get("externalSkillCandidates", {}).get("globalDefault") is False
        and layers["externalSkillCandidates"].get("sourceIdentityProvesValue")
        is False,
        "external Skill candidate boundary drifted",
    )
    _require(
        layers.get("runnerAndLedger", {}).get("methodTreatment") is False
        and layers.get("processFidelityLedger", {}).get(
            "terminalCorrectnessEquivalent"
        )
        is False,
        "infrastructure was promoted to method or terminal equivalence",
    )

    quadrants = {
        item["id"]: item for item in document.get("quadrants", [])
    }
    _require(
        {key: item.get("name") for key, item in quadrants.items()}
        == EXPECTED_QUADRANTS,
        "quadrant set drifted",
    )
    for quadrant_id, quadrant in quadrants.items():
        _require(
            quadrant.get("risk")
            and quadrant.get("requiredResponse")
            and quadrant.get("currentMechanisms")
            and quadrant.get("acceptance")
            and quadrant.get("falsifier")
            and quadrant.get("forbiddenClaim"),
            f"quadrant contract incomplete: {quadrant_id}",
        )
    _require(
        "unlabelled fact" in quadrants["UNK-KU-01"]["falsifier"],
        "known-unknown uncertainty could be promoted to certainty",
    )
    _require(
        "confirmed user preference"
        in quadrants["UNK-UK-01"]["falsifier"],
        "unknown-known preference boundary drifted",
    )
    _require(
        "absence of unknown unknowns"
        in quadrants["UNK-UU-01"]["forbiddenClaim"],
        "unknown-unknown completeness boundary drifted",
    )

    lifecycle = {
        item["phase"]: item for item in document.get("lifecycle", [])
    }
    _require(set(lifecycle) == EXPECTED_PHASES, "lifecycle phase set drifted")
    _require(
        all(item.get("hardStandardReplacement") is False for item in lifecycle.values()),
        "lifecycle practice replaced a hard standard",
    )
    _require(
        "cannot substitute for tests"
        in lifecycle["post-implementation"]["artifactPolicy"],
        "quiz or explanation was promoted to acceptance evidence",
    )

    scenarios = {
        item["id"]: item for item in document.get("scenarioMatrix", [])
    }
    _require(set(scenarios) == EXPECTED_SCENARIOS, "scenario matrix set drifted")
    for scenario_id, scenario in scenarios.items():
        _require(
            scenario.get("hostDifference")
            and scenario.get("permissionBoundary")
            and scenario.get("metric")
            and scenario.get("reuseOrder")
            and scenario.get("fallback")
            and scenario.get("falsifiableConclusion"),
            f"scenario evidence contract incomplete: {scenario_id}",
        )
    _require(
        scenarios["UNK-UU-01"]["permissionBoundary"]
        == "discovery is read-only evidence gathering, never action authority",
        "discovery was promoted to authority",
    )
    _require(
        "Terminal correctness cannot rescue"
        in scenarios["UNK-LIFE-01"]["falsifiableConclusion"],
        "terminal correctness was allowed to erase process loss",
    )

    decision = document.get("decision", {})
    _require(
        decision.get("methodAddsUsefulResearchLens") is True
        and decision.get("methodBecomesHardStandard") is False
        and decision.get("methodBecomesGlobalMandatoryWorkflow") is False
        and decision.get("newSkillImplementationNecessary") is False
        and decision.get("existingSelfAuthoredChainRemoved") is False
        and decision.get("externalSkillInstalledOrPromoted") is False,
        "mapping decision promoted an unproved method or self-build need",
    )
    execution = document.get("executionBoundary", {})
    _require(
        execution.get("repositoryResearchAndMappingOnly") is True
        and execution.get("modelRequestCount") == 0
        and execution.get("candidateDispatchCount") == 0
        and execution.get("candidateSkillInvocationCount") == 0
        and all(
            execution.get(key) is False
            for key in (
                "installationPerformed",
                "ccSwitchChanged",
                "globalConfigurationChanged",
                "externalAccountMutationPerformed",
                "portfolioMutationAuthorized",
            )
        ),
        "mapping execution boundary drifted",
    )
    _require(
        document.get("claimBoundary")
        and all(value is False for value in document["claimBoundary"].values()),
        "mapping claim boundary was promoted",
    )
    _require(
        document.get("documentation") == DOCUMENTATION_PATH,
        "mapping documentation pointer drifted",
    )
    documentation = (root / DOCUMENTATION_PATH).read_text(encoding="utf-8")
    for phrase in (
        "Known Knowns",
        "Known Unknowns",
        "Unknown Knowns",
        "Unknown Unknowns",
        "Hard standards are controls, not Skill treatments",
        "cannot substitute for tests",
        "does not authorize installation",
    ):
        _require(
            phrase in documentation,
            f"mapping documentation boundary missing: {phrase}",
        )
    for path in NARRATIVE_PATHS:
        narrative = (root / path).read_text(encoding="utf-8")
        _require(
            "unknown-quadrant process-fidelity mapping" in narrative,
            f"mapping narrative pointer missing: {path}",
        )


def main() -> int:
    validate_mapping(_load(ROOT, MAPPING_PATH))
    print(
        "human-ai collaboration unknown-quadrant process-fidelity mapping "
        "validation passed"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
