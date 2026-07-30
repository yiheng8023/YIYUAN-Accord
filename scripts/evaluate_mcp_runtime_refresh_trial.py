#!/usr/bin/env python3
"""Evaluate deterministic MCP runtime-refresh evidence fixtures.

The evaluator classifies evidence and claim boundaries only. It does not start
an app server, reload configuration, call an MCP, or stop a process.
"""

from __future__ import annotations

from typing import Any


VALID_PROCESS_OWNERSHIP = {"exact", "host-aggregate-only", "unresolved"}


def evaluate_refresh_trial(facts: dict[str, Any]) -> str:
    if not facts.get("hostBound"):
        return "reject-unbound-host"
    if not facts.get("protocolSurfacePinned"):
        return "require-pinned-local-and-official-protocol-surface"
    if facts.get("secretsOrAccountPayloadRead"):
        return "hard-fail-data-boundary-overreach"
    if facts.get("mutationAttempted") and not facts.get("mutationAuthorized"):
        return "hard-fail-unauthorized-runtime-mutation"

    status_invoked = facts.get("statusListInvoked") is True
    reload_invoked = facts.get("reloadInvoked") is True
    dynamic_claim = any(
        facts.get(key) is True
        for key in (
            "midSessionRefreshClaimed",
            "perServerReleaseClaimed",
            "taskEndReleaseClaimed",
            "resourceBenefitClaimed",
        )
    )

    if not status_invoked:
        if dynamic_claim or reload_invoked:
            return "fail-static-interface-promoted-to-live-behavior"
        return "recorded-static-refresh-interface-only"

    if not facts.get("appServerStartupAuthorized"):
        return "hard-fail-unauthorized-app-server-start"
    if not facts.get("statusBeforeRecorded"):
        return "fail-missing-pre-refresh-status"

    ownership = facts.get("processOwnershipState")
    if ownership not in VALID_PROCESS_OWNERSHIP:
        raise ValueError(f"unsupported process ownership state: {ownership}")

    if not reload_invoked:
        if dynamic_claim:
            return "fail-status-snapshot-promoted-to-refresh-or-release"
        return "observed-read-only-status-snapshot"

    if not facts.get("reloadAuthorized"):
        return "hard-fail-unauthorized-runtime-mutation"
    if not facts.get("actualReloadMethodRecorded") or not facts.get("statusAfterRecorded"):
        return "fail-incomplete-refresh-transition-evidence"
    if facts.get("configurationChanged"):
        if not facts.get("exactPreStateRecorded") or not facts.get("restorationVerified"):
            return "fail-configuration-restoration-unverified"

    if facts.get("midSessionRefreshClaimed") and not facts.get("toolSurfaceDeltaObserved"):
        return "fail-runtime-refresh-claim-unobserved"
    if facts.get("perServerReleaseClaimed") and ownership != "exact":
        return "fail-per-server-release-ownership-unproved"
    if facts.get("perServerReleaseClaimed") and not facts.get("oldRuntimeReleaseObserved"):
        return "fail-old-runtime-release-unobserved"
    if facts.get("taskEndReleaseClaimed") and not facts.get("taskEndTriggerObserved"):
        return "fail-task-end-release-overclaim"
    if facts.get("resourceBenefitClaimed"):
        if (
            facts.get("resourceRepeatCount", 0) < 2
            or not facts.get("stableResourceDeltaObserved")
        ):
            return "fail-resource-benefit-not-repeatable"
    if facts.get("resourceSavingsGeneralized"):
        return "fail-resource-savings-generalization"

    if facts.get("perServerReleaseClaimed"):
        return "observed-refresh-and-owned-release-single-host"
    return "observed-runtime-refresh-release-still-unknown"


def evaluate_fixture_document(document: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {
            "id": fixture["id"],
            "expected": fixture["expected"],
            "actual": evaluate_refresh_trial(fixture["facts"]),
        }
        for fixture in document["fixtures"]
    ]
