#!/usr/bin/env python3
"""Validate the dated Skill source-and-layer classification."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def validate_classification(document: dict[str, object], root: Path = ROOT) -> None:
    expected_header = {
        "schema": 1,
        "id": "skill-portfolio-source-and-layer-classification-2026-07-28",
        "date": "2026-07-28",
        "status": "verified-read-only-single-host-classification-no-portfolio-mutation",
    }
    for key, expected in expected_header.items():
        if document.get(key) != expected:
            raise ValueError(f"classification {key} drifted")

    standards = document.get("standards")
    if not isinstance(standards, dict):
        raise ValueError("classification standards missing")
    if (
        standards.get("nameMustMatchParentDirectory") is not True
        or standards.get("portablePhysicalSourceGroupingInsideActiveSkillRoot")
        is not False
        or standards.get("metadataMapAllowed") is not True
        or standards.get("thirdPartyBodiesShouldBeRewrittenForClassification")
        is not False
    ):
        raise ValueError("Agent Skills directory or metadata boundary drifted")

    dimensions = document.get("classificationDimensions")
    expected_dimensions = {
        "source-authority",
        "carrier",
        "capability-layer",
        "lifecycle",
        "exposure-evidence",
    }
    if (
        not isinstance(dimensions, list)
        or {item.get("id") for item in dimensions if isinstance(item, dict)}
        != expected_dimensions
    ):
        raise ValueError("classification dimensions drifted")

    observation = document.get("currentHostObservation")
    if not isinstance(observation, dict):
        raise ValueError("current host observation missing")
    cc = observation.get("ccSwitch")
    if not isinstance(cc, dict):
        raise ValueError("CC Switch observation missing")
    source_counts = cc.get("installedRowsByRecordedSource")
    if (
        cc.get("ccSwitchVersion") is not None
        or cc.get("skillsTableRows") != 75
        or cc.get("distinctSkillNames") != 73
        or not isinstance(source_counts, dict)
        or sum(source_counts.values()) != 75
        or cc.get("mattInstalledSkills") != ["handoff"]
        or cc.get("databaseCategoryOrTagFields") != []
        or cc.get("installedUiShowsInlineSource") is not True
        or cc.get("installedUiExposesCategoryOrTagFilter") is not False
        or cc.get("directDatabaseMutationAllowed") is not False
    ):
        raise ValueError("CC Switch classification observation drifted")

    runtime = observation.get("runtimeAndPluginCarriers")
    if (
        not isinstance(runtime, dict)
        or runtime.get("systemSkillMdFiles") != 6
        or runtime.get("pluginCacheSkillMdFiles") != 328
        or sum(runtime.get("pluginCacheBreakdown", {}).values()) != 328
        or runtime.get("cachePresenceProvesCurrentExposure") is not False
        or runtime.get("pluginOrAppSkillsAutomaticallyBelongToCcSwitch")
        is not False
    ):
        raise ValueError("runtime/plugin carrier boundary drifted")

    counts = observation.get("countReconciliation")
    if (
        not isinstance(counts, dict)
        or counts.get("historical251IsCurrentInstalledCount") is not False
        or counts.get("currentInstalledCount") != 75
        or counts.get("currentUiMeaningOf251Reobserved") is not False
    ):
        raise ValueError("historical count boundary drifted")

    controls = document.get("selfAuthoredControlPlane")
    if not isinstance(controls, list):
        raise ValueError("self-authored control-plane classification missing")
    by_name = {
        item.get("name"): item
        for item in controls
        if isinstance(item, dict) and isinstance(item.get("name"), str)
    }
    if set(by_name) != {
        "intent-contract",
        "capability-router",
        "closure-contract",
    }:
        raise ValueError("self-authored control-plane names drifted")
    if any(
        item.get("capabilityLayer") != "semantic-control-plane"
        or item.get("provenFullReplacement") is not None
        for item in by_name.values()
    ):
        raise ValueError("self-authored replacement claim drifted")
    if (
        by_name["capability-router"].get("currentDisposition")
        != "provisional-retain-no-known-full-suite-replacement-proved"
    ):
        raise ValueError("capability-router disposition drifted")

    management = document.get("managementModel")
    if (
        not isinstance(management, dict)
        or management.get("physicalSkillRootsStayFlat") is not True
        or management.get("ccSwitchRemainsManagerForSharedNonOfficialInstalledSkills")
        is not True
        or management.get("runtimeOwnedAndPluginAppSkillsRemainRuntimeOwned")
        is not True
        or management.get("classificationIsDerivedRegistryNotSecondPayloadStore")
        is not True
    ):
        raise ValueError("management model drifted")

    decisions = document.get("currentDecisions")
    if not isinstance(decisions, dict):
        raise ValueError("classification decisions missing")
    required_false = {
        "retireSelfAuthoredControlPlaneNow",
        "claimCapabilityRouterHasAProvenCompleteReplacement",
        "restoreOrEnableHookByThisClassification",
        "installOrUninstallSkillsByThisClassification",
        "moveSkillsIntoNestedSourceDirectories",
        "rewriteThirdPartySkillFrontmatterForLocalTags",
        "changeCcSwitchDatabaseSchemaOrRows",
        "treatAllCachedPluginSkillsAsActive",
    }
    if any(decisions.get(key) is not False for key in required_false):
        raise ValueError("classification authorized a forbidden mutation or claim")
    if decisions.get("useDerivedClassificationBeforePortfolioMutation") is not True:
        raise ValueError("derived classification gate missing")

    documentation = root / str(document.get("documentation"))
    text = " ".join(documentation.read_text(encoding="utf-8").split())
    for phrase in (
        "Keep active Skill roots flat.",
        "No known complete one-for-one replacement is proved.",
        "Current installed evidence is 75.",
        "Direct SQLite mutation is not an acceptable way to add tags.",
        "classification performs no installation",
    ):
        if phrase not in text:
            raise ValueError(f"classification documentation missing: {phrase}")


def main() -> int:
    path = (
        ROOT
        / "registry/skill-portfolio-source-and-layer-classification-2026-07-28.json"
    )
    validate_classification(json.loads(path.read_text(encoding="utf-8")))
    print("Skill portfolio source-and-layer classification validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
