#!/usr/bin/env python3
"""Validate the dated CC Switch seven-Skill Lark update event."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_PATH = (
    "registry/cc-switch-lark-seven-skill-update-event-2026-07-27.json"
)
DOCUMENTATION_PATH = (
    "docs/strategy/CC-SWITCH-LARK-SEVEN-SKILL-UPDATE-EVENT-2026-07-27.md"
)
EXPECTED_HEAD = "7abcaa7f68ac60811f6c4b95e2f9f2a25800c852"
EXPECTED_SKILLS = {
    "lark-apps": (
        "master",
        18682,
        "4bd8d41467b40f1aa1d0e115a36d9c7115d5bb79d31e0809f0f1b48ec85e4bd9",
        "5be1a8793089d8e7c111566ffb545711f88fc947",
    ),
    "lark-base": (
        "main",
        19935,
        "aef3c07dbeb11cc87352b217fd3d9868b41f31f0cf3ae3de906e4e8443c4a01e",
        "459dae04b83100f6c0c97df9967435bc2d574607",
    ),
    "lark-calendar": (
        "master",
        12317,
        "d9f7150664f23f6e75f3cbdf410df5fc448fd5cd90b7cc959420ca86b2287611",
        "7edd4f1fae0213bc68376e48e562840dfb60d91a",
    ),
    "lark-doc": (
        "main",
        9313,
        "249110f21116d2e1eb09cc1b9b266889f290be57944975236254945dada65c0c",
        "478be8bb9f4f53c724b138e0faec29ec0e763f9b",
    ),
    "lark-drive": (
        "main",
        27549,
        "5423817c78709d70b0b84bb7bee15b8abc21c5982fc48c7e37ca2ddc42972c19",
        "2be992fa18dbfce0d56b7889dacc9daa7d93f80b",
    ),
    "lark-slides": (
        "main",
        26585,
        "edd9faa1f576589211ec622aa00b9f2acb726641a9ff20ac19d932e5a291e216",
        "60c165ea53cb84d207662c1bf3bd2e0962a98e9d",
    ),
    "lark-task": (
        "main",
        12283,
        "c9bae3576de69599b8b0587c120042fe8e6b27e9837b2d23ee6f43ca4974a41a",
        "a044d48001ffcaf477715c2500ecc90df52ad189",
    ),
}
EXPECTED_PROJECTION = {
    "ccSwitchPhysicalEntries": 75,
    "ccSwitchResolvableSkillMd": 75,
    "agentsEntries": 73,
    "agentsResolvableSkillMd": 73,
    "claudeEntries": 251,
    "claudeResolvableSkillMd": 75,
    "claudeUnresolvedEntries": 176,
    "codexEntries": 77,
    "codexResolvableSkillMd": 75,
    "codexNonSkillContainerRoots": 2,
}
EXPECTED_FALSE_CLAIMS = {
    "allLarkSkillTreesEqualUpstream",
    "allCcDatabaseRowsResolvable",
    "ccSwitchDiscoveryHealthyForAllSources",
    "claudeLoaderInvocationProved",
    "codexLoaderInvocationProved",
    "crossDeviceEqualityProved",
    "deduplicationAuthorized",
    "cleanupAuthorized",
    "portfolioDecisionProved",
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def validate_event(
    document: dict[str, Any],
    *,
    root: Path = ROOT,
) -> None:
    _require(
        document.get("schema") == 1
        and document.get("id")
        == "cc-switch-lark-seven-skill-update-event-2026-07-27"
        and document.get("date") == "2026-07-27"
        and document.get("status")
        == (
            "live-seven-skill-cohort-update-verified-current-host-"
            "residual-drift-open"
        ),
        "CC Switch Lark update identity drifted",
    )
    authority = document.get("authorityBoundary")
    _require(
        authority
        == {
            "userAuthorizedSevenPendingUpdates": True,
            "ccSwitchGuiMutation": True,
            "scopeLimitedToNamedSevenSkills": True,
            "agentCreatedSeparateBackup": False,
            "ccSwitchInternalRollbackBackupObserved": True,
            "cloudBackupInvokedByAgent": False,
            "accountOrCredentialRead": False,
            "globalConfigurationMutation": False,
            "skillEnableDisableOrDelete": False,
            "gitMutation": False,
            "remoteRepositoryMutation": False,
        },
        "CC Switch Lark update authority boundary drifted",
    )
    execution = document.get("execution")
    _require(
        isinstance(execution, dict)
        and execution.get("surface") == "CC Switch GUI"
        and execution.get("passSizes") == [4, 3]
        and execution.get("namedSkillCount") == 7
        and execution.get("pendingUpdateIndicatorAfter") == 0
        and execution.get("databaseRowsAfter") == 251
        and execution.get("enabledClaudeRowsAfter") == 251
        and execution.get("enabledCodexRowsAfter") == 251
        and execution.get("larkRepositoryRowsAfter") == 27,
        "CC Switch Lark update execution evidence drifted",
    )
    upstream = document.get("upstreamObservation")
    _require(
        isinstance(upstream, dict)
        and upstream.get("repository") == "larksuite/cli"
        and upstream.get("configuredRepositoryBranch") == "HEAD"
        and upstream.get("defaultBranch") == "main"
        and upstream.get("headCommit") == EXPECTED_HEAD
        and upstream.get("mainCommit") == EXPECTED_HEAD
        and upstream.get("masterCommit") == EXPECTED_HEAD
        and upstream.get("mainAndMasterEqualAtObservation") is True
        and upstream.get("verificationSurface")
        == "authenticated read-only GitHub API content response",
        "CC Switch Lark update upstream evidence drifted",
    )
    skills = document.get("skills")
    _require(
        isinstance(skills, list) and len(skills) == len(EXPECTED_SKILLS),
        "CC Switch Lark update Skill set drifted",
    )
    by_directory = {
        item.get("directory"): item
        for item in skills
        if isinstance(item, dict)
        and isinstance(item.get("directory"), str)
    }
    _require(
        set(by_directory) == set(EXPECTED_SKILLS),
        "CC Switch Lark update Skill identity set drifted",
    )
    for directory, (
        branch,
        size,
        digest,
        blob_sha,
    ) in EXPECTED_SKILLS.items():
        item = by_directory[directory]
        _require(
            item
            == {
                "id": f"larksuite/cli:{directory}",
                "directory": directory,
                "databaseBranchMetadata": branch,
                "skillMdBytes": size,
                "skillMdSha256": digest,
                "upstreamGitBlobSha": blob_sha,
                "localEntrypointEqualsUpstreamHead": True,
                "wholeTreeEqualityProved": False,
                "claudeProjectionTarget": (
                    f"~/.cc-switch/skills/{directory}"
                ),
                "codexProjectionTarget": (
                    f"~/.cc-switch/skills/{directory}"
                ),
            },
            f"CC Switch Lark update binding drifted: {directory}",
        )
    _require(
        document.get("postUpdateProjectionObservation")
        == EXPECTED_PROJECTION,
        "CC Switch Lark post-update projection count drifted",
    )
    residuals = document.get("residuals")
    _require(
        isinstance(residuals, list)
        and {item.get("id") for item in residuals if isinstance(item, dict)}
        == {
            "claude-stale-row-projection-gap",
            "composio-discovery-404",
            "lark-row-branch-alias-metadata",
        }
        and all(item.get("status") != "resolved" for item in residuals),
        "CC Switch Lark residual boundary drifted",
    )
    decision = document.get("decision")
    _require(
        isinstance(decision, dict)
        and decision.get("namedSevenUpdatesApplied") is True
        and decision.get("namedSevenEntrypointsMatchUpstreamHead") is True
        and decision.get("broaderStaleRowRepairComplete") is False
        and decision.get("composioDiscoveryRecovered") is False
        and decision.get("safeDeduplicationOrCleanupProved") is False
        and decision.get("crossDeviceRestoreEqualityProved") is False
        and decision.get("skillInvocationOrBehavioralValueProved") is False
        and "separate evidence gaps"
        in decision.get("nextBoundedAction", ""),
        "CC Switch Lark update decision boundary drifted",
    )
    claims = document.get("claimBoundary")
    _require(
        isinstance(claims, dict)
        and set(claims) == EXPECTED_FALSE_CLAIMS
        and all(value is False for value in claims.values()),
        "CC Switch Lark update claim boundary drifted",
    )
    _require(
        document.get("documentation") == DOCUMENTATION_PATH,
        "CC Switch Lark update documentation binding drifted",
    )
    text = (root / DOCUMENTATION_PATH).read_text(encoding="utf-8")
    for phrase in (
        "seven named live updates verified",
        "entrypoint equality, not whole-tree equality",
        "176 unresolved Claude",
        "Composio discovery/update scan still returned HTTP 404",
        "NO-GO boundary",
        "does not authorize stale-row repair",
    ):
        _require(
            phrase in text,
            f"CC Switch Lark update documentation missing: {phrase}",
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    root = args.root.resolve()
    document = json.loads(
        (root / EVIDENCE_PATH).read_text(encoding="utf-8")
    )
    validate_event(document, root=root)
    print("CC Switch Lark seven-Skill update event passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
