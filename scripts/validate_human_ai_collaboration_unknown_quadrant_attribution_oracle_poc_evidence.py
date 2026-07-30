#!/usr/bin/env python3
"""Validate the deterministic unknown-quadrant attribution-oracle PoC."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

try:
    from scripts.evaluate_human_ai_collaboration_unknown_quadrant_attribution import (
        evaluate_fixture_document,
    )
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from evaluate_human_ai_collaboration_unknown_quadrant_attribution import (
        evaluate_fixture_document,
    )


ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_PATH = (
    "registry/human-ai-collaboration-unknown-quadrant-attribution-"
    "oracle-poc-evidence-2026-07-27.json"
)
DOCUMENTATION_PATH = (
    "docs/strategy/HUMAN-AI-COLLABORATION-UNKNOWN-QUADRANT-"
    "ATTRIBUTION-ORACLE-POC-EVIDENCE-2026-07-27.md"
)
FIXTURE_PATH = (
    "tests/fixtures/human-ai-collaboration-unknown-quadrant-"
    "attribution-fixtures-2026-07-27.json"
)
EXPECTED_SOURCE_PATHS = {
    "registry/human-ai-collaboration-unknown-quadrant-process-fidelity-mapping-2026-07-27.json",
    "registry/human-ai-collaboration-tdd-current-self-authored-treatment-gap-audit-2026-07-27.json",
    "registry/skill-ecosystem-current-evidence-reconciliation-2026-07-27.json",
    FIXTURE_PATH,
    "scripts/evaluate_human_ai_collaboration_unknown_quadrant_attribution.py",
}
EXPECTED_CASE_COUNTS = {
    "known-knowns": 3,
    "known-unknowns": 2,
    "unknown-knowns": 3,
    "unknown-unknowns": 3,
    "method-attribution": 6,
    "weak-route": 2,
    "residual-gap": 3,
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
        == "human-ai-collaboration-unknown-quadrant-attribution-oracle-"
        "poc-evidence-2026-07-27",
        "evidence identity drifted",
    )
    _require(
        document.get("status")
        == "deterministic-zero-model-oracle-poc-validated-no-live-"
        "treatment-evidence",
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

    fixture = _load(root, FIXTURE_PATH)
    _require(
        fixture.get("status") == "deterministic-zero-model-fixtures",
        "fixture status drifted",
    )
    candidates = {
        item["id"]: item for item in fixture.get("candidateClasses", [])
    }
    _require(
        set(candidates)
        == {
            "native",
            "matt.current",
            "superpowers.6.2.0",
            "self.phase-controls",
        },
        "candidate class set drifted",
    )
    _require(
        candidates["matt.current"].get("methodTreatment") is True
        and candidates["superpowers.6.2.0"].get("methodTreatment") is True
        and candidates["native"].get("methodTreatment") is False
        and candidates["self.phase-controls"].get("methodTreatment") is False,
        "candidate treatment classification drifted",
    )
    hard = fixture.get("hardStandardBoundary", {})
    _require(
        hard.get("sameAcrossArms") is True
        and hard.get("candidateCreditAllowed") is False
        and hard.get("terminalCorrectnessCannotRescueProcessLoss") is True,
        "fixture hard-standard boundary drifted",
    )

    results = evaluate_fixture_document(fixture)
    mismatches = [
        item for item in results if item["actual"] != item["expected"]
    ]
    case_counts: dict[str, int] = {}
    for item in fixture.get("fixtures", []):
        case = str(item.get("facts", {}).get("case", ""))
        case_counts[case] = case_counts.get(case, 0) + 1
    result = document.get("fixtureResult", {})
    _require(
        len(results) == 22
        and not mismatches
        and result.get("fixtureCount") == 22
        and result.get("matchedExpectedCount") == 22
        and result.get("mismatchCount") == 0
        and result.get("caseCounts") == EXPECTED_CASE_COUNTS
        and case_counts == EXPECTED_CASE_COUNTS,
        "fixture result drifted",
    )
    _require(
        result.get("zeroModel") is True
        and result.get("zeroSkillInvocation") is True
        and result.get("zeroExternalAccess") is True,
        "fixture execution classification drifted",
    )

    attribution = document.get("attributionContract", {})
    _require(
        attribution.get("hardStandardInterceptionCanCreditMethod") is False
        and attribution.get("multipleUnisolatedMethodsCanBeAttributed") is False
        and attribution.get("phaseControlsCanBeRelabelledAsDomainMethod")
        is False
        and attribution.get("runnerOrLedgerCanBeCreditedAsMethodValue") is False
        and attribution.get("terminalCorrectnessCanRescueProcessLoss") is False
        and attribution.get("singleObservedRunProvesNetValue") is False
        and attribution.get("sourceOrPayloadPresenceProvesInvocation") is False
        and attribution.get(
            "candidateInvocationAndPrivateOracleAndProcessFidelityRequired"
        )
        is True,
        "method-attribution firewall drifted",
    )
    weak = document.get("weakRouteContract", {})
    _require(
        weak.get("primaryWeakAcceptanceModel") == "gpt-5.3-codex-spark"
        and weak.get("primaryWeakAcceptanceReasoning") == "low"
        and weak.get("freshHostRouteReceiptRequired") is True
        and weak.get("lunaLowRole")
        == "capacity-diagnostic-only-after-named-weak-failure"
        and weak.get("routeObservationAloneProvesCandidateValue") is False,
        "weak-route boundary drifted",
    )
    residual = document.get("residualGapContract", {})
    _require(
        residual.get("eligibleExternalCandidateEvaluationRequired") is True
        and residual.get("minimumIndependentWeakMethodFailureCount") == 3
        and residual.get("methodSpecificFailureRequired") is True
        and residual.get(
            "hardStandardOrInfrastructureFailureCountsAsResidualMethodGap"
        )
        is False
        and residual.get("deterministicFixtureFailureCountsAsLiveWeakFailure")
        is False
        and residual.get("thresholdSatisfactionAuthorizesSelfAuthoring")
        is False,
        "residual-gap firewall drifted",
    )

    decision = document.get("decision", {})
    _require(
        decision.get("deterministicOraclePocValidated") is True
        and decision.get("readyForPacketCompatibilityChecks") is True
        and decision.get("readyForLiveWeakDispatch") is False
        and decision.get("liveDispatchAuthorized") is False
        and decision.get("existingHistoricalFixturesMutated") is False
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
        "All 22",
        "Hard standards remain shared controls",
        "Terminal correctness cannot rescue",
        "does not authorize self-authoring",
        "does not authorize live",
    ):
        _require(
            phrase in documentation,
            f"evidence documentation boundary missing: {phrase}",
        )
    for path in NARRATIVE_PATHS:
        narrative = (root / path).read_text(encoding="utf-8")
        _require(
            "unknown-quadrant attribution-oracle PoC" in narrative,
            f"evidence narrative pointer missing: {path}",
        )


def main() -> int:
    validate_evidence(_load(ROOT, EVIDENCE_PATH))
    print(
        "human-ai collaboration unknown-quadrant attribution-oracle PoC "
        "evidence validation passed"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
