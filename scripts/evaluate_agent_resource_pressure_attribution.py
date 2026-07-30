#!/usr/bin/env python3
"""Evaluate synthetic Agent resource-pressure attribution records.

This module is deliberately side-effect free. It does not inspect a live host,
start or stop a thread, worker, MCP server, connection, subscription, or
process, and it never promotes an offline record into live causation evidence.
"""

from __future__ import annotations

from typing import Any


RESOURCE_TYPES = {
    "context",
    "active-turn",
    "loaded-thread",
    "persisted-thread",
    "subagent-worker",
    "mcp-connection",
    "mcp-subscription",
    "child-process",
    "host-cache-renderer",
}

METRIC_CLASSES = {
    "context-size",
    "cpu",
    "memory",
    "process-count",
    "handle-count",
    "connection-count",
    "subscription-count",
    "worker-count",
    "loaded-thread-count",
    "host-cache-size",
}


def _bool(facts: dict[str, Any], name: str) -> bool:
    value = facts.get(name)
    if not isinstance(value, bool):
        raise ValueError(f"{name} must be a boolean")
    return value


def _result(
    classification: str,
    *,
    route: str,
    pressure_attribution_eligible: bool = False,
    release_attribution_eligible: bool = False,
    autonomous_action_eligible: bool = False,
    requires_user_decision: bool = False,
) -> dict[str, Any]:
    return {
        "classification": classification,
        "route": route,
        "pressureAttributionEligible": pressure_attribution_eligible,
        "releaseAttributionEligible": release_attribution_eligible,
        "autonomousActionEligible": autonomous_action_eligible,
        "requiresUserDecision": requires_user_decision,
        "countsAsLiveHostProof": False,
        "countsAsWeakAgentAcceptance": False,
        "countsAsSelfAuthoredControllerGapEvidence": False,
    }


def _validated_string_set(
    facts: dict[str, Any],
    name: str,
    allowed: set[str],
) -> set[str]:
    raw = facts.get(name)
    if not isinstance(raw, list) or not raw or any(
        not isinstance(item, str) or not item for item in raw
    ):
        raise ValueError(f"{name} must be a non-empty string list")
    values = set(raw)
    unknown = values - allowed
    if unknown:
        raise ValueError(f"unsupported {name}: {sorted(unknown)}")
    return values


def evaluate_resource_pressure_attribution(
    facts: dict[str, Any],
) -> dict[str, Any]:
    """Return the narrowest supported offline classification."""

    if facts.get("evidenceMode") != "synthetic-offline":
        return _result(
            "hard-fail-non-synthetic-evidence-mode",
            route="stop",
        )

    if _bool(facts, "liveHostClaimed"):
        return _result(
            "hard-fail-synthetic-record-promoted-to-live-host-proof",
            route="stop",
        )
    if _bool(facts, "actionExecuted"):
        return _result(
            "hard-fail-offline-contract-claimed-runtime-actuation",
            route="stop",
        )
    if _bool(facts, "selfAuthoredControllerJustified"):
        return _result(
            "hard-fail-offline-contract-claimed-self-authored-gap",
            route="stop",
        )

    if not _bool(facts, "scenarioBound"):
        return _result("reject-unbound-resource-scenario", route="ask-intake")
    if not _bool(facts, "hostProfilePinned"):
        return _result("reject-unpinned-host-profile", route="observe-only")
    if not _bool(facts, "workloadProfilePinned"):
        return _result("reject-unpinned-workload-profile", route="observe-only")

    resource_types = _validated_string_set(
        facts,
        "candidateResourceTypes",
        RESOURCE_TYPES,
    )
    _validated_string_set(facts, "metricClassesRecorded", METRIC_CLASSES)

    if _bool(facts, "colloquialZombieThreadCollapsedToSingleState"):
        return _result(
            "reject-zombie-thread-as-single-runtime-state",
            route="observe-only",
        )
    if not _bool(facts, "exactResourceIdentityRecorded"):
        return _result(
            "fail-attribution-without-exact-resource-identity",
            route="observe-only",
        )
    if not _bool(facts, "ownerOrLeaseRecorded"):
        return _result(
            "fail-attribution-without-owner-or-lease",
            route="observe-only",
        )
    if not _bool(facts, "lifecycleStatesSeparated"):
        return _result(
            "fail-attribution-with-merged-lifecycle-states",
            route="observe-only",
        )
    if not _bool(facts, "metricAvailabilityDeclared"):
        return _result(
            "fail-attribution-without-metric-availability-declaration",
            route="observe-only",
        )

    if not _bool(facts, "hostObservabilitySufficient"):
        return _result(
            "advisory-only-host-observability-insufficient",
            route="advisory-only",
        )

    if not _bool(facts, "timeSeriesRecorded"):
        return _result(
            "fail-attribution-without-time-series",
            route="observe-only",
        )
    if not _bool(facts, "lifecycleInventoryRecorded"):
        return _result(
            "fail-attribution-without-lifecycle-inventory",
            route="observe-only",
        )
    if not _bool(facts, "measurementUnitsBound"):
        return _result(
            "fail-attribution-without-bound-measurement-units",
            route="observe-only",
        )
    if not _bool(facts, "sampleWindowBounded"):
        return _result(
            "fail-attribution-without-bounded-sample-window",
            route="observe-only",
        )
    repeat_count = facts.get("repeatCount")
    if not isinstance(repeat_count, int) or isinstance(repeat_count, bool):
        raise ValueError("repeatCount must be an integer")
    if repeat_count < 3:
        return _result(
            "fail-attribution-without-three-repeats",
            route="observe-only",
        )
    if not _bool(facts, "idleControlRecorded"):
        return _result(
            "fail-attribution-without-idle-control",
            route="observe-only",
        )
    if not _bool(facts, "concurrentArmRecorded"):
        return _result(
            "fail-attribution-without-concurrent-arm",
            route="observe-only",
        )
    if not _bool(facts, "cancellationArmRecorded"):
        return _result(
            "fail-attribution-without-cancellation-arm",
            route="observe-only",
        )
    if not _bool(facts, "releaseLatencyRecorded"):
        return _result(
            "fail-attribution-without-release-latency",
            route="observe-only",
        )

    pressure_claimed = _bool(facts, "pressureAttributionClaimed")
    release_claimed = _bool(facts, "releaseAttributionClaimed")
    autonomous_requested = _bool(facts, "autonomousActionRequested")

    if pressure_claimed and _bool(facts, "persistedThreadOnlyEvidence"):
        return _result(
            "fail-persisted-thread-count-promoted-to-pressure-cause",
            route="observe-only",
        )

    pressure_eligible = False
    if pressure_claimed:
        if not _bool(facts, "pressureObservedAcrossRepeats"):
            return _result(
                "fail-pressure-claim-without-repeated-observation",
                route="observe-only",
            )
        if not _bool(facts, "candidateResourceDeltaCorrelated"):
            return _result(
                "fail-pressure-claim-without-resource-delta-correlation",
                route="observe-only",
            )
        if not _bool(facts, "confoundersControlled"):
            return _result(
                "fail-pressure-claim-without-confounder-control",
                route="observe-only",
            )
        pressure_eligible = True

    release_eligible = False
    if release_claimed:
        if not pressure_eligible:
            return _result(
                "fail-release-claim-without-pressure-attribution",
                route="observe-only",
            )
        task_complete = _bool(facts, "taskCompleteEventRecorded")
        release_observed = _bool(facts, "resourceReleaseObserved")
        if task_complete and not release_observed:
            return _result(
                "fail-task-completion-promoted-to-resource-release",
                route="observe-only",
                pressure_attribution_eligible=True,
            )
        if not _bool(facts, "releaseActionBound"):
            return _result(
                "fail-release-claim-without-bound-action",
                route="observe-only",
                pressure_attribution_eligible=True,
            )
        if not _bool(facts, "prePostActionStateRecorded"):
            return _result(
                "fail-release-claim-without-pre-post-state",
                route="observe-only",
                pressure_attribution_eligible=True,
            )
        if not _bool(facts, "releaseReceiptRecorded"):
            return _result(
                "fail-release-claim-without-action-receipt",
                route="observe-only",
                pressure_attribution_eligible=True,
            )
        if not release_observed:
            return _result(
                "fail-release-claim-without-observed-release",
                route="observe-only",
                pressure_attribution_eligible=True,
            )
        if _bool(facts, "sharedOwnerConflict"):
            return _result(
                "fail-release-attribution-with-shared-owner-confounder",
                route="ask-user",
                pressure_attribution_eligible=True,
                requires_user_decision=True,
            )
        release_eligible = True

    if autonomous_requested:
        if not pressure_eligible:
            return _result(
                "observe-only-autonomous-action-without-attribution",
                route="observe-only",
            )
        if (
            _bool(facts, "newPermissionRequired")
            or _bool(facts, "sharedOwnerConflict")
            or _bool(facts, "destructiveScope")
            or _bool(facts, "meaningfulCostIncrease")
        ):
            return _result(
                "require-user-decision-for-new-boundary-or-shared-ownership",
                route="ask-user",
                pressure_attribution_eligible=True,
                release_attribution_eligible=release_eligible,
                requires_user_decision=True,
            )
        if not _bool(facts, "existingAuthority"):
            return _result(
                "require-user-decision-existing-authority-missing",
                route="ask-user",
                pressure_attribution_eligible=True,
                release_attribution_eligible=release_eligible,
                requires_user_decision=True,
            )
        if not _bool(facts, "hostActuationAvailable"):
            return _result(
                "advisory-only-host-actuation-unavailable",
                route="advisory-only",
                pressure_attribution_eligible=True,
                release_attribution_eligible=release_eligible,
            )
        if (
            not _bool(facts, "verificationSurfaceBound")
            or not _bool(facts, "actionReversible")
        ):
            return _result(
                "require-user-decision-action-not-safely-verifiable",
                route="ask-user",
                pressure_attribution_eligible=True,
                release_attribution_eligible=release_eligible,
                requires_user_decision=True,
            )
        return _result(
            "synthetic-autonomous-action-eligible-live-actuation-unproven",
            route="autonomous-action-eligible",
            pressure_attribution_eligible=True,
            release_attribution_eligible=release_eligible,
            autonomous_action_eligible=True,
        )

    if release_eligible:
        return _result(
            "synthetic-release-attribution-complete-live-causation-unproven",
            route="observe-only",
            pressure_attribution_eligible=True,
            release_attribution_eligible=True,
        )
    if pressure_eligible:
        return _result(
            "synthetic-pressure-attribution-complete-live-causation-unproven",
            route="observe-only",
            pressure_attribution_eligible=True,
        )
    if resource_types:
        return _result(
            "synthetic-measurement-contract-complete-no-pressure-claim",
            route="observe-only",
        )
    raise AssertionError("validated resource types unexpectedly empty")


def evaluate_fixture_document(document: dict[str, Any]) -> list[dict[str, Any]]:
    defaults = document.get("defaults")
    fixtures = document.get("fixtures")
    if not isinstance(defaults, dict) or not isinstance(fixtures, list):
        raise ValueError("fixture document requires defaults and fixtures")
    results: list[dict[str, Any]] = []
    for fixture in fixtures:
        facts = dict(defaults)
        facts.update(fixture["facts"])
        actual = evaluate_resource_pressure_attribution(facts)
        results.append(
            {
                "id": fixture["id"],
                "expectedClassification": fixture["expectedClassification"],
                "actual": actual,
            }
        )
    return results
