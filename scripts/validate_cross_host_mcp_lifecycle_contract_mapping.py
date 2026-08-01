#!/usr/bin/env python3
"""Validate the bounded Kimi/Codex MCP lifecycle contract projection."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
MAPPING_PATH = (
    "registry/cross-host-mcp-lifecycle-contract-mapping-2026-08-02.json"
)
SCRIPT_PATH = "scripts/validate_cross_host_mcp_lifecycle_contract_mapping.py"
TEST_PATH = "tests/test_cross_host_mcp_lifecycle_contract_mapping.py"
REQUIRED_FILES = (MAPPING_PATH, SCRIPT_PATH, TEST_PATH)

SOURCE_SPECS = (
    (
        "registry/mcp-task-selection-decision-contract-2026-07-23.json",
        "portable-selection-contract",
    ),
    (
        "registry/mcp-task-lifecycle-evidence-contract-2026-07-23.json",
        "portable-lifecycle-contract",
    ),
    (
        "audits/kimi-three-hook-comparison-replay-2026-08-01/REPORT.json",
        "kimi-synthetic-mechanism-evidence",
    ),
    (
        "registry/mcp-app-server-0.145.0-startup-profile-evidence-2026-07-23.json",
        "codex-startup-profile-evidence",
    ),
    (
        "registry/mcp-app-server-0.145.0-reload-release-attribution-evidence-2026-07-27.json",
        "codex-reload-release-falsifier",
    ),
    (
        "registry/mcp-app-server-0.145.0-thread-unsubscribe-release-attribution-evidence-2026-07-27.json",
        "codex-unsubscribe-release-falsifier",
    ),
    (
        "registry/mcp-app-server-0.145.0-idle-unload-evidence-2026-07-23.json",
        "codex-idle-unload-evidence",
    ),
    (
        "registry/mcp-app-server-0.146.0-reload-release-version-change-evidence-2026-08-02.json",
        "codex-current-version-reload-release-evidence",
    ),
)


def _load(root: Path, relative: str) -> dict[str, Any]:
    return json.loads((root / relative).read_text(encoding="utf-8"))


def _sha256(root: Path, relative: str) -> str:
    return hashlib.sha256((root / relative).read_bytes()).hexdigest()


def _require_source_evidence(sources: dict[str, dict[str, Any]]) -> None:
    selection = sources[SOURCE_SPECS[0][0]]
    lifecycle = sources[SOURCE_SPECS[1][0]]
    kimi = sources[SOURCE_SPECS[2][0]]
    startup = sources[SOURCE_SPECS[3][0]]
    reload_evidence = sources[SOURCE_SPECS[4][0]]
    unsubscribe = sources[SOURCE_SPECS[5][0]]
    idle = sources[SOURCE_SPECS[6][0]]
    current_reload = sources[SOURCE_SPECS[7][0]]

    if (
        selection.get("policy", {}).get("selectionDoesNotAuthorizeActivation")
        is not True
        or selection.get("policy", {}).get("releaseRequestDoesNotProveRelease")
        is not True
        or selection.get("policy", {}).get("defaultActivationScopeIsTaskOrPhaseOnly")
        is not True
        or selection.get("claimBoundary", {}).get("crossHostSupportProved")
        is not False
    ):
        raise RuntimeError("Cross-host MCP selection source evidence drifted")
    if (
        lifecycle.get("operatingPolicy", {}).get(
            "fallbackWhenDynamicLifecycleUnproved"
        )
        != "startup-or-new-thread-profile-or-documented-native-idle-timeout"
        or lifecycle.get("operatingPolicy", {}).get("policyDoesNotProveHostActuation")
        is not True
        or lifecycle.get("claimBoundary", {}).get("sameSessionSwitchingProved")
        is not False
    ):
        raise RuntimeError("Cross-host MCP lifecycle source evidence drifted")

    kimi_cases = {
        row.get("id"): row
        for row in kimi.get("mechanismCases", [])
        if isinstance(row, dict)
    }
    if (
        kimi.get("status") != "valid-mechanism-replay-only"
        or kimi.get("evidenceCost", {}).get("modelRequestCount") != 0
        or kimi.get("claimBoundary", {}).get("liveHostAcceptanceProved")
        is not False
        or any(
            kimi_cases.get(case_id, {}).get("passed") is not True
            for case_id in (
                "mcp-pinned-default-on",
                "mcp-explicit-off",
                "mcp-default-off",
                "mcp-missing-gate-fail-open",
            )
        )
        or kimi.get("claimBoundary", {}).get("hostHookRegistrationProved")
        is not False
        or kimi.get("claimBoundary", {}).get("dynamicMcpLifecycleProved")
        is not False
    ):
        raise RuntimeError("Cross-host MCP Kimi source evidence drifted")
    topology = kimi.get("topology", {})
    lanes = {
        row.get("id"): row
        for row in topology.get("lanes", [])
        if isinstance(row, dict)
    }
    if (
        topology.get("executablePrototypeCount") != 2
        or topology.get("sharedInfrastructureCount") != 1
        or topology.get("ruleTextGroupCount") != 2
        or lanes.get("lane-1-context-lifecycle-handoff", {}).get(
            "executablePrototype"
        )
        != "hooks/context-usage.mjs"
        or lanes.get("lane-3-mcp-on-demand-activation", {}).get(
            "executablePrototype"
        )
        != "hooks/mcp-gate.mjs"
        or lanes.get("lane-1-context-lifecycle-handoff", {}).get(
            "sharedInfrastructure"
        )
        != ["hooks/session-start.mjs"]
        or lanes.get("lane-3-mcp-on-demand-activation", {}).get(
            "sharedInfrastructure"
        )
        != ["hooks/session-start.mjs"]
        or lanes.get("lane-2-branch-worktree-judgment", {}).get(
            "executablePrototype"
        )
        is not None
    ):
        raise RuntimeError("Cross-host MCP Kimi topology evidence drifted")

    startup_conclusions = startup.get("supportedConclusions", {})
    if (
        startup_conclusions.get("startupProfileDirectCallBoundaryObservedForThisHostAndSentinel")
        is not True
        or startup_conclusions.get("fullProfileExposedBothToolsAcrossTwoRuns")
        is not True
        or startup_conclusions.get("filteredProfileKeptIdentityAndRejectedHoldAcrossTwoRuns")
        is not True
        or startup_conclusions.get("disabledProfileRejectedBothToolsWithoutSentinelAcrossTwoRuns")
        is not True
        or startup_conclusions.get("serverDisablePreventedSentinelProcessStartupInThisRun")
        is not True
        or startup_conclusions.get("startupOrNewThreadConfigurationIsABoundedFallbackForThisHost")
        is not True
        or startup.get("claimBoundary", {}).get("automaticTaskScopedOnDemandSwitchingProved")
        is not False
    ):
        raise RuntimeError("Cross-host MCP Codex startup evidence drifted")
    if (
        reload_evidence.get("decision", {}).get("reloadRequestAcceptanceObserved")
        is not True
        or reload_evidence.get("decision", {}).get(
            "nativeReloadIsNotATestedImmediateReleaseMechanismForAlreadyLoadedRuntime"
        )
        is not True
        or reload_evidence.get("decision", {}).get(
            "reloadCausedPriorRuntimeReleaseInTestedWindow"
        )
        is not False
        or reload_evidence.get("decision", {}).get(
            "residualSelfAuthoredControllerGapProved"
        )
        is not False
    ):
        raise RuntimeError("Cross-host MCP Codex reload evidence drifted")
    if (
        unsubscribe.get("decision", {}).get("unsubscribeRequestAcceptanceObserved")
        is not True
        or unsubscribe.get("decision", {}).get(
            "unsubscribeImmediateReleaseInTestedWindowObserved"
        )
        is not False
        or unsubscribe.get("decision", {}).get(
            "unsubscribeAsObservedImmediateReleaseMechanismFalsifiedForTestedBoundary"
        )
        is not True
        or unsubscribe.get("decision", {}).get(
            "nativeThirtyMinuteIdleFallbackRemainsSeparate"
        )
        is not True
        or unsubscribe.get("decision", {}).get(
            "residualSelfAuthoredControllerGapProved"
        )
        is not False
    ):
        raise RuntimeError("Cross-host MCP Codex unsubscribe evidence drifted")
    if (
        idle.get("supportedConclusions", {}).get("documentedThirtyMinuteIdlePathExecuted")
        is not True
        or idle.get("supportedConclusions", {}).get(
            "newThreadDirectCallRecoveredWithNewSentinelInstance"
        )
        is not True
        or idle.get("supportedConclusions", {}).get(
            "exactSentinelChildProcessCountChangedFromOneToZero"
        )
        is not True
        or idle.get("claimBoundary", {}).get("stableResourceSavingsProved")
        is not False
    ):
        raise RuntimeError("Cross-host MCP Codex idle evidence drifted")
    if (
        current_reload.get("status")
        != (
            "observed-three-repetition-single-host-version-bounded-config-"
            "disable-plus-reload-release"
        )
        or current_reload.get("hostBinding", {}).get("codexVersion")
        != "codex-cli 0.146.0"
        or current_reload.get("aggregateObservation", {}).get(
            "validRepetitionCount"
        )
        != 3
        or current_reload.get("aggregateObservation", {}).get(
            "reloadReleaseObservedCount"
        )
        != 3
        or current_reload.get("aggregateObservation", {}).get(
            "loadedRuntimeRetainedCount"
        )
        != 0
        or current_reload.get("decision", {}).get(
            "boundedNativeSameThreadConfigDisablePlusReloadAndReleaseObserved"
        )
        is not True
        or current_reload.get("decision", {}).get(
            "selfAuthoredControllerEligible"
        )
        is not False
        or current_reload.get("claimBoundary", {}).get(
            "taskEndImmediateReleaseProved"
        )
        is not False
        or current_reload.get("claimBoundary", {}).get("crossHostParityProved")
        is not False
        or current_reload.get("claimBoundary", {}).get(
            "residualNeedForSelfAuthoredControllerProved"
        )
        is not False
    ):
        raise RuntimeError("Cross-host MCP current Codex evidence drifted")


def build_mapping(*, root: Path = ROOT) -> dict[str, Any]:
    sources = {path: _load(root, path) for path, _ in SOURCE_SPECS}
    _require_source_evidence(sources)
    return {
        "schema": 1,
        "id": "cross-host-mcp-lifecycle-contract-mapping-2026-08-02",
        "date": "2026-08-02",
        "status": (
            "cross-host-contract-mapped-current-codex-bounded-native-win-"
            "no-generalized-runtime-claim"
        ),
        "laneId": "lane-3-mcp-on-demand-activation-and-release",
        "scope": {
            "mode": "zero-model-version-aware-evidence-projection",
            "hostCount": 2,
            "modelRequestCount": 0,
            "mappingExecutionLiveHostProbeCount": 0,
            "boundSourceLiveHostProbeRepetitionCount": 3,
            "mappingConfigurationMutationCount": 0,
            "boundOfficialSourceSnapshotCount": 1,
            "selfAuthoredRuntimeAdded": False,
        },
        "sourceBindings": [
            {
                "path": path,
                "role": role,
                "fileSha256": _sha256(root, path),
            }
            for path, role in SOURCE_SPECS
        ],
        "portableContract": {
            "desiredState": "smallest-authorized-task-or-phase-mcp-set",
            "lifecycleStates": [
                "selected",
                "activation-authorized",
                "call-admitted",
                "schema-exposed",
                "runtime-loaded",
                "release-requested",
                "runtime-released",
                "recovered",
            ],
            "authorityRule": "selection-does-not-authorize-activation-or-release",
            "observationRule": "request-acceptance-does-not-prove-runtime-state",
            "fallbackRule": (
                "startup-or-new-thread-profile-or-documented-native-idle-timeout-"
                "only-where-host-evidence-supports-it"
            ),
            "unsupportedRule": "mark-unavailable-or-unproved-and-degrade-explicitly",
        },
        "architectureLayers": [
            {
                "id": "portable-decision-contract",
                "responsibility": (
                    "host-independent desired state authority evidence and "
                    "fallback semantics"
                ),
                "mustNotContain": "one-host-actuation-assumptions",
            },
            {
                "id": "host-neutral-adapter-contract",
                "responsibility": (
                    "map portable lifecycle states onto declared host "
                    "capabilities while preserving unsupported operations"
                ),
                "operations": [
                    "inspect-host-capabilities",
                    "plan-minimal-authorized-set",
                    "request-host-native-activation-or-call-admission",
                    "observe-schema-and-runtime-state-separately",
                    "request-release",
                    "observe-exact-release",
                    "recover-or-degrade-explicitly",
                ],
                "authorityBoundary": (
                    "host-native-enforcement-and-lifecycle-remain-authoritative"
                ),
                "isUniversalRuntimeImplementation": False,
            },
            {
                "id": "host-specific-implementation-and-evidence",
                "responsibility": (
                    "bind one host mechanism version authority and observed "
                    "lifecycle limits without promotion to another host"
                ),
                "mappedHostMechanismFamilies": [
                    "kimi-code-synthetic-mechanism",
                    "codex-cli-app-server",
                ],
                "crossHostByteParityRequired": False,
            },
        ],
        "hostMappings": [
            {
                "hostId": "kimi-code",
                "mechanismClass": "pre-tool-call-admission-hook",
                "evidenceState": "synthetic-mechanism-replay-only",
                "freshness": "pinned-revision-not-current-live-host-proof",
                "hostMechanismTopology": {
                    "executablePrototypes": [
                        "hooks/context-usage.mjs",
                        "hooks/mcp-gate.mjs",
                    ],
                    "sharedInjectionInfrastructure": "hooks/session-start.mjs",
                    "ruleTextGroups": [
                        "AGENTS.md#上下文交接协议",
                        "AGENTS.md#Git纪律",
                    ],
                    "lane2ExecutablePrototype": None,
                },
                "contractProjection": {
                    "selected": "portable-contract-only",
                    "activation-authorized": "not-observed",
                    "call-admitted": "synthetic-explicit-default-and-fail-open-replayed",
                    "schema-exposed": "not-observed",
                    "runtime-loaded": "not-observed",
                    "release-requested": "operator-contract-static-only",
                    "runtime-released": "not-observed",
                    "recovered": "not-observed",
                },
                "effectiveBoundary": "call-admission-only-no-schema-or-process-release",
                "degradedFallback": "requires-separate-host-native-lifecycle-evidence",
            },
            {
                "hostId": "codex-cli-app-server-0.146.0-windows",
                "mechanismClass": (
                    "version-aware-startup-profile-app-server-refresh-and-"
                    "process-lifecycle"
                ),
                "evidenceState": (
                    "bounded-current-reload-release-plus-historical-"
                    "startup-idle-evidence"
                ),
                "freshness": (
                    "current-for-0.146.0-reload-release-only-historical-for-"
                    "startup-idle-and-unsubscribe"
                ),
                "contractProjection": {
                    "selected": "portable-offline-contract-only",
                    "activation-authorized": (
                        "bounded-probe-authority-only-not-a-host-state-observation"
                    ),
                    "call-admitted": (
                        "historical-startup-boundaries-plus-current-same-thread-"
                        "disabled-rejection-observed"
                    ),
                    "schema-exposed": "not-observed-schema-list-not-called",
                    "runtime-loaded": (
                        "historical-enabled-start-plus-current-baseline-load-"
                        "observed"
                    ),
                    "release-requested": (
                        "current-config-disable-reload-accepted-with-historical-"
                        "unsubscribe-separated"
                    ),
                    "runtime-released": (
                        "three-of-three-exact-baseline-release-after-config-"
                        "disable-and-reload"
                    ),
                    "recovered": (
                        "three-of-three-exact-config-restore-new-thread-control-"
                        "succeeded"
                    ),
                },
                "effectiveBoundary": (
                    "bounded-current-config-disable-reload-release-plus-version-"
                    "bound-startup-new-thread-and-idle-fallback"
                ),
                "degradedFallback": (
                    "current-native-disable-reload-only-for-tested-boundary-"
                    "otherwise-version-bound-startup-new-thread-or-idle-path"
                ),
            },
        ],
        "decision": {
            "portableContractFieldsMapped": True,
            "materiallyDifferentMechanismsMapped": True,
            "portableAdapterHostImplementationSeparationEnforced": True,
            "unsupportedOperationsExplicit": True,
            "boundedCurrentCodexConfigDisablePlusReloadReleaseProved": True,
            "generalizedRuntimeCapabilityProved": False,
            "crossHostParityProved": False,
            "sameSessionDynamicLifecycleProved": False,
            "stableResourceBenefitProved": False,
            "residualSelfAuthoredGapProved": False,
            "selfAuthoredControllerEligible": False,
            "nextGate": (
                "use one bound workload only when current-version or cross-host "
                "behavior would change the fallback or residual-gap decision"
            ),
        },
        "claimBoundary": {
            "currentKimiHostBehaviorProved": False,
            "currentCodexHostBehaviorProved": False,
            "crossHostParityProved": False,
            "sameSessionSwitchingProved": False,
            "taskEndImmediateReleaseProved": False,
            "leaseOrReferenceCountProved": False,
            "stableResourceBenefitProved": False,
            "universalMcpLifecycleProved": False,
            "selfAuthoredResidualGapProved": False,
            "productionReadinessProved": False,
        },
    }


def validate_mapping(document: dict[str, Any], *, root: Path = ROOT) -> None:
    expected = build_mapping(root=root)
    if document != expected:
        raise RuntimeError("Cross-host MCP lifecycle projection drifted")


def main() -> int:
    validate_mapping(_load(ROOT, MAPPING_PATH), root=ROOT)
    print("Cross-host MCP lifecycle contract mapping validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
