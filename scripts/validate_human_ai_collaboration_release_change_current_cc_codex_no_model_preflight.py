#!/usr/bin/env python3
"""Validate the current CC/Codex no-model release-change preflight."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_PATH = (
    "registry/"
    "human-ai-collaboration-release-change-current-cc-codex-no-model-preflight-2026-07-30.json"
)
DOCUMENTATION_PATH = (
    "docs/strategy/"
    "HUMAN-AI-COLLABORATION-RELEASE-CHANGE-CURRENT-CC-CODEX-NO-MODEL-PREFLIGHT-2026-07-30.md"
)
EXPECTED_CANDIDATES = {
    "skill.curated.ci-cd-and-automation": {
        "bytes": 11470,
        "sha256": "7aa008e4be26068c9e61ea8a9303711020e376c6cbfdf10d581a9fd400acf8ea",
        "tree": "b99b47b56d6e64723953296bf89bf4988a7efe067bd99c5335454188b285d944",
    },
    "skill.curated.shipping-and-launch": {
        "bytes": 11464,
        "sha256": "195a1fad5612627464df4581954727b8ebd649b0ce4bfe91e06655bcc32302b0",
        "tree": "71cabfbce6288267c1b1821fcae556af0f639354e4feb48b45da06be5765c04a",
    },
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def validate_preflight(
    document: dict[str, Any],
    *,
    root: Path = ROOT,
) -> None:
    _require(
        document.get("schema") == 1
        and document.get("id")
        == "human-ai-collaboration-release-change-current-cc-codex-no-model-preflight-2026-07-30"
        and document.get("date") == "2026-07-30"
        and document.get("scenarioId") == "SE-RELEASE-CHANGE-01"
        and document.get("status")
        == "current-cc-exact-two-candidates-task-inventory-listed-fresh-desktop-reprobe-blocked",
        "release/change current CC/Codex preflight identity drifted",
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
        "release/change repository posture drifted",
    )
    sources = set(document.get("sourceBindings", []))
    for required in (
        "registry/human-ai-collaboration-release-change-zero-model-protocol-2026-07-27.json",
        "registry/human-ai-collaboration-release-change-candidate-preflight-2026-07-27.json",
        "registry/cc-switch-fourteen-skill-live-preflight-contract-2026-07-30.json",
        "registry/codex-common-root-doc-pdf-host-disable-transaction-2026-07-30.json",
        "scripts/preflight_cc_switch_fourteen_skill_subtraction.py",
        "scripts/probe_codex_app_server_skill_exposure.py",
    ):
        _require(required in sources, f"release/change source binding missing: {required}")
    authority = document.get("authorityBoundary", {})
    _require(
        authority.get("readLocalCcDatabaseSettingsSkillTreesAndLinks") is True
        and authority.get("readCurrentCodexConfigPolicyRows") is True
        and authority.get("startShortLivedNoModelAppServer") is True
        and authority.get("sourceBodyExecution") is False
        and authority.get("modelRequest") is False
        and authority.get("candidateInvocation") is False
        and authority.get("ccSwitchMutation") is False
        and authority.get("hostProjectionMutation") is False
        and authority.get("globalConfigurationMutation") is False
        and authority.get("dependencyInstall") is False
        and authority.get("cleanupOrDeletion") is False
        and authority.get("gitCommitOrPushDuringProbe") is False,
        "release/change authority boundary drifted",
    )
    whole = document.get("wholeStateObservation", {})
    _require(
        whole.get("frozenWholeStatePreflightPassed") is False
        and whole.get("currentCounts")
        == {
            "databaseRows": 55,
            "ccSkillTrees": 55,
            "backupCount": 20,
            "projectionEntryCounts": {
                "ccSwitch": 55,
                "agents": 41,
                "claude": 55,
                "codex": 57,
            },
        }
        and whole.get("fingerprintMatchesFrozen")
        == {
            "managerBinary": True,
            "settings": True,
            "database": False,
            "ccTrees": True,
            "projections": False,
            "backups": True,
            "codexSkillConfig": True,
            "wholeState": False,
        },
        "release/change whole-state observation drifted",
    )
    drift = document.get("driftAttribution", {})
    hypotheses = drift.get("rankedHypotheses", [])
    _require(
        len(hypotheses) == 4
        and [item.get("rank") for item in hypotheses] == [1, 2, 3, 4]
        and hypotheses[0].get("outcome") == "supported-exactly"
        and hypotheses[1].get("outcome") == "falsified"
        and hypotheses[2].get("outcome") == "falsified"
        and hypotheses[3].get("outcome")
        == "not-proved-windowsapps-createprocess-denied",
        "release/change ranked diagnosis drifted",
    )
    delta = drift.get("exactObservedDelta", {})
    _require(
        {
            (item.get("name"), item.get("frozenEnabledCodex"), item.get("currentEnabledCodex"))
            for item in delta.get("databaseRows", [])
        }
        == {("doc", 0, 1), ("pdf", 0, 1)}
        and {
            (item.get("name"), item.get("frozenState"), item.get("currentState"))
            for item in delta.get("codexPrivateProjectionRows", [])
        }
        == {
            ("doc", "absent", "resolvable-symlink-to-cc-source"),
            ("pdf", "absent", "resolvable-symlink-to-cc-source"),
        },
        "release/change doc/pdf exact drift attribution changed",
    )
    counterfactual = drift.get("readOnlyCounterfactual", {})
    _require(
        counterfactual.get("databaseFingerprintMatchesFrozen") is True
        and counterfactual.get("projectionFingerprintMatchesFrozen") is True
        and counterfactual.get("wholeStateFingerprintMatchesFrozen") is True
        and counterfactual.get("liveStateMutated") is False
        and drift.get("candidateCohortCausedWholeStateFailure") is False
        and drift.get("oldFrozenBaselineShouldBeRefreshedFromThisObservation")
        is False,
        "release/change counterfactual or baseline boundary drifted",
    )
    candidates = document.get("candidateObservations", [])
    by_id = {item.get("candidateId"): item for item in candidates}
    _require(
        len(candidates) == 2 and set(by_id) == set(EXPECTED_CANDIDATES),
        "release/change candidate coverage drifted",
    )
    for candidate_id, expected in EXPECTED_CANDIDATES.items():
        item = by_id[candidate_id]
        _require(
            item.get("ccSkillMdBytes") == expected["bytes"]
            and item.get("ccSkillMdSha256") == expected["sha256"]
            and item.get("ccTreeManifestSha256") == expected["tree"]
            and item.get("databaseEnabledCodex") == 1
            and item.get("databaseEnabledClaude") == 1
            and item.get("ccSourcePhysical") is True
            and item.get("agentsProjectionExactSymlink") is True
            and item.get("claudeProjectionExactSymlink") is True
            and item.get("codexProjectionExactSymlink") is True
            and item.get("repositoryReleasePayloadExact") is True
            and item.get("currentTaskRuntimeInventoryListed") is True
            and item.get("currentTaskRuntimeInventoryPath", "").startswith(
                "C:/Users/15521/.cc-switch/skills/"
            ),
            f"release/change candidate identity drifted: {candidate_id}",
        )
    carriers = document.get("hostCarrierObservations", {})
    npm = carriers.get("npmCli", {})
    _require(
        npm.get("version") == "codex-cli 0.146.0"
        and npm.get("pluginsDisabledArm")
        == {
            "skillCount": 6,
            "userSkillCount": 0,
            "candidateRowCount": 0,
            "stderrLineCount": 0,
        }
        and npm.get("pluginsEnabledArm")
        == {
            "skillCount": 6,
            "userSkillCount": 0,
            "candidateRowCount": 0,
            "stderrLineCount": 0,
        }
        and npm.get("configPrePostStable") is True
        and npm.get("interpretation")
        == "different-carrier-observation-not-candidate-failure",
        "release/change npm carrier observation drifted",
    )
    desktop = carriers.get("desktop", {})
    _require(
        desktop.get("version") == "Codex Desktop/0.146.0"
        and desktop.get("runningProcessObserved") is True
        and desktop.get("freshAppServerSpawnAttemptedInSandbox") is True
        and desktop.get("freshAppServerSpawnAttemptedWithEscalation") is True
        and desktop.get("freshAppServerSpawnResult")
        == "blocked-windowsapps-acl-winerror-5"
        and desktop.get("freshSkillsListReproduced") is False
        and carriers.get("carrierEquivalenceProved") is False,
        "release/change Desktop carrier boundary drifted",
    )
    decision = document.get("preflightDecision", {})
    _require(
        decision.get("currentCcEntityIdentityProvedForBothCandidates") is True
        and decision.get("currentManagerEnablementProvedForBothCandidates")
        is True
        and decision.get("currentFilesystemProjectionProvedForBothCandidates")
        is True
        and decision.get(
            "currentTaskRuntimeInventoryListingObservedForBothCandidates"
        )
        is True
        and decision.get("independentFreshDesktopExposureReproduced") is False
        and decision.get("candidateLoaderInvocationProved") is False
        and decision.get("candidateInstructionsReachedModelProved") is False
        and decision.get("candidateBehaviorOrValueProved") is False
        and decision.get("formalNativeOrCandidateArmEligible") is False
        and decision.get("docPdfDriftRequiresSeparateLifecycleReconciliation")
        is True
        and decision.get("candidateInstallUpdateEnableOrMutationAuthorized")
        is False
        and decision.get("selfAuthoredWorkEligible") is False,
        "release/change preflight decision boundary drifted",
    )
    _require(
        all(value == 0 for value in document.get("executionCounters", {}).values()),
        "release/change execution counter drifted",
    )
    claims = document.get("claimBoundary", {})
    _require(
        claims.get("provesCurrentCcBodyAndProjectionIdentity") is True
        and claims.get("provesCurrentTaskStartupInventoryListing") is True
        and claims.get("provesIndependentFreshDesktopExposure") is False
        and claims.get("provesCandidateInvocationOrInstructionDelivery") is False
        and claims.get("provesCandidateBehaviorValuePreferenceOrSuperiority")
        is False
        and claims.get("provesNpmCliAndDesktopCarrierEquivalence") is False
        and claims.get("provesDocPdfEffectiveRuntimeSuppressionAfterRehydration")
        is False
        and claims.get("provesReleaseReadinessOrRealRollback") is False
        and claims.get("provesResidualSelfAuthoredGap") is False
        and claims.get("authorizesPortfolioOrHostMutation") is False,
        "release/change claim boundary drifted",
    )
    cleanup = document.get("cleanup", {})
    _require(
        cleanup.get("temporaryRootCreated") is False
        and cleanup.get("temporaryRootAbsent") is True
        and cleanup.get("rawConfigRecorded") is False
        and cleanup.get("rawDatabaseRecorded") is False
        and cleanup.get("shortLivedNpmAppServersExited") is True
        and cleanup.get("desktopFreshProcessCreated") is False
        and cleanup.get("repositoryCleanupInventoryStableBeforeEvidenceWrite")
        is True,
        "release/change cleanup boundary drifted",
    )
    _require(
        document.get("documentation") == DOCUMENTATION_PATH,
        "release/change documentation binding drifted",
    )
    text = (root / DOCUMENTATION_PATH).read_text(encoding="utf-8")
    for phrase in (
        "The two approved release/change candidates did not drift",
        "exactly the rehydration",
        "The frozen baseline must not be refreshed",
        "candidate failure.",
        "Windows package ACLs rejected",
        "lifecycle-reconciliation gap",
    ):
        _require(
            phrase in text,
            f"release/change documentation missing: {phrase}",
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    root = args.root.resolve()
    document = json.loads((root / EVIDENCE_PATH).read_text(encoding="utf-8"))
    validate_preflight(document, root=root)
    print("Release/change current CC/Codex no-model preflight passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
