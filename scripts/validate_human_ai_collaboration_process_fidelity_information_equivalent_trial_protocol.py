#!/usr/bin/env python3
"""Validate the preregistered information-equivalent process-fidelity trial."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
PROTOCOL_PATH = (
    "registry/"
    "human-ai-collaboration-process-fidelity-information-equivalent-"
    "trial-protocol-v2-2026-07-27.json"
)
DOC_PATH = (
    "docs/strategy/"
    "HUMAN-AI-COLLABORATION-PROCESS-FIDELITY-INFORMATION-EQUIVALENT-"
    "TRIAL-PROTOCOL-V2-2026-07-27.md"
)
MATRIX_PATH = (
    "registry/"
    "human-ai-collaboration-scenario-evidence-matrix-batch-01-"
    "2026-07-24.json"
)
ACCEPTANCE_PATH = "registry/program-acceptance-map.json"
SOURCE_FIXTURE_PATH = (
    "tests/fixtures/"
    "human-ai-collaboration-process-fidelity-research-oracle-v2-2026-07-27.json"
)

SOURCE_SHA256 = (
    "85ac1584b14ec293b60d8123385ad34c13d1e22470a7f7ab420fdef533a5d992"
)
ORACLE_SHA256 = (
    "e2dacb10be81d87f63bb5bbdaf94a45ce9f49335bd10b72620b6e41461b99a76"
)
PUBLIC_CLAIMS_SHA256 = (
    "e0de7c0c6648959dde02929c8eac8f4b6367fdac7046c04c302e098e56133aa0"
)
PROMPT_SHA256 = (
    "42962d4c9460f5560e9bee79fccecfb0c67726023823167efb46199ed1bfcfe5"
)
PUBLIC_BUNDLE_SHA256 = (
    "b477ef4f58c68fcfeb7024604257f50f2a15fae7c184adf2314debfbad3b8226"
)
ARM_IDS = [
    "complete-single-turn",
    "same-thread-incremental-information",
    "source-backed-fresh-session-recovery",
]
SOURCE_IDS = ["SRC-A", "SRC-B", "SRC-C", "SRC-D"]
CLAIM_IDS = ["C1", "C2", "C3", "C4", "C5"]


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    _require(isinstance(value, dict), f"Expected JSON object: {path}")
    return value


def _canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _plain_sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _index(items: Any, field: str, label: str) -> dict[str, dict[str, Any]]:
    _require(isinstance(items, list), f"{label} must be a list")
    result: dict[str, dict[str, Any]] = {}
    for item in items:
        _require(isinstance(item, dict), f"{label} entries must be objects")
        key = item.get(field)
        _require(
            isinstance(key, str) and bool(key),
            f"{label} entry needs {field}",
        )
        _require(key not in result, f"{label} duplicate {field}: {key}")
        result[key] = item
    return result


def _acceptance_index(document: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return _index(document.get("acceptanceCriteria"), "id", "Acceptance criteria")


def validate_protocol(
    protocol: dict[str, Any],
    *,
    root: Path = ROOT,
    matrix: dict[str, Any] | None = None,
    acceptance: dict[str, Any] | None = None,
) -> None:
    """Reject information drift, confounds, overclaims, and premature promotion."""
    expected_identity = {
        "schema": 1,
        "id": (
            "human-ai-collaboration-process-fidelity-information-"
            "equivalent-trial-protocol-v2-2026-07-27"
        ),
        "date": "2026-07-27",
        "status": (
            "v2-source-backed-smoke-passed-three-arm-cohort-not-executed"
        ),
    }
    for key, value in expected_identity.items():
        _require(
            protocol.get(key) == value,
            f"Information-equivalent protocol {key} drifted",
        )

    identity = protocol.get("identityLedger")
    _require(
        isinstance(identity, dict)
        and identity.get("fixtureId")
        == "fixture.synthetic-conflicting-claims-v2"
        and identity.get("submissionArmId") == "GEN-NATIVE-SPARK"
        and identity.get("informationArmIds") == ARM_IDS
        and identity.get("identitiesMayBeSubstituted") is False,
        "Information-equivalent identity ledger drifted",
    )

    supersession = protocol.get("supersessionBinding")
    _require(
        isinstance(supersession, dict)
        and supersession.get("v1ProtocolPath")
        == (
            "registry/human-ai-collaboration-process-fidelity-information-"
            "equivalent-trial-protocol-2026-07-27.json"
        )
        and supersession.get("v1CalibrationEvidencePath")
        == (
            "registry/human-ai-collaboration-process-fidelity-v1-"
            "calibration-abort-2026-07-27.json"
        )
        and supersession.get("v1CalibrationStatus")
        == "measurement-ambiguous-v1-cohort-aborted"
        and supersession.get("v1RunCountEligibleForV2") == 0
        and supersession.get("v1AndV2RunsMayBeCombined") is False,
        "Information-equivalent v1 quarantine binding drifted",
    )
    for path_key in ("v1ProtocolPath", "v1CalibrationEvidencePath"):
        _require(
            (root / supersession[path_key]).is_file(),
            f"Information-equivalent supersession artifact missing: {path_key}",
        )

    authority = protocol.get("authorityBoundary")
    _require(
        isinstance(authority, dict)
        and authority.get("owningRepository") == "agent-autonomy-harness",
        "Information-equivalent protocol authority identity drifted",
    )
    for key, value in authority.items():
        if key == "owningRepository":
            continue
        _require(
            value is False,
            f"Information-equivalent protocol authority overclaimed: {key}",
        )

    scope = protocol.get("subprotocolScope")
    _require(
        isinstance(scope, dict)
        and scope.get("category")
        == "delivery-topology-and-absolute-task-fidelity"
        and scope.get("terminalTaskFidelityInScope") is True
        and scope.get("trueOutputToInputChainedTransformInScope") is False
        and scope.get("processHopLedgerProduced") is False
        and scope.get("cascadeMeasurementProduced") is False
        and scope.get("endToEndProcessFidelityAcceptanceSufficientAlone")
        is False
        and isinstance(scope.get("requiredComplement"), str)
        and bool(scope["requiredComplement"]),
        "Information-equivalent subprotocol scope drifted",
    )
    if matrix is None:
        matrix = _load(root / MATRIX_PATH)
    canonical_hard_requirements = _index(
        matrix.get("hardRequirements"),
        "id",
        "Hard requirements",
    )
    scenario = protocol.get("scenarioBinding")
    _require(isinstance(scenario, dict), "Scenario binding is missing")
    _require(
        scenario.get("primaryScenarioId") == "GEN-RESEARCH-01"
        and scenario.get("crossCuttingRiskId")
        == "XCR-01-process-fidelity-and-loss"
        and scenario.get("transportScenarioIds") == ["CTX-04", "CTX-05"]
        and scenario.get("explicitlyNotBoundScenarioIds")
        == ["CTX-02", "CTX-03", "CTX-06", "CTX-07"],
        "Information-equivalent scenario binding drifted",
    )
    expected_protocol_hard_requirements = [
        "HR-01-goal-and-acceptance",
        "HR-02-truth-provenance-and-uncertainty",
        "HR-03-authority-data-and-least-privilege",
        "HR-05-reversibility-recovery-and-continuity",
        "HR-06-human-decision-and-accountability",
    ]
    _require(
        scenario.get("protocolHardRequirementIds")
        == expected_protocol_hard_requirements
        and set(expected_protocol_hard_requirements)
        <= set(canonical_hard_requirements),
        "Information-equivalent hard-requirement binding drifted",
    )
    acceptance_ids = scenario.get("acceptanceIds")
    _require(
        isinstance(acceptance_ids, dict)
        and acceptance_ids.get("primary")
        == ["acceptance.end-to-end-process-fidelity"]
        and acceptance_ids.get("supporting")
        == [
            "acceptance.native-runtime-baseline",
            "acceptance.cross-agent-claim-limits",
            "acceptance.ai-independent-hard-standard-boundary",
            "acceptance.dynamic-runtime-control-gap-research",
            "acceptance.native-task-orchestration-boundary",
        ],
        "Information-equivalent acceptance binding drifted",
    )

    binding = protocol.get("sourceAndOracleBinding")
    _require(
        isinstance(binding, dict)
        and binding.get("fixturePath") == SOURCE_FIXTURE_PATH
        and binding.get("fixtureKey") == "researchOracle"
        and binding.get("fixtureId")
        == "fixture.synthetic-conflicting-claims-v2"
        and binding.get("semanticContractVersion")
        == "research-claim-entailment-v2"
        and binding.get("privateOracleVersion")
        == "synthetic-conflicting-claims-hidden-oracle-v2"
        and binding.get("sourceIds") == SOURCE_IDS
        and binding.get("claimIds") == CLAIM_IDS,
        "Information-equivalent source or oracle identity drifted",
    )
    fixture = _load(root / SOURCE_FIXTURE_PATH).get("researchOracle")
    _require(
        isinstance(fixture, dict)
        and fixture.get("fixtureId") == binding.get("fixtureId"),
        "Information-equivalent source fixture is missing or drifted",
    )
    public_claims = [
        {
            "id": item.get("id"),
            "meaning": item.get("meaning"),
            "requiredSourceIds": item.get("requiredSourceIds"),
        }
        for item in fixture.get("claims", [])
    ]
    private_oracle_payload = {
        "claims": [
            {
                "id": item.get("id"),
                "state": item.get("state"),
                "sourceIds": item.get("sourceIds"),
            }
            for item in fixture.get("claims", [])
        ],
        "unsupportedConclusionCount": 0,
        "externalAccessUsed": False,
        "writePerformed": False,
    }
    expected_hashes = {
        "sourcePacketCanonicalSha256": _canonical_sha256(
            fixture.get("sourcePacket")
        ),
        "publicClaimsToAssessCanonicalSha256": _canonical_sha256(
            public_claims
        ),
        "privateOracleCanonicalSha256": _canonical_sha256(
            private_oracle_payload
        ),
        "publicTaskInstructionSha256": _plain_sha256(
            fixture.get("publicPrompt", "")
        ),
        "publicInformationBundleCanonicalSha256": _canonical_sha256(
            {
                "fixtureId": fixture.get("fixtureId"),
                "semanticContractVersion": fixture.get(
                    "semanticContractVersion"
                ),
                "publicPrompt": fixture.get("publicPrompt"),
                "sourcePacket": fixture.get("sourcePacket"),
                "claimsToAssess": public_claims,
            }
        ),
    }
    frozen_expected_hashes = {
        "sourcePacketCanonicalSha256": SOURCE_SHA256,
        "publicClaimsToAssessCanonicalSha256": PUBLIC_CLAIMS_SHA256,
        "privateOracleCanonicalSha256": ORACLE_SHA256,
        "publicTaskInstructionSha256": PROMPT_SHA256,
        "publicInformationBundleCanonicalSha256": PUBLIC_BUNDLE_SHA256,
    }
    _require(
        expected_hashes == frozen_expected_hashes,
        "Information-equivalent source fixture bytes drifted",
    )
    _require(
        all(binding.get(key) == value for key, value in expected_hashes.items()),
        "Information-equivalent source or oracle fingerprint drifted",
    )
    _require(
        [item.get("id") for item in fixture.get("sourcePacket", [])]
        == SOURCE_IDS
        and [item.get("id") for item in fixture.get("claims", [])]
        == CLAIM_IDS,
        "Information-equivalent source or claim set drifted",
    )
    _require(
        all(
            item.get("requiredSourceIds") == item.get("sourceIds")
            and isinstance(item.get("requiredSourceIds"), list)
            and item.get("requiredSourceIds")
            for item in fixture.get("claims", [])
        )
        and "logical negation" in fixture.get("publicPrompt", "")
        and "does not count requested claims" in fixture.get("publicPrompt", ""),
        "Information-equivalent v2 public semantic contract drifted",
    )
    private_oracle = binding.get("privateOracle")
    _require(
        isinstance(private_oracle, dict)
        and private_oracle.get("owner") == "parent-harness"
        and private_oracle.get("frozenBeforeAnyArmDispatch") is True
        and private_oracle.get(
            "sameFingerprintRequiredForEveryArmAndRepetition"
        )
        is True
        and private_oracle.get("contentWrittenIntoPublicPrompt") is False
        and private_oracle.get("contentWrittenIntoIncrementalMessages")
        is False
        and private_oracle.get("contentWrittenIntoSourceBackedArtifact")
        is False
        and private_oracle.get("mayBeChangedAfterFirstArmOutput") is False,
        "Information-equivalent private oracle was exposed or made mutable",
    )

    equivalence = protocol.get("informationEquivalenceContract")
    _require(
        isinstance(equivalence, dict)
        and equivalence.get("allArmsProjectOneFrozenSourcePacket") is True
        and equivalence.get("allArmsUseOneFrozenPrivateOracle") is True
        and equivalence.get("allArmsUseOneOutputContract") is True
        and equivalence.get("allArmsUseOneModelAndReasoningRoute") is True
        and equivalence.get("allArmsUseOneAuthorityBoundary") is True
        and equivalence.get("allArmsForbidShellAndGeneralFileReads") is True
        and equivalence.get("sourceBackedArmUsesOnlyParentScopedReadTool")
        is True
        and equivalence.get("onlyAllowedCrossArmDifference")
        == (
            "predeclared delivery topology, including the parent-scoped "
            "public-bundle read transport required by the source-backed arm"
        )
        and equivalence.get("preDispatchFailureOutcome")
        == "fail-arm-information-equivalence-zero-dispatch",
        "Information-equivalence contract drifted",
    )
    _require(
        len(equivalence.get("forbiddenConfounds", [])) >= 7,
        "Information-equivalence confound boundary is incomplete",
    )

    host = protocol.get("hostAndModelBinding")
    _require(
        isinstance(host, dict)
        and host.get("primaryWeakModelRequested") == "gpt-5.3-codex-spark"
        and host.get("primaryReasoningEffortRequested") == "low"
        and host.get("routeMustBeRevalidatedBeforeEveryRun") is True
        and host.get("providerFallbackAllowed") is False
        and host.get("unavailableRequestedRouteOutcome")
        == "blocked-requested-model-route-unavailable",
        "Information-equivalent host or weak-model binding drifted",
    )
    diagnostic = host.get("conditionalCapacityDiagnostic")
    _require(
        isinstance(diagnostic, dict)
        and diagnostic.get("requestedModelId") == "gpt-5.6-terra"
        and diagnostic.get("requestedReasoningEffort") == "low"
        and diagnostic.get("mayReplaceWeakAgentAcceptance") is False,
        "Information-equivalent capacity diagnostic boundary drifted",
    )

    arms = _index(protocol.get("trialArms"), "id", "Information arms")
    _require(list(arms) == ARM_IDS, "Information arm identity or order drifted")
    for arm_id, arm in arms.items():
        _require(
            arm.get("informationArmId") == arm_id
            and arm.get("freshTaskPerRepetition") is True
            and arm.get("sourceIdsExact") == SOURCE_IDS
            and arm.get("privateOracleCanonicalSha256") == ORACLE_SHA256
            and arm.get("modelId") == "gpt-5.3-codex-spark"
            and arm.get("reasoningEffort") == "low"
            and arm.get("candidateCapabilityIds") == [],
            f"Information arm confound or manifest drifted: {arm_id}",
        )
    incremental = arms["same-thread-incremental-information"]
    shards = incremental.get("sourceShardIdsInOrder")
    _require(
        shards == [["SRC-A"], ["SRC-B"], ["SRC-C"], ["SRC-D"]]
        and [item for shard in shards for item in shard] == SOURCE_IDS
        and incremental.get("prematureSubstantiveAnswerIsProcessDeviation")
        is True,
        "Incremental information shard manifest drifted",
    )
    recovery = arms["source-backed-fresh-session-recovery"]
    _require(
        recovery.get(
            "sourceBackedArtifactMustMatchPublicInformationBundleCanonicalSha256"
        )
        == PUBLIC_BUNDLE_SHA256
        and recovery.get("scopedReadToolName")
        == "read_public_information_bundle"
        and recovery.get("scopedReadToolCallCountExact") == 1
        and recovery.get("shellOrCommandExecutionAllowed") is False
        and recovery.get("generalFilesystemReadAllowed") is False
        and recovery.get("agentVisibleFileNamesExact")
        == ["PUBLIC-SOURCE-BUNDLE.json"]
        and recovery.get("producerAgentBehaviorInScope") is False
        and recovery.get("handoffSkillInvocationInScope") is False
        and recovery.get(
            "manualOrParentAuthorizedCreationMustNotBeLabeledAutomatic"
        )
        is True,
        "Source-backed fresh-session arm drifted",
    )

    repetition = protocol.get("repetitionAndOrderingContract")
    _require(
        isinstance(repetition, dict)
        and repetition.get("minimumValidRepetitionsPerArm") == 3
        and repetition.get("freshTaskRequiredForEveryRepetition") is True
        and repetition.get("crossArmTaskReuseAllowed") is False
        and repetition.get("priorArmOutputReuseAllowed") is False
        and repetition.get("balancedOrder")
        == [
            ARM_IDS,
            [ARM_IDS[1], ARM_IDS[2], ARM_IDS[0]],
            [ARM_IDS[2], ARM_IDS[0], ARM_IDS[1]],
        ]
        and repetition.get("incompleteOrOpaqueArmOutcome")
        == "incomplete-no-arm-ranking-or-evidence-promotion",
        "Information-equivalent repetition or ordering contract drifted",
    )

    execution = protocol.get("executionBoundary")
    _require(
        isinstance(execution, dict)
        and execution.get("zeroDispatchOnPreflightFailure") is True
        and "MCP, App, Plugin, or candidate Skill use"
        in execution.get("forbiddenEffects", [])
        and "shell or command execution in any arm"
        in execution.get("forbiddenEffects", [])
        and "general filesystem reads or parent-evidence reads"
        in execution.get("forbiddenEffects", [])
        and (
            "parent evidence root separated from the exact Agent-visible "
            "file set"
        )
        in execution.get("preDispatchGates", [])
        and (
            "source-backed scoped reader returns only the exact public-bundle "
            "hash"
        )
        in execution.get("preDispatchGates", [])
        and "separate live task-creation authority for each dispatched task"
        in execution.get("preDispatchGates", []),
        "Information-equivalent execution boundary drifted",
    )

    measurement = protocol.get("measurementContract")
    ledgers = (
        measurement.get("ledgerSeparation")
        if isinstance(measurement, dict)
        else None
    )
    hard_gates = (
        measurement.get("hardPerRunGates")
        if isinstance(measurement, dict)
        else None
    )
    _require(
        isinstance(hard_gates, dict)
        and isinstance(ledgers, dict)
        and "cannot rescue failure" in ledgers.get("absoluteTaskLedger", "")
        and "without a synthetic total score"
        in ledgers.get("relativeProcessLedger", "")
        and ledgers.get("ambiguousOrUnprovedDesignOutcome")
        == "invalid-design-no-comparison"
        and ledgers.get("validDesignButAllArmsAbsoluteFailureOutcome")
        == "bounded-relative-observation-no-acceptance"
        and hard_gates.get("requiredClaimIdsExact") is True
        and hard_gates.get("claimStateAndSourceSetExact") is True
        and hard_gates.get("unsupportedConclusionCountMax") == 0
        and hard_gates.get("externalAccessUsed") is False
        and hard_gates.get("writePerformed") is False
        and hard_gates.get("authorityDriftCountMax") == 0
        and hard_gates.get("unsupportedAutomaticCapabilityClaimCountMax")
        == 0
        and hard_gates.get("privateOracleExposureCountMax") == 0
        and hard_gates.get("preDispatchPublicCarrierOracleIsolationProved")
        is True
        and hard_gates.get("runtimeReadBoundaryProved") is True
        and hard_gates.get("commandExecutionCountMax") == 0
        and hard_gates.get("sourceBackedScopedReadToolCallCountExact") == 1,
        "Information-equivalent hard per-run gates drifted",
    )
    _require(
        "cannot erase" in measurement.get("intermediateLossRule", "")
        and "not universal hard-standard thresholds"
        in measurement.get("thresholdLimit", ""),
        "Information-equivalent process-loss boundary drifted",
    )

    observation = protocol.get("hostObservationBoundary")
    _require(
        isinstance(observation, dict)
        and observation.get("manualFreshTaskCreationMayBeObserved") is True
        and observation.get("manualSourceArtifactConsumptionMayBeObserved")
        is True
        and observation.get("automaticCompressionRequiresNativeEventEvidence")
        is True
        and observation.get(
            "automaticThreadCreationRequiresNativeEventEvidence"
        )
        is True
        and observation.get(
            "handoffSkillInvocationRequiresLoaderAndInvocationEvidence"
        )
        is True
        and observation.get("missingNativeEvidenceOutcome")
        == "opaque-or-unproved-not-inferred"
        and observation.get(
            "manualActionCannotSatisfyAutomaticCapabilityClaim"
        )
        is True,
        "Information-equivalent host-capability boundary was promoted",
    )

    reuse = protocol.get("reuseBindings")
    _require(isinstance(reuse, dict), "Information-equivalent reuse bindings missing")
    for key in (
        "sourceFixture",
        "existingWeakAgentBuilder",
        "existingWeakAgentRunner",
        "existingContextContract",
        "existingProcessFidelityEvaluator",
        "primarySourceDesignInput",
    ):
        path = reuse.get(key)
        _require(
            isinstance(path, str) and (root / path).is_file(),
            f"Information-equivalent reuse binding missing: {key}",
        )

    packet = protocol.get("packetPreparation")
    _require(
        isinstance(packet, dict)
        and packet.get("status")
        == (
            "implemented-v2-separated-carriers-zero-dispatch-"
            "not-live-evidence"
        )
        and packet.get("parentEvidencePackageFileNames")
        == [
            "PUBLIC-SOURCE-BUNDLE.json",
            "TRIAL-PACKET.json",
            "BUILD-MANIFEST.json",
        ]
        and packet.get("agentVisibleFileNamesForDirectAndIncrementalArms")
        == []
        and packet.get("agentVisibleFileNamesForSourceBackedArm")
        == ["PUBLIC-SOURCE-BUNDLE.json"]
        and packet.get("parentEvidenceRootMustNotBeRuntimeWorkspaceRoot")
        is True
        and packet.get("sourceBackedScopedReadToolRequired") is True
        and packet.get("shellExecutionForbiddenForEveryArm") is True
        and packet.get("privateOracleContentWritten") is False
        and packet.get("agentRunStartedByBuilderOrPreflight") is False
        and packet.get("builderDispatchCount") == 0
        and packet.get("builderScoredArmCount") == 0
        and packet.get("additionalLiveTaskCreationAuthorized") is False,
        "Information-equivalent packet preparation boundary drifted",
    )
    _require(
        packet.get("runnerAdapterImplemented") is True
        and packet.get("runnerDefaultsToNoLiveDispatch") is True
        and packet.get("liveRunnerExecuted") is True
        and packet.get("liveRunnerDispatchCount") == 2
        and packet.get("liveCalibrationDispatchCount") == 1
        and packet.get("measurementInvalidDispatchCount") == 1
        and packet.get("absoluteTaskValidTransportRepetitionCount") == 1
        and packet.get("processTraceValidRepetitionCount") == 0
        and packet.get("completedThreeRepetitionArmCount") == 0
        and packet.get("v1CalibrationRunExcluded") is True,
        "Information-equivalent runner adapter boundary drifted",
    )
    calibration = protocol.get("liveSmokeCalibration")
    _require(
        isinstance(calibration, dict)
        and calibration.get("status")
        == "measurement-invalid-source-backed-smoke-01-excluded"
        and calibration.get("informationArmId")
        == "source-backed-fresh-session-recovery"
        and calibration.get("dispatchCount") == 1
        and calibration.get("validArmCount") == 0
        and calibration.get("observedFailureCodes") == ["unknown-arm"]
        and calibration.get("dynamicToolCallObserved") is True
        and calibration.get("scopedDynamicToolSucceeded") is True
        and calibration.get("runtimeReadBoundaryProved") is True
        and calibration.get("commandExecutionObserved") is False
        and calibration.get("fileChangeObserved") is False
        and calibration.get("allNonIdentityOracleFieldsMatched") is True
        and calibration.get("oneSmokeDispatchConsumed") is True
        and calibration.get("eligibleForThreeArmComparison") is False,
        "Information-equivalent live smoke calibration drifted",
    )
    for key in (
        "temporaryReportPath",
        "temporaryReportFileSha256",
        "temporaryReportCanonicalSha256",
        "preCorrectionProtocolFileSha256",
        "sourceFixtureFileSha256",
        "preCorrectionRunnerFileSha256",
        "cause",
        "correction",
        "claimLimit",
    ):
        _require(
            isinstance(calibration.get(key), str) and calibration[key],
            f"Information-equivalent live smoke calibration missing: {key}",
        )
    smoke = protocol.get("liveSmokeEvidence")
    _require(
        isinstance(smoke, dict)
        and smoke.get("path")
        == (
            "registry/human-ai-collaboration-process-fidelity-v2-"
            "source-backed-smoke-evidence-2026-07-27.json"
        )
        and (root / smoke["path"]).is_file()
        and smoke.get("status")
        == (
            "bounded-source-backed-smoke-pass-one-absolute-task-valid-"
            "transport-repetition"
        )
        and smoke.get("informationArmId")
        == "source-backed-fresh-session-recovery"
        and smoke.get("validRepetitionCount") == 1
        and smoke.get("requiredValidRepetitionsForCompletedArm") == 3
        and smoke.get("completedArmCount") == 0
        and smoke.get("countsAsAbsoluteTaskValidTransportRepetition") is True
        and smoke.get("countsAsProcessTraceValidRepetition") is False
        and smoke.get("processHopLedgerPresent") is False
        and smoke.get("cascadeMeasurementPresent") is False
        and smoke.get("countsAsProcessFidelityComparison") is False
        and smoke.get("evidenceStopRequired") is True,
        "Information-equivalent valid source-backed smoke binding drifted",
    )
    trace_calibration = protocol.get("chainedTraceMeasurementCalibration")
    _require(
        isinstance(trace_calibration, dict)
        and trace_calibration.get("path")
        == (
            "registry/human-ai-collaboration-process-fidelity-chained-trace-"
            "measurement-calibration-2026-07-27.json"
        )
        and (root / trace_calibration["path"]).is_file()
        and trace_calibration.get("status")
        == "zero-agent-passed-live-cohort-not-authorized"
        and trace_calibration.get("agentDispatchCount") == 0
        and trace_calibration.get("modelCallCount") == 0
        and trace_calibration.get("existingTransportSmokeCountsAsProcessTrace")
        is False
        and trace_calibration.get("rawEventTraceAdapterImplemented") is True
        and trace_calibration.get(
            "existingSmokeDeterministicallyRescoredAsProcessTrace"
        )
        is False
        and trace_calibration.get("formalLiveCohortAuthorized") is False,
        "Information-equivalent chained-trace calibration binding drifted",
    )
    trace_eligibility = protocol.get("existingSmokeTraceEligibilityAssessment")
    _require(
        isinstance(trace_eligibility, dict)
        and trace_eligibility.get("path")
        == (
            "registry/human-ai-collaboration-process-fidelity-raw-event-trace-"
            "eligibility-assessment-2026-07-27.json"
        )
        and (root / trace_eligibility["path"]).is_file()
        and trace_eligibility.get("status")
        == "transport-pilot-only-process-trace-ineligible"
        and trace_eligibility.get("opaqueMaterialEdgeIds")
        == ["scoped-read-result-to-agent-structured-response"]
        and trace_eligibility.get("processHopLedgerPresent") is False
        and trace_eligibility.get("manualSupplementationUsed") is False
        and trace_eligibility.get(
            "formalProcessCohortStartingValidRepetitionCount"
        )
        == 0,
        "Information-equivalent existing-smoke trace eligibility drifted",
    )
    for key in (
        "builder",
        "preflight",
        "tests",
        "runnerAdapter",
        "runnerAdapterTests",
    ):
        path = packet.get(key)
        _require(
            isinstance(path, str) and (root / path).is_file(),
            f"Information-equivalent packet preparation file missing: {key}",
        )

    claims = protocol.get("claimBoundary")
    _require(
        isinstance(claims, dict)
        and len(claims) >= 12
        and all(value is False for value in claims.values()),
        "Information-equivalent protocol claim boundary was promoted",
    )
    decision = protocol.get("decision")
    _require(
        isinstance(decision, dict)
        and decision.get("protocolPreregistered") is True
        and decision.get("v1CalibrationQuarantined") is True
        and decision.get("v2SemanticContractFrozen") is True
        and decision.get("offlineContractReadyForValidation") is True
        and decision.get("offlineContractValidated") is True
        and decision.get("packetBuilderImplemented") is True
        and decision.get("zeroDispatchPreflightImplemented") is True
        and decision.get("existingReadOnlyRunnerParameterized") is True
        and decision.get("runnerDefaultsToNoLiveDispatch") is True
        and decision.get("liveExecutionReady") is False
        and decision.get(
            "oneAbsoluteTaskValidSourceBackedTransportRepetitionRecorded"
        )
        is True
        and decision.get("processTraceValidRepetitionCount") == 0
        and decision.get(
            "zeroAgentChainedTraceMeasurementCalibrationPassed"
        )
        is True
        and decision.get("existingTransportSmokeProcessTraceEligible")
        is False
        and decision.get("formalProcessCohortStartingValidRepetitionCount")
        == 0
        and decision.get("completedInformationArmCount") == 0
        and decision.get("widerCohortStarted") is False
        and decision.get("newStandaloneRunnerAuthorized") is False
        and decision.get("liveRunnerDispatchAuthorized") is False,
        "Information-equivalent protocol decision drifted",
    )

    risks = _index(
        matrix.get("crossCuttingRisks"),
        "id",
        "Cross-cutting risks",
    )
    risk = risks.get("XCR-01-process-fidelity-and-loss")
    _require(
        isinstance(risk, dict)
        and risk.get("evidenceState")
        == "planned-no-end-to-end-process-fidelity-evidence"
        and risk.get("measurementCalibrationEvidence")
        == (
            "registry/human-ai-collaboration-process-fidelity-v1-"
            "calibration-abort-2026-07-27.json"
        )
        and risk.get("chainedTraceMeasurementCalibrationEvidence")
        == (
            "registry/human-ai-collaboration-process-fidelity-chained-trace-"
            "measurement-calibration-2026-07-27.json"
        ),
        "Information-equivalent protocol promoted matrix process-fidelity evidence",
    )
    matrix_binding = matrix.get(
        "processFidelityInformationEquivalentTrialProtocol"
    )
    _require(
        isinstance(matrix_binding, dict)
        and matrix_binding.get("path") == PROTOCOL_PATH
        and matrix_binding.get("status")
        == (
            "v2-source-backed-smoke-passed-three-arm-cohort-not-executed"
        )
        and matrix_binding.get("v1CalibrationStatus")
        == "measurement-ambiguous-v1-cohort-aborted"
        and matrix_binding.get("v1RunCountEligibleForV2") == 0
        and matrix_binding.get("primaryScenarioId") == "GEN-RESEARCH-01"
        and matrix_binding.get("crossCuttingRiskId")
        == "XCR-01-process-fidelity-and-loss"
        and matrix_binding.get("armCount") == 3
        and matrix_binding.get("weakModelRequested")
        == "gpt-5.3-codex-spark"
        and matrix_binding.get("reasoningEffortRequested") == "low"
        and matrix_binding.get("packetPreparationStatus")
        == (
            "implemented-v2-separated-carriers-zero-dispatch-not-live-evidence"
        )
        and matrix_binding.get("runnerAdapterStatus")
        == (
            "corrected-and-one-absolute-task-valid-source-backed-transport-"
            "repetition-recorded-evidence-stop"
        )
        and matrix_binding.get("liveCalibrationStatus")
        == "measurement-invalid-source-backed-smoke-01-excluded"
        and matrix_binding.get("liveCalibrationDispatchCount") == 1
        and matrix_binding.get("measurementInvalidDispatchCount") == 1
        and matrix_binding.get("absoluteTaskValidTransportRepetitionCount") == 1
        and matrix_binding.get("processTraceValidRepetitionCount") == 0
        and matrix_binding.get("chainedTraceMeasurementCalibrationPath")
        == (
            "registry/human-ai-collaboration-process-fidelity-chained-trace-"
            "measurement-calibration-2026-07-27.json"
        )
        and matrix_binding.get("chainedTraceMeasurementCalibrationStatus")
        == "zero-agent-passed-live-cohort-not-authorized"
        and matrix_binding.get("existingSmokeTraceEligibilityAssessmentPath")
        == (
            "registry/human-ai-collaboration-process-fidelity-raw-event-trace-"
            "eligibility-assessment-2026-07-27.json"
        )
        and matrix_binding.get("existingSmokeTraceEligibilityStatus")
        == "transport-pilot-only-process-trace-ineligible"
        and matrix_binding.get(
            "formalProcessCohortStartingValidRepetitionCount"
        )
        == 0
        and matrix_binding.get("completedInformationArmCount") == 0
        and matrix_binding.get("liveSmokeEvidencePath")
        == (
            "registry/human-ai-collaboration-process-fidelity-v2-"
            "source-backed-smoke-evidence-2026-07-27.json"
        )
        and matrix_binding.get("currentHostScopedDynamicReadObserved") is True
        and matrix_binding.get("runtimeReadBoundaryProvedForCalibration")
        is True
        and matrix_binding.get("liveExecutionAuthorized") is False
        and matrix_binding.get(
            "automaticCompressionOrThreadCreationClaimed"
        )
        is False
        and matrix_binding.get("handoffSkillInvocationClaimed") is False
        and matrix_binding.get("evidenceStatePromotionAuthorized") is False,
        "Information-equivalent matrix protocol binding drifted",
    )
    scenarios = _index(matrix.get("scenarios"), "id", "Scenario matrix")
    _require(
        scenarios.get("GEN-RESEARCH-01", {}).get("evidenceState")
        == (
            "bounded-synthetic-v2-source-backed-smoke-pass-"
            "no-topology-comparison"
        ),
        "Information-equivalent protocol promoted research scenario evidence",
    )

    if acceptance is None:
        acceptance = _load(root / ACCEPTANCE_PATH)
    criteria = _acceptance_index(acceptance)
    _require(
        criteria.get("acceptance.end-to-end-process-fidelity", {}).get(
            "assessment"
        )
        == "partial",
        "Information-equivalent protocol promoted program acceptance",
    )
    for acceptance_id in (
        acceptance_ids["primary"] + acceptance_ids["supporting"]
    ):
        _require(
            acceptance_id in criteria,
            f"Information-equivalent acceptance target is unknown: {acceptance_id}",
        )

    _require(
        protocol.get("documentation") == DOC_PATH,
        "Information-equivalent protocol documentation path drifted",
    )
    normalized_doc = " ".join(
        (root / DOC_PATH).read_text(encoding="utf-8").split()
    )
    for phrase in (
        "live three-arm cohort not executed",
        "V1 remains historical host/runner diagnostic evidence",
        "only allowed difference is the delivery topology",
        "parent-scoped dynamic read tool",
        "two ledgers that cannot cancel each other",
        "Relative improvement cannot rescue an absolute weak-Agent failure",
        "cannot prove automatic thread creation",
        "not evidence that the `handoff` Skill loaded or ran",
        "A matching final answer does not erase intermediate process loss",
        "delivery-topology and absolute-task-fidelity subprotocol",
        "does not produce a process-hop ledger or cascade measurement",
        "stays `partial`",
        "zero trial calls",
        "zero dispatch and zero scored arms",
        "defaults to no live dispatch",
        "before the first task turn",
        "One live v2 calibration dispatch occurred",
        "one absolute-task-valid transport repetition out of three required",
        "zero-Agent chained-trace calibration passed",
        "existing smoke is process-trace ineligible",
        "starts from zero",
        "does not prove",
    ):
        _require(
            phrase in normalized_doc,
            f"Information-equivalent documentation boundary missing: {phrase}",
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    root = args.root.resolve()
    validate_protocol(_load(root / PROTOCOL_PATH), root=root)
    print("information-equivalent process-fidelity trial protocol: valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
