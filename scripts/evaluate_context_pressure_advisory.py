#!/usr/bin/env python3
"""Classify offline context-pressure evidence without taking host actions.

This contract is intentionally advisory.  It does not compact context, create
threads, invoke a loader, or claim that one host's signal applies elsewhere.
When a handoff is appropriate, the only follow-on is the existing CTX-04/05
repository-anchored packet and its separately-authorized thread-creation gate.
"""

from __future__ import annotations

from typing import Any


PROVENANCE = {
    "direct-counter",
    "host-event",
    "heuristic",
    "user-observed",
    "unknown",
}


def _require_bool(facts: dict[str, Any], name: str) -> bool:
    value = facts.get(name)
    if not isinstance(value, bool):
        raise ValueError(f"{name} must be a boolean")
    return value


def _hard_failure(facts: dict[str, Any]) -> str | None:
    if _require_bool(facts, "automaticCreationClaimed"):
        return "hard-fail-automatic-thread-creation-claim"
    if _require_bool(facts, "losslessHandoffClaimed"):
        return "hard-fail-lossless-handoff-claim"
    if _require_bool(facts, "crossHostParityClaimed"):
        return "hard-fail-cross-host-parity-claim"
    if _require_bool(facts, "fixedPercentageClaimed"):
        return "hard-fail-fixed-context-percentage-claim"
    if _require_bool(facts, "terraCountsAsWeakAgentAcceptance"):
        return "hard-fail-terra-counted-as-weak-agent-acceptance"
    return None


def evaluate_advisory(facts: dict[str, Any]) -> dict[str, Any]:
    """Return an explainable, side-effect-free advisory decision.

    Required facts deliberately describe observation and authority separately.
    `threadCreationAuthorized` is never inferred from a pressure signal.
    """

    provenance = facts.get("signalProvenance")
    if provenance not in PROVENANCE:
        raise ValueError("signalProvenance is unsupported")

    observed = _require_bool(facts, "signalObserved")
    pressure = _require_bool(facts, "pressureIndicated")
    critical_drift = _require_bool(facts, "criticalFactDriftObserved")
    thread_authorized = _require_bool(facts, "threadCreationAuthorized")
    packet_prepared = _require_bool(facts, "ctx0405PacketPrepared")

    hard_failure = _hard_failure(facts)
    trace = ["OBSERVE"]
    if hard_failure:
        trace.append("UNKNOWN")
        return {
            "state": "UNKNOWN",
            "classification": hard_failure,
            "trace": trace,
            "followOn": "none",
            "countsAsLiveHostProof": False,
            "countsAsWeakAgentAcceptance": False,
        }

    if provenance == "unknown" or not observed:
        trace.append("UNKNOWN")
        return {
            "state": "UNKNOWN",
            "classification": "insufficient-supported-pressure-signal",
            "trace": trace,
            "followOn": "none",
            "countsAsLiveHostProof": False,
            "countsAsWeakAgentAcceptance": False,
        }

    evaluation_state = (
        "EVALUATE" if provenance in {"direct-counter", "host-event"} else "HEURISTIC_EVALUATE"
    )
    trace.append(evaluation_state)
    if critical_drift:
        decision = "REQUIRE_USER_DECISION"
    elif pressure:
        decision = "RECOMMEND_HANDOFF"
    else:
        decision = "CONTINUE"
    trace.append(decision)

    if decision == "CONTINUE":
        return {
            "state": "CONTINUE",
            "classification": "supported-signal-no-advisory-trigger",
            "trace": trace,
            "followOn": "none",
            "countsAsLiveHostProof": False,
            "countsAsWeakAgentAcceptance": False,
        }

    # A pressure signal cannot create a thread.  The authority gate is explicit
    # even when a CTX-04/05 packet has already been prepared.
    if not thread_authorized or not packet_prepared:
        trace.append("WAIT")
        reason = "missing-explicit-thread-authority" if not thread_authorized else "ctx0405-packet-not-prepared"
        return {
            "state": "WAIT",
            "classification": reason,
            "trace": trace,
            "followOn": "prepare-or-use-existing-ctx04-ctx05-packet-only",
            "countsAsLiveHostProof": False,
            "countsAsWeakAgentAcceptance": False,
        }

    trace.append("HANDOFF_PACKET_READY")
    return {
        "state": "HANDOFF_PACKET_READY",
        "classification": "explicit-authority-and-existing-ctx04-ctx05-packet-ready",
        "trace": trace,
        "followOn": "existing-ctx04-ctx05-separately-authorized-live-thread-trial",
        "countsAsLiveHostProof": False,
        "countsAsWeakAgentAcceptance": False,
    }


def evaluate_fixture_document(document: dict[str, Any]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for fixture in document["fixtures"]:
        actual = evaluate_advisory(dict(fixture["facts"]))
        results.append({"id": fixture["id"], "expected": fixture["expected"], "actual": actual})
    return results
