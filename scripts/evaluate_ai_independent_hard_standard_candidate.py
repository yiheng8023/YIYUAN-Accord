#!/usr/bin/env python3
"""Evaluate the AI-independent boundary of a future hard-standard candidate."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
GATE_PATH = Path(
    "registry/ai-independent-hard-standard-boundary-gate-2026-08-07.json"
)
ACCEPTANCE_PATH = Path("registry/program-acceptance-map.json")
REBASELINE_PATH = Path(
    "registry/human-ai-collaboration-coverage-rebaseline-2026-07-24.json"
)
EVIDENCE_ID = "evidence.ai-independent-hard-standard-boundary-gate-2026-08-07"

REMOVED_SOFT_CAPABILITIES = {
    "AI",
    "model",
    "Skill",
    "Hook",
    "Agent behavior",
}
AI_INDEPENDENT_EXECUTION_KINDS = {
    "deterministic-cli",
    "project-process",
    "domain-control",
    "human-procedure",
}
AI_INDEPENDENT_PROOF_KINDS = {
    "deterministic-validator",
    "domain-verification",
    "independent-inspection",
}
ACCOUNTABLE_OWNER_TYPES = {
    "human",
    "governed-organization-role",
    "project-authority-role",
    "domain-authority-role",
}
MUTATION_CASE_IDS = (
    "wrong-candidate-class",
    "obligation-statement",
    "obligation-without-ai",
    "obligation-without-skills",
    "obligation-evidence",
    "owner-type",
    "owner-non-ai",
    "owner-evidence",
    "execution-skill-only",
    "execution-evidence",
    "proof-skill-only",
    "proof-evidence",
    "ablation-removal",
    "ablation-obligation",
    "ablation-owner",
    "ablation-execution-reference",
    "ablation-proof-reference",
    "ablation-evidence",
    "separate-admission",
    "current-admitted",
)


def _nonempty_strings(value: Any) -> bool:
    return (
        isinstance(value, list)
        and bool(value)
        and all(isinstance(item, str) and item for item in value)
    )


def evaluate_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    """Return a fail-closed boundary decision without admitting a standard."""
    blockers: list[str] = []
    obligation = candidate.get("obligation", {})
    owner = candidate.get("accountableOwner", {})
    execution_surfaces = candidate.get("executionSurfaces", [])
    proof_surfaces = candidate.get("proofSurfaces", [])
    ablation = candidate.get("counterfactualAblation", {})
    admission = candidate.get("admission", {})

    if candidate.get("candidateClass") != "future-hard-standard-candidate":
        blockers.append("wrong-candidate-class")
    if not (
        isinstance(obligation.get("statement"), str)
        and obligation.get("statement")
        and obligation.get("validWithoutAI") is True
        and obligation.get("validWithoutSkills") is True
        and _nonempty_strings(obligation.get("evidenceIds"))
    ):
        blockers.append("obligation-not-ai-independent")
    if not (
        isinstance(owner.get("authorityId"), str)
        and owner.get("authorityId")
        and owner.get("authorityType") in ACCOUNTABLE_OWNER_TYPES
        and owner.get("nonAI") is True
        and _nonempty_strings(owner.get("evidenceIds"))
    ):
        blockers.append("accountable-owner-missing")

    execution_ids = {
        item.get("id")
        for item in execution_surfaces
        if isinstance(item, dict)
        and item.get("availableWithoutAIOrSkills") is True
        and item.get("kind") in AI_INDEPENDENT_EXECUTION_KINDS
        and _nonempty_strings(item.get("evidenceIds"))
        and isinstance(item.get("id"), str)
        and item.get("id")
    }
    proof_ids = {
        item.get("id")
        for item in proof_surfaces
        if isinstance(item, dict)
        and item.get("availableWithoutAIOrSkills") is True
        and item.get("kind") in AI_INDEPENDENT_PROOF_KINDS
        and _nonempty_strings(item.get("evidenceIds"))
        and isinstance(item.get("id"), str)
        and item.get("id")
    }
    if not execution_ids:
        blockers.append("no-ai-independent-execution-surface")
    if not proof_ids:
        blockers.append("no-ai-independent-proof-surface")

    if set(ablation.get("removedCapabilities", [])) != REMOVED_SOFT_CAPABILITIES:
        blockers.append("counterfactual-removal-set-incomplete")
    if not _nonempty_strings(ablation.get("evidenceIds")):
        blockers.append("counterfactual-evidence-missing")
    if not (
        ablation.get("obligationPreserved") is True
        and ablation.get("ownerPreserved") is True
    ):
        blockers.append("counterfactual-invariant-not-preserved")
    if set(ablation.get("executionSurfaceIds", [])) - execution_ids:
        blockers.append("counterfactual-execution-reference-invalid")
    if set(ablation.get("proofSurfaceIds", [])) - proof_ids:
        blockers.append("counterfactual-proof-reference-invalid")
    if not ablation.get("executionSurfaceIds", []):
        blockers.append("counterfactual-execution-reference-invalid")
    if not ablation.get("proofSurfaceIds", []):
        blockers.append("counterfactual-proof-reference-invalid")

    if not (
        admission.get("separateGovernedAdmissionRequired") is True
        and admission.get("currentStatus") == "not-admitted"
    ):
        blockers.append("separate-admission-boundary-missing")

    return {
        "decision": "blocked" if blockers else "boundary-eligible",
        "blockers": blockers,
        "admissionAuthorized": False,
        "claimBoundary": "synthetic-gate-mechanism-only",
    }


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _mutation_cases(candidate: dict[str, Any]) -> list[tuple[str, dict[str, Any], str]]:
    specifications = (
        ("wrong-candidate-class", ("candidateClass",), "external", "wrong-candidate-class"),
        ("obligation-statement", ("obligation", "statement"), "", "obligation-not-ai-independent"),
        ("obligation-without-ai", ("obligation", "validWithoutAI"), False, "obligation-not-ai-independent"),
        ("obligation-without-skills", ("obligation", "validWithoutSkills"), False, "obligation-not-ai-independent"),
        ("obligation-evidence", ("obligation", "evidenceIds"), [], "obligation-not-ai-independent"),
        ("owner-type", ("accountableOwner", "authorityType"), "model", "accountable-owner-missing"),
        ("owner-non-ai", ("accountableOwner", "nonAI"), False, "accountable-owner-missing"),
        ("owner-evidence", ("accountableOwner", "evidenceIds"), [], "accountable-owner-missing"),
        ("execution-skill-only", ("executionSurfaces", 0, "kind"), "Skill", "no-ai-independent-execution-surface"),
        ("execution-evidence", ("executionSurfaces", 0, "evidenceIds"), [], "no-ai-independent-execution-surface"),
        ("proof-skill-only", ("proofSurfaces", 0, "kind"), "Skill", "no-ai-independent-proof-surface"),
        ("proof-evidence", ("proofSurfaces", 0, "evidenceIds"), [], "no-ai-independent-proof-surface"),
        ("ablation-removal", ("counterfactualAblation", "removedCapabilities"), ["AI"], "counterfactual-removal-set-incomplete"),
        ("ablation-obligation", ("counterfactualAblation", "obligationPreserved"), False, "counterfactual-invariant-not-preserved"),
        ("ablation-owner", ("counterfactualAblation", "ownerPreserved"), False, "counterfactual-invariant-not-preserved"),
        ("ablation-execution-reference", ("counterfactualAblation", "executionSurfaceIds"), ["missing"], "counterfactual-execution-reference-invalid"),
        ("ablation-proof-reference", ("counterfactualAblation", "proofSurfaceIds"), ["missing"], "counterfactual-proof-reference-invalid"),
        ("ablation-evidence", ("counterfactualAblation", "evidenceIds"), [], "counterfactual-evidence-missing"),
        ("separate-admission", ("admission", "separateGovernedAdmissionRequired"), False, "separate-admission-boundary-missing"),
        ("current-admitted", ("admission", "currentStatus"), "admitted", "separate-admission-boundary-missing"),
    )
    cases: list[tuple[str, dict[str, Any], str]] = []
    for case_id, path, replacement, blocker in specifications:
        mutated = copy.deepcopy(candidate)
        target: Any = mutated
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = replacement
        cases.append((case_id, mutated, blocker))
    return cases


def validate_gate_record(
    record: dict[str, Any],
    *,
    acceptance: dict[str, Any] | None = None,
    rebaseline: dict[str, Any] | None = None,
    root: Path = ROOT,
) -> None:
    """Validate one in-memory gate record and all declared failure injections."""
    _require(
        record.get("schema") == 1
        and record.get("id") == "ai-independent-hard-standard-boundary-gate-v1"
        and record.get("status") == "verified-synthetic-gate-mechanism-only",
        "AI-independent hard-standard gate identity drifted",
    )
    documentation = record.get("documentation")
    _require(
        documentation
        == "docs/strategy/AI-INDEPENDENT-HARD-STANDARD-BOUNDARY-GATE-2026-08-07.md"
        and (root / documentation).is_file(),
        "AI-independent hard-standard documentation binding drifted",
    )
    _require(
        record.get("publicSeam")
        == {
            "evaluator": "scripts/evaluate_ai_independent_hard_standard_candidate.py",
            "test": "tests/test_ai_independent_hard_standard_boundary_gate.py",
            "mode": "pure-zero-model-no-capability-execution",
        },
        "AI-independent hard-standard public seam drifted",
    )
    source_bindings = record.get("sourceBindings", {})
    _require(
        source_bindings
        == {
            "programAcceptanceMap": str(ACCEPTANCE_PATH).replace("\\", "/"),
            "coverageRebaseline": str(REBASELINE_PATH).replace("\\", "/"),
        }
        and all((root / path).is_file() for path in source_bindings.values()),
        "AI-independent hard-standard source binding drifted",
    )
    if rebaseline is None:
        rebaseline = json.loads(
            (root / REBASELINE_PATH).read_text(encoding="utf-8")
        )
    source_gates = {
        item.get("id"): item
        for item in rebaseline.get("gates", [])
        if isinstance(item, dict)
    }
    source_gate = source_gates.get("gate.ai-independent-hard-standard", {})
    _require(
        source_gate.get("passCondition")
        == "A proposed hard standard remains valid and testable when AI and Skills are absent."
        and source_gate.get("falsifier")
        == "A Skill instruction, Agent behavior, or model capability is the only execution or proof surface for a mandatory standard."
        and rebaseline.get("decision", {}).get("hardStandardPromotionAuthorized")
        is False,
        "AI-independent hard-standard source gate drifted",
    )
    if acceptance is None:
        acceptance = json.loads(
            (root / ACCEPTANCE_PATH).read_text(encoding="utf-8")
        )
    criteria = {
        item.get("id"): item
        for item in acceptance.get("acceptanceCriteria", [])
        if isinstance(item, dict)
    }
    evidence = {
        item.get("id"): item
        for item in acceptance.get("evidence", [])
        if isinstance(item, dict)
    }
    criterion = criteria.get("acceptance.ai-independent-hard-standard-boundary", {})
    evidence_item = evidence.get(EVIDENCE_ID, {})
    _require(
        criterion.get("assessment") == "verified"
        and criterion.get("verificationIds")
        == ["verification.ai-independent-hard-standard-boundary"]
        and EVIDENCE_ID in criterion.get("evidenceIds", [])
        and "sole mandatory execution or proof surface"
        in criterion.get("statement", "")
        and evidence_item.get("path") == str(GATE_PATH).replace("\\", "/")
        and evidence_item.get("supports")
        == ["acceptance.ai-independent-hard-standard-boundary"],
        "AI-independent hard-standard acceptance binding drifted",
    )
    fixture = record.get("syntheticFixture", {})
    candidate = fixture.get("candidate", {})
    _require(
        fixture.get("declaredSynthetic") is True
        and fixture.get("realStandardRepresented") is False
        and str(candidate.get("id", "")).startswith("synthetic-"),
        "AI-independent hard-standard synthetic boundary drifted",
    )
    _require(
        evaluate_candidate(candidate) == fixture.get("expectedDecision"),
        "AI-independent hard-standard positive fixture drifted",
    )
    mutations = _mutation_cases(candidate)
    _require(
        tuple(record.get("failureInjectionCaseIds", [])) == MUTATION_CASE_IDS
        and tuple(case_id for case_id, _, _ in mutations) == MUTATION_CASE_IDS,
        "AI-independent hard-standard mutation ledger drifted",
    )
    for case_id, mutated, expected_blocker in mutations:
        decision = evaluate_candidate(mutated)
        _require(
            decision.get("decision") == "blocked"
            and decision.get("admissionAuthorized") is False
            and expected_blocker in decision.get("blockers", []),
            f"AI-independent hard-standard mutation did not fail closed: {case_id}",
        )
    claims = record.get("claimBoundary", {})
    _require(
        claims.get("provesFailClosedGateMechanism") is True
        and all(
            claims.get(key) is False
            for key in (
                "provesRealStandardNeed",
                "provesEvidenceTruth",
                "provesStandardValue",
                "provesAdoptionOrCompliance",
                "provesCrossHostBehavior",
                "provesProductionReadiness",
            )
        ),
        "AI-independent hard-standard claim boundary drifted",
    )
    _require(
        record.get("authorityBoundary")
        and all(value is False for value in record["authorityBoundary"].values()),
        "AI-independent hard-standard authority boundary expanded",
    )


def validate_repository_gate(root: Path = ROOT) -> dict[str, Any]:
    """Validate the checked-in gate record and its synthetic public seam."""
    record = json.loads((root / GATE_PATH).read_text(encoding="utf-8"))
    validate_gate_record(
        record,
        acceptance=json.loads(
            (root / ACCEPTANCE_PATH).read_text(encoding="utf-8")
        ),
        rebaseline=json.loads(
            (root / REBASELINE_PATH).read_text(encoding="utf-8")
        ),
        root=root,
    )
    return record


def main() -> int:
    validate_repository_gate()
    print("AI-independent hard-standard boundary gate validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
