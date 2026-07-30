#!/usr/bin/env python3
"""Validate the bounded Codex Desktop resource-observability preflight."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_PATH = (
    ROOT / "registry/codex-desktop-resource-observability-preflight-2026-07-31.json"
)
DOCUMENT_PATH = (
    ROOT / "docs/strategy/CODEX-DESKTOP-RESOURCE-OBSERVABILITY-PREFLIGHT-2026-07-31.md"
)
PROGRAM_MAP_PATH = ROOT / "registry/program-acceptance-map.json"
EVIDENCE_ID = "evidence.codex-desktop-resource-observability-preflight-2026-07-31"
ACCEPTANCE_ID = "acceptance.dynamic-runtime-control-gap-research"


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_preflight(
    evidence: dict[str, Any] | None = None,
    *,
    root: Path = ROOT,
    program_map: dict[str, Any] | None = None,
) -> None:
    evidence = evidence or _load(
        root
        / "registry/codex-desktop-resource-observability-preflight-2026-07-31.json"
    )
    program_map = program_map or _load(root / "registry/program-acceptance-map.json")

    _require(evidence.get("schema") == 1, "Evidence schema drifted")
    _require(
        evidence.get("status")
        == (
            "observed-live-read-only-single-host-desktop-resource-observability-"
            "owner-attribution-blocked-no-actuation"
        ),
        "Evidence status drifted",
    )

    host = evidence.get("hostBinding", {})
    _require(
        host.get("surface") == "Codex Desktop"
        and host.get("codexCliVersion") == "codex-cli 0.146.0"
        and host.get("repositoryHead")
        == "db8078e9b5686c4d7d958184241ceddd64dab592",
        "Host binding drifted",
    )
    authority = evidence.get("authorityBoundary", {})
    _require(
        authority.get("readOnlyLocalHostObservation") is True,
        "Read-only authority marker drifted",
    )
    for key in (
        "modelTurnStarted",
        "threadCreatedArchivedOrDeleted",
        "mcpEnabledDisabledReloadedOrReconfigured",
        "processStoppedOrRestarted",
        "hookPluginAppOrGlobalConfigChanged",
        "rawCommandLinesRetained",
        "credentialValuesRetained",
        "threadTitlesBodiesOrSummariesRetained",
    ):
        _require(authority.get(key) is False, f"Authority boundary drifted: {key}")

    thread_inventory = evidence.get("threadInventoryObservation", {})
    _require(
        thread_inventory.get("returnedTotalCount") == 60
        and thread_inventory.get("resultTruncatedAtRequestedLimit") is True
        and thread_inventory.get("codex") == {"active": 2, "notLoaded": 18}
        and thread_inventory.get("chatgpt") == {"idle": 40},
        "Thread inventory observation drifted",
    )
    _require(
        thread_inventory.get("provesLoadedRuntimeCount") is False
        and thread_inventory.get("provesThreadToProcessOwnership") is False
        and thread_inventory.get("provesResourceRelease") is False,
        "Thread inventory was promoted beyond its evidence",
    )

    mcp = evidence.get("mcpConfigurationObservation", {})
    _require(
        mcp.get("configuredEntryCount") == 9
        and mcp.get("enabledEntryCount") == 9
        and len(mcp.get("localConfiguredEntries", [])) == 7
        and len(mcp.get("remoteConfiguredEntries", [])) == 2,
        "MCP configuration inventory drifted",
    )
    _require(
        mcp.get("configurationStatusEqualsLoadedRuntime") is False
        and mcp.get("configurationInventoryIsCompletePluginRuntimeInventory")
        is False
        and mcp.get("perEntryProcessOrConnectionOwnershipExposed") is False,
        "MCP configuration was promoted to runtime proof",
    )

    source = evidence.get("officialSourceCorrelation", {})
    _require(
        source.get("repository") == "openai/codex"
        and source.get("codexCliTag") == "rust-v0.146.0"
        and source.get("codexCliTagCommit")
        == "e363b08c9175ac1cbe5893615dd2cb9ddf95043b",
        "Official source pin drifted",
    )
    protocol = source.get("protocolSurfacesAtPinnedCommit", {})
    _require(
        protocol.get("loadedThreadIds") == "thread/loaded/list"
        and protocol.get("threadScopedMcpStartupOwner")
        == "mcpServer/startupStatus/updated.threadId"
        and protocol.get("threadTokenUsage") == "thread/tokenUsage/updated"
        and len(protocol.get("threadBackgroundTerminalActuators", [])) == 3,
        "Official protocol surface inventory drifted",
    )
    implementation = source.get("implementationObservationsAtPinnedCommit", {})
    _require(
        implementation.get("connectionManagerSourceBlob")
        == "2e6be9864f842d56d93535e34597875fc185ce14"
        and implementation.get("connectionManagerHasExplicitShutdown") is True
        and implementation.get("stdioLauncherSourceBlob")
        == "4a2c52a40fb03da30e0c2e2eb7293a918a0e0a6d"
        and implementation.get("stdioChildKillOnDropEnabled") is True,
        "Pinned implementation observation drifted",
    )
    issues = {item.get("number"): item for item in source.get("issueSnapshot", [])}
    _require(
        issues.get(18881, {}).get("state") == "closed"
        and issues.get(18881, {}).get("stateReason") == "completed"
        and issues.get(11324, {}).get("state") == "open"
        and issues.get(17832, {}).get("state") == "open"
        and issues.get(35676, {}).get("state") == "open",
        "Official issue snapshot drifted",
    )
    _require(
        source.get("currentTaskSurfaceExposesLoadedThreadList") is False
        and source.get("currentTaskSurfaceExposesMcpStartupOwnerReceipt") is False
        and source.get("currentTaskSurfaceExposesSubscriberPresence") is False
        and source.get("historicalManagerReplacementIssueAttributionEligible")
        is False
        and source.get("openIssuesCorroborateRiskButDoNotProveLocalCause") is True
        and source.get("officialProtocolReuseMustPrecedeControllerDesign") is True,
        "Official-source interpretation drifted",
    )

    process = evidence.get("processTreeObservation", {})
    samples = process.get("samples", [])
    _require(
        process.get("observerProcessAndDescendantsExcluded") is True
        and process.get("codexRuntimeRootCount") == 1
        and process.get("sampleCount") == 3
        and isinstance(samples, list)
        and len(samples) == 3,
        "Process sample contract drifted",
    )
    _require(
        {item.get("nonObserverProcessCount") for item in samples} == {118}
        and {item.get("tcpConnectionCount") for item in samples} == {34},
        "Stable process or connection observations drifted",
    )
    _require(
        all(
            isinstance(item.get("workingSetBytes"), int)
            and item["workingSetBytes"] > 6_000_000_000
            and isinstance(item.get("privateBytes"), int)
            and item["privateBytes"] > 4_000_000_000
            for item in samples
        ),
        "Measured resource floor drifted",
    )

    classified = process.get("classifiedSnapshot", {})
    roots = classified.get("repeatedRoots", [])
    by_label = {item.get("label"): item for item in roots}
    expected_root_counts = {
        "unclassified-node": 24,
        "playwright": 6,
        "context7": 6,
        "codegraph": 6,
        "neo4j-graph": 6,
        "node-repl": 6,
    }
    _require(
        classified.get("repeatedStartupCohortCount") == 6
        and len(classified.get("cohortAnchorsUtc", [])) == 6
        and {label: by_label[label].get("rootCount") for label in by_label}
        == expected_root_counts,
        "Repeated cohort classification drifted",
    )
    aggregate = classified.get("repeatedCohortAggregate", {})
    aggregate_fields = {
        "directRootCount": "rootCount",
        "processCount": "processCount",
        "workingSetBytes": "workingSetBytes",
        "privateBytes": "privateBytes",
        "handles": "handles",
        "threads": "threads",
    }
    for aggregate_field, root_field in aggregate_fields.items():
        _require(
            aggregate.get(aggregate_field)
            == sum(item.get(root_field, 0) for item in roots),
            f"Repeated cohort aggregate drifted: {aggregate_field}",
        )
    _require(
        aggregate
        == {
            "directRootCount": 54,
            "processCount": 114,
            "workingSetBytes": 5490900992,
            "privateBytes": 3578617856,
            "handles": 22074,
            "threads": 888,
        },
        "Repeated cohort totals drifted",
    )
    _require(
        process.get("workingSetSumMayDoubleCountSharedPages") is True
        and process.get("sampleWindowIsNotAnIdleControl") is True
        and process.get("sampleWindowIsNotAControlledSameWorkloadRepetition")
        is True,
        "Measurement limitations drifted",
    )

    decision = evidence.get("observabilityDecision", {})
    for key in (
        "threadStatusSurfaceAvailable",
        "configuredMcpInventorySurfaceAvailable",
        "processIdentityAndMetricSurfaceAvailable",
        "repeatedRuntimeStartupCohortsObserved",
        "officialProtocolOffersPotentialOwnerInputs",
    ):
        _require(decision.get(key) is True, f"Observed surface drifted: {key}")
    for key in (
        "contextSizeOrCompactionTelemetryAvailable",
        "threadToProcessOwnerOrLeaseMappingObserved",
        "mcpToThreadOwnerOrLeaseMappingObserved",
        "taskCompletionOrCancellationReleaseReceiptObserved",
        "safeTaskScopedRuntimeActuatorObserved",
        "officialProtocolInputsExposedOnCurrentTaskSurface",
        "pressureAttributionEligible",
        "releaseAttributionEligible",
        "autonomousActionEligible",
        "selfAuthoredControllerGapProved",
    ):
        _require(decision.get(key) is False, f"Decision boundary drifted: {key}")

    claims = evidence.get("claimBoundary", {})
    _require(
        isinstance(claims, dict)
        and claims
        and all(value is False for value in claims.values()),
        "Claim boundary must remain entirely negative",
    )

    document = (
        root
        / "docs/strategy/CODEX-DESKTOP-RESOURCE-OBSERVABILITY-PREFLIGHT-2026-07-31.md"
    ).read_text(encoding="utf-8")
    normalized = " ".join(document.split())
    for phrase in (
        "six near-identical startup cohorts",
        "does not prove that six user threads own them",
        "pressure attribution is not eligible",
        "does not justify a self-authored controller",
        "Reusing or exposing those host primitives must precede",
        "No model turn",
    ):
        _require(phrase in normalized, f"Documentation missing: {phrase}")

    acceptances = {
        item.get("id"): item for item in program_map.get("acceptanceCriteria", [])
    }
    _require(ACCEPTANCE_ID in acceptances, "Runtime acceptance is missing")
    _require(
        EVIDENCE_ID in acceptances[ACCEPTANCE_ID].get("evidenceIds", []),
        "Runtime acceptance is not linked to the preflight",
    )
    records = {item.get("id"): item for item in program_map.get("evidence", [])}
    _require(EVIDENCE_ID in records, "Program evidence record is missing")
    _require(
        records[EVIDENCE_ID].get("path")
        == "registry/codex-desktop-resource-observability-preflight-2026-07-31.json",
        "Program evidence path drifted",
    )


def main() -> int:
    validate_preflight()
    print("Codex Desktop resource-observability preflight validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
