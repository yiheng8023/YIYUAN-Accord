#!/usr/bin/env python3
"""Validate the six-specialist Skill portfolio static triage."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_PATH = (
    "registry/skill-portfolio-six-specialist-static-triage-2026-07-30.json"
)
DOCUMENTATION_PATH = (
    "docs/strategy/"
    "SKILL-PORTFOLIO-SIX-SPECIALIST-STATIC-TRIAGE-2026-07-30.md"
)
EXPECTED_NAMES = {
    "disciplined-coding",
    "migrate-to-shoehorn",
    "obsidian-open-format-knowledge-files",
    "obsidian-vault",
    "playwright",
    "security-ownership-map",
}
EXPECTED_REMOVAL_PREVIEW = EXPECTED_NAMES - {
    "obsidian-open-format-knowledge-files"
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
        == "skill-portfolio-six-specialist-static-triage-2026-07-30"
        and document.get("date") == "2026-07-30"
        and document.get("status")
        == "read-only-static-triage-five-removal-preview-candidates-one-retain",
        "Six-specialist triage identity drifted",
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
        "Six-specialist repository posture drifted",
    )
    authority = document.get("authorityBoundary", {})
    _require(
        authority.get("readLiveCcDatabase") is True
        and authority.get("readInstalledSkillBodiesAndTrees") is True
        and authority.get("readPublicPrimarySourcesAndPackageMetadata") is True
        and authority.get("readCurrentCapabilityInventory") is True
        and authority.get("sourceBodyExecution") is False
        and authority.get("dependencyInstall") is False
        and authority.get("skillInstallUpdateDisableOrDelete") is False
        and authority.get("ccSwitchMutation") is False
        and authority.get("globalConfigHookRulesOrForeignRootMutation") is False
        and authority.get("modelDispatch") is False
        and authority.get("gitCommitOrPush") is False,
        "Six-specialist authority boundary drifted",
    )
    live = document.get("liveState", {})
    _require(
        live.get("databaseRows") == 55
        and live.get("targetRows") == 6
        and live.get("targetRowsWithSourceMetadata") == 0
        and live.get("allTargetsClaudeEnabled") is True
        and live.get("allTargetsCodexEnabled") is True
        and live.get("allTargetsOtherRecordedHostsDisabled") is True
        and live.get("currentCodexPluginEnabledSkillCount") == 76
        and live.get("allSixCurrentlyCodexExposed") is True
        and live.get("noNewModelRequestSent") is True,
        "Six-specialist live-state evidence drifted",
    )
    refresh = document.get("primarySourceRefresh", {})
    openai = refresh.get("openaiSkills", {})
    _require(
        openai.get("mainRevision")
        == "49f948faa9258a0c61caceaf225e179651397431"
        and openai.get("playwrightWholeTreeFileCount") == 9
        and openai.get(
            "playwrightWholeTreeMatchesCurrentUpstreamAfterLfNormalization"
        )
        is True
        and openai.get("securityOwnershipMapWholeTreeFileCount") == 8
        and openai.get(
            "securityOwnershipMapWholeTreeMatchesCurrentUpstreamAfterLfNormalization"
        )
        is True,
        "Six-specialist OpenAI source refresh drifted",
    )
    matt = refresh.get("mattpocockSkills", {})
    _require(
        matt.get("mainRevision")
        == "2ab958093e83e0ec752e6c1c5932da465bf23e0c"
        and matt.get("migrateToShoehornLifecycle") == "misc-non-promoted"
        and matt.get("migrateToShoehornLiveTreeMatchesCurrentUpstream") is False
        and matt.get("obsidianVaultLifecycle") == "personal-non-promoted"
        and matt.get("obsidianVaultLiveTreeMatchesCurrentUpstream") is False
        and matt.get("disciplinedCodingExistsInCurrentTree") is False,
        "Six-specialist Matt source refresh drifted",
    )
    kepano = refresh.get("kepanoObsidianSkills", {})
    _require(
        kepano.get("mainRevision")
        == "a1dc48e68138490d522c04cbf5822214c6eb1202"
        and kepano.get("installedAdaptationDeclaredSourceRevision")
        == kepano.get("mainRevision")
        and kepano.get("declaredSourceRevisionIsCurrentMain") is True,
        "Six-specialist Obsidian source refresh drifted",
    )
    packages = refresh.get("packageMetadata", {})
    _require(
        packages.get("shoehorn", {}).get("version") == "0.1.2"
        and packages.get("shoehorn", {}).get("license") == "MIT"
        and packages.get("playwrightCli", {}).get("version") == "0.1.17"
        and packages.get("playwrightCli", {}).get("license") == "Apache-2.0",
        "Six-specialist package metadata drifted",
    )
    items = document.get("items", [])
    by_name = {item.get("name"): item for item in items}
    _require(
        len(items) == 6 and set(by_name) == EXPECTED_NAMES,
        "Six-specialist item coverage drifted",
    )
    expected_counts = {
        "disciplined-coding": (2, 6075),
        "migrate-to-shoehorn": (1, 3377),
        "obsidian-open-format-knowledge-files": (1, 4394),
        "obsidian-vault": (1, 1932),
        "playwright": (9, 23256),
        "security-ownership-map": (8, 101180),
    }
    for name, (file_count, byte_count) in expected_counts.items():
        item = by_name[name]
        _require(
            item.get("fileCount") == file_count
            and item.get("bytes") == byte_count
            and isinstance(item.get("skillSha256"), str)
            and len(item["skillSha256"]) == 64
            and isinstance(item.get("treeManifestSha256"), str)
            and len(item["treeManifestSha256"]) == 64
            and isinstance(item.get("ccContentHash"), str)
            and len(item["ccContentHash"]) == 64,
            f"Six-specialist static identity drifted: {name}",
        )
    _require(
        by_name["disciplined-coding"].get("sourceAuthorityBound") is False
        and by_name["disciplined-coding"].get("currentUpstreamExact") is False
        and "native passed the recorded strict process 3/3"
        in by_name["disciplined-coding"].get("behaviorEvidence", ""),
        "Disciplined-coding evidence boundary drifted",
    )
    _require(
        by_name["migrate-to-shoehorn"].get("repositoryApprovedPayloadByteEqual")
        is True
        and by_name["migrate-to-shoehorn"].get("currentUpstreamExact") is False
        and by_name["migrate-to-shoehorn"].get("runtimeDependencies")
        == ["@total-typescript/shoehorn"],
        "Shoehorn disposition evidence drifted",
    )
    open_format = by_name["obsidian-open-format-knowledge-files"]
    _require(
        open_format.get("repositoryApprovedPayloadByteEqual") is True
        and open_format.get("declaredSourceRevisionCurrent") is True
        and open_format.get("runtimeDependencies") == []
        and open_format.get("disposition") == "retain-active",
        "Open-format retain evidence drifted",
    )
    _require(
        by_name["obsidian-vault"].get("repoVaultPathFilePresent") is False
        and by_name["obsidian-vault"].get("vaultPathEnvironmentPresent") is False
        and by_name["obsidian-vault"].get("currentUpstreamExact") is False,
        "Obsidian-vault disposition evidence drifted",
    )
    _require(
        by_name["playwright"].get("currentUpstreamExactAfterLfNormalization")
        is True
        and by_name["playwright"].get("npxPresent") is True
        and by_name["playwright"].get("playwrightCliGloballyInstalled") is False
        and "live Playwright MCP tools"
        in by_name["playwright"].get("currentHostAlternatives", []),
        "Playwright carrier evidence drifted",
    )
    _require(
        by_name["security-ownership-map"].get(
            "currentUpstreamExactAfterLfNormalization"
        )
        is True
        and by_name["security-ownership-map"].get(
            "networkxInstalledInCurrentPython"
        )
        is False
        and "Git history"
        in by_name["security-ownership-map"].get("dataBoundary", ""),
        "Security ownership dependency or data boundary drifted",
    )
    decision = document.get("decision", {})
    _require(
        set(decision.get("retainActive", []))
        == {"obsidian-open-format-knowledge-files"}
        and set(decision.get("readyForManagerRemovalPreview", []))
        == EXPECTED_REMOVAL_PREVIEW
        and decision.get("readyCount") == 5
        and decision.get("readyFileCount") == 21
        and decision.get("readyPayloadBytes") == 135820
        and decision.get(
            "allFiveHaveNoObservedHardNamedDependencyFromRetainedSkillBodies"
        )
        is True
        and decision.get("removalMeansActiveCcCopyOnly") is True
        and decision.get("sourceAndApprovedPayloadMetadataRemain") is True
        and decision.get("directUninstallAuthorized") is False,
        "Six-specialist decision boundary drifted",
    )
    cleanup = document.get("cleanup", {})
    _require(
        cleanup
        == {
            "temporarySourceRootCreated": False,
            "temporarySourceRootAbsent": True,
            "noSourceBodyExecuted": True,
            "noDependencyInstalled": True,
            "repositoryCleanupInventoryStable": True,
        },
        "Six-specialist cleanup evidence drifted",
    )
    claims = document.get("claimBoundary", {})
    _require(
        claims.get("currentStaticSourceAndDependencyTriageProved") is True
        and claims.get("currentManagerAndCodexExposureReusedFromDatedLiveEvidence")
        is True
        and claims.get("openFormatRetainDecisionSupported") is True
        and claims.get("fiveItemRemovalPreviewEligibilitySupported") is True
        and claims.get("fiveItemManagerRemovalAuthorized") is False
        and claims.get("behavioralValueProvedForAllSix") is False
        and claims.get("crossHostValueProvedForAllSix") is False
        and claims.get("programCloseoutProved") is False,
        "Six-specialist claim boundary drifted",
    )
    _require(
        document.get("documentation") == DOCUMENTATION_PATH,
        "Six-specialist documentation binding drifted",
    )
    text = (root / DOCUMENTATION_PATH).read_text(encoding="utf-8")
    for phrase in (
        "not one homogeneous group",
        "Eligibility is not deletion authority",
        "retaining exactly",
        "historical documents that called it a Matt-family treatment",
        "The problem is carrier placement",
        "required `networkx` dependency",
        "applies only to the active CC copies",
    ):
        _require(
            phrase in text,
            f"Six-specialist documentation missing: {phrase}",
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    root = args.root.resolve()
    document = json.loads((root / EVIDENCE_PATH).read_text(encoding="utf-8"))
    validate_triage(document, root=root)
    print("Six-specialist Skill portfolio static triage passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
