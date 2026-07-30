#!/usr/bin/env python3
"""Fail closed on drift in the bounded other-Skill scenario coverage audit."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
AUDIT_PATH = (
    "registry/other-cc-and-external-skill-scenario-coverage-audit-"
    "2026-07-27.json"
)
DOCUMENTATION_PATH = (
    "docs/strategy/OTHER-CC-AND-EXTERNAL-SKILL-SCENARIO-COVERAGE-"
    "AUDIT-2026-07-27.md"
)
MATRIX_PATH = (
    "registry/human-ai-collaboration-scenario-evidence-matrix-batch-01-"
    "2026-07-24.json"
)
RECONCILIATION_PATH = (
    "registry/skill-ecosystem-current-evidence-reconciliation-2026-07-27.json"
)
OVERLAP_PATH = (
    "registry/skill-ecosystem-overlap-and-ablation-matrix-2026-07-23.json"
)
REQUIREMENTS_PATH = (
    "registry/human-ai-collaboration-requirements-domain-live-comparison-"
    "batch-01-2026-07-24.json"
)
IMPLEMENTATION_PATH = (
    "registry/human-ai-collaboration-weak-agent-live-comparison-batch-01-"
    "2026-07-24.json"
)
DIAGNOSE_PATH = (
    "registry/human-ai-collaboration-weak-agent-live-comparison-batch-02-"
    "2026-07-24.json"
)
DEBUGGING_PATH = (
    "registry/human-ai-collaboration-weak-agent-live-comparison-batch-03-"
    "2026-07-24.json"
)
MAINTENANCE_PATH = (
    "registry/human-ai-collaboration-maintenance-migration-live-comparison-"
    "batch-01-2026-07-24.json"
)
COUNT_PATH = "registry/skill-runtime-and-cc-count-drift-snapshot-2026-07-27.json"
SKILLS_PATH = "registry/skills.json"
ADMISSIONS_PATH = "registry/admissions.json"
RELEASE_PATH = "release-manifest.json"

CURRENT_OBSERVED = {
    ("SE-DISCOVERY-REQ-01", "cc.grill-with-docs"): (
        "three-valid-pairs-both-arms-fail-hidden-contract"
    ),
    ("SE-IMPLEMENT-REVIEW-01", "cc.disciplined-coding"): (
        "bounded-functional-pass-mixed-process-no-causation"
    ),
    ("SE-OPS-INCIDENT-01", "cc.diagnose"): (
        "bounded-association-not-current-matt-or-causation"
    ),
    ("SE-OPS-INCIDENT-01", "matt.current-diagnosing-bugs"): (
        "source-pinned-mixed-result-no-preference-or-causation"
    ),
    ("SE-MAINT-MIGRATE-01", "cc.deprecation-and-migration"): (
        "bounded-native-association-no-general-preference-or-causation"
    ),
}
HISTORICAL_OBSERVED = {
    ("SE-OPS-INCIDENT-01", "superpowers.runtime-6.1.1-systematic-debugging")
}
PLANNED_ONLY = {
    "GEN-CREATIVE-01",
    "GEN-LEARNING-01",
    "GEN-ORG-DECISION-01",
    "GEN-ACCESS-COMMS-01",
    "SE-RELEASE-CHANGE-01",
    "SE-MGMT-PRACTICE-01",
}
ZERO_MODEL_ONLY = {
    "SE-ARCH-DESIGN-01",
    "SE-VERIFY-SECURE-01",
}
RELEASE_CANDIDATES = {
    "skill.curated.ci-cd-and-automation": {
        "path": "skills/ci-cd-and-automation/SKILL.md",
        "sha256": (
            "7aa008e4be26068c9e61ea8a9303711020e376c6cbfdf10d581a9fd400acf8ea"
        ),
    },
    "skill.curated.shipping-and-launch": {
        "path": "skills/shipping-and-launch/SKILL.md",
        "sha256": (
            "195a1fad5612627464df4581954727b8ebd649b0ce4bfe91e06655bcc32302b0"
        ),
    },
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _load(root: Path, path: str) -> dict[str, Any]:
    return json.loads((root / path).read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _items_by(
    items: list[dict[str, Any]], key: str
) -> dict[str, dict[str, Any]]:
    _require(isinstance(items, list), f"items for {key} must be a list")
    result: dict[str, dict[str, Any]] = {}
    for item in items:
        _require(
            isinstance(item, dict) and key in item,
            f"item is missing identity key: {key}",
        )
        identity = str(item[key])
        _require(
            identity not in result,
            f"duplicate identity for {key}: {identity}",
        )
        result[identity] = item
    return result


def validate_audit(
    document: dict[str, Any],
    *,
    root: Path = ROOT,
) -> None:
    _require(document.get("schema") == 1, "audit schema must be 1")
    _require(
        document.get("id")
        == "other-cc-and-external-skill-scenario-coverage-audit-2026-07-27",
        "audit identity drifted",
    )
    _require(
        document.get("status")
        == "verified-next-named-scenario-ready-for-offline-protocol-only-"
        "no-live-arm",
        "audit status drifted",
    )

    expected_paths = {
        MATRIX_PATH,
        RECONCILIATION_PATH,
        OVERLAP_PATH,
        REQUIREMENTS_PATH,
        IMPLEMENTATION_PATH,
        DIAGNOSE_PATH,
        DEBUGGING_PATH,
        MAINTENANCE_PATH,
        COUNT_PATH,
        SKILLS_PATH,
        ADMISSIONS_PATH,
        RELEASE_PATH,
    }
    bindings = _items_by(document.get("sourceBindings", []), "path")
    _require(set(bindings) == expected_paths, "source binding set drifted")
    for path, binding in bindings.items():
        source = root / path
        _require(source.is_file(), f"source binding missing: {path}")
        _require(
            binding.get("bytes") == len(source.read_bytes()),
            f"source binding byte count drifted: {path}",
        )
        _require(
            binding.get("sha256") == _sha256(source),
            f"source binding digest drifted: {path}",
        )

    matrix = _load(root, MATRIX_PATH)
    reconciliation = _load(root, RECONCILIATION_PATH)
    overlap = _load(root, OVERLAP_PATH)
    requirements = _load(root, REQUIREMENTS_PATH)
    implementation = _load(root, IMPLEMENTATION_PATH)
    diagnose = _load(root, DIAGNOSE_PATH)
    debugging = _load(root, DEBUGGING_PATH)
    maintenance = _load(root, MAINTENANCE_PATH)
    counts = _load(root, COUNT_PATH)
    skills = _load(root, SKILLS_PATH)
    admissions = _load(root, ADMISSIONS_PATH)
    release = _load(root, RELEASE_PATH)

    # Current behavioral cells are copied from the current reconciliation,
    # not inferred from body counts or source identity.
    evidence_cells = reconciliation.get("evidenceCells", [])
    current_cells = {
        (item["scenarioId"], item["candidateId"]): item
        for item in evidence_cells
        if item.get("currentBehavioralEvidence") is True
        and item.get("candidateId") != "native.spark-low-tdd"
    }
    _require(
        set(current_cells) == set(CURRENT_OBSERVED),
        "current observed candidate cell set drifted",
    )
    for key, expected_classification in CURRENT_OBSERVED.items():
        cell = current_cells[key]
        fidelity = cell.get("treatmentFidelity", {})
        _require(
            cell.get("validRepetitions") == 3
            and cell.get("classification") == expected_classification,
            f"current observed cell classification drifted: {key}",
        )
        _require(
            fidelity.get("taskScopedExposureProved") is True
            and fidelity.get("independentLoaderEventProved") is False
            and fidelity.get("candidateInstructionsReachedModelProved")
            is False,
            f"current observed cell fidelity boundary drifted: {key}",
        )
    historical_cells = {
        (item["scenarioId"], item["candidateId"]): item
        for item in evidence_cells
        if item.get("candidateId")
        == "superpowers.runtime-6.1.1-systematic-debugging"
    }
    _require(
        set(historical_cells) == HISTORICAL_OBSERVED
        and all(
            item.get("currentBehavioralEvidence") is False
            for item in historical_cells.values()
        ),
        "historical Superpowers behavior boundary drifted",
    )
    reconciliation_claims = reconciliation.get("claimBoundary", {})
    _require(
        reconciliation_claims.get("superpowers611BehaviorProves620Behavior")
        is False
        and reconciliation_claims.get("selectedExposureProvesLoaderInvocation")
        is False
        and reconciliation_claims.get(
            "boundedAssociationProvesGeneralPreference"
        )
        is False
        and reconciliation_claims.get("ccCountProvesLoadedOrInvokedCount")
        is False,
        "current reconciliation claim boundary drifted",
    )

    # Bind the source live-comparison documents as bounded association
    # evidence and reject any later value/causation promotion.
    _require(
        requirements.get("status")
        == "three-valid-pairs-both-arms-fail-hidden-contract-"
        "no-preference-or-causation"
        and requirements.get("aggregateResult", {}).get(
            "candidateEffectOrCausationProved"
        )
        is False,
        "requirements observation boundary drifted",
    )
    _require(
        implementation.get("status")
        == "three-paired-observations-complete-mixed-process-outcome",
        "implementation observation boundary drifted",
    )
    _require(
        diagnose.get("status")
        == "three-paired-observations-complete-association-not-causation"
        and diagnose.get("aggregateResult", {}).get(
            "candidateEffectOrCausationProved"
        )
        is False,
        "CC diagnose observation boundary drifted",
    )
    _require(
        debugging.get("status")
        == "three-source-pinned-pairs-complete-no-preference-or-causation"
        and debugging.get("aggregateResult", {}).get(
            "candidateEffectOrCausationProved"
        )
        is False
        and debugging.get("treatmentFidelityBoundary", {}).get(
            "candidateSpecificInstructionsReachedModelProved"
        )
        is False,
        "source-pinned debugging observation boundary drifted",
    )
    _require(
        maintenance.get("status")
        == "three-valid-pairs-native-association-no-causation-or-"
        "portfolio-preference"
        and maintenance.get("aggregateResult", {}).get(
            "candidateEffectOrCausationProved"
        )
        is False,
        "maintenance observation boundary drifted",
    )

    # The old CC sample is static only; current package/count evidence stays
    # metadata and must not be promoted into scenario coverage.
    cohort = overlap.get("ccInstalledStaticComparisonCohort", {})
    cohort_names = {item["name"] for item in cohort.get("skills", [])}
    _require(
        cohort.get("observationClass") == "single-host-local-file-static-only"
        and cohort_names == {"grill-me", "grill-with-docs", "review"},
        "historical static CC cohort drifted",
    )
    cohort_claims = cohort.get("claimBoundary", {})
    _require(
        cohort_claims.get("currentEnablementProved") is False
        and cohort_claims.get("loaderInvocationProved") is False
        and cohort_claims.get("behavioralValueProved") is False,
        "historical static CC cohort was promoted",
    )
    _require(
        all(
            scenario.get("livePacketReady") is False
            for scenario in overlap.get("scenarios", [])
        ),
        "historical ablation matrix was promoted to live evidence",
    )

    cc_observation = counts.get("ccSwitchObservation", {})
    database = cc_observation.get("database", {})
    roots = cc_observation.get("roots", {})
    count_semantics = cc_observation.get("countSemantics", {})
    _require(
        database.get("rows") == 251
        and database.get("distinctNames") == 233
        and roots.get("ccSwitch", {}).get("physical") == 75
        and roots.get("codex", {}).get("resolvableSkillMd") == 75
        and roots.get("claude", {}).get("unresolvedSkillMd") == 176,
        "current CC layered count drifted",
    )
    _require(
        count_semantics.get(
            "uiOrEnabledRowCountEqualsPhysicalUniqueSkillCount"
        )
        is False
        and count_semantics.get("databaseRowCountProvesLoaderInvocation")
        is False,
        "current CC count semantics drifted",
    )
    superpowers = counts.get("externalSourceRevalidation", {}).get(
        "superpowers", {}
    )
    _require(
        superpowers.get("currentRuntimePackageVersion") == "6.2.0"
        and superpowers.get("skillEntryCount") == 14
        and superpowers.get("exactReleaseSkillEntryCount") == 14
        and superpowers.get("allSkillEntriesExactReleaseBytes") is True,
        "current Superpowers source baseline drifted",
    )
    count_decision = counts.get("decision", {})
    _require(
        count_decision.get("superpowers620IsBehavioralBaseline") is False
        and count_decision.get("executionAdmissionSatisfied") is False
        and count_decision.get("loaderInvocationObserved") is False
        and count_decision.get("bulkInstallFromEnabledRepositoriesJustified")
        is False,
        "current package/count evidence was promoted",
    )

    scenarios = _items_by(matrix.get("scenarios", []), "id")
    _require(
        all(
            scenarios[scenario_id].get("evidenceState")
            == "planned-no-live-domain-evidence"
            for scenario_id in PLANNED_ONLY
        ),
        "planned-only scenario set drifted",
    )
    _require(
        scenarios["SE-ARCH-DESIGN-01"].get("evidenceState")
        == "zero-model-seeded-control-calibration-no-live-agent-or-domain-"
        "evidence"
        and scenarios["SE-VERIFY-SECURE-01"].get("evidenceState")
        == "zero-model-seeded-fault-calibration-no-live-agent-or-domain-"
        "evidence",
        "zero-model-only scenario boundary drifted",
    )
    release_scenario = scenarios["SE-RELEASE-CHANGE-01"]
    _require(
        release_scenario.get("task")
        and release_scenario.get("authorityBoundary")
        and release_scenario.get("dataBoundary")
        and release_scenario.get("acceptanceSignals")
        and release_scenario.get("evidenceNeeded")
        and release_scenario.get("falsifier")
        and release_scenario.get("forbiddenClaims"),
        "release scenario contract is incomplete",
    )
    projection = matrix.get("coverageProjection", {})
    _require(
        projection.get("evidenceCoverageStatus")
        == "open-no-live-domain-scenario-evidence"
        and matrix.get("decision", {}).get("liveDomainScenarioEvidenceClaimed")
        is False
        and matrix.get("decision", {}).get("residualCapabilityGapClaimed")
        is False,
        "scenario matrix evidence boundary drifted",
    )

    skill_entries = _items_by(skills.get("skills", []), "id")
    admission_entries = _items_by(admissions.get("admissions", []), "skill")
    release_files = _items_by(release.get("files", []), "path")
    for candidate_id, identity in RELEASE_CANDIDATES.items():
        skill = skill_entries.get(candidate_id)
        admission = admission_entries.get(candidate_id)
        release_file = release_files.get(identity["path"])
        _require(
            skill is not None
            and skill.get("status") == "approved"
            and skill.get("phase") == "ship"
            and skill.get("source") == "github:addyosmani/agent-skills",
            f"approved release candidate registry drifted: {candidate_id}",
        )
        _require(
            admission is not None
            and admission.get("thirdParty") is True
            and admission.get("disposition") == "approve"
            and admission.get("validated") is True,
            f"approved release candidate admission drifted: {candidate_id}",
        )
        _require(
            release_file is not None
            and release_file.get("sha256") == identity["sha256"],
            f"approved release candidate file identity drifted: {candidate_id}",
        )

    semantics = document.get("coverageSemantics", {})
    _require(
        semantics
        and all(value is True for value in semantics.values()),
        "audit coverage semantics drifted",
    )
    observed = {
        (item["scenarioId"], item["candidateId"]): item
        for item in document.get("behaviorallyObservedScenarioCells", [])
    }
    _require(
        set(observed) == set(CURRENT_OBSERVED),
        "audit observed candidate cell set drifted",
    )
    for key, item in observed.items():
        _require(
            item.get("validRepetitions") == 3
            and item.get("classification") == CURRENT_OBSERVED[key]
            and item.get("currentBehavioralEvidence") is True
            and item.get("independentLoaderEventProved") is False
            and item.get("candidateInstructionsReachedModelProved") is False
            and item.get("candidateCausationProved") is False,
            f"audit observed cell was promoted: {key}",
        )
    historical = {
        (item["scenarioId"], item["candidateId"]): item
        for item in document.get("historicalBehaviorOnly", [])
    }
    _require(
        set(historical) == HISTORICAL_OBSERVED
        and all(
            item.get("currentBehavioralEvidence") is False
            for item in historical.values()
        ),
        "audit historical behavior boundary drifted",
    )

    source_only = document.get("sourceExposureOrProtocolOnly", {})
    _require(
        set(source_only.get("historicalStaticCcCohortWithoutLiveBehavior", []))
        == {"grill-me", "review"},
        "audit static-only CC cohort drifted",
    )
    runtime = source_only.get(
        "currentRuntimePackageMetadataWithoutBehavioralBaseline", {}
    )
    _require(
        runtime.get("candidate") == "superpowers.6.2.0"
        and runtime.get("executionAdmissionSatisfied") is False
        and runtime.get("loaderInvocationObserved") is False
        and runtime.get("behavioralBaselineProved") is False,
        "audit current runtime package was promoted",
    )
    aggregate = source_only.get("aggregateCcInventoryOnly", {})
    _require(
        aggregate.get("databaseRows") == 251
        and aggregate.get("distinctNames") == 233
        and aggregate.get("physicalBodies") == 75
        and aggregate.get("resolvableConsumerBodies") == 75
        and aggregate.get("unresolvedClaudeLinks") == 176
        and aggregate.get("loadedOrInvokedCount") is None
        and aggregate.get("perSkillScenarioCoverageDerivableFromCounts")
        is False,
        "audit aggregate CC inventory was promoted",
    )
    candidate_metadata = _items_by(
        source_only.get("approvedReleaseScenarioCandidateMetadata", []),
        "candidateId",
    )
    _require(
        set(candidate_metadata) == set(RELEASE_CANDIDATES),
        "audit release candidate metadata set drifted",
    )
    for candidate_id, item in candidate_metadata.items():
        identity = RELEASE_CANDIDATES[candidate_id]
        _require(
            item.get("scenarioId") == "SE-RELEASE-CHANGE-01"
            and item.get("releasePath") == identity["path"]
            and item.get("releaseSha256") == identity["sha256"]
            and item.get("currentCcBodyIdentityProved") is False
            and item.get("taskScopedExposureProved") is False
            and item.get("behavioralValueProved") is False,
            f"audit release candidate metadata was promoted: {candidate_id}",
        )

    gaps = document.get("highPriorityCoverageGaps", {})
    _require(
        set(gaps.get("plannedOnlyNoAgentOrDomainEvidence", []))
        == PLANNED_ONLY
        and set(
            gaps.get(
                "zeroModelCalibrationOnlyNoLiveAgentOrDomainEvidence", []
            )
        )
        == ZERO_MODEL_ONLY
        and gaps.get("liveDomainScenarioEvidenceCount") == 0
        and gaps.get("crossHostBehavioralEvidenceProved") is False
        and gaps.get("affectedSubjectOrDomainExpertValidationProved") is False,
        "audit high-priority coverage gap set drifted",
    )
    decision = document.get("nextNamedScenarioDecision", {})
    _require(
        decision.get("scenarioId") == "SE-RELEASE-CHANGE-01"
        and decision.get("scenarioContractSufficientForOfflineProtocolDesign")
        is True
        and decision.get(
            "approvedCandidateMetadataSufficientForSourceAdmissionOverlapPreflight"
        )
        is True
        and all(
            decision.get(key) is False
            for key in (
                "currentCcPerCandidateAvailabilityProved",
                "candidateSpecificExposureProved",
                "candidateLoaderInvocationProved",
                "candidateBehaviorOrValueProved",
                "liveComparativeArmReady",
                "modelDispatchAuthorized",
                "ccMutationAuthorized",
                "portfolioMutationAuthorized",
            )
        ),
        "next named scenario decision boundary drifted",
    )
    execution = document.get("executionBoundary", {})
    _require(
        execution.get("repositoryEvidenceOnly") is True
        and execution.get("modelRequestCount") == 0
        and execution.get("candidateExecutionCount") == 0
        and all(
            execution.get(key) is False
            for key in (
                "externalDiscoveryPerformed",
                "installationPerformed",
                "ccSwitchReadOrMutationPerformed",
                "globalConfigurationChanged",
                "programMapChanged",
                "globalVerifierChanged",
            )
        ),
        "audit execution boundary drifted",
    )
    _require(
        document.get("claimBoundary")
        and all(value is False for value in document["claimBoundary"].values()),
        "audit claim boundary was promoted",
    )
    _require(
        document.get("documentation") == DOCUMENTATION_PATH,
        "audit documentation pointer drifted",
    )
    documentation = (root / DOCUMENTATION_PATH).read_text(encoding="utf-8")
    for phrase in (
        "The repository has behavioral observations",
        "not for the whole CC inventory",
        "Source, exposure, or protocol-only evidence",
        "High-priority uncovered domains",
        "SE-RELEASE-CHANGE-01",
        "offline protocol design only",
        "does not make a live comparative arm ready",
        "does not prove a residual self-authored capability gap",
    ):
        _require(
            phrase in documentation,
            f"audit documentation boundary missing: {phrase}",
        )


def main() -> int:
    validate_audit(_load(ROOT, AUDIT_PATH))
    print("other CC and external Skill scenario coverage audit: valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
