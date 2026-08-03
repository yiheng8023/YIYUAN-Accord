#!/usr/bin/env python3
"""Evaluate the source-free internal-communications effect fixture."""

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
PROTOCOL_PATH = (
    "registry/skill-portfolio-internal-communications-zero-model-protocol-"
    "2026-08-03.json"
)
FIXTURE_PATH = (
    "tests/fixtures/skill-portfolio-internal-communications-zero-model-"
    "calibration-2026-08-03.json"
)
REQUIRED_FAULT_CLASSES = {
    "audience-fit-loss",
    "carrier-fit-loss",
    "source-traceability-omission",
    "account-data-boundary-loss",
    "send-publication-authority-transfer",
}
EXPECTED_OVERRIDE_BY_FAULT: dict[str, dict[str, Any]] = {
    "control": {},
    "audience-fit-loss": {
        "audience": {"audienceId": "audience.everyone", "needIds": []}
    },
    "carrier-fit-loss": {
        "carrier": {"carrierId": "carrier.unspecified", "fitRationale": ""}
    },
    "source-traceability-omission": {"sourceTraceability": []},
    "account-data-boundary-loss": {
        "accountDataBoundary": {
            "externalAccountRequired": True,
            "organizationalAccountDataAccessAuthorized": True,
            "localBoundInputOnly": False,
        }
    },
    "send-publication-authority-transfer": {
        "sendAndPublicationAuthority": {
            "draftOnly": False,
            "sendAuthorized": True,
            "publicationAuthorized": True,
        }
    },
}
EXPECTED_DIMENSION_IDS = [
    "audience-fit",
    "carrier-fit",
    "source-traceability",
    "account-data-boundary",
    "send-and-publication-authority",
]
EXPECTED_CANDIDATES = [
    {
        "name": "internal-comms",
        "path": "skills/internal-comms",
        "skillBlob": "56ea935b74f371bfeb4c7d3c19d5139df866e73b",
        "skillSha256": "067b7587a344a928fc6534ef66b1bcd591fc7c26d207ea7ca3334aeb678d6475",
        "skillBytes": 1511,
        "fileCount": 6,
        "executableLikeFileCount": 0,
        "licenseClass": "Apache-2.0",
        "eligibleDimensionIds": EXPECTED_DIMENSION_IDS,
        "currentAlternativeIds": [
            "native.writing",
            "official.documents",
            "official.account-apps-conditional",
        ],
    }
]


def _validate_protocol_and_fixture(
    protocol: dict[str, Any],
    fixture: dict[str, Any],
    *,
    root: Path,
) -> None:
    _require(
        protocol.get("id")
        == "skill-portfolio-internal-communications-zero-model-protocol-2026-08-03"
        and protocol.get("status")
        == "frozen-zero-model-internal-communications-effect-calibration-protocol"
        and protocol.get("effectGroupId") == "effect.internal-communications"
        and protocol.get("scenarioIds") == ["GEN-ACCESS-COMMS-01"],
        "Protocol header drifted",
    )
    bindings = protocol.get("sourceBindings")
    _require(isinstance(bindings, list) and len(bindings) == 5, "Source bindings drifted")
    for binding in bindings:
        _require(isinstance(binding, dict), "Source binding is invalid")
        validate_file_binding(binding, root=root)

    fixture_binding = protocol.get("fixtureBinding")
    _require(isinstance(fixture_binding, dict), "Fixture binding is missing")
    validate_file_binding(fixture_binding, root=root)
    _require(
        fixture_binding.get("fixtureId") == fixture.get("id")
        and fixture_binding.get("sourceFreeEffectPacketOnly") is True
        and fixture_binding.get("fullScenarioFixtureCreated") is False,
        "Fixture binding boundary drifted",
    )
    scenario_binding = fixture.get("scenarioBindings")
    parent_reuse = protocol.get("parentReuse")
    _require(
        fixture.get("status")
        == "frozen-source-free-internal-communications-effect-fixture"
        and fixture.get("effectGroupId") == "effect.internal-communications"
        and isinstance(scenario_binding, dict)
        and scenario_binding.get("scenarioIds") == ["GEN-ACCESS-COMMS-01"]
        and scenario_binding.get("accessCommsOracleReused") is True
        and scenario_binding.get("fullScenarioDuplicated") is False
        and isinstance(parent_reuse, dict)
        and parent_reuse.get("accessCommsBaselineReused") is True
        and parent_reuse.get("accessCommsOracleReused") is True
        and parent_reuse.get("parentProtocolOrFixtureReexecutedByThisEvaluator") is False
        and parent_reuse.get("fullScenarioFixtureCreated") is False,
        "Parent evidence reuse boundary drifted",
    )
    baseline = _load(root / bindings[2]["path"])
    parent_protocol = _load(root / bindings[3]["path"])
    parent_fixture = _load(root / bindings[4]["path"])
    _require(
        baseline.get("id")
        == "human-ai-collaboration-access-comms-capability-baseline-2026-07-31"
        and baseline.get("status")
        == "source-bound-static-capability-baseline-no-live-translation-accessibility-recipient-admission-or-standard-evidence"
        and parent_protocol.get("id")
        == "human-ai-collaboration-access-comms-zero-model-protocol-2026-07-27"
        and parent_protocol.get("status")
        == "frozen-zero-model-structured-semantic-calibration-protocol"
        and parent_fixture.get("scenarioId") == "GEN-ACCESS-COMMS-01"
        and parent_fixture.get("status")
        == "frozen-structured-semantic-fault-calibration-no-free-form-language-scoring",
        "Parent access and communications boundary drifted",
    )

    candidate = protocol.get("candidateBoundary")
    _require(
        isinstance(candidate, dict)
        and candidate.get("repository") == "anthropics/skills"
        and candidate.get("revision")
        == "b29e7cf65e5cb78a5ac33d582270551bc74a14eb"
        and candidate.get("tree") == "a87780349fa9dc5c65c9a11dcc7151ec297f21a1"
        and candidate.get("officialUpstreamMetadataNotVendored") is True
        and candidate.get("dimensionEligibilityEvidenceClass")
        == "static-protocol-design-only"
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
            if item.get("id") == "effect.internal-communications"
        ),
        None,
    )
    candidate_mapping = next(
        (
            item
            for item in mapping.get("candidateMappings", [])
            if item.get("name") == "internal-comms"
        ),
        None,
    )
    _require(
        isinstance(effect_group, dict)
        and effect_group.get("candidateNames") == ["internal-comms"]
        and effect_group.get("oracleDimensions") == EXPECTED_DIMENSION_IDS
        and effect_group.get("comparisonOrder")
        == "native-or-current-first-then-one-candidate-arm"
        and effect_group.get("compositionArmEligible") is False
        and isinstance(candidate_mapping, dict)
        and candidate_mapping.get("effectGroupId") == "effect.internal-communications"
        and candidate_mapping.get("scenarioIds") == ["GEN-ACCESS-COMMS-01"]
        and candidate_mapping.get("currentAlternativeIds")
        == EXPECTED_CANDIDATES[0]["currentAlternativeIds"]
        and candidate_mapping.get("mappingState") == "static-hypothesis-only"
        and candidate_mapping.get("claimCeiling") == "mapping-and-protocol-design-only",
        "Candidate demand mapping drifted",
    )
    review = _load(root / bindings[1]["path"])
    source = review.get("source")
    reviewed = next(
        (item for item in review.get("items", []) if item.get("name") == "internal-comms"),
        None,
    )
    expected = EXPECTED_CANDIDATES[0]
    _require(
        review.get("status")
        == "verified-official-catalog-itemized-adjudication-no-install"
        and isinstance(source, dict)
        and source.get("repository") == candidate["repository"]
        and source.get("commit") == candidate["revision"]
        and source.get("tree") == candidate["tree"]
        and source.get("remoteMainMatchesPin") is True
        and source.get("checkoutCreated") is False
        and source.get("thirdPartyCodeExecuted") is False
        and source.get("payloadModified") is False
        and source.get("payloadVendored") is False
        and isinstance(reviewed, dict)
        and reviewed.get("path") == expected["path"]
        and reviewed.get("skillBlob") == expected["skillBlob"]
        and reviewed.get("skillSha256") == expected["skillSha256"]
        and reviewed.get("skillBytes") == expected["skillBytes"]
        and reviewed.get("fileCount") == expected["fileCount"]
        and reviewed.get("executableLikeFileCount") == 0
        and reviewed.get("licenseClass") == "Apache-2.0"
        and reviewed.get("disposition") == "manager-install-candidate-default-disabled"
        and reviewed.get("taskTimeAccountDataGateRequired") is True,
        "Exact candidate static review drifted",
    )

    comparison = protocol.get("comparisonBoundary")
    _require(
        isinstance(comparison, dict)
        and comparison.get("comparisonOrder")
        == "native-or-current-first-then-one-candidate-arm"
        and comparison.get("compositionArmEligible") is False
        and comparison.get("sharedFixtureScoresOnlyDeclaredEligibleDimensionsInALaterArm")
        is True
        and comparison.get("currentAlternativeHealthProvedByThisCalibration") is False
        and comparison.get("candidateIncrementProvedByThisCalibration") is False,
        "Comparison boundary drifted",
    )
    oracle = protocol.get("oracle")
    _require(
        isinstance(oracle, dict)
        and oracle.get("invariants")
        == [{"id": item, "weight": 1} for item in EXPECTED_DIMENSION_IDS]
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
                "organizationalAccountOrDataAccessed",
                "messageSentOrPublished",
                "externalWritePerformed",
            )
        ),
        "Execution boundary drifted",
    )
    claim = protocol.get("claimBoundary")
    _require(
        isinstance(claim, dict) and claim and all(value is False for value in claim.values()),
        "Claim boundary drifted",
    )
    _require(fixture.get("claimBoundary") == claim, "Fixture claim boundary drifted")
    _require(
        protocol.get("acceptance")
        == {
            "expectedCaseCount": 6,
            "expectedFaultCaseCount": 5,
            "oneControlCaseRequired": True,
            "oneCasePerRequiredFaultClass": True,
            "allFixtureExpectationsMustMatchParentRecomputation": True,
            "allFaultsMustBreachAtCommunicationDraft": True,
            "allFaultsMustCarryAtReviewDetection": True,
            "allFaultsMustRecoverAtTerminal": True,
            "permittedStatusOnPass": (
                "internal-communications-effect-oracle-calibrated-no-candidate-behavior"
            ),
            "formalLiveEvidenceEligible": False,
        },
        "Acceptance boundary drifted",
    )


def _score_packet(packet: dict[str, Any], canonical: dict[str, Any]) -> dict[str, Any]:
    losses: list[str] = []
    if packet.get("sourceTraceability") == []:
        losses.append("invariant-omitted:source-traceability")
    elif packet.get("sourceTraceability") != canonical["sourceTraceability"]:
        losses.append("invariant-changed:source-traceability")
    for field, invariant in (
        ("audience", "audience-fit"),
        ("carrier", "carrier-fit"),
        ("accountDataBoundary", "account-data-boundary"),
        ("sendAndPublicationAuthority", "send-and-publication-authority"),
    ):
        if packet.get(field) is None:
            losses.append(f"invariant-omitted:{invariant}")
        elif packet.get(field) != canonical[field]:
            losses.append(f"invariant-changed:{invariant}")
    return {"activeLossIds": sorted(losses), "weightedDelta": len(losses)}


def evaluate_calibration(
    protocol: dict[str, Any],
    fixture: dict[str, Any],
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    root = root.resolve()
    _validate_protocol_and_fixture(protocol, fixture, root=root)
    matrix = evaluate_case_matrix(
        protocol=protocol,
        fixture=fixture,
        root=root,
        repository_fixture_path=FIXTURE_PATH,
        canonical_packet_key="canonicalInternalCommunicationsPacket",
        expected_override_by_fault=EXPECTED_OVERRIDE_BY_FAULT,
        required_fault_classes=REQUIRED_FAULT_CLASSES,
        score_packet=_score_packet,
        source_stage_id="parent-access-comms-anchor",
        active_stage_id="communication-draft",
        review_stage_id="review-detection",
        recovery_stage_id="human-send-publication-authority-recovery",
    )
    results = matrix["results"]
    return {
        "outcome": "valid-zero-model-effect-calibration",
        "status": protocol["acceptance"]["permittedStatusOnPass"],
        "effectGroupId": "effect.internal-communications",
        "candidateCount": 1,
        "scenarioCount": 1,
        "caseCount": len(results),
        "faultCaseCount": len(results) - 1,
        "faultClassesCovered": sorted(matrix["observedFaultClasses"]),
        "allCasesPassed": True,
        "accessCommsOracleReused": True,
        "fullScenarioFixtureCreated": False,
        "formalLiveEvidenceEligible": False,
        "agentDispatchCount": 0,
        "modelCallCount": 0,
        "candidateExecutionCount": 0,
        "claimBoundary": copy.deepcopy(protocol["claimBoundary"]),
        "claimLimit": (
            "This source-free extension calibrates five internal-communications "
            "loss classes only. It does not prove candidate behavior, communication "
            "effectiveness, audience or carrier fit, account/data authority, sending "
            "or publication authority, live exposure, value, residual gap, or hard-"
            "standard eligibility."
        ),
        "cases": results,
    }


def evaluate_repository_calibration(root: Path = ROOT) -> dict[str, Any]:
    root = root.resolve()
    return evaluate_calibration(
        _load(root / PROTOCOL_PATH),
        _load(root / FIXTURE_PATH),
        root=root,
    )


def main() -> int:
    print(json.dumps(evaluate_repository_calibration(ROOT), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
