#!/usr/bin/env python3
"""Validate the dated Skill runtime and CC count drift snapshot."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_PATH = (
    "registry/skill-runtime-and-cc-count-drift-snapshot-2026-07-27.json"
)
DOC_PATH = (
    "docs/strategy/SKILL-RUNTIME-AND-CC-COUNT-DRIFT-SNAPSHOT-2026-07-27.md"
)
ACCEPTANCE_MAP_PATH = "registry/program-acceptance-map.json"
CONTINUATION_PATH = "docs/operations/CONTINUATION.md"
RESEARCH_PLAN_PATH = "docs/strategy/RESEARCH-AND-POC-PLAN.md"
EVIDENCE_ID = "evidence.skill-runtime-and-cc-count-drift-snapshot-2026-07-27"
SUPPORTED_ACCEPTANCE_IDS = [
    "acceptance.cc-switch-source-preserving-skill-pool",
    "acceptance.user-sovereign-capability-governance",
    "acceptance.foreign-managed-capability-coexistence",
]
EXPECTED_SKILL_DIGESTS = {
    "brainstorming": "4a54a4858b99807f3155ed1614b2f116e35ea5c1b788e793f565dd837fd3891f",
    "dispatching-parallel-agents": "1968923066f3b707eb01d1992cdf4c42284c3855f70253b9cd5000ff45fca13c",
    "executing-plans": "c4c3d8b628c51114cd165fb8246fe02744cd8be180032328391252e653028d9b",
    "finishing-a-development-branch": "d0ac8360ed9d59121776ef95c84bcb38e9747de0d7ae7e227dca81e437593b9b",
    "receiving-code-review": "091df1629510af1b92fc4abd6f96732ebedb4cb2c0f3457e8f2740b0504a2438",
    "requesting-code-review": "d71cc01ba56d2325cf8af5f7c11837819b63ecd57de0bfdb812f7f3ff7751df8",
    "subagent-driven-development": "349a08ad8b59b19b86c13a7d2f34a1a38719bf88257004a863eefefa8d9f9e40",
    "systematic-debugging": "808fc5717aa88ad65efff312b11c186294d3e6ee301afb584e2f86599b137787",
    "test-driven-development": "bf1b8216e523851a411e91d429a7c1c2a173e79d88957bc78e348218d50edd54",
    "using-git-worktrees": "8cfb86f121269e8f7f12361e6795c4f6738828340e28964c9229d365666c9edd",
    "using-superpowers": "55379fe7c1c473a02c61961c822996bff30e1320d6921d9062509bc508482c05",
    "verification-before-completion": "2befe7fc55bcadaa3d97dd9e8efeb633d2561c0ebe74c5a8b17c4d9e7e4520b3",
    "writing-plans": "72190c88b2b5a67a96b91d66aa72b9161913e10e8769da3f28a226f4cc7b99d0",
    "writing-skills": "d34db5c8aed6a4e0440132bd0613aace70a693ec7819d5637ad77481d8e10d1b",
}
EXPECTED_ENABLED_REPOSITORIES = [
    "ComposioHQ/awesome-claude-skills@master",
    "JimLiu/baoyu-skills@main",
    "anthropics/skills@main",
    "cexll/myclaude@master",
    "larksuite/cli@HEAD",
    "mattpocock/skills@main",
]
EXPECTED_CLAIM_BOUNDARY_KEYS = {
    "databaseEnablementProvesInvocation",
    "physicalBodyProvesConsumerLoaderUse",
    "sourceRegistrationProvesAllRepositorySkillsInstalled",
    "exactSkillBytesProveBehavioralValue",
    "releaseNotesProveLocalBehavior",
    "runtimePluginPresenceProvesFullFrameworkUse",
    "crossDeviceEqualityProved",
    "staleRowRepairProved",
    "superpowers620WeakAgentValueProved",
    "mattSuperiorityProved",
    "selfAuthoredResidualGapProved",
    "safeCleanupOrMigrationProved",
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_snapshot(
    document: dict[str, Any],
    *,
    root: Path = ROOT,
) -> None:
    _require(
        document.get("schema") == 1
        and document.get("id")
        == "skill-runtime-and-cc-count-drift-snapshot-2026-07-27"
        and document.get("date") == "2026-07-27"
        and document.get("status")
        == (
            "current-host-read-only-count-and-source-drift-reconciled-"
            "no-mutation"
        ),
        "Skill runtime drift snapshot identity changed.",
    )
    authority = document.get("authorityBoundary")
    _require(
        isinstance(authority, dict)
        and authority.get("localReadOnlyInventory") is True
        and authority.get("authenticatedReadOnlyGithubApi") is True
        and authority.get("skillBodyExecution") is False
        and authority.get("modelRequestSent") is False
        and authority.get("ccSwitchMutation") is False
        and authority.get("pluginMutation") is False
        and authority.get("globalConfigurationMutation") is False
        and authority.get("credentialValueRecorded") is False
        and authority.get("accountSyncInvoked") is False
        and authority.get("installEnableDisableRelinkOrDelete") is False
        and authority.get("gitMutation") is False,
        "Skill runtime drift authority boundary changed.",
    )
    host = document.get("host")
    _require(isinstance(host, dict), "Skill runtime host shape changed.")
    reproducer = host.get("inventoryReproducer")
    _require(
        isinstance(reproducer, dict)
        and isinstance(reproducer.get("path"), str),
        "Skill inventory reproducer shape changed.",
    )
    reproducer_path = root / reproducer.get("path", "")
    _require(
        isinstance(host, dict)
        and host.get("ccSwitchVersion") == "3.18.0"
        and reproducer_path.is_file()
        and reproducer.get("bytes") == reproducer_path.stat().st_size
        and reproducer.get("fileSha256", "").lower()
        == _sha256(reproducer_path).lower()
        and host.get("inventoryCompactJsonBytes") == 102055
        and host.get("inventoryCompactJsonSha256")
        == "a8842ce553b4f5de8089355a68991d8e824ae2bc1c1f88fdf7bb7f4bfda6bbd1",
        "Skill inventory reproducer or dated digest changed.",
    )

    observation = document.get("ccSwitchObservation")
    _require(
        isinstance(observation, dict),
        "CC observation shape changed.",
    )
    settings = observation.get("settings")
    database = observation.get("database")
    roots = observation.get("roots")
    _require(
        isinstance(settings, dict)
        and isinstance(database, dict)
        and isinstance(roots, dict)
        and set(roots) == {"ccSwitch", "agents", "claude", "codex"}
        and all(isinstance(value, dict) for value in roots.values()),
        "CC observation nested shape changed.",
    )
    _require(
        settings
        == {
            "skillStorageLocation": "cc_switch",
            "skillSyncMethod": "symlink",
            "backupRetainCount": 3,
            "visibleApps": ["claude", "claude-desktop", "codex"],
        },
        "CC settings observation changed.",
    )
    _require(
        isinstance(observation, dict)
        and database.get("rows") == 251
        and database.get("distinctNames") == 233
        and database.get("enabledClaude") == 251
        and database.get("enabledCodex") == 251
        and database.get("duplicateNameGroupCount") == 15
        and database.get("enabledRepositoryCount") == 6,
        "CC database count observation changed.",
    )
    _require(
        database.get("enabledRepositories") == EXPECTED_ENABLED_REPOSITORIES
        and database.get("enabledRepositoryCount")
        == len(EXPECTED_ENABLED_REPOSITORIES),
        "CC enabled repository identity changed.",
    )
    _require(
        roots.get("ccSwitch", {}).get("topLevelDirectories") == 75
        and roots.get("ccSwitch", {}).get("resolvableSkillMd") == 75
        and roots.get("agents", {}).get("topLevelDirectories") == 73
        and roots.get("agents", {}).get("resolvableSkillMd") == 73
        and roots.get("claude", {}).get("topLevelDirectories") == 251
        and roots.get("claude", {}).get("resolvableSkillMd") == 75
        and roots.get("claude", {}).get("unresolvedSkillMd") == 176
        and roots.get("codex", {}).get("topLevelDirectories") == 77
        and roots.get("codex", {}).get("resolvableSkillMd") == 75
        and roots.get("codex", {}).get(
            "containerRootsWithoutTopLevelSkillMd"
        )
        == [".system", "codex-primary-runtime"],
        "CC physical or projection layer count changed.",
    )
    for root_name, expected_types in {
        "ccSwitch": (75, 0, 0),
        "agents": (30, 42, 1),
        "claude": (1, 235, 15),
        "codex": (6, 70, 1),
    }.items():
        root_observation = roots[root_name]
        physical, symlink, junction = expected_types
        _require(
            root_observation.get("physical", 0) == physical
            and root_observation.get("symlink", 0) == symlink
            and root_observation.get("junction", 0) == junction
            and physical + symlink + junction
            == root_observation.get("topLevelDirectories"),
            f"CC root type arithmetic changed for {root_name}.",
        )
    presence = observation.get("databaseRootPresence", {})
    backup = observation.get("localBackupDirectoryInventory", {})
    _require(
        presence
        == {
            "ccSwitchRowsWithDirectory": 75,
            "ccSwitchRowsWithResolvableSkillMd": 75,
            "agentsRowsWithDirectory": 73,
            "agentsRowsWithResolvableSkillMd": 73,
            "claudeRowsWithDirectory": 251,
            "claudeRowsWithResolvableSkillMd": 75,
            "codexRowsWithDirectory": 75,
            "codexRowsWithResolvableSkillMd": 75,
        }
        and observation.get("sameNameDifferentSkillMdHashCount") == 30
        and backup
        == {
            "topLevelEntries": 20,
            "directories": 76,
            "files": 480,
            "bytes": 8927752,
            "restoreVerifiedByThisSnapshot": False,
            "crossDeviceEqualityProved": False,
        },
        "CC root presence, collision, or local backup inventory changed.",
    )
    semantics = observation.get("countSemantics", {})
    persistent = observation.get("persistentGap", {})
    _require(
        semantics.get("uiOrEnabledRowCountEqualsPhysicalUniqueSkillCount")
        is False
        and semantics.get(
            "projectionEntryCountEqualsResolvableSkillCount"
        )
        is False
        and semantics.get("databaseRowCountProvesLoaderInvocation") is False
        and semantics.get("ccPhysicalRootIsCurrentBodyCountSurface") is True
        and semantics.get("consumerProjectionMustBeResolvedSeparately")
        is True
        and persistent.get("missingBodyDatabaseRows") == 176
        and persistent.get("claudeBrokenCcTargetLinks") == 176
        and persistent.get("matchesPriorStaleRowClassification") is True
        and persistent.get("supportedBulkReconcilerObserved") is False
        and persistent.get("mutationAuthorized") is False,
        "CC count semantics or persistent stale-row boundary changed.",
    )
    _require(
        database.get("rows")
        == database.get("enabledClaude")
        == database.get("enabledCodex")
        == roots["claude"]["topLevelDirectories"]
        and database["rows"] - roots["ccSwitch"]["resolvableSkillMd"]
        == persistent["missingBodyDatabaseRows"]
        == roots["claude"]["unresolvedSkillMd"]
        == roots["claude"]["topLevelDirectories"]
        - roots["claude"]["resolvableSkillMd"],
        "CC 251/75/176 arithmetic invariant changed.",
    )

    sources = document.get("externalSourceRevalidation")
    _require(
        isinstance(sources, dict)
        and set(sources) == {"mattPocock", "superpowers"}
        and all(isinstance(value, dict) for value in sources.values()),
        "External source revalidation shape changed.",
    )
    matt = sources["mattPocock"]
    superpowers = sources["superpowers"]
    _require(
        matt.get("repository") == "mattpocock/skills"
        and matt.get("mainCommit")
        == "ed37663cc5fbef691ddfecd080dff42f7e7e350d"
        and matt.get("priorPinnedMainStillCurrent") is True
        and matt.get("sourceDriftObserved") is False,
        "Matt source revalidation changed.",
    )
    _require(
        superpowers.get("repository") == "obra/superpowers"
        and superpowers.get("latestRelease") == "v6.2.0"
        and superpowers.get("releaseCommit")
        == "3dcbd5c4b48e02263fbf4a3c01e3fe4f81d584d9"
        and superpowers.get("releasePublishedAt") == "2026-07-24T00:28:17Z"
        and superpowers.get("mainCommitMatchesReleaseCommit") is True
        and superpowers.get("priorComparisonVersion") == "6.1.1"
        and superpowers.get("releaseDeltaCommitCount") == 51
        and superpowers.get("releaseDeltaChangedFileCount") == 54
        and superpowers.get("releaseDeltaSkillPathChangedFileCount") == 26
        and superpowers.get("currentRuntimePackageVersion") == "6.2.0"
        and superpowers.get("currentRuntimePackageRootClass")
        == "codex-plugin-cache-home-relative"
        and superpowers.get("currentRuntimePackageRootHomeRelative")
        == ".codex/plugins/cache/openai-curated-remote/superpowers/6.2.0"
        and superpowers.get("hostLocalPathRedacted") is True
        and superpowers.get("currentRuntimePackageFileCount") == 72
        and superpowers.get("currentRuntimePackageTreeSha256")
        == "948ff71f332ad9bb3f1031ad468bf0a6f6a55c80d1c106f92a831b63e6ea7874"
        and superpowers.get("exactUpstreamBlobCount") == 55
        and superpowers.get("openaiPackagingDifferenceCount") == 17
        and superpowers.get("openaiPackagingDifferenceClasses")
        == {
            "pluginManifest": 1,
            "pluginAssets": 2,
            "agentsOpenaiMetadata": 14,
        }
        and superpowers.get("skillEntryCount") == 14
        and superpowers.get("exactReleaseSkillEntryCount") == 14
        and superpowers.get("allSkillEntriesExactReleaseBytes") is True
        and superpowers.get("selectedSkillDigests") == EXPECTED_SKILL_DIGESTS
        and superpowers.get("priorSixSkillSample", {}).get("unchanged")
        == ["using-superpowers"]
        and superpowers.get("priorSixSkillSample", {}).get("changed")
        == [
            "brainstorming",
            "writing-plans",
            "verification-before-completion",
            "subagent-driven-development",
            "systematic-debugging",
        ],
        "Superpowers 6.2.0 source or package observation changed.",
    )
    _require(
        all(
            isinstance(value, str)
            and len(value) == 64
            and all(character in "0123456789abcdef" for character in value)
            for value in superpowers["selectedSkillDigests"].values()
        ),
        "Superpowers selected Skill digest shape changed.",
    )
    packaging = superpowers["openaiPackagingDifferenceClasses"]
    sample = superpowers["priorSixSkillSample"]
    _require(
        superpowers["currentRuntimePackageFileCount"]
        == superpowers["exactUpstreamBlobCount"]
        + superpowers["openaiPackagingDifferenceCount"]
        and sum(packaging.values())
        == superpowers["openaiPackagingDifferenceCount"]
        and superpowers["skillEntryCount"]
        == superpowers["exactReleaseSkillEntryCount"]
        == len(EXPECTED_SKILL_DIGESTS)
        and set(sample["unchanged"]).isdisjoint(sample["changed"])
        and set(sample["unchanged"] + sample["changed"])
        <= set(EXPECTED_SKILL_DIGESTS),
        "Superpowers package or sample arithmetic changed.",
    )

    governance = document.get("superpowers620GovernanceReview")
    _require(
        isinstance(governance, dict)
        and isinstance(governance.get("selectiveReuseCandidates"), list)
        and isinstance(governance.get("globalDefaultRejections"), list)
        and all(
            isinstance(item, dict)
            for item in governance["selectiveReuseCandidates"]
            + governance["globalDefaultRejections"]
        )
        and isinstance(governance.get("conditionalExternalEffect"), dict),
        "Superpowers governance shape changed.",
    )
    _require(
        [
            (item["capability"], item["disposition"])
            for item in governance["selectiveReuseCandidates"]
        ]
        == [
            (
                "test-driven-development",
                "retain-source-pinned-single-skill-comparison-arm",
            ),
            (
                "systematic-debugging",
                "retain-selective-diagnostic-candidate",
            ),
            (
                "verification-before-completion",
                "retain-as-domain-verification-substep-candidate",
            ),
            (
                "subagent-driven-development",
                "retain-pattern-reference-not-default-controller",
            ),
        ]
        and [
            item["capability"] for item in governance["globalDefaultRejections"]
        ]
        == [
            "using-superpowers",
            "brainstorming",
            "full-superpowers-bootstrap",
        ]
        and governance.get("conditionalExternalEffect", {}).get(
            "automaticAtPluginStartup"
        )
        is False
        and governance.get("conditionalExternalEffect", {}).get(
            "requiresOfferAndUserAcceptance"
        )
        is True
        and governance.get("conditionalExternalEffect", {}).get(
            "remoteLogoMayCarryVersionTelemetryByDefault"
        )
        is True
        and governance.get("conditionalExternalEffect", {}).get(
            "projectPromptOrClickTelemetryClaimed"
        )
        is False
        and governance.get("conditionalExternalEffect", {}).get(
            "disableEnvironmentVariablesDocumented"
        )
        is True
        and governance.get("conditionalExternalEffect", {}).get(
            "activatedOrTestedHere"
        )
        is False,
        "Superpowers selective-governance review changed.",
    )
    _require(
        all(
            not any(
                word in item["disposition"]
                for word in ("adopt", "admitted", "approved", "global-default")
            )
            for item in governance["selectiveReuseCandidates"]
        ),
        "Superpowers selective candidate was promoted to an execution default.",
    )
    decision = document.get("decision")
    _require(
        isinstance(decision, dict),
        "Skill runtime drift decision shape changed.",
    )
    _require(
        decision.get("oldUiCountWasNecessarilyWrong") is False
        and decision.get("oldUiCountWasPhysicalUniqueSkillCount") is False
        and decision.get("currentCountMustBeReportedByLayer") is True
        and decision.get("ccSwitchStaleRowGapResolved") is False
        and decision.get("superpowers611RemainsCurrentComparisonBaseline")
        is False
        and decision.get(
            "superpowers620IsCurrentRuntimeOwnedSourcePackageBaseline"
        )
        is True
        and decision.get("superpowers620IsBehavioralBaseline") is False
        and decision.get("executionAdmissionSatisfied") is False
        and decision.get("loaderInvocationObserved") is False
        and decision.get("copySuperpowersRuntimePayloadsIntoCcForCodex")
        is False
        and decision.get("bulkInstallFromEnabledRepositoriesJustified")
        is False
        and decision.get("currentMattPinnedEvidenceStillFresh") is True
        and decision.get("currentTdd620SelectiveProtocolInvalidated")
        is False
        and decision.get(
            "selectiveProtocolSourcePinsDoNotImplyExecutionEligibility"
        )
        is True
        and decision.get("selfAuthoredContractsCanBeRetiredFromStaticEvidence")
        is False
        and decision.get("portfolioMutationAuthorized") is False,
        "Skill runtime drift portfolio decision changed.",
    )
    next_action = decision.get("nextBoundedAction")
    _require(
        isinstance(next_action, str)
        and all(
            phrase in next_action
            for phrase in (
                "source-pinned selective arms",
                "current pinned revision",
                "live weak-Agent attribution",
                "before any deduplication, retirement, or source migration",
            )
        ),
        "Skill runtime drift next bounded action changed.",
    )
    claims = document.get("claimBoundary")
    _require(
        isinstance(claims, dict)
        and set(claims) == EXPECTED_CLAIM_BOUNDARY_KEYS
        and all(value is False for value in claims.values()),
        "Skill runtime drift claim boundary was promoted.",
    )
    claim_limit = document.get("claimLimit")
    _require(
        document.get("documentation") == DOC_PATH
        and (root / DOC_PATH).is_file()
        and isinstance(claim_limit, str)
        and all(
            phrase in claim_limit
            for phrase in (
                "single-host inventory",
                "does not prove loader invocation",
                "cross-device equality",
                "migration safety",
                "residual self-authored gap",
            )
        ),
        "Skill runtime drift documentation binding changed.",
    )
    normalized = " ".join(
        (root / DOC_PATH).read_text(encoding="utf-8").split()
    )
    for phrase in (
        "current-host read-only drift reconciled; no mutation",
        "not the number of unique physical, resolvable Skill bodies",
        "14 `SKILL.md` entries are all exact release bytes",
        "source/package baseline, not a behavioral baseline",
        "Do not make `using-superpowers`, `brainstorming`, or the full bootstrap a global default",
        "Exact bytes prove source identity, not invocation or value",
        "does not prove restore success or content equality after moving to another device",
    ):
        _require(
            phrase in normalized,
            f"Skill runtime drift documentation missing: {phrase}",
        )

    acceptance_map = json.loads(
        (root / ACCEPTANCE_MAP_PATH).read_text(encoding="utf-8")
    )
    evidence_items = acceptance_map.get("evidence")
    acceptance_items = acceptance_map.get("acceptanceCriteria")
    _require(
        isinstance(evidence_items, list)
        and isinstance(acceptance_items, list)
        and all(isinstance(item, dict) for item in evidence_items)
        and all(isinstance(item, dict) for item in acceptance_items),
        "Skill runtime drift acceptance map shape changed.",
    )
    evidence_records = {
        item["id"]: item
        for item in evidence_items
        if isinstance(item.get("id"), str)
    }
    _require(
        evidence_records.get(EVIDENCE_ID)
        == {
            "id": EVIDENCE_ID,
            "path": EVIDENCE_PATH,
            "kind": (
                "current-host-read-only-layered-cc-count-and-superpowers-"
                "6.2.0-source-drift-reconciliation-no-mutation"
            ),
            "asOf": "2026-07-27",
            "supports": SUPPORTED_ACCEPTANCE_IDS,
        },
        "Skill runtime drift acceptance evidence record changed.",
    )
    acceptance_records = {
        item["id"]: item
        for item in acceptance_items
        if isinstance(item.get("id"), str)
    }
    _require(
        all(
            acceptance_id in acceptance_records
            and isinstance(
                acceptance_records[acceptance_id].get("evidenceIds"),
                list,
            )
            and
            EVIDENCE_ID in acceptance_records[acceptance_id]["evidenceIds"]
            for acceptance_id in SUPPORTED_ACCEPTANCE_IDS
        ),
        "Skill runtime drift acceptance backlink changed.",
    )
    for carrier_path in (CONTINUATION_PATH, RESEARCH_PLAN_PATH):
        carrier = " ".join(
            (root / carrier_path).read_text(encoding="utf-8").split()
        )
        _require(
            "SKILL-RUNTIME-AND-CC-COUNT-DRIFT-SNAPSHOT-2026-07-27.md"
            in carrier
            and "source/package baseline" in carrier
            and "prove invocation" in carrier
            and (
                "copying it into CC" in carrier
                or "copy runtime-owned Superpowers payloads into CC"
                in carrier
            ),
            f"Skill runtime drift carrier boundary changed: {carrier_path}",
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    root = args.root.resolve()
    document = json.loads(
        (root / EVIDENCE_PATH).read_text(encoding="utf-8")
    )
    validate_snapshot(document, root=root)
    print("Skill runtime and CC count drift snapshot passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
