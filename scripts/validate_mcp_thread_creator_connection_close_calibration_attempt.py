#!/usr/bin/env python3
"""Validate the invalid creator-connection-close calibration attempt."""

from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
RECORD_PATH = (
    "registry/"
    "mcp-thread-creator-connection-close-calibration-attempt-2026-07-27.json"
)
DOCUMENTATION_PATH = (
    "docs/"
    "mcp-thread-creator-connection-close-calibration-attempt-2026-07-27.md"
)
PROBE_PATH = (
    "scripts/probe_codex_app_server_mcp_thread_creator_connection_close.py"
)
PROTOCOL_PATH = (
    "registry/"
    "mcp-thread-creator-connection-close-attribution-protocol-2026-07-27.json"
)
ATTEMPT_PROBE_SHA256 = (
    "98B248688F98DECB35AE0B1F34DB4AA2DA819ED7DDF91BA3E4AC1C707AFCAC6"
)
CURRENT_PROBE_SHA256 = (
    "66CF7066B68D92139653C5E41AD74CAA64D00273C662A2899E396501974C2CF6"
)
SENTINEL_LOG_SHA256 = (
    "9630EEA400B3F4D5B60D1472802014197E560FCFA30963183B4658876E2B7AC1"
)
CONFIG_SHA256 = (
    "5526767B48F5D20EAC1C96ED16D5820D4E2A63322AF35A45A7F615D419D2C8E2"
)
NORMALIZED_EVIDENCE_PATH = (
    "audits/mcp-thread-creator-connection-close-calibration-attempt-"
    "2026-07-27/normalized-evidence.json"
)
NORMALIZED_EVIDENCE_SHA256 = (
    "6EC43BDD24F6C88E75EA5B5D0C7DECB84903F9453979446D6B9E872655BED4CC"
)
NORMALIZED_EVIDENCE_BYTES = 2545
SENTINEL_PID = 34556
SENTINEL_INSTANCE_ID = "b2456f9a-9163-49ab-9674-b325f3795e23"
SENTINEL_START_AT = "2026-07-27T01:32:19.527503+00:00"
SENTINEL_STOP_AT = "2026-07-27T01:32:50.444071+00:00"
ATTEMPT_ROOT = ".tmp/mcp-creator-close-calibration-20260727-01"
WORKSPACE_ROOT = (
    ".tmp/mcp-creator-close-calibration-workspace-20260727-01"
)
REQUESTED_OUTPUT = (
    ".tmp/mcp-creator-close-calibration-output-20260727-01"
)
SENTINEL_LOG_PATH = (
    f"{ATTEMPT_ROOT}/connected-control/codex-home/sentinel-events.jsonl"
)
CONFIG_PATH = (
    f"{ATTEMPT_ROOT}/connected-control/codex-home/config.toml"
)
FAILURE_PATH = (
    f"{ATTEMPT_ROOT}/connected-control/codex-home/sessions/2026/07/27/"
    "rollout-2026-07-27T09-32-19-019fa133-90af-74b0-83e8-"
    "31c069cfacce.jsonl"
)
EXPECTED_TOP_LEVEL_KEYS = {
    "schema",
    "id",
    "date",
    "status",
    "protocol",
    "probe",
    "attempt",
    "observedLocalEvidence",
    "configurationBoundary",
    "normalizedEvidence",
    "authorityIncident",
    "remediation",
    "cleanupBoundary",
    "claimBoundary",
    "nextGate",
    "documentation",
}
EXPECTED_CLAIM_KEYS = {
    "creatorConnectionCloseReleaseObserved",
    "creatorConnectionCloseRetentionObserved",
    "taskEndReleaseProved",
    "leaseOrReferenceCountProved",
    "resourceBenefitProved",
    "formalProtocolValidityProved",
    "selfAuthoredControllerNeedProved",
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def load_json_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    _require(isinstance(value, dict), f"JSON object required: {path}")
    return value


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not line.strip():
            continue
        value = json.loads(line)
        _require(
            isinstance(value, dict),
            f"Sentinel event line {line_number} is not an object",
        )
        events.append(value)
    return events


def _validate_documentation(record: dict[str, Any], *, root: Path) -> None:
    documentation_path = root / str(record.get("documentation"))
    _require(
        record.get("documentation") == DOCUMENTATION_PATH
        and documentation_path.is_file(),
        "Calibration documentation binding drifted",
    )
    text = documentation_path.read_text(encoding="utf-8")
    required_phrases = (
        "No `pair-report.json` was generated.",
        "broader orphan absence is not proved",
        "`loopbackTransportExecutionAuthorized=false`",
        ATTEMPT_PROBE_SHA256,
        CURRENT_PROBE_SHA256,
        "not the identity of the remediated probe",
        "no longer calls `wait_for_rollout`",
        "No live rerun was",
        ATTEMPT_ROOT,
        WORKSPACE_ROOT,
        "cleanup transaction removed them",
        "normalized-evidence.json",
        "proves no creator-connection-close release or",
        "lease or reference count",
        "resource",
        "self-authored controller",
    )
    for phrase in required_phrases:
        _require(
            phrase in text,
            f"Calibration documentation boundary missing: {phrase}",
        )


def _validate_probe_binding(record: dict[str, Any], *, root: Path) -> None:
    probe = record.get("probe")
    _require(
        isinstance(probe, dict)
        and probe
        == {
            "path": PROBE_PATH,
            "sha256AtAttempt": ATTEMPT_PROBE_SHA256,
            "sha256AtAttemptRole": "attempt-time-source-identity-only",
            "currentProbeMayDifferAfterRemediation": True,
            "currentSha256": CURRENT_PROBE_SHA256,
            "currentProbeContainsWaitForRollout": False,
        },
        "Calibration probe identity boundary drifted",
    )
    _require(
        ATTEMPT_PROBE_SHA256 != CURRENT_PROBE_SHA256,
        "Attempt-time probe identity was promoted to current identity",
    )
    current_probe_path = root / PROBE_PATH
    _require(
        current_probe_path.is_file()
        and file_sha256(current_probe_path) == CURRENT_PROBE_SHA256,
        "Current remediated probe SHA256 drifted",
    )
    current_source = current_probe_path.read_text(encoding="utf-8")
    _require(
        "def observe_rollout_materialization(" in current_source
        and "wait_for_rollout" not in current_source,
        "Current probe restored a blocking wait_for_rollout prerequisite",
    )


def _validate_attempt(record: dict[str, Any], *, root: Path) -> None:
    attempt = record.get("attempt")
    _require(
        isinstance(attempt, dict)
        and attempt
        == {
            "type": "calibration",
            "startedAt": SENTINEL_START_AT,
            "failedBeforePairedWindow": True,
            "pairedWindowEntered": False,
            "formalLivePairedRunCount": 0,
            "pairReportGenerated": False,
            "root": ATTEMPT_ROOT,
            "workspace": WORKSPACE_ROOT,
            "requestedOutput": REQUESTED_OUTPUT,
            "requestedOutputExists": False,
            "failureClass": (
                "runner-prerequisite-invalid-for-zero-turn-thread"
            ),
            "failureMessage": (
                "thread rollout did not materialize before the 30-second "
                "timeout"
            ),
            "failurePath": FAILURE_PATH,
            "failureIsHostReleaseOutcome": False,
        },
        "Calibration attempt boundary drifted",
    )
    _require(
        not (root / REQUESTED_OUTPUT).exists(),
        "Calibration requested output unexpectedly exists",
    )
    _require(
        not (root / FAILURE_PATH).exists(),
        "Zero-turn rollout unexpectedly materialized at the failure path",
    )
    pair_reports = [
        path
        for relative_root in (ATTEMPT_ROOT, WORKSPACE_ROOT)
        for path in (root / relative_root).rglob("pair-report.json")
    ]
    _require(
        not pair_reports,
        "Calibration pair report exists despite pre-window failure",
    )


def _validate_sentinel_evidence(
    record: dict[str, Any],
    *,
    root: Path,
) -> None:
    evidence = record.get("observedLocalEvidence")
    _require(
        isinstance(evidence, dict)
        and evidence
        == {
            "startedArmCount": 1,
            "startedArm": "connected-control",
            "sentinelEventLog": SENTINEL_LOG_PATH,
            "sentinelEventLogBytes": 789,
            "sentinelEventLogSha256": SENTINEL_LOG_SHA256,
            "sentinelInstanceStartAt": SENTINEL_START_AT,
            "sentinelInstanceStopAt": SENTINEL_STOP_AT,
            "sentinelPid": SENTINEL_PID,
            "sentinelInstanceId": SENTINEL_INSTANCE_ID,
            "sentinelPidAbsentAtPostFailureInspection": True,
            "broaderProcessFamilyAbsenceProved": False,
            "cimProcessFamilyInspectionSucceeded": False,
            "cimInspectionFailure": "access-denied",
        },
        "Calibration Sentinel evidence boundary drifted",
    )
    _require(
        not (root / SENTINEL_LOG_PATH).exists(),
        "Calibration raw Sentinel event log reappeared after cleanup",
    )


def _validate_normalized_evidence(
    record: dict[str, Any],
    *,
    root: Path,
) -> None:
    binding = record.get("normalizedEvidence")
    _require(
        isinstance(binding, dict)
        and binding
        == {
            "path": NORMALIZED_EVIDENCE_PATH,
            "bytes": NORMALIZED_EVIDENCE_BYTES,
            "sha256": NORMALIZED_EVIDENCE_SHA256,
            "allFiveSentinelEventsPreserved": True,
            "isolatedConfigSemanticsPreserved": True,
            "rawRuntimeStateRetained": False,
            "machineAbsolutePathsRetained": False,
            "secretMaterialRetained": False,
        },
        "Calibration normalized evidence binding drifted",
    )
    path = root / NORMALIZED_EVIDENCE_PATH
    _require(
        path.is_file()
        and path.stat().st_size == NORMALIZED_EVIDENCE_BYTES
        and file_sha256(path) == NORMALIZED_EVIDENCE_SHA256,
        "Calibration normalized evidence file drifted",
    )
    normalized = load_json_object(path)
    source = normalized.get("sourceArtifacts")
    _require(
        normalized.get("status")
        == "compact-semantic-evidence-preserved-before-temporary-root-cleanup"
        and isinstance(source, dict)
        and source.get("rawArtifactsRetained") is False
        and source.get("sentinelEventLog", {}).get("bytes") == 789
        and source.get("sentinelEventLog", {}).get("sha256")
        == SENTINEL_LOG_SHA256
        and source.get("isolatedConfig", {}).get("bytes") == 607
        and source.get("isolatedConfig", {}).get("sha256") == CONFIG_SHA256,
        "Calibration normalized source bindings drifted",
    )
    events = normalized.get("sentinelEvents")
    _require(
        isinstance(events, list) and len(events) == 5,
        "Calibration normalized Sentinel event count drifted",
    )
    starts = [event for event in events if event.get("event") == "instance-start"]
    stops = [event for event in events if event.get("event") == "instance-stop"]
    _require(
        starts
        == [
            {
                "timestamp": SENTINEL_START_AT,
                "event": "instance-start",
                "pid": SENTINEL_PID,
                "instanceId": SENTINEL_INSTANCE_ID,
            }
        ]
        and stops
        == [
            {
                "timestamp": SENTINEL_STOP_AT,
                "event": "instance-stop",
                "pid": SENTINEL_PID,
                "instanceId": SENTINEL_INSTANCE_ID,
            }
        ],
        "Calibration Sentinel start-stop identity drifted",
    )
    timestamps = [
        datetime.fromisoformat(str(event["timestamp"])) for event in events
    ]
    _require(
        timestamps == sorted(timestamps),
        "Calibration Sentinel event order drifted",
    )
    config = normalized.get("isolatedConfigSemantics")
    _require(
        isinstance(config, dict)
        and config.get("serverId") == "lifecycle_sentinel"
        and config.get("commandClass") == "python"
        and config.get("script") == "scripts/mcp_lifecycle_sentinel.py"
        and config.get("eventLogWasInsideTemporaryRoot") is True
        and config.get("cleanupMarkerWasInsideTemporaryRoot") is True
        and config.get("startupTimeoutSeconds") == 10
        and config.get("toolTimeoutSeconds") == 15
        and config.get("enabled") is True
        and config.get("accountStateCopied") is False
        and config.get("secretMaterialPreserved") is False
        and config.get("machineAbsolutePathsPreserved") is False,
        "Calibration normalized isolated config semantics drifted",
    )


def validate_attempt(
    record: dict[str, Any],
    *,
    root: Path = ROOT,
) -> None:
    _require(
        set(record) == EXPECTED_TOP_LEVEL_KEYS,
        "Calibration record top-level surface drifted",
    )
    _require(
        record.get("schema") == 1
        and record.get("id")
        == (
            "mcp-thread-creator-connection-close-calibration-attempt-"
            "2026-07-27"
        )
        and record.get("date") == "2026-07-27"
        and record.get("status")
        == (
            "invalid-pre-window-calibration-rollout-prerequisite-and-"
            "authority-conflict-recorded"
        ),
        "Calibration record identity or status drifted",
    )
    protocol = record.get("protocol")
    _require(
        isinstance(protocol, dict)
        and protocol
        == {
            "path": PROTOCOL_PATH,
            "sha256AtAttempt": (
                "8A110058AAC75DDC54E2B3795F6F6BE12004E4CDE0262045BEA79D112D157326"
            ),
            "loopbackTransportExecutionAuthorizedAtAttempt": False,
        },
        "Calibration protocol authority binding drifted",
    )
    _validate_probe_binding(record, root=root)
    _validate_attempt(record, root=root)
    _validate_sentinel_evidence(record, root=root)
    _validate_normalized_evidence(record, root=root)

    configuration = record.get("configurationBoundary")
    _require(
        isinstance(configuration, dict)
        and configuration
        == {
            "isolatedCodexHomeOnly": True,
            "isolatedConfig": CONFIG_PATH,
            "isolatedConfigBytes": 607,
            "isolatedConfigSha256": CONFIG_SHA256,
            "globalConfigurationMutationObserved": False,
            "accountStateCopied": False,
            "modelTurnRequestedByProbe": False,
            "externalNetworkTrafficInspected": False,
            "zeroNetworkTrafficClaimed": False,
        },
        "Calibration configuration boundary drifted",
    )
    _require(
        not (root / CONFIG_PATH).exists(),
        "Calibration raw isolated configuration reappeared after cleanup",
    )

    authority = record.get("authorityIncident")
    _require(
        isinstance(authority, dict)
        and authority
        == {
            "protocolLoopbackBoundaryWasFalse": True,
            "preWindowLoopbackCalibrationStarted": True,
            "formalPairedWindowStarted": False,
            "incidentDoesNotAuthorizeContinuation": True,
            "rerunRequiresExplicitLoopbackExecutionAuthorization": True,
        },
        "Calibration authority conflict boundary drifted",
    )
    remediation = record.get("remediation")
    _require(
        isinstance(remediation, dict)
        and remediation
        == {
            "zeroTurnRolloutAbsenceIsNowObservationNotGate": True,
            "probeWaitForRolloutRemoved": True,
            "deterministicRegressionTestAdded": True,
            "liveRerunPerformed": False,
        },
        "Calibration remediation or no-rerun boundary drifted",
    )
    cleanup = record.get("cleanupBoundary")
    _require(
        isinstance(cleanup, dict)
        and cleanup
        == {
            "rootsOriginallyRetained": [ATTEMPT_ROOT, WORKSPACE_ROOT],
            "deletionAuthorizedOn": "2026-07-30",
            "cleanupExecuted": True,
            "cleanupExecutionEvidence": (
                "registry/closeout-cleanup-execution-2026-07-30.json"
            ),
            "rootsAbsentAfterCleanup": True,
            "inventoryRegistrationRequired": False,
        },
        "Calibration cleanup retention boundary drifted",
    )
    for relative_root in cleanup["rootsOriginallyRetained"]:
        _require(
            not (root / relative_root).exists(),
            f"Cleaned calibration root reappeared: {relative_root}",
        )
    claims = record.get("claimBoundary")
    _require(
        isinstance(claims, dict)
        and set(claims) == EXPECTED_CLAIM_KEYS
        and all(value is False for value in claims.values()),
        "Calibration release/task-end/lease/resource/controller claim promoted",
    )
    _require(
        record.get("nextGate")
        == (
            "Do not rerun the loopback calibration or formal paired protocol "
            "until the user explicitly authorizes that live transport "
            "execution boundary; then use fresh exact roots and preserve "
            "this invalid attempt unchanged."
        ),
        "Calibration next gate drifted",
    )
    _validate_documentation(record, root=root)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--record", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.root.resolve()
    record_path = (
        args.record.resolve()
        if args.record is not None
        else (root / RECORD_PATH).resolve()
    )
    record = load_json_object(record_path)
    validate_attempt(record, root=root)
    print(
        "MCP thread creator connection-close calibration attempt "
        "validation passed."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
