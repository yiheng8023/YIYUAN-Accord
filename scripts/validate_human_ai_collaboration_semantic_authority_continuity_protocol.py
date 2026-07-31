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
        == "no-model-admission-complete-live-dispatch-not-authorized"
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
        "weakAgentRunner": "scripts/run_human_ai_collaboration_weak_agent_trial.py",
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
