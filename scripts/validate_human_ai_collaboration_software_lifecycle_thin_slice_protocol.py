#!/usr/bin/env python3
"""Validate the preregistered seven-stage software lifecycle thin slice."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
PROTOCOL_PATH = (
    "registry/"
    "human-ai-collaboration-software-lifecycle-thin-slice-protocol-"
    "2026-07-27.json"
)
EXPECTED_STAGE_ORDER = [
    "SE-TS-01-requirements-domain",
    "SE-TS-02-architecture-design",
    "SE-TS-03-implementation-tdd",
    "SE-TS-04-independent-review-test-security",
    "SE-TS-05-release-rollback-gating",
    "SE-TS-06-observation-incident-handling",
    "SE-TS-07-maintenance-evolution",
]
EXPECTED_STAGE_CLASSES = [
    "requirements-domain",
    "architecture-design",
    "implementation-tdd",
    "independent-review-test-security",
    "release-rollback-gating",
    "observation-incident-handling",
    "maintenance-evolution",
]
EXPECTED_GATES = [
    "G0-source-scope-authority",
    "G1-requirements-decision",
    "G2-architecture-security-decision",
    "G3-implementation-mutation-envelope",
    "G4-independent-acceptance-and-risk-decision",
    "G5-simulated-release-and-rollback-decision",
    "G6-simulated-fault-and-recovery-decision",
    "G7-maintenance-deprecation-decision",
]
EXPECTED_CLAIM_KEYS = {
    "provesLiveAgentBehavior",
    "provesHumanDecisionQuality",
    "provesProductionReadiness",
    "provesRealReleaseOrDeployment",
    "provesRemoteGitOrCi",
    "provesDynamicMcpLifecycle",
    "provesCandidateSkillDeliveryCausationPreferenceOrValue",
    "provesSelfAuthoredResidualGap",
    "provesCrossHostPortability",
    "provesAutomaticThreadCreationCompressionOrHandoffInvocation",
    "provesAllLifecycleSlices",
    "provesGeneralSoftwareEngineeringCompetence",
    "provesHumanAuthorityWhenReceiptsAreSimulated",
    "provesLosslessEndToEndProcess",
    "authorizesGitDeploymentMcpCandidateSkillPortfolioOrCleanupMutation",
}
EXPECTED_SCHEMA_BINDINGS = {
    "stageEnvelopeSchema": (
        "schemas/software-lifecycle-stage-envelope-v1.schema.json",
        "https://example.invalid/agent-autonomy-harness/"
        "software-lifecycle-stage-envelope-v1.schema.json",
    ),
    "acceptedInvariantLedgerSchema": (
        "schemas/software-lifecycle-accepted-invariant-ledger-v1.schema.json",
        "https://example.invalid/agent-autonomy-harness/"
        "software-lifecycle-accepted-invariant-ledger-v1.schema.json",
    ),
    "humanAuthorityReceiptSchema": (
        "schemas/software-lifecycle-human-authority-receipt-v1.schema.json",
        "https://example.invalid/agent-autonomy-harness/"
        "software-lifecycle-human-authority-receipt-v1.schema.json",
    ),
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_json_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    _require(isinstance(value, dict), f"JSON object required: {path}")
    return value


def _unique_nonempty_strings(value: Any) -> bool:
    return (
        isinstance(value, list)
        and all(isinstance(item, str) and item for item in value)
        and len(value) == len(set(value))
    )


def _assert_strict_object_schemas(value: Any, *, location: str) -> None:
    if isinstance(value, dict):
        type_value = value.get("type")
        is_object_schema = type_value == "object" or (
            isinstance(type_value, list) and "object" in type_value
        )
        if is_object_schema:
            _require(
                value.get("additionalProperties") is False,
                f"Object schema is not closed: {location}",
            )
            _require(
                _unique_nonempty_strings(value.get("required")),
                f"Object schema lacks an exact required surface: {location}",
            )
        for key, child in value.items():
            _assert_strict_object_schemas(
                child,
                location=f"{location}/{key}",
            )
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _assert_strict_object_schemas(
                child,
                location=f"{location}/{index}",
            )


def _validate_schema_bindings(
    document: dict[str, Any],
    *,
    root: Path,
    schemas: dict[str, dict[str, Any]] | None,
) -> None:
    bindings = document.get("contractBindings")
    _require(
        isinstance(bindings, dict)
        and set(bindings) == set(EXPECTED_SCHEMA_BINDINGS),
        "Lifecycle protocol schema binding set drifted",
    )
    for key, (expected_path, expected_id) in EXPECTED_SCHEMA_BINDINGS.items():
        binding = bindings[key]
        _require(
            isinstance(binding, dict)
            and set(binding) == {"path", "fileSha256"}
            and binding.get("path") == expected_path,
            f"Lifecycle schema binding shape drifted: {key}",
        )
        path = root / expected_path
        _require(path.is_file(), f"Lifecycle schema is missing: {key}")
        _require(
            binding.get("fileSha256") == _file_sha256(path),
            f"Lifecycle schema hash drifted: {key}",
        )
        schema = (
            schemas[key]
            if schemas is not None and key in schemas
            else _read_json_object(path)
        )
        _require(
            schema.get("$schema")
            == "https://json-schema.org/draft/2020-12/schema"
            and schema.get("$id") == expected_id
            and schema.get("type") == "object"
            and schema.get("additionalProperties") is False,
            f"Lifecycle schema identity drifted: {key}",
        )
        _assert_strict_object_schemas(schema, location=key)


def validate_protocol(
    document: dict[str, Any],
    *,
    root: Path = ROOT,
    schemas: dict[str, dict[str, Any]] | None = None,
) -> None:
    _require(
        document.get("schema") == 1
        and document.get("id")
        == "human-ai-collaboration-source-backed-software-lifecycle-thin-slice-v1"
        and document.get("status")
        == "preregistered-zero-model-calibration-only"
        and document.get("scenarioId") == "SE-E2E-THIN-01",
        "Lifecycle protocol identity drifted",
    )
    _require(
        document.get("scenarioBindings")
        == [
            "SE-DISCOVERY-REQ-01",
            "SE-ARCH-DESIGN-01",
            "SE-IMPLEMENT-REVIEW-01",
            "SE-VERIFY-SECURE-01",
            "SE-RELEASE-CHANGE-01",
            "SE-OPS-INCIDENT-01",
            "SE-MAINT-MIGRATE-01",
        ],
        "Lifecycle scenario binding order drifted",
    )
    _validate_schema_bindings(document, root=root, schemas=schemas)

    reuse = document.get("reuseBoundary")
    _require(
        isinstance(reuse, dict)
        and set(reuse)
        == {
            "newManagerOrSkillCreated",
            "frozenThreeStageTraceModified",
            "requirementsDomainSemanticsReused",
            "tddEventAndParentOracleSemanticsReused",
            "cumulativeLossLedgerReusable",
            "gitObserverReusableReadOnlyOnly",
            "maintenanceConsumerAndUnknownTelemetrySemanticsReused",
            "existingDomainRunnersBecomeWholeLifecycleRunner",
        }
        and reuse["newManagerOrSkillCreated"] is False
        and reuse["frozenThreeStageTraceModified"] is False
        and reuse["existingDomainRunnersBecomeWholeLifecycleRunner"] is False
        and all(
            reuse[key] is True
            for key in (
                "requirementsDomainSemanticsReused",
                "tddEventAndParentOracleSemanticsReused",
                "cumulativeLossLedgerReusable",
                "gitObserverReusableReadOnlyOnly",
                "maintenanceConsumerAndUnknownTelemetrySemanticsReused",
            )
        ),
        "Lifecycle reuse boundary drifted",
    )

    modes = document.get("executionModes")
    current = modes.get("current") if isinstance(modes, dict) else None
    future = (
        modes.get("futureNativeWeakAgent")
        if isinstance(modes, dict)
        else None
    )
    _require(
        isinstance(current, dict)
        and current
        == {
            "mode": "zero-model-scripted-calibration",
            "agentDispatchCount": 0,
            "modelCallCount": 0,
            "actualRouteObserved": False,
            "formalLiveEvidenceEligible": False,
            "simulatedAuthorityReceiptsOnly": True,
        },
        "Lifecycle zero-model boundary drifted",
    )
    _require(
        isinstance(future, dict)
        and future.get("requestedModel") == "gpt-5.3-codex-spark"
        and future.get("requestedReasoningEffort") == "low"
        and future.get("providerFallbackAllowed") is False
        and future.get("requiresSeparateAuthorization") is True
        and future.get("candidateSkillsAllowed") is False,
        "Lifecycle weak-Agent future boundary drifted",
    )

    authority = document.get("authorityBoundary")
    _require(
        isinstance(authority, dict)
        and authority.get("repositoryProtocolAndTestWritesAuthorized") is True
        and authority.get("disposableZeroModelFixtureWritesAuthorized") is True,
        "Lifecycle local authority drifted",
    )
    _require(
        all(
            value is False
            for key, value in authority.items()
            if key
            not in {
                "repositoryProtocolAndTestWritesAuthorized",
                "disposableZeroModelFixtureWritesAuthorized",
            }
        ),
        "Lifecycle external or live authority was promoted",
    )

    _require(
        document.get("stageOrder") == EXPECTED_STAGE_ORDER,
        "Lifecycle stage order drifted",
    )
    stages = document.get("stages")
    _require(
        isinstance(stages, list)
        and len(stages) == 7
        and all(isinstance(item, dict) for item in stages),
        "Lifecycle stage set must contain seven objects",
    )
    _require(
        [item.get("sequence") for item in stages] == list(range(1, 8))
        and [item.get("stageId") for item in stages] == EXPECTED_STAGE_ORDER
        and [item.get("stageClass") for item in stages]
        == EXPECTED_STAGE_CLASSES,
        "Lifecycle stage identity or sequence drifted",
    )
    for stage in stages:
        for key in (
            "role",
            "independenceClass",
        ):
            _require(
                isinstance(stage.get(key), str) and stage[key],
                f"Lifecycle stage field missing: {stage.get('stageId')}:{key}",
            )
        for key in (
            "entryGates",
            "requiredInputRoles",
            "requiredOutputRoles",
            "requiredSections",
            "requiredAuthorityGates",
            "stageValidators",
        ):
            _require(
                _unique_nonempty_strings(stage.get(key))
                and bool(stage[key]),
                f"Lifecycle stage list invalid: {stage['stageId']}:{key}",
            )
        _require(
            set(stage["entryGates"]) <= set(EXPECTED_GATES)
            and set(stage["requiredAuthorityGates"]) <= set(EXPECTED_GATES)
            and (
                stage.get("exitGate") is None
                or stage["exitGate"] in EXPECTED_GATES
            ),
            f"Lifecycle stage references an unknown gate: {stage['stageId']}",
        )
    _require(
        stages[3]["role"]
        != stages[2]["role"]
        and "distinct-execution-identity"
        in stages[3]["independenceClass"],
        "Lifecycle independent reviewer separation weakened",
    )

    gates = document.get("gates")
    _require(
        isinstance(gates, list)
        and len(gates) == 8
        and all(isinstance(item, dict) for item in gates)
        and [item.get("sequence") for item in gates] == list(range(8))
        and [item.get("gateId") for item in gates] == EXPECTED_GATES,
        "Lifecycle G0-G7 gate set drifted",
    )
    for gate in gates:
        _require(
            isinstance(gate.get("authorityRole"), str)
            and gate["authorityRole"]
            and isinstance(gate.get("decisionClass"), str)
            and gate["decisionClass"]
            and _unique_nonempty_strings(gate.get("mayAuthorize"))
            and _unique_nonempty_strings(gate.get("mayNotAuthorize"))
            and bool(gate["mayAuthorize"])
            and bool(gate["mayNotAuthorize"]),
            f"Lifecycle gate surface invalid: {gate.get('gateId')}",
        )

    receipt_rules = document.get("authorityReceiptRules")
    _require(
        isinstance(receipt_rules, dict)
        and set(receipt_rules)
        == {
            "noGateAuthorityInheritance",
            "singleUseRequired",
            "exactRunStageProposalAndBeforeLedgerBindingRequired",
            "truthReceiptDoesNotAuthorizeGitDeployExternalWriteOrCleanup",
            "syntheticReceiptMustBeSimulated",
            "agentSelfIssuedReceiptAccepted",
            "reviewOrTestEvidenceCountsAsHumanReceipt",
        }
        and all(
            receipt_rules[key] is True
            for key in (
                "noGateAuthorityInheritance",
                "singleUseRequired",
                "exactRunStageProposalAndBeforeLedgerBindingRequired",
                "truthReceiptDoesNotAuthorizeGitDeployExternalWriteOrCleanup",
                "syntheticReceiptMustBeSimulated",
            )
        )
        and receipt_rules["agentSelfIssuedReceiptAccepted"] is False
        and receipt_rules["reviewOrTestEvidenceCountsAsHumanReceipt"] is False,
        "Lifecycle authority receipt rules drifted",
    )

    ledger_rules = document.get("acceptedInvariantLedgerRules")
    _require(
        isinstance(ledger_rules, dict)
        and len(ledger_rules) == 8
        and all(value is True for value in ledger_rules.values()),
        "Lifecycle accepted invariant ledger rules drifted",
    )
    classification = document.get("classification")
    _require(
        isinstance(classification, dict)
        and set(classification)
        == {"validCalibrationOnly", "partialValidStop", "invalid"}
        and all(
            isinstance(value, str) and value
            for value in classification.values()
        ),
        "Lifecycle outcome classification drifted",
    )
    fixtures = document.get("zeroModelFixtureFamilies")
    _require(
        _unique_nonempty_strings(fixtures) and len(fixtures) == 10,
        "Lifecycle zero-model fixture families drifted",
    )
    claims = document.get("claimBoundary")
    _require(
        isinstance(claims, dict)
        and set(claims) == EXPECTED_CLAIM_KEYS
        and all(value is False for value in claims.values()),
        "Lifecycle claim boundary was weakened or omitted",
    )
    _require(
        document.get("nextGate")
        == "Validate exact protocol and schema shape, then implement a "
        "zero-model scripted capture/evaluator with durable artifacts before "
        "considering one separately authorized native weak-Agent run.",
        "Lifecycle next gate drifted",
    )


def main() -> int:
    document = _read_json_object(ROOT / PROTOCOL_PATH)
    validate_protocol(document, root=ROOT)
    print("Software lifecycle thin-slice protocol validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
