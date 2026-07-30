#!/usr/bin/env python3
"""Validate the Codex Desktop official control-surface access preflight."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_PATH = (
    ROOT
    / "registry/codex-desktop-official-control-surface-access-preflight-2026-07-31.json"
)
DOCUMENT_PATH = (
    ROOT
    / "docs/strategy/CODEX-DESKTOP-OFFICIAL-CONTROL-SURFACE-ACCESS-PREFLIGHT-2026-07-31.md"
)
PROGRAM_MAP_PATH = ROOT / "registry/program-acceptance-map.json"
EVIDENCE_ID = (
    "evidence.codex-desktop-official-control-surface-access-preflight-2026-07-31"
)
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
    evidence = evidence or _load(EVIDENCE_PATH)
    program_map = program_map or _load(PROGRAM_MAP_PATH)

    _require(evidence.get("schema") == 1, "Evidence schema drifted")
    _require(
        evidence.get("status")
        == (
            "observed-local-cli-protocol-schema-current-desktop-attachment-and-"
            "owner-telemetry-unavailable-no-runtime-actuation"
        ),
        "Evidence status drifted",
    )

    host = evidence.get("hostBinding", {})
    _require(
        host.get("codexCliVersion") == "codex-cli 0.146.0"
        and host.get("repositoryHead")
        == "202cf04732272c646be2c8c15bf2bbccb749d113"
        and host.get("priorEvidenceId")
        == "codex-desktop-resource-observability-preflight-2026-07-31",
        "Host binding drifted",
    )

    authority = evidence.get("authorityBoundary", {})
    _require(
        authority.get("localSchemaGenerationOnly") is True,
        "Schema-only authority marker drifted",
    )
    for key in (
        "connectedToDesktopAppServer",
        "newAppServerStarted",
        "modelTurnStarted",
        "threadCreatedResumedForkedUnsubscribedArchivedOrDeleted",
        "mcpProcessOrConnectionStartedStoppedReloadedOrReconfigured",
        "backgroundTerminalStopped",
        "hookPluginAppSkillOrGlobalConfigChanged",
        "rawProcessCommandLinesRetained",
        "threadTitlesBodiesOrSummariesRetained",
    ):
        _require(authority.get(key) is False, f"Authority boundary drifted: {key}")

    probe = evidence.get("localProtocolSchemaProbe", {})
    _require(
        probe.get("generatedFileCount") == 349
        and probe.get("generatedBytes") == 3343741
        and probe.get("nodeProcessCountBefore") == 72
        and probe.get("nodeProcessCountAfter") == 72
        and probe.get("addedNodeProcessCount") == 0
        and probe.get("removedNodeProcessCount") == 0
        and probe.get("temporaryRootRemoved") is True
        and probe.get("emptyTemporaryParentRemoved") is True,
        "Local schema probe drifted",
    )
    digests = probe.get("relevantArtifactDigests", [])
    _require(
        len(digests) == 7
        and len({item.get("path") for item in digests}) == 7
        and all(
            isinstance(item.get("sha256"), str) and len(item["sha256"]) == 64
            for item in digests
        ),
        "Schema digest inventory drifted",
    )

    protocol = evidence.get("protocolCapabilityObservation", {})
    _require(
        protocol.get("loadedThreadInventory", {}).get("method")
        == "thread/loaded/list"
        and protocol.get("threadScopedMcpInventory", {}).get("method")
        == "mcpServerStatus/list"
        and protocol.get("threadScopedMcpInventory", {}).get(
            "requestAcceptsNullableThreadId"
        )
        is True
        and protocol.get("threadScopedMcpStartupReceipt", {}).get(
            "containsNullableThreadId"
        )
        is True
        and protocol.get("contextTelemetry", {}).get("containsModelContextWindow")
        is True,
        "Official protocol capability observation drifted",
    )
    background = protocol.get("threadBackgroundTerminalTelemetry", {})
    _require(
        background.get("listMethod") == "thread/backgroundTerminals/list"
        and background.get("requiresThreadId") is True
        and {"osPid", "rssKb", "cpuPercent"}.issubset(
            set(background.get("fields", []))
        )
        and background.get("isMcpProcessTelemetry") is False,
        "Background-terminal protocol boundary drifted",
    )
    _require(
        protocol.get("threadScopedMcpInventory", {}).get(
            "responseContainsPerProcessResourceMetrics"
        )
        is False
        and protocol.get("threadScopedMcpInventory", {}).get(
            "responseContainsLeaseOrSubscriberCount"
        )
        is False,
        "MCP status was promoted beyond its schema",
    )

    desktop = evidence.get("currentDesktopAccessObservation", {})
    for key in (
        "codexAppListThreadsAvailable",
        "codexAppReadThreadAvailable",
        "currentThreadReportedActive",
        "currentTurnReportedInProgress",
        "appServerProxyCommandAvailable",
    ):
        _require(desktop.get(key) is True, f"Observed Desktop surface drifted: {key}")
    for key in (
        "codexAppThreadReadExposesTokenUsage",
        "codexAppThreadReadExposesBackgroundTerminals",
        "codexAppThreadReadExposesMcpOwnerOrLease",
        "currentVisibleToolSetExposesThreadLoadedList",
        "currentVisibleToolSetExposesThreadBackgroundTerminalList",
        "currentVisibleToolSetExposesThreadScopedMcpStatus",
        "currentThreadTerminalAttached",
        "defaultAppServerControlDirectoryPresent",
        "managedAppServerDaemonLifecycleSupportedOnWindows",
        "codexRuntimeTcpListenerObserved",
        "supportedCurrentDesktopAppServerAttachPathObserved",
        "persistedOrUiThreadVisibilityEqualsLoadedRuntimeAccess",
    ):
        _require(desktop.get(key) is False, f"Desktop access boundary drifted: {key}")

    decision = evidence.get("decision", {})
    _require(
        decision.get("officialProtocolDefinitionGap") is False
        and decision.get("currentDesktopOwnerTelemetryAccessGapObserved") is True
        and decision.get("currentDesktopActuatorAccessGapObserved") is True
        and decision.get("officialPrimitiveReuseRequiredBeforeSelfAuthoredController")
        is True
        and decision.get("safeCurrentDesktopOwnerAttributionEligible") is False
        and decision.get("safeCurrentDesktopReleaseAttributionEligible") is False
        and decision.get("autonomousRuntimeActionEligible") is False
        and decision.get("selfAuthoredControllerGapProved") is False
        and decision.get("isolatedAppServerLifecycleTrialAuthorized") is False,
        "Decision boundary drifted",
    )

    claims = evidence.get("claimBoundary", {})
    _require(
        claims and all(value is False for value in claims.values()),
        "Claim boundary must remain entirely negative",
    )

    document = DOCUMENT_PATH.read_text(encoding="utf-8")
    normalized = " ".join(document.split())
    for phrase in (
        "The remaining observed gap is not a missing protocol definition",
        "background-terminal telemetry is not MCP-process telemetry",
        "did not observe a supported attach path",
        "official protocol definition gap: false",
        "requires separate authorization",
    ):
        _require(phrase in normalized, f"Documentation missing: {phrase}")

    acceptances = {
        item.get("id"): item for item in program_map.get("acceptanceCriteria", [])
    }
    _require(
        EVIDENCE_ID in acceptances.get(ACCEPTANCE_ID, {}).get("evidenceIds", []),
        "Runtime acceptance is not linked to the access preflight",
    )
    records = {item.get("id"): item for item in program_map.get("evidence", [])}
    _require(
        records.get(EVIDENCE_ID, {}).get("path")
        == (
            "registry/codex-desktop-official-control-surface-access-"
            "preflight-2026-07-31.json"
        ),
        "Program evidence record drifted",
    )


def main() -> int:
    validate_preflight()
    print("Codex Desktop official control-surface access validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
