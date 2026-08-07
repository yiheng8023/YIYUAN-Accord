#!/usr/bin/env python3
"""Validate the first open-world collaboration scenario-evidence batch."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from validate_human_ai_collaboration_coverage_rebaseline import (
        EXPECTED_AXES,
        EXPECTED_LIFECYCLE_SLICES,
    )
except ModuleNotFoundError:
    from scripts.validate_human_ai_collaboration_coverage_rebaseline import (
        EXPECTED_AXES,
        EXPECTED_LIFECYCLE_SLICES,
    )


ROOT = Path(__file__).resolve().parent.parent
MATRIX_PATH = (
    "registry/human-ai-collaboration-scenario-evidence-matrix-batch-01-2026-07-24.json"
)
MATRIX_DOC_PATH = (
    "docs/strategy/HUMAN-AI-COLLABORATION-SCENARIO-EVIDENCE-MATRIX-BATCH-01-2026-07-24.md"
)
REBASELINE_PATH = "registry/human-ai-collaboration-coverage-rebaseline-2026-07-24.json"
MATRIX_EVIDENCE_ID = (
    "evidence.human-ai-collaboration-scenario-evidence-matrix-batch-01"
)
AI_INDEPENDENT_HARD_STANDARD_GATE_EVIDENCE_ID = (
    "evidence.ai-independent-hard-standard-boundary-gate-2026-08-07"
)
REBASELINE_EVIDENCE_ID = "evidence.human-ai-collaboration-coverage-rebaseline"
RELEASE_CHANGE_PROTOCOL_EVIDENCE_ID = (
    "evidence.human-ai-collaboration-release-change-zero-model-"
    "protocol-2026-07-27"
)
RELEASE_CHANGE_CURRENT_CC_CODEX_PREFLIGHT_EVIDENCE_ID = (
    "evidence.human-ai-collaboration-release-change-current-cc-codex-"
    "no-model-preflight-2026-07-30"
)
TDD_READINESS_EVIDENCE_ID = (
    "evidence.human-ai-collaboration-tdd-current-execution-readiness-"
    "reconciliation-2026-07-27"
)
TDD_SUCCESSOR_CONTRACT_EVIDENCE_ID = (
    "evidence.human-ai-collaboration-tdd-noncomparative-dispatch-"
    "successor-contract-v2-2026-07-27"
)
ACCESS_COMMS_CALIBRATION_EVIDENCE_ID = (
    "evidence.human-ai-collaboration-access-comms-zero-model-calibration-"
    "2026-07-27"
)
ORG_DECISION_CALIBRATION_EVIDENCE_ID = (
    "evidence.human-ai-collaboration-org-decision-zero-model-calibration-"
    "2026-07-31"
)
ENGINEERING_MANAGEMENT_CALIBRATION_EVIDENCE_ID = (
    "evidence.human-ai-collaboration-engineering-management-zero-model-"
    "calibration-2026-07-31"
)
AI_ERA_ENGINEERING_REVALIDATION_EVIDENCE_ID = (
    "evidence.ai-era-classical-software-engineering-principles-"
    "revalidation-2026-07-31"
)
MULTIDIMENSIONAL_ENGINEERING_EVALUATION_EVIDENCE_ID = (
    "evidence.multidimensional-software-engineering-evaluation-contract-"
    "2026-07-31"
)
MULTIDIMENSIONAL_ENGINEERING_SOURCE_SNAPSHOT_EVIDENCE_ID = (
    "evidence.multidimensional-software-engineering-source-snapshot-"
    "2026-07-31"
)
LONGHORIZON_STATIC_REUSE_ASSESSMENT_EVIDENCE_ID = (
    "evidence.process-loss-longhorizon-harness-static-reuse-assessment-2026-08-07"
)
LONGHORIZON_INTERFACE_GAP_MAPPING_EVIDENCE_ID = (
    "evidence.process-loss-longhorizon-harness-interface-gap-mapping-2026-08-07"
)
LONGHORIZON_EXECUTION_PREFLIGHT_EVIDENCE_ID = (
    "evidence.process-loss-longhorizon-harness-execution-preflight-2026-08-07"
)
LEARNING_CAPABILITY_BASELINE_EVIDENCE_ID = (
    "evidence.human-ai-collaboration-learning-capability-baseline-2026-07-31"
)
CREATIVE_CAPABILITY_BASELINE_EVIDENCE_ID = (
    "evidence.human-ai-collaboration-creative-capability-baseline-2026-07-31"
)
ACCESS_COMMS_CAPABILITY_BASELINE_EVIDENCE_ID = (
    "evidence.human-ai-collaboration-access-comms-capability-baseline-2026-07-31"
)
CURRENT_CANDIDATE_COVERAGE_RECONCILIATION_EVIDENCE_ID = (
    "evidence.human-ai-collaboration-current-candidate-capability-coverage-"
    "reconciliation-2026-08-01"
)
LEARNING_NORU_INDEPENDENT_REVIEW_READINESS_EVIDENCE_ID = (
    "evidence.human-ai-collaboration-learning-noru-independent-review-"
    "readiness-2026-08-01"
)
SYSTEM_MANAGER_REFERENCE_COHORT_EVIDENCE_ID = (
    "evidence.skill-portfolio-system-manager-reference-cohort-2026-08-06"
)
SEMANTIC_AUTHORITY_CONTINUITY_EVIDENCE_ID = (
    "evidence.human-ai-collaboration-semantic-authority-"
    "continuity-protocol-2026-07-28"
)
CURRENT_MATT_EXPOSURE_REFRESH_EVIDENCE_ID = (
    "evidence.human-ai-collaboration-semantic-authority-"
    "current-matt-no-model-exposure-refresh-2026-07-31"
)
NATIVE_LOCAL_EXPOSURE_ORACLE_EVIDENCE_ID = (
    "evidence.human-ai-collaboration-semantic-authority-native-local-"
    "no-model-exposure-and-oracle-2026-08-01"
)
SEMANTIC_EXECUTION_PLAN_PREFLIGHT_EVIDENCE_ID = (
    "evidence.human-ai-collaboration-semantic-authority-execution-plan-"
    "preflight-2026-08-01"
)
SEMANTIC_RUNTIME_ADAPTER_PREFLIGHT_EVIDENCE_ID = (
    "evidence.human-ai-collaboration-semantic-authority-runtime-adapter-"
    "preflight-2026-08-01"
)
SEMANTIC_LIVE_ADAPTER_DECISION_EVIDENCE_ID = (
    "evidence.human-ai-collaboration-semantic-authority-live-dispatch-"
    "adapter-decision-2026-08-01"
)
SEMANTIC_LIVE_DISPATCH_GATE_PREFLIGHT_EVIDENCE_ID = (
    "evidence.human-ai-collaboration-semantic-authority-live-dispatch-"
    "gate-preflight-2026-08-01"
)
EXPECTED_HOSTS = {
    "host.native-transparent",
    "host.configurable-agent",
    "host.opaque",
    "host.human-only-control",
}
EXPECTED_HARD_REQUIREMENTS = {
    "HR-01-goal-and-acceptance",
    "HR-02-truth-provenance-and-uncertainty",
    "HR-03-authority-data-and-least-privilege",
    "HR-04-domain-safety-quality-and-rights",
    "HR-05-reversibility-recovery-and-continuity",
    "HR-06-human-decision-and-accountability",
    "HR-07-lifecycle-maintenance-and-retirement",
}
EXPECTED_GENERAL_SCENARIOS = {
    "GEN-CREATIVE-01",
    "GEN-RESEARCH-01",
    "GEN-LEARNING-01",
    "GEN-ORG-DECISION-01",
    "GEN-ACCESS-COMMS-01",
}
EXPECTED_SOFTWARE_SCENARIOS = {
    "SE-DISCOVERY-REQ-01",
    "SE-ARCH-DESIGN-01",
    "SE-IMPLEMENT-REVIEW-01",
    "SE-VERIFY-SECURE-01",
    "SE-RELEASE-CHANGE-01",
    "SE-OPS-INCIDENT-01",
    "SE-MAINT-MIGRATE-01",
    "SE-MGMT-PRACTICE-01",
}
EXPECTED_LANES = {
    "context-lifecycle-and-continuation",
    "git-collaboration-topology",
    "task-scoped-mcp-lifecycle",
    "skill-portfolio-and-ablation",
}
ACCEPTANCE_IDS = {
    "acceptance.solution-neutral-collaboration-rebaseline",
    "acceptance.software-engineering-lifecycle-specialization",
    "acceptance.end-to-end-process-fidelity",
    "acceptance.ai-independent-hard-standard-boundary",
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _index(items: Any, field: str, label: str) -> dict[str, dict[str, Any]]:
    _require(isinstance(items, list), f"{label} must be a list")
    result: dict[str, dict[str, Any]] = {}
    for item in items:
        _require(isinstance(item, dict), f"{label} entries must be objects")
        key = item.get(field)
        _require(_text(key), f"{label} entry is missing {field}")
        _require(key not in result, f"{label} contains duplicate {field}: {key}")
        result[key] = item
    return result


def validate_matrix(
    document: dict[str, Any],
    rebaseline: dict[str, Any],
    program: dict[str, Any],
    acceptance: dict[str, Any],
    *,
    root: Path = ROOT,
) -> None:
    _require(document.get("schema") == 1, "Scenario matrix schema must be 1")
    _require(
        document.get("id")
        == "human-ai-collaboration-scenario-evidence-matrix-batch-01-2026-07-24",
        "Scenario matrix identity drifted",
    )
    _require(
        document.get("status")
        == "planned-falsifiable-scenario-batch-no-live-domain-evidence",
        "Scenario matrix status overclaimed or drifted",
    )
    authority = document.get("authorityBoundary")
    _require(isinstance(authority, dict), "Scenario matrix authority boundary is missing")
    _require(
        authority.get("calibrationState") == "paused-read-only-source",
        "Scenario matrix CALIBRATION state drifted",
    )
    for key in (
        "calibrationWriteAuthorized",
        "assetsAdmissionAuthorized",
        "hardStandardPromotionAuthorized",
        "skillOrHookMutationAuthorized",
        "runtimeMutationAuthorized",
        "externalCapabilityInstallationAuthorized",
        "liveAccountOrPrivateDataAccessAuthorized",
        "gitCommitOrPushAuthorized",
    ):
        _require(authority.get(key) is False, f"Scenario matrix authority promoted: {key}")

    basis = document.get("basis", {})
    _require(
        basis.get("coverageRebaseline") == REBASELINE_PATH,
        "Scenario matrix rebaseline binding drifted",
    )
    _require(
        basis.get("supplementalSdlcResearchIntake")
        == "registry/user-supplied-human-ai-sdlc-research-intake-2026-07-24.json",
        "Scenario matrix supplemental SDLC intake binding drifted",
    )
    _require(
        rebaseline.get("id") == "human-ai-collaboration-coverage-rebaseline-2026-07-24",
        "Scenario matrix rebaseline object drifted",
    )
    semantics = document.get("coverageSemantics")
    _require(isinstance(semantics, dict), "Scenario matrix coverage semantics are missing")
    _require(
        semantics.get("model") == "open-world-versioned-observed-and-unassessed-cells",
        "Scenario matrix became a closed-world coverage model",
    )
    for key in (
        "scenarioCountIsCompletionTarget",
        "allAxesSampledMeansWholeDomainCovered",
        "allLifecycleSlicesSampledMeansSoftwareLifecycleCovered",
        "plannedScenarioMeansEvidenceExists",
        "unknownMeansResidualCapabilityGap",
    ):
        _require(semantics.get(key) is False, f"Scenario matrix completeness or gap claim promoted: {key}")
    _require("independent of AI" in str(semantics.get("hardRequirementRole")), "Hard requirement independence is missing")
    _require("cannot replace" in str(semantics.get("softCapabilityRole")), "Soft capability role was promoted")

    reuse = document.get("reuseOrder")
    _require(
        isinstance(reuse, list)
        and [item.get("code") for item in reuse if isinstance(item, dict)]
        == ["N", "O", "E", "C", "H", "R"],
        "Scenario matrix reuse order drifted",
    )
    for item in reuse:
        _require(_text(item.get("class")), "Scenario matrix reuse class is missing")

    hosts = _index(document.get("hostClasses"), "id", "Scenario matrix host classes")
    _require(set(hosts) == EXPECTED_HOSTS, "Scenario matrix host classes drifted")
    for item in hosts.values():
        _require(_text(item.get("description")) and _text(item.get("claimLimit")), "Scenario matrix host boundary is incomplete")

    hard_requirements = _index(
        document.get("hardRequirements"), "id", "Scenario matrix hard requirements"
    )
    _require(
        set(hard_requirements) == EXPECTED_HARD_REQUIREMENTS,
        "Scenario matrix hard requirement set drifted",
    )
    for item in hard_requirements.values():
        _require(item.get("validWithoutAi") is True, "Hard requirement became AI-dependent")
        for key in ("obligation", "ownerClass", "verificationClass"):
            _require(_text(item.get(key)), f"Hard requirement {key} is missing")

    cross_risks = _index(
        document.get("crossCuttingRisks"), "id", "Scenario matrix cross-cutting risks"
    )
    _require(
        set(cross_risks) == {"XCR-01-process-fidelity-and-loss"},
        "Scenario matrix process-fidelity cross-cut drifted",
    )
    process_risk = cross_risks["XCR-01-process-fidelity-and-loss"]
    _require(
        process_risk.get("appliesToAllScenarios") is True,
        "Process-fidelity cross-cut lost all-scenario scope",
    )
    for key in (
        "requiredInvariants",
        "acceptanceSignals",
        "evidenceNeeded",
        "forbiddenClaims",
    ):
        values = process_risk.get(key)
        _require(
            isinstance(values, list) and len(values) >= 4,
            f"Process-fidelity {key} is incomplete",
        )
    for key in ("scope", "failureAndFallback", "falsifier", "evidenceState"):
        _require(_text(process_risk.get(key)), f"Process-fidelity {key} is missing")
    measurement_contract = process_risk.get("measurementContract")
    _require(
        isinstance(measurement_contract, dict)
        and set(measurement_contract)
        == {
            "invariantSurvivalRate",
            "weightedOmissionScore",
            "addedAssumptionCount",
            "provenanceBreakCount",
            "authorityDriftCount",
            "detectionLatencyHops",
            "amplificationFactor",
            "recoveryDistanceHops",
            "rollbackSuccessRate",
            "thresholdRule",
        }
        and all(_text(value) for value in measurement_contract.values())
        and "preregister" in measurement_contract["thresholdRule"]
        and "last trusted recovery anchor"
        in measurement_contract["thresholdRule"],
        "Process-fidelity measurement contract is incomplete",
    )
    _require(
        "Every scenario references this risk"
        in str(process_risk.get("scenarioBindingRule"))
        and "last source-backed recovery anchor"
        in str(process_risk.get("scenarioBindingRule")),
        "Process-fidelity scenario binding rule drifted",
    )
    _require(
        process_risk.get("evidenceState")
        == "planned-no-end-to-end-process-fidelity-evidence",
        "Process-fidelity evidence was overclaimed",
    )
    _require(
        process_risk.get("deterministicEvidence")
        == (
            "registry/process-fidelity-multihop-injection-poc-"
            "evidence-2026-07-26.json"
        ),
        "Process-fidelity deterministic evidence binding drifted",
    )
    _require(
        process_risk.get("measurementCalibrationEvidence")
        == (
            "registry/human-ai-collaboration-process-fidelity-v1-"
            "calibration-abort-2026-07-27.json"
        )
        and process_risk.get("chainedTraceMeasurementCalibrationEvidence")
        == (
            "registry/human-ai-collaboration-process-fidelity-chained-trace-"
            "measurement-calibration-2026-07-27.json"
        )
        and process_risk.get("rawEventTraceEligibilityEvidence")
        == (
            "registry/human-ai-collaboration-process-fidelity-raw-event-trace-"
            "eligibility-assessment-2026-07-27.json"
        )
        and process_risk.get("cumulativeLossAccountingEvidence")
        == (
            "registry/human-ai-collaboration-process-fidelity-cumulative-"
            "loss-accounting-poc-evidence-2026-07-27.json"
        ),
        "Process-fidelity calibration evidence binding drifted",
    )

    scenarios = _index(document.get("scenarios"), "id", "Scenario matrix scenarios")
    expected_scenarios = EXPECTED_GENERAL_SCENARIOS | EXPECTED_SOFTWARE_SCENARIOS
    _require(set(scenarios) == expected_scenarios, "Scenario matrix scenario set drifted")
    axis_union: set[str] = set()
    lifecycle_union: set[str] = set()
    for scenario_id, scenario in scenarios.items():
        is_general = scenario_id in EXPECTED_GENERAL_SCENARIOS
        _require(
            scenario.get("kind")
            == (
                "general-human-ai-collaboration"
                if is_general
                else "software-engineering-specialization"
            ),
            f"Scenario kind drifted: {scenario_id}",
        )
        for key in (
            "domain",
            "task",
            "authorityBoundary",
            "dataBoundary",
            "failureAndFallback",
            "falsifier",
            "evidenceState",
        ):
            _require(_text(scenario.get(key)), f"Scenario {key} is missing: {scenario_id}")
        if scenario_id == "SE-OPS-INCIDENT-01":
            _require(
                scenario.get("evidenceState")
                == "bounded-synthetic-live-agent-evidence-no-live-domain-evidence"
                and scenario.get("liveEvidence")
                == [
                    "registry/human-ai-collaboration-weak-agent-live-comparison-batch-02-2026-07-24.json",
                    "registry/human-ai-collaboration-weak-agent-live-comparison-batch-03-2026-07-24.json",
                ]
                and "0/3 native and 2/3 diagnose"
                in str(scenario.get("observedResult"))
                and "full hidden contract passed Matt 1/3 and Superpowers 2/3"
                in str(scenario.get("observedResult"))
                and "favors neither candidate"
                in str(scenario.get("observedResult"))
                and _text(scenario.get("remainingEvidenceGap")),
                f"Scenario evidence was overclaimed or drifted: {scenario_id}",
            )
        elif scenario_id == "SE-DISCOVERY-REQ-01":
            _require(
                scenario.get("evidenceState")
                == "bounded-synthetic-live-agent-evidence-no-loader-causation-or-live-domain-evidence"
                and scenario.get("protocolEvidence")
                == "registry/human-ai-collaboration-requirements-domain-challenge-protocol-batch-01-2026-07-24.json"
                and scenario.get("preflightEvidence")
                == "registry/requirements-domain-exposure-preflight-evidence-2026-07-24.json"
                and scenario.get("liveEvidence")
                == [
                    "registry/human-ai-collaboration-requirements-domain-live-comparison-batch-01-2026-07-24.json"
                ]
                and "Visible tests passed native 0/3"
                in str(scenario.get("observedResult"))
                and "hidden contract passed 0/3 in both arms"
                in str(scenario.get("observedResult"))
                and "no preference, added value, harm, loader event, causation"
                in str(scenario.get("observedResult"))
                and _text(scenario.get("remainingEvidenceGap")),
                f"Requirements scenario evidence was overclaimed or drifted: {scenario_id}",
            )
        elif scenario_id == "SE-IMPLEMENT-REVIEW-01":
            _require(
                scenario.get("evidenceState")
                == "bounded-synthetic-live-agent-evidence-no-loader-causation-or-live-domain-evidence"
                and scenario.get("protocolEvidence")
                == "registry/human-ai-collaboration-comparative-protocol-batch-01-2026-07-24.json"
                and scenario.get("nextProtocolEvidence")
                == "registry/human-ai-collaboration-new-feature-tdd-protocol-2026-07-26.json"
                and scenario.get("nextProtocolPreflightEvidence")
                == "registry/human-ai-collaboration-new-feature-tdd-exposure-preflight-2026-07-26.json"
                and scenario.get("nextProtocolPilotEvidence")
                == "registry/human-ai-collaboration-tdd-raw-item-pilot-evidence-2026-07-26.json"
                and scenario.get("nextProtocolFormalEvidence")
                == "registry/human-ai-collaboration-tdd-formal-runner-first-attempt-evidence-2026-07-26.json"
                and scenario.get("nextProtocolNativeBatchEvidence")
                == "registry/human-ai-collaboration-tdd-native-formal-attempt-batch-2026-07-26.json"
                and scenario.get("nextProtocolNoncomparativeDiagnostic")
                == "registry/human-ai-collaboration-tdd-noncomparative-treatment-diagnostic-protocol-2026-07-26.json"
                and scenario.get(
                    "nextProtocolSourceGovernancePreflightEvidence"
                )
                == "registry/human-ai-collaboration-tdd-noncomparative-treatment-diagnostic-source-governance-preflight-2026-07-26.json"
                and scenario.get(
                    "nextProtocolExactCandidateAdmissionGapAuditEvidence"
                )
                == "registry/human-ai-collaboration-tdd-exact-candidate-admission-gap-audit-2026-07-26.json"
                and scenario.get(
                    "nextProtocolDispatchIdentityLedgerPocEvidence"
                )
                == "registry/human-ai-collaboration-tdd-noncomparative-dispatch-identity-ledger-poc-evidence-2026-07-26.json"
                and scenario.get(
                    "nextProtocolDispatchAuthorizationAdapterPocEvidence"
                )
                == "registry/human-ai-collaboration-tdd-noncomparative-dispatch-authorization-adapter-poc-evidence-2026-07-26.json"
                and scenario.get(
                    "nextProtocolRunnerPreflightPocEvidence"
                )
                == "registry/human-ai-collaboration-tdd-noncomparative-runner-preflight-poc-evidence-2026-07-26.json"
                and scenario.get("liveEvidence")
                == [
                    "registry/human-ai-collaboration-weak-agent-live-comparison-batch-01-2026-07-24.json"
                ]
                and "Both arms passed the visible and hidden functional oracle 3/3"
                in str(scenario.get("observedResult"))
                and "strict process boundary passed native 3/3 and the candidate 2/3"
                in str(scenario.get("observedResult"))
                and "transient out-of-scope .tmp.patch"
                in str(scenario.get("observedResult"))
                and "loader invocation"
                in str(scenario.get("observedResult"))
                and "raw trace could be normalized"
                in str(scenario.get("observedResult"))
                and "opaque-write trace failed closed"
                in str(scenario.get("observedResult"))
                and "three capped native attempts"
                in str(scenario.get("observedResult"))
                and "r3 killed 7/7 mutants"
                in str(scenario.get("observedResult"))
                and "Zero repetitions count"
                in str(scenario.get("observedResult"))
                and "no valid native comparison baseline"
                in str(scenario.get("observedResult"))
                and "offline and raw-event classifiers"
                in str(scenario.get("remainingEvidenceGap"))
                and "executable seven-mutant suite"
                in str(scenario.get("remainingEvidenceGap"))
                and "Valid native and treatment repetitions remain at zero"
                in str(scenario.get("remainingEvidenceGap"))
                and "Formal Matt or Superpowers comparison is blocked"
                in str(scenario.get("remainingEvidenceGap"))
                and "offline injected-factory runner-preflight PoC"
                in str(scenario.get("remainingEvidenceGap"))
                and "one immutable authorization envelope"
                in str(scenario.get("remainingEvidenceGap"))
                and "not integrated with the formal runner"
                in str(scenario.get("remainingEvidenceGap"))
                and "current Matt projection is not the approved release payload"
                in str(scenario.get("remainingEvidenceGap"))
                and "Superpowers 6.2.0 is not a repository-approved release entry"
                in str(scenario.get("remainingEvidenceGap"))
                and "exact-candidate execution admission remains unsatisfied"
                in str(scenario.get("remainingEvidenceGap"))
                and "static audit admits or rejects neither candidate"
                in str(scenario.get("remainingEvidenceGap"))
                and "not current live runtime enforcement"
                in str(scenario.get("remainingEvidenceGap"))
                and "not integrated with the formal runner or a real app-server factory"
                in str(scenario.get("remainingEvidenceGap"))
                and "protocol-eligibility gate"
                in str(scenario.get("remainingEvidenceGap"))
                and "accepted admission is synthetic test data"
                in str(scenario.get("remainingEvidenceGap"))
                and "injected fake factory observes a prior reservation against the protocol-selected ledger"
                in str(scenario.get("remainingEvidenceGap"))
                and "wrapper exposes no caller-selected ledger path"
                in str(scenario.get("remainingEvidenceGap"))
                and "explicit construction-succeeded event"
                in str(scenario.get("remainingEvidenceGap"))
                and "factory exception remains primary"
                in str(scenario.get("remainingEvidenceGap"))
                and "Manual retain-consumed-no-retry reconciliation is unit-tested"
                in str(scenario.get("remainingEvidenceGap"))
                and "required injected structured handle validator"
                in str(scenario.get("remainingEvidenceGap"))
                and "same-process registered resources once in LIFO order"
                in str(scenario.get("remainingEvidenceGap"))
                and "reserved-without-construction-outcome"
                in str(scenario.get("remainingEvidenceGap"))
                and "protocol-selected-ledger-local rather than system-global"
                in str(scenario.get("remainingEvidenceGap"))
                and "no live ledger authority is configured"
                in str(scenario.get("remainingEvidenceGap"))
                and "live source-snapshot-to-factory materialization freshness"
                in str(scenario.get("remainingEvidenceGap"))
                and "real app-server handle adapter"
                in str(scenario.get("remainingEvidenceGap"))
                and "real child-process or socket cleanup"
                in str(scenario.get("remainingEvidenceGap"))
                and "cross-process exactly-once cleanup"
                in str(scenario.get("remainingEvidenceGap"))
                and "executable hidden oracle"
                in str(scenario.get("remainingEvidenceGap"))
                and _text(scenario.get("remainingEvidenceGap")),
                f"Implementation scenario evidence was overclaimed or drifted: {scenario_id}",
            )
        elif scenario_id == "GEN-RESEARCH-01":
            _require(
                scenario.get("evidenceState")
                == (
                    "bounded-synthetic-v2-source-backed-smoke-pass-"
                    "no-topology-comparison"
                )
                and scenario.get("protocolEvidence")
                == "registry/human-ai-collaboration-comparative-protocol-batch-01-2026-07-24.json"
                and scenario.get("liveEvidence")
                == [
                    "registry/human-ai-collaboration-read-only-claim-live-comparison-2026-07-26.json",
                    (
                        "registry/human-ai-collaboration-process-fidelity-v1-"
                        "calibration-abort-2026-07-27.json"
                    ),
                    (
                        "registry/human-ai-collaboration-process-fidelity-v2-"
                        "source-backed-smoke-evidence-2026-07-27.json"
                    ),
                ]
                and scenario.get("measurementCalibrationEvidence")
                == (
                    "registry/human-ai-collaboration-process-fidelity-"
                    "chained-trace-measurement-calibration-2026-07-27.json"
                )
                and scenario.get("rawEventTraceEligibilityEvidence")
                == (
                    "registry/human-ai-collaboration-process-fidelity-raw-"
                    "event-trace-eligibility-assessment-2026-07-27.json"
                )
                and scenario.get("chainedTransformTrialProtocol")
                == (
                    "registry/human-ai-collaboration-process-fidelity-chained-"
                    "transform-trial-protocol-2026-07-27.json"
                )
                and scenario.get("chainedTransformTrialProtocolV2Amendment")
                == (
                    "registry/human-ai-collaboration-process-fidelity-chained-"
                    "transform-trial-protocol-v2-amendment-2026-07-27.json"
                )
                and scenario.get("chainedTransformPacketPreflight")
                == (
                    "registry/human-ai-collaboration-process-fidelity-chained-"
                    "transform-packet-preflight-2026-07-27.json"
                )
                and scenario.get("chainedTransformAdapterEvaluatorPocEvidence")
                == (
                    "registry/human-ai-collaboration-process-fidelity-chained-"
                    "transform-adapter-evaluator-poc-evidence-2026-07-27.json"
                )
                and scenario.get("cumulativeLossAccountingPocEvidence")
                == (
                    "registry/human-ai-collaboration-process-fidelity-"
                    "cumulative-loss-accounting-poc-evidence-2026-07-27.json"
                )
                and scenario.get("softwareLifecycleThinSliceProtocol")
                == (
                    "registry/human-ai-collaboration-software-lifecycle-"
                    "thin-slice-protocol-2026-07-27.json"
                )
                and scenario.get(
                    "softwareLifecycleThinSliceZeroModelCalibrationEvidence"
                )
                == (
                    "registry/human-ai-collaboration-software-lifecycle-"
                    "thin-slice-zero-model-calibration-evidence-2026-07-27.json"
                )
                and scenario.get("chainedTransformDispatchGateContract")
                == (
                    "registry/human-ai-collaboration-process-fidelity-chained-"
                    "transform-dispatch-gate-contract-2026-07-27.json"
                )
                and scenario.get("chainedTransformDispatchLedgerContract")
                == (
                    "registry/human-ai-collaboration-process-fidelity-chained-"
                    "transform-dispatch-ledger-contract-2026-07-27.json"
                )
                and "HR-05-reversibility-recovery-and-continuity"
                in scenario.get("hardRequirementIds", [])
                and "public contract did not uniquely define"
                in str(scenario.get("observedResult"))
                and "remaining v1 tasks were cancelled"
                in str(scenario.get("observedResult"))
                and "one absolute-task-valid transport repetition out of three required"
                in str(scenario.get("observedResult"))
                and "records zero formal process runs"
                in str(scenario.get("observedResult"))
                and "liveDispatchReady=false"
                in str(scenario.get("observedResult"))
                and "zero-model sequential artifact adapter"
                in str(scenario.get("observedResult"))
                and "additive parent-recomputed cumulative-loss accounting PoC"
                in str(scenario.get("observedResult"))
                and "stayed 6 rather than being double-counted or erased"
                in str(scenario.get("observedResult"))
                and "separated requested route, host-effective route"
                in str(scenario.get("observedResult"))
                and "same-host cross-process one-shot ledger"
                in str(scenario.get("observedResult"))
                and "formal process cohort remains at zero"
                in str(scenario.get("observedResult"))
                and "No live chained-transform run"
                in str(scenario.get("remainingEvidenceGap"))
                and "human-to-source or terminal-to-human accountable edge"
                in str(scenario.get("remainingEvidenceGap"))
                and "live cross-boundary cumulative-loss budget"
                in str(scenario.get("remainingEvidenceGap")),
                f"Research scenario evidence was overclaimed or drifted: {scenario_id}",
            )
        elif scenario_id == "SE-ARCH-DESIGN-01":
            _require(
                scenario.get("evidenceState")
                == (
                    "zero-model-seeded-control-calibration-"
                    "no-live-agent-or-domain-evidence"
                )
                and scenario.get("calibrationEvidence")
                == (
                    "registry/human-ai-collaboration-software-lifecycle-"
                    "thin-slice-zero-model-calibration-evidence-2026-07-27.json"
                )
                and "rejects six controls"
                in str(scenario.get("observedResult"))
                and "no Skill was executed"
                in str(scenario.get("observedResult"))
                and "No live Agent proposal"
                in str(scenario.get("remainingEvidenceGap")),
                "Architecture scenario calibration evidence drifted",
            )
        elif scenario_id == "SE-VERIFY-SECURE-01":
            _require(
                scenario.get("evidenceState")
                == (
                    "zero-model-seeded-fault-calibration-"
                    "no-live-agent-or-domain-evidence"
                )
                and scenario.get("calibrationEvidence")
                == (
                    "registry/human-ai-collaboration-software-lifecycle-"
                    "thin-slice-zero-model-calibration-evidence-2026-07-27.json"
                )
                and "three predeclared synthetic faults"
                in str(scenario.get("observedResult"))
                and "zero of two benign canaries"
                in str(scenario.get("observedResult"))
                and "No live reviewer"
                in str(scenario.get("remainingEvidenceGap")),
                "Security scenario calibration evidence drifted",
            )
        elif scenario_id == "SE-MAINT-MIGRATE-01":
            _require(
                scenario.get("evidenceState")
                == "bounded-synthetic-live-agent-evidence-no-loader-causation-or-live-domain-evidence"
                and scenario.get("protocolEvidence")
                == "registry/human-ai-collaboration-maintenance-migration-protocol-batch-01-2026-07-24.json"
                and scenario.get("liveEvidence")
                == [
                    "registry/human-ai-collaboration-maintenance-migration-live-comparison-batch-01-2026-07-24.json"
                ]
                and "native 3/3"
                in str(scenario.get("observedResult"))
                and "CC deprecation-and-migration 1/3"
                in str(scenario.get("observedResult"))
                and "no independent loader event"
                in str(scenario.get("observedResult"))
                and _text(scenario.get("remainingEvidenceGap")),
                f"Migration scenario evidence was overclaimed or drifted: {scenario_id}",
            )
        else:
            _require(
                scenario.get("evidenceState")
                == "planned-no-live-domain-evidence",
                f"Scenario evidence was overclaimed: {scenario_id}",
            )
        affected = scenario.get("affectedSubjects")
        _require(isinstance(affected, list) and len(affected) >= 3, f"Scenario affected subjects are incomplete: {scenario_id}")
        axes = scenario.get("axisIds")
        _require(
            isinstance(axes, list)
            and len(axes) == len(set(axes))
            and set(axes) <= EXPECTED_AXES
            and len(axes) >= 7,
            f"Scenario axis projection is invalid: {scenario_id}",
        )
        axis_union.update(axes)
        slices = scenario.get("softwareLifecycleSlices")
        _require(isinstance(slices, list) and len(slices) == len(set(slices)), f"Scenario lifecycle slices are invalid: {scenario_id}")
        _require(set(slices) <= EXPECTED_LIFECYCLE_SLICES, f"Scenario lifecycle slice is unknown: {scenario_id}")
        _require((not slices) if is_general else bool(slices), f"Scenario general/software lifecycle boundary drifted: {scenario_id}")
        lifecycle_union.update(slices)
        _require(set(scenario.get("hostClassIds", [])) == EXPECTED_HOSTS, f"Scenario host comparison drifted: {scenario_id}")
        hard_ids = set(scenario.get("hardRequirementIds", []))
        _require(hard_ids <= EXPECTED_HARD_REQUIREMENTS and len(hard_ids) >= 5, f"Scenario hard requirement mapping is invalid: {scenario_id}")
        _require(
            scenario.get("crossCuttingRiskIds")
            == ["XCR-01-process-fidelity-and-loss"],
            f"Scenario lost process-fidelity binding: {scenario_id}",
        )
        _require(
            {
                "HR-01-goal-and-acceptance",
                "HR-02-truth-provenance-and-uncertainty",
                "HR-03-authority-data-and-least-privilege",
                "HR-06-human-decision-and-accountability",
            }
            <= hard_ids,
            f"Scenario lost core mandatory gates: {scenario_id}",
        )
        _require(scenario.get("routeApplicability") == ["N", "O", "E", "C", "H", "R"], f"Scenario route order drifted: {scenario_id}")
        for key in ("acceptanceSignals", "evidenceNeeded", "forbiddenClaims"):
            values = scenario.get(key)
            _require(isinstance(values, list) and len(values) >= 3, f"Scenario {key} is incomplete: {scenario_id}")
    _require(axis_union == EXPECTED_AXES, "Scenario matrix does not structurally sample every mother-framework axis")
    _require(
        lifecycle_union == EXPECTED_LIFECYCLE_SLICES,
        "Scenario matrix does not structurally sample every software lifecycle slice",
    )

    lanes = _index(document.get("existingNarrowEvidenceLinks"), "lane", "Narrow evidence links")
    _require(set(lanes) == EXPECTED_LANES, "Narrow evidence lane set drifted")
    for item in lanes.values():
        _require(
            item.get("path") == "docs/strategy/POC-SCENARIO-EVIDENCE-MATRIX.md",
            "Narrow evidence path drifted",
        )
        _require(_text(item.get("state")) and _text(item.get("claimLimit")), "Narrow evidence boundary is incomplete")

    projection = document.get("coverageProjection")
    _require(isinstance(projection, dict), "Scenario matrix coverage projection is missing")
    _require(projection.get("generalScenarioCount") == 5, "General scenario count drifted")
    _require(projection.get("softwareEngineeringScenarioCount") == 8, "Software scenario count drifted")
    _require(projection.get("motherFrameworkAxisSampleCount") == 9, "Axis sample count drifted")
    _require(projection.get("softwareLifecycleSliceSampleCount") == 14, "Lifecycle sample count drifted")
    bounded_synthetic_slices: set[str] = set()
    zero_model_calibrated_slices: set[str] = set()
    planned_slices: set[str] = set()
    for scenario in scenarios.values():
        slices = set(scenario.get("softwareLifecycleSlices", []))
        if not slices:
            continue
        evidence_state = str(scenario.get("evidenceState", ""))
        if evidence_state.startswith("bounded-synthetic-live-agent-evidence-"):
            bounded_synthetic_slices.update(slices)
        elif evidence_state.startswith("zero-model-"):
            zero_model_calibrated_slices.update(slices)
        elif evidence_state == "planned-no-live-domain-evidence":
            planned_slices.update(slices)
        else:
            raise RuntimeError(
                "Software lifecycle evidence grade is not classified: "
                f"{scenario.get('id')}"
            )
    grade_counts = projection.get("softwareLifecycleEvidenceGradeCounts")
    _require(
        grade_counts
        == {
            "namedOrSampled": 14,
            "boundedSyntheticAgent": 8,
            "zeroModelCalibrated": 4,
            "plannedOnly": 2,
            "liveDomain": 0,
        },
        "Software lifecycle evidence-grade counts drifted",
    )
    grade_records = _index(
        projection.get("softwareLifecycleEvidenceGrades"),
        "grade",
        "Software lifecycle evidence grades",
    )
    bounded_record = grade_records.get(
        "bounded-synthetic-agent-no-live-domain"
    )
    zero_model_record = grade_records.get(
        "zero-model-calibrated-no-live-agent-or-domain"
    )
    planned_record = grade_records.get("planned-no-live-domain")
    bounded_declared = (
        bounded_record.get("sliceIds")
        if isinstance(bounded_record, dict)
        else None
    )
    zero_model_declared = (
        zero_model_record.get("sliceIds")
        if isinstance(zero_model_record, dict)
        else None
    )
    planned_declared = (
        planned_record.get("sliceIds")
        if isinstance(planned_record, dict)
        else None
    )
    _require(
        set(grade_records)
        == {
            "bounded-synthetic-agent-no-live-domain",
            "zero-model-calibrated-no-live-agent-or-domain",
            "planned-no-live-domain",
        }
        and isinstance(bounded_declared, list)
        and isinstance(zero_model_declared, list)
        and isinstance(planned_declared, list)
        and len(bounded_declared) == len(set(bounded_declared))
        and len(zero_model_declared) == len(set(zero_model_declared))
        and len(planned_declared) == len(set(planned_declared))
        and set(bounded_declared) == bounded_synthetic_slices
        and set(zero_model_declared) == zero_model_calibrated_slices
        and set(planned_declared) == planned_slices
        and grade_counts["boundedSyntheticAgent"]
        == len(bounded_synthetic_slices)
        and grade_counts["zeroModelCalibrated"]
        == len(zero_model_calibrated_slices)
        and grade_counts["plannedOnly"] == len(planned_slices)
        and grade_counts["namedOrSampled"]
        == len(
            bounded_synthetic_slices
            | zero_model_calibrated_slices
            | planned_slices
        )
        and grade_counts["liveDomain"] == 0
        and bounded_synthetic_slices.isdisjoint(planned_slices)
        and bounded_synthetic_slices.isdisjoint(
            zero_model_calibrated_slices
        )
        and zero_model_calibrated_slices.isdisjoint(planned_slices)
        and (
            bounded_synthetic_slices
            | zero_model_calibrated_slices
            | planned_slices
        )
        == EXPECTED_LIFECYCLE_SLICES,
        "Software lifecycle evidence-grade partition drifted",
    )
    _require(
        projection.get("evidenceCoverageStatus") == "open-no-live-domain-scenario-evidence",
        "Scenario evidence coverage was overclaimed",
    )
    _require(
        isinstance(projection.get("unassessedDimensions"), list)
        and len(projection["unassessedDimensions"]) >= 7,
        "Scenario matrix unassessed dimensions are incomplete",
    )
    _require(_text(projection.get("nextBatchRule")), "Scenario matrix next-batch rule is missing")

    decision = document.get("decision")
    _require(isinstance(decision, dict), "Scenario matrix decision is missing")
    _require(decision.get("scenarioContractReadyForReview") is True, "Scenario contract readiness drifted")
    for key in (
        "liveDomainScenarioEvidenceClaimed",
        "wholeHumanAiCoverageClaimed",
        "softwareLifecycleCoverageClaimed",
        "endToEndProcessFidelityClaimed",
        "residualCapabilityGapClaimed",
        "repositoryAuthoringJustified",
        "hardStandardPromotionAuthorized",
    ):
        _require(decision.get(key) is False, f"Scenario matrix decision overclaimed: {key}")
    _require(_text(decision.get("nextBoundedResult")), "Scenario matrix next bounded result is missing")

    _require(document.get("documentation") == MATRIX_DOC_PATH, "Scenario matrix documentation path drifted")
    doc_path = root / MATRIX_DOC_PATH
    _require(doc_path.is_file(), "Scenario matrix documentation is missing")
    doc = " ".join(doc_path.read_text(encoding="utf-8").split())
    for phrase in (
        "counts are navigation data, not completion targets",
        "does not prove whole-domain or full-lifecycle coverage",
        "Hard requirements are compulsory outcome and evidence gates",
        "A planned scenario is not evidence",
        "Cross-cutting process fidelity",
        "eight slices have bounded synthetic Agent evidence",
        "four have only zero-model calibration",
        "two open graduation subgates",
        "No installation, runtime mutation",
    ):
        _require(phrase in doc, f"Scenario matrix documentation boundary missing: {phrase}")

    initiatives = _index(program.get("currentInitiatives"), "id", "Program initiatives")
    initiative = initiatives.get("initiative.human-ai-collaboration-coverage-rebaseline")
    _require(initiative is not None, "Scenario matrix initiative is missing")
    _require(initiative.get("currentMatrixEvidence") == MATRIX_PATH, "Scenario matrix program binding drifted")

    criteria = _index(acceptance.get("acceptanceCriteria"), "id", "Acceptance criteria")
    for acceptance_id in ACCEPTANCE_IDS:
        item = criteria.get(acceptance_id)
        expected_assessment = (
            "verified"
            if acceptance_id == "acceptance.ai-independent-hard-standard-boundary"
            else "partial"
        )
        _require(item is not None and item.get("assessment") == expected_assessment, f"Scenario matrix acceptance state drifted: {acceptance_id}")
        expected_evidence_ids = [REBASELINE_EVIDENCE_ID, MATRIX_EVIDENCE_ID]
        if acceptance_id == "acceptance.solution-neutral-collaboration-rebaseline":
            expected_evidence_ids += [
                LEARNING_CAPABILITY_BASELINE_EVIDENCE_ID,
                CREATIVE_CAPABILITY_BASELINE_EVIDENCE_ID,
                ACCESS_COMMS_CAPABILITY_BASELINE_EVIDENCE_ID,
                CURRENT_CANDIDATE_COVERAGE_RECONCILIATION_EVIDENCE_ID,
                LEARNING_NORU_INDEPENDENT_REVIEW_READINESS_EVIDENCE_ID,
                SYSTEM_MANAGER_REFERENCE_COHORT_EVIDENCE_ID,
            ]
        if (
            acceptance_id
            == "acceptance.software-engineering-lifecycle-specialization"
        ):
            expected_evidence_ids += [
                RELEASE_CHANGE_PROTOCOL_EVIDENCE_ID,
                RELEASE_CHANGE_CURRENT_CC_CODEX_PREFLIGHT_EVIDENCE_ID,
                TDD_READINESS_EVIDENCE_ID,
                TDD_SUCCESSOR_CONTRACT_EVIDENCE_ID,
                AI_ERA_ENGINEERING_REVALIDATION_EVIDENCE_ID,
                MULTIDIMENSIONAL_ENGINEERING_EVALUATION_EVIDENCE_ID,
                MULTIDIMENSIONAL_ENGINEERING_SOURCE_SNAPSHOT_EVIDENCE_ID,
                ENGINEERING_MANAGEMENT_CALIBRATION_EVIDENCE_ID,
            ]
        if acceptance_id == "acceptance.ai-independent-hard-standard-boundary":
            expected_evidence_ids += [
                AI_ERA_ENGINEERING_REVALIDATION_EVIDENCE_ID,
                MULTIDIMENSIONAL_ENGINEERING_EVALUATION_EVIDENCE_ID,
                MULTIDIMENSIONAL_ENGINEERING_SOURCE_SNAPSHOT_EVIDENCE_ID,
                AI_INDEPENDENT_HARD_STANDARD_GATE_EVIDENCE_ID,
            ]
        if acceptance_id == "acceptance.end-to-end-process-fidelity":
            expected_evidence_ids += [
                "evidence.process-fidelity-multihop-injection-poc-2026-07-26",
                (
                    "evidence.human-ai-collaboration-process-fidelity-v1-"
                    "calibration-abort-2026-07-27"
                ),
                (
                    "evidence.human-ai-collaboration-process-fidelity-v2-"
                    "protocol-2026-07-27"
                ),
                (
                    "evidence.human-ai-collaboration-process-fidelity-v2-"
                    "source-backed-smoke-2026-07-27"
                ),
                (
                    "evidence.human-ai-collaboration-process-fidelity-"
                    "chained-trace-calibration-2026-07-27"
                ),
                (
                    "evidence.human-ai-collaboration-process-fidelity-"
                    "chained-transform-protocol-2026-07-27"
                ),
                (
                    "evidence.human-ai-collaboration-process-fidelity-"
                    "chained-transform-packet-preflight-2026-07-27"
                ),
                (
                    "evidence.human-ai-collaboration-process-fidelity-"
                    "chained-transform-adapter-evaluator-poc-2026-07-27"
                ),
                (
                    "evidence.human-ai-collaboration-process-fidelity-"
                    "cumulative-loss-accounting-poc-2026-07-27"
                ),
                (
                    "evidence.human-ai-collaboration-software-lifecycle-"
                    "thin-slice-zero-model-calibration-2026-07-27"
                ),
                (
                    "evidence.human-ai-collaboration-process-fidelity-"
                    "chained-transform-dispatch-gate-contract-2026-07-27"
                ),
                (
                    "evidence.human-ai-collaboration-process-fidelity-"
                    "chained-transform-dispatch-ledger-contract-2026-07-27"
                ),
                (
                    "evidence.human-ai-collaboration-process-fidelity-"
                    "chained-transform-v2-amendment-2026-07-27"
                ),
                (
                    "evidence.human-ai-collaboration-process-fidelity-"
                    "raw-event-trace-eligibility-2026-07-27"
                ),
                (
                    "evidence.context-handoff-receiver-delta-ledger-"
                    "2026-07-27"
                ),
                ACCESS_COMMS_CALIBRATION_EVIDENCE_ID,
                ORG_DECISION_CALIBRATION_EVIDENCE_ID,
                ENGINEERING_MANAGEMENT_CALIBRATION_EVIDENCE_ID,
                (
                    "evidence.human-ai-collaboration-semantic-authority-"
                    "layer-reconciliation-2026-07-28"
                ),
                SEMANTIC_AUTHORITY_CONTINUITY_EVIDENCE_ID,
                CURRENT_MATT_EXPOSURE_REFRESH_EVIDENCE_ID,
                NATIVE_LOCAL_EXPOSURE_ORACLE_EVIDENCE_ID,
                SEMANTIC_EXECUTION_PLAN_PREFLIGHT_EVIDENCE_ID,
                SEMANTIC_RUNTIME_ADAPTER_PREFLIGHT_EVIDENCE_ID,
                SEMANTIC_LIVE_ADAPTER_DECISION_EVIDENCE_ID,
                SEMANTIC_LIVE_DISPATCH_GATE_PREFLIGHT_EVIDENCE_ID,
                MULTIDIMENSIONAL_ENGINEERING_EVALUATION_EVIDENCE_ID,
                MULTIDIMENSIONAL_ENGINEERING_SOURCE_SNAPSHOT_EVIDENCE_ID,
                LONGHORIZON_STATIC_REUSE_ASSESSMENT_EVIDENCE_ID,
                LONGHORIZON_INTERFACE_GAP_MAPPING_EVIDENCE_ID,
                LONGHORIZON_EXECUTION_PREFLIGHT_EVIDENCE_ID,
            ]
        _require(
            item.get("evidenceIds") == expected_evidence_ids,
            f"Scenario matrix acceptance evidence mapping drifted: {acceptance_id}",
        )
    evidence = _index(acceptance.get("evidence"), "id", "Acceptance evidence")
    matrix_evidence = evidence.get(MATRIX_EVIDENCE_ID)
    _require(matrix_evidence is not None, "Scenario matrix acceptance evidence is missing")
    _require(matrix_evidence.get("path") == MATRIX_PATH, "Scenario matrix acceptance evidence path drifted")
    _require(set(matrix_evidence.get("supports", [])) == ACCEPTANCE_IDS, "Scenario matrix support set drifted")


def _load(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    _require(isinstance(value, dict), f"Expected JSON object: {path}")
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    root = args.root.resolve()
    validate_matrix(
        _load(root / MATRIX_PATH),
        _load(root / REBASELINE_PATH),
        _load(root / "registry/curation-program-plan.json"),
        _load(root / "registry/program-acceptance-map.json"),
        root=root,
    )
    print("human-AI collaboration scenario-evidence matrix batch 01: valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
