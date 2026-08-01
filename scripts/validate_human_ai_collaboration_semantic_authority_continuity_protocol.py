#!/usr/bin/env python3
"""Validate the frozen semantic-authority continuity comparison protocol."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
PROTOCOL_PATH = Path(
    "registry/human-ai-collaboration-semantic-authority-continuity-protocol-2026-07-28.json"
)
RECONCILIATION_PATH = Path(
    "registry/human-ai-collaboration-semantic-authority-layer-reconciliation-2026-07-28.json"
)
EXPOSURE_REPORT_PATH = Path(
    "audits/human-ai-collaboration-semantic-authority-current-matt-"
    "no-model-exposure-2026-07-28/REPORT.json"
)
EXPOSURE_REFRESH_REPORT_PATH = Path(
    "audits/human-ai-collaboration-semantic-authority-current-matt-"
    "no-model-exposure-2026-07-31/REPORT.json"
)
NATIVE_LOCAL_EXPOSURE_REPORT_PATH = Path(
    "audits/human-ai-collaboration-semantic-authority-native-local-"
    "no-model-exposure-2026-08-01/REPORT.json"
)
EXECUTION_PLAN_PREFLIGHT_REPORT_PATH = Path(
    "audits/human-ai-collaboration-semantic-authority-execution-plan-"
    "preflight-2026-08-01/REPORT.json"
)
RUNTIME_ADAPTER_PREFLIGHT_REPORT_PATH = Path(
    "audits/human-ai-collaboration-semantic-authority-runtime-adapter-"
    "preflight-2026-08-01/REPORT.json"
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _index(rows: list[dict], key: str, label: str) -> dict[str, dict]:
    result = {str(row.get(key)): row for row in rows if isinstance(row, dict)}
    _require(len(result) == len(rows), f"{label} identities drifted")
    return result


def validate_protocol(document: dict, *, root: Path = ROOT) -> None:
    _require(
        document.get("schema") == 1
        and document.get("status")
        == (
            "no-model-admission-plan-and-runtime-adapter-preflight-complete-"
            "live-dispatch-not-authorized"
        )
        and document.get("scenarioId") == "HAC-SEMANTIC-AUTHORITY-01"
        and document.get("matrixCellId") == "SEM-03",
        "Semantic continuity protocol identity drifted",
    )

    sources = document.get("sourceBindings", {})
    expected_sources = {
        "semanticReconciliation": str(RECONCILIATION_PATH).replace("\\", "/"),
        "historicalRequirementsProtocol": (
            "registry/human-ai-collaboration-requirements-domain-challenge-"
            "protocol-batch-01-2026-07-24.json"
        ),
        "historicalRequirementsEvidence": (
            "registry/human-ai-collaboration-requirements-domain-live-"
            "comparison-batch-01-2026-07-24.json"
        ),
        "candidateWeakAgentRunner": (
            "scripts/run_human_ai_collaboration_weak_agent_trial.py"
        ),
        "parentOracleReuseDecision": (
            "registry/human-ai-collaboration-unknown-quadrant-parent-oracle-"
            "seam-reuse-decision-2026-07-27.json"
        ),
        "fixtureDefinition": (
            "tests/fixtures/human-ai-collaboration-semantic-authority-"
            "continuity-2026-07-28.json"
        ),
        "fixtureBuilder": (
            "scripts/build_human_ai_collaboration_semantic_authority_"
            "continuity_trial.py"
        ),
        "currentMattStaticAdmission": (
            "registry/human-ai-collaboration-semantic-authority-current-matt-"
            "static-admission-2026-07-28.json"
        ),
        "currentMattNoModelExposureReport": str(EXPOSURE_REPORT_PATH).replace(
            "\\", "/"
        ),
        "currentMattNoModelExposureRefreshReport": str(
            EXPOSURE_REFRESH_REPORT_PATH
        ).replace("\\", "/"),
        "nativeLocalNoModelExposureAndOracleReport": str(
            NATIVE_LOCAL_EXPOSURE_REPORT_PATH
        ).replace("\\", "/"),
        "semanticExecutionPlanBuilder": (
            "scripts/build_human_ai_collaboration_semantic_authority_"
            "execution_plan.py"
        ),
        "semanticExecutionPlanPreflightReport": str(
            EXECUTION_PLAN_PREFLIGHT_REPORT_PATH
        ).replace("\\", "/"),
        "semanticDryRuntimeAdapter": (
            "scripts/run_human_ai_collaboration_semantic_authority_"
            "runtime_adapter.py"
        ),
        "semanticDryRuntimeAdapterPreflightReport": str(
            RUNTIME_ADAPTER_PREFLIGHT_REPORT_PATH
        ).replace("\\", "/"),
    }
    _require(sources == expected_sources, "Semantic continuity source bindings drifted")
    for relative in sources.values():
        _require((root / relative).is_file(), f"Semantic continuity source missing: {relative}")

    treatments = _index(document.get("treatments", []), "id", "Treatment")
    _require(
        set(treatments)
        == {
            "SEM-NATIVE",
            "SEM-LOCAL-ADAPTED-MONOLITH",
            "SEM-MATT-CURRENT-COMPOSITION",
        },
        "Semantic continuity treatment set drifted",
    )
    native = treatments["SEM-NATIVE"]
    _require(
        native.get("selectedUserSkills") == []
        and native.get("allConfigurableUserSkillsDisabled") is True
        and native.get("executionAdmissionSatisfied") is False,
        "Semantic continuity native control drifted",
    )

    local = treatments["SEM-LOCAL-ADAPTED-MONOLITH"]
    local_path = root / Path(str(local.get("path")))
    _require(
        local.get("identity") == "cc.grill-with-docs"
        and local.get("managementOwner") == "CC Switch"
        and local.get("path") == "skills/grill-with-docs/SKILL.md"
        and local.get("bytes") == 5340
        and local.get("sha256")
        == "e1078020c41b954638ba94acda95a3340739908bd68b1db9bc2af129d3936035"
        and local.get("selectedUserSkills") == ["cc.grill-with-docs"]
        and local.get("allOtherConfigurableUserSkillsDisabled") is True
        and local.get("executionAdmissionSatisfied") is False
        and local_path.is_file(),
        "Semantic continuity local treatment drifted",
    )
    local_bytes = local_path.read_bytes()
    _require(
        len(local_bytes) == local["bytes"]
        and hashlib.sha256(local_bytes).hexdigest() == local["sha256"],
        "Semantic continuity frozen local treatment bytes drifted",
    )

    current = treatments["SEM-MATT-CURRENT-COMPOSITION"]
    revision = "ed37663cc5fbef691ddfecd080dff42f7e7e350d"
    _require(
        current.get("repository") == "https://github.com/mattpocock/skills"
        and current.get("revision") == revision
        and current.get("entrySkill") == "grill-with-docs"
        and current.get("dependencySkills") == ["grilling", "domain-modeling"],
        "Semantic continuity current composition identity drifted",
    )
    components = _index(current.get("components", []), "name", "Component")
    _require(
        set(components) == {"grill-with-docs", "grilling", "domain-modeling"},
        "Semantic continuity current component set drifted",
    )
    reconciliation = json.loads(
        (root / RECONCILIATION_PATH).read_text(encoding="utf-8")
    )
    observed = _index(
        reconciliation["sourceObservation"]["files"], "path", "Observed source"
    )
    expected_component_paths = {
        "grill-with-docs": "skills/engineering/grill-with-docs/SKILL.md",
        "grilling": "skills/productivity/grilling/SKILL.md",
        "domain-modeling": "skills/engineering/domain-modeling/SKILL.md",
    }
    for name, path in expected_component_paths.items():
        component = components[name]
        source = observed[path]
        _require(
            component.get("path") == path
            and component.get("bytes") == source.get("bytes")
            and component.get("sha256") == source.get("sha256")
            and component.get("rawUrl")
            == f"https://raw.githubusercontent.com/mattpocock/skills/{revision}/{path}",
            f"Semantic continuity current component pin drifted: {name}",
        )
    _require(
        current.get("isolatedProjectionImplemented") is True,
        "Semantic continuity isolated projection implementation was not recorded",
    )
    _require(
        current.get("dependencyCompleteExposureProved") is True,
        "Semantic continuity dependency-complete exposure was not recorded",
    )
    for key in (
        "entryLoaderInvocationProved",
        "dependencyLoaderInvocationProved",
        "executionAdmissionSatisfied",
    ):
        _require(current.get(key) is False, f"Semantic continuity admission promoted: {key}")
    _require(
        current.get("licenseProvenanceSecurityPortabilityRecheckSatisfied")
        is True,
        "Semantic continuity static admission was not reconciled",
    )

    fixture = document.get("fixtureDesign", {})
    _require(
        fixture.get("fixtureId") == "fixture.pitch-semantic-authority-cross-lifecycle-v1"
        and len(fixture.get("initialAmbiguities", [])) == 4
        and len(fixture.get("frozenHumanDecisionsInjectedByHarness", [])) == 4
        and fixture.get("portableAuthorityCarrierRequired") is True
        and fixture.get("literalContextMdFilenameRequired") is False
        and fixture.get("privateOracleExcludedFromAgentPackets") is True
        and fixture.get("selfAuthoredSkillArmPresent") is False,
        "Semantic continuity fixture boundary drifted",
    )

    phases = document.get("lifecycleSequence", [])
    _require(
        [phase.get("id") for phase in phases]
        == [
            "SEM-PHASE-1-ELICIT",
            "SEM-PHASE-2-MODEL",
            "SEM-PHASE-3-SPEC",
            "SEM-PHASE-4-REVIEW-HANDOFF",
        ]
        and all(phase.get("freshThreadRequired") is True for phase in phases),
        "Semantic continuity lifecycle sequence drifted",
    )
    model = document.get("modelPolicy", {})
    _require(
        model.get("requestedModel") == "gpt-5.3-codex-spark"
        and model.get("requestedReasoningEffort") == "low"
        and model.get("actualModelAndReasoningMustBeRecorded") is True
        and model.get("silentModelSubstitutionAllowed") is False
        and model.get("unavailableRequestedModelOutcome")
        == "invalid-environment-run-do-not-score"
        and model.get("capableDiagnosticCountsTowardWeakAgentAcceptance") is False,
        "Semantic continuity weak-Agent policy drifted",
    )
    _require(
        len(document.get("sharedHardAcceptance", [])) == 8
        and len(document.get("directionalMeasurements", [])) == 11
        and len(document.get("falsifiableDecisionRules", [])) == 5,
        "Semantic continuity measurement contract drifted",
    )

    gate = document.get("executionAdmission", {})
    _require(
        gate.get("minimumValidRunsPerTreatment") == 3
        and gate.get("liveRunAuthorizedByThisRecord") is False,
        "Semantic continuity execution gate drifted",
    )
    _require(
        gate.get("protocolAndOracleFrozen") is True
        and gate.get("fixtureBuilderImplemented") is True
        and gate.get("offlineOracleFaultTestsPass") is True,
        "Semantic continuity fixture gate rolled back",
    )
    _require(
        gate.get("isolatedThreeSkillProjectionImplemented") is True
        and gate.get("projectionBuilderFaultTestsPass") is True
        and gate.get("liveProjectionMaterialized") is True
        and gate.get("lastProjectionAttemptOutcome")
        == "pass-exact-eight-file-materialization-and-no-model-exposure"
        and gate.get("lastNoModelAdmissionOutcome")
        == (
            "pass-native-disabled-local-selected-current-composition-and-"
            "public-packet-oracle-isolation"
        )
        and gate.get("failedAttemptLeftPartialProjection") is False,
        "Semantic continuity projection implementation checkpoint drifted",
    )
    _require(
        gate.get("nativeDisabledExposureProved") is True,
        "Semantic continuity native-disabled exposure was not recorded",
    )
    _require(
        gate.get("localMonolithSelectedExposureProved") is True,
        "Semantic continuity local monolith exposure was not recorded",
    )
    _require(
        gate.get("publicPacketPrivateOracleLeakageRejected") is True,
        "Semantic continuity private-oracle isolation was not recorded",
    )
    _require(
        gate.get("existingRunnerSupportsSemanticTreatments") is False,
        "Semantic continuity runner compatibility overclaimed",
    )
    _require(
        gate.get("existingRunnerLoaderInvocationProved") is False
        and gate.get("existingRunnerInstructionDeliveryProved") is False,
        "Semantic continuity runner evidence overclaimed",
    )
    _require(
        gate.get("semanticExecutionPlanAdapterImplemented") is True
        and gate.get("semanticExecutionPlanPreflightPass") is True,
        "Semantic continuity execution-plan preflight was not recorded",
    )
    _require(
        gate.get("semanticDryRuntimeAdapterImplemented") is True
        and gate.get("semanticDryRuntimeAdapterPreflightPass") is True,
        "Semantic continuity dry runtime-adapter preflight was not recorded",
    )
    _require(
        gate.get("semanticLiveRuntimeAdapterImplemented") is False,
        "Semantic continuity live runtime adapter overclaimed",
    )
    _require(
        gate.get("dispatchReadinessProved") is False,
        "Semantic continuity dispatch readiness overclaimed",
    )
    _require(
        gate.get("currentCompositionDependencyCompleteExposureProved") is True,
        "Semantic continuity current composition exposure was not recorded",
    )
    _require(
        gate.get("currentHostRefreshExposureProved") is True,
        "Semantic continuity current-host exposure was not recorded",
    )
    _require(
        gate.get("exactCurrentComponentsRetrievedAndHashVerified") is True
        and gate.get("licenseProvenanceSecurityPortabilityRecheckSatisfied")
        is True,
        "Semantic continuity static execution gate was not reconciled",
    )

    exposure_report = json.loads(
        (root / EXPOSURE_REPORT_PATH).read_text(encoding="utf-8")
    )
    report_body = dict(exposure_report)
    report_digest = report_body.pop("reportSha256", None)
    computed_report_digest = hashlib.sha256(
        json.dumps(
            report_body,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    _require(
        report_digest == computed_report_digest
        == "024e1b27a51c897f7dac66ab19028a4a4ac6e59ef73cc89b37beefab264238ab",
        "Semantic continuity exposure report digest drifted",
    )
    _require(
        exposure_report.get("status") == "preflight-pass-no-turn"
        and exposure_report.get("candidateId")
        == "matt.current.grill-with-docs-composition"
        and exposure_report.get("projectionManifestSha256")
        == "81570ce9ed247e5f346aa96f97fe30a89f3c15a333289f59192e2146751a3332"
        and exposure_report.get("projectedTreeSha256")
        == "295c4f5819f38e49cd4955d81294a5da1ce3197d78fc52c24bfecaf92027daa5",
        "Semantic continuity exposure identity drifted",
    )
    exposure = exposure_report.get("exposure", {})
    _require(
        exposure.get("requiredSkillCount") == 3
        and exposure.get("requiredSkillNames")
        == ["domain-modeling", "grill-with-docs", "grilling"]
        and exposure.get("allRequiredExactPathsPresent") is True,
        "Semantic continuity dependency exposure drifted",
    )
    arms = _index(exposure_report.get("arms", []), "arm", "Exposure arm")
    _require(
        arms["control-unselected"]["inventory"][
            "enabledConfigurableSkillCount"
        ]
        == 0
        and arms["composition-selected"]["inventory"][
            "enabledConfigurableSkillCount"
        ]
        == 3
        and all(
            arm["inventory"].get(key) is True
            for arm in arms.values()
            for key in (
                "sameIdentitySet",
                "onlyExpectedConfigurableSkillsEnabled",
                "allNonConfigurableStatesPreserved",
            )
        ),
        "Semantic continuity task-scoped exposure drifted",
    )
    _require(
        exposure_report.get("threadStarted") is False
        and exposure_report.get("turnStarted") is False
        and exposure_report.get("modelRequestSent") is False
        and all(exposure_report.get("stability", {}).values())
        and all(
            value is False
            for value in exposure_report.get("claimBoundary", {}).values()
        ),
        "Semantic continuity no-model or claim boundary drifted",
    )

    exposure_refresh_report = json.loads(
        (root / EXPOSURE_REFRESH_REPORT_PATH).read_text(encoding="utf-8")
    )
    refresh_body = dict(exposure_refresh_report)
    refresh_digest = refresh_body.pop("reportSha256", None)
    computed_refresh_digest = hashlib.sha256(
        json.dumps(
            refresh_body,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    _require(
        refresh_digest == computed_refresh_digest
        == "8b1493583296bf2fd289b56b5d9d34156c3ffb1d39a59fd957f30851231e1c5d",
        "Semantic continuity current-host exposure report digest drifted",
    )
    _require(
        exposure_refresh_report.get("status") == "preflight-pass-no-turn"
        and exposure_refresh_report.get("candidateId")
        == "matt.current.grill-with-docs-composition"
        and exposure_refresh_report.get("projectionManifestSha256")
        == "6f8a2ca7b1552028b6c5e785b82b2b56979a62190e66763f2c6ffc3bc87d7001"
        and exposure_refresh_report.get("projectedTreeSha256")
        == "295c4f5819f38e49cd4955d81294a5da1ce3197d78fc52c24bfecaf92027daa5",
        "Semantic continuity current-host exposure identity drifted",
    )
    _require(
        exposure_refresh_report.get("host", {}).get("userAgent")
        == (
            "Codex Desktop/0.146.0 (Windows 10.0.26200; x86_64) unknown "
            "(agent_autonomy_harness_skill_exposure_probe; 1.0.0)"
        )
        and exposure_refresh_report.get("controlInventory", {}).get("skillCount")
        == 50
        and exposure_refresh_report.get("controlInventory", {}).get(
            "countsByScope"
        )
        == {"repo": 3, "system": 6, "user": 41},
        "Semantic continuity current-host inventory snapshot drifted",
    )
    refresh_exposure = exposure_refresh_report.get("exposure", {})
    _require(
        refresh_exposure.get("requiredSkillCount") == 3
        and refresh_exposure.get("requiredSkillNames")
        == ["domain-modeling", "grill-with-docs", "grilling"]
        and refresh_exposure.get("allRequiredExactPathsPresent") is True,
        "Semantic continuity current-host dependency exposure drifted",
    )
    refresh_arms = _index(
        exposure_refresh_report.get("arms", []),
        "arm",
        "Current-host exposure arm",
    )
    _require(
        refresh_arms["control-unselected"]["inventory"][
            "enabledConfigurableSkillCount"
        ]
        == 0
        and refresh_arms["composition-selected"]["inventory"][
            "enabledConfigurableSkillCount"
        ]
        == 3
        and all(
            arm["inventory"].get(key) is True
            for arm in refresh_arms.values()
            for key in (
                "sameIdentitySet",
                "onlyExpectedConfigurableSkillsEnabled",
                "allNonConfigurableStatesPreserved",
            )
        ),
        "Semantic continuity current-host task-scoped exposure drifted",
    )
    _require(
        exposure_refresh_report.get("runtimeIsolation")
        == {
            "codexHomeMode": "temporary-empty-under-projection",
            "temporaryCodexHomeRetained": False,
            "mcpConfigurationMode": "empty-table-override",
            "inheritedGlobalConfigExecuted": False,
        }
        and exposure_refresh_report.get("threadStarted") is False
        and exposure_refresh_report.get("turnStarted") is False
        and exposure_refresh_report.get("modelRequestSent") is False
        and all(exposure_refresh_report.get("stability", {}).values())
        and all(
            value is False
            for value in exposure_refresh_report.get("claimBoundary", {}).values()
        ),
        "Semantic continuity current-host isolation or claim boundary drifted",
    )

    native_local_report = json.loads(
        (root / NATIVE_LOCAL_EXPOSURE_REPORT_PATH).read_text(encoding="utf-8")
    )
    native_local_body = dict(native_local_report)
    native_local_digest = native_local_body.pop("reportSha256", None)
    computed_native_local_digest = hashlib.sha256(
        json.dumps(
            native_local_body,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    _require(
        native_local_digest == computed_native_local_digest
        == "7949dd6d1fdd3236141762b1ae4954ae58ffcdc945db5ed4874ede62aa0097b5",
        "Semantic continuity native/local exposure report digest drifted",
    )
    _require(
        native_local_report.get("status") == "preflight-pass-no-turn"
        and native_local_report.get("probeId")
        == "semantic-authority-native-local-no-model-exposure-v1"
        and native_local_report.get("host", {}).get("userAgent")
        == (
            "Codex Desktop/0.146.0 (Windows 10.0.26200; x86_64) unknown "
            "(agent_autonomy_harness_skill_exposure_probe; 1.0.0)"
        )
        and native_local_report.get("controlInventory", {}).get("skillCount")
        == 48
        and native_local_report.get("controlInventory", {}).get(
            "countsByScope"
        )
        == {"repo": 1, "system": 6, "user": 41},
        "Semantic continuity native/local host snapshot drifted",
    )
    local_treatment = native_local_report.get("localTreatment", {})
    _require(
        local_treatment
        == {
            "identity": "cc.grill-with-docs",
            "skillName": "grill-with-docs",
            "bytes": 5340,
            "sha256": (
                "e1078020c41b954638ba94acda95a3340739908bd68b1db9bc2af129d3936035"
            ),
            "allRequiredExactPathsPresent": True,
        },
        "Semantic continuity local monolith identity drifted",
    )
    native_local_arms = _index(
        native_local_report.get("arms", []),
        "arm",
        "Native/local exposure arm",
    )
    _require(
        native_local_arms["native-configurable-skills-disabled"]["inventory"][
            "enabledConfigurableSkillCount"
        ]
        == 0
        and native_local_arms["local-adapted-monolith-selected"]["inventory"][
            "enabledConfigurableSkillCount"
        ]
        == 1
        and all(
            arm["inventory"].get(key) is True
            for arm in native_local_arms.values()
            for key in (
                "sameIdentitySet",
                "onlyExpectedConfigurableSkillsEnabled",
                "allNonConfigurableStatesPreserved",
            )
        ),
        "Semantic continuity native/local task-scoped exposure drifted",
    )
    _require(
        native_local_report.get("publicPacketOracleIsolation")
        == {
            "positivePacketFailureCodes": [],
            "fullOracleLeakFailureCodes": [
                "hard-fail-unmanifested-public-file",
                "hard-fail-private-oracle-leak",
            ],
            "partialCanaryLeakFailureCodes": [
                "hard-fail-private-oracle-leak",
                "hard-fail-public-file-digest-drift",
            ],
            "publicPacketPrivateOracleLeakageRejected": True,
        },
        "Semantic continuity public-packet private-oracle isolation drifted",
    )
    _require(
        native_local_report.get("runtimeIsolation")
        == {
            "codexHomeMode": "temporary-empty-under-treatment-root",
            "temporaryCodexHomeRetained": False,
            "treatmentRootMode": "temporary-under-repository-tmp",
            "temporaryTreatmentRootRetained": False,
            "mcpConfigurationMode": "empty-table-override",
            "inheritedGlobalConfigExecuted": False,
        }
        and native_local_report.get("threadStarted") is False
        and native_local_report.get("turnStarted") is False
        and native_local_report.get("modelRequestSent") is False
        and all(native_local_report.get("stability", {}).values())
        and all(
            value is False
            for value in native_local_report.get("claimBoundary", {}).values()
        ),
        "Semantic continuity native/local isolation or claim boundary drifted",
    )

    execution_plan_report = json.loads(
        (root / EXECUTION_PLAN_PREFLIGHT_REPORT_PATH).read_text(encoding="utf-8")
    )
    execution_plan_body = dict(execution_plan_report)
    execution_plan_digest = execution_plan_body.pop("reportSha256", None)
    computed_execution_plan_digest = hashlib.sha256(
        json.dumps(
            execution_plan_body,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    _require(
        execution_plan_digest == computed_execution_plan_digest
        == "74a7113c4dc2502460644d701d83608c4cbda9c84ccfec21d34167a6bbc39617",
        "Semantic continuity execution-plan report digest drifted",
    )
    _require(
        execution_plan_report.get("status") == "preflight-pass-no-dispatch"
        and execution_plan_report.get("id")
        == (
            "human-ai-collaboration-semantic-authority-"
            "execution-plan-preflight-v1"
        )
        and execution_plan_report.get("candidateRunnerAssessment")
        == {
            "acceptsSemanticTreatmentIds": False,
            "loaderInvocationProved": False,
            "instructionDeliveryProved": False,
            "dedicatedAdapterRequired": True,
        },
        "Semantic continuity execution-plan identity drifted",
    )
    execution_plan_treatments = _index(
        execution_plan_report.get("treatments", []),
        "treatmentId",
        "Execution-plan treatment",
    )
    _require(
        {
            treatment_id: (
                row.get("runId"),
                row.get("planSha256"),
                row.get("publicPacketManifestSha256"),
            )
            for treatment_id, row in execution_plan_treatments.items()
        }
        == {
            "SEM-NATIVE": (
                "SEM03-ADMISSION-NATIVE-001",
                "748fc795823d2b71f8937c287540d97df122f79528582ca0e213a3e366fd36a2",
                "45ae2e21334d807b7b37c07964c2a2eeafe4f00ed437f55f341c5c46f0932d27",
            ),
            "SEM-LOCAL-ADAPTED-MONOLITH": (
                "SEM03-ADMISSION-LOCAL-001",
                "b1419556f71f0f890bcad792a314e79a2dc205c8b7da6afcad4f544329af95cb",
                "e2d46a706c461b7c0ad4f3592fe727fa4edfc0c7d7843ade751c4fa6feba67ab",
            ),
            "SEM-MATT-CURRENT-COMPOSITION": (
                "SEM03-ADMISSION-CURRENT-001",
                "f1c26c4dcf37caa67996184090cfdc8e8b2e5abd43d0886769762c973ace97d1",
                "71985f01848f58497232075a916c703e0df13438fcc76573464653eae5279b97",
            ),
        }
        and all(
            row.get("status") == "compiled-no-dispatch"
            and row.get("failureCodes") == []
            and row.get("modelRequestSent") is False
            and row.get("threadStarted") is False
            and row.get("turnStarted") is False
            for row in execution_plan_treatments.values()
        ),
        "Semantic continuity execution-plan matrix drifted",
    )
    _require(
        execution_plan_report.get("temporaryProcessRootRetained") is False
        and execution_plan_report.get("modelRequestSent") is False
        and execution_plan_report.get("threadStarted") is False
        and execution_plan_report.get("turnStarted") is False
        and all(
            value is False
            for value in execution_plan_report.get("claimBoundary", {}).values()
        ),
        "Semantic continuity execution-plan boundary drifted",
    )

    runtime_report = json.loads(
        (root / RUNTIME_ADAPTER_PREFLIGHT_REPORT_PATH).read_text(encoding="utf-8")
    )
    runtime_body = dict(runtime_report)
    runtime_digest = runtime_body.pop("reportSha256", None)
    computed_runtime_digest = hashlib.sha256(
        json.dumps(
            runtime_body,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    _require(
        runtime_digest == computed_runtime_digest
        == "284122bab9c24d31308bd75868d7369f7cd47fc4eb49ad17af18f058add3386f",
        "Semantic continuity runtime-adapter report digest drifted",
    )
    _require(
        runtime_report.get("status") == "preflight-pass-no-dispatch"
        and runtime_report.get("id")
        == (
            "human-ai-collaboration-semantic-authority-runtime-adapter-"
            "preflight-v1"
        )
        and runtime_report.get("appServerSessionCount") == 6
        and runtime_report.get("appServerRequestCount") == 12
        and runtime_report.get("hostInventoryBaselineCounts")
        == {"system": 6, "user": 55},
        "Semantic continuity runtime-adapter identity drifted",
    )
    runtime_treatments = _index(
        runtime_report.get("treatments", []),
        "treatmentId",
        "Runtime-adapter treatment",
    )
    _require(
        {
            treatment_id: (
                row.get("runId"),
                row.get("planSha256"),
                row.get("phaseEnvelopeCount"),
                row.get("projection", {}).get("requiredSkillNames"),
            )
            for treatment_id, row in runtime_treatments.items()
        }
        == {
            "SEM-NATIVE": (
                "SEM03-DRY-NATIVE-001",
                "de42e75c4c711c1465473667383cb6303870060082d8d71a12eef2ffa3033055",
                4,
                [],
            ),
            "SEM-LOCAL-ADAPTED-MONOLITH": (
                "SEM03-DRY-LOCAL-001",
                "f4878066f805e7e9b7854f874a20b2ef7bed39f7711816d096f0fa5b67100ee5",
                4,
                ["grill-with-docs"],
            ),
            "SEM-MATT-CURRENT-COMPOSITION": (
                "SEM03-DRY-CURRENT-001",
                "05af2255ede76fbf6a103b7106974df5ede97c95d862e42d0a2052416ee006b8",
                4,
                ["domain-modeling", "grill-with-docs", "grilling"],
            ),
        }
        and all(
            row.get("status") == "preflight-pass-no-dispatch"
            and row.get("failureCodes") == []
            and row.get("phaseRequestsTransmitted") is False
            and row.get("inventory", {}).get("appServerSessionCount") == 2
            and row.get("inventory", {}).get("appServerRequestCount") == 4
            and row.get("inventory", {}).get(
                "appServerInventoryRequestsTransmitted"
            )
            is True
            and row.get("inventory", {}).get("threadStarted") is False
            and row.get("inventory", {}).get("turnStarted") is False
            and row.get("inventory", {}).get("modelRequestSent") is False
            for row in runtime_treatments.values()
        ),
        "Semantic continuity runtime-adapter matrix drifted",
    )
    _require(
        runtime_report.get("temporaryProcessRootRetained") is False
        and runtime_report.get("phaseRequestsTransmitted") is False
        and runtime_report.get("modelRequestSent") is False
        and runtime_report.get("threadStarted") is False
        and runtime_report.get("turnStarted") is False
        and all(
            value is False
            for value in runtime_report.get("claimBoundary", {}).values()
        ),
        "Semantic continuity runtime-adapter boundary drifted",
    )

    authority = document.get("authorityBoundary", {})
    _require(
        authority.get("repositoryProtocolWritesAuthorized") is True
        and authority.get("validatorAndTestWritesAuthorized") is True
        and authority.get("fixtureBuilderWriteAuthorized") is True,
        "Semantic continuity repository authority drifted",
    )
    for key, value in authority.items():
        if key not in {
            "repositoryProtocolWritesAuthorized",
            "validatorAndTestWritesAuthorized",
            "fixtureBuilderWriteAuthorized",
        }:
            _require(value is False, f"Semantic continuity authority expanded: {key}")

    decision = document.get("decision", {})
    _require(
        decision.get("threeTreatmentDesignFrozen") is True
        and decision.get("currentUpstreamTreatmentAdmitted") is False
        and decision.get("liveExecutionStarted") is False
        and decision.get("generalDirectionConfirmedByThisProtocol") is False
        and decision.get("candidatePreferenceAllowed") is False
        and decision.get("ccMutationAllowed") is False
        and decision.get("selfAuthoredResidualGapProved") is False,
        "Semantic continuity decision overclaimed",
    )
    _require(
        all(value is False for value in document.get("claimBoundary", {}).values()),
        "Semantic continuity claim boundary was promoted",
    )

    documentation = root / str(document.get("documentation"))
    _require(documentation.is_file(), "Semantic continuity documentation is missing")
    text = " ".join(documentation.read_text(encoding="utf-8").split())
    for phrase in (
        "no treatment has been run",
        "literal filename `CONTEXT.md` is not",
        "Terminal correctness cannot erase",
        "does not justify mandatory grilling",
        "report association only",
        "Silent substitution is invalid",
        "execution admission gates were still open at that static-admission checkpoint",
        "All declared no-model admission gates are now closed",
        "it is not an automatic model run",
    ):
        _require(phrase in text, f"Semantic continuity documentation missing: {phrase}")


def main() -> int:
    document = json.loads((ROOT / PROTOCOL_PATH).read_text(encoding="utf-8"))
    validate_protocol(document, root=ROOT)
    print("Semantic-authority continuity protocol validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
