#!/usr/bin/env python3
"""Evaluate the domain-only Obsidian format-semantics effect fixture."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

try:
    from .evaluate_skill_portfolio_zero_model_effect_cases import (
        evaluate_case_matrix,
        load_json_object as _load,
        require as _require,
        validate_file_binding,
    )
except ImportError:  # pragma: no cover - direct script execution
    from evaluate_skill_portfolio_zero_model_effect_cases import (
        evaluate_case_matrix,
        load_json_object as _load,
        require as _require,
        validate_file_binding,
    )


ROOT = Path(__file__).resolve().parent.parent
PROTOCOL_PATH = "registry/skill-portfolio-obsidian-format-semantics-zero-model-protocol-2026-08-03.json"
FIXTURE_PATH = "tests/fixtures/skill-portfolio-obsidian-format-semantics-zero-model-calibration-2026-08-03.json"
REQUIRED_FAULT_CLASSES = {
    "format-validity-loss",
    "referential-integrity-loss",
    "source-preservation-loss",
    "bounded-file-write-loss",
    "vault-organization-assumption",
}
EXPECTED_OVERRIDE_BY_FAULT: dict[str, dict[str, Any]] = {
    "control": {},
    "format-validity-loss": {
        "formatValidity": {"formatId": "unknown", "schemaValidated": False}
    },
    "referential-integrity-loss": {
        "referentialIntegrity": {
            "declaredReferenceIds": ["reference.note-a"],
            "resolvedReferenceIds": [],
            "brokenReferenceIds": ["reference.note-a"],
        }
    },
    "source-preservation-loss": {
        "sourcePreservation": {"sourceIds": [], "preserved": False}
    },
    "bounded-file-write-loss": {
        "boundedFileWrite": {
            "targetPath": "../unbound-output.md",
            "withinAuthorizedRoot": False,
            "writeAuthorized": True,
        }
    },
    "vault-organization-assumption": {
        "vaultOrganizationAssumption": {
            "organizationModelAssumed": True,
            "userVaultStructureRequired": True,
        }
    },
}
EXPECTED_DIMENSION_IDS = [
    "format-validity",
    "referential-integrity",
    "source-preservation",
    "bounded-file-write",
    "no-vault-organization-assumption",
]
EXPECTED_CANDIDATES = [
    {
        "name": "json-canvas",
        "path": "skills/json-canvas/SKILL.md",
        "sha256": "788535277bc5f460bec97d467615a2ce97e2957dad1b1fc961e645f64c827128",
        "dependencyFiles": [
            {
                "path": "skills/json-canvas/references/EXAMPLES.md",
                "sha256": "c6fce2e043f98d5bf3c52662a0261aa3e12d5eabbb37585e3c4c52a968b109a1",
            }
        ],
        "eligibleDimensionIds": EXPECTED_DIMENSION_IDS[:4],
        "currentAlternativeIds": [
            "native.json-editing",
            "official.figma-diagram-generation",
        ],
    },
    {
        "name": "obsidian-bases",
        "path": "skills/obsidian-bases/SKILL.md",
        "sha256": "83bc04a2c306a61c216c0cfecbb4d032cc763896623d229cd2a6dab811083032",
        "dependencyFiles": [
            {
                "path": "skills/obsidian-bases/references/FUNCTIONS_REFERENCE.md",
                "sha256": "0d0cd128bc5070ef1aba2baef41bd55b31b3f56961975934d7a5172396ca0006",
            }
        ],
        "eligibleDimensionIds": EXPECTED_DIMENSION_IDS,
        "currentAlternativeIds": ["native.yaml-editing", "managed.obsidian-vault"],
    },
    {
        "name": "obsidian-markdown",
        "path": "skills/obsidian-markdown/SKILL.md",
        "sha256": "ef409b7eeda59e2e0c5cdead334dcc997dc9459d689859b3a610ffa9af5cabc5",
        "dependencyFiles": [
            {
                "path": "skills/obsidian-markdown/references/CALLOUTS.md",
                "sha256": "3b8f63c90f692ac40e6989fda2ab2fed3bb482ff515176b40d18dac8402e516b",
            },
            {
                "path": "skills/obsidian-markdown/references/EMBEDS.md",
                "sha256": "d9f9f485ded6a32b4d76e59eaddc442bd09faf851d755f052759fc9ab1a25b2c",
            },
            {
                "path": "skills/obsidian-markdown/references/PROPERTIES.md",
                "sha256": "28da58935ca3296f30b7e9aa25f2a695963dc0a3e4062638428d3bcb2094562a",
            },
        ],
        "eligibleDimensionIds": EXPECTED_DIMENSION_IDS,
        "currentAlternativeIds": [
            "native.markdown-editing",
            "managed.obsidian-vault",
        ],
    },
]


def _validate_protocol_and_fixture(
    protocol: dict[str, Any], fixture: dict[str, Any], *, root: Path
) -> None:
    _require(
        protocol.get("id")
        == "skill-portfolio-obsidian-format-semantics-zero-model-protocol-2026-08-03"
        and protocol.get("status")
        == "frozen-zero-model-domain-only-obsidian-format-semantics-effect-calibration-protocol"
        and protocol.get("effectGroupId") == "effect.obsidian-format-semantics"
        and protocol.get("scenarioIds") == [],
        "Protocol header drifted",
    )
    bindings = protocol.get("sourceBindings")
    _require(isinstance(bindings, list) and len(bindings) == 3, "Source bindings drifted")
    for binding in bindings:
        _require(isinstance(binding, dict), "Source binding is invalid")
        validate_file_binding(binding, root=root)
    fixture_binding = protocol.get("fixtureBinding")
    _require(isinstance(fixture_binding, dict), "Fixture binding is missing")
    validate_file_binding(fixture_binding, root=root)
    _require(
        fixture_binding.get("fixtureId") == fixture.get("id")
        and fixture_binding.get("sourceFreeEffectPacketOnly") is True
        and fixture_binding.get("domainOnlyFixture") is True
        and fixture_binding.get("fullScenarioFixtureCreated") is False,
        "Fixture binding boundary drifted",
    )
    scenario = fixture.get("scenarioBindings")
    domain = protocol.get("domainOnlyBoundary")
    _require(
        fixture.get("status")
        == "frozen-source-free-domain-only-obsidian-format-semantics-fixture"
        and fixture.get("effectGroupId") == "effect.obsidian-format-semantics"
        and isinstance(scenario, dict)
        and scenario.get("scenarioIds") == []
        and scenario.get("domainOnlyFixture") is True
        and scenario.get("absenceOfScenarioMappingPromotedToResidualGap") is False
        and isinstance(domain, dict)
        and domain.get("scenarioMappingAbsent") is True
        and domain.get("absenceOfScenarioMappingPromotedToResidualGap") is False
        and domain.get("formatFixturePromotedToScenarioCoverage") is False
        and domain.get("fullScenarioFixtureCreated") is False,
        "Domain-only boundary drifted",
    )

    manager = protocol.get("managerRegistrationBoundary")
    _require(
        manager
        == {
            "managerRepositoryRegistered": True,
            "managerDiscoveryNamesProved": True,
            "managerDiscoveryPayloadBytesProved": False,
            "candidateInstalled": False,
            "hostExposed": False,
            "invocationProved": False,
            "instructionDeliveryProved": False,
            "behaviorProved": False,
            "valueProved": False,
        },
        "Manager registration boundary drifted",
    )
    registration = _load(root / bindings[2]["path"])
    registration_claim = registration.get("claimBoundary")
    _require(
        registration.get("status") == "verified-manager-repository-registration-no-install"
        and isinstance(registration_claim, dict)
        and registration_claim.get("managerRepositoryRegistered") is True
        and registration_claim.get("managerDiscoveryNamesProved") is True
        and registration_claim.get("candidateInstalled") is False
        and registration_claim.get("hostExposed") is False
        and registration_claim.get("behaviorProved") is False
        and registration_claim.get("valueProved") is False,
        "Manager registration evidence drifted",
    )

    candidate = protocol.get("candidateBoundary")
    _require(
        isinstance(candidate, dict)
        and candidate.get("repository") == "kepano/obsidian-skills"
        and candidate.get("revision") == "a1dc48e68138490d522c04cbf5822214c6eb1202"
        and candidate.get("tree") == "49d7c3b7f6aa4d266631c886284415d111070941"
        and candidate.get("dimensionEligibilityEvidenceClass") == "static-protocol-design-only"
        and candidate.get("candidates") == EXPECTED_CANDIDATES
        and all(
            candidate.get(key) is False
            for key in (
                "allCandidatesInstalled",
                "allCandidatesProjected",
                "allCandidatesEnabled",
                "allCandidatesExposed",
                "allCandidatesExecuted",
                "candidateBehaviorOrValueProved",
            )
        ),
        "Candidate identity, eligibility, or lifecycle boundary drifted",
    )
    mapping = _load(root / bindings[0]["path"])
    effect_group = next(
        (
            item
            for item in mapping.get("effectGroups", [])
            if item.get("id") == "effect.obsidian-format-semantics"
        ),
        None,
    )
    mappings = [
        item
        for item in mapping.get("candidateMappings", [])
        if item.get("effectGroupId") == "effect.obsidian-format-semantics"
    ]
    _require(
        isinstance(effect_group, dict)
        and effect_group.get("candidateNames") == [item["name"] for item in EXPECTED_CANDIDATES]
        and effect_group.get("oracleDimensions") == EXPECTED_DIMENSION_IDS
        and effect_group.get("compositionArmEligible") is False
        and [item.get("name") for item in mappings]
        == [item["name"] for item in EXPECTED_CANDIDATES]
        and all(item.get("scenarioIds") == [] for item in mappings)
        and all(item.get("mappingState") == "static-hypothesis-only" for item in mappings)
        and all(item.get("claimCeiling") == "mapping-and-protocol-design-only" for item in mappings),
        "Candidate demand mapping drifted",
    )
    review = _load(root / bindings[1]["path"])
    source = review.get("source")
    reviewed_by_name = {item.get("name"): item for item in review.get("skills", [])}
    _require(
        review.get("status") == "reviewed-source-cohort-manager-registration-eligible-install-held"
        and isinstance(source, dict)
        and source.get("repository") == candidate["repository"]
        and source.get("commit") == candidate["revision"]
        and source.get("tree") == candidate["tree"]
        and source.get("license") == "MIT"
        and source.get("worktreeClean") is True
        and source.get("payloadModified") is False
        and source.get("sourceFilesVendoredIntoHarness") is False
        and source.get("bundledExecutableFileCount") == 0,
        "Exact candidate source review drifted",
    )
    for expected in EXPECTED_CANDIDATES:
        reviewed = reviewed_by_name.get(expected["name"])
        _require(
            isinstance(reviewed, dict)
            and reviewed.get("path") == expected["path"]
            and reviewed.get("sha256") == expected["sha256"]
            and reviewed.get("dependencyFiles") == expected["dependencyFiles"]
            and reviewed.get("executableFileCount") == 0
            and reviewed.get("runtimeDependency") is None
            and reviewed.get("runtimeDependencyPresent") is True
            and reviewed.get("disposition") == "manager-install-candidate-default-disabled",
            "Exact candidate static review drifted",
        )
    comparison = protocol.get("comparisonBoundary")
    _require(
        isinstance(comparison, dict)
        and comparison.get("comparisonOrder") == "native-or-current-first-then-one-candidate-arm"
        and comparison.get("compositionArmEligible") is False
        and comparison.get("sharedFixtureScoresOnlyDeclaredEligibleDimensionsInALaterArm") is True
        and comparison.get("currentAlternativeHealthProvedByThisCalibration") is False
        and comparison.get("candidateIncrementProvedByThisCalibration") is False,
        "Comparison boundary drifted",
    )
    oracle = protocol.get("oracle")
    _require(
        isinstance(oracle, dict)
        and oracle.get("invariants") == [{"id": item, "weight": 1} for item in EXPECTED_DIMENSION_IDS]
        and oracle.get("unauthorizedAssumptions") == []
        and oracle.get("faultBudgetMaximum") == 0
        and oracle.get("parentRecomputed") is True
        and oracle.get("terminalRecoveryDoesNotEraseHistoricalUniqueLoss") is True,
        "Oracle boundary drifted",
    )
    execution = protocol.get("executionBoundary")
    _require(
        isinstance(execution, dict)
        and execution.get("repositoryEvidenceOnly") is True
        and execution.get("agentDispatchCount") == 0
        and execution.get("modelCallCount") == 0
        and execution.get("candidateExecutionCount") == 0
        and all(
            execution.get(key) is False
            for key in (
                "externalAccessUsedByCalibration",
                "candidatePayloadReadByCalibration",
                "sourceProjectionOrInstallationPerformed",
                "ccSwitchPluginMcpHookOrRuntimeMutationPerformed",
                "vaultOrNoteDataAccessed",
                "fileOrVaultWritePerformed",
            )
        ),
        "Execution boundary drifted",
    )
    claim = protocol.get("claimBoundary")
    _require(isinstance(claim, dict) and claim and all(value is False for value in claim.values()), "Claim boundary drifted")
    _require(fixture.get("claimBoundary") == claim, "Fixture claim boundary drifted")
    _require(
        protocol.get("acceptance")
        == {
            "expectedCaseCount": 6,
            "expectedFaultCaseCount": 5,
            "oneControlCaseRequired": True,
            "oneCasePerRequiredFaultClass": True,
            "allFixtureExpectationsMustMatchParentRecomputation": True,
            "allFaultsMustBreachAtFormatDraft": True,
            "allFaultsMustCarryAtReviewDetection": True,
            "allFaultsMustRecoverAtTerminal": True,
            "permittedStatusOnPass": "obsidian-format-semantics-effect-oracle-calibrated-no-candidate-behavior",
            "formalLiveEvidenceEligible": False,
        },
        "Acceptance boundary drifted",
    )


def _score_packet(packet: dict[str, Any], canonical: dict[str, Any]) -> dict[str, Any]:
    losses: list[str] = []
    for field, invariant in (
        ("formatValidity", "format-validity"),
        ("referentialIntegrity", "referential-integrity"),
        ("sourcePreservation", "source-preservation"),
        ("boundedFileWrite", "bounded-file-write"),
        ("vaultOrganizationAssumption", "no-vault-organization-assumption"),
    ):
        if packet.get(field) is None:
            losses.append(f"invariant-omitted:{invariant}")
        elif packet.get(field) != canonical[field]:
            losses.append(f"invariant-changed:{invariant}")
    return {"activeLossIds": sorted(losses), "weightedDelta": len(losses)}


def evaluate_calibration(protocol: dict[str, Any], fixture: dict[str, Any], *, root: Path = ROOT) -> dict[str, Any]:
    root = root.resolve()
    _validate_protocol_and_fixture(protocol, fixture, root=root)
    matrix = evaluate_case_matrix(
        protocol=protocol,
        fixture=fixture,
        root=root,
        repository_fixture_path=FIXTURE_PATH,
        canonical_packet_key="canonicalObsidianFormatPacket",
        expected_override_by_fault=EXPECTED_OVERRIDE_BY_FAULT,
        required_fault_classes=REQUIRED_FAULT_CLASSES,
        score_packet=_score_packet,
        source_stage_id="domain-only-format-anchor",
        active_stage_id="format-draft",
        review_stage_id="review-detection",
        recovery_stage_id="human-vault-write-authority-recovery",
    )
    results = matrix["results"]
    return {
        "outcome": "valid-zero-model-effect-calibration",
        "status": protocol["acceptance"]["permittedStatusOnPass"],
        "effectGroupId": "effect.obsidian-format-semantics",
        "candidateCount": 3,
        "scenarioCount": 0,
        "caseCount": len(results),
        "faultCaseCount": len(results) - 1,
        "faultClassesCovered": sorted(matrix["observedFaultClasses"]),
        "allCasesPassed": True,
        "domainOnlyFixture": True,
        "managerRepositoryRegistrationReused": True,
        "candidateInstallationPromoted": False,
        "formalLiveEvidenceEligible": False,
        "agentDispatchCount": 0,
        "modelCallCount": 0,
        "candidateExecutionCount": 0,
        "claimBoundary": copy.deepcopy(protocol["claimBoundary"]),
        "claimLimit": "This domain-only source-free extension calibrates five format-semantics loss classes only. It does not prove scenario coverage, residual gap, candidate installation, exposure, behavior, format correctness beyond the fixture, vault access or write authority, an organization model, value, or hard-standard eligibility.",
        "cases": results,
    }


def evaluate_repository_calibration(root: Path = ROOT) -> dict[str, Any]:
    root = root.resolve()
    return evaluate_calibration(_load(root / PROTOCOL_PATH), _load(root / FIXTURE_PATH), root=root)


def main() -> int:
    print(json.dumps(evaluate_repository_calibration(ROOT), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
