#!/usr/bin/env python3
"""Validate the CC Switch 3.19 fourteen-Skill subtraction refresh."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_PATH = (
    "registry/"
    "cc-switch-fourteen-skill-subtraction-preview-3.19-refresh-2026-07-30.json"
)
DOCUMENTATION_PATH = (
    "docs/strategy/"
    "CC-SWITCH-FOURTEEN-SKILL-SUBTRACTION-PREVIEW-3.19-"
    "REFRESH-2026-07-30.md"
)
LAYERED_EVIDENCE_PATH = (
    "registry/"
    "cc-switch-fourteen-skill-subtraction-preview-3.19-"
    "layered-refresh-2026-07-31.json"
)
LAYERED_DOCUMENTATION_PATH = (
    "docs/strategy/"
    "CC-SWITCH-FOURTEEN-SKILL-SUBTRACTION-PREVIEW-3.19-"
    "LAYERED-REFRESH-2026-07-31.md"
)
LAYERED_ID = (
    "cc-switch-fourteen-skill-subtraction-preview-3.19-"
    "layered-refresh-2026-07-31"
)
LIVE_PREFLIGHT_PATH = (
    "registry/cc-switch-fourteen-skill-live-preflight-contract-2026-07-31.json"
)
EXACT_AUTHORIZATION = [
    "uninstall exactly the fourteen named Skills through uninstall_skill_unified",
    (
        "allow CC Switch retention to evict exactly the fourteen named oldest "
        "backups if no concurrent backup appears"
    ),
    (
        "remove exactly the fourteen resulting broken ~/.agents/skills links "
        "only after full manager success"
    ),
    "write and verify one configured CC Switch remote snapshot",
    (
        "create then exactly clean the bounded recovery archive and temporary "
        "CDP/debug helper"
    ),
]
EXPECTED_NAMES = {
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


def _validate_layered_delta_overlay(
    document: dict[str, Any],
    *,
    root: Path | None,
) -> None:
    _require(
        document.get("schema") == 1
        and document.get("id") == LAYERED_ID
        and document.get("date") == "2026-07-31"
        and document.get("status")
        == (
            "read-only-manager-319-layered-refresh-awaiting-"
            "exact-mutation-authorization"
        ),
        "CC 3.19 layered refresh identity drifted",
    )
    _require(
        document.get("predecessors")
        == {
            "managerRefresh": EVIDENCE_PATH,
            "livePreflightContract": LIVE_PREFLIGHT_PATH,
        },
        "CC 3.19 layered refresh predecessor binding drifted",
    )
    posture = document.get("repositoryPosture", {})
    _require(
        posture.get("branch") == "main"
        and posture.get("head")
        == "6deaf10a5a66322ff9f149734578a77e0fcfb92c"
        and posture.get("originMain") == posture.get("head")
        and posture.get("ahead") == 0
        and posture.get("behind") == 0
        and posture.get("inheritedChangesPreserved") is True,
        "CC 3.19 layered repository posture drifted",
    )
    authority = document.get("authorityBoundary", {})
    _require(
        authority.get("readCurrentPredecessorsAndLivePreflight") is True
        and authority.get("ccSwitchUninstallRestoreRemoteSyncOrToggle") is False
        and authority.get("agentsBrokenLinkCleanup") is False
        and authority.get("recoveryArchiveOrDebugBridgeCreation") is False
        and authority.get("globalConfigRulesHookOrForeignRootMutation") is False
        and authority.get("separateAppServerOrModelDispatch") is False,
        "CC 3.19 layered authority boundary drifted",
    )
    reused = document.get("reusedFrozenSurfaces", {})
    _require(
        reused.get("managerBinaryAnd319SourceSemantics") is True
        and reused.get("fourteenNamesRowsContentHashesTreeManifestsAndHostLinks")
        is True
        and reused.get("backupCountOrderAndExactFourteenEvictionIds") is True
        and reused.get("canarySequentialBatchRollbackAndCleanupProcedure") is True
        and reused.get("exactFivePartAuthorizationBoundary") is True
        and reused.get("candidateCohortCount") == 14
        and reused.get("backupCount") == 20
        and reused.get("expectedEvictionCount") == 14
        and reused.get("canary") == "edit-article",
        "CC 3.19 layered frozen surface binding drifted",
    )
    live = document.get("liveDelta", {})
    _require(
        live.get("priorCodexTopLevelEntries") == 55
        and live.get("codexTopLevelEntries") == 57
        and live.get("docPdfPrivateAliasCount") == 2
        and live.get("docPdfPolicyMode") == "canonical-host-disable"
        and live.get("targetAndBackupFingerprintsUnchanged") is True
        and live.get("livePreflightWholeStateFingerprint")
        == "3245721c8dae1f2008d4c795e6fcbe66da5a64994d25d6ae13d5f4eef2d86c01",
        "CC 3.19 layered live delta drifted",
    )
    post = document.get("expectedPostState", {})
    _require(
        post.get("databaseRows") == 41
        and post.get("ccSwitchEntries") == 41
        and post.get("agentsEntries") == 27
        and post.get("claudeEntries") == 41
        and post.get("codexTopLevelEntries") == 43
        and post.get("docPdfPrivateAliasCount") == 2
        and post.get("docPdfPolicyMode") == "canonical-host-disable"
        and post.get("brokenLinksAcrossFourRoots") == 0
        and post.get("mattPromotedRowsRemain") == 22
        and post.get("selfAuthoredRowsRemain") == 3
        and post.get("diagnoseRemains") is True
        and post.get("forecastBinding") is True
        and post.get("invalidatedByConcurrentCcMutation") is True,
        "CC 3.19 layered expected post-state drifted",
    )
    transaction = document.get("transactionAndRollbackDelta", {})
    _require(
        transaction.get("managerTransactionUnchanged") is True
        and transaction.get(
            "docPdfCanonicalHostDisableMatt22AndTraeRootsAreUnchangedSentinels"
        )
        is True
        and transaction.get("codexCountCorrection") == "57 - 14 = 43"
        and transaction.get("noDocPdfToggleConfigWriteOrRestartRequired") is True,
        "CC 3.19 layered transaction delta drifted",
    )
    _require(
        document.get("authorizationRequired") == EXACT_AUTHORIZATION,
        "CC 3.19 layered exact authorization drifted",
    )
    out_of_scope = document.get("explicitlyOutOfScope", [])
    _require(
        "any doc or pdf manager toggle, Codex config write, restart, or separate app-server"
        in out_of_scope
        and "the three self-authored CC rows or their Claude links"
        in out_of_scope
        and "Matt's twenty-two promoted Skills" in out_of_scope
        and "Trae-owned or Plugin-owned roots" in out_of_scope
        and "any first-party .agents or .codex physical directory mutation"
        in out_of_scope,
        "CC 3.19 layered out-of-scope boundary drifted",
    )
    _require(
        document.get("cleanup")
        == {
            "temporarySourceRootCreated": False,
            "transactionArchiveCreated": False,
            "debugListenerOrBridgeCreated": False,
            "managerHostOrConfigMutation": False,
        },
        "CC 3.19 layered cleanup boundary drifted",
    )
    claims = document.get("claimBoundary", {})
    _require(
        claims.get("transactionPredictionCurrent") is True
        and claims.get("frozenTransactionDesignReused") is True
        and claims.get("liveUninstallAuthorized") is False
        and claims.get("liveUninstallExecuted") is False
        and claims.get("postStateProved") is False
        and claims.get("rollbackExecutionProved") is False
        and claims.get("remoteSnapshotProved") is False
        and claims.get("remainingPortfolioBehavioralValueProved") is False
        and claims.get("programCloseoutProved") is False,
        "CC 3.19 layered claim boundary drifted",
    )
    if root is None:
        return
    _require(
        document.get("documentation") == LAYERED_DOCUMENTATION_PATH,
        "CC 3.19 layered documentation binding drifted",
    )
    manager_refresh = json.loads(
        (root / EVIDENCE_PATH).read_text(encoding="utf-8")
    )
    live_preflight = json.loads(
        (root / LIVE_PREFLIGHT_PATH).read_text(encoding="utf-8")
    )
    _require(
        manager_refresh.get("id")
        == "cc-switch-fourteen-skill-subtraction-preview-3.19-refresh-2026-07-30"
        and live_preflight.get("id")
        == "cc-switch-fourteen-skill-live-preflight-contract-2026-07-31",
        "CC 3.19 layered predecessor identity drifted",
    )
    text = (root / LAYERED_DOCUMENTATION_PATH).read_text(encoding="utf-8")
    for phrase in (
        "57 → 43",
        "not a new transaction design",
        "canonical host-disable",
        "five-part authorization boundary",
        "No mutation has been authorized or executed.",
    ):
        _require(
            phrase in text,
            f"CC 3.19 layered documentation missing: {phrase}",
        )


def validate_refresh(
    document: dict[str, Any],
    *,
    root: Path | None = ROOT,
) -> None:
    if document.get("id") == LAYERED_ID:
        _validate_layered_delta_overlay(document, root=root)
        return
    _require(
        document.get("schema") == 1
        and document.get("id")
        == "cc-switch-fourteen-skill-subtraction-preview-3.19-refresh-2026-07-30"
        and document.get("date") == "2026-07-30"
        and document.get("status")
        == "read-only-manager-319-refresh-awaiting-exact-mutation-authorization",
        "CC 3.19 fourteen-Skill refresh identity drifted",
    )
    posture = document.get("repositoryPosture", {})
    _require(
        posture.get("branch") == "main"
        and posture.get("head")
        == "55659f30091990f7c589932e0379880de30dc403"
        and posture.get("originMain") == posture.get("head")
        and posture.get("ahead") == 0
        and posture.get("behind") == 0
        and posture.get("worktreeIntentionallyLargeAndDirty") is True
        and posture.get("inheritedChangesPreserved") is True,
        "CC 3.19 fourteen-Skill repository posture drifted",
    )
    authority = document.get("authorityBoundary", {})
    _require(
        authority.get("readLiveDatabaseBodiesLinksSettingsProcessesAndBackups")
        is True
        and authority.get("freshProcessNoModelSkillsList") is True
        and authority.get("readCurrentOfficialCcSwitchTagSource") is True
        and authority.get("ccSwitchUninstallRestoreRemoteSyncOrToggle") is False
        and authority.get("agentsBrokenLinkCleanup") is False
        and authority.get("recoveryArchiveOrDebugBridgeCreation") is False
        and authority.get("globalConfigRulesHookOrForeignRootMutation") is False
        and authority.get("modelDispatch") is False
        and authority.get("gitCommitOrPush") is False,
        "CC 3.19 fourteen-Skill authority boundary drifted",
    )
    manager = document.get("manager", {})
    settings = manager.get("settings", {})
    official = manager.get("officialSource", {})
    _require(
        manager.get("binaryFileVersion") == "3.19.0"
        and manager.get("binaryProductVersion") == "3.19.0"
        and manager.get("binaryBytes") == 32584192
        and manager.get("binarySha256")
        == "aa2962e5414e11e2b418eccc640cb24a1ad902f6d081c514d740edb735e5a101"
        and manager.get("processCount") == 1
        and settings.get("skillStorageLocation") == "cc_switch"
        and settings.get("skillSyncMethod") == "symlink"
        and settings.get("skillPathOverridesObserved") is False
        and official.get("tag") == "v3.19.0"
        and official.get("tagObject")
        == "09ccf3280c779c6cf7023cd2c3fc3faa21af8b73"
        and official.get("commit")
        == "c0ff89b9b208c092d6ef40b155403dcf290e5767"
        and official.get("serviceBlob")
        == "84f02e9ebdcfdd7f53c683669e1c942c5fe75944"
        and official.get("commandBlob")
        == "6ac90ac54702117fef8cb78ddc93cfddde763e0c"
        and official.get("appTypeBlob")
        == "74eac3f846dbcd78304231df044b7c585dbaccc3"
        and official.get("tagSignatureVerifiedByGitHub") is False
        and official.get("binaryToTagCryptographicAttributionProved") is False,
        "CC 3.19 manager identity drifted",
    )
    semantics = document.get("managerSemantics", {})
    required_true = {
        "uninstallValidatesSingleSegmentDirectoryBeforeFilesystemActions",
        "allFourteenDirectoriesPassObservedSingleSegmentShape",
        "uninstallIteratesAllAppsWithoutConsultingEnabledFlagsForCleanup",
        "removePathUnlinksSymlinkWithoutDeletingCcSource",
        "removePathRecursivelyDeletesPhysicalDirectory",
        "allFourteenClaudeAndCodexTargetsAreCcSymlinks",
        "noneOfFourteenCodexTargetsAreExternallyOwnedPhysicalDirectories",
        "ordinaryUninstallHasNoFirstPartyPhysicalDirectoryCollisionForThisCohort",
        "restoreRejectsExistingIdentityOrDirectoryCollision",
        "restoreEnablesExactlyOneRequestedHost",
        "dualHostRollbackRequiresRestoreThenSecondHostToggle",
        "backupCleanupFailureIsWarningOnly",
    }
    _require(
        semantics.get("uninstallCommand") == "uninstall_skill_unified"
        and semantics.get("uninstallService") == "SkillService::uninstall"
        and all(semantics.get(key) is True for key in required_true)
        and semantics.get("commonAgentsCompatibilityLinksManagedByUninstall")
        is False
        and semantics.get("skillBackupRetention") == 20
        and semantics.get("directDatabaseWriteRequired") is False
        and len(semantics.get("sourceReferences", [])) >= 7,
        "CC 3.19 manager semantics drifted",
    )
    live = document.get("livePreState", {})
    _require(
        live.get("databaseRows") == 55
        and live.get("databaseDistinctNames") == 55
        and live.get("targetRows") == 14
        and live.get("allTargetDatabaseContentHashesMatchPriorPreview") is True
        and live.get("allTargetRowsLocalOrUnattributed") is True
        and live.get("allTargetRowsClaudeEnabled") is True
        and live.get("allTargetRowsCodexEnabled") is True
        and live.get("allTargetRowsOtherRecordedHostsDisabled") is True
        and live.get("allTargetCcTreesPresent") is True
        and live.get("allTargetFileCountsAndBytesMatchPriorPreview") is True
        and live.get("allTargetAgentsLinksResolveToCc") is True
        and live.get("allTargetClaudeLinksResolveToCc") is True
        and live.get("allTargetCodexLinksResolveToCc") is True
        and live.get("brokenLinksAcrossTargetFourRootPaths") == 0
        and live.get("freshNoModelAppServerInventoryCount") == 64
        and live.get("freshNoModelAppServerTargetCount") == 14
        and live.get("allFreshNoModelTargetsEnabled") is True
        and live.get("modelTurnSent") is False
        and live.get("managerBackupCount") == 20,
        "CC 3.19 live pre-state drifted",
    )
    cohort = document.get("candidateCohort", {})
    items = cohort.get("items", [])
    by_name = {item.get("name"): item for item in items}
    _require(
        cohort.get("count") == 14
        and cohort.get("fileCount") == 19
        and cohort.get("bytes") == 58356
        and set(cohort.get("names", [])) == EXPECTED_NAMES
        and len(items) == 14
        and set(by_name) == EXPECTED_NAMES
        and "NUL" in cohort.get("treeManifestAlgorithm", ""),
        "CC 3.19 cohort coverage drifted",
    )
    expected_shape = {
        "design-an-interface": (1, 3460),
        "edit-article": (1, 735),
        "qa": (1, 5095),
        "request-refactor-plan": (1, 2779),
        "review": (1, 6406),
        "setup-pre-commit": (1, 2352),
        "setup-project-skills": (6, 13532),
        "to-issues": (1, 4082),
        "to-prd": (1, 3643),
        "ubiquitous-language": (1, 4890),
        "writing-beats": (1, 2888),
        "writing-fragments": (1, 3400),
        "writing-shape": (1, 4657),
        "zoom-out": (1, 437),
    }
    for name, (file_count, byte_count) in expected_shape.items():
        item = by_name[name]
        _require(
            item.get("fileCount") == file_count
            and item.get("bytes") == byte_count
            and isinstance(item.get("dbContentHash"), str)
            and len(item["dbContentHash"]) == 64
            and isinstance(item.get("currentTreeManifestSha256"), str)
            and len(item["currentTreeManifestSha256"]) == 64,
            f"CC 3.19 cohort item drifted: {name}",
        )
    rotation = document.get("backupRotation", {})
    _require(
        rotation.get("currentBackupCount") == 20
        and rotation.get("retention") == 20
        and rotation.get("newBackupsIfAllFourteenSucceed") == 14
        and rotation.get("expectedEvictionCount") == 14
        and len(rotation.get("expectedEvictedBackupIds", [])) == 14
        and len(rotation.get("expectedRetainedExistingBackupIds", [])) == 6
        and rotation.get("projectionAssumesNoConcurrentBackupCreation") is True
        and rotation.get("managerWillPerformEvictionAutomatically") is True
        and rotation.get("evictionRequiresExplicitAuthorization") is True,
        "CC 3.19 backup rotation drifted",
    )
    transaction = document.get("transactionAndRollback", {})
    _require(
        transaction.get("canary") == "edit-article"
        and transaction.get("remainingBatchCount") == 13
        and transaction.get("createAndVerifySecretScreenedExactRecoveryArchiveBeforeCanary")
        is True
        and transaction.get("invokeUninstallSequentiallyAndStopOnFirstFailure")
        is True
        and transaction.get("removeExactFourteenBrokenAgentsLinksOnlyAfterFullManagerSuccess")
        is True
        and transaction.get("requestAndVerifyOneConfiguredRemoteSnapshot") is True
        and transaction.get("exactlyCleanRecoveryArchiveAndDebugBridgeAfterDurableEvidence")
        is True
        and transaction.get("restoreCompletedUninstallsInReverseOrder") is True
        and transaction.get("restoreSecondHostWith")
        == "toggle_skill_app app=codex enabled=true"
        and transaction.get("firstPartyCurrentPhysicalTreesAreUnchangedSentinels")
        is True
        and transaction.get("docPdfPolicyMatt22AndTraeRootsAreUnchangedSentinels")
        is True,
        "CC 3.19 transaction or rollback drifted",
    )
    post = document.get("expectedPostStateIfOnlyThisTransactionRunsFromCurrentSnapshot", {})
    _require(
        post.get("databaseRows") == 41
        and post.get("databaseDistinctNames") == 41
        and post.get("ccSwitchEntries") == 41
        and post.get("agentsEntries") == 27
        and post.get("claudeEntries") == 41
        and post.get("codexTopLevelEntries") == 41
        and post.get("brokenLinksAcrossFourRoots") == 0
        and post.get("docAndPdfRemainSharedAndCodexDisabled") is True
        and post.get("mattPromotedRowsRemain") == 22
        and post.get("selfAuthoredRowsRemain") == 3
        and post.get("diagnoseRemains") is True
        and post.get("forecastBinding") is True
        and post.get("invalidatedByConcurrentCcMutation") is True,
        "CC 3.19 expected post-state drifted",
    )
    _require(
        len(document.get("authorizationRequired", [])) == 5
        and "the three self-authored CC rows or their Claude links"
        in document.get("explicitlyOutOfScope", [])
        and "any first-party .agents or .codex physical directory mutation"
        in document.get("explicitlyOutOfScope", []),
        "CC 3.19 authorization boundary drifted",
    )
    _require(
        document.get("cleanup")
        == {
            "temporarySourceRootCreated": False,
            "temporarySourceRootAbsent": True,
            "noTransactionArchiveCreatedYet": True,
            "noDebugListenerOrBridgeCreated": True,
            "noManagerHostOrConfigMutation": True,
        },
        "CC 3.19 cleanup boundary drifted",
    )
    claims = document.get("claimBoundary", {})
    _require(
        claims.get("live319ManagerSemanticsRefreshed") is True
        and claims.get("exactCurrentCohortRowsShapesLinksAndExposureProved")
        is True
        and claims.get("currentTreeManifestDigestsFrozenUnderDeclaredAlgorithm")
        is True
        and claims.get("backupRotationProjectedNotExecuted") is True
        and claims.get("firstPartyCollisionExcludedFromCohort") is True
        and claims.get("liveUninstallAuthorized") is False
        and claims.get("liveUninstallExecuted") is False
        and claims.get("postStateProved") is False
        and claims.get("behavioralValueOfRemainingPortfolioProved") is False
        and claims.get("programCloseoutProved") is False,
        "CC 3.19 claim boundary drifted",
    )
    _require(
        document.get("documentation") == DOCUMENTATION_PATH,
        "CC 3.19 documentation binding drifted",
    )
    text = (root / DOCUMENTATION_PATH).read_text(encoding="utf-8")
    for phrase in (
        "Ordinary manager uninstall therefore unlinks the two host",
        "That source-level safety distinction does not authorize the transaction.",
        "new current tree-manifest digests under an explicit",
        "automatic deletion",
        "`edit-article` remains the one-file canary",
        "pending authorization still has five exact parts",
        "the three self-authored rows",
    ):
        _require(
            phrase in text,
            f"CC 3.19 documentation missing: {phrase}",
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    root = args.root.resolve()
    for evidence_path in (EVIDENCE_PATH, LAYERED_EVIDENCE_PATH):
        document = json.loads(
            (root / evidence_path).read_text(encoding="utf-8")
        )
        validate_refresh(document, root=root)
    print(
        "CC Switch 3.19 fourteen-Skill subtraction refreshes passed."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
