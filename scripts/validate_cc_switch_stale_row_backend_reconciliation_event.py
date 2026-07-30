#!/usr/bin/env python3
"""Validate the dated CC Switch stale-row backend reconciliation event."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_PATH = (
    "registry/cc-switch-3.18-stale-row-backend-reconciliation-event-2026-07-27.json"
)
DOCUMENTATION_PATH = (
    "docs/strategy/CC-SWITCH-3.18-STALE-ROW-BACKEND-RECONCILIATION-EVENT-2026-07-27.md"
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def validate_event(document: dict[str, Any], *, root: Path = ROOT) -> None:
    _require(
        document.get("schema") == 1
        and document.get("id")
        == "cc-switch-3.18-stale-row-backend-reconciliation-event-2026-07-27"
        and document.get("date") == "2026-07-27"
        and document.get("status")
        == "live-backend-reconciliation-executed-and-verified-current-host",
        "CC Switch stale-row reconciliation identity drifted",
    )
    preflight = document.get("preflight")
    _require(
        isinstance(preflight, dict)
        and preflight.get("databaseRows") == 251
        and preflight.get("physicalSsotBodies") == 75
        and preflight.get("missingBodyLocalRows") == 176
        and preflight.get("exactRuntimePluginDirectoryMatches") == 148
        and preflight.get("qualifiedRuntimePluginAliasMatches") == 25
        and len(preflight.get("historicalAliasRows", [])) == 3
        and preflight.get("nonLocalOrRepositoryAttributedTargets") == 0
        and preflight.get("targetWithPhysicalSsotDirectory") == 0,
        "CC Switch stale-row preflight drifted",
    )
    authority = document.get("authorityBoundary")
    _require(
        isinstance(authority, dict)
        and authority.get("userAuthorizedCcSwitchPortfolioManagement") is True
        and authority.get("scopeLimitedToMissingBodyLocalRows") is True
        and authority.get("ccSwitchBackendMutation") is True
        and authority.get("rawSqliteMutation") is False
        and authority.get("computerUseMutation") is False
        and authority.get("physicalSsotDeletion") is False,
        "CC Switch stale-row authority boundary drifted",
    )
    execution = document.get("execution")
    _require(
        isinstance(execution, dict)
        and execution.get("surface")
        == "temporary-localhost-webview2-cdp-to-tauri-ipc"
        and execution.get("tauriCommand") == "uninstall_skill_unified"
        and execution.get("remainingBatchRequested") == 175
        and execution.get("remainingBatchSucceeded") == 175
        and execution.get("remainingBatchErrors") == 0
        and execution.get("unexpectedContentBackupResults") == 0
        and execution.get("temporaryDebugPortClosedAfter") is True
        and execution.get("ordinaryCcSwitchRestartedAfter") is True,
        "CC Switch stale-row execution evidence drifted",
    )
    post = document.get("postVerification")
    _require(
        isinstance(post, dict)
        and post.get("databaseRows") == 75
        and post.get("physicalSsotBodies") == 75
        and post.get("missingBodyDatabaseRows") == 0
        and post.get("claudeProjectionEntries") == 75
        and post.get("claudeBrokenSymlinks") == 0
        and post.get("codexTopLevelEntries") == 77
        and post.get("codexBrokenSymlinks") == 0
        and post.get("temporaryDebugPortOpen") is False,
        "CC Switch stale-row post-verification drifted",
    )
    cloud = document.get("cloudSyncObservation")
    _require(
        isinstance(cloud, dict)
        and cloud.get("lastLocalManifestHash")
        == cloud.get("lastRemoteManifestHash")
        and cloud.get("localAndRemoteManifestHashEqual") is True
        and cloud.get("crossDeviceRestoreEqualityProved") is False,
        "CC Switch stale-row cloud-sync boundary drifted",
    )
    decision = document.get("decision")
    _require(
        isinstance(decision, dict)
        and decision.get("staleRowGapResolvedOnCurrentHost") is True
        and decision.get("physicalPortfolioBodyCountChanged") is False
        and decision.get("currentCcManagedBodyCount") == 75
        and decision.get("portfolioQualityReviewComplete") is False
        and decision.get("deduplicationOrRetirementComplete") is False
        and decision.get("upstreamBatchReconcilerExists") is False,
        "CC Switch stale-row decision boundary drifted",
    )
    claims = document.get("claimBoundary")
    _require(
        isinstance(claims, dict)
        and claims
        and all(value is False for value in claims.values()),
        "CC Switch stale-row claim boundary drifted",
    )
    _require(
        document.get("documentation") == DOCUMENTATION_PATH,
        "CC Switch stale-row documentation binding drifted",
    )
    text = (root / DOCUMENTATION_PATH).read_text(encoding="utf-8")
    for phrase in (
        "75 database rows and 75 physical SSOT bodies",
        "No Computer Use action and no raw SQLite mutation",
        "supersedes later-live-count use",
        "does not prove loader invocation",
    ):
        _require(
            phrase in text,
            f"CC Switch stale-row documentation missing: {phrase}",
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    root = args.root.resolve()
    document = json.loads((root / EVIDENCE_PATH).read_text(encoding="utf-8"))
    validate_event(document, root=root)
    print("CC Switch stale-row backend reconciliation event verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
