#!/usr/bin/env python3
"""Validate the Huashu and PM current-component delta research."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_PATH = (
    "registry/"
    "user-starred-huashu-pm-current-component-delta-research-2026-07-30.json"
)
DOCUMENTATION_PATH = (
    "docs/strategy/"
    "USER-STARRED-HUASHU-PM-CURRENT-COMPONENT-DELTA-RESEARCH-2026-07-30.md"
)
EXPECTED_SCENARIOS = {
    "GEN-CREATIVE-01",
    "GEN-ORG-DECISION-01",
    "SE-MGMT-PRACTICE-01",
}
EXPECTED_PM_COMPONENTS = {
    "stakeholder-map": {
        "path": "pm-execution/skills/stakeholder-map/SKILL.md",
        "blob": "08e5ad24a830a8faef9942a6fd9acdd274261835",
        "bytes": 2510,
    },
    "strategy-red-team": {
        "path": "pm-execution/skills/strategy-red-team/SKILL.md",
        "blob": "fe7b7feaaa7a7662d72aac226d40d3abea7e0596",
        "bytes": 4515,
    },
}
EXPECTED_PM_EXCLUSIONS = {
    "pre-mortem",
    "prioritization-frameworks",
    "outcome-roadmap",
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def validate_research(
    document: dict[str, Any],
    *,
    root: Path = ROOT,
) -> None:
    _require(
        document.get("schema") == 1
        and document.get("id")
        == "user-starred-huashu-pm-current-component-delta-research-2026-07-30"
        and document.get("date") == "2026-07-30"
        and document.get("status")
        == "read-only-current-revision-delta-two-pm-static-candidates-no-huashu-atomic-candidate",
        "Huashu and PM delta research identity drifted",
    )
    posture = document.get("repositoryPosture", {})
    _require(
        posture.get("branch") == "main"
        and posture.get("head")
        == "55659f30091990f7c589932e0379880de30dc403"
        and posture.get("upstream") == "origin/main"
        and posture.get("originMain") == posture.get("head")
        and posture.get("ahead") == 0
        and posture.get("behind") == 0
        and posture.get("worktreeIntentionallyLargeAndDirty") is True
        and posture.get("inheritedChangesPreserved") is True,
        "Huashu and PM repository posture drifted",
    )
    authority = document.get("authorityBoundary", {})
    _require(
        authority.get("readRepositoryEvidence") is True
        and authority.get("readPublicPrimarySources") is True
        and authority.get("sourceRepositoryCheckoutOrDownload") is False
        and authority.get("sourceBodyExecution") is False
        and authority.get("dependencyInstall") is False
        and authority.get("skillInstallUpdateEnableDisableOrDelete") is False
        and authority.get("ccSwitchMutation") is False
        and authority.get("globalConfigHookRulesOrForeignRootMutation") is False
        and authority.get("modelDispatch") is False
        and authority.get("gitCommitOrPush") is False,
        "Huashu and PM authority boundary drifted",
    )
    inputs = set(document.get("inputs", []))
    for required in (
        "registry/user-starred-new-source-preflight-2026-07-18.json",
        "registry/round02-candidate-reviews.json",
        "registry/round02-huashu-design-guidance-adaptation-gate.json",
        "registry/round02-huashu-toolchain-media-adaptation-gate.json",
        "registry/round02-pm-execution-adaptation-gate.json",
        "registry/round02-pm-analytics-adaptation-gate.json",
        "registry/round02-pm-market-discovery-adaptation-gate.json",
        "registry/round02-pm-toolkit-boundary-adaptation-gate.json",
        "registry/human-ai-collaboration-scenario-evidence-matrix-batch-01-2026-07-24.json",
        "registry/other-cc-and-external-skill-scenario-coverage-audit-2026-07-27.json",
    ):
        _require(required in inputs, f"Huashu and PM input binding missing: {required}")
    bindings = document.get("scenarioBindings", [])
    _require(
        len(bindings) == 3
        and {item.get("scenarioId") for item in bindings} == EXPECTED_SCENARIOS
        and all(
            isinstance(item.get("source"), str)
            and item.get("allowedAction")
            and item.get("humanAuthority")
            for item in bindings
        ),
        "Huashu and PM scenario binding drifted",
    )
    sources = document.get("sources", {})
    huashu = sources.get("huashuDesign", {})
    _require(
        huashu.get("repository") == "alchaincyf/huashu-design"
        and huashu.get("defaultBranch") == "master"
        and huashu.get("revision")
        == "1572d431f1411c82ec0baea94dea6a45f6063b26"
        and huashu.get("commitDate") == "2026-07-27T02:52:54Z"
        and huashu.get("tree")
        == "04501b8d8ac964e72d6b04afa933d9ab218dbc5f"
        and huashu.get("license") == "MIT"
        and huashu.get("fileCount") == 189
        and huashu.get("skillBodyCount") == 1
        and huashu.get("referenceFileCount") == 32
        and huashu.get("assetFileCount") == 105
        and huashu.get("scriptFileCount") == 19
        and huashu.get("demoFileCount") == 23
        and huashu.get("hookPath") == "scripts/design-gate-hook.sh"
        and huashu.get("hookOptIn") is True
        and huashu.get("commitsAheadOfRound02Pin") == 26
        and huashu.get("changedFilesFromRound02Pin") == 39
        and huashu.get("commitsAheadOfPreflightPin") == 16
        and huashu.get("changedFilesFromPreflightPin") == 31
        and huashu.get("readmeDeclaresSkillOnlyInstallDependencyIncomplete")
        is True,
        "Huashu current source identity or structure drifted",
    )
    _require(
        huashu.get("currentAtomicCandidate") is False
        and huashu.get("disposition")
        == "retain-source-metadata-and-current-pin"
        and huashu.get("reopenRequiresFixedComparativeBriefAndNamedMarginalGap")
        is True
        and "OpenAI-official" in huashu.get("reason", ""),
        "Huashu atomic-candidate boundary drifted",
    )
    pm = sources.get("pmSkills", {})
    _require(
        pm.get("repository") == "phuryn/pm-skills"
        and pm.get("defaultBranch") == "main"
        and pm.get("revision")
        == "18468a95b427e70e258b51389796367c6f684e7d"
        and pm.get("commitDate") == "2026-07-03T11:34:34Z"
        and pm.get("tree")
        == "514548cbf646ce42fb9ea9a8cc901f05373ab2ff"
        and pm.get("license") == "MIT"
        and pm.get("release") == "v2.1.0"
        and pm.get("releaseExactAtHead") is True
        and pm.get("fileCount") == 147
        and pm.get("skillBodyCount") == 68
        and pm.get("pluginManifestCount") == 9
        and pm.get("hookCount") == 0
        and pm.get("repositoryScriptCount") == 3
        and pm.get("identicalToPreflightPin") is True
        and pm.get("commitsAheadOfRound02Pin") == 1
        and pm.get("changedFilesFromRound02Pin") == 27,
        "PM current source identity or structure drifted",
    )
    components = pm.get("selectedComponents", [])
    by_name = {item.get("name"): item for item in components}
    _require(
        len(components) == 2 and set(by_name) == set(EXPECTED_PM_COMPONENTS),
        "PM selected component coverage drifted",
    )
    for name, expected in EXPECTED_PM_COMPONENTS.items():
        item = by_name[name]
        _require(
            item.get("path") == expected["path"]
            and item.get("blob") == expected["blob"]
            and item.get("bytes") == expected["bytes"]
            and item.get("status") == "static-protocol-candidate-only"
            and item.get("hardRuntimeDependency") is False,
            f"PM selected component identity drifted: {name}",
        )
    exclusions = pm.get("excludedFromThisBatch", [])
    _require(
        len(exclusions) == 3
        and {item.get("name") for item in exclusions} == EXPECTED_PM_EXCLUSIONS
        and all(item.get("scope") == "batch-local" for item in exclusions)
        and pm.get("selectedPairDependencyLinked") is False
        and pm.get("selectedPairScenarioComplete") is False
        and pm.get("individualProjectionOfficiallySupportedByUpstream") is False,
        "PM exclusion or completeness boundary drifted",
    )
    decision = document.get("decision", {})
    _require(
        decision.get("huashuCurrentAtomicCandidateCount") == 0
        and decision.get("pmStaticProtocolCandidateCount") == 2
        and decision.get("wholeSourceInstallAuthorized") is False
        and decision.get("selectedComponentInstallAuthorized") is False
        and decision.get("sourceAcquisitionOrProjectionAuthorized") is False
        and decision.get("pluginEnablementAuthorized") is False
        and decision.get("modelDispatchAuthorized") is False
        and decision.get("externalLookupOrOrganizationalDataAccessAuthorized")
        is False
        and decision.get("offlineFixedFixtureProtocolAuthorized") is False
        and decision.get("portfolioMutationAuthorized") is False
        and decision.get("selfAuthoredWorkEligible") is False,
        "Huashu and PM decision boundary drifted",
    )
    claims = document.get("claimBoundary", {})
    _require(
        claims.get("currentPrimarySourceIdentityAndDriftProved") is True
        and claims.get("staticSourceBodyAndOverlapDispositionProved") is True
        and claims.get("installationOrAdmissionProved") is False
        and claims.get("hostExposureOrInvocationProved") is False
        and claims.get("behavioralIncrementProved") is False
        and claims.get("crossHostValueProved") is False
        and claims.get("residualCapabilityGapProved") is False
        and claims.get("selfAuthoredNecessityProved") is False
        and claims.get("programCloseoutProved") is False,
        "Huashu and PM claim boundary drifted",
    )
    _require(
        document.get("cleanup")
        == {
            "temporarySourceRootCreated": False,
            "temporarySourceRootAbsent": True,
            "noSourceBodyExecuted": True,
            "noDependencyInstalled": True,
            "inheritedTemporaryRootsUntouched": True,
            "repositoryCleanupInventoryStable": True,
        },
        "Huashu and PM cleanup evidence drifted",
    )
    _require(
        document.get("documentation") == DOCUMENTATION_PATH,
        "Huashu and PM documentation binding drifted",
    )
    text = (root / DOCUMENTATION_PATH).read_text(encoding="utf-8")
    for phrase in (
        "no current atomic component candidate",
        "retain exactly two static component candidates",
        "sufficient alone or together",
        "Exclusion is batch-local",
        "This review does not authorize installation or a live model trial",
        "No current evidence supports whole-source installation",
    ):
        _require(
            phrase in text,
            f"Huashu and PM documentation missing: {phrase}",
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    root = args.root.resolve()
    document = json.loads((root / EVIDENCE_PATH).read_text(encoding="utf-8"))
    validate_research(document, root=root)
    print("Huashu and PM current-component delta research passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
