#!/usr/bin/env python3
"""Validate the dated CC Switch subtraction and Codex shadow-disable event."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_PATH = (
    "registry/"
    "cc-switch-subtraction-cohort-and-codex-shadow-disable-event-2026-07-29.json"
)
DOCUMENTATION_PATH = (
    "docs/strategy/"
    "CC-SWITCH-SUBTRACTION-COHORT-AND-CODEX-SHADOW-DISABLE-EVENT-2026-07-29.md"
)
EXPECTED_REMOVED = {
    "-21risk-automation",
    "git-guardrails",
    "git-guardrails-claude-code",
    "scaffold-exercises",
    "sora",
    "write-a-skill",
}
EXPECTED_RETAINED = {
    "capability-router",
    "caveman",
    "closure-contract",
    "intent-contract",
    "kimi-webbridge",
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def validate_event(document: dict[str, Any], *, root: Path = ROOT) -> None:
    _require(
        document.get("schema") == 1
        and document.get("id")
        == "cc-switch-subtraction-cohort-and-codex-shadow-disable-event-2026-07-29"
        and document.get("date") == "2026-07-29"
        and document.get("status")
        == "live-subtraction-cohort-and-codex-shadow-disable-verified-current-host",
        "CC Switch subtraction event identity drifted",
    )
    authority = document.get("authorityBoundary")
    _require(
        isinstance(authority, dict)
        and authority.get("userAuthorizedExactTransaction") is True
        and authority.get("ccSwitchBackendWasMutationSurface") is True
        and authority.get("agentsBrokenLinksRemovedSeparately") is True
        and authority.get("traeRootsExcluded") is True
        and authority.get("sharedRootPreserved") is True
        and authority.get("ccSwitchStorageModeChanged") is False
        and authority.get("directDatabaseWrite") is False
        and authority.get("accountOrCredentialRead") is False
        and authority.get("hookMutation") is False
        and authority.get("agentsRulesMutation") is False
        and authority.get("modelDispatch") is False
        and authority.get("gitCommitOrPush") is False,
        "CC Switch subtraction authority boundary drifted",
    )
    _require(
        set(document.get("removedSkills", [])) == EXPECTED_REMOVED
        and document.get("removedSkills") == sorted(EXPECTED_REMOVED),
        "CC Switch subtraction cohort drifted",
    )
    _require(
        document.get("codexOnlyDisabledSkills") == ["doc", "pdf"],
        "CC Switch Codex-only disable cohort drifted",
    )
    _require(
        set(document.get("explicitlyRetainedSkills", [])) == EXPECTED_RETAINED,
        "CC Switch explicit retention cohort drifted",
    )
    pre = document.get("preState")
    _require(
        isinstance(pre, dict)
        and pre.get("databaseRows") == 61
        and pre.get("databaseDistinctNames") == 60
        and pre.get("databaseDuplicateNames") == {"git-guardrails": 2}
        and pre.get("enabledClaudeRows") == 61
        and pre.get("enabledCodexRows") == 61,
        "CC Switch subtraction pre-state drifted",
    )
    recovery = document.get("recoveryPreflight")
    _require(
        isinstance(recovery, dict)
        and recovery.get("secretScreenedArchiveCreated") is True
        and recovery.get("rawDatabaseCopied") is False
        and recovery.get("settingsRead") is False
        and recovery.get("secretMatches") == 0
        and recovery.get("sourceConsistencyPassed") is True
        and recovery.get("archiveVerificationPassed") is True,
        "CC Switch subtraction recovery evidence drifted",
    )
    execution = document.get("execution")
    _require(
        isinstance(execution, dict)
        and execution.get("canarySkill") == "-21risk-automation"
        and execution.get("canarySucceeded") is True
        and execution.get("remainingUninstallCount") == 5
        and execution.get("remainingUninstallSucceeded") == 5
        and execution.get("failedUninstalls") == 0
        and execution.get("codexOnlyToggleCount") == 2
        and execution.get("codexOnlyTogglesSucceeded") == 2
        and execution.get("agentsBrokenLinkCleanupCount") == 5
        and execution.get("agentsBrokenLinkCleanupSucceeded") == 5
        and len(execution.get("exactManagerBackupsRetained", [])) == 6
        and execution.get("explicitRemoteSyncStatus") == "uploaded"
        and execution.get("remoteSnapshotCompatible") is True
        and execution.get("remoteSnapshotArtifacts") == ["db.sql", "skills.zip"],
        "CC Switch subtraction execution evidence drifted",
    )
    post = document.get("postState")
    _require(
        isinstance(post, dict)
        and post.get("databaseRows") == 55
        and post.get("databaseDistinctNames") == 55
        and post.get("enabledClaudeRows") == 55
        and post.get("enabledCodexRows") == 53
        and post.get("sourceCounts")
        == {"localOrUnattributed": 33, "mattpocock": 22}
        and post.get("ccSwitchEntries") == 55
        and post.get("agentsEntries") == 41
        and post.get("claudeEntries") == 55
        and post.get("codexTopLevelEntries") == 55
        and post.get("codexManagedResolvableSkillMd") == 53
        and post.get("brokenSkillLinks")
        == {"ccSwitch": 0, "agents": 0, "claude": 0, "codex": 0}
        and post.get("removedSkillsAbsentAcrossCcAgentsClaudeCodex") is True
        and post.get("docAndPdfRemainInCcAgentsClaude") is True
        and post.get("docAndPdfAbsentFromCodexProjection") is True
        and post.get("retainedSkillsRemainClaudeAndCodexEnabled") is True
        and post.get("ccSwitchProcessCount") == 1
        and post.get("temporaryDebugPortOpen") is False,
        "CC Switch subtraction post-state drifted",
    )
    foreign = document.get("foreignRootObservation")
    _require(
        isinstance(foreign, dict)
        and foreign.get("transactionTargetsExcludedTrae") is True
        and foreign.get("traeCommonRootExists") is True
        and foreign.get("traePluginRootExists") is True
        and foreign.get("prePostContentHashSentinelAvailable") is False,
        "CC Switch subtraction foreign-root boundary drifted",
    )
    cleanup = document.get("cleanup")
    _require(
        isinstance(cleanup, dict)
        and cleanup.get("temporaryRecoveryRootRetained") is False
        and cleanup.get("temporaryRecoveryRootAbsent") is True
        and cleanup.get("temporaryCdpHelperAbsent") is True
        and cleanup.get("ccSwitchManagedBackupsRetained") is True
        and cleanup.get("repositoryCleanupInventoryStable") is True,
        "CC Switch subtraction cleanup evidence drifted",
    )
    verification = document.get("verification")
    _require(
        isinstance(verification, dict)
        and verification.get("semanticAuthorityExtendedTestCount") == 24
        and verification.get("semanticAuthorityExtendedTestsPassed") is True
        and verification.get("eventValidatorTestsPassed") is True
        and verification.get("topLevelVerifierPassed") is True,
        "CC Switch subtraction verification evidence drifted",
    )
    claims = document.get("claimBoundary")
    _require(
        isinstance(claims, dict)
        and claims.get("exactSharedSubtractionProved") is True
        and claims.get("codexShadowDisableProved") is True
        and claims.get("claudeRetentionForDocAndPdfProved") is True
        and claims.get("freshTaskCatalogRefreshObserved") is False
        and claims.get("loaderInvocationProved") is False
        and claims.get("behavioralValueProved") is False
        and claims.get("remainingPortfolioQualityProved") is False
        and claims.get("selfAuthoredChainDispositioned") is False
        and claims.get("programCloseoutProved") is False,
        "CC Switch subtraction claim boundary drifted",
    )
    _require(
        document.get("documentation") == DOCUMENTATION_PATH,
        "CC Switch subtraction documentation binding drifted",
    )
    text = (root / DOCUMENTATION_PATH).read_text(encoding="utf-8")
    for phrase in (
        "exact shared subtraction and Codex-only shadow disable verified",
        "The common root itself was preserved.",
        "disabled only their Codex projection",
        "SQLite was read only for verification",
        "claims bounded target exclusion rather than byte-level foreign-root",
        "does not prove loader",
    ):
        _require(
            phrase in text,
            f"CC Switch subtraction documentation missing: {phrase}",
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    root = args.root.resolve()
    document = json.loads((root / EVIDENCE_PATH).read_text(encoding="utf-8"))
    validate_event(document, root=root)
    print("CC Switch subtraction and Codex shadow-disable event passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
