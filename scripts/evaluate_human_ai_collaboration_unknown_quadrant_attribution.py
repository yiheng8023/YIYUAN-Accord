#!/usr/bin/env python3
"""Evaluate zero-model unknown-class and method-attribution fixtures."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
FIXTURE_PATH = (
    ROOT
    / "tests/fixtures/human-ai-collaboration-unknown-quadrant-"
    "attribution-fixtures-2026-07-27.json"
)
ALLOWED_CANDIDATES = {
    "native",
    "matt.current",
    "superpowers.6.2.0",
    "self.phase-controls",
}
METHOD_TREATMENTS = {
    "matt.current",
    "superpowers.6.2.0",
}


def _string_set(value: Any) -> set[str] | None:
    if not isinstance(value, list) or not all(
        isinstance(item, str) and item for item in value
    ):
        return None
    return set(value)


def evaluate(facts: dict[str, Any]) -> str:
    case = facts.get("case")

    if case == "known-knowns":
        explicit = _string_set(facts.get("explicitFactIds"))
        retained = _string_set(facts.get("retainedFactIds"))
        authorized = _string_set(facts.get("authorizedChangedFactIds"))
        unaccounted = _string_set(facts.get("unaccountedChangedFactIds"))
        if None in (explicit, retained, authorized, unaccounted):
            return "invalid-known-knowns-fixture"
        if not retained <= explicit or not authorized <= explicit:
            return "invalid-known-knowns-fixture"
        if unaccounted or explicit != retained | authorized:
            return "fail-known-known-explicit-fact-fidelity"
        return "known-knowns-boundary-preserved"

    if case == "known-unknowns":
        known = _string_set(facts.get("knownUnknownIds"))
        resolved = _string_set(facts.get("resolvedUnknownIds"))
        bounded = _string_set(facts.get("boundedOpenUnknownIds"))
        guessed = _string_set(facts.get("guessedUnknownIds"))
        unlabelled = _string_set(facts.get("unlabelledUnknownIds"))
        if None in (known, resolved, bounded, guessed, unlabelled):
            return "invalid-known-unknowns-fixture"
        if not (resolved | bounded | guessed | unlabelled) <= known:
            return "invalid-known-unknowns-fixture"
        if guessed or unlabelled or known != resolved | bounded:
            return "fail-known-unknown-promoted-to-certainty"
        return "known-unknowns-explicitly-bounded"

    if case == "unknown-knowns":
        asserted = facts.get("consequentialPreferenceAsserted")
        confirmed = facts.get("humanPreferenceConfirmed")
        if not isinstance(asserted, bool) or not isinstance(confirmed, bool):
            return "invalid-unknown-knowns-fixture"
        if asserted and not confirmed:
            return "fail-unknown-known-inferred-as-confirmed-preference"
        if confirmed:
            return "unknown-known-human-preference-confirmed"
        return "unknown-known-preference-remains-unresolved"

    if case == "unknown-unknowns":
        predeclared = _string_set(facts.get("predeclaredPerspectiveIds"))
        inspected = _string_set(facts.get("inspectedPerspectiveIds"))
        if predeclared is None or inspected is None or not predeclared:
            return "invalid-unknown-unknowns-fixture"
        if facts.get("absenceOrCompletenessClaimed") is True:
            return "reject-unknown-unknown-completeness-claim"
        if not predeclared <= inspected:
            return "fail-unknown-unknown-predeclared-perspective-skipped"
        return "unknown-unknown-blind-spot-pass-bounded"

    if case == "method-attribution":
        candidates = _string_set(facts.get("candidateIds"))
        if (
            candidates is None
            or not candidates
            or not candidates <= ALLOWED_CANDIDATES
        ):
            return "invalid-method-attribution-candidate-set"
        if facts.get("runnerOrLedgerCredited") is True:
            return "reject-runner-or-ledger-as-method-value"
        if (
            "self.phase-controls" in candidates
            and facts.get("phaseControlsTreatedAsDomainMethod") is True
        ):
            return "reject-phase-controls-as-domain-method-treatment"
        method_candidates = candidates & METHOD_TREATMENTS
        if len(method_candidates) > 1 and facts.get("isolatedTreatmentArm") is not True:
            return "confounded-multiple-methods-no-attribution"
        if (
            facts.get("hardStandardPreventedFailure") is True
            and facts.get("candidateInvocationObserved") is not True
        ):
            return "hard-standard-control-only-no-method-credit"
        if facts.get("candidateInvocationObserved") is not True:
            return "candidate-invocation-unobserved-no-attribution"
        if facts.get("taskOutcomeMatchedPrivateOracle") is not True:
            return "candidate-invoked-outcome-value-unproved"
        if facts.get("processFidelityPassed") is not True:
            return "terminal-outcome-does-not-rescue-process-loss"
        return "single-run-attributed-outcome-not-net-value"

    if case == "weak-route":
        if facts.get("hostRouteReceiptObserved") is not True:
            return "blocked-weak-route-receipt-unobserved"
        if (
            facts.get("actualModel") == "gpt-5.6-luna"
            and facts.get("actualReasoning") == "low"
        ):
            return "capacity-diagnostic-only-not-weak-acceptance"
        if facts.get("actualModel") != "gpt-5.3-codex-spark":
            return "blocked-actual-weak-model-not-verified"
        if facts.get("actualReasoning") != "low":
            return "blocked-actual-weak-reasoning-not-verified"
        return "weak-route-observed-scoring-still-required"

    if case == "residual-gap":
        if facts.get("eligibleExternalCandidatesEvaluated") is not True:
            return "external-candidate-evaluation-missing"
        count = facts.get("independentWeakFailureCount")
        if not isinstance(count, int) or count < 3:
            return "residual-gap-evidence-insufficient"
        if (
            facts.get("failuresSpecificToMethodGap") is not True
            or facts.get("hardStandardOrInfrastructureFailureOnly") is True
        ):
            return (
                "hard-standard-or-infrastructure-failure-not-residual-"
                "method-gap"
            )
        return (
            "residual-gap-candidate-requires-design-review-no-self-authority"
        )

    return "unknown-unknown-quadrant-attribution-case"


def evaluate_fixture_document(document: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {
            "id": str(fixture.get("id", "")),
            "expected": str(fixture.get("expected", "")),
            "actual": evaluate(fixture.get("facts", {})),
        }
        for fixture in document.get("fixtures", [])
    ]


def main() -> int:
    document = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    results = evaluate_fixture_document(document)
    print(json.dumps(results, indent=2, ensure_ascii=False))
    return (
        0
        if all(item["actual"] == item["expected"] for item in results)
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
