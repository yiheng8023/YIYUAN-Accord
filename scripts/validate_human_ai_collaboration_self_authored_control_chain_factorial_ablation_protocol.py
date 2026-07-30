#!/usr/bin/env python3
"""Validate the self-authored control-chain factorial ablation protocol."""

from __future__ import annotations

import json
from pathlib import Path

try:
    from scripts.evaluate_human_ai_collaboration_self_authored_control_chain_factorial_evidence import (
        validate_adapter_contract,
    )
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from evaluate_human_ai_collaboration_self_authored_control_chain_factorial_evidence import (
        validate_adapter_contract,
    )


ROOT = Path(__file__).resolve().parent.parent
PROTOCOL_PATH = Path(
    "registry/human-ai-collaboration-self-authored-control-chain-"
    "factorial-ablation-protocol-2026-07-28.json"
)
AUDIT_PATH = Path(
    "registry/human-ai-collaboration-self-authored-control-chain-"
    "carrier-audit-2026-07-28.json"
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _index(rows: list[dict], key: str, label: str) -> dict[str, dict]:
    indexed = {str(row.get(key)): row for row in rows if isinstance(row, dict)}
    _require(len(indexed) == len(rows), f"{label} identities drifted")
    return indexed


def validate_protocol(document: dict, *, root: Path = ROOT) -> None:
    _require(
        document.get("schema") == 1
        and document.get("status")
        == "preregistered-offline-factorial-ablation-no-live-run",
        "Factorial protocol identity drifted",
    )

    expected_sources = {
        "carrierAudit": str(AUDIT_PATH).replace("\\", "/"),
        "overlapMatrix": (
            "registry/skill-ecosystem-overlap-and-ablation-matrix-2026-07-23.json"
        ),
        "scenarioPackets": (
            "tests/fixtures/skill-overlap-scenario-packets-2026-07-23.json"
        ),
        "baseLiveEvidenceContract": (
            "registry/skill-live-run-evidence-contract-2026-07-23.json"
        ),
        "baseLiveEvaluator": "scripts/evaluate_skill_live_run_evidence.py",
        "instructionCarrierContract": (
            "registry/instruction-carrier-adherence-contract-2026-07-23.json"
        ),
        "contextPressureEnvelope": (
            "registry/context-pressure-provenance-evidence-envelope-2026-07-24.json"
        ),
    }
    sources = document.get("sourceBindings", {})
    _require(sources == expected_sources, "Factorial source bindings drifted")
    for relative in sources.values():
        _require((root / relative).is_file(), f"Factorial source missing: {relative}")

    scenarios = _index(
        document.get("scenarioSelection", []), "scenarioId", "Scenario"
    )
    expected_scenario_skills = {
        "INT-AMB-01": "intent-contract",
        "ROUTE-MIN-01": "capability-router",
        "CLOSE-PRESS-01": "closure-contract",
    }
    _require(
        {
            scenario_id: row.get("expectedRelevantSkill")
            for scenario_id, row in scenarios.items()
        }
        == expected_scenario_skills
        and all(len(row.get("criticalFalsifiers", [])) >= 3 for row in scenarios.values()),
        "Factorial scenario selection drifted",
    )
    packet_fixture = json.loads(
        (root / sources["scenarioPackets"]).read_text(encoding="utf-8")
    )
    packet_scenarios = {
        str(row.get("scenarioId"))
        for row in packet_fixture.get("fixtures", [])
        if isinstance(row, dict)
    }
    _require(
        set(scenarios).issubset(packet_scenarios),
        "Factorial scenario packet binding drifted",
    )

    held = document.get("heldConstant", {})
    _require(
        held.get("hardStandardsEnabledEveryCell") is True
        and held.get("hardStandardsCreditedAsTreatmentValue") is False
        and all(
            held.get(key) is True
            for key in (
                "samePublicPacketBytesWithinScenarioBlock",
                "samePrivateOracleWithinScenarioBlock",
                "sameRequestedModelAndReasoning",
                "sameSandboxAndAuthorityEnvelope",
                "sameUnselectedCapabilityIsolation",
                "repositoryHeadAndDirtyBaselineParentObserved",
            )
        ),
        "Factorial held-constant boundary drifted",
    )

    factors = document.get("factors", {})
    chain = factors.get("chain", {})
    hook = factors.get("hook", {})
    chain_levels = _index(chain.get("levels", []), "id", "Chain level")
    hook_levels = _index(hook.get("levels", []), "id", "Hook level")
    _require(
        chain.get("independentVariable") is True
        and set(chain_levels) == {"hard-only", "exact-current-three-skill-chain"}
        and hook.get("independentVariable") is True
        and set(hook_levels) == {"off", "auto"},
        "Factorial independent-variable design drifted",
    )
    _require(
        chain_levels["hard-only"].get("taskScopedExposedSkillIdentities") == []
        and chain_levels["hard-only"].get("selectedSkillLoaderEventsAllowed")
        is False,
        "Hard-only isolation drifted",
    )
    exact_level = chain_levels["exact-current-three-skill-chain"]
    _require(
        exact_level.get("taskScopedExposedSkillIdentities")
        == ["intent-contract", "capability-router", "closure-contract"]
        and exact_level.get(
            "selectedSkillLoaderEventRequiredForScenarioRelevantSkill"
        )
        is True
        and exact_level.get("unrelatedSkillLoaderEventCreditedAsValue") is False,
        "Exact-chain treatment drifted",
    )

    audit = json.loads((root / AUDIT_PATH).read_text(encoding="utf-8"))
    audited_skills = {
        row["name"]: (row["currentBytes"], row["currentSha256"])
        for row in audit["currentCarrierObservation"]["skills"]
    }
    protocol_pins = {
        row["name"]: (row["bytes"], row["sha256"])
        for row in chain.get("exactSkillPins", [])
    }
    _require(
        protocol_pins == audited_skills == {
            "intent-contract": (
                29139,
                "1d67e4b84856bcd0828d89b82803a7275d95d8e586fd8efcd127f89e82845753",
            ),
            "capability-router": (
                22018,
                "eb9f7d253d12682a3e8b9f87faf5bad4284a2d268b25c30cc5ad9f6dd36eb8fe",
            ),
            "closure-contract": (
                12187,
                "59edfc131c45b7aa1ef85a1737317a0cc97adcfb0ddceb7ee81e9c744b13bbb3",
            ),
        },
        "Exact Skill pins drifted from carrier audit",
    )
    audited_dependencies = {
        (row["skillName"], row["relativePath"]): (
            row["currentBytes"],
            row["currentSha256"],
        )
        for row in audit["currentCarrierObservation"]["currentPackageDependencies"]
    }
    protocol_dependencies = {
        (row["skillName"], row["relativePath"]): (
            row["bytes"],
            row["sha256"],
        )
        for row in chain.get("exactDependencyPins", [])
    }
    _require(
        protocol_dependencies == audited_dependencies == {
            ("intent-contract", "references/intake-contract.md"): (
                20948,
                "66e3990e36f3771c5bd22136834100b7aba799c6416968f486e5929204392b93",
            ),
            ("capability-router", "references/routing-contract.md"): (
                10108,
                "17d7ef3892f2794f78321615f276d89e5040059b6bf49793c2edebbfe5e90c3b",
            ),
        },
        "Exact Skill dependency pins drifted from carrier audit",
    )

    hook_observation = audit["hookObservation"]
    hook_pins = hook.get("exactPins", {})
    _require(
        hook_pins
        == {
            "registrationSha256": hook_observation["registrationSha256"],
            "handlerSha256": hook_observation["handlerSha256"],
            "policySha256": hook_observation["policySha256"],
        },
        "Hook pins drifted from carrier audit",
    )
    off = hook_levels["off"]
    auto = hook_levels["auto"]
    _require(
        off.get("hookRegistrationExposed") is False
        and off.get("hookTriggerEventAllowed") is False
        and off.get("expectedAdditionalContextBytes") == 0
        and auto.get("hookRegistrationExposed") is True
        and auto.get("hookTriggerEventRequired") is True
        and auto.get("event") == "UserPromptSubmit"
        and auto.get("action") == "advisory-context-injection"
        and auto.get("mayDeny") is False
        and auto.get("mayMutateExternalState") is False
        and auto.get("handlerFailure") == "fail-open-with-evidence",
        "Hook treatment boundary drifted",
    )
    isolation = hook.get("isolationBoundary", {})
    _require(
        isolation.get("liveUserHookConfigurationMutationAllowed") is False
        and isolation.get(
            "disposableIsolatedProfileOrParentControlledEquivalentRequired"
        )
        is True
        and isolation.get("currentRegistrationUsedAsDatedIdentityOnly") is True,
        "Hook isolation boundary drifted",
    )

    cells = _index(document.get("factorialCells", []), "id", "Factorial cell")
    observed_cells = {
        (row.get("chain"), row.get("hook")) for row in cells.values()
    }
    _require(
        set(cells)
        == {
            "CHAIN-HARD-HOOK-OFF",
            "CHAIN-HARD-HOOK-AUTO",
            "CHAIN-EXACT-HOOK-OFF",
            "CHAIN-EXACT-HOOK-AUTO",
        }
        and observed_cells
        == {
            ("hard-only", "off"),
            ("hard-only", "auto"),
            ("exact-current-three-skill-chain", "off"),
            ("exact-current-three-skill-chain", "auto"),
        },
        "Factorial cell coverage drifted",
    )

    model = document.get("modelPolicy", {})
    _require(
        model.get("requestedModel") == "gpt-5.3-codex-spark"
        and model.get("requestedReasoningEffort") == "low"
        and model.get("actualModelAndReasoningMustBeParentObserved") is True
        and model.get("silentModelSubstitutionAllowed") is False
        and model.get("unavailableRequestedRouteOutcome")
        == "invalid-environment-run-do-not-score"
        and model.get("strongerModelDiagnosticCountsTowardWeakAgentAcceptance")
        is False,
        "Factorial model route drifted",
    )

    envelope = document.get("evidenceEnvelope", {})
    aggregate = envelope.get("pairedBlockAggregation", {})
    _require(
        envelope.get("minimumIndependentRunsPerScenarioCell") == 3
        and envelope.get("totalValidRunsRequired") == 36
        and set(envelope.get("distinctPerRun", []))
        == {"runId", "taskId", "hostRunId", "hostThreadId"}
        and len(envelope.get("parentObservedRequired", [])) == 11
        and len(envelope.get("directionalMeasures", [])) == 9
        and aggregate.get("chainMainEffectComparedAcrossMatchedHookLevels") is True
        and aggregate.get("hookMainEffectComparedAcrossMatchedChainLevels") is True
        and aggregate.get("interactionReportedSeparately") is True
        and aggregate.get("singleRunWinnerAllowed") is False,
        "Factorial evidence envelope drifted",
    )

    fallback = document.get("failureFallbackProbe", {})
    _require(
        fallback.get("separateFromScoredWeakModelCells") is True
        and fallback.get("zeroModelInjectedHandlerFailureRequiredBeforeLiveRun")
        is True
        and fallback.get("liveUserHookConfigurationMutationAllowed") is False
        and fallback.get("failureProbeCountsAsHookValue") is False,
        "Factorial failure-fallback boundary drifted",
    )
    _require(
        len(document.get("attributionRules", [])) == 7,
        "Factorial attribution rules drifted",
    )

    gate = document.get("executionAdmission", {})
    _require(
        gate.get("protocolAndFactorialCellsFrozen") is True
        and gate.get("existingPacketsAndOraclesReused") is True
        and gate.get("factorialEvidenceAdapterImplemented") is True
        and gate.get("isolatedHookModeHarnessImplemented") is True
        and gate.get("zeroModelFailureFallbackProbePassed") is True
        and gate.get("hookModePreflightEvidenceValidated") is True
        and gate.get("dependencyCompleteProjectionImplemented") is True
        and gate.get("projectionBuilderFaultTestsPass") is True
        and gate.get("taskScopedFourCellExposureProved") is True
        and gate.get("currentHostObservabilityAdmissionRecorded") is True
        and all(
            gate.get(key) is False
            for key in (
                "baseLiveEvaluatorUnderstandsHookFactor",
                "independentScenarioRelevantSkillLoaderEventAvailable",
                "noModelHostHookConsumptionProved",
                "liveWeakModelRunAuthorizedByThisRecord",
                "admittedForLiveExecution",
            )
        ),
        "Factorial execution admission overclaimed",
    )
    validate_adapter_contract(protocol=document)
    preflight = document.get("preflightEvidence")
    _require(
        preflight
        == (
            "audits/human-ai-collaboration-self-authored-control-chain-hook-"
            "mode-preflight-2026-07-28/REPORT.json"
        )
        and (root / preflight).is_file(),
        "Factorial preflight evidence binding drifted",
    )
    four_cell = document.get("fourCellExposureEvidence")
    _require(
        four_cell
        == (
            "audits/human-ai-collaboration-self-authored-control-chain-four-"
            "cell-exposure-2026-07-28/REPORT.json"
        )
        and (root / four_cell).is_file(),
        "Factorial four-cell evidence binding drifted",
    )
    observability = document.get("loaderHookObservabilityAdmission")
    _require(
        observability
        == (
            "registry/human-ai-collaboration-self-authored-control-chain-"
            "loader-hook-observability-admission-2026-07-28.json"
        )
        and (root / observability).is_file(),
        "Factorial observability admission binding drifted",
    )
    authority = document.get("authorityBoundary", {})
    _require(
        authority
        and all(value is False for value in authority.values()),
        "Factorial authority expanded",
    )
    decision = document.get("decisionBoundary", {})
    _require(
        decision
        and all(value is False for value in decision.values()),
        "Factorial decision boundary overclaimed",
    )

    documentation = document.get("documentation")
    _require(
        documentation
        == (
            "docs/strategy/HUMAN-AI-COLLABORATION-SELF-AUTHORED-CONTROL-"
            "CHAIN-FACTORIAL-ABLATION-PROTOCOL-2026-07-28.md"
        )
        and (root / documentation).is_file(),
        "Factorial documentation binding drifted",
    )


def main() -> int:
    document = json.loads((ROOT / PROTOCOL_PATH).read_text(encoding="utf-8"))
    validate_protocol(document, root=ROOT)
    print(
        "human-AI collaboration self-authored control-chain factorial "
        "ablation protocol verified"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
