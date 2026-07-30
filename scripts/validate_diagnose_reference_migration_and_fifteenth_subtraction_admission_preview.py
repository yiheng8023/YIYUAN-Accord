#!/usr/bin/env python3
"""Validate the diagnose reference migration and fifteenth admission preview."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_PATH = (
    "registry/"
    "diagnose-reference-migration-and-fifteenth-subtraction-admission-preview-"
    "2026-07-30.json"
)
DOCUMENTATION_PATH = (
    "docs/strategy/"
    "DIAGNOSE-REFERENCE-MIGRATION-AND-FIFTEENTH-SUBTRACTION-"
    "ADMISSION-PREVIEW-2026-07-30.md"
)


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
        == "diagnose-reference-migration-and-fifteenth-subtraction-admission-preview-2026-07-30"
        and document.get("date") == "2026-07-30"
        and document.get("status")
        == "read-only-reference-migration-preview-fifteenth-admission-blocked",
        "Diagnose migration preview identity drifted",
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
        "Diagnose migration repository posture drifted",
    )
    authority = document.get("authorityBoundary", {})
    _require(
        authority.get("readRepositoriesDatabaseInstalledTreesAndHostExposure")
        is True
        and authority.get("reuseExistingCurrentMattAdmissionEvidence") is True
        and authority.get("sourceSkillEdit") is False
        and authority.get("activeCcProjectionEdit") is False
        and authority.get("firstPartyCarrierRetirement") is False
        and authority.get("skillUninstallOrLinkCleanup") is False
        and authority.get("modelDispatch") is False
        and authority.get("globalConfigRulesHookOrForeignRootMutation") is False
        and authority.get("gitCommitOrPush") is False,
        "Diagnose migration authority boundary drifted",
    )
    legacy = document.get("currentLegacyCandidate", {})
    _require(
        legacy.get("name") == "diagnose"
        and legacy.get("databaseId") == "local:diagnose"
        and legacy.get("databaseSourceMetadataBound") is False
        and legacy.get("enabledClaude") is True
        and legacy.get("enabledCodex") is True
        and legacy.get("enabledOtherRecordedHosts") is False
        and legacy.get("fileCount") == 2
        and legacy.get("bytes") == 8328
        and legacy.get("treeManifestSha256")
        == "58d74dc854790dc503e3318d7aa1409a250e81e3f46fd8846acbb4066591cf71"
        and legacy.get("commonRootPathType") == "symbolic-link-to-cc"
        and legacy.get("freshNoModelCodexExposure") is True
        and legacy.get("databaseDescriptionEncodingCorruptionObserved") is True,
        "Diagnose legacy candidate evidence drifted",
    )
    replacement = document.get("currentPromotedReplacement", {})
    _require(
        replacement.get("name") == "diagnosing-bugs"
        and replacement.get("databaseId")
        == "mattpocock/skills:skills/engineering/diagnosing-bugs"
        and replacement.get("pinnedRevision")
        == "2ab958093e83e0ec752e6c1c5932da465bf23e0c"
        and replacement.get("installedTreeExactAtPinnedCurrentMain") is True
        and replacement.get("enabledClaude") is True
        and replacement.get("enabledCodex") is True
        and replacement.get("enabledOtherRecordedHosts") is False
        and replacement.get("fileCount") == 3
        and replacement.get("bytes") == 9803
        and replacement.get("treeManifestSha256")
        == "f6038c2a61532144539a684863428afa1c77e5da050bc969f7542f24bd50ea53"
        and replacement.get("commonRootPathPresent") is False
        and replacement.get("freshNoModelCodexExposure") is True
        and replacement.get("priorSkillMdSimilarityToLegacy") == 0.8412
        and replacement.get("replacementAddsTighterLoopAndMinimisationControls")
        is True,
        "Diagnosing-bugs replacement evidence drifted",
    )
    references = document.get("exactIdentityReferences", [])
    by_owner = {item.get("owner"): item for item in references}
    _require(
        len(references) == 3
        and set(by_owner)
        == {
            "current-source-capability-router",
            "legacy-cc-capability-router",
            "observability-and-instrumentation",
        },
        "Diagnose exact reference coverage drifted",
    )
    current_router = by_owner["current-source-capability-router"]
    old_router = by_owner["legacy-cc-capability-router"]
    observability = by_owner["observability-and-instrumentation"]
    _require(
        current_router.get("sourceAuthority")
        == "C:/Projects/codex-user-config"
        and "diagnosis capability" in current_router.get("proposedText", "")
        and old_router.get("sourceAuthority")
        == "legacy-divergent-cc-snapshot-not-authority"
        and old_router.get("proposedText") is None
        and "do-not-patch-in-place"
        in old_router.get("disposition", "")
        and observability.get("sourceAuthority")
        == "agent-autonomy-harness-governed-adaptation"
        and "active task-bound diagnosis workflow"
        in observability.get("proposedText", ""),
        "Diagnose source-authority migration route drifted",
    )
    privacy = document.get("adjacentObservabilityPrivacyRepair", {})
    _require(
        "${userId}" in privacy.get("currentText", "")
        and "${userId}" not in privacy.get("proposedText", "")
        and privacy.get("liveAndGovernedSourceCurrentlyByteEqual") is True
        and privacy.get("currentBytes") == 11761
        and privacy.get("currentSha256")
        == "4ff6d4d23e5b41db29e9b4e289e033ccc1281b986053ca45e83b889955395aa0"
        and privacy.get("mutationAuthorized") is False,
        "Diagnose adjacent observability privacy repair drifted",
    )
    gates = document.get("dependencyOrder", [])
    _require(
        [gate.get("gate") for gate in gates]
        == ["D15-01", "D15-02", "D15-03", "D15-04", "D15-05"]
        and all(gate.get("satisfied") is False for gate in gates),
        "Diagnose dependency order drifted",
    )
    subtraction = document.get("conditionalSubtraction", {})
    arithmetic = subtraction.get(
        "currentSnapshotArithmeticIfOnlyFifteenRowsWereRemoved",
        {},
    )
    _require(
        subtraction.get("currentReadyCohortCount") == 14
        and subtraction.get("conditionalCohortCountAfterAllGates") == 15
        and subtraction.get("currentReadyFileCount") == 19
        and subtraction.get("conditionalFileCountAfterAllGates") == 21
        and subtraction.get("currentReadyPayloadBytes") == 58356
        and subtraction.get("conditionalPayloadBytesAfterAllGates") == 66684
        and subtraction.get("diagnoseCurrentlyAdmitted") is False
        and subtraction.get("diagnoseCanBeAdmittedAfterAllGates") is True
        and arithmetic.get("beforeRows") == 55
        and arithmetic.get("afterRows") == 40
        and arithmetic.get("forecastBinding") is False
        and subtraction.get("diagnosingBugsMustRemain") is True
        and subtraction.get("diagnosingBugsCommonRootProjectionCurrentlyAbsent")
        is True
        and subtraction.get("crossHostPortabilityProved") is False
        and subtraction.get("managerRemovalAuthorized") is False,
        "Diagnose conditional subtraction boundary drifted",
    )
    _require(
        document.get("cleanup")
        == {
            "temporarySourceRootCreated": False,
            "temporarySourceRootAbsent": True,
            "noPatchFileCreated": True,
            "noRecoveryArchiveCreated": True,
            "noSkillBodyExecuted": True,
            "noModelTurnSent": True,
            "noManagerHostOrSourceMutation": True,
        },
        "Diagnose cleanup boundary drifted",
    )
    claims = document.get("claimBoundary", {})
    _require(
        claims.get("exactCurrentReferencesBound") is True
        and claims.get("currentReplacementIdentityAndExposureBound") is True
        and claims.get("sourceAuthoritySpecificMigrationPreviewProved") is True
        and claims.get("firstPartyCarrierPolicyResolved") is False
        and claims.get("referenceMigrationApplied") is False
        and claims.get("zeroRetainedReferenceStateProved") is False
        and claims.get("diagnoseFifteenthAdmissionCurrentlyProved") is False
        and claims.get("manager319FifteenItemTransactionReady") is False
        and claims.get("behavioralValueOrCrossHostPortabilityProved") is False
        and claims.get("programCloseoutProved") is False,
        "Diagnose claim boundary drifted",
    )
    _require(
        document.get("documentation") == DOCUMENTATION_PATH,
        "Diagnose documentation binding drifted",
    )
    text = (root / DOCUMENTATION_PATH).read_text(encoding="utf-8")
    for phrase in (
        "`diagnose` remains blocked",
        "The correct route is not to patch every visible copy.",
        "Exact source-authority migration",
        "must not be patched in place",
        "These are proposed exact source changes, not applied changes.",
        "Only then does the cohort grow from 14 to a conditional 15",
        "The arithmetic `55 - 15 = 40` is not a forecast",
    ):
        _require(
            phrase in text,
            f"Diagnose documentation missing: {phrase}",
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    root = args.root.resolve()
    document = json.loads((root / EVIDENCE_PATH).read_text(encoding="utf-8"))
    validate_preview(document, root=root)
    print("Diagnose reference migration and fifteenth admission preview passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
