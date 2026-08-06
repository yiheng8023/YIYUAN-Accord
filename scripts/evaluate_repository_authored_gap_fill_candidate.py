#!/usr/bin/env python3
"""Evaluate a repository-authored gap-fill candidate without executing it."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
GATE_PATH = Path("registry/repository-authored-gap-fill-gate-2026-08-06.json")
PROGRAM_PLAN_PATH = Path("registry/curation-program-plan.json")
ACCEPTANCE_PATH = Path("registry/program-acceptance-map.json")
PORTFOLIO_AUTHORITY_PATH = Path("registry/skill-portfolio-current-authority.json")
PROJECTION_PATH = Path("registry/portfolio-tasktime-projection-contract-2026-08-06.json")

REQUIRED_ALTERNATIVE_ROUTES = (
    "native-runtime",
    "official-runtime",
    "task-bound-targeted-discovery",
    "reviewed-maintained-external",
    "composition",
    "non-skill-harness",
    "project-standard",
    "human-control",
)

MUTATION_CASE_IDS = (
    "wrong-origin-class",
    "incumbent-exemption",
    "residual-gap-status",
    "residual-gap-evidence",
    *(f"alternative-{route}" for route in REQUIRED_ALTERNATIVE_ROUTES),
    "design-provenance",
    "license-ownership",
    "security-review",
    "portability-review",
    "overlap-review",
    "tests",
    "owner-approval",
)


def _nonempty_strings(value: Any) -> bool:
    return (
        isinstance(value, list)
        and bool(value)
        and all(isinstance(item, str) and item for item in value)
    )


def evaluate_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    """Return the fail-closed admission decision for one candidate fixture."""
    blockers: list[str] = []
    if candidate.get("originClass") != "repository-authored-gap-fill-candidate":
        blockers.append("wrong-origin-class")
    if candidate.get("incumbentExemptionRequested") is not False:
        blockers.append("incumbent-exemption-forbidden")

    residual = candidate.get("residualGap", {})
    if residual.get("status") != "supported":
        blockers.append("residual-gap-not-supported")
    elif not (
        isinstance(residual.get("demandCoordinateId"), str)
        and residual.get("demandCoordinateId")
        and _nonempty_strings(residual.get("reproductionEvidenceIds"))
    ):
        blockers.append("residual-gap-evidence-incomplete")

    alternatives = candidate.get("alternatives", {})
    for route in REQUIRED_ALTERNATIVE_ROUTES:
        record = alternatives.get(route, {})
        if record.get("status") != "exhausted-with-evidence" or not _nonempty_strings(
            record.get("evidenceIds")
        ):
            blockers.append(f"alternative-not-exhausted:{route}")

    provenance = candidate.get("designProvenance", {})
    if not (
        provenance.get("repositoryOwned") is True
        and isinstance(provenance.get("rationale"), str)
        and provenance.get("rationale")
        and _nonempty_strings(provenance.get("evidenceIds"))
    ):
        blockers.append("design-provenance-incomplete")

    license_ownership = candidate.get("licenseOwnership", {})
    if not (
        license_ownership.get("confirmed") is True
        and isinstance(license_ownership.get("licenseId"), str)
        and license_ownership.get("licenseId")
    ):
        blockers.append("license-ownership-unconfirmed")

    reviews = candidate.get("reviews", {})
    for review_name in ("security", "portability", "overlap"):
        review = reviews.get(review_name, {})
        if review.get("status") != "passed" or not _nonempty_strings(
            review.get("evidenceIds")
        ):
            blockers.append(f"{review_name}-review-incomplete")

    tests = candidate.get("tests", {})
    if tests.get("status") != "passed" or not _nonempty_strings(
        tests.get("evidenceIds")
    ):
        blockers.append("tests-incomplete")

    approval = candidate.get("ownerApproval", {})
    if not (
        approval.get("status") == "approved"
        and isinstance(approval.get("receiptId"), str)
        and approval.get("receiptId")
    ):
        blockers.append("owner-approval-missing")

    return {
        "decision": "blocked" if blockers else "mechanism-eligible",
        "blockers": blockers,
        "executionAuthorized": False,
        "claimBoundary": "synthetic-gate-mechanism-only",
    }


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _mutation_cases(candidate: dict[str, Any]) -> list[tuple[str, dict[str, Any], str]]:
    cases: list[tuple[str, dict[str, Any], str]] = []

    mutated = copy.deepcopy(candidate)
    mutated["originClass"] = "third-party-candidate"
    cases.append(("wrong-origin-class", mutated, "wrong-origin-class"))

    mutated = copy.deepcopy(candidate)
    mutated["incumbentExemptionRequested"] = True
    cases.append(
        ("incumbent-exemption", mutated, "incumbent-exemption-forbidden")
    )

    mutated = copy.deepcopy(candidate)
    mutated["residualGap"]["status"] = "not-supported"
    cases.append(("residual-gap-status", mutated, "residual-gap-not-supported"))

    mutated = copy.deepcopy(candidate)
    mutated["residualGap"]["reproductionEvidenceIds"] = []
    cases.append(
        ("residual-gap-evidence", mutated, "residual-gap-evidence-incomplete")
    )

    for route in REQUIRED_ALTERNATIVE_ROUTES:
        mutated = copy.deepcopy(candidate)
        mutated["alternatives"][route]["status"] = "viable"
        cases.append(
            (
                f"alternative-{route}",
                mutated,
                f"alternative-not-exhausted:{route}",
            )
        )

    scalar_cases = (
        (
            "design-provenance",
            ("designProvenance", "repositoryOwned"),
            False,
            "design-provenance-incomplete",
        ),
        (
            "license-ownership",
            ("licenseOwnership", "confirmed"),
            False,
            "license-ownership-unconfirmed",
        ),
        (
            "security-review",
            ("reviews", "security", "status"),
            "pending",
            "security-review-incomplete",
        ),
        (
            "portability-review",
            ("reviews", "portability", "status"),
            "pending",
            "portability-review-incomplete",
        ),
        (
            "overlap-review",
            ("reviews", "overlap", "status"),
            "pending",
            "overlap-review-incomplete",
        ),
        ("tests", ("tests", "status"), "pending", "tests-incomplete"),
        (
            "owner-approval",
            ("ownerApproval", "status"),
            "pending",
            "owner-approval-missing",
        ),
    )
    for case_id, path, replacement, blocker in scalar_cases:
        mutated = copy.deepcopy(candidate)
        target = mutated
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = replacement
        cases.append((case_id, mutated, blocker))
    return cases


def validate_gate_record(
    record: dict[str, Any],
    *,
    program: dict[str, Any],
    acceptance: dict[str, Any],
    authority: dict[str, Any],
    projection: dict[str, Any],
    root: Path = ROOT,
) -> None:
    _require(
        record.get("schema") == 1
        and record.get("id") == "repository-authored-gap-fill-gate-v1"
        and record.get("status") == "verified-synthetic-gate-mechanism-only",
        "repository-authored gap-fill gate identity drifted",
    )
    _require(
        record.get("documentation")
        == "docs/strategy/REPOSITORY-AUTHORED-GAP-FILL-GATE-2026-08-06.md"
        and (root / record["documentation"]).is_file(),
        "repository-authored gap-fill documentation binding drifted",
    )
    expected_sources = {
        "programPlan": str(PROGRAM_PLAN_PATH).replace("\\", "/"),
        "programAcceptanceMap": str(ACCEPTANCE_PATH).replace("\\", "/"),
        "portfolioAuthority": str(PORTFOLIO_AUTHORITY_PATH).replace("\\", "/"),
        "semanticProjection": str(PROJECTION_PATH).replace("\\", "/"),
    }
    _require(
        record.get("sourceBindings") == expected_sources
        and all((root / path).is_file() for path in expected_sources.values()),
        "repository-authored gap-fill source binding drifted",
    )

    origin_classes = {
        item.get("id"): item
        for item in program.get("candidateOriginPolicy", {}).get("classes", [])
    }
    origin = origin_classes.get("repository-authored-gap-fill-candidate", {})
    _require(
        origin.get("eligibilityGate") == "residual-gap-supported"
        and origin.get("releaseEligible") is False
        and set(origin.get("requiredEvidence", []))
        == {
            "alternative comparison",
            "repeated or important residual-gap evidence",
            "design provenance and license ownership",
            "security, portability, overlap, and tests",
            "owner approval before admission",
        },
        "repository-authored candidate-origin policy drifted",
    )
    sequence_gates = {
        item.get("id"): item for item in program.get("sequenceGates", [])
    }
    _require(
        sequence_gates.get("gate.residual-gap-before-repository-authoring", {}).get(
            "prerequisite"
        )
        == "residual-gap-supported",
        "repository-authored sequence gate drifted",
    )

    criteria = {
        item.get("id"): item
        for item in acceptance.get("acceptanceCriteria", [])
        if isinstance(item, dict)
    }
    criterion = criteria.get("acceptance.repository-authored-gap-fill-gate", {})
    _require(
        criterion.get("assessment") == "verified"
        and criterion.get("verificationIds")
        == ["verification.repository-authored-gap-fill"]
        and "evidence.repository-authored-gap-fill-gate-2026-08-06"
        in criterion.get("evidenceIds", [])
        and "non-executable candidate" in criterion.get("statement", ""),
        "repository-authored acceptance binding drifted",
    )
    _require(
        authority.get("selfAuthoredBoundary", {}).get("residualGapRequired") is True
        and projection.get("schedulerLanes", {})
        .get("repositoryAuthoredGapFill", {})
        .get("requiresResidualGapEvidence")
        is True,
        "repository-authored authority or projection drifted",
    )

    seam = record.get("publicSeam", {})
    _require(
        seam.get("evaluator")
        == "scripts/evaluate_repository_authored_gap_fill_candidate.py"
        and seam.get("test") == "tests/test_repository_authored_gap_fill_gate.py"
        and seam.get("mode") == "pure-zero-model-no-capability-execution",
        "repository-authored public seam drifted",
    )
    fixture = record.get("syntheticFixture", {})
    candidate = fixture.get("candidate", {})
    _require(
        fixture.get("declaredSynthetic") is True
        and fixture.get("realTaskOrCandidateRepresented") is False
        and str(candidate.get("id", "")).startswith("synthetic-")
        and not {"payloadPath", "installer", "command"}.intersection(candidate),
        "repository-authored synthetic fixture boundary drifted",
    )
    _require(
        evaluate_candidate(candidate) == fixture.get("expectedDecision"),
        "repository-authored positive fixture drifted",
    )

    mutations = _mutation_cases(candidate)
    _require(
        tuple(record.get("failureInjectionCaseIds", [])) == MUTATION_CASE_IDS
        and tuple(case_id for case_id, _, _ in mutations) == MUTATION_CASE_IDS,
        "repository-authored mutation ledger drifted",
    )
    for case_id, mutated, blocker in mutations:
        decision = evaluate_candidate(mutated)
        _require(
            decision.get("decision") == "blocked"
            and decision.get("executionAuthorized") is False
            and blocker in decision.get("blockers", []),
            f"repository-authored mutation did not fail closed: {case_id}",
        )

    claims = record.get("claimBoundary", {})
    _require(
        claims.get("provesFailClosedGateMechanism") is True
        and all(
            claims.get(key) is False
            for key in (
                "provesRealResidualGap",
                "provesCandidateNeed",
                "provesCandidateBehavior",
                "provesCandidateValue",
                "provesPortability",
                "provesProductionReadiness",
            )
        ),
        "repository-authored claim boundary drifted",
    )
    _require(
        record.get("authorityBoundary")
        and all(value is False for value in record["authorityBoundary"].values()),
        "repository-authored authority boundary expanded",
    )


def validate_repository_gate(root: Path = ROOT) -> dict[str, Any]:
    record = json.loads((root / GATE_PATH).read_text(encoding="utf-8"))
    validate_gate_record(
        record,
        program=json.loads((root / PROGRAM_PLAN_PATH).read_text(encoding="utf-8")),
        acceptance=json.loads((root / ACCEPTANCE_PATH).read_text(encoding="utf-8")),
        authority=json.loads(
            (root / PORTFOLIO_AUTHORITY_PATH).read_text(encoding="utf-8")
        ),
        projection=json.loads((root / PROJECTION_PATH).read_text(encoding="utf-8")),
        root=root,
    )
    return record


def main() -> int:
    validate_repository_gate()
    print("Repository-authored gap-fill gate validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
