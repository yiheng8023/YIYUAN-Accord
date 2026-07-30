#!/usr/bin/env python3
"""Evaluate the GEN-ACCESS-COMMS-01 structured zero-model calibration.

The evaluator is intentionally domain-specific.  It converts frozen structured
semantic states into parent-scored active-loss sets, then delegates cumulative
set accounting to the existing process-fidelity implementation.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

try:
    from .evaluate_process_fidelity_cumulative_loss_accounting import (
        build_cumulative_loss_ledger,
    )
    from .run_process_fidelity_chained_transform_trial import (
        canonical_sha256,
        file_sha256,
    )
except ImportError:  # pragma: no cover - direct script execution
    from evaluate_process_fidelity_cumulative_loss_accounting import (
        build_cumulative_loss_ledger,
    )
    from run_process_fidelity_chained_transform_trial import (
        canonical_sha256,
        file_sha256,
    )


ROOT = Path(__file__).resolve().parent.parent
PROTOCOL_PATH = (
    "registry/human-ai-collaboration-access-comms-zero-model-protocol-"
    "2026-07-27.json"
)
FIXTURE_PATH = (
    "tests/fixtures/human-ai-collaboration-access-comms-zero-model-"
    "calibration-2026-07-27.json"
)
REQUIRED_FAULT_CLASSES = {
    "accessibility-structure-break",
    "actor-swap",
    "deadline-unit-drift",
    "invented-commitment",
    "negation-flip",
    "obligation-weakening",
    "terminology-drift",
    "uncertainty-deletion",
}
EXPECTED_FAULT_SPECIFICATIONS = {
    "obligation-weakening": (["obligation"], [], []),
    "actor-swap": (["actor"], [], []),
    "negation-flip": (["negation"], [], []),
    "deadline-unit-drift": (["deadline", "unit"], [], []),
    "uncertainty-deletion": ([], ["uncertainty"], []),
    "invented-commitment": ([], [], ["invented-commitment"]),
    "terminology-drift": (["terminology"], [], []),
    "accessibility-structure-break": (
        ["accessibility-structure"],
        [],
        [],
    ),
}
EXPECTED_INVARIANT_WEIGHTS = {
    "actor": 5,
    "obligation": 5,
    "negation": 5,
    "deadline": 4,
    "unit": 4,
    "uncertainty": 3,
    "terminology": 2,
    "accessibility-structure": 2,
}
EXPECTED_ASSUMPTION_WEIGHTS = {"invented-commitment": 5}
EXPECTED_STAGE_POLICY = {
    "stageIdsInOrder": [
        "source-anchor",
        "adapted-message",
        "review-detection",
        "human-review-recovery",
    ],
    "adaptedMessageIntroducesTheRegisteredFault": True,
    "reviewStageCarriesTheFaultAndMustDetectTheExactActiveLossSet": True,
    "terminalStageRestoresTheExactSourceAnchor": True,
    "simulatedReviewIsHumanEvidence": False,
    "terminalRecoveryCanEraseHistoricalUniqueLoss": False,
}
EXPECTED_ACCEPTANCE = {
    "expectedCaseCount": 9,
    "expectedFaultCaseCount": 8,
    "oneControlCaseRequired": True,
    "oneCasePerRequiredFaultClass": True,
    "allFixtureExpectationsMustMatchParentRecomputation": True,
    "allFaultsMustBreachAtAdaptedMessage": True,
    "allFaultsMustCarryAtReviewDetection": True,
    "allFaultsMustRecoverAtTerminal": True,
    "permittedStatusOnPass": (
        "zero-model-calibrated-no-live-agent-or-domain"
    ),
    "formalLiveEvidenceEligible": False,
}
EXPECTED_PROTOCOL_HEADER = {
    "schema": 1,
    "id": (
        "human-ai-collaboration-access-comms-zero-model-protocol-"
        "2026-07-27"
    ),
    "date": "2026-07-27",
    "status": "frozen-zero-model-structured-semantic-calibration-protocol",
}
EXPECTED_FIXTURE_HEADER = {
    "schema": 1,
    "id": (
        "human-ai-collaboration-access-comms-zero-model-calibration-"
        "2026-07-27"
    ),
    "date": "2026-07-27",
    "scenarioId": "GEN-ACCESS-COMMS-01",
    "status": (
        "frozen-structured-semantic-fault-calibration-"
        "no-free-form-language-scoring"
    ),
}
EXPECTED_LOCAL_CALIBRATION_NARROWING = {
    "authorityBoundary": (
        "Deterministic local calibration only; no official release, "
        "legally consequential wording, or human-review authority is "
        "exercised."
    ),
    "dataBoundary": (
        "Repository-controlled synthetic structured semantic fixture only; "
        "no account, private data, network, or live recipient input."
    ),
    "falsifier": (
        "A seeded structured mutation that weakens an obligation, swaps the "
        "accountable actor, flips a negation, drifts a deadline or unit, "
        "deletes uncertainty, invents a commitment, changes bound "
        "terminology, or breaks the frozen accessibility structure must not "
        "pass the calibrated gate."
    ),
    "sourceAcceptanceSignalsNotProved": [
        "accessibility conformance",
        "comprehension",
        "recipient harm or confusion",
    ],
    "sourceEvidenceStillRequired": [
        "accessibility checks",
        "bilingual or domain review",
        "human-only control",
        "recipient comprehension sample",
    ],
    "sourceEvidenceStateRemains": "planned-no-live-domain-evidence",
}
EXPECTED_FAILURE_FALLBACK = [
    (
        "Any source, fixture, or reused accounting-module digest drift "
        "invalidates the calibration."
    ),
    "Any missing, duplicated, or unknown fault class fails closed.",
    (
        "Any unknown invariant, omission, change, assumption, stage, or "
        "expected loss set fails closed."
    ),
    (
        "A recovered terminal state cannot remove the historical cumulative "
        "unique loss."
    ),
    (
        "Failure retains the scenario at planned-no-live-domain-evidence and "
        "authorizes no candidate comparison or implementation."
    ),
]
EXPECTED_PROTOCOL_CLAIM_BOUNDARY = {
    "freeFormLanguageCorrectnessProved": False,
    "bilingualDomainCorrectnessProved": False,
    "recipientComprehensionProved": False,
    "accessibilityConformanceProved": False,
    "humanReviewEffectProved": False,
    "liveAgentOrDomainEvidenceProved": False,
    "candidateSkillValueProved": False,
    "crossHostBehaviorProved": False,
    "wholeHumanAiCollaborationCovered": False,
    "residualSelfAuthoredGapProved": False,
}
EXPECTED_FIXTURE_CLAIM_BOUNDARY = {
    "freeFormLanguageCorrectnessProved": False,
    "bilingualDomainCorrectnessProved": False,
    "recipientComprehensionProved": False,
    "accessibilityConformanceProved": False,
    "liveAgentOrDomainEvidenceProved": False,
    "candidateSkillValueProved": False,
    "crossHostBehaviorProved": False,
}
EXPECTED_EXECUTION_BOUNDARY = {
    "repositoryEvidenceOnly": True,
    "agentDispatchCount": 0,
    "modelCallCount": 0,
    "externalAccessUsed": False,
    "networkAccessUsed": False,
    "accountOrPrivateDataAccessed": False,
    "candidateSkillMaterializedOrExecuted": False,
    "ccSwitchReadOrMutationPerformed": False,
    "globalConfigurationReadOrChanged": False,
    "gitOperationPerformed": False,
    "releaseOrPublicationActionPerformed": False,
}
EXPECTED_CASE_POLICY = {
    "stageIdsInOrder": [
        "source-anchor",
        "adapted-message",
        "review-detection",
        "human-review-recovery",
    ],
    "allFaultCasesRecoverToExactSourceAnchor": True,
    "reviewDetectionMustEqualParentRecomputedActiveLossIds": True,
    "terminalRecoveryDoesNotEraseCumulativeUniqueLoss": True,
    "faultBudgetMaximum": 0,
}
EXPECTED_DOCUMENTATION = (
    "docs/strategy/"
    "HUMAN-AI-COLLABORATION-ACCESS-COMMS-ZERO-MODEL-CALIBRATION-"
    "2026-07-27.md"
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _string_list(value: Any, *, label: str) -> list[str]:
    _require(
        isinstance(value, list)
        and all(isinstance(item, str) and item for item in value)
        and len(value) == len(set(value)),
        f"{label} must be a unique non-empty string list",
    )
    return sorted(value)


def _repository_file(root: Path, relative: Any, *, label: str) -> Path:
    _require(
        isinstance(relative, str) and bool(relative),
        f"{label} path is missing",
    )
    relative_path = Path(relative)
    _require(
        not relative_path.is_absolute()
        and ".." not in relative_path.parts,
        f"{label} path escapes the repository root",
    )
    lexical_path = root / relative_path
    current = root
    for part in relative_path.parts:
        current = current / part
        is_junction = bool(
            getattr(current, "is_junction", lambda: False)()
        )
        _require(
            not current.is_symlink() and not is_junction,
            f"{label} path must not traverse a link",
        )
    try:
        resolved = lexical_path.resolve(strict=True)
        resolved.relative_to(root)
    except (OSError, ValueError):
        raise RuntimeError(
            f"{label} path escapes the repository root or is missing"
        ) from None
    _require(resolved.is_file(), f"{label} path is not a file")
    return resolved


def _validate_bindings(
    protocol: dict[str, Any],
    fixture: dict[str, Any],
    *,
    root: Path,
) -> None:
    _require(
        {key: protocol.get(key) for key in EXPECTED_PROTOCOL_HEADER}
        == EXPECTED_PROTOCOL_HEADER,
        "Protocol header drifted",
    )
    _require(
        {key: fixture.get(key) for key in EXPECTED_FIXTURE_HEADER}
        == EXPECTED_FIXTURE_HEADER,
        "Fixture header drifted",
    )
    _require(
        fixture.get("scenarioId") == "GEN-ACCESS-COMMS-01"
        and protocol.get("scenarioBinding", {}).get("scenarioId")
        == "GEN-ACCESS-COMMS-01",
        "Scenario binding drifted",
    )
    fixture_binding = protocol.get("fixtureBinding")
    _require(isinstance(fixture_binding, dict), "Fixture binding is missing")
    _require(
        fixture_binding.get("path") == FIXTURE_PATH
        and fixture_binding.get("fixtureId") == fixture["id"]
        and fixture_binding.get("fileSha256", "").lower()
        == file_sha256(
            _repository_file(
                root,
                fixture_binding.get("path"),
                label="Fixture binding",
            )
        ).lower(),
        "Fixture binding drifted",
    )
    _require(
        fixture_binding.get("fixtureFrozen") is True
        and fixture_binding.get("structuredSemanticNormalFormOnly") is True
        and fixture_binding.get("freeFormLanguageParserIncluded") is False,
        "Fixture scope boundary drifted",
    )

    scenario_binding = protocol.get("scenarioBinding")
    _require(
        isinstance(scenario_binding, dict),
        "Scenario source binding is missing",
    )
    scenario_path = _repository_file(
        root,
        scenario_binding.get("sourcePath"),
        label="Scenario source binding",
    )
    _require(
        file_sha256(scenario_path).lower()
        == str(scenario_binding.get("sourceFileSha256", "")).lower(),
        "Scenario source binding drifted",
    )
    scenario_document = json.loads(scenario_path.read_text(encoding="utf-8"))
    source_scenarios = [
        item
        for item in scenario_document.get("scenarios", [])
        if isinstance(item, dict)
        and item.get("id") == "GEN-ACCESS-COMMS-01"
    ]
    _require(
        len(source_scenarios) == 1
        and scenario_binding.get("sourceScenarioContract")
        == source_scenarios[0],
        "Source scenario contract drifted",
    )
    _require(
        scenario_binding.get("localCalibrationNarrowing")
        == EXPECTED_LOCAL_CALIBRATION_NARROWING,
        "Local calibration narrowing drifted",
    )

    reuse = protocol.get("processFidelityReuse")
    _require(
        isinstance(reuse, dict)
        and reuse.get("reusedFunction")
        == "build_cumulative_loss_ledger"
        and reuse.get("newGenericSimulationFrameworkCreated") is False,
        "Process-fidelity reuse contract drifted",
    )
    module_path = _repository_file(
        root,
        reuse.get("modulePath"),
        label="Process-fidelity reuse binding",
    )
    _require(
        file_sha256(module_path).lower()
        == str(reuse.get("moduleFileSha256", "")).lower(),
        "Process-fidelity reuse binding drifted",
    )


def _validate_protocol_and_fixture_shape(
    protocol: dict[str, Any],
    fixture: dict[str, Any],
) -> tuple[list[str], dict[str, Any], dict[str, Any]]:
    protocol_faults = _string_list(
        protocol.get("requiredFaultClasses"),
        label="Protocol fault classes",
    )
    _require(
        set(protocol_faults) == REQUIRED_FAULT_CLASSES,
        "Protocol fault classes drifted",
    )
    fault_specifications = protocol.get("faultSpecifications")
    _require(
        isinstance(fault_specifications, dict)
        and set(fault_specifications) == REQUIRED_FAULT_CLASSES,
        "Fault specifications drifted",
    )
    for fault_class, specification in fault_specifications.items():
        _require(
            isinstance(specification, dict),
            f"Fault specification is invalid: {fault_class}",
        )
        changed = _string_list(
            specification.get("changedInvariantIds"),
            label=f"Changed invariants for {fault_class}",
        )
        omitted = _string_list(
            specification.get("omittedInvariantIds"),
            label=f"Omitted invariants for {fault_class}",
        )
        assumptions = _string_list(
            specification.get("assumptionIds"),
            label=f"Assumptions for {fault_class}",
        )
        _require(
            (changed, omitted, assumptions)
            == EXPECTED_FAULT_SPECIFICATIONS[fault_class],
            f"Fault specification drifted: {fault_class}",
        )
    cases = fixture.get("cases")
    _require(isinstance(cases, list), "Fixture cases are missing")
    acceptance = protocol.get("acceptance")
    _require(isinstance(acceptance, dict), "Acceptance contract is missing")
    _require(
        acceptance == EXPECTED_ACCEPTANCE,
        "Acceptance contract drifted",
    )
    _require(
        protocol.get("stagePolicy") == EXPECTED_STAGE_POLICY,
        "Stage policy drifted",
    )
    _require(
        protocol.get("failureFallback") == EXPECTED_FAILURE_FALLBACK,
        "Failure fallback drifted",
    )
    _require(
        protocol.get("documentation") == EXPECTED_DOCUMENTATION,
        "Documentation binding drifted",
    )
    _require(
        fixture.get("casePolicy") == EXPECTED_CASE_POLICY,
        "Fixture case policy drifted",
    )
    _require(
        fixture.get("claimBoundary") == EXPECTED_FIXTURE_CLAIM_BOUNDARY,
        "Fixture claim boundary drifted",
    )
    _require(
        len(cases) == acceptance.get("expectedCaseCount") == 9,
        "Fixture case count drifted",
    )
    fault_classes = [
        item.get("faultClass")
        for item in cases
        if isinstance(item, dict)
        and item.get("faultClass") != "control"
    ]
    _require(
        len(fault_classes)
        == acceptance.get("expectedFaultCaseCount")
        == 8
        and len(fault_classes) == len(set(fault_classes))
        and set(fault_classes) == REQUIRED_FAULT_CLASSES,
        "Fixture fault class coverage drifted",
    )
    case_ids = [
        item.get("id") for item in cases if isinstance(item, dict)
    ]
    _require(
        len(case_ids) == len(cases)
        and all(isinstance(item, str) and item for item in case_ids)
        and len(case_ids) == len(set(case_ids)),
        "Fixture case identities drifted",
    )
    controls = [
        item for item in cases if item.get("faultClass") == "control"
    ]
    _require(len(controls) == 1, "Exactly one control case is required")

    oracle = protocol.get("oracle")
    _require(isinstance(oracle, dict), "Protocol oracle is missing")
    invariants = oracle.get("invariants")
    assumptions = oracle.get("unauthorizedAssumptions")
    _require(
        isinstance(invariants, list)
        and invariants
        and isinstance(assumptions, list),
        "Protocol oracle weights are missing",
    )
    invariant_weights = {
        item.get("id"): item.get("weight") for item in invariants
    }
    assumption_weights = {
        item.get("id"): item.get("weight") for item in assumptions
    }
    _require(
        len(invariant_weights) == len(invariants)
        and all(
            isinstance(key, str)
            and key
            and isinstance(value, (int, float))
            and not isinstance(value, bool)
            and value > 0
            for key, value in invariant_weights.items()
        ),
        "Invariant weights are invalid",
    )
    _require(
        len(assumption_weights) == len(assumptions)
        and all(
            isinstance(key, str)
            and key
            and isinstance(value, (int, float))
            and not isinstance(value, bool)
            and value > 0
            for key, value in assumption_weights.items()
        ),
        "Assumption weights are invalid",
    )
    _require(
        invariant_weights == EXPECTED_INVARIANT_WEIGHTS
        and assumption_weights == EXPECTED_ASSUMPTION_WEIGHTS
        and oracle.get("faultBudgetMaximum") == 0
        and oracle.get("comparisonMode")
        == "exact-structured-value-and-assumption-comparison"
        and oracle.get("parentRecomputedOnly") is True
        and oracle.get("fixtureReportedMetricsTrusted") is False,
        "Oracle contract drifted",
    )

    source = fixture.get("sourceAnchor")
    _require(isinstance(source, dict), "Source anchor is missing")
    values = source.get("values")
    _require(
        isinstance(values, dict)
        and set(values) == set(invariant_weights),
        "Source invariant set drifted",
    )
    _require(
        set(
            _string_list(
                source.get("provenanceIds"),
                label="Source provenance ids",
            )
        )
        == set(invariant_weights),
        "Source provenance set drifted",
    )
    _require(
        source.get("assumptionIds") == [],
        "Source assumptions must be empty",
    )
    return protocol_faults, invariant_weights, assumption_weights


def _materialize_stages(
    case: dict[str, Any],
    source: dict[str, Any],
    *,
    invariant_ids: set[str],
    assumption_ids: set[str],
) -> list[dict[str, Any]]:
    case_id = case.get("id")
    fault_class = case.get("faultClass")
    _require(
        isinstance(case_id, str) and case_id,
        "Case identity is missing",
    )
    _require(
        fault_class == "control" or fault_class in REQUIRED_FAULT_CLASSES,
        "Unknown fault class",
    )
    changes = case.get("changes")
    _require(isinstance(changes, dict), "Case changes are invalid")
    omitted = set(
        _string_list(
            case.get("omittedInvariantIds"),
            label="Omitted invariant ids",
        )
    )
    assumptions = set(
        _string_list(
            case.get("assumptionIds"),
            label="Assumption ids",
        )
    )
    _require(
        set(changes).issubset(invariant_ids)
        and omitted.issubset(invariant_ids)
        and not (set(changes) & omitted),
        "Unknown or conflicting invariant mutation",
    )
    unknown_assumptions = assumptions - assumption_ids
    _require(
        not unknown_assumptions,
        f"Unknown assumption id: {sorted(unknown_assumptions)}",
    )
    if fault_class == "control":
        _require(
            not changes and not omitted and not assumptions,
            "Control case must not mutate the source",
        )
    else:
        _require(
            bool(changes or omitted or assumptions),
            "Fault case must introduce one registered mutation",
        )

    adapted_values = copy.deepcopy(source["values"])
    for invariant_id in omitted:
        adapted_values.pop(invariant_id)
    adapted_values.update(copy.deepcopy(changes))
    provenance = copy.deepcopy(source["provenanceIds"])
    adapted = {
        "values": adapted_values,
        "provenanceIds": provenance,
        "assumptionIds": sorted(assumptions),
    }
    return [
        {
            "stageId": "source-anchor",
            "values": copy.deepcopy(source["values"]),
            "provenanceIds": copy.deepcopy(source["provenanceIds"]),
            "assumptionIds": [],
            "detectedLossIds": [],
        },
        {
            "stageId": "adapted-message",
            **copy.deepcopy(adapted),
            "detectedLossIds": [],
        },
        {
            "stageId": "review-detection",
            **copy.deepcopy(adapted),
            "detectedLossIds": _string_list(
                case.get("reviewDetectedLossIds"),
                label="Review detected loss ids",
            ),
        },
        {
            "stageId": "human-review-recovery",
            "values": copy.deepcopy(source["values"]),
            "provenanceIds": copy.deepcopy(source["provenanceIds"]),
            "assumptionIds": [],
            "detectedLossIds": [],
        },
    ]


def _score_stage(
    stage: dict[str, Any],
    source: dict[str, Any],
    *,
    invariant_weights: dict[str, int | float],
    assumption_weights: dict[str, int | float],
) -> dict[str, Any]:
    values = stage.get("values")
    _require(isinstance(values, dict), "Stage values are invalid")
    _require(
        set(values).issubset(invariant_weights),
        "Stage contains an unknown invariant value",
    )
    assumptions = _string_list(
        stage.get("assumptionIds"),
        label="Stage assumption ids",
    )
    _require(
        set(assumptions).issubset(assumption_weights),
        "Stage contains an unknown assumption",
    )
    provenance = _string_list(
        stage.get("provenanceIds"),
        label="Stage provenance ids",
    )
    _require(
        set(provenance).issubset(invariant_weights),
        "Stage contains unknown provenance",
    )

    omitted = sorted(set(invariant_weights) - set(values))
    changed = sorted(
        invariant_id
        for invariant_id, expected in source["values"].items()
        if invariant_id in values and values[invariant_id] != expected
    )
    missing_provenance = sorted(set(invariant_weights) - set(provenance))
    active_loss_ids = sorted(
        [f"invariant-omitted:{item}" for item in omitted]
        + [f"invariant-changed:{item}" for item in changed]
        + [f"assumption:{item}" for item in assumptions]
        + [
            f"provenance-missing:{item}"
            for item in missing_provenance
        ]
    )
    weighted_delta = (
        sum(invariant_weights[item] for item in omitted)
        + sum(invariant_weights[item] for item in changed)
        + sum(assumption_weights[item] for item in assumptions)
        + len(missing_provenance)
    )
    detected = _string_list(
        stage.get("detectedLossIds"),
        label="Stage detected loss ids",
    )
    detection_valid = (
        detected == active_loss_ids if stage["stageId"] == "review-detection"
        else detected == []
    )
    return {
        "stageId": stage["stageId"],
        "omittedInvariantIds": omitted,
        "changedInvariantIds": changed,
        "assumptionIds": assumptions,
        "missingProvenanceIds": missing_provenance,
        "activeLossIds": active_loss_ids,
        "detectedLossIds": detected,
        "detectionEvidenceValid": detection_valid,
        "weightedDelta": weighted_delta,
    }


def _evaluate_case(
    case: dict[str, Any],
    fixture: dict[str, Any],
    protocol: dict[str, Any],
    *,
    invariant_weights: dict[str, int | float],
    assumption_weights: dict[str, int | float],
) -> dict[str, Any]:
    source = fixture["sourceAnchor"]
    stages = _materialize_stages(
        case,
        source,
        invariant_ids=set(invariant_weights),
        assumption_ids=set(assumption_weights),
    )
    if case.get("faultClass") != "control":
        specification = protocol["faultSpecifications"].get(
            case.get("faultClass")
        )
        _require(
            isinstance(specification, dict)
            and sorted(case.get("changes", {}).keys())
            == sorted(specification["changedInvariantIds"])
            and sorted(case.get("omittedInvariantIds", []))
            == sorted(specification["omittedInvariantIds"])
            and sorted(case.get("assumptionIds", []))
            == sorted(specification["assumptionIds"]),
            f"Fault mutation shape drifted for {case.get('faultClass')}",
        )
    scored = [
        _score_stage(
            stage,
            source,
            invariant_weights=invariant_weights,
            assumption_weights=assumption_weights,
        )
        for stage in stages
    ]
    expected_order = protocol["stagePolicy"]["stageIdsInOrder"]
    _require(
        [stage["stageId"] for stage in scored] == expected_order,
        "Stage order drifted",
    )
    ledger = build_cumulative_loss_ledger(
        scored,
        protocol,
        cumulative_unique_loss_weight_max=protocol["oracle"][
            "faultBudgetMaximum"
        ],
    )

    expected_adapted = _string_list(
        case.get("expectedAdaptedActiveLossIds"),
        label="Expected adapted active loss ids",
    )
    expected_unique = _string_list(
        case.get("expectedCumulativeUniqueLossIds"),
        label="Expected cumulative unique loss ids",
    )
    _require(
        scored[1]["activeLossIds"] == expected_adapted,
        f"Expected adapted loss set drifted for {case['id']}",
    )
    _require(
        scored[2]["activeLossIds"] == expected_adapted
        and scored[2]["detectionEvidenceValid"],
        f"Review detection drifted for {case['id']}",
    )
    _require(
        scored[-1]["activeLossIds"] == [],
        f"Terminal recovery drifted for {case['id']}",
    )
    _require(
        ledger["cumulativeUniqueLossIds"] == expected_unique,
        f"Expected cumulative loss set drifted for {case['id']}",
    )
    _require(
        ledger["budgetExceededAtHop"]
        == case.get("expectedBudgetExceededAtHop"),
        f"Expected budget result drifted for {case['id']}",
    )
    return {
        "caseId": case["id"],
        "faultClass": case["faultClass"],
        "casePass": True,
        "expectedAdaptedActiveLossIds": expected_adapted,
        "expectedCumulativeUniqueLossIds": expected_unique,
        "stages": scored,
        "cumulativeLoss": ledger,
    }


def evaluate_calibration(
    protocol: dict[str, Any],
    fixture: dict[str, Any],
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    """Evaluate already-loaded protocol and fixture documents."""

    root = root.resolve()
    _validate_bindings(
        protocol,
        fixture,
        root=root,
    )
    (
        _protocol_faults,
        invariant_weights,
        assumption_weights,
    ) = _validate_protocol_and_fixture_shape(protocol, fixture)
    cases = [
        _evaluate_case(
            case,
            fixture,
            protocol,
            invariant_weights=invariant_weights,
            assumption_weights=assumption_weights,
        )
        for case in fixture["cases"]
    ]
    fault_classes = sorted(
        item["faultClass"]
        for item in cases
        if item["faultClass"] != "control"
    )
    claim_boundary = protocol.get("claimBoundary")
    _require(
        claim_boundary == EXPECTED_PROTOCOL_CLAIM_BOUNDARY,
        "Protocol claim boundary drifted",
    )
    execution = protocol.get("executionBoundary")
    _require(
        execution == EXPECTED_EXECUTION_BOUNDARY,
        "Execution boundary drifted",
    )
    protocol_path = _repository_file(
        root,
        PROTOCOL_PATH,
        label="Repository protocol",
    )
    fixture_path = _repository_file(
        root,
        FIXTURE_PATH,
        label="Repository fixture",
    )
    _require(
        protocol
        == json.loads(protocol_path.read_text(encoding="utf-8")),
        "Protocol argument is not the repository-bound object",
    )
    _require(
        fixture
        == json.loads(fixture_path.read_text(encoding="utf-8")),
        "Fixture argument is not the hash-bound repository object",
    )
    report: dict[str, Any] = {
        "schema": 1,
        "id": (
            "human-ai-collaboration-access-comms-zero-model-calibration-"
            "report-2026-07-27"
        ),
        "scenarioId": "GEN-ACCESS-COMMS-01",
        "outcome": "valid-zero-model-calibration",
        "status": "zero-model-calibrated-no-live-agent-or-domain",
        "caseCount": len(cases),
        "faultCaseCount": len(fault_classes),
        "faultClassesCovered": fault_classes,
        "allCasesPassed": all(item["casePass"] for item in cases),
        "agentDispatchCount": 0,
        "modelCallCount": 0,
        "externalAccessUsed": False,
        "formalLiveEvidenceEligible": False,
        "cases": cases,
        "claimBoundary": copy.deepcopy(claim_boundary),
        "claimLimit": (
            "This report proves only a zero-model structured semantic "
            "calibration over the exact frozen fixture and the reused "
            "parent-recomputed process-fidelity accounting. It does not "
            "score free-form language, prove bilingual or domain "
            "correctness, recipient comprehension, accessibility "
            "conformance, human-review effect, live Agent or domain "
            "behavior, candidate Skill value, or cross-host behavior."
        ),
    }
    report["reportSha256"] = canonical_sha256(report)
    return report


def evaluate_repository_calibration(
    root: Path = ROOT,
) -> dict[str, Any]:
    """Load and evaluate the repository-bound calibration."""

    root = root.resolve()
    protocol_path = _repository_file(
        root,
        PROTOCOL_PATH,
        label="Repository protocol",
    )
    fixture_path = _repository_file(
        root,
        FIXTURE_PATH,
        label="Repository fixture",
    )
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    return evaluate_calibration(
        protocol,
        fixture,
        root=root,
    )


def main() -> int:
    print(
        json.dumps(
            evaluate_repository_calibration(ROOT),
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
