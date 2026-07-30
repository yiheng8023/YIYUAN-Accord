#!/usr/bin/env python3
"""Validate the current-55 Skill portfolio subtractive triage."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_PATH = (
    "registry/skill-portfolio-current-55-subtractive-triage-2026-07-30.json"
)
DOCUMENTATION_PATH = (
    "docs/strategy/SKILL-PORTFOLIO-CURRENT-55-SUBTRACTIVE-TRIAGE-2026-07-30.md"
)
EXPECTED_COHORT_COUNTS = {
    "current-matt-promoted-exact": 22,
    "self-authored-falsifiable-controls": 3,
    "explicit-user-or-host-exceptions": 2,
    "shared-entity-codex-shadow-disabled": 2,
    "strong-subtraction-candidates": 15,
    "source-rebinding-and-current-delta-review": 5,
    "task-bound-specialist-value-or-overlap-open": 6,
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def validate_triage(
    document: dict[str, Any],
    *,
    root: Path = ROOT,
) -> None:
    _require(
        document.get("schema") == 1
        and document.get("id")
        == "skill-portfolio-current-55-subtractive-triage-2026-07-30"
        and document.get("date") == "2026-07-30"
        and document.get("status")
        == "current-live-55-partitioned-read-only-subtraction-preview-open",
        "Current-55 triage identity drifted",
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
        "Current-55 repository posture drifted",
    )
    authority = document.get("authorityBoundary", {})
    _require(
        authority.get("readLiveCcDatabase") is True
        and authority.get("readInstalledSkillBodies") is True
        and authority.get("readPublicUpstreamSources") is True
        and authority.get("temporarySourceCloneAndExactCleanup") is True
        and authority.get("ccSwitchMutation") is False
        and authority.get("skillInstallUpdateDisableOrDelete") is False
        and authority.get("globalConfigMutation") is False
        and authority.get("hookMutation") is False
        and authority.get("agentsRulesMutation") is False
        and authority.get("modelDispatch") is False
        and authority.get("gitCommitOrPush") is False,
        "Current-55 authority boundary drifted",
    )
    manager = document.get("liveManagerState", {})
    _require(
        manager.get("databaseRows") == 55
        and manager.get("databaseDistinctNames") == 55
        and manager.get("claudeEnabledRows") == 55
        and manager.get("codexDatabaseEnabledRows") == 53
        and manager.get("sourceAttributedMattRows") == 22
        and manager.get("localOrUnattributedRows") == 33
        and manager.get("duplicateNameCount") == 0,
        "Current-55 manager state drifted",
    )
    exposure = document.get("liveCodexExposure", {})
    _require(
        exposure.get("host") == "Codex Desktop/0.146.0"
        and exposure.get("pluginEnabledSkillCount") == 76
        and exposure.get("sharedDocEnabled") is False
        and exposure.get("sharedPdfEnabled") is False
        and exposure.get("runtimeDocumentsEnabled") is True
        and exposure.get("runtimePdfEnabled") is True
        and exposure.get("modelRequestSent") is False,
        "Current-55 Codex exposure drifted",
    )
    source = document.get("sourceRefresh", {})
    matt = source.get("mattpocock", {})
    _require(
        matt.get("mainRevision")
        == "2ab958093e83e0ec752e6c1c5932da465bf23e0c"
        and matt.get("installedPinnedRevision") == matt.get("mainRevision")
        and matt.get("headMatchesInstalledPin") is True
        and matt.get("promotedSkillCount") == 22
        and matt.get("repositorySkillMdCount") == 41
        and matt.get("livePromotedWholeTreeRawBlobMismatchCount") == 0
        and matt.get("ccSnapshotStalenessObservedForPromotedSuite") is False,
        "Current-55 Matt source refresh drifted",
    )
    addy = source.get("addyosmani", {})
    _require(
        addy.get("mainRevision")
        == "7829ffd90d973b6325f5f12f1b1226dcace74443"
        and addy.get("lastReviewedRevision")
        == "06300e258ef62cdbfbc9b1615ac5b4f58bee05ac"
        and addy.get("headAdvancedSinceLastReview") is True
        and set(addy.get("selectedPathsChangedSinceLastReview", []))
        == {
            "skills/performance-optimization/SKILL.md",
            "skills/shipping-and-launch/SKILL.md",
        }
        and len(addy.get("liveSelectedSkills", [])) == 5
        and addy.get("liveRowsCarryCcSourceMetadata") is False
        and addy.get("liveBodiesEqualCurrentUpstreamAfterLfNormalization") == 0
        and addy.get("decision")
        == "retain-frozen-current-bodies-pending-source-rebinding-and-current-delta-review",
        "Current-55 Addy source refresh drifted",
    )
    partition = document.get("portfolioPartition", {})
    cohorts = partition.get("cohorts", [])
    _require(
        partition.get("partitionIsMutuallyExclusive") is True
        and partition.get("partitionCoversAllDatabaseRows") is True
        and partition.get("total") == 55
        and len(cohorts) == len(EXPECTED_COHORT_COUNTS),
        "Current-55 partition header drifted",
    )
    observed_counts: dict[str, int] = {}
    all_names: list[str] = []
    for cohort in cohorts:
        cohort_id = cohort.get("id")
        count = cohort.get("count")
        names = cohort.get("names", [])
        _require(
            isinstance(cohort_id, str)
            and isinstance(count, int)
            and isinstance(names, list)
            and count == len(names),
            "Current-55 cohort cardinality drifted",
        )
        observed_counts[cohort_id] = count
        all_names.extend(names)
    _require(
        observed_counts == EXPECTED_COHORT_COUNTS
        and len(all_names) == 55
        and len(set(all_names)) == 55,
        "Current-55 partition coverage or exclusivity drifted",
    )
    subtraction = document.get("subtractionEvidence", {})
    pairs = subtraction.get("supersededLegacyPairs", [])
    _require(
        {
            (item.get("candidate"), item.get("currentPromotedReplacement"))
            for item in pairs
        }
        == {
            ("diagnose", "diagnosing-bugs"),
            ("review", "code-review"),
            ("setup-project-skills", "setup-matt-pocock-skills"),
            ("to-issues", "to-tickets"),
            ("to-prd", "to-spec"),
        }
        and all(item.get("currentReplacementInstalledExact") is True for item in pairs),
        "Current-55 legacy replacement mapping drifted",
    )
    lifecycle = subtraction.get("currentMattNonPromotedLifecycle", {})
    _require(
        set(lifecycle.get("deprecated", []))
        == {
            "design-an-interface",
            "qa",
            "request-refactor-plan",
            "ubiquitous-language",
        }
        and set(lifecycle.get("inProgress", []))
        == {"writing-beats", "writing-fragments", "writing-shape"}
        and lifecycle.get("personal") == ["edit-article"]
        and lifecycle.get("misc") == ["setup-pre-commit"]
        and lifecycle.get("absentFromCurrentTree") == ["zoom-out"],
        "Current-55 non-promoted lifecycle drifted",
    )
    ready = set(subtraction.get("readyForManagerRemovalPreview", []))
    blocked = set(subtraction.get("blockedBeforeManagerRemoval", []))
    _require(
        len(ready) == 14
        and blocked == {"diagnose"}
        and ready.isdisjoint(blocked)
        and len(ready | blocked) == 15,
        "Current-55 removal preview boundary drifted",
    )
    gates = {
        item.get("candidate"): item
        for item in subtraction.get("referenceGates", [])
    }
    _require(
        gates.get("diagnose", {}).get("status") == "blocked-before-removal"
        and set(gates.get("diagnose", {}).get("exactOrSemanticDependents", []))
        == {"capability-router", "observability-and-instrumentation"}
        and gates.get("qa", {}).get("status")
        == "upstream-release-consistency-warning",
        "Current-55 reference gate drifted",
    )
    corrections = document.get("importantCorrections", [])
    _require(
        any("not the one-click installer" in item for item in corrections)
        and any("current main equals the installed pin" in item for item in corrections)
        and any("Removing diagnose now" in item for item in corrections),
        "Current-55 correction set drifted",
    )
    cleanup = document.get("cleanup", {})
    _require(
        cleanup
        == {
            "mattRefreshTempRootAbsent": True,
            "addyRefreshTempRootAbsent": True,
            "noSourceBodyExecuted": True,
            "repositoryCleanupInventoryStable": True,
        },
        "Current-55 cleanup evidence drifted",
    )
    claims = document.get("claimBoundary", {})
    _require(
        claims.get("currentLive55InventoryProved") is True
        and claims.get("mattPromotedSourceFreshnessAndTreeIdentityProved") is True
        and claims.get("addyCurrentSourceDriftProved") is True
        and claims.get("subtractionCandidateEligibilityProved") is True
        and claims.get("managerRemovalAuthorized") is False
        and claims.get("behavioralValueProvedForAllRetainedSkills") is False
        and claims.get("selfAuthoredDispositionProved") is False
        and claims.get("programCloseoutProved") is False,
        "Current-55 claim boundary drifted",
    )
    _require(
        document.get("documentation") == DOCUMENTATION_PATH,
        "Current-55 documentation binding drifted",
    )
    text = (root / DOCUMENTATION_PATH).read_text(encoding="utf-8")
    for phrase in (
        "live 55 partitioned",
        "covers all 55 distinct database rows exactly once",
        "There is no promoted-suite snapshot staleness",
        "not Matt's one-click cross-Agent installer",
        "Fourteen items are ready",
        "Removing it first would turn subtraction into a broken route",
        "sent no model request",
    ):
        _require(
            phrase in text,
            f"Current-55 documentation missing: {phrase}",
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    root = args.root.resolve()
    document = json.loads((root / EVIDENCE_PATH).read_text(encoding="utf-8"))
    validate_triage(document, root=root)
    print("Current-55 Skill portfolio subtractive triage passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
