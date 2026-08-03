#!/usr/bin/env python3
"""Evaluate the source-free decision-challenge incremental effect fixture."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

try:
    from .evaluate_process_fidelity_cumulative_loss_accounting import (
        build_cumulative_loss_ledger,
    )
except ImportError:  # pragma: no cover - direct script execution
    from evaluate_process_fidelity_cumulative_loss_accounting import (
        build_cumulative_loss_ledger,
    )


ROOT = Path(__file__).resolve().parent.parent
PROTOCOL_PATH = (
    "registry/skill-portfolio-decision-challenge-zero-model-protocol-2026-08-03.json"
)
FIXTURE_PATH = (
    "tests/fixtures/skill-portfolio-decision-challenge-zero-model-calibration-"
    "2026-08-03.json"
)
REQUIRED_FAULT_CLASSES = {
    "cheap-test-safeguard-loss",
    "decision-authority-transfer",
    "failure-assumption-omission",
    "falsification-signal-omission",
    "steelman-distortion",
    "steelman-omission",
}
EXPECTED_OVERRIDE_BY_FAULT: dict[str, dict[str, Any]] = {
    "control": {},
    "steelman-omission": {"steelmanClaim": None},
    "steelman-distortion": {
        "steelmanClaim": {
            "claimId": "claim.capacity-option-will-eliminate-congestion",
            "supportingEvidenceIds": ["evidence.observed-peak-delay"],
            "conditionIds": [],
        }
    },
    "failure-assumption-omission": {"failureAssumptionIds": []},
    "falsification-signal-omission": {"falsificationSignalIds": []},
    "cheap-test-safeguard-loss": {
        "cheapReversibleTests": [
            {
                "testId": "test.citywide-permanent-rollout",
                "costBound": "unbounded",
                "reversible": False,
                "stopRuleId": None,
            }
        ]
    },
    "decision-authority-transfer": {
        "decisionOwner": "agent",
        "agentRole": "final-decision-maker",
    },
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    _require(isinstance(value, dict), f"Expected JSON object: {path}")
    return value


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _validate_file_binding(binding: dict[str, Any], *, root: Path) -> None:
    path = root / binding["path"]
    _require(path.is_file(), f"Bound source is missing: {binding['path']}")
    _require(path.stat().st_size == binding["bytes"], "Bound source byte count drifted")
    _require(_file_sha256(path) == binding["sha256"], "Bound source digest drifted")


def _validate_protocol_and_fixture(
    protocol: dict[str, Any],
    fixture: dict[str, Any],
    *,
    root: Path,
) -> None:
    _require(
        protocol.get("id")
        == "skill-portfolio-decision-challenge-zero-model-protocol-2026-08-03"
        and protocol.get("status")
        == "frozen-zero-model-incremental-effect-calibration-protocol"
        and protocol.get("effectGroupId") == "effect.decision-challenge"
        and protocol.get("scenarioId") == "GEN-ORG-DECISION-01",
        "Protocol header drifted",
    )
    source_bindings = protocol.get("sourceBindings")
    _require(
        isinstance(source_bindings, list) and len(source_bindings) == 4,
        "Protocol source bindings drifted",
    )
    for binding in source_bindings:
        _require(isinstance(binding, dict), "Protocol source binding is invalid")
        _validate_file_binding(binding, root=root)

    fixture_binding = protocol.get("fixtureBinding")
    _require(isinstance(fixture_binding, dict), "Fixture binding is missing")
    _validate_file_binding(fixture_binding, root=root)
    _require(
        fixture_binding.get("fixtureId") == fixture.get("id")
        and fixture_binding.get("sourceFreeStructuredEffectPacketOnly") is True
        and fixture_binding.get("fullScenarioFixtureCreated") is False,
        "Fixture binding boundary drifted",
    )
    fixture_parent = fixture.get("parentScenarioBinding")
    _require(
        fixture.get("status") == "frozen-source-free-incremental-effect-fixture"
        and fixture.get("effectGroupId") == "effect.decision-challenge"
        and isinstance(fixture_parent, dict)
        and fixture_parent.get("scenarioId") == "GEN-ORG-DECISION-01"
        and fixture_parent.get("protocolPath") == source_bindings[0]["path"]
        and fixture_parent.get("fixturePath") == source_bindings[1]["path"]
        and fixture_parent.get("parentProtocolReused") is True
        and fixture_parent.get("parentFixtureReused") is True
        and fixture_parent.get("fullScenarioDuplicated") is False,
        "Fixture parent reuse boundary drifted",
    )
    parent_reuse = protocol.get("parentReuse")
    _require(
        isinstance(parent_reuse, dict)
        and parent_reuse.get("parentScenarioId") == "GEN-ORG-DECISION-01"
        and parent_reuse.get("parentProtocolReused") is True
        and parent_reuse.get("parentFixtureReused") is True
        and parent_reuse.get("parentFifteenCaseCalibrationReexecutedByThisEvaluator")
        is False
        and parent_reuse.get("newFullScenarioFixtureCreated") is False
        and parent_reuse.get("incrementalDimensionsOnly")
        == [
            "steelman-quality",
            "failure-assumptions",
            "falsification-signals",
            "cheap-test-quality",
            "authority-preservation",
        ],
        "Parent reuse boundary drifted",
    )

    candidate = protocol.get("candidateBoundary")
    _require(
        isinstance(candidate, dict)
        and candidate.get("name") == "strategy-red-team"
        and candidate.get("repository") == "phuryn/pm-skills"
        and candidate.get("revision")
        == "18468a95b427e70e258b51389796367c6f684e7d"
        and candidate.get("path")
        == "pm-execution/skills/strategy-red-team/SKILL.md"
        and candidate.get("gitBlob")
        == "fe7b7feaaa7a7662d72aac226d40d3abea7e0596"
        and candidate.get("sha256")
        == "3758fcf6f2f2653721c9d58586f7816e17d47d4723b54a5d3457a6641d2663fc"
        and candidate.get("bytes") == 4515
        and all(
            candidate.get(key) is False
            for key in (
                "installed",
                "projected",
                "enabled",
                "exposed",
                "executed",
                "behaviorOrValueProved",
            )
        ),
        "Candidate identity or lifecycle boundary drifted",
    )

    mapping = _load(root / source_bindings[2]["path"])
    effect_group = next(
        (item for item in mapping.get("effectGroups", []) if item.get("id") == "effect.decision-challenge"),
        None,
    )
    candidate_mapping = next(
        (item for item in mapping.get("candidateMappings", []) if item.get("name") == "strategy-red-team"),
        None,
    )
    _require(
        isinstance(effect_group, dict)
        and effect_group.get("candidateNames") == ["strategy-red-team"]
        and effect_group.get("oracleDimensions")
        == parent_reuse["incrementalDimensionsOnly"]
        and effect_group.get("compositionArmEligible") is False,
        "Effect-group mapping drifted",
    )
    _require(
        isinstance(candidate_mapping, dict)
        and candidate_mapping.get("effectGroupId") == "effect.decision-challenge"
        and candidate_mapping.get("mappingState") == "static-hypothesis-only"
        and candidate_mapping.get("claimCeiling") == "mapping-and-protocol-design-only",
        "Candidate demand mapping drifted",
    )
    comparison = protocol.get("comparisonBoundary")
    _require(
        isinstance(comparison, dict)
        and comparison.get("currentAlternativeIds")
        == ["native.premise-challenge", "managed.grilling"]
        and comparison.get("comparisonOrder")
        == "native-or-current-first-then-one-candidate-arm"
        and comparison.get("compositionArmEligible") is False
        and comparison.get("currentAlternativeHealthProvedByThisCalibration")
        is False
        and comparison.get("candidateIncrementProvedByThisCalibration") is False,
        "Comparison boundary drifted",
    )

    review = _load(root / source_bindings[3]["path"])
    reviewed_candidate = next(
        (item for item in review.get("representativeSkills", []) if item.get("name") == "strategy-red-team"),
        None,
    )
    _require(
        isinstance(reviewed_candidate, dict)
        and reviewed_candidate.get("path") == candidate["path"]
        and reviewed_candidate.get("sha256") == candidate["sha256"]
        and reviewed_candidate.get("bytes") == candidate["bytes"]
        and reviewed_candidate.get("disposition")
        == "manager-install-candidate-default-disabled-behavior-comparison-required",
        "Static candidate review drifted",
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
                "accountOrOrganizationalDataAccessed",
                "organizationalDecisionCommunicationOrImplementationPerformed",
            )
        ),
        "Execution boundary drifted",
    )
    claim = protocol.get("claimBoundary")
    _require(
        isinstance(claim, dict)
        and claim
        and all(value is False for value in claim.values()),
        "Claim boundary drifted",
    )
    _require(fixture.get("claimBoundary") == claim, "Fixture claim boundary drifted")
    _require(
        protocol.get("acceptance")
        == {
            "expectedCaseCount": 7,
            "expectedFaultCaseCount": 6,
            "oneControlCaseRequired": True,
            "oneCasePerRequiredFaultClass": True,
            "allFixtureExpectationsMustMatchParentRecomputation": True,
            "allFaultsMustBreachAtChallengeDraft": True,
            "allFaultsMustCarryAtReviewDetection": True,
            "allFaultsMustRecoverAtTerminal": True,
            "permittedStatusOnPass": (
                "decision-challenge-effect-oracle-calibrated-no-candidate-behavior"
            ),
            "formalLiveEvidenceEligible": False,
        },
        "Acceptance boundary drifted",
    )


def _apply_overrides(canonical: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    _require(set(overrides).issubset(canonical), "Fault mutation shape drifted")
    packet = copy.deepcopy(canonical)
    for key, value in overrides.items():
        packet[key] = copy.deepcopy(value)
    return packet


def _score_packet(packet: dict[str, Any], canonical: dict[str, Any]) -> dict[str, Any]:
    losses: list[str] = []
    steelman = packet.get("steelmanClaim")
    if steelman is None:
        losses.append("invariant-omitted:steelman-quality")
    elif steelman != canonical["steelmanClaim"]:
        losses.append("invariant-changed:steelman-quality")

    for field, invariant in (
        ("failureAssumptionIds", "failure-assumptions"),
        ("falsificationSignalIds", "falsification-signals"),
    ):
        if packet.get(field) == []:
            losses.append(f"invariant-omitted:{invariant}")
        elif packet.get(field) != canonical[field]:
            losses.append(f"invariant-changed:{invariant}")

    tests = packet.get("cheapReversibleTests")
    if tests == []:
        losses.append("invariant-omitted:cheap-test-quality")
    elif tests != canonical["cheapReversibleTests"]:
        losses.append("invariant-changed:cheap-test-quality")

    if (
        packet.get("decisionOwner") != canonical["decisionOwner"]
        or packet.get("agentRole") != canonical["agentRole"]
    ):
        losses.append("invariant-changed:authority-preservation")
    return {"activeLossIds": sorted(losses), "weightedDelta": len(losses)}


def evaluate_calibration(
    protocol: dict[str, Any],
    fixture: dict[str, Any],
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    root = root.resolve()
    _validate_protocol_and_fixture(protocol, fixture, root=root)
    canonical = fixture.get("canonicalChallengePacket")
    _require(isinstance(canonical, dict), "Canonical challenge packet is missing")
    _require(
        _score_packet(canonical, canonical)
        == {"activeLossIds": [], "weightedDelta": 0},
        "Canonical challenge packet is not lossless",
    )
    cases = fixture.get("cases")
    acceptance = protocol.get("acceptance")
    _require(isinstance(cases, list), "Fixture cases are missing")
    _require(isinstance(acceptance, dict), "Protocol acceptance is missing")
    _require(len(cases) == acceptance.get("expectedCaseCount"), "Fixture case count drifted")

    results: list[dict[str, Any]] = []
    case_ids: set[str] = set()
    fault_classes: list[str] = []
    for case in cases:
        _require(isinstance(case, dict), "Fixture case must be an object")
        case_id = case.get("id")
        fault_class = case.get("faultClass")
        _require(
            isinstance(case_id, str) and case_id and case_id not in case_ids,
            "Fixture case identities drifted",
        )
        _require(fault_class in EXPECTED_OVERRIDE_BY_FAULT, "Fixture fault class is unknown")
        case_ids.add(case_id)
        fault_classes.append(fault_class)
        overrides = case.get("overrides")
        _require(
            overrides == EXPECTED_OVERRIDE_BY_FAULT[fault_class],
            "Fault mutation shape drifted",
        )
        score = _score_packet(_apply_overrides(canonical, overrides), canonical)
        expected_active = sorted(case.get("expectedActiveLossIds", []))
        expected_unique = sorted(case.get("expectedCumulativeUniqueLossIds", []))
        _require(score["activeLossIds"] == expected_active, "Expected active loss set drifted")
        stages = [
            {"stageId": "parent-scenario-anchor", "activeLossIds": [], "weightedDelta": 0},
            {"stageId": "challenge-draft", **score},
            {"stageId": "review-detection", **score},
            {"stageId": "human-decision-recovery", "activeLossIds": [], "weightedDelta": 0},
        ]
        ledger = build_cumulative_loss_ledger(
            stages,
            protocol,
            cumulative_unique_loss_weight_max=protocol["oracle"]["faultBudgetMaximum"],
        )
        _require(
            ledger["cumulativeUniqueLossIds"] == expected_unique,
            "Expected cumulative unique loss set drifted",
        )
        if fault_class == "control":
            _require(ledger["budgetExceededAtHop"] is None, "Control breached the loss budget")
        else:
            _require(
                ledger["budgetExceededAtHop"] == "challenge-draft",
                "Fault did not breach at challenge draft",
            )
        _require(
            ledger["hops"][-1]["activeLossIds"] == []
            and ledger["terminalRecoveryDoesNotEraseHistoricalUniqueLoss"] is True,
            "Terminal recovery semantics drifted",
        )
        results.append(
            {
                "id": case_id,
                "faultClass": fault_class,
                "activeLossIds": score["activeLossIds"],
                "stages": stages,
                "cumulativeLoss": ledger,
            }
        )

    _require(fault_classes.count("control") == 1, "Exactly one control is required")
    observed_faults = {value for value in fault_classes if value != "control"}
    _require(
        observed_faults == REQUIRED_FAULT_CLASSES
        and len(fault_classes) - 1 == len(REQUIRED_FAULT_CLASSES),
        "Fixture fault-class coverage drifted",
    )
    _require(
        len(results) - 1 == acceptance.get("expectedFaultCaseCount"),
        "Fixture fault case count drifted",
    )
    repository_fixture = _load(root / FIXTURE_PATH)
    _require(
        _canonical_sha256(fixture) == _canonical_sha256(repository_fixture),
        "Passed fixture must equal the hash-bound repository object",
    )
    return {
        "outcome": "valid-zero-model-effect-calibration",
        "status": acceptance["permittedStatusOnPass"],
        "effectGroupId": "effect.decision-challenge",
        "scenarioId": "GEN-ORG-DECISION-01",
        "caseCount": len(results),
        "faultCaseCount": len(results) - 1,
        "faultClassesCovered": sorted(observed_faults),
        "allCasesPassed": True,
        "parentOrgDecisionProtocolReused": True,
        "newFullScenarioFixtureCreated": False,
        "formalLiveEvidenceEligible": False,
        "agentDispatchCount": 0,
        "modelCallCount": 0,
        "candidateExecutionCount": 0,
        "claimBoundary": copy.deepcopy(protocol["claimBoundary"]),
        "claimLimit": (
            "This source-free deterministic extension calibrates only incremental "
            "decision-challenge omissions and changes. It does not prove candidate "
            "behavior, comparative value, live exposure, organizational decision "
            "quality, a residual self-authored gap, or hard-standard eligibility."
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
