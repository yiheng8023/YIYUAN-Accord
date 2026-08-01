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


def build_mapping(*, root: Path = ROOT) -> dict[str, Any]:
    sources = {path: _load(root, path) for path, _ in SOURCE_SPECS}
    _require_source_evidence(sources)
    return {
        "schema": 1,
        "id": "cross-host-mcp-lifecycle-contract-mapping-2026-08-02",
        "date": "2026-08-02",
        "status": "cross-host-contract-mapped-no-generalized-runtime-claim",
        "laneId": "lane-3-mcp-on-demand-activation-and-release",
        "scope": {
            "mode": "zero-model-existing-evidence-projection",
            "hostCount": 2,
            "modelRequestCount": 0,
            "liveHostProbeCount": 0,
            "configurationMutationCount": 0,
            "externalDiscoveryCount": 0,
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
        "hostMappings": [
            {
                "hostId": "kimi-code",
                "mechanismClass": "pre-tool-call-admission-hook",
                "evidenceState": "synthetic-mechanism-replay-only",
                "freshness": "pinned-revision-not-current-live-host-proof",
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
                "hostId": "codex-cli-app-server-0.145.0-windows",
                "mechanismClass": "startup-profile-and-app-server-process-lifecycle",
                "evidenceState": "bounded-historical-live-host-evidence",
                "freshness": "historical-version-bound-not-current-host-proof",
                "contractProjection": {
                    "selected": "portable-offline-contract-only",
                    "activation-authorized": (
                        "bounded-probe-authority-only-not-a-host-state-observation"
                    ),
                    "call-admitted": "startup-full-filtered-disabled-boundary-observed",
                    "schema-exposed": "not-observed-schema-list-not-called",
                    "runtime-loaded": "enabled-start-and-disabled-start-suppression-observed",
                    "release-requested": "reload-and-unsubscribe-accepted-not-release-proof",
                    "runtime-released": "single-sentinel-thirty-minute-idle-unload-observed",
                    "recovered": "new-thread-new-instance-recovery-observed",
                },
                "effectiveBoundary": (
                    "startup-new-thread-profile-plus-observed-idle-fallback"
                ),
                "degradedFallback": (
                    "startup-or-new-thread-profile-or-observed-native-idle-path"
                ),
            },
        ],
        "decision": {
            "portableContractFieldsMapped": True,
            "materiallyDifferentMechanismsMapped": True,
            "unsupportedOperationsExplicit": True,
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
