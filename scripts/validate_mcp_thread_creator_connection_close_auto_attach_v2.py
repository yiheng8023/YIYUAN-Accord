#!/usr/bin/env python3
"""Fail-closed validation for the offline auto-attach v2 amendment."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
AMENDMENT_PATH = (
    "registry/"
    "mcp-thread-creator-connection-close-auto-attach-offline-amendment-v2-"
    "2026-07-27.json"
)
PROTOCOL_PATH = (
    "registry/"
    "mcp-thread-creator-connection-close-auto-attach-protocol-v2-"
    "2026-07-27.json"
)
PROBE_PATH = (
    "scripts/"
    "probe_codex_app_server_mcp_thread_creator_connection_close_auto_attach_"
    "v2.py"
)
TEST_PATH = (
    "tests/"
    "test_codex_app_server_mcp_thread_creator_connection_close_auto_attach_"
    "v2_probe.py"
)
DOCUMENTATION_PATH = (
    "docs/"
    "mcp-thread-creator-connection-close-auto-attach-offline-amendment-v2-"
    "2026-07-27.md"
)
ADMISSION_PATH = (
    "registry/"
    "mcp-thread-creator-close-observer-acquisition-path-admission-"
    "2026-07-27.json"
)
OLD_PROTOCOL_PATH = (
    "registry/"
    "mcp-thread-creator-connection-close-attribution-protocol-2026-07-27.json"
)
OLD_PROBE_PATH = (
    "scripts/probe_codex_app_server_mcp_thread_creator_connection_close.py"
)
SHA256_BINDINGS = {
    ADMISSION_PATH: (
        "CD39E16132771F2D0233DFCD29C818215372A14D0538C0444261F065B4AC241D"
    ),
    OLD_PROTOCOL_PATH: (
        "8A110058AAC75DDC54E2B3795F6F6BE12004E4CDE0262045BEA79D112D157326"
    ),
    OLD_PROBE_PATH: (
        "66CF7066B68D92139653C5E41AD74CAA64D00273C662A2899E396501974C2CF6"
    ),
    PROTOCOL_PATH: (
        "86974D1684ABCE53DC1114EAEE901BD430D05834C46D044DDEDF4CEB03F8CBAF"
    ),
    PROBE_PATH: (
        "A4BA8ECCE063DC142CECBE7AA2D248703A4FEDBFD4D21A18105DC5077F8C7B58"
    ),
    TEST_PATH: (
        "867CA0A60B5DBCA85187D77297758F6E642FCD1DB7744BDCDD1823E5159FBBB1"
    ),
}
EXPECTED_SETUP = [
    "Connection B initializes.",
    (
        "Connection B completes config/read as an initialized barrier before "
        "connection A sends thread/start."
    ),
    "Connection A initializes.",
    "Connection A starts one non-ephemeral read-only thread.",
    "Connection A calls Sentinel identity on that thread.",
    (
        "Connection B directly calls Sentinel identity on the same thread "
        "without thread/resume."
    ),
    (
        "The parent requires A and B to report the same Sentinel PID and "
        "instance ID and binds that exact process identity."
    ),
]
FORBIDDEN_IMPORT_ROOTS = {
    "socket",
    "subprocess",
    "requests",
    "urllib",
    "websocket",
    "websockets",
}
FORBIDDEN_REQUEST_METHODS = {
    "turn/start",
    "thread/resume",
    "thread/unsubscribe",
}
CLAIM_KEYS = {
    "autoAttachIsSecondSubscriptionProved",
    "autoAttachCreatesIndependentOwnerProved",
    "leaseOrReferenceCountProved",
    "taskEndSemanticsProved",
    "finalReleaseSemanticsProved",
    "resourceBenefitProved",
    "crossHostParityProved",
    "crossVersionParityProved",
    "selfAuthoredControllerNeedProved",
    "liveReadinessProved",
}
DENIED_EXECUTION_KEYS = {
    "appServerStartAuthorized",
    "loopbackTransportExecutionAuthorized",
    "modelOrAccountUseAuthorized",
    "externalNetworkUseAuthorized",
    "configurationMutationAuthorized",
    "installationAuthorized",
    "liveProtocolExecutionAuthorized",
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    _require(isinstance(value, dict), f"JSON object required: {path}")
    return value


def validate_probe_source(source: str) -> None:
    tree = ast.parse(source)
    imported_roots: set[str] = set()
    requested_methods: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(
                alias.name.split(".")[0] for alias in node.names
            )
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".")[0])
        elif (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "request"
            and len(node.args) > 1
            and isinstance(node.args[1], ast.Constant)
            and isinstance(node.args[1].value, str)
        ):
            requested_methods.append(node.args[1].value)
    _require(
        imported_roots.isdisjoint(FORBIDDEN_IMPORT_ROOTS),
        "V2 probe gained a live transport or process dependency",
    )
    _require(
        not FORBIDDEN_REQUEST_METHODS.intersection(requested_methods),
        "V2 probe contains a forbidden host RPC",
    )
    _require(
        {"initialize", "config/read", "thread/start", "mcpServer/tool/call"}
        .issubset(requested_methods),
        "V2 probe required RPC surface drifted",
    )
    _require(
        "def execute_offline_injected_arm(" in source
        and '"formalLiveRun": False' in source
        and '"role": "diagnostic-only"' in source
        and "Live execution is not implemented or authorized" in source,
        "V2 probe offline-only boundary drifted",
    )


def validate_protocol(document: dict[str, Any]) -> None:
    _require(
        document.get("schemaVersion") == 1
        and document.get("id")
        == "MCP-THREAD-CREATOR-CONNECTION-CLOSE-AUTO-ATTACH-V2-01"
        and document.get("date") == "2026-07-27"
        and document.get("status")
        == "offline-amendment-not-live-executed",
        "V2 protocol identity drifted",
    )
    _require(
        document.get("formalRunCount") == 0,
        "V2 protocol formal-run boundary was promoted",
    )
    supersession = document.get("supersessionBoundary", {})
    _require(
        supersession.get("amendsProtocolPath") == OLD_PROTOCOL_PATH
        and supersession.get("amendsProtocolSha256")
        == SHA256_BINDINGS[OLD_PROTOCOL_PATH]
        and supersession.get("oldProtocolMutationAuthorized") is False
        and supersession.get("oldProbePath") == OLD_PROBE_PATH
        and supersession.get("oldProbeSha256")
        == SHA256_BINDINGS[OLD_PROBE_PATH]
        and supersession.get("oldProbeMutationAuthorized") is False,
        "V2 protocol historical-preservation boundary drifted",
    )
    design = document.get("design", {})
    _require(
        design.get("setupSequence") == EXPECTED_SETUP,
        "V2 protocol setup sequence drifted",
    )
    _require(
        design.get("rolloutMaterializationRole")
        == "diagnostic-only-never-a-prerequisite"
        and "sealed before the observer post-window" in str(
            design.get("evidenceSeal")
        )
        and "without thread/resume" in str(design.get("postWindow"))
        and "close both injected connection transports" in str(
            design.get("failureCleanup")
        ),
        "V2 protocol diagnostic, seal, or cleanup boundary drifted",
    )
    per_arm = design.get("perArm", {})
    _require(
        per_arm.get("appServerProcesses") == 1
        and per_arm.get("webSocketBridgeProcesses") == 2
        and per_arm.get("loadedThreads") == 1
        and per_arm.get("modelTurns") == 0,
        "V2 protocol per-arm topology drifted",
    )
    boundary = document.get("executionBoundary", {})
    _require(
        boundary.get("offlineProtocolAndDeterministicTestsAuthorized") is True
        and boundary.get("formalLivePairedRunsExecuted") is False
        and all(
            boundary.get(key) is False
            for key in (
                "appServerStartAuthorized",
                "loopbackTransportExecutionAuthorized",
                "modelOrAccountUseAuthorized",
                "externalNetworkUseAuthorized",
                "globalConfigurationMutationAuthorized",
                "installationAuthorized",
                "liveProtocolExecutionAuthorized",
            )
        ),
        "V2 protocol execution boundary was expanded",
    )
    claims = document.get("claimBoundary")
    _require(
        isinstance(claims, dict)
        and set(claims) == CLAIM_KEYS
        and all(value is False for value in claims.values()),
        "V2 protocol claim boundary was promoted",
    )


def validate_amendment(document: dict[str, Any]) -> None:
    _require(
        document.get("schema") == 1
        and document.get("id")
        == (
            "mcp-thread-creator-connection-close-auto-attach-offline-"
            "amendment-v2-2026-07-27"
        )
        and document.get("date") == "2026-07-27"
        and document.get("status")
        == (
            "offline-v2-amendment-deterministically-validated-not-live-"
            "authorized"
        ),
        "V2 amendment identity drifted",
    )
    bindings = document.get("sourceBindings", {})
    expected_bindings = {
        "admissionGate": {
            "path": ADMISSION_PATH,
            "sha256": SHA256_BINDINGS[ADMISSION_PATH],
            "requiredConclusion": "offline-amendment-required-before-live",
        },
        "historicalProtocol": {
            "path": OLD_PROTOCOL_PATH,
            "sha256": SHA256_BINDINGS[OLD_PROTOCOL_PATH],
            "mutationAuthorized": False,
        },
        "historicalProbe": {
            "path": OLD_PROBE_PATH,
            "sha256": SHA256_BINDINGS[OLD_PROBE_PATH],
            "mutationAuthorized": False,
        },
        "v2Protocol": {
            "path": PROTOCOL_PATH,
            "sha256": SHA256_BINDINGS[PROTOCOL_PATH],
        },
        "v2Probe": {
            "path": PROBE_PATH,
            "sha256": SHA256_BINDINGS[PROBE_PATH],
        },
        "v2ProbeTests": {
            "path": TEST_PATH,
            "sha256": SHA256_BINDINGS[TEST_PATH],
        },
    }
    _require(
        bindings == expected_bindings,
        "V2 amendment exact source bindings drifted",
    )
    offline = document.get("offlineAmendment", {})
    _require(
        offline.get("acquisitionPath") == "thread-created-auto-attach"
        and offline.get("observerBarrierBeforeCreatorThreadStart") is True
        and offline.get("creatorThreadEphemeral") is False
        and offline.get("creatorThreadSandbox") == "read-only"
        and offline.get("observerCallsSameThreadDirectly") is True
        and offline.get("observerThreadResumeCalls") == 0
        and offline.get("rolloutMaterializationRole") == "diagnostic-only"
        and offline.get("evidenceSealBeforeObserverPostWindowCall") is True
        and offline.get("failureCleanupClosesBothInjectedTransports") is True
        and offline.get("failureCleanupInvokesBoundedSentinelCleanup") is True
        and offline.get("modelTurnRequests") == 0,
        "V2 amendment acquisition or cleanup fact drifted",
    )
    deterministic = document.get("deterministicValidation", {})
    _require(
        deterministic.get("transport") == "injected-in-memory-fake-only"
        and deterministic.get("scenarioCount") == 16
        and all(
            deterministic.get(key) is True
            for key in (
                "exactRpcOrderCovered",
                "observerNoResumeCovered",
                "sameThreadBindingCovered",
                "sameExactSentinelBindingCovered",
                "rolloutAbsenceDiagnosticOnlyCovered",
                "sealBeforePostWindowCallCovered",
                "failureCleanupCovered",
            )
        )
        and all(
            deterministic.get(key) is False
            for key in (
                "liveAppServerStarted",
                "loopbackTransportOpened",
                "modelTurnRequested",
                "externalNetworkUsed",
                "configurationMutated",
            )
        ),
        "V2 amendment deterministic-validation boundary drifted",
    )
    formal = document.get("formalEvidenceBoundary", {})
    _require(
        formal
        == {
            "formalLiveRunCount": 0,
            "formalPairReportCount": 0,
            "liveHostOutcomeObserved": False,
            "offlineSimulationIsLiveEvidence": False,
        },
        "V2 amendment formal evidence boundary was promoted",
    )
    execution = document.get("executionBoundary", {})
    _require(
        execution.get("offlineSourceValidationAuthorized") is True
        and execution.get("offlineDeterministicSimulationAuthorized") is True
        and all(execution.get(key) is False for key in DENIED_EXECUTION_KEYS),
        "V2 amendment execution boundary was expanded",
    )
    claims = document.get("claimBoundary")
    _require(
        isinstance(claims, dict)
        and set(claims) == CLAIM_KEYS
        and all(value is False for value in claims.values()),
        "V2 amendment claim boundary was promoted",
    )
    next_gate = document.get("nextGate", {})
    _require(
        next_gate.get("disposition")
        == "offline-v2-ready-for-integration-review"
        and next_gate.get(
            "liveExecutionRequiresSeparateExplicitAuthorization"
        )
        is True
        and next_gate.get("liveExecutionAuthorizedByThisRecord") is False
        and next_gate.get("globalVerifierIntegrationDelegatedToMainThread")
        is True,
        "V2 amendment next-gate boundary drifted",
    )


def validate_documentation(root: Path) -> None:
    path = root / DOCUMENTATION_PATH
    _require(path.is_file(), "V2 amendment documentation is missing")
    text = path.read_text(encoding="utf-8")
    for phrase in (
        "offline-amendment-required-before-live",
        SHA256_BINDINGS[OLD_PROTOCOL_PATH],
        SHA256_BINDINGS[OLD_PROBE_PATH],
        "Connection B sends no `thread/resume`.",
        "Sixteen offline scenarios",
        "Formal live run count and formal pair",
        "remain zero",
        "Offline simulation is not live evidence.",
        "requires a separate explicit authorization decision.",
    ):
        _require(
            phrase in text,
            f"V2 amendment documentation boundary missing: {phrase}",
        )


def load_and_validate(*, root: Path = ROOT) -> None:
    for relative_path, expected_sha256 in SHA256_BINDINGS.items():
        path = root / relative_path
        _require(path.is_file(), f"Bound v2 source is missing: {relative_path}")
        _require(
            file_sha256(path) == expected_sha256,
            f"Bound v2 source SHA256 drifted: {relative_path}",
        )
    admission = load_json(root / ADMISSION_PATH)
    _require(
        admission.get("admissionDecision", {}).get("conclusion")
        == "offline-amendment-required-before-live"
        and admission.get("admissionDecision", {}).get(
            "liveRerunAuthorized"
        )
        is False,
        "Admission gate conclusion or no-live boundary drifted",
    )
    validate_protocol(load_json(root / PROTOCOL_PATH))
    validate_probe_source((root / PROBE_PATH).read_text(encoding="utf-8"))
    amendment = load_json(root / AMENDMENT_PATH)
    validate_amendment(amendment)
    _require(
        amendment.get("documentation") == DOCUMENTATION_PATH,
        "V2 amendment documentation binding drifted",
    )
    validate_documentation(root)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    load_and_validate(root=args.root.resolve())
    print("MCP creator-close auto-attach v2 offline validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
