#!/usr/bin/env python3
"""Classify offline MCP task-lifecycle evidence contracts.

This module deliberately evaluates only synthetic, side-effect-free records.
It never starts a host or MCP server, reads process state, or upgrades a
synthetic contract into a live-host claim.
"""

from __future__ import annotations

from typing import Any


REQUIRED_DIMENSIONS = {
    "lease",
    "referenceCount",
    "taskEndExit",
    "duplicateIdentity",
    "crashRecovery",
    "resourceControl",
    "sameSessionSwitching",
}


def _result(classification: str) -> dict[str, Any]:
    return {
        "classification": classification,
        "countsAsLiveHostProof": False,
        "countsAsWeakAgentAcceptance": False,
    }


def _evaluate_lease_reference_trace(trace: object) -> str | None:
    """Validate one synthetic multi-task lease/reference-count event trace."""
    if not isinstance(trace, list) or not trace:
        return "fail-lease-reference-trace-missing"

    active: dict[str, str] = {}
    acquired: set[str] = set()
    tasks: set[str] = set()
    maximum_active = 0
    server_released = False

    for raw_event in trace:
        if not isinstance(raw_event, dict):
            return "fail-lease-reference-trace-malformed"
        event = raw_event.get("event")
        if server_released:
            return "fail-lease-reference-trace-event-after-server-release"

        if event == "acquire":
            allowed = {"event", "taskId", "leaseId", "parentTaskId"}
            if set(raw_event) - allowed:
                return "fail-lease-reference-trace-malformed"
            task_id = raw_event.get("taskId")
            lease_id = raw_event.get("leaseId")
            parent_task_id = raw_event.get("parentTaskId")
            if (
                not isinstance(task_id, str)
                or not task_id
                or not isinstance(lease_id, str)
                or not lease_id
                or (
                    parent_task_id is not None
                    and (not isinstance(parent_task_id, str) or not parent_task_id)
                )
            ):
                return "fail-lease-reference-trace-malformed"
            if lease_id in acquired:
                return "fail-lease-reference-trace-duplicate-acquire"
            acquired.add(lease_id)
            active[lease_id] = task_id
            tasks.add(task_id)
            maximum_active = max(maximum_active, len(active))
            continue

        if event == "release":
            if set(raw_event) != {"event", "taskId", "leaseId", "reason"}:
                return "fail-lease-reference-trace-malformed"
            task_id = raw_event.get("taskId")
            lease_id = raw_event.get("leaseId")
            reason = raw_event.get("reason")
            if (
                not isinstance(task_id, str)
                or not task_id
                or not isinstance(lease_id, str)
                or not lease_id
                or reason not in {"task-complete", "task-cancelled", "task-failed"}
            ):
                return "fail-lease-reference-trace-malformed"
            if lease_id not in acquired:
                return "fail-lease-reference-trace-unknown-release"
            if lease_id not in active:
                return "fail-lease-reference-trace-double-release"
            if active[lease_id] != task_id:
                return "fail-lease-reference-trace-cross-task-release"
            del active[lease_id]
            continue

        if event == "server-release":
            if set(raw_event) != {"event"}:
                return "fail-lease-reference-trace-malformed"
            if active:
                return "fail-lease-reference-trace-premature-server-release"
            server_released = True
            continue

        return "fail-lease-reference-trace-malformed"

    if active:
        return "fail-lease-reference-trace-leaked-lease"
    if not server_released:
        return "fail-lease-reference-trace-final-server-release-missing"
    if len(tasks) < 2 or maximum_active < 2:
        return "fail-lease-reference-trace-no-overlapping-tasks"
    return None


def evaluate_task_lifecycle_evidence(facts: dict[str, Any]) -> dict[str, Any]:
    """Return the narrowest supported classification for one offline record."""
    if facts.get("evidenceMode") != "synthetic-offline":
        return _result("hard-fail-non-synthetic-evidence-mode")
    if facts.get("hostOrMcpStarted"):
        return _result("hard-fail-offline-contract-started-host-or-mcp")
    if facts.get("hostStateRead") or facts.get("processStateRead"):
        return _result("hard-fail-offline-contract-read-live-state")
    if facts.get("liveHostClaimed") or facts.get("weakAgentAcceptanceClaimed"):
        return _result("fail-synthetic-evidence-promoted-to-live-claim")
    if not facts.get("scenarioBound"):
        return _result("reject-unbound-task-scenario")
    if not facts.get("evidenceSchemaPinned"):
        return _result("require-pinned-lifecycle-evidence-schema")

    requested = set(facts.get("claimedDimensions", []))
    unknown = requested - REQUIRED_DIMENSIONS
    if unknown:
        raise ValueError(f"unsupported lifecycle dimensions: {sorted(unknown)}")
    if not requested:
        return _result("synthetic-contract-recorded-no-lifecycle-claim")

    if "lease" in requested:
        if not facts.get("exactTaskIdentityRecorded"):
            return _result("fail-lease-without-exact-task-identity")
        if not facts.get("leaseAcquireEventRecorded") or not facts.get("leaseReleaseEventRecorded"):
            return _result("fail-lease-transition-incomplete")
        if not facts.get("leaseEventOrderValidated"):
            return _result("fail-lease-event-order-unvalidated")
    if "referenceCount" in requested:
        if not facts.get("exactTaskIdentityRecorded"):
            return _result("fail-reference-count-without-exact-task-identity")
        if not facts.get("concurrentAcquireReleaseTraceRecorded"):
            return _result("fail-reference-count-without-concurrent-trace")
        if not facts.get("underflowAndDoubleReleaseCasesCovered"):
            return _result("fail-reference-count-without-negative-cases")
        if not facts.get("referenceCountTraceEndsAtZero"):
            return _result("fail-reference-count-without-zero-terminal-state")
    if requested & {"lease", "referenceCount"}:
        trace_failure = _evaluate_lease_reference_trace(
            facts.get("leaseReferenceTrace")
        )
        if trace_failure is not None:
            return _result(trace_failure)
    if "taskEndExit" in requested:
        if not facts.get("exactTaskIdentityRecorded"):
            return _result("fail-task-end-exit-without-exact-task-identity")
        if (
            not facts.get("taskEndEventRecorded")
            or not facts.get("finalLeaseReleaseEventRecorded")
            or not facts.get("exactExitEventRecorded")
        ):
            return _result("fail-task-end-exit-transition-incomplete")
        if not facts.get("taskEndReleaseExitOrderValidated"):
            return _result("fail-task-end-release-exit-order-unvalidated")
        if not facts.get("referenceCountZeroBeforeExitRecorded"):
            return _result("fail-task-end-exit-without-zero-reference-count")
    if "duplicateIdentity" in requested:
        if not facts.get("exactMcpInstanceIdentityRecorded"):
            return _result("fail-duplicate-control-without-exact-mcp-identity")
        if not facts.get("concurrentInstanceWindowRecorded"):
            return _result("fail-duplicate-control-without-concurrent-window")
        if not facts.get("duplicateAttemptTraceRecorded"):
            return _result("fail-duplicate-control-without-duplicate-attempt-trace")
        if not facts.get("identityCollisionOutcomeRecorded"):
            return _result("fail-duplicate-control-without-collision-outcome")
    if "crashRecovery" in requested:
        if not facts.get("faultClassDeclared"):
            return _result("fail-crash-recovery-without-fault-class")
        if not facts.get("preFaultExactIdentityRecorded") or not facts.get("postFaultExactIdentityRecorded"):
            return _result("fail-crash-recovery-without-pre-post-identity")
        if not facts.get("sameThreadRecoveryOutcomeRecorded"):
            return _result("fail-crash-recovery-without-same-thread-outcome")
        if not facts.get("recoveryFallbackDeclared"):
            return _result("fail-crash-recovery-without-bounded-fallback")
    if "resourceControl" in requested:
        if facts.get("resourceRepeatCount", 0) < 2:
            return _result("fail-resource-control-without-repeat")
        if not facts.get("resourceBaselineAndPostStateRecorded"):
            return _result("fail-resource-control-without-baseline-and-post-state")
        if not facts.get("resourceMetricScopeBounded"):
            return _result("fail-resource-control-without-bounded-metric-scope")
        if not facts.get("controlWorkloadRecorded"):
            return _result("fail-resource-control-without-control-workload")
        if not facts.get("resourceSampleWindowBounded"):
            return _result("fail-resource-control-without-bounded-sample-window")
    if "sameSessionSwitching" in requested:
        if not facts.get("exactSameThreadIdentityRecorded"):
            return _result("fail-same-session-switching-without-exact-thread")
        if not facts.get("baselineAndPostDirectCallRecorded"):
            return _result("fail-same-session-switching-without-direct-call-pair")
        if not facts.get("activeTurnBetweenCallsRecorded"):
            return _result("fail-same-session-switching-without-active-turn")
        if not facts.get("sameSessionRefreshEvidencePacketRecorded"):
            return _result("fail-same-session-switching-without-evidence-packet")

    return _result("synthetic-lifecycle-contract-complete-live-claims-unproven")


def evaluate_fixture_document(document: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "id": fixture["id"],
            "expected": fixture["expected"],
            "actual": evaluate_task_lifecycle_evidence(fixture["facts"]),
        }
        for fixture in document["fixtures"]
    ]
