#!/usr/bin/env python3
"""Validate the Claude carrier and subtraction sequencing decision preview."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_PATH = (
    "registry/"
    "self-authored-three-claude-carrier-and-subtraction-sequencing-"
    "decision-preview-2026-07-30.json"
)
DOC_PATH = (
    "docs/strategy/"
    "SELF-AUTHORED-THREE-CLAUDE-CARRIER-AND-SUBTRACTION-SEQUENCING-"
    "DECISION-PREVIEW-2026-07-30.md"
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def validate_preview(document: dict[str, Any], *, root: Path = ROOT) -> None:
    _require(
        document.get("schema") == 1
        and document.get("id")
        == "self-authored-three-claude-carrier-and-subtraction-sequencing-decision-preview-2026-07-30"
        and document.get("status")
        == "read-only-decision-ready-recommend-source-owned-claude-links-after-fourteen-subtraction",
        "Claude carrier decision identity drifted",
    )
    authority = document.get("authorityBoundary", {})
    _require(
        authority.get("readRepositoriesLocalHostAndOfficialPublicDocs") is True
        and authority.get("writeHarnessDecisionEvidence") is True
        and all(
            authority.get(key) is False
            for key in (
                "modifyCodexUserConfigInstaller",
                "ccSwitchMutation",
                "claudeCodexAgentsOrGlobalConfigMutation",
                "interactiveClaudeSessionOrModelDispatch",
                "recoveryArchiveRemoteSnapshotOrBackupRotation",
                "gitCommitOrPush",
            )
        ),
        "Claude carrier decision authority drifted",
    )
    official = document.get("officialClaudeCodeContract", {})
    _require(
        official.get("documentationUrl")
        == "https://code.claude.com/docs/en/skills"
        and official.get("localVersion") == "2.1.220"
        and official.get("directAgentsRootDiscoveryDocumented") is False
        and official.get("directorySymlinkSupportMinimumVersion") == "2.1.203"
        and official.get("currentVersionMeetsDocumentedSymlinkMinimum") is True
        and official.get(
            "documentedPrecedenceIndependentlyVerifiedAgainstCurrentRuntime"
        )
        is False
        and official.get("documentedPrecedenceHasUnresolvedOfficialIssueReport")
        is True
        and official.get("precedenceIssueUrl")
        == "https://github.com/anthropics/claude-code/issues/53288"
        and official.get("sameTargetReachableFromMultipleLocationsLoadsOnce")
        is True
        and official.get("pluginSkillsAreNamespaced") is True
        and official.get("officialStandaloneNoModelCliInventoryCommandFound")
        is False,
        "Claude official carrier contract drifted",
    )
    local = document.get("localClaudeState", {})
    _require(
        local.get("version") == "2.1.220"
        and local.get("claudeSkillEntries") == 55
        and local.get("agentsSkillEntries") == 41
        and local.get("codexSkillEntries") == 55
        and local.get("threeClaudeEntriesAreSymlinksToLegacyCcTrees") is True
        and local.get("threeAgentsEntriesAreCurrentPhysicalSourceProjections")
        is True
        and local.get("threeCodexEntriesAreCurrentPhysicalSourceProjections")
        is True
        and local.get("threeCurrentSourceSkillMdLineCounts")
        == {
            "intent-contract": 504,
            "capability-router": 419,
            "closure-contract": 253,
        }
        and local.get("allThreeCurrentSkillMdStayUnderOfficial500LineGuidance")
        is False
        and local.get("intentContractLinesOverGuidance") == 4
        and local.get("official500LineGuidanceIsKnownHardLoaderLimit") is False
        and local.get("lineGuidanceWarningBlocksStaticAdapterEligibility")
        is False
        and local.get("skillsDirItemsAreRegisteredPlugins") is False
        and local.get("pluginListResultDoesNotDisproveStandaloneSkillDiscovery")
        is True
        and local.get("freshStandaloneClaudeLoaderExposureProved") is False,
        "Claude local carrier state drifted",
    )
    adapter = document.get("sourceOwnedAdapter", {})
    _require(
        adapter.get("recommendedTargetShape")
        == "~/.claude/skills/<name> symbolic-link -> ~/.agents/skills/<name>"
        and adapter.get("usesDocumentedClaudePersonalSkillLocation") is True
        and adapter.get("usesDocumentedDirectorySymlinkSupport") is True
        and adapter.get("requiresCustomLoaderOrHook") is False
        and adapter.get("requiresPluginPackaging") is False
        and adapter.get("duplicatesSkillBodyBytes") is False
        and adapter.get("keepsCcSwitchAsOwnerOfSharedThirdPartySkills") is True
        and adapter.get("keepsCodexUserConfigAsOwnerOfFirstPartyThree") is True
        and adapter.get("requiresCodexUserConfigInstallerChange") is True
        and adapter.get("installerChangeAuthorized") is False
        and adapter.get("liveProjectionChangeAuthorized") is False,
        "Claude source-owned adapter decision drifted",
    )
    decision = document.get("optionDecision", {})
    options = {item.get("id"): item for item in decision.get("options", [])}
    _require(
        set(options)
        == {
            "A-quarantine-claude-legacy",
            "B-source-owned-claude-symlink-adapter",
        }
        and options["A-quarantine-claude-legacy"].get("recommended") is False
        and options["B-source-owned-claude-symlink-adapter"].get("recommended")
        is True
        and decision.get("recommendedOption")
        == "B-source-owned-claude-symlink-adapter"
        and decision.get("userDecisionStillRequired") is True,
        "Claude A/B decision drifted",
    )
    transaction = document.get("collisionSafeFirstPartyTransactionPreview", {})
    simulation = transaction.get("windowsSimulation", {})
    _require(
        transaction.get("ordinaryCcUninstallRemainsUnsafeAgainstCurrentPhysicalCodexTrees")
        is True
        and len(transaction.get("perSkillSequence", [])) == 4
        and len(transaction.get("postManagerSequenceForRecommendedB", [])) == 4
        and simulation.get("stagedLinkRenameIntoAbsentDestinationPassed") is True
        and simulation.get("atomicReplaceOverExistingDirectorySymlinkPassed")
        is False
        and simulation.get("atomicReplaceFailure") == "PermissionError WinError 5"
        and transaction.get("directDatabaseWriteRequired") is False
        and transaction.get("ordinaryCcUninstallWithoutCodexQuarantineAllowed")
        is False
        and transaction.get("mutationAuthorized") is False,
        "Claude collision-safe transaction preview drifted",
    )
    sequencing = document.get("transactionSequencing", {})
    phase1 = sequencing.get("phase1Fourteen", {})
    phase2 = sequencing.get("phase2FirstPartyThree", {})
    _require(
        sequencing.get("currentBackupCount") == 20
        and sequencing.get("fourteenFirstRecommended") is True
        and phase1.get("databaseRowsAfter") == 41
        and len(phase1.get("evictsOriginalBackups", [])) == 14
        and phase1.get("coveredByExistingFivePartAuthorizationRequest") is True
        and phase2.get("databaseRowsAfter") == 38
        and phase2.get("additionalOriginalBackupEvictionsIfNoConcurrentBackup")
        == [
            "20260729_093746_21risk-automation",
            "20260729_093826_git-guardrails",
            "20260729_093827_git-guardrails-claude-code",
        ]
        and phase2.get("requiresNewExplicitBackupEvictionAuthorization") is True
        and phase2.get("finalOriginalBackupsRetained")
        == [
            "20260729_093827_scaffold-exercises",
            "20260729_093827_write-a-skill",
            "20260729_093827_sora",
        ]
        and sequencing.get("totalOriginalBackupEvictionsAcrossBothPhases") == 17
        and sequencing.get("sameFinalOriginalEvictionSetIfFirstPartyRunsFirst")
        is True
        and sequencing.get("firstPartyFirstInvalidatesCurrentFourteenPreflight")
        is True,
        "Claude and fourteen transaction sequencing drifted",
    )
    initial_order = (
        phase1["evictsOriginalBackups"]
        + phase2["additionalOriginalBackupEvictionsIfNoConcurrentBackup"]
        + phase2["finalOriginalBackupsRetained"]
    )
    simulated = list(initial_order)
    evicted: list[str] = []
    for index in range(14):
        simulated.append(f"phase1-new-{index + 1:02d}")
        evicted.append(simulated.pop(0))
    phase1_evicted = list(evicted)
    for index in range(3):
        simulated.append(f"phase2-new-{index + 1:02d}")
        evicted.append(simulated.pop(0))
    _require(
        len(initial_order) == 20
        and phase1_evicted == phase1["evictsOriginalBackups"]
        and evicted
        == (
            phase1["evictsOriginalBackups"]
            + phase2["additionalOriginalBackupEvictionsIfNoConcurrentBackup"]
        )
        and simulated[:3] == phase2["finalOriginalBackupsRetained"]
        and len(simulated) == 20,
        "Claude and fourteen backup retention simulation drifted",
    )
    topology = document.get("projectedFinalTopologyIfRecommendedBThenSucceeds", {})
    _require(
        topology
        == {
            "databaseRows": 38,
            "ccSwitchEntries": 38,
            "agentsEntries": 27,
            "claudeEntries": 41,
            "codexTopLevelEntries": 41,
            "firstPartyRowsInCcSwitch": 0,
            "firstPartyCcBodies": 0,
            "firstPartyAgentsPhysicalTrees": 3,
            "firstPartyCodexPhysicalTrees": 3,
            "firstPartyClaudeLinksToAgents": 3,
            "brokenLinksAcrossManagedRoots": 0,
            "forecastOnly": True,
        },
        "Claude recommended final topology projection drifted",
    )
    claims = document.get("claimBoundary", {})
    _require(
        claims.get("officialClaudeDirectorySymlinkSupportProvedForCurrentVersion")
        is True
        and all(
            claims.get(key) is False
            for key in (
                "directAgentsRootDiscoveryProved",
                "currentLegacyClaudeLinkLoaderExposureProved",
                "recommendedAdapterLiveExposureProved",
                "recommendedAdapterInvocationBehaviorOrValueProved",
                "firstPartyRetirementAuthorized",
                "fourteenSubtractionAuthorizedByThisRecord",
                "combinedPostStateProved",
                "programCloseoutProved",
            )
        ),
        "Claude carrier claim boundary drifted",
    )
    _require(
        document.get("documentation") == DOC_PATH,
        "Claude carrier documentation binding drifted",
    )
    text = (root / DOC_PATH).read_text(encoding="utf-8")
    for phrase in (
        "B: source-owned Claude symlink adapter",
        "v2.1.203",
        "`~/.agents/skills`",
        "WinError 5",
        "four lines above",
        "seventeen original backups",
        "Run the fourteen-item transaction first",
        "forecasts, not a proved post-state",
        "not a standalone Skill inventory",
    ):
        _require(
            phrase in text,
            f"Claude carrier documentation missing: {phrase}",
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    root = args.root.resolve()
    document = json.loads((root / EVIDENCE_PATH).read_text(encoding="utf-8"))
    validate_preview(document, root=root)
    print("Self-authored three Claude carrier decision preview passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
