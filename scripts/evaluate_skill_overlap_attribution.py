#!/usr/bin/env python3
"""Evaluate deterministic Skill-overlap attribution boundaries.

These fixtures classify evidence sufficiency before any live weak-Agent arm.
They do not execute Skills, create tasks, mutate Agent homes, or infer runtime
behavior from installed files.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
FIXTURE_PATH = (
    ROOT / "tests/fixtures/skill-overlap-attribution-fixtures-2026-07-23.json"
)


def evaluate(facts: dict[str, Any]) -> str:
    case = facts.get("case")

    if case == "arm-design":
        if facts.get("eligibility") == "not-applicable":
            if isinstance(facts.get("notApplicableReason"), str) and facts[
                "notApplicableReason"
            ].strip():
                return "arm-not-applicable-explicit-not-residual-gap"
            return "arm-design-incomplete"
        required = (
            "intervention",
            "payloadIdentity",
            "payloadSha256",
            "hostExposureEvidence",
            "loaderEvidence",
            "triggerMode",
            "triggerBoundary",
            "primaryMetric",
            "sharedControlsNotCredited",
        )
        if any(key not in facts for key in required):
            return "arm-design-incomplete"
        if facts.get("sharedControlsNotCredited") is not True:
            return "arm-design-credits-hard-standard"
        if (
            facts.get("intervention") == "selective-single-skill"
            and facts.get("triggerMode") == "full-bootstrap"
        ):
            return "arm-design-trigger-boundary-conflict"
        if (
            "ask-matt" in str(facts.get("payloadIdentity", "")).lower()
            and facts.get("triggerBoundary") == "cross-ecosystem-top-level"
        ):
            return "arm-design-reject-second-top-level-router-trigger"
        return "arm-design-ready-for-live-packet"

    if case == "skill-value-attribution":
        if facts.get("hardStandardPreventedFailure") is True:
            if facts.get("skillInvocationObserved") is not True:
                return "hard-standard-control-only"
        if facts.get("skillInvocationObserved") is not True:
            if facts.get("agentSelfReportedInvocation") is True:
                return "skill-invocation-unproved-agent-self-report-only"
            if facts.get("payloadPresent") is True:
                return "skill-invocation-unproved-payload-presence-only"
            return "skill-value-unobserved"
        if facts.get("taskOutcomeMatchedPrivateOracle") is not True:
            return "skill-invoked-outcome-value-unproved"
        return "single-run-skill-outcome-observed-not-net-value"

    if case == "handoff":
        if facts.get("hostLoaderEventObserved") is not True:
            return "handoff-invocation-unproved"
        if facts.get("producerEvidenceComplete") is not True:
            return "handoff-producer-evidence-incomplete"
        if facts.get("receiverExecutionObserved") is not True:
            return "handoff-producer-evidence-only"
        if facts.get("receiverPrivateOracleMatched") is not True:
            return "handoff-receiver-quality-failed"
        if (
            facts.get("independentHostRunCount") != 3
            or facts.get("independentHostThreadCount") != 3
        ):
            return "handoff-repetition-insufficient"
        return "handoff-live-arm-observed-not-superiority"

    if case == "router-scope":
        if (
            facts.get("candidate") == "ask-matt"
            and facts.get("scope") == "cross-ecosystem-top-level"
        ):
            return "reject-second-top-level-router"
        if (
            facts.get("candidate") == "ask-matt"
            and facts.get("scope") == "matt-internal-subflow"
        ):
            return "eligible-bounded-matt-subflow"
        if (
            facts.get("candidate") == "superpowers-full-bootstrap"
            and facts.get("nativeTaskSufficient") is True
        ):
            return "separate-full-bootstrap-arm-not-minimal-route"
        return "router-scope-unresolved"

    if case == "closure-scope":
        if (
            facts.get("localEngineeringVerificationPassed") is True
            and facts.get("remoteOrAcceptanceEvidenceMissing") is True
            and facts.get("externalSkillClaimsClosed") is True
        ):
            return "reject-cross-domain-closure-scope-upgrade"
        return "closure-evidence-remains-bounded"

    if case == "git-topology-attribution":
        if (
            facts.get("worktreeOrHookExecuted") is True
            and facts.get("topologyJudgmentObserved") is not True
        ):
            return "execution-does-not-prove-topology-judgment"
        return "topology-attribution-unresolved"

    if case == "weak-condition":
        if (
            facts.get("actualModel") == "gpt-5.6-terra"
            and facts.get("actualReasoning") == "low"
        ):
            return "capacity-diagnostic-only-not-weak-acceptance"
        if facts.get("actualModel") != "gpt-5.3-codex-spark":
            return "blocked-actual-weak-model-not-verified"
        if facts.get("actualReasoning") != "low":
            return "blocked-actual-weak-reasoning-not-verified"
        return "weak-condition-observed-scoring-still-required"

    if case == "residual-gap":
        if facts.get("selfAuthoredExposureState") not in {"absent", "host-disabled"}:
            return "confounded-self-authored-disabled-arm"
        if facts.get("eligibleExternalCandidatePresent") is not True:
            return "candidate-gap-not-residual-capability-gap"
        if facts.get("repeatedWeakAgentFailureObserved") is not True:
            return "live-residual-gap-evidence-missing"
        return "residual-gap-candidate-requires-design-review"

    return "unknown-skill-overlap-attribution-case"


def evaluate_fixture_document(document: dict[str, Any]) -> list[dict[str, str]]:
    results: list[dict[str, str]] = []
    for fixture in document.get("fixtures", []):
        actual = evaluate(fixture.get("facts", {}))
        results.append(
            {
                "id": str(fixture.get("id", "")),
                "expected": str(fixture.get("expected", "")),
                "actual": actual,
            }
        )
    return results


def main() -> int:
    document = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    results = evaluate_fixture_document(document)
    print(json.dumps(results, indent=2, ensure_ascii=False))
    return 0 if all(item["actual"] == item["expected"] for item in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
