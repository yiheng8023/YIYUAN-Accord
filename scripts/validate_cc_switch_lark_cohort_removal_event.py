#!/usr/bin/env python3
"""Validate the dated CC Switch shared Lark cohort removal event."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_PATH = (
    "registry/cc-switch-lark-cohort-removal-event-2026-07-28.json"
)
DOCUMENTATION_PATH = (
    "docs/strategy/CC-SWITCH-LARK-COHORT-REMOVAL-EVENT-2026-07-28.md"
)
EXPECTED_SKILLS = {
    "lark-approval",
    "lark-apps",
    "lark-attendance",
    "lark-base",
    "lark-calendar",
    "lark-contact",
    "lark-doc",
    "lark-drive",
    "lark-event",
    "lark-im",
    "lark-mail",
    "lark-markdown",
    "lark-minutes",
    "lark-note",
    "lark-okr",
    "lark-openapi-explorer",
    "lark-shared",
    "lark-sheets",
    "lark-skill-maker",
    "lark-slides",
    "lark-task",
    "lark-vc",
    "lark-vc-agent",
    "lark-whiteboard",
    "lark-wiki",
    "lark-workflow-meeting-summary",
    "lark-workflow-standup-report",
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
        == "cc-switch-lark-cohort-removal-event-2026-07-28"
        and document.get("date") == "2026-07-28"
        and document.get("status")
        == "live-shared-lark-cohort-removal-verified-current-host",
        "CC Switch Lark removal identity drifted",
    )
    authority = document.get("authorityBoundary")
    _require(
        isinstance(authority, dict)
        and authority.get("userAuthorizedCompleteSharedLarkRemoval") is True
        and authority.get("scopeLimitedToExactTwentySevenSkillCohort") is True
        and authority.get("ccSwitchBackendWasMutationSurface") is True
        and authority.get("agentsLockManagedCopiesRemovedSeparately") is True
        and authority.get("traeRootsExcluded") is True
        and authority.get("ccSwitchStorageModeChanged") is False
        and authority.get("directDatabaseWrite") is False
        and authority.get("accountOrCredentialRead") is False
        and authority.get("hookMutation") is False
        and authority.get("modelDispatch") is False
        and authority.get("gitCommitOrPush") is False,
        "CC Switch Lark removal authority boundary drifted",
    )
    directory = document.get("directoryAuthority")
    _require(
        directory
        == {
            "sharedThirdPartyEntityStore": "~/.cc-switch/skills",
            "codexAndClaudeRole": "CC Switch managed consumer projections",
            "agentsRole": (
                "compatibility or unsupported-host adapter, not a second "
                "entity store"
            ),
            "traeRole": "foreign-managed common and versioned Plugin roots",
            "skillStorageLocation": "cc_switch",
        },
        "CC Switch Lark removal directory authority drifted",
    )
    skills = document.get("removedSkills")
    _require(
        isinstance(skills, list)
        and len(skills) == 27
        and set(skills) == EXPECTED_SKILLS
        and skills == sorted(skills),
        "CC Switch Lark removal cohort drifted",
    )
    baseline = document.get("managerBaseline")
    _require(
        isinstance(baseline, dict)
        and baseline.get("repository") == "farion1231/cc-switch"
        and baseline.get("version") == "3.18.0"
        and baseline.get("tagObject")
        == "0dfc78f520a01b9c17d128cad21ee03cd7f30106"
        and baseline.get("commit")
        == "606e7bbe75db7f8285f7a3be006fac22b5d22796"
        and baseline.get("builtInBackupRetention") == 20,
        "CC Switch Lark removal manager baseline drifted",
    )
    pre = document.get("preState")
    _require(
        isinstance(pre, dict)
        and pre.get("databaseRows") == 88
        and pre.get("databaseLarkRows") == 27
        and pre.get("ccSwitchLarkEntries") == 27
        and pre.get("agentsPhysicalLarkEntries") == 27
        and pre.get("agentsLockLarkEntries") == 27
        and pre.get("codexLarkEntries") == 27
        and pre.get("claudeLarkEntries") == 27
        and pre.get("traeCommonLarkEntries") == 0
        and pre.get("traePluginLarkEntries") == 26,
        "CC Switch Lark removal pre-state drifted",
    )
    execution = document.get("execution")
    _require(
        isinstance(execution, dict)
        and execution.get("canaryCount") == 1
        and execution.get("remainingBatchCount") == 26
        and execution.get("successfulUninstalls") == 27
        and execution.get("failedUninstalls") == 0
        and execution.get("agentsLockSchema") == 3
        and execution.get("agentsLockReplacementAtomic") is True
        and execution.get("ccSwitchManagedBackupsAfter") == 20
        and execution.get("ccSwitchManagedBackupsRetained") is True
        and execution.get("explicitRemoteSyncStatus") == "uploaded"
        and execution.get("remoteSnapshotId")
        == "56f7000c5713a571b3edcb7facf766d06616e1ce4811191c0f87d7883ab0ee72"
        and execution.get("remoteSnapshotArtifacts") == ["db.sql", "skills.zip"],
        "CC Switch Lark removal execution evidence drifted",
    )
    post = document.get("postState")
    _require(
        isinstance(post, dict)
        and post.get("databaseRows") == 61
        and post.get("databaseLarkRows") == 0
        and post.get("ccSwitchEntries") == 61
        and post.get("ccSwitchLarkEntries") == 0
        and post.get("ccSwitchBrokenLinks") == 0
        and post.get("agentsEntries") == 46
        and post.get("agentsLinks") == 43
        and post.get("agentsPhysicalEntries") == 3
        and post.get("agentsLarkEntries") == 0
        and post.get("agentsBrokenLinks") == 0
        and post.get("agentsLockLarkEntries") == 0
        and post.get("codexEntries") == 63
        and post.get("codexLarkEntries") == 0
        and post.get("codexBrokenLinks") == 0
        and post.get("claudeEntries") == 61
        and post.get("claudeLarkEntries") == 0
        and post.get("claudeBrokenLinks") == 0
        and post.get("ccSwitchProcessCount") == 1
        and post.get("temporaryDebugPortOpen") is False,
        "CC Switch Lark removal post-state drifted",
    )
    sentinels = document.get("foreignRootSentinels")
    _require(
        isinstance(sentinels, dict)
        and sentinels.get("traeCommonLarkEntriesBefore") == 0
        and sentinels.get("traeCommonLarkEntriesAfter") == 0
        and sentinels.get("traeCommonNamesAndHashesStable") is True
        and sentinels.get("traePluginLarkEntriesBefore") == 26
        and sentinels.get("traePluginLarkEntriesAfter") == 26
        and sentinels.get("traePluginNamesAndHashesStable") is True,
        "CC Switch Lark removal foreign-root sentinels drifted",
    )
    cleanup = document.get("cleanup")
    _require(
        isinstance(cleanup, dict)
        and cleanup.get("agentRecoveryRootRetained") is False
        and cleanup.get("agentRecoveryRootAbsent") is True
        and cleanup.get("temporarySourceRootAbsent") is True
        and cleanup.get("temporarySnapshotScriptAbsent") is True
        and cleanup.get("ccSwitchManagedBackupsRetained") is True
        and cleanup.get("repositoryLocalSem03TemporaryRootsAbsent") is True
        and cleanup.get("repositoryCleanupInventoryStable") is True,
        "CC Switch Lark removal cleanup evidence drifted",
    )
    verification = document.get("verification")
    _require(
        isinstance(verification, dict)
        and verification.get("semanticAuthorityFocusedCurrentTestCount") == 18
        and verification.get("semanticAuthorityFocusedCurrentTestsPassed") is True
        and verification.get("topLevelVerifierPassed") is True
        and verification.get("freshTaskRequiredToRefreshStartupSkillCatalog")
        is True,
        "CC Switch Lark removal verification boundary drifted",
    )
    claims = document.get("claimBoundary")
    _require(
        claims
        == {
            "sharedLarkCapabilityRemoved": True,
            "traePluginLarkCapabilityRemoved": False,
            "freshTaskCatalogRefreshObserved": False,
            "loaderInvocationProved": False,
            "crossHostBehaviorProved": False,
            "portfolioQualityProved": False,
            "programCloseoutProved": False,
        },
        "CC Switch Lark removal claim boundary drifted",
    )
    _require(
        document.get("documentation") == DOCUMENTATION_PATH,
        "CC Switch Lark removal documentation binding drifted",
    )
    text = (root / DOCUMENTATION_PATH).read_text(encoding="utf-8")
    for phrase in (
        "shared 27-Skill Lark cohort removed",
        "not a second third-party entity store",
        "Trae's common root had zero Lark Skills before and after",
        "The temporary source clone, snapshot helper, and agent-created recovery bundle",
        "fresh task or UI",
        "does not prove fresh-task loader behavior",
    ):
        _require(
            phrase in text,
            f"CC Switch Lark removal documentation missing: {phrase}",
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
    print("CC Switch Lark cohort removal event passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
