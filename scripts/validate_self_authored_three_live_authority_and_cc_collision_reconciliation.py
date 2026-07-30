#!/usr/bin/env python3
"""Validate the self-authored three authority and CC collision record."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_PATH = (
    "registry/"
    "self-authored-three-live-authority-and-cc-collision-reconciliation-"
    "2026-07-30.json"
)
DOCUMENTATION_PATH = (
    "docs/strategy/"
    "SELF-AUTHORED-THREE-LIVE-AUTHORITY-AND-CC-COLLISION-"
    "RECONCILIATION-2026-07-30.md"
)
EXPECTED_NAMES = {
    "intent-contract",
    "capability-router",
    "closure-contract",
}
EXPECTED_CURRENT_TREES = {
    "intent-contract": (
        2,
        50087,
        "67d30201ed6ab42f65ae896e55ad3594a5bf97402db9cc1ba980b0b7494a7e1d",
    ),
    "capability-router": (
        2,
        32126,
        "193a2e413084aa2d2a7714bbaddfaf076393c7c4c9ce049709129f1afb8bce1a",
    ),
    "closure-contract": (
        1,
        12187,
        "5a6924e0efe9153307003322b9ee0d5cd3efae40cc0067fe0a1b84cc67d8fd99",
    ),
}
EXPECTED_LEGACY_TREES = {
    "intent-contract": (
        2,
        41369,
        "9d716e595dcfc1b0e6e471dbe72f34d6491ec84387b45de5c422769d28e5224e",
    ),
    "capability-router": (
        2,
        21375,
        "a313d8cb76fe34c63066a404e68495cd6ef16e5031a6335eee3ab4ff1f05a79b",
    ),
    "closure-contract": (
        1,
        7872,
        "2933dc8485c495b3afcfc643184c56959c4104d87c3641ab24a5e62aa9fedeea",
    ),
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def validate_reconciliation(
    document: dict[str, Any],
    *,
    root: Path = ROOT,
) -> None:
    _require(
        document.get("schema") == 1
        and document.get("id")
        == "self-authored-three-live-authority-and-cc-collision-reconciliation-2026-07-30"
        and document.get("date") == "2026-07-30"
        and document.get("status")
        == "read-only-authority-proved-cc-ownership-collision-blocks-ordinary-manager-actions",
        "Self-authored collision record identity drifted",
    )
    posture = document.get("repositoryPosture", {})
    _require(
        posture.get("branch") == "main"
        and posture.get("head")
        == "55659f30091990f7c589932e0379880de30dc403"
        and posture.get("originMain") == posture.get("head")
        and posture.get("upstream") == "origin/main"
        and posture.get("ahead") == 0
        and posture.get("behind") == 0
        and posture.get("worktreeIntentionallyLargeAndDirty") is True
        and posture.get("inheritedChangesPreserved") is True,
        "Self-authored collision repository posture drifted",
    )
    authority = document.get("authorityBoundary", {})
    _require(
        authority.get("readHarnessAndSourceRepositories") is True
        and authority.get("readLiveCcDatabaseSettingsAndInstalledTrees") is True
        and authority.get("readCurrentHostExposureWithoutModelDispatch") is True
        and authority.get("readCurrentOfficialCcSwitchTagSource") is True
        and authority.get("skillBodyExecution") is False
        and authority.get("modelDispatch") is False
        and authority.get("ccSwitchMutation") is False
        and authority.get("skillInstallUpdateDisableDeleteOrRelink") is False
        and authority.get("globalConfigRulesHookOrForeignRootMutation") is False
        and authority.get("gitCommitOrPush") is False,
        "Self-authored collision authority boundary drifted",
    )
    source = document.get("sourceAuthority", {})
    installer = source.get("installer", {})
    _require(
        source.get("repositoryPath") == "C:/Projects/codex-user-config"
        and source.get("branch") == "main"
        and source.get("head")
        == "0c93458d48cb1ebaa6d0d289e3a21f46d2f61f65"
        and source.get("originMain") == source.get("head")
        and source.get("ahead") == 0
        and source.get("behind") == 0
        and source.get("threeSkillTreesCleanAtHead") is True
        and "current source authority"
        in source.get("declaredRole", "")
        and set(installer.get("firstPartySkills", [])) == EXPECTED_NAMES
        and installer.get("targetRoots")
        == [".agents/skills", ".codex/skills"]
        and installer.get("claudeTargetDefined") is False
        and installer.get("ccSwitchTargetDefined") is False,
        "Self-authored source authority drifted",
    )
    manager = document.get("liveManager", {})
    settings = manager.get("settings", {})
    official = manager.get("officialSource", {})
    _require(
        manager.get("binaryFileVersion") == "3.19.0"
        and manager.get("binaryProductVersion") == "3.19.0"
        and manager.get("databaseRows") == 55
        and settings.get("skillStorageLocation") == "cc_switch"
        and settings.get("skillSyncMethod") == "symlink"
        and settings.get("skillPathOverridesObserved") is False
        and settings.get("defaultCodexTarget")
        == "C:/Users/15521/.codex/skills"
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
        "Self-authored current manager or source identity drifted",
    )
    rows = manager.get("threeRows", [])
    rows_by_name = {row.get("name"): row for row in rows}
    _require(
        len(rows) == 3 and set(rows_by_name) == EXPECTED_NAMES,
        "Self-authored CC row coverage drifted",
    )
    for name, row in rows_by_name.items():
        _require(
            row.get("id") == f"local:{name}"
            and row.get("directory") == name
            and row.get("repoOwner") is None
            and row.get("repoName") is None
            and row.get("repoBranch") is None
            and row.get("enabledClaude") is True
            and row.get("enabledCodex") is True
            and row.get("enabledGemini") is False
            and row.get("enabledOpenCode") is False
            and row.get("enabledHermes") is False
            and row.get("enabledGrokBuild") is False
            and isinstance(row.get("contentHash"), str)
            and len(row["contentHash"]) == 64,
            f"Self-authored CC row drifted: {name}",
        )
    packages = document.get("packages", [])
    packages_by_name = {item.get("name"): item for item in packages}
    _require(
        len(packages) == 3 and set(packages_by_name) == EXPECTED_NAMES,
        "Self-authored package coverage drifted",
    )
    for name in EXPECTED_NAMES:
        package = packages_by_name[name]
        current = package.get("currentSourceProjection", {})
        legacy = package.get("legacyCcProjection", {})
        current_count, current_bytes, current_hash = EXPECTED_CURRENT_TREES[name]
        legacy_count, legacy_bytes, legacy_hash = EXPECTED_LEGACY_TREES[name]
        _require(
            len(current.get("roots", [])) == 3
            and current.get("allRootsArePhysicalDirectories") is True
            and current.get("allRootsByteEqual") is True
            and current.get("fileCount") == current_count
            and current.get("bytes") == current_bytes
            and current.get("treeManifestSha256") == current_hash
            and len(current.get("files", [])) == current_count,
            f"Self-authored current tree drifted: {name}",
        )
        _require(
            legacy.get("ccRootIsPhysicalDirectory") is True
            and legacy.get("claudePathType") == "symbolic-link"
            and legacy.get("claudeTarget") == legacy.get("ccRoot")
            and legacy.get("claudeAndCcByteEqual") is True
            and legacy.get("fileCount") == legacy_count
            and legacy.get("bytes") == legacy_bytes
            and legacy.get("treeManifestSha256") == legacy_hash
            and len(legacy.get("files", [])) == legacy_count
            and legacy.get("matchesCurrentSourceProjection") is False,
            f"Self-authored legacy tree drifted: {name}",
        )
    exposure = document.get("codexExposure", {})
    _require(
        exposure.get("inventoryCount") == 64
        and exposure.get("matchingEntries") == 6
        and exposure.get("entriesPerLogicalName") == 2
        and len(exposure.get("paths", [])) == 6
        and exposure.get("allMatchingEntriesUserScoped") is True
        and exposure.get("allMatchingEntriesEnabled") is True
        and exposure.get("modelTurnSent") is False
        and exposure.get("provesDuplicateDiscovery") is True
        and exposure.get("provesInvocation") is False
        and exposure.get("provesInstructionDelivery") is False
        and exposure.get("provesBehavior") is False
        and exposure.get("provesValue") is False,
        "Self-authored Codex exposure boundary drifted",
    )
    claude = document.get("claudeExposure", {})
    _require(
        claude.get("staticSymlinkProjectionObserved") is True
        and claude.get("allThreeLinksResolveToLegacyCcTrees") is True
        and claude.get("freshClaudeLoaderExposureProved") is False
        and claude.get("invocationProved") is False
        and claude.get("instructionDeliveryProved") is False
        and claude.get("behaviorProved") is False
        and claude.get("valueProved") is False,
        "Self-authored Claude exposure boundary drifted",
    )
    collision = document.get("managerCollision", {})
    required_true = {
        "currentRowDirectoriesPassSingleSegmentShape",
        "uninstallCommandCallsSkillServiceUninstall",
        "uninstallIteratesAllAppTypes",
        "allAppTypesIncludesClaudeAndCodex",
        "codexDestinationResolvesToPhysicalFirstPartyDirectory",
        "uninstallRemoveFromAppIgnoresEnabledFlags",
        "removePathUnlinksSymlinksOnly",
        "removePathRecursivelyDeletesPhysicalDirectories",
        "ordinaryUninstallWouldDeleteCurrentPhysicalCodexProjection",
        "ordinaryUninstallWouldRemoveClaudeLegacySymlink",
        "ordinaryCodexDisableWouldDeleteCurrentPhysicalCodexProjection",
        "ordinaryCodexEnableOrSyncWithSymlinkModeWouldDeleteCurrentPhysicalCodexProjectionBeforeCreatingCcLink",
        "uninstallBackupProtectsCcBodyAndMetadataOnly",
        "uninstallBackupDoesNotProtectExternallyOwnedNewerCodexProjection",
    }
    _require(
        all(collision.get(key) is True for key in required_true)
        and collision.get("ordinaryCcUninstallToggleOrSyncSafeForTheseThree")
        is False
        and len(collision.get("sourceReferences", [])) >= 7,
        "Self-authored manager collision boundary drifted",
    )
    references = document.get("diagnoseReferenceBoundary", {})
    _require(
        references.get("currentSourceCapabilityRouterStillNamesDiagnose") is True
        and references.get("legacyCcCapabilityRouterStillNamesDiagnose") is True
        and references.get("observabilitySkillStillNamesCanonicalDiagnose") is True
        and references.get("observabilitySkillStillContainsPiiLoggingExample")
        is True
        and references.get("promotedDiagnosingBugsExists") is True
        and references.get("mutationAuthorized") is False,
        "Self-authored diagnose reference boundary drifted",
    )
    decision = document.get("decision", {})
    choice_ids = {
        choice.get("id")
        for choice in decision.get("policyChoicesRequiringUserDecision", [])
    }
    _require(
        decision.get("canonicalSourceAuthority")
        == "C:/Projects/codex-user-config"
        and decision.get("commonAndCodexPhysicalCopiesAreCurrentSourceProjections")
        is True
        and decision.get("ccCopiesAreLegacyDivergentSnapshots") is True
        and decision.get("claudeLinksAreLegacyDivergentProjections") is True
        and decision.get("ccRowsAreNotSourceAuthority") is True
        and decision.get("ordinaryManagerMutationBlocked") is True
        and choice_ids
        == {"quarantine-claude-legacy", "source-owned-claude-adapter"}
        and decision.get("codexDualRootSimplificationIsSeparateGate") is True
        and decision.get("codexDualRootMutationAuthorized") is False
        and decision.get("firstPartyCcRetirementMutationAuthorized") is False
        and decision.get("diagnoseReferenceMutationAuthorized") is False
        and decision.get("priorFourteenPreviewRequiresManager319RefreshBeforeExecution")
        is True,
        "Self-authored decision boundary drifted",
    )
    _require(
        document.get("cleanup")
        == {
            "temporarySourceRootCreated": False,
            "temporarySourceRootAbsent": True,
            "noRecoveryArchiveCreated": True,
            "noDatabaseCopyCreated": True,
            "noSourceBodyExecuted": True,
            "noModelTurnSent": True,
            "noManagerOrHostMutation": True,
        },
        "Self-authored cleanup boundary drifted",
    )
    claims = document.get("claimBoundary", {})
    _require(
        claims.get("sourceAuthorityProvedForCurrentThreeTrees") is True
        and claims.get("currentSourceAgentsCodexByteParityProved") is True
        and claims.get("legacyCcClaudeDivergenceProved") is True
        and claims.get("codexDualRootNoModelExposureProved") is True
        and claims.get("currentCc319CollisionRiskProvedFromOfficialTagSource")
        is True
        and claims.get("binarySupplyChainIdentityToOfficialTagProved") is False
        and claims.get("claudeLoaderExposureProved") is False
        and claims.get("skillInvocationOrInstructionDeliveryProved") is False
        and claims.get("behavioralValueOrSuperiorityProved") is False
        and claims.get("crossHostParityRequired") is False
        and claims.get("retirementOrMigrationAuthorized") is False
        and claims.get("programCloseoutProved") is False,
        "Self-authored claim boundary drifted",
    )
    _require(
        document.get("documentation") == DOCUMENTATION_PATH,
        "Self-authored documentation binding drifted",
    )
    text = (root / DOCUMENTATION_PATH).read_text(encoding="utf-8")
    for phrase in (
        "This is an ownership collision, not a normal duplicate-name cleanup.",
        "Codex exposure is duplicate exposure, not value proof",
        "ordinary CC uninstall, Codex disable, Codex enable, or sync can",
        "Do not call ordinary CC uninstall, toggle, or sync",
        "Quarantine the Claude legacy projection",
        "Create a source-owned Claude adapter first",
        "Codex dual-root simplification is a separate gate",
        "must be refreshed against live 3.19.0",
    ):
        _require(
            phrase in text,
            f"Self-authored documentation missing: {phrase}",
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    root = args.root.resolve()
    document = json.loads((root / EVIDENCE_PATH).read_text(encoding="utf-8"))
    validate_reconciliation(document, root=root)
    print("Self-authored three authority and CC collision reconciliation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
