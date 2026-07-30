#!/usr/bin/env python3
"""Fail-closed validation for creator-connection-close attribution protocol."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
PROTOCOL_PATH = (
    "registry/"
    "mcp-thread-creator-connection-close-attribution-protocol-2026-07-27.json"
)
PROTOCOL_SOURCE_SHA256 = (
    "8a110058aac75ddc54e2b3795f6f6be12004e4cde0262045bea79d112d157326"
)
BOUND_FILE_SHA256 = {
    "scripts/probe_codex_app_server_mcp_thread_creator_connection_close.py": (
        "66cf7066b68d92139653c5e41ad74caa64d00273c662a2899e396501974c2cf6"
    ),
    (
        "tests/fixtures/"
        "mcp-thread-creator-connection-close-attribution-2026-07-27.json"
    ): "ea985b4dc3f85109ce46cfc613c05398553fd38ef938142ffa709afbda311e9a",
    (
        "tests/"
        "test_codex_app_server_mcp_thread_creator_connection_close_probe.py"
    ): "a5a462bfdfacd1eda8a169ac39e700fb06819e7cb474ef41f56947fe7c407f43",
}
EXPECTED_ARMS = ["connected-control", "creator-connection-close"]
EXPECTED_TOP_LEVEL_KEYS = {
    "schemaVersion",
    "id",
    "status",
    "date",
    "question",
    "nonClaims",
    "design",
    "validityRequirements",
    "preRegisteredOutcomes",
    "failClosedReasons",
    "requiredArtifactsPerArm",
    "aggregateArtifacts",
    "executionBoundary",
}
EXPECTED_SETUP_SEQUENCE = [
    "Connection A initializes.",
    "Connection A starts one non-ephemeral read-only thread.",
    "Connection A calls Sentinel identity.",
    (
        "The parent binds the returned Sentinel PID and instance ID to an "
        "exact OS process identity whose parent is the app-server."
    ),
    (
        "Connection B initializes, reads configuration as a materialization "
        "barrier, resumes the same thread, and calls Sentinel identity."
    ),
    (
        "The parent requires A and B to report the same Sentinel PID and "
        "instance ID and revalidates that exact OS identity."
    ),
]
EXPECTED_VALIDITY_REQUIREMENTS = [
    (
        "Both arms use the same bound Codex executable/version and "
        "protocol/probe/dependency hashes."
    ),
    (
        "Each arm has one exact app-server identity and two distinct exact "
        "bridge identities."
    ),
    (
        "A and B bind to the same thread and exact Sentinel PID/instance at "
        "baseline."
    ),
    (
        "The exact Sentinel process is a child of the app-server and has one "
        "matching instance-start event."
    ),
    (
        "The treatment transport-action ledger contains exactly one "
        "creator-connection-close action; the control ledger is empty."
    ),
    "No host RPC is sent inside either window.",
    (
        "The treatment bridge-close evidence binds to connection A, exits "
        "without a harness kill, and records a clean WebSocket close."
    ),
    (
        "The control connection A, both connection B processes, and both "
        "app-servers meet their arm-specific liveness requirements through "
        "the window."
    ),
    (
        "Each arm contains exactly eleven samples with nonnegative skew no "
        "greater than 250 milliseconds."
    ),
    "No model turn request or notification is present.",
    "Configuration bytes remain equal to the pre-window bytes.",
    "No auth state is produced.",
    (
        "Window evidence is sealed before the observer post-window call."
    ),
    "Cleanup occurs only after the evidence boundary.",
]
EXPECTED_OUTCOMES = {
    "creator-connection-close-release-associated-bounded": (
        "Control retains the exact Sentinel and treatment has a matching "
        "stop event plus exact final process absence."
    ),
    "creator-connection-close-immediate-release-falsified-bounded": (
        "Both control and treatment retain the exact Sentinel through five "
        "seconds and the observer post-window call returns the same "
        "PID/instance."
    ),
    "inconclusive-valid-bounded": (
        "Both arm measurements are valid but the control does not establish "
        "the required retained baseline or the paired pattern is otherwise "
        "non-attributable."
    ),
    "invalid": (
        "Any identity, timing, action, RPC, liveness, configuration, "
        "model-turn, evidence-order, or cleanup validity requirement fails."
    ),
}
EXPECTED_NON_CLAIMS = {
    "The creator connection is a lease owner.",
    "A public or internal reference count exists.",
    "Connection close is task end.",
    (
        "The result generalizes beyond Codex CLI app-server 0.145.0 on "
        "Windows."
    ),
    "The result generalizes beyond the local Python Sentinel.",
    "The result proves stable resource benefit.",
    "The result proves zero network traffic.",
    (
        "The result proves a self-authored controller is or is not required."
    ),
}
EXPECTED_WINDOW_FORBIDDEN_ACTIONS = {
    "turn/start",
    "thread/start",
    "thread/resume",
    "thread/unsubscribe",
    "mcpServer/tool/call",
    "config/read",
    "config reload",
    "configuration write",
    "new thread",
    "process signal",
    "cleanup marker",
    "app-server teardown",
    "observer connection close",
}
EXPECTED_REQUIRED_ARTIFACTS = [
    "report.json",
    "process-samples.jsonl",
    "sentinel-events.jsonl",
    "rpc-ledger.json",
    "transport-actions.json",
    "bridge-events.jsonl",
    "stderr.log",
    "config-manifest.json",
]
EXPECTED_FAIL_CLOSED_REASONS = {
    "baseline-connections-not-distinct",
    "baseline-thread-id-mismatch",
    "baseline-sentinel-call-identity-mismatch",
    "baseline-sentinel-process-drift",
    "sentinel-start-binding-not-unique",
    "sample-count-mismatch",
    "sample-timing-skew",
    "app-server-not-alive-through-window",
    "observer-bridge-not-alive-through-window",
    "control-creator-bridge-not-alive-through-window",
    "treatment-creator-bridge-still-alive-at-window-end",
    "transport-action-ledger-mismatch",
    "creator-close-not-exactly-bound",
    "in-window-host-rpc-observed",
    "model-turn-observed",
    "configuration-drift",
    "auth-state-produced",
    "post-window-call-precedes-evidence-seal",
    "process-and-stop-evidence-do-not-converge",
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_json_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    _require(isinstance(value, dict), f"JSON object required: {path}")
    return value


def _exact_unique_strings(value: Any, expected: set[str], label: str) -> None:
    _require(
        isinstance(value, list)
        and all(isinstance(item, str) and item for item in value)
        and len(value) == len(set(value))
        and set(value) == expected,
        f"{label} drifted",
    )


def validate_bound_files(*, root: Path = ROOT) -> None:
    for relative_path, expected_sha256 in BOUND_FILE_SHA256.items():
        path = root / relative_path
        _require(path.is_file(), f"Bound file is missing: {relative_path}")
        _require(
            file_sha256(path) == expected_sha256,
            f"Bound file SHA256 drifted: {relative_path}",
        )
    probe_text = (
        root
        / "scripts/probe_codex_app_server_mcp_thread_creator_connection_close.py"
    ).read_text(encoding="utf-8")
    _require(
        "def observe_rollout_materialization(" in probe_text
        and "wait_for_rollout" not in probe_text,
        "Zero-turn rollout absence became a blocking probe prerequisite",
    )


def validate_protocol(
    document: dict[str, Any],
    *,
    root: Path = ROOT,
    verify_bound_files: bool = True,
) -> None:
    _require(
        set(document) == EXPECTED_TOP_LEVEL_KEYS,
        "Protocol top-level surface drifted",
    )
    _require(
        document.get("schemaVersion") == 1
        and document.get("id")
        == "MCP-THREAD-CREATOR-CONNECTION-CLOSE-ATTRIBUTION-01"
        and document.get("status") == "protocol-only-not-live-executed"
        and document.get("date") == "2026-07-27",
        "Protocol identity or status drifted",
    )
    _require(
        document.get("question")
        == (
            "On Codex CLI app-server 0.145.0 for Windows, while one observer "
            "WebSocket and the app-server remain alive, is closing only the "
            "WebSocket connection that created the loaded thread associated "
            "with release of the exact local Sentinel process within five "
            "seconds?"
        ),
        "Protocol falsifiable question drifted",
    )
    _exact_unique_strings(
        document.get("nonClaims"),
        EXPECTED_NON_CLAIMS,
        "Protocol forbidden claims",
    )

    design = document.get("design")
    _require(
        isinstance(design, dict)
        and set(design)
        == {
            "repetitions",
            "pairedArms",
            "perArm",
            "setupSequence",
            "window",
            "evidenceSeal",
            "postWindow",
            "teardown",
        }
        and design.get("repetitions") == 3
        and design.get("pairedArms") == EXPECTED_ARMS,
        "Protocol paired design drifted",
    )
    per_arm = design.get("perArm")
    _require(
        isinstance(per_arm, dict)
        and per_arm
        == {
            "isolatedCodexHome": True,
            "isolatedWorkspace": True,
            "appServerProcesses": 1,
            "webSocketBridgeProcesses": 2,
            "loadedThreads": 1,
            "sentinelInstancesAtBaseline": 1,
            "pluginsAndAppsDisabled": True,
            "currentAccountStateCopied": False,
            "currentUserConfigCopied": False,
            "modelTurns": 0,
        },
        "Protocol per-arm isolation drifted",
    )
    setup = design.get("setupSequence")
    _require(
        setup == EXPECTED_SETUP_SEQUENCE,
        "Protocol baseline binding sequence drifted",
    )
    window = design.get("window")
    _require(
        isinstance(window, dict)
        and set(window)
        == {
            "seconds",
            "sampleIntervalSeconds",
            "expectedSamplesPerArm",
            "maximumActionSkewMilliseconds",
            "maximumSampleSkewMilliseconds",
            "connectedControlAction",
            "creatorConnectionCloseAction",
            "allowedParentActions",
            "forbiddenActions",
        }
        and window.get("seconds") == 5
        and window.get("sampleIntervalSeconds") == 0.5
        and window.get("expectedSamplesPerArm") == 11
        and window.get("maximumActionSkewMilliseconds") == 100
        and window.get("maximumSampleSkewMilliseconds") == 250
        and window.get("connectedControlAction")
        == "No transport action and no host RPC."
        and window.get("creatorConnectionCloseAction")
        == (
            "Close only connection A bridge stdin/WebSocket. Do not send "
            "thread/unsubscribe, config reload, signal, cleanup marker, or "
            "any host RPC."
        ),
        "Protocol attribution window drifted",
    )
    _exact_unique_strings(
        window.get("forbiddenActions"),
        EXPECTED_WINDOW_FORBIDDEN_ACTIONS,
        "Protocol forbidden window actions",
    )
    _exact_unique_strings(
        window.get("allowedParentActions"),
        {
            (
                "sample exact process identities for app-server, Sentinel, "
                "connection A bridge, and connection B bridge"
            ),
            "read the local Sentinel event log",
            "record bridge lifecycle events",
        },
        "Protocol allowed parent actions",
    )
    _require(
        design.get("evidenceSeal")
        == (
            "Process samples, Sentinel events, RPC ledgers, transport-action "
            "ledger, bridge lifecycle evidence, and configuration bytes/hash "
            "are sealed before the observer post-window tool call."
        )
        and design.get("postWindow")
        == (
            "After the evidence seal only, connection B calls Sentinel "
            "identity to distinguish retained same instance, replacement "
            "instance, and call failure."
        )
        and design.get("teardown")
        == (
            "Harness teardown and Sentinel cleanup occur only after all "
            "post-window evidence is recorded."
        ),
        "Protocol evidence ordering drifted",
    )

    validity = document.get("validityRequirements")
    _require(
        validity == EXPECTED_VALIDITY_REQUIREMENTS,
        "Protocol validity requirements drifted",
    )
    _require(
        document.get("preRegisteredOutcomes") == EXPECTED_OUTCOMES,
        "Protocol preregistered outcomes drifted",
    )
    _exact_unique_strings(
        document.get("failClosedReasons"),
        EXPECTED_FAIL_CLOSED_REASONS,
        "Protocol fail-closed reason set",
    )
    _require(
        document.get("requiredArtifactsPerArm")
        == EXPECTED_REQUIRED_ARTIFACTS,
        "Protocol required artifact set drifted",
    )
    _require(
        document.get("aggregateArtifacts")
        == [
            "pair-report.json",
            (
                "registry/mcp-app-server-0.145.0-thread-creator-connection-"
                "close-attribution-evidence-2026-07-27.json"
            ),
            (
                "docs/mcp-app-server-0.145.0-thread-creator-connection-close-"
                "attribution-evidence-2026-07-27.md"
            ),
        ],
        "Protocol aggregate artifact set drifted",
    )
    _require(
        document.get("executionBoundary")
        == {
            "protocolAndDeterministicTestsAuthorized": True,
            "formalLivePairedRunsExecuted": False,
            "modelOrAccountUseAuthorized": False,
            "externalNetworkUseAuthorized": False,
            "loopbackTransportExecutionAuthorized": False,
            "globalConfigurationMutationAuthorized": False,
            "installationAuthorized": False,
        },
        "Protocol execution boundary was weakened",
    )
    if verify_bound_files:
        validate_bound_files(root=root)


def load_and_validate_protocol(
    *,
    root: Path = ROOT,
    protocol_path: Path | None = None,
) -> dict[str, Any]:
    path = (
        protocol_path.resolve()
        if protocol_path is not None
        else (root / PROTOCOL_PATH).resolve()
    )
    _require(path.is_file(), f"Protocol source is missing: {path}")
    _require(
        file_sha256(path) == PROTOCOL_SOURCE_SHA256,
        "Protocol source digest drifted",
    )
    document = _read_json_object(path)
    validate_protocol(document, root=root, verify_bound_files=True)
    return document


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--protocol", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    load_and_validate_protocol(
        root=args.root.resolve(),
        protocol_path=args.protocol,
    )
    print(
        "MCP thread creator connection-close attribution protocol "
        "validation passed."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
