#!/usr/bin/env python3
"""Validate the exact CC Switch fourteen-Skill subtraction preview."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_PATH = (
    "registry/cc-switch-fourteen-skill-subtraction-preview-2026-07-30.json"
)
DOCUMENTATION_PATH = (
    "docs/strategy/"
    "CC-SWITCH-FOURTEEN-SKILL-SUBTRACTION-PREVIEW-2026-07-30.md"
)
EXPECTED = {
    "design-an-interface",
    "edit-article",
    "qa",
    "request-refactor-plan",
    "review",
    "setup-pre-commit",
    "setup-project-skills",
    "to-issues",
    "to-prd",
    "ubiquitous-language",
    "writing-beats",
    "writing-fragments",
    "writing-shape",
    "zoom-out",
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def validate_preview(
    document: dict[str, Any],
    *,
    root: Path = ROOT,
) -> None:
    _require(
        document.get("schema") == 1
        and document.get("id")
        == "cc-switch-fourteen-skill-subtraction-preview-2026-07-30"
        and document.get("date") == "2026-07-30"
        and document.get("status")
        == "read-only-manager-preview-awaiting-exact-mutation-authorization",
        "Fourteen-Skill preview identity drifted",
    )
    _require(
        document.get("predecessor")
        == "registry/skill-portfolio-current-55-subtractive-triage-2026-07-30.json",
        "Fourteen-Skill preview predecessor drifted",
    )
    authority = document.get("authorityBoundary", {})
    _require(
        authority.get("readLiveDatabaseBodiesProjectionsAndProcesses") is True
        and authority.get("readPublicCcSwitchTagSource") is True
        and authority.get("temporaryCcSwitchSourceCloneAndExactCleanup") is True
        and authority.get("freshProcessNoModelSkillsList") is True
        and authority.get("ccSwitchUninstall") is False
        and authority.get("ccSwitchRestore") is False
        and authority.get("ccSwitchRemoteSync") is False
        and authority.get("agentsBrokenLinkCleanup") is False
        and authority.get("globalConfigHookRulesOrForeignRootMutation") is False
        and authority.get("modelDispatch") is False
        and authority.get("gitCommitOrPush") is False,
        "Fourteen-Skill preview authority drifted",
    )
    manager = document.get("managerSource", {})
    _require(
        manager.get("version") == "3.18.0"
        and manager.get("tagObject")
        == "0dfc78f520a01b9c17d128cad21ee03cd7f30106"
        and manager.get("commit")
        == "606e7bbe75db7f8285f7a3be006fac22b5d22796"
        and manager.get("uninstallCommand") == "uninstall_skill_unified"
        and manager.get("restoreCommand") == "restore_skill_backup"
        and manager.get("secondHostEnableCommand") == "toggle_skill_app"
        and manager.get("skillBackupRetention") == 20
        and manager.get("directDatabaseWriteRequired") is False,
        "Fourteen-Skill manager source drifted",
    )
    semantics = document.get("managerSemantics", {})
    _require(
        semantics.get("backupCreatedBeforeDestructiveSteps") is True
        and semantics.get("restoreRejectsExistingIdentityOrDirectoryCollision") is True
        and semantics.get("restoreEnablesExactlyOneRequestedHost") is True
        and semantics.get("dualHostRollbackRequiresRestoreThenSecondHostToggle")
        is True
        and semantics.get("commonAgentsCompatibilityLinksManagedByUninstall")
        is False,
        "Fourteen-Skill manager semantics drifted",
    )
    pre = document.get("livePreState", {})
    _require(
        pre.get("databaseRows") == 55
        and pre.get("databaseDistinctNames") == 55
        and pre.get("claudeEnabledRows") == 55
        and pre.get("codexDatabaseEnabledRows") == 53
        and pre.get("ccSwitchEntries") == 55
        and pre.get("agentsEntries") == 41
        and pre.get("claudeEntries") == 55
        and pre.get("codexTopLevelEntries") == 55
        and pre.get("codexResolvableCcSkillMd") == 53
        and pre.get("brokenLinksAcrossFourRoots") == 0
        and pre.get("managerBackupCount") == 20
        and pre.get("managerProcessCount") == 1
        and pre.get("managerDebugListenerOpen") is False,
        "Fourteen-Skill live pre-state drifted",
    )
    cohort = document.get("candidateCohort", {})
    items = cohort.get("items", [])
    _require(
        cohort.get("count") == 14
        and cohort.get("fileCount") == 19
        and cohort.get("bytes") == 58356
        and set(cohort.get("names", [])) == EXPECTED
        and len(items) == 14
        and {item.get("name") for item in items} == EXPECTED
        and sum(item.get("fileCount", 0) for item in items) == 19
        and sum(item.get("bytes", 0) for item in items) == 58356,
        "Fourteen-Skill candidate manifest drifted",
    )
    _require(
        cohort.get("allDatabaseRowsLocalOrUnattributed") is True
        and cohort.get("allClaudeEnabled") is True
        and cohort.get("allCodexEnabled") is True
        and cohort.get("enabledGeminiRows") == 0
        and cohort.get("enabledOpenCodeRows") == 0
        and cohort.get("enabledHermesRows") == 0
        and cohort.get("enabledGrokBuildRows") == 0
        and cohort.get("allAgentsLinksResolveToCcSwitch") is True
        and cohort.get("allClaudeLinksResolveToCcSwitch") is True
        and cohort.get("allCodexLinksResolveToCcSwitch") is True
        and cohort.get("freshAppServerInventoryCount") == 64
        and cohort.get("freshAppServerTargetCount") == 14
        and cohort.get("allFreshAppServerTargetsEnabled") is True
        and cohort.get("freshAppServerStderrLineCount") == 0
        and cohort.get("freshAppServerConfigPrePostStable") is True,
        "Fourteen-Skill exposure or projection drifted",
    )
    gates = document.get("exclusionsAndReferenceGates", {})
    _require(
        gates.get("diagnoseExcluded") is True
        and gates.get("qaPromotedSetupMentionRecorded") is True
        and gates.get("qaMentionIsHardExecutionDependency") is False
        and gates.get("remainingThirteenHaveNoObservedHardNamedDependencyFromRetainedBodies")
        is True
        and gates.get("genericEnglishWordMatchesWereNotTreatedAsSkillDependencies")
        is True,
        "Fourteen-Skill reference boundary drifted",
    )
    rotation = document.get("backupRotationProjection", {})
    _require(
        rotation.get("currentBackupCount") == 20
        and rotation.get("newBackupCountIfAllFourteenSucceed") == 14
        and rotation.get("retentionAfterTransaction") == 20
        and rotation.get("expectedOldBackupEvictionCount") == 14
        and rotation.get("expectedEvictedCohort")
        == "the fourteen oldest remaining Lark-removal backups"
        and rotation.get("expectedRetainedPriorSubtractionBackups") == 6
        and rotation.get("projectionAssumesNoConcurrentBackupCreation") is True
        and rotation.get("managerWillPerformEvictionAutomatically") is True
        and rotation.get("evictionRequiresExplicitAuthorization") is True,
        "Fourteen-Skill backup rotation projection drifted",
    )
    recovery = document.get("recoveryPreflight", {})
    _require(
        recovery.get("plannedExactArchiveSkillCount") == 14
        and recovery.get("plannedExactArchiveFileCount") == 19
        and recovery.get("plannedExactArchivePayloadBytes") == 58356
        and recovery.get("excludeRawDatabaseSettingsCredentialsAccountAndSessionData")
        is True
        and recovery.get("secretScanRequired") is True
        and recovery.get("archiveVerificationRequiredBeforeCanary") is True,
        "Fourteen-Skill recovery preflight drifted",
    )
    plan = document.get("transactionPlan", {})
    _require(
        plan.get("canary") == "edit-article"
        and plan.get("remainingBatchCount") == 13
        and len(plan.get("steps", [])) == 11
        and "uninstall_skill_unified" in plan.get("steps", [])[2]
        and any("~/.agents/skills" in step for step in plan.get("steps", [])),
        "Fourteen-Skill transaction plan drifted",
    )
    rollback = document.get("rollbackPlan", {})
    _require(
        rollback.get("stopOnFirstFailure") is True
        and rollback.get("restoreCompletedUninstallsInReverseOrder") is True
        and rollback.get("restoreCommand") == "restore_skill_backup"
        and rollback.get("restoreCurrentApp") == "claude"
        and rollback.get("restoreSecondHostWith")
        == "toggle_skill_app app=codex enabled=true"
        and rollback.get("agentsLinksRemainUntilFullBatchSuccess") is True
        and rollback.get("verifyTreeHashDatabaseFlagsAndBothHostProjectionsAfterEveryRestore")
        is True,
        "Fourteen-Skill rollback plan drifted",
    )
    post = document.get("expectedPostState", {})
    _require(
        post
        == {
            "databaseRows": 41,
            "databaseDistinctNames": 41,
            "claudeEnabledRows": 41,
            "codexDatabaseEnabledRows": 39,
            "ccSwitchEntries": 41,
            "agentsEntries": 27,
            "claudeEntries": 41,
            "codexTopLevelEntries": 41,
            "codexResolvableCcSkillMd": 39,
            "brokenLinksAcrossFourRoots": 0,
            "docAndPdfRemainSharedAndCodexDisabled": True,
            "mattPromotedRowsRemain": 22,
            "selfAuthoredRowsRemain": 3,
            "diagnoseRemains": True,
        },
        "Fourteen-Skill expected post-state drifted",
    )
    _require(
        len(document.get("authorizationRequired", [])) == 5
        and "diagnose removal or reference repair"
        in document.get("explicitlyOutOfScope", [])
        and "model dispatch" in document.get("explicitlyOutOfScope", []),
        "Fourteen-Skill authorization scope drifted",
    )
    cleanup = document.get("cleanup", {})
    _require(
        cleanup
        == {
            "ccSwitchSourceTempRootAbsent": True,
            "noTransactionArchiveCreatedYet": True,
            "noDebugListenerCreated": True,
            "repositoryCleanupInventoryStable": True,
        },
        "Fourteen-Skill cleanup evidence drifted",
    )
    claims = document.get("claimBoundary", {})
    _require(
        claims.get("exactCohortAndCurrentExposureProved") is True
        and claims.get("managerBackendAndRestoreSemanticsProved") is True
        and claims.get("backupRotationProjectedNotExecuted") is True
        and claims.get("liveUninstallAuthorized") is False
        and claims.get("liveUninstallExecuted") is False
        and claims.get("postStateProved") is False
        and claims.get("behavioralValueOfRemainingPortfolioProved") is False
        and claims.get("programCloseoutProved") is False,
        "Fourteen-Skill claim boundary drifted",
    )
    _require(
        document.get("documentation") == DOCUMENTATION_PATH,
        "Fourteen-Skill documentation binding drifted",
    )
    text = (root / DOCUMENTATION_PATH).read_text(encoding="utf-8")
    for phrase in (
        "read-only manager preview",
        "`diagnose` is excluded",
        "enables exactly one requested",
        "automatically evict the fourteen oldest",
        "proposed canary is `edit-article`",
        "No uninstall, restore, remote sync",
    ):
        _require(
            phrase in text,
            f"Fourteen-Skill documentation missing: {phrase}",
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    root = args.root.resolve()
    document = json.loads((root / EVIDENCE_PATH).read_text(encoding="utf-8"))
    validate_preview(document, root=root)
    print("CC Switch fourteen-Skill subtraction preview passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
