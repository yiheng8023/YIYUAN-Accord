from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import base64
import ctypes
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import Mock, patch

from harness import task_validator_o4_continuous_self_correction as v1
from harness import task_validator_o4_continuous_self_correction_v2 as v2
from harness import task_validator_o4_continuous_self_correction_v3 as validator
from tests.product.test_o4_continuous_self_correction_validator import (
    DESTINATION_CARRIER_ID,
    SOURCE_CARRIER_ID,
    SOURCE_REVISION,
    TEST_CWD,
    raw_compaction_observations,
    raw_transition_observations,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def source_binding(
    *, native_sha256: str | None = None, native_bytes: int = 288_476_976
) -> dict[str, object]:
    return {
        "repository": "https://github.com/openai/codex",
        "releaseVersion": "0.148.0",
        "tag": "rust-v0.148.0",
        "tagObject": "ab52d1794d47d47ecaeb0ec37fc00fa31593ecf3",
        "peeledCommit": "3ba0f711642a888aec92a611a3f3b2211157ff89",
        "npmPackage": "@openai/codex",
        "npmPackageVersion": "0.148.0",
        "npmPackageIntegrity": (
            "sha512-bh5kH9+BMrFaHGmLeoSansPdfRksvr4UXzjQInns/KRO7r8VJ+6AAW+"
            "SqUsE8XcG3+OW/mI4EEy8Gpo9UDXGvQ=="
        ),
        "npmTarball": (
            "https://registry.npmjs.org/@openai/codex/-/codex-0.148.0.tgz"
        ),
        "nativePackageAlias": "@openai/codex-win32-x64",
        "nativePackageName": "@openai/codex",
        "nativePackageVersion": "0.148.0-win32-x64",
        "nativePackageIntegrity": (
            "sha512-/Jg8eYw0BqTGNUpnrzzWlK2kbu29NWg7t6pnUDEfxqpTUf+mK8r3"
            "okXQn60Zjbk9InYZ4d8SwSjrtOa+i5hSPw=="
        ),
        "nativePackageTarball": (
            "https://registry.npmjs.org/@openai/codex/-/"
            "codex-0.148.0-win32-x64.tgz"
        ),
        "platform": "win32-x64",
        "license": "Apache-2.0",
        "nativeExecutableSha256": (
            native_sha256
            if native_sha256 is not None
            else "2ad2cf8a732da68b8f141634f92db1a03016c5faf533a7225fbc0fb740130410"
        ),
        "nativeExecutableBytes": native_bytes,
        "nativeAuthenticodeStatus": "Valid",
        "nativeAuthenticodeSigner": (
            'CN="OpenAI OpCo, LLC", O="OpenAI OpCo, LLC", '
            "L=San Francisco, S=California, C=US"
        ),
        "nativeAuthenticodeCertificateSha256": "4" * 64,
        "nativeArchiveExecutableSha256": (
            native_sha256
            if native_sha256 is not None
            else "2ad2cf8a732da68b8f141634f92db1a03016c5faf533a7225fbc0fb740130410"
        ),
        "nativeArchiveExecutableBytes": native_bytes,
        "sourceBlobSha256s": {
            path: hashlib.sha256(path.encode("utf-8")).hexdigest()
            for path in validator.SOURCE_BLOB_PATHS
        },
        "protocolPath": "codex-rs/protocol/src/protocol.rs",
        "appServerPath": "codex-rs/app-server/README.md",
        "goalProtocolPath": (
            "codex-rs/app-server-protocol/src/protocol/v2/thread.rs"
        ),
        "notificationProtocolPath": (
            "codex-rs/app-server-protocol/src/protocol/common.rs"
        ),
        "threadDataPath": (
            "codex-rs/app-server-protocol/src/protocol/v2/thread_data.rs"
        ),
        "goalProcessorPath": (
            "codex-rs/app-server/src/request_processors/thread_goal_processor.rs"
        ),
        "requiredAppServerContract": validator.REQUIRED_APP_SERVER_CONTRACT,
    }


def user_chronology_baseline() -> dict[str, object]:
    return {
        "schema": 1,
        "source": "source-bound-pre-registration-user-chronology-v1",
        "sourceCarrierIdentitySha256": v1._canonical_sha256(SOURCE_CARRIER_ID),
        "userMessageCount": 1,
        "userMessageIdentitySha256": v1._canonical_sha256(["user-message-1"]),
        "userMessageContentIdentitySha256": v1._canonical_sha256(
            [[{"type": "text", "text": v1.CARRIER_GOAL_TEXT}]]
        ),
        "controlledGoalMessageSha256": v1.CARRIER_GOAL_SHA256,
        "threadReadResponseRecordSha256": "9" * 64,
    }


def snapshot_record(
    bound_source: dict[str, object],
    *, public_identity: str = "codex-native-snapshot.public-v1:" + "a" * 32,
) -> dict[str, object]:
    return {
        "schema": 1,
        "captureKind": "o4-task-scoped-native-execution-snapshot",
        "publicIdentity": public_identity,
        "state": "materialized-before-manifest-and-registration",
        "sourceReleaseVersion": bound_source["releaseVersion"],
        "sourceExecutableSha256": bound_source["nativeExecutableSha256"],
        "sourceExecutableBytes": bound_source["nativeExecutableBytes"],
        "snapshotExecutableSha256": bound_source["nativeExecutableSha256"],
        "snapshotExecutableBytes": bound_source["nativeExecutableBytes"],
        "sourceAndSnapshotByteIdentity": "equal",
        "snapshotVersionOutput": f"codex-cli {bound_source['releaseVersion']}",
        "authenticodeStatus": bound_source["nativeAuthenticodeStatus"],
        "authenticodeSigner": bound_source["nativeAuthenticodeSigner"],
        "authenticodeCertificateSha256": bound_source[
            "nativeAuthenticodeCertificateSha256"
        ],
        **validator.SNAPSHOT_POLICY,
    }


def attestation_binding() -> dict[str, object]:
    algorithm = b"ssh-ed25519"
    key = b"\x42" * 32
    blob = (
        len(algorithm).to_bytes(4, "big")
        + algorithm
        + len(key).to_bytes(4, "big")
        + key
    )
    encoded = base64.b64encode(blob).decode("ascii")
    return {
        "schema": 1,
        "scheme": "openssh-sshsig-ed25519",
        "publicIdentity": "o4-capture-attestation.public-v1:" + "d" * 32,
        "namespace": validator.ATTESTATION_NAMESPACE,
        "publicKey": "ssh-ed25519 " + encoded,
        "publicKeyFingerprint": "SHA256:"
        + base64.b64encode(hashlib.sha256(blob).digest())
        .decode("ascii")
        .rstrip("="),
        "keygenExecutableSha256": "e" * 64,
        "implementation": "OpenSSH-sshsig",
        "implementationVersion": "OpenSSH_for_Windows_9.5p1",
        "distribution": "Windows-inbox-OpenSSH",
        "sourceRepository": "https://github.com/PowerShell/Win32-OpenSSH",
        "license": "OpenSSH-BSD-style",
        "maturity": "operating-system-provided-established",
        "reuseBoundary": (
            "task-scoped-ed25519-sshsig-evidence-carrier-not-identity-or-"
            "authorization"
        ),
    }


def attestation_record() -> dict[str, object]:
    return {
        "schema": 1,
        "publicIdentity": "o4-capture-attestation.public-v1:" + "d" * 32,
        "namespace": validator.ATTESTATION_NAMESPACE,
        "payloadSha256": "f" * 64,
        "signatureBase64": base64.b64encode(b"fixture-signature").decode("ascii"),
    }


def launch_record(
    bound_source: dict[str, object],
    snapshot: dict[str, object],
    public_identity: str = "codex-app-server-launch.public-v1:" + "5" * 32,
) -> dict[str, object]:
    return {
        "schema": 1,
        "source": "task-scoped-native-snapshot-app-server-launch",
        "launchPublicIdentity": public_identity,
        "snapshotPublicIdentity": snapshot["publicIdentity"],
        "releaseVersion": bound_source["releaseVersion"],
        "processImageSha256": snapshot["snapshotExecutableSha256"],
        "processImageBytes": snapshot["snapshotExecutableBytes"],
        "processImageObservedFromHost": True,
        "command": "app-server",
        "cwdClass": "exact-authorized-isolate-root",
        "environmentClass": (
            "isolated-codex-home-plus-explicit-source-bound-network-environment"
        ),
        "ambientExecutableUsed": False,
    }


def private_scenario(
    scenario_identity: str,
    raw: list[dict[str, object]],
    bound_source: dict[str, object],
    snapshot: dict[str, object],
    launch_digit: str,
) -> dict[str, object]:
    for item in raw:
        report = item.get("report")
        if isinstance(report, dict) and "activeIncrement" in report:
            report["activeIncrement"] = validator.INCREMENT_ID
    transition = scenario_identity == v1.CARRIER_SCENARIO_IDENTITIES[1]
    chronology_request_id = 91 if transition else 90
    chronology = [
        {
            "source": "codex-app-server-json-rpc-v0.147.0",
            "message": {
                "method": "thread/read",
                "id": chronology_request_id,
                "params": {"threadId": SOURCE_CARRIER_ID, "includeTurns": True},
            },
        },
        {
            "source": "codex-app-server-json-rpc-v0.147.0",
            "message": {
                "id": chronology_request_id,
                "result": {
                    "thread": {
                        "id": SOURCE_CARRIER_ID,
                        "turns": [
                            {
                                "id": "turn-user-1",
                                "items": [
                                    {
                                        "type": "userMessage",
                                        "id": "user-message-1",
                                        "content": [
                                            {"type": "text", "text": v1.CARRIER_GOAL_TEXT}
                                        ],
                                    }
                                ],
                            }
                        ],
                    }
                },
            },
        },
    ]
    raw = [*chronology, *raw]
    if not transition:
        post_compaction_chronology = deepcopy(chronology)
        post_compaction_chronology[0]["message"]["id"] = chronology_request_id + 100
        post_compaction_chronology[1]["message"]["id"] = chronology_request_id + 100
        for index, item in enumerate(raw):
            message = item.get("message") if isinstance(item, dict) else None
            params = message.get("params") if isinstance(message, dict) else None
            compacted_item = params.get("item") if isinstance(params, dict) else None
            if (
                isinstance(message, dict)
                and message.get("method") == "item/completed"
                and isinstance(compacted_item, dict)
                and compacted_item.get("type") == "contextCompaction"
            ):
                raw[index + 1 : index + 1] = post_compaction_chronology
                break
    launch = launch_record(
        bound_source,
        snapshot,
        "codex-app-server-launch.public-v1:" + launch_digit * 32,
    )
    bound_raw = [
        validator.bind_snapshot_app_server_message(
            launch, bound_source, snapshot, item["message"]
        )
        if item.get("source") == "codex-app-server-json-rpc-v0.147.0"
        else item
        for item in raw
    ]
    preflight = {
        "source": "task-scoped-native-snapshot-preflight",
        "snapshotPublicIdentity": snapshot["publicIdentity"],
        "releaseVersion": bound_source["releaseVersion"],
        "registeredSha256": snapshot["snapshotExecutableSha256"],
        "observedExecutableSha256": snapshot["snapshotExecutableSha256"],
        "observedExecutableBytes": snapshot["snapshotExecutableBytes"],
        "versionOutput": snapshot["snapshotVersionOutput"],
        "ambientExecutableUsed": False,
    }
    terminal = validator.snapshot_app_server_terminal_observation(
        launch,
        bound_source,
        snapshot,
        return_code=0,
        termination_route="stdin-close-clean-exit-after-thread-archive",
    )
    if transition:
        bound_raw.insert(
            0,
            {
                "source": "task-bound-effective-context-window-observer-v3",
                "carrierId": SOURCE_CARRIER_ID,
                "effectiveContextWindowTokens": None,
                "usedContextTokens": None,
                "usedContextBasisPoints": None,
                "usageBand": "unknown",
                "tokenUsageRecordOrdinal": None,
                "tokenUsageRecordSha256": None,
                "calibrationBands": deepcopy(
                    validator.TRANSITION_AND_CLEANUP_BOUNDARY[
                        "taskScopedContextCalibrationBands"
                    ]
                ),
                "turnCountRecommendationState": (
                    "not-established-by-bound-official-source"
                ),
                "turnCountRecommendation": None,
                "automaticCompactionCount": 0,
                "manualCompactionCount": 1,
                "opaqueCompactionSummaryCountProxy": 1,
                "userChronologyBaselineCount": 1,
                "userChronologyCurrentCount": 1,
                "userChronologyBaselineSha256": v1._canonical_sha256(
                    ["user-message-1"]
                ),
                "userChronologyCurrentSha256": v1._canonical_sha256(
                    ["user-message-1"]
                ),
                "userChronologyBaselineContentSha256": v1._canonical_sha256(
                    [[{"type": "text", "text": v1.CARRIER_GOAL_TEXT}]]
                ),
                "userChronologyCurrentContentSha256": v1._canonical_sha256(
                    [[{"type": "text", "text": v1.CARRIER_GOAL_TEXT}]]
                ),
                "sourceCarrierIdentitySha256": v1._canonical_sha256(
                    SOURCE_CARRIER_ID
                ),
                "userInitiatedHandoffObserved": False,
                "agentTransitionTriggeredBeforeUserIntervention": True,
            },
        )
    return {
        "scenarioIdentity": scenario_identity,
        "sourceCarrierId": SOURCE_CARRIER_ID,
        "expectedHead": SOURCE_REVISION,
        "destinationCarrierId": DESTINATION_CARRIER_ID if transition else None,
        "expectedCwd": TEST_CWD if transition else None,
        "rawObservations": [launch, preflight, *bound_raw, terminal],
    }


def passing_fault_suite(source_revision: str) -> dict[str, object]:
    return {
        "schema": 1,
        "suiteIdentity": validator.SUITE_IDENTITY,
        "sourceRevision": source_revision,
        "faultScenarioResults": [
            {
                "scenarioIdentity": scenario.scenario_identity,
                "scenarioClass": scenario.scenario_class,
                "mutationIdentity": scenario.mutation_identity,
                "expectedDiagnostic": scenario.expected_diagnostic,
                "baselineValid": True,
                "divergenceDetected": True,
                "expectedDiagnosticObserved": True,
                "recoveredValid": True,
                "recoveredHeadMatches": True,
                "probeCleanupVerified": True,
                "faultReportSha256": str(index + 1) * 64,
                "recoveryReportSha256": str(index + 5) * 64,
            }
            for index, scenario in enumerate(validator.FAULT_SCENARIOS)
        ],
        "allFaultControlsObserved": True,
        "cleanupVerified": True,
    }


def passing_material_checkpoint_binding(
    fault_suite: dict[str, object],
    projections: list[dict[str, object]],
    baseline_revision: str = SOURCE_REVISION,
) -> dict[str, object]:
    results = fault_suite["faultScenarioResults"]
    assert isinstance(results, list)
    checkpoint_evidence = projections[0]["materialCheckpointEvidence"]
    assert isinstance(checkpoint_evidence, dict)
    reconciliation_sha256 = str(
        checkpoint_evidence["reconciliationEventShapeSha256"]
    )
    verifier_report_sha256 = str(checkpoint_evidence["verifierReportSha256"])
    identities = [
        *[
            "fault-recovery:"
            + str(item["scenarioIdentity"])
            + ":"
            + str(item["faultReportSha256"])
            + ":"
            + str(item["recoveryReportSha256"])
            for item in results
            if isinstance(item, dict)
        ],
        "post-compaction-goal-authority-reconciliation-v1:"
        + reconciliation_sha256,
        "canonical-verifier:" + verifier_report_sha256,
        "git-clean-head:" + baseline_revision,
    ]
    return {
        "schema": 1,
        "checkpointIdentities": identities,
        "materialCheckpointCount": 7,
        "faultSuiteSha256": v1._canonical_sha256(fault_suite),
        "reconciliationEventShapeSha256": reconciliation_sha256,
        "verifierRecordSha256": checkpoint_evidence["verifierRecordSha256"],
        "verifierReportSha256": verifier_report_sha256,
        "gitRecordSha256": checkpoint_evidence["gitRecordSha256"],
        "gitHead": baseline_revision,
    }


def capture_thread_read_chronology(
    process: object,
    capture: object,
    bound_source: dict[str, object],
    snapshot: dict[str, object],
    *,
    request_id: int = 91,
    user_message_ids: tuple[str, ...] = ("user-message-1",),
) -> None:
    request = {
        "method": "thread/read",
        "id": request_id,
        "params": {"threadId": SOURCE_CARRIER_ID, "includeTurns": True},
    }
    response = {
        "id": request_id,
        "result": {
            "thread": {
                "id": SOURCE_CARRIER_ID,
                "turns": [
                    {
                        "id": "turn-user-chronology",
                        "items": [
                            {
                                "type": "userMessage",
                                "id": item_id,
                                "content": [
                                    {
                                        "type": "text",
                                        "text": (
                                            v1.CARRIER_GOAL_TEXT
                                            if item_id == "user-message-1"
                                            else "Please hand off now."
                                        ),
                                    }
                                ],
                            }
                            for item_id in user_message_ids
                        ],
                    }
                ],
            }
        },
    }
    process.stdin = io.BytesIO()
    process.stdout = io.BytesIO(
        json.dumps(response, sort_keys=True, separators=(",", ":")).encode("utf-8")
        + b"\n"
    )
    validator.write_snapshot_app_server_message(process, request)
    observed = validator.read_snapshot_app_server_message(
        process,
        capture.launch,
        bound_source,
        snapshot,
    )
    assert observed["message"] == response


def captured_scenario(
    value: dict[str, object],
    bound_source: dict[str, object],
    snapshot: dict[str, object],
    isolate_root: Path,
    suite: object,
) -> object:
    captured_value = deepcopy(value)
    raw = captured_value["rawObservations"]
    assert isinstance(raw, list)
    capture = validator._LiveAppServerCapture(
        raw[0],
        raw[1],
        bound_source,
        snapshot,
        isolate_root,
        suite,
    )
    messages = deepcopy(raw[2:-1])
    server_messages = []
    for record in messages:
        if not isinstance(record, dict) or not str(record.get("source", "")).startswith(
            "codex-app-server-json-rpc-v"
        ):
            continue
        message = record["message"]
        assert isinstance(message, dict)
        if not ("id" in message and "method" in message):
            server_messages.append(message)
    stdout = b"".join(
        json.dumps(message, sort_keys=True, separators=(",", ":")).encode("utf-8")
        + b"\n"
        for message in server_messages
    )
    process = Mock()
    process.stdin = io.BytesIO()
    process.stdout = io.BytesIO(stdout)
    process.stderr = io.BytesIO(b"")
    process.wait.return_value = 0
    process.poll.return_value = 0
    process._o4_native_snapshot_launch = True
    process._o4_live_capture = capture
    process._o4_bounded_streams = validator._BoundedAppServerStreams(process)
    verifier_seen = False
    skip_git = False
    for record in messages:
        assert isinstance(record, dict)
        source = record.get("source")
        if source == "task-bound-carrier-fitness-observer-v1":
            validator.capture_unknown_capacity_transition_signal(
                process, str(captured_value["sourceCarrierId"])
            )
        elif source == "python--B--m-harness-verify-json":
            report = deepcopy(record["report"])
            assert isinstance(report, dict)
            if captured_value["scenarioIdentity"] == v1.CARRIER_SCENARIO_IDENTITIES[1]:
                release_records = [
                    item
                    for item in messages
                    if isinstance(item, dict)
                    and item.get("source")
                    == "harness-source-carrier-release-preflight-v1"
                ]
                assert len(release_records) == 1
                report["sourceCarrierRelease"] = deepcopy(
                    release_records[0]["report"]
                )
            fault_suite = passing_fault_suite(str(captured_value["expectedHead"]))
            with (
                patch("harness.control.verify_product", return_value=report),
                patch(
                    "harness.control._evidence_git",
                    side_effect=[
                        (str(captured_value["expectedHead"]) + "\n").encode(
                            "ascii"
                        ),
                        b"",
                    ],
                ),
                patch.object(
                    validator,
                    "run_fault_suite",
                    return_value=fault_suite,
                ),
            ):
                validator.capture_repository_checkpoint(
                    process,
                    Path("."),
                    str(record["carrierId"]),
                    str(captured_value["expectedHead"]),
                )
            verifier_seen = True
            skip_git = True
        elif source == "git-rev-parse-and-status-v1" and skip_git:
            skip_git = False
        elif source == "harness-source-carrier-release-preflight-v1":
            validator.capture_source_carrier_release_preflight(
                process, str(captured_value["sourceCarrierId"])
            )
        elif isinstance(source, str) and source.startswith(
            "codex-app-server-json-rpc-v"
        ):
            message = record["message"]
            assert isinstance(message, dict)
            if "id" in message and "method" in message:
                validator.write_snapshot_app_server_message(process, message)
            else:
                observed = validator.read_snapshot_app_server_message(
                    process,
                    capture.launch,
                    bound_source,
                    snapshot,
                )
                assert observed == record
    assert verifier_seen
    kernel32 = ctypes.WinDLL("Kernel32.dll", use_last_error=True)
    create_event = kernel32.CreateEventW
    create_event.argtypes = [ctypes.c_void_p, ctypes.c_bool, ctypes.c_bool, ctypes.c_wchar_p]
    create_event.restype = ctypes.c_void_p
    handle = create_event(None, True, True, None)
    assert handle
    process._handle = int(handle)
    try:
        terminal = validator.close_task_scoped_snapshot_app_server(
            process,
            capture.launch,
            bound_source,
            snapshot,
        )
        assert terminal == raw[-1]
    finally:
        kernel32.CloseHandle(ctypes.c_void_p(handle))
    return validator.finalize_live_app_server_scenario(
        process,
        str(captured_value["scenarioIdentity"]),
        bound_source,
        snapshot,
        str(captured_value["sourceCarrierId"]),
        str(captured_value["expectedHead"]),
        destination_carrier_id=captured_value["destinationCarrierId"],
        expected_cwd=captured_value["expectedCwd"],
    )


def snapshot_cleanup_record(
    snapshot: dict[str, object], reason: str = "accepted"
) -> dict[str, object]:
    return {
        "schema": 1,
        "source": "task-scoped-native-snapshot-terminal-cleanup",
        "snapshotPublicIdentity": snapshot["publicIdentity"],
        "snapshotSha256": snapshot["snapshotExecutableSha256"],
        "reason": reason,
        "snapshotPresentBeforeCleanup": True,
        "snapshotAbsentAfterCleanup": True,
        "taskParentAbsentAfterCleanup": True,
        "privatePathPublished": False,
    }


def registration_values(
    bound_source: dict[str, object],
    snapshot: dict[str, object],
    public_attestation: dict[str, object],
    source_attestation: dict[str, object],
    chronology_baseline: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "normativeProfileIdentity": "bound-by-core",
        "cohortProtocolIdentity": "bound-by-core",
        "profileSha256": "b" * 64,
        "cohortProtocolSha256": "c" * 64,
        "environmentAttributionBinding": {
            "manifestLocator": "bound-by-core",
            "manifestRevision": SOURCE_REVISION,
        },
        "counterexampleIdentityAndSource": validator.counterexample_sources(
            bound_source
        ),
        "startingAuthorityGoalAndCarrierState": {
            "registrationRevisionRule": v1.REGISTRATION_REVISION_RULE,
            "measurementBaselineRevisionRule": v1.MEASUREMENT_BASELINE_REVISION_RULE,
            "authorityPaths": [
                "product/constitution.json",
                "product/program.json",
                "product/acceptance.json",
            ],
            "goalBoundary": (
                "registered-o4-controlled-carrier-goal-under-current-v1.2-acceptance"
            ),
            "controlledGoalArtifact": validator.CARRIER_GOAL_BINDING,
            "carrierState": {
                "repository": "single-main-checkout-clean-at-scenario-start",
                "sourceConversation": (
                    "native-active-goal-observed-before-compaction-or-transition-and-"
                    "cleared-only-after-destination-verification"
                ),
                "destinationConversation": (
                    "fresh-thread-started-with-zero-inherited-turns-then-exact-active-"
                    "goal-installed-from-this-registration"
                ),
                "capacitySignal": "reliable-risk-or-explicit-unknown-rule-only",
            },
            "officialCodexSource": bound_source,
            "taskScopedNativeExecution": validator._snapshot_registration_binding(
                snapshot
            ),
            "taskScopedCaptureAttestation": public_attestation,
        },
        "injectedOrObservedFailure": validator.FAILURE_BINDINGS,
        "expectedDetectionAndCorrection": validator.CORRECTION_BINDINGS,
        "transitionAndCleanupBoundary": validator.TRANSITION_AND_CLEANUP_BOUNDARY,
        "scenarioValidator": {
            "suiteIdentity": validator.SUITE_IDENTITY,
            "scenarioIdentities": list(validator.SCENARIO_IDENTITIES),
            "validatorIdentity": validator.VALIDATOR_KIND,
            "validatorLocator": validator.VALIDATOR_LOCATOR,
            "hostProjectionBuilder": (
                f"{validator.VALIDATOR_LOCATOR}:project_raw_carrier_observations"
            ),
            "captureSuiteBuilder": (
                f"{validator.VALIDATOR_LOCATOR}:begin_task_scoped_capture_suite"
            ),
            "preRegistrationCaptureSuiteBuilder": (
                f"{validator.VALIDATOR_LOCATOR}:begin_pre_registration_capture_suite"
            ),
            "sourceUserChronologyBaselineBuilder": (
                f"{validator.VALIDATOR_LOCATOR}:capture_source_user_chronology_baseline"
            ),
            "snapshotLaunchBuilder": (
                f"{validator.VALIDATOR_LOCATOR}:launch_task_scoped_snapshot_app_server"
            ),
            "snapshotRequestWriter": (
                f"{validator.VALIDATOR_LOCATOR}:write_snapshot_app_server_message"
            ),
            "snapshotResponseReader": (
                f"{validator.VALIDATOR_LOCATOR}:read_snapshot_app_server_message"
            ),
            "repositoryCheckpointRecorder": (
                f"{validator.VALIDATOR_LOCATOR}:capture_repository_checkpoint"
            ),
            "carrierFitnessRecorder": (
                f"{validator.VALIDATOR_LOCATOR}:capture_unknown_capacity_transition_signal"
            ),
            "sourceReleaseRecorder": (
                f"{validator.VALIDATOR_LOCATOR}:capture_source_carrier_release_preflight"
            ),
            "sourcePreparationBuilder": (
                f"{validator.VALIDATOR_LOCATOR}:seal_source_preparation_attestation"
            ),
            "privateMeasurementBuilder": (
                f"{validator.VALIDATOR_LOCATOR}:persist_and_attest_private_measurement"
            ),
            "liveScenarioBuilder": (
                f"{validator.VALIDATOR_LOCATOR}:finalize_live_app_server_scenario"
            ),
            "snapshotCleanupBuilder": (
                f"{validator.VALIDATOR_LOCATOR}:cleanup_task_scoped_native_snapshot"
            ),
            "publicObservationBuilder": (
                f"{validator.VALIDATOR_LOCATOR}:finalize_public_measurement_observation"
            ),
            "codexSourceBinding": bound_source,
            "taskScopedNativeSnapshot": validator._snapshot_registration_binding(
                snapshot
            ),
            "taskScopedCaptureAttestation": public_attestation,
            "sourcePreparationAttestation": source_attestation,
            "sourceUserChronologyBaseline": (
                deepcopy(chronology_baseline)
                if chronology_baseline is not None
                else user_chronology_baseline()
            ),
            "controlledGoalArtifact": validator.CARRIER_GOAL_BINDING,
            "receiptOnlyAccepted": False,
        },
    }


def run_git(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
        text=True,
    )
    return completed.stdout.strip()


def write_json(path: Path, value: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


class O4ContinuousSelfCorrectionV3ValidatorTests(unittest.TestCase):
    def test_source_preparation_signature_is_bound_to_manifest_revision(self) -> None:
        bound_source = source_binding()
        snapshot = snapshot_record(bound_source)
        environment_binding = {
            "manifestLocator": "bound-by-core",
            "manifestRevision": SOURCE_REVISION,
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            public_attestation = validator.create_task_attestation_key(
                root, "o4-capture-attestation.public-v1:" + "7" * 32
            )
            with (
                patch.object(
                    validator,
                    "_manifest_runtime_bindings",
                    return_value=(bound_source, snapshot, public_attestation),
                ),
                patch.object(
                    validator,
                    "verified_task_scoped_snapshot_executable",
                    return_value=Path("codex.exe"),
                ),
                patch.object(
                    validator, "_default_official_source_probe", return_value=True
                ),
            ):
                isolate = root / "isolate"
                isolate.mkdir()
                suite = validator._LiveO4CaptureSuite(isolate, snapshot, None)
                scenario = private_scenario(
                    v1.CARRIER_SCENARIO_IDENTITIES[0],
                    raw_compaction_observations(),
                    bound_source,
                    snapshot,
                    "0",
                )
                raw = scenario["rawObservations"]
                capture = validator._LiveAppServerCapture(
                    raw[0], raw[1], bound_source, snapshot, isolate, suite
                )
                process = Mock()
                process._o4_native_snapshot_launch = True
                process._o4_live_capture = capture
                capture_thread_read_chronology(
                    process, capture, bound_source, snapshot, request_id=70
                )
                chronology = validator.capture_source_user_chronology_baseline(
                    REPO_ROOT, process, SOURCE_CARRIER_ID
                )
                signature = validator.seal_source_preparation_attestation(
                    Path("."),
                    isolate,
                    root,
                    environment_binding,
                    bound_source,
                    snapshot,
                    public_attestation,
                    chronology,
                )
                late_suite = validator._LiveO4CaptureSuite(isolate, snapshot, None)
                late_capture = validator._LiveAppServerCapture(
                    raw[0], raw[1], bound_source, snapshot, isolate, late_suite
                )
                late_process = Mock()
                late_process._o4_native_snapshot_launch = True
                late_process._o4_live_capture = late_capture
                capture_thread_read_chronology(
                    late_process,
                    late_capture,
                    bound_source,
                    snapshot,
                    request_id=71,
                )
                late_chronology = validator.capture_source_user_chronology_baseline(
                    REPO_ROOT, late_process, SOURCE_CARRIER_ID
                )
                capture_thread_read_chronology(
                    late_process,
                    late_capture,
                    bound_source,
                    snapshot,
                    request_id=72,
                    user_message_ids=("user-message-1", "user-handoff-request"),
                )
                with self.assertRaisesRegex(ValueError, "token is required"):
                    validator.seal_source_preparation_attestation(
                        Path("."),
                        isolate,
                        root,
                        environment_binding,
                        bound_source,
                        snapshot,
                        public_attestation,
                        late_chronology,
                    )
                poisoned_suite = validator._LiveO4CaptureSuite(
                    isolate, snapshot, None
                )
                poisoned_capture = validator._LiveAppServerCapture(
                    raw[0],
                    raw[1],
                    bound_source,
                    snapshot,
                    isolate,
                    poisoned_suite,
                )
                poisoned_process = Mock()
                poisoned_process._o4_native_snapshot_launch = True
                poisoned_process._o4_live_capture = poisoned_capture
                capture_thread_read_chronology(
                    poisoned_process,
                    poisoned_capture,
                    bound_source,
                    snapshot,
                    request_id=73,
                )
                poisoned_chronology = (
                    validator.capture_source_user_chronology_baseline(
                        REPO_ROOT, poisoned_process, SOURCE_CARRIER_ID
                    )
                )
                poisoned_capture._poison()
                with self.assertRaisesRegex(ValueError, "token is required"):
                    validator.seal_source_preparation_attestation(
                        Path("."),
                        isolate,
                        root,
                        environment_binding,
                        bound_source,
                        snapshot,
                        public_attestation,
                        poisoned_chronology,
                    )
            increment = {
                "id": validator.INCREMENT_ID,
                "taskRegistration": {
                    "locator": validator.REGISTRATION_LOCATOR,
                    "sourceRevision": SOURCE_REVISION,
                },
            }
            registration = {
                "incrementId": validator.INCREMENT_ID,
                "criterionIds": ["O4"],
                "preRegistrationValues": registration_values(
                    bound_source,
                    snapshot,
                    public_attestation,
                    signature,
                    dict(chronology),
                ),
                "preMeasurementValidator": {
                    "kind": validator.VALIDATOR_KIND,
                    "version": 1,
                    "locator": validator.VALIDATOR_LOCATOR,
                },
            }
            errors: list[str] = []
            with (
                patch.object(
                    validator,
                    "_manifest_runtime_bindings",
                    return_value=(bound_source, snapshot, public_attestation),
                ),
                patch.object(
                    validator, "_git_revision_is_strict_ancestor", return_value=True
                ),
                patch.object(v1, "_goal_artifact_committed", return_value=True),
            ):
                self.assertTrue(
                    validator.validate_registration(
                        registration, increment, ("O4",), Path("."), errors
                    ),
                    errors,
                )
                changed = deepcopy(registration)
                changed["preRegistrationValues"]["environmentAttributionBinding"][
                    "manifestRevision"
                ] = "9" * 40
                errors = []
                self.assertFalse(
                    validator.validate_registration(
                        changed, increment, ("O4",), Path("."), errors
                    )
                )
            self.assertIn(
                "O4 third-generation source preparation attestation is not verifiable",
                errors,
            )

    def test_private_projection_parallel_stress_is_deterministic(self) -> None:
        bound_source = source_binding()
        snapshot = snapshot_record(bound_source)
        value = {
            "schema": 1,
            "suiteIdentity": validator.SUITE_IDENTITY,
            "state": "measurement-complete-live-private-source",
            "sourceBinding": bound_source,
            "snapshotBinding": snapshot,
            "registrationSourceRevision": SOURCE_REVISION,
            "measurementBaselineRevision": SOURCE_REVISION,
            "scenarios": [
                private_scenario(
                    v1.CARRIER_SCENARIO_IDENTITIES[0],
                    raw_compaction_observations(),
                    bound_source,
                    snapshot,
                    "b",
                ),
                private_scenario(
                    v1.CARRIER_SCENARIO_IDENTITIES[1],
                    raw_transition_observations(),
                    bound_source,
                    snapshot,
                    "c",
                ),
            ],
            "snapshotCleanup": snapshot_cleanup_record(snapshot),
        }

        def replay(_: int) -> str:
            result = validator._replay_private_measurement_value(
                value, bound_source, snapshot, SOURCE_REVISION, SOURCE_REVISION
            )
            if result is None:
                raise AssertionError("private O4 stress replay failed")
            return hashlib.sha256(
                json.dumps(
                    result,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            ).hexdigest()

        with ThreadPoolExecutor(max_workers=8) as executor:
            digests = list(executor.map(replay, range(256 * 8)))
        self.assertEqual(len(digests), 2048)
        self.assertEqual(len(set(digests)), 1)

    def test_private_measurement_is_required_replayable_and_exactly_released(self) -> None:
        bound_source = source_binding()
        snapshot = snapshot_record(bound_source)
        scenarios = [
            private_scenario(
                v1.CARRIER_SCENARIO_IDENTITIES[0],
                raw_compaction_observations(),
                bound_source,
                snapshot,
                "7",
            ),
            private_scenario(
                v1.CARRIER_SCENARIO_IDENTITIES[1],
                raw_transition_observations(),
                bound_source,
                snapshot,
                "8",
            ),
        ]
        cleanup = snapshot_cleanup_record(snapshot)
        with tempfile.TemporaryDirectory() as directory:
            private_root = Path(directory) / "raw"
            private_root.mkdir()
            self.assertIsNone(
                validator._load_private_measurement(
                    private_root,
                    bound_source,
                    snapshot,
                    SOURCE_REVISION,
                    SOURCE_REVISION,
                )
            )
            validator.persist_private_measurement(
                private_root,
                bound_source,
                snapshot,
                SOURCE_REVISION,
                SOURCE_REVISION,
                scenarios,
                cleanup,
            )
            replay = validator._load_private_measurement(
                private_root,
                bound_source,
                snapshot,
                SOURCE_REVISION,
                SOURCE_REVISION,
            )
            self.assertIsNotNone(replay)
            assert replay is not None
            self.assertEqual(
                [item["scenarioIdentity"] for item in replay[0]],
                list(v1.CARRIER_SCENARIO_IDENTITIES),
            )
            record = validator.cleanup_private_measurement(
                private_root, snapshot, reason="claim-revoked"
            )
            self.assertTrue(record["privateMeasurementAbsentAfterCleanup"])
            self.assertIsNone(
                validator._load_private_measurement(
                    private_root,
                    bound_source,
                    snapshot,
                    SOURCE_REVISION,
                    SOURCE_REVISION,
                )
            )
            self.assertFalse(private_root.exists())

    def test_public_measurement_signature_survives_raw_and_key_cleanup(self) -> None:
        bound_source = source_binding()
        snapshot = snapshot_record(bound_source)
        scenarios = [
            private_scenario(
                v1.CARRIER_SCENARIO_IDENTITIES[0],
                raw_compaction_observations(),
                bound_source,
                snapshot,
                "1",
            ),
            private_scenario(
                v1.CARRIER_SCENARIO_IDENTITIES[1],
                raw_transition_observations(),
                bound_source,
                snapshot,
                "2",
            ),
        ]
        cleanup = snapshot_cleanup_record(snapshot)
        value = {
            "schema": 1,
            "suiteIdentity": validator.SUITE_IDENTITY,
            "state": "measurement-complete-live-private-source",
            "sourceBinding": bound_source,
            "snapshotBinding": snapshot,
            "registrationSourceRevision": SOURCE_REVISION,
            "measurementBaselineRevision": SOURCE_REVISION,
            "scenarios": scenarios,
            "snapshotCleanup": cleanup,
        }
        replay = validator._replay_private_measurement_value(
            value,
            bound_source,
            snapshot,
            SOURCE_REVISION,
            SOURCE_REVISION,
        )
        self.assertIsNotNone(replay)
        assert replay is not None
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            raw_root = parent / "raw"
            key_root = parent / "key"
            isolate_root = parent / "isolate"
            raw_root.mkdir()
            key_root.mkdir()
            isolate_root.mkdir()
            validator.initialize_authorized_o4_isolate_root(
                isolate_root, snapshot["publicIdentity"]
            )
            (isolate_root / "auth.json").write_text(
                '{"private":"fixture"}\n', encoding="utf-8"
            )
            public_attestation = validator.create_task_attestation_key(
                key_root, "o4-capture-attestation.public-v1:" + "8" * 32
            )
            fault_suite = passing_fault_suite(SOURCE_REVISION)
            original_persist = validator.persist_private_measurement

            def persist_while_roots_are_locked(*args: object, **kwargs: object) -> None:
                for locked_root in (raw_root, isolate_root, key_root):
                    moved = locked_root.with_name(locked_root.name + "-moved")
                    with self.assertRaises(OSError):
                        locked_root.rename(moved)
                    self.assertFalse(moved.exists())
                original_persist(*args, **kwargs)

            with (
                patch.object(
                    validator,
                    "_measurement_context",
                    return_value=(SOURCE_REVISION, {}),
                ),
                patch.object(
                    validator,
                    "_registered_runtime_bindings",
                    return_value=(
                        bound_source,
                        snapshot,
                        public_attestation,
                        user_chronology_baseline(),
                    ),
                ),
                patch.object(
                    validator, "run_fault_suite", return_value=fault_suite
                ),
                patch.object(
                    validator,
                    "persist_private_measurement",
                    side_effect=persist_while_roots_are_locked,
                ),
            ):
                with self.assertRaisesRegex(
                    ValueError, "requires live task-owned operands"
                ):
                    validator.persist_and_attest_private_measurement(
                        Path("."),
                        raw_root,
                        key_root,
                        bound_source,
                        snapshot,
                        public_attestation,
                        SOURCE_REVISION,
                        scenarios,
                        cleanup,
                    )
                suite = validator._LiveO4CaptureSuite(
                    isolate_root, snapshot, user_chronology_baseline()
                )
                captured = [
                    captured_scenario(
                        item,
                        bound_source,
                        snapshot,
                        isolate_root,
                        suite,
                    )
                    for item in scenarios
                ]
                pending = (
                    validator.persist_and_attest_private_measurement(
                        Path("."),
                        raw_root,
                        key_root,
                        bound_source,
                        snapshot,
                        public_attestation,
                        SOURCE_REVISION,
                        captured,
                        validator._TaskScopedSnapshotCleanup(
                            cleanup,
                            isolate_root,
                        ),
                    )
                )
            measurement_document = pending._measurement_document
            payload = {
                key: value
                for key, value in measurement_document.items()
                if key != "captureAttestation"
            }
            signature = measurement_document["captureAttestation"]
            with self.assertRaises(TypeError):
                validator.finalize_public_measurement_observation(  # type: ignore[call-arg]
                    parent / "raw-decoy",
                    parent / "isolate-decoy",
                    parent / "key-decoy",
                    measurement_document,
                    public_attestation,
                )
            observation = validator.finalize_public_measurement_observation(
                pending,
            )
            self.assertTrue(all(lock.disposed for lock in pending._root_locks))
            self.assertTrue(all(lock._handle is None for lock in pending._root_locks))
            self.assertFalse(raw_root.exists())
            self.assertFalse(key_root.exists())
            self.assertFalse(isolate_root.exists())
            self.assertTrue(observation["attestationKeyCleanup"]["privateKeyAbsentAfterCleanup"])
            self.assertTrue(
                validator.verify_task_attestation(
                    public_attestation, payload, signature
                )
            )
            with self.assertRaisesRegex(ValueError, "pending finalization"):
                validator.finalize_public_measurement_observation(pending)
            self.assertNotIn("persist_private_measurement", validator.__all__)
            self.assertNotIn(
                "_attest_terminal_private_resource_cleanup", validator.__all__
            )

    def test_live_capture_view_is_read_only_and_sealed(self) -> None:
        bound_source = source_binding()
        snapshot = snapshot_record(bound_source)
        with tempfile.TemporaryDirectory() as directory:
            isolate = Path(directory) / "isolate"
            isolate.mkdir()
            suite = validator._LiveO4CaptureSuite(
                isolate, snapshot, user_chronology_baseline()
            )
            scenario = private_scenario(
                v1.CARRIER_SCENARIO_IDENTITIES[0],
                raw_compaction_observations(),
                bound_source,
                snapshot,
                "8",
            )
            captured = captured_scenario(
                scenario, bound_source, snapshot, isolate, suite
            )
            capture = captured._capture
            view = capture.messages
            original = capture.messages[0]
            view[0]["tampered"] = True
            self.assertEqual(capture.messages[0], original)
            with self.assertRaises(AttributeError):
                capture.messages = ()  # type: ignore[misc]
            self.assertFalse(hasattr(capture, "_append_code_owned_message"))
            with self.assertRaisesRegex(ValueError, "capture event"):
                validator._CodeOwnedCaptureEvent(
                    object(), capture, "response-read", {"source": "forged"}
                )
            captured._value["scenarioIdentity"] = "forged"
            self.assertNotEqual(
                captured._capture_digest,
                v1._canonical_sha256(captured._value),
            )

    def test_attestation_verifier_rejects_ssh_keygen_digest_drift(self) -> None:
        payload = {
            "kind": "o4-v3-source-preparation-before-measurement",
            "public": True,
        }
        raw = validator._canonical_attestation_payload(payload)
        record = attestation_record()
        record["payloadSha256"] = hashlib.sha256(raw).hexdigest()
        with tempfile.TemporaryDirectory() as directory:
            drifted = Path(directory) / "ssh-keygen.exe"
            drifted.write_bytes(b"drifted-openssh-verifier")
            with patch.object(
                validator,
                "_trusted_ssh_keygen_executable",
                return_value=drifted,
            ):
                self.assertFalse(
                    validator.verify_task_attestation(
                        attestation_binding(), payload, record
                    )
                )

    def test_unstoppable_task_process_is_reported_as_residue(self) -> None:
        process = Mock()
        process.terminate.side_effect = subprocess.TimeoutExpired("terminate", 5)
        process.kill.side_effect = subprocess.TimeoutExpired("kill", 5)
        with self.assertRaisesRegex(RuntimeError, "could not be terminated"):
            validator._terminate_task_scoped_process(process)

    def test_unstoppable_task_process_still_closes_every_stream(self) -> None:
        process = Mock()
        process.stdin = io.BytesIO()
        process.stdout = io.BytesIO()
        process.stderr = io.BytesIO()
        process.terminate.side_effect = subprocess.TimeoutExpired("terminate", 5)
        process.kill.side_effect = subprocess.TimeoutExpired("kill", 5)
        with self.assertRaisesRegex(RuntimeError, "process or stream residue"):
            validator._terminate_and_close_task_scoped_process_streams(
                process, require_bounded_capture=False
            )
        self.assertTrue(process.stdin.closed)
        self.assertTrue(process.stdout.closed)
        self.assertTrue(process.stderr.closed)

    def test_public_observation_uses_registered_attestation_not_private_raw(self) -> None:
        bound_source = source_binding()
        snapshot = snapshot_record(bound_source)
        scenarios = [
            private_scenario(
                v1.CARRIER_SCENARIO_IDENTITIES[0],
                raw_compaction_observations(),
                bound_source,
                snapshot,
                "9",
            ),
            private_scenario(
                v1.CARRIER_SCENARIO_IDENTITIES[1],
                raw_transition_observations(),
                bound_source,
                snapshot,
                "a",
            ),
        ]
        cleanup = snapshot_cleanup_record(snapshot)
        replay = validator._replay_private_measurement_value(
            {
                "schema": 1,
                "suiteIdentity": validator.SUITE_IDENTITY,
                "state": "measurement-complete-live-private-source",
                "sourceBinding": bound_source,
                "snapshotBinding": snapshot,
                "registrationSourceRevision": SOURCE_REVISION,
                "measurementBaselineRevision": SOURCE_REVISION,
                "scenarios": scenarios,
                "snapshotCleanup": cleanup,
            },
            bound_source,
            snapshot,
            SOURCE_REVISION,
            SOURCE_REVISION,
        )
        self.assertIsNotNone(replay)
        assert replay is not None
        fault_suite = passing_fault_suite(SOURCE_REVISION)
        material_checkpoint_binding = passing_material_checkpoint_binding(
            fault_suite, replay[0]
        )
        public_attestation = attestation_binding()
        observation = {
            "schema": 1,
            "kind": "o4-v3-public-measurement-after-registration",
            "suiteIdentity": validator.SUITE_IDENTITY,
            "registrationSourceRevision": SOURCE_REVISION,
            "measurementBaselineRevision": SOURCE_REVISION,
            "sourceBinding": bound_source,
            "snapshotBinding": snapshot,
            "faultSuite": fault_suite,
            "materialCheckpointBinding": material_checkpoint_binding,
            "carrierProjections": replay[0],
            "claimCeiling": validator.CLAIM_CEILING,
            "cleanupVerified": True,
            "snapshotCleanup": cleanup,
            "captureAttestation": attestation_record(),
            "privateMeasurementCleanup": {
                "schema": 1,
                "source": "private-o4-measurement-terminal-cleanup",
                "snapshotPublicIdentity": snapshot["publicIdentity"],
                "reason": "accepted",
                "privateMeasurementAbsentAfterCleanup": True,
                "privateRootAbsentAfterCleanup": True,
                "privatePathPublished": False,
            },
            "isolatedCodexHomeCleanup": {
                "schema": 1,
                "source": (
                    "authorized-o4-v3-isolated-codex-home-terminal-cleanup"
                ),
                "snapshotPublicIdentity": snapshot["publicIdentity"],
                "reason": "accepted",
                "isolatedCodexHomeAbsentAfterCleanup": True,
                "privatePathPublished": False,
            },
            "terminalCleanupAttestation": attestation_record(),
            "attestationKeyCleanup": {
                "schema": 1,
                "source": "o4-capture-attestation-key-terminal-cleanup",
                "publicIdentity": public_attestation["publicIdentity"],
                "publicKeyFingerprint": public_attestation[
                    "publicKeyFingerprint"
                ],
                "reason": "accepted",
                "privateKeyAbsentAfterCleanup": True,
                "privateRootAbsentAfterCleanup": True,
                "privatePathPublished": False,
            },
        }
        with (
            patch.object(
                validator,
                "_registered_runtime_bindings",
                return_value=(
                    bound_source,
                    snapshot,
                    public_attestation,
                    user_chronology_baseline(),
                ),
            ),
            patch.object(
                validator,
                "_measurement_context",
                return_value=(SOURCE_REVISION, {}),
            ),
            patch.object(validator, "run_fault_suite", return_value=fault_suite),
            patch.object(validator, "verify_task_attestation", return_value=False),
        ):
            self.assertFalse(
                validator._observation_valid(Path("."), observation, SOURCE_REVISION)
            )
        with (
            patch.object(
                validator,
                "_registered_runtime_bindings",
                return_value=(
                    bound_source,
                    snapshot,
                    public_attestation,
                    user_chronology_baseline(),
                ),
            ),
            patch.object(
                validator,
                "_measurement_context",
                return_value=(SOURCE_REVISION, {}),
            ),
            patch.object(validator, "run_fault_suite", return_value=fault_suite),
            patch.object(validator, "verify_task_attestation", return_value=True),
        ):
            self.assertTrue(
                validator._observation_valid(Path("."), observation, SOURCE_REVISION)
            )
            tampered = deepcopy(observation)
            tampered["materialCheckpointBinding"]["checkpointIdentities"][0] = (
                "fault-recovery:forged"
            )
            self.assertFalse(
                validator._observation_valid(Path("."), tampered, SOURCE_REVISION)
            )
            user_triggered = deepcopy(observation)
            decision = user_triggered["carrierProjections"][1][
                "carrierDecisionEvidence"
            ]
            decision["userInitiatedHandoffObserved"] = True
            decision["agentTransitionTriggeredBeforeUserIntervention"] = False
            self.assertFalse(
                validator._observation_valid(
                    Path("."), user_triggered, SOURCE_REVISION
                )
            )

    @unittest.skipUnless(os.name == "nt", "directory delete sharing is Windows-bound")
    def test_pending_finalization_prevents_renamed_decoy_root(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            raw = parent / "raw"
            isolate = parent / "isolate"
            key = parent / "key"
            for root in (raw, isolate, key):
                root.mkdir()
            identities = tuple(
                validator._directory_object_identity(root)
                for root in (raw, isolate, key)
            )
            trees = tuple(
                validator._private_resource_tree_identity(root)
                for root in (raw, isolate, key)
            )
            locks = tuple(
                validator._LockedPrivateResourceRoot(root)
                for root in (raw, isolate, key)
            )
            pending = validator._PendingMeasurementFinalization(
                {},
                {},
                raw,
                isolate,
                key,
                identities,
                trees,
                locks,
            )
            moved = parent / "raw-moved"
            try:
                with self.assertRaises(OSError):
                    raw.rename(moved)
            finally:
                for lock in pending._root_locks:
                    lock.release()
            self.assertFalse(moved.exists())
            self.assertTrue(raw.exists())

    @unittest.skipUnless(os.name == "nt", "handle quarantine is Windows-bound")
    def test_private_tree_recovers_renamed_child_by_file_id(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            root = parent / "private"
            root.mkdir()
            child = root / "secret.bin"
            child.write_bytes(b"private-task-material")
            expected = validator._private_resource_tree_identity(root)
            lock = validator._LockedPrivateResourceRoot(root)
            moved = parent / "escaped-secret.bin"
            attempts: list[str] = []
            original_quarantine = validator._LockedPrivateResourceRoot.quarantine

            def racing_quarantine(root_lock: object) -> None:
                original_quarantine(root_lock)
                if not attempts:
                    path = root_lock.path / "secret.bin"
                    path.rename(moved)
                    path.write_bytes(b"foreign-decoy")
                    attempts.append(str(path))

            try:
                with patch.object(
                    validator._LockedPrivateResourceRoot,
                    "quarantine",
                    new=racing_quarantine,
                ):
                    with self.assertRaisesRegex(RuntimeError, "unexpected residue"):
                        validator._dispose_locked_private_tree(lock, expected)
                self.assertEqual(len(attempts), 1)
                self.assertFalse(moved.exists())
                self.assertTrue(lock.path.exists())
                decoy = next(lock.path.iterdir())
                self.assertEqual(decoy.read_bytes(), b"foreign-decoy")
            finally:
                lock.release()
                if lock.path.exists():
                    for item in lock.path.iterdir():
                        item.unlink()
                    lock.path.rmdir()
            self.assertEqual(list(parent.iterdir()), [])

    @unittest.skipUnless(os.name == "nt", "hard-link cleanup is Windows-bound")
    def test_private_tree_never_claims_cleanup_with_external_hard_link(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            root = parent / "private"
            root.mkdir()
            child = root / "secret.bin"
            child.write_bytes(b"private-task-material")
            expected = validator._private_resource_tree_identity(root)
            external = parent / "external-hard-link.bin"
            os.link(child, external)
            lock = validator._LockedPrivateResourceRoot(root)
            try:
                with self.assertRaisesRegex(ValueError, "external hard link"):
                    validator._dispose_locked_private_tree(lock, expected)
                self.assertTrue(external.exists())
                self.assertTrue(any(lock.path.iterdir()))
                self.assertFalse(lock.disposed)
            finally:
                lock.release()
                external.unlink(missing_ok=True)
                if lock.path.exists():
                    for item in lock.path.iterdir():
                        item.unlink()
                    lock.path.rmdir()
            self.assertEqual(list(parent.iterdir()), [])

    @unittest.skipUnless(os.name == "nt", "open-handle cleanup is Windows-bound")
    def test_private_tree_never_claims_cleanup_with_foreign_open_handle(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            root = parent / "private"
            root.mkdir()
            child = root / "secret.bin"
            child.write_bytes(b"private-task-material")
            expected = validator._private_resource_tree_identity(root)
            kernel32 = ctypes.WinDLL("Kernel32.dll", use_last_error=True)
            kernel32.CreateFileW.argtypes = [
                ctypes.c_wchar_p,
                ctypes.c_uint32,
                ctypes.c_uint32,
                ctypes.c_void_p,
                ctypes.c_uint32,
                ctypes.c_uint32,
                ctypes.c_void_p,
            ]
            kernel32.CreateFileW.restype = ctypes.c_void_p
            foreign = kernel32.CreateFileW(
                str(child),
                0x80000000,
                0x00000001 | 0x00000002 | 0x00000004,
                None,
                3,
                0,
                None,
            )
            self.assertNotIn(foreign, (None, ctypes.c_void_p(-1).value))
            lock = validator._LockedPrivateResourceRoot(root)
            try:
                with self.assertRaisesRegex(OSError, "cleanup quarantine"):
                    validator._dispose_locked_private_tree(lock, expected)
                self.assertFalse(lock.disposed)
                self.assertTrue(any(lock.path.iterdir()))
                self.assertTrue(kernel32.CloseHandle(ctypes.c_void_p(foreign)))
                foreign = None
                validator._dispose_locked_private_tree(lock, expected)
                self.assertTrue(lock.disposed)
                self.assertFalse(lock.path.exists())
            finally:
                if foreign not in (None, ctypes.c_void_p(-1).value):
                    kernel32.CloseHandle(ctypes.c_void_p(foreign))
                lock.release()
            self.assertEqual(list(parent.iterdir()), [])

    def test_native_archive_sri_binds_the_exact_executable_member(self) -> None:
        native = b"official-native-package-member-v3\n" * 64
        archive_buffer = io.BytesIO()
        with tarfile.open(fileobj=archive_buffer, mode="w:gz") as package:
            member = tarfile.TarInfo(
                "package/vendor/x86_64-pc-windows-msvc/bin/codex.exe"
            )
            member.size = len(native)
            package.addfile(member, io.BytesIO(native))
        archive = archive_buffer.getvalue()
        bound_source = source_binding(
            native_sha256=hashlib.sha256(native).hexdigest(),
            native_bytes=len(native),
        )
        bound_source["nativePackageIntegrity"] = "sha512-" + base64.b64encode(
            hashlib.sha512(archive).digest()
        ).decode("ascii")

        class Response(io.BytesIO):
            status = 200
            headers: dict[str, str] = {}

            def geturl(self) -> str:
                return str(bound_source["nativePackageTarball"])

        with tempfile.TemporaryDirectory() as directory:
            isolate = Path(directory) / "isolate"
            isolate.mkdir()
            with (
                patch.object(
                    validator, "_trusted_windows_curl_executable", return_value=None
                ),
                patch.object(
                    validator.urllib.request,
                    "urlopen",
                    return_value=Response(archive),
                ),
            ):
                digest, byte_count = (
                    validator._verify_native_package_archive_executable(
                        bound_source, isolate
                    )
                )
            self.assertEqual(digest, hashlib.sha256(native).hexdigest())
            self.assertEqual(byte_count, len(native))
            self.assertFalse((isolate / ".harness").exists())
            with (
                patch.object(
                    validator, "_trusted_windows_curl_executable", return_value=None
                ),
                patch.object(
                    validator.urllib.request,
                    "urlopen",
                    return_value=Response(archive),
                ),
                patch.object(
                    validator, "MAX_NATIVE_PACKAGE_EXPANDED_BYTES", len(native) - 1
                ),
                self.assertRaisesRegex(ValueError, "expanded byte limit"),
            ):
                validator._verify_native_package_archive_executable(
                    bound_source, isolate
                )
            self.assertFalse((isolate / ".harness").exists())

    def test_prior_generation_validator_bytes_remain_frozen(self) -> None:
        self.assertEqual(
            hashlib.sha256(Path(v1.VALIDATOR_LOCATOR).read_bytes()).hexdigest(),
            "4e08aed6dd4070016e910aac31192af2ff2c78cf2b779da2a04acada20fd8aa1",
        )
        self.assertEqual(
            hashlib.sha256(Path(v2.VALIDATOR_LOCATOR).read_bytes()).hexdigest(),
            "255ae6df24599572f0d311e5aa6ee7a33dd3b70389b5e96097dde7957d43d367",
        )

    def test_official_source_is_exact_but_not_a_global_version_constant(self) -> None:
        value = source_binding()
        self.assertTrue(validator.official_source_binding_valid(value))

        mutable = deepcopy(value)
        mutable["releaseVersion"] = "latest"
        self.assertFalse(validator.official_source_binding_valid(mutable))

        wrong_tag = deepcopy(value)
        wrong_tag["tag"] = "rust-v0.147.0"
        self.assertFalse(validator.official_source_binding_valid(wrong_tag))

        bad_integrity = deepcopy(value)
        bad_integrity["nativePackageIntegrity"] = "sha512-not-a-digest"
        self.assertFalse(validator.official_source_binding_valid(bad_integrity))

        forged = deepcopy(value)
        forged["tagObject"] = "f" * 40
        forged["peeledCommit"] = "e" * 40
        forged["nativeAuthenticodeSigner"] = "CN=OpenAI Imposter"
        self.assertFalse(validator.official_source_binding_valid(forged))

    def test_default_signature_probe_rejects_shell_diagnostics_and_empty_identity(
        self,
    ) -> None:
        completed = subprocess.CompletedProcess(
            args=["powershell.exe"],
            returncode=0,
            stdout=b'{"status":"","signer":""}',
            stderr=b"module load failed",
        )
        with (
            patch.object(validator.os, "name", "nt"),
            patch.object(
                validator,
                "_trusted_windows_powershell_executable",
                return_value=Path(
                    r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
                ),
            ),
            patch.object(validator.subprocess, "run", return_value=completed),
        ):
            with self.assertRaisesRegex(ValueError, "signature probe failed"):
                validator._default_signature_probe(Path("codex.exe"))

    def test_official_source_probe_requires_exact_live_release_observation(self) -> None:
        value = source_binding()
        observation = {
            key: value[key]
            for key in (
                "tagObject",
                "peeledCommit",
                "npmPackageIntegrity",
                "npmTarball",
                "nativePackageIntegrity",
                "nativePackageTarball",
                "sourceBlobSha256s",
            )
        }
        with patch.object(
            validator,
            "_official_source_network_observation",
            return_value=observation,
        ):
            self.assertTrue(validator._default_official_source_probe(value))
            drifted = deepcopy(value)
            drifted["sourceBlobSha256s"] = {
                **value["sourceBlobSha256s"],
                validator.SOURCE_BLOB_PATHS[0]: "f" * 64,
            }
            self.assertFalse(validator._default_official_source_probe(drifted))

    def test_materialized_snapshot_survives_ambient_drift_and_rejects_tamper(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            isolate = root / "isolate"
            isolate.mkdir()
            validator.initialize_authorized_o4_isolate_root(
                isolate, "codex-native-snapshot.public-v1:" + "b" * 32
            )
            source = root / "ambient-codex.exe"
            original = b"codex-native-fixture-v3\n" * 64
            source.write_bytes(original)
            bound_source = source_binding(
                native_sha256=hashlib.sha256(original).hexdigest(),
                native_bytes=len(original),
            )
            signature = lambda path: (  # noqa: E731
                bound_source["nativeAuthenticodeStatus"],
                bound_source["nativeAuthenticodeSigner"],
                bound_source["nativeAuthenticodeCertificateSha256"],
            )
            version = lambda executable, home: "codex-cli 0.148.0"  # noqa: E731
            snapshot = validator.materialize_task_scoped_native_snapshot(
                source,
                isolate,
                bound_source,
                "codex-native-snapshot.public-v1:" + "b" * 32,
                version_probe=version,
                signature_probe=signature,
                official_source_probe=lambda value: True,
            )
            self.assertTrue(validator.snapshot_record_valid(snapshot, bound_source))
            self.assertNotIn(str(root), json.dumps(snapshot, sort_keys=True))

            source.write_bytes(b"ambient-installation-updated-after-snapshot")
            executable = validator.verified_task_scoped_snapshot_executable(
                isolate,
                bound_source,
                snapshot,
                version_probe=version,
                signature_probe=signature,
            )
            self.assertEqual(executable.read_bytes(), original)
            preflight = validator.snapshot_preflight_observation(
                isolate,
                bound_source,
                snapshot,
                version_probe=version,
                signature_probe=signature,
            )
            self.assertFalse(preflight["ambientExecutableUsed"])
            self.assertNotIn(str(root), json.dumps(preflight, sort_keys=True))

            executable.write_bytes(b"tampered")
            with self.assertRaisesRegex(ValueError, "preflight failed"):
                validator.verified_task_scoped_snapshot_executable(
                    isolate,
                    bound_source,
                    snapshot,
                    version_probe=version,
                    signature_probe=signature,
                )

    def test_failed_snapshot_materialization_cleans_exact_task_parent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            isolate = root / "isolate"
            isolate.mkdir()
            validator.initialize_authorized_o4_isolate_root(
                isolate, "codex-native-snapshot.public-v1:" + "c" * 32
            )
            source = root / "ambient-codex.exe"
            source.write_bytes(b"wrong-bytes")
            with self.assertRaisesRegex(ValueError, "does not match"):
                validator.materialize_task_scoped_native_snapshot(
                    source,
                    isolate,
                    source_binding(native_sha256="d" * 64, native_bytes=11),
                    "codex-native-snapshot.public-v1:" + "c" * 32,
                    version_probe=lambda executable, home: "codex-cli 0.148.0",
                    signature_probe=lambda path: (
                        "Valid",
                        'CN="OpenAI OpCo, LLC", O="OpenAI OpCo, LLC"',
                        "4" * 64,
                    ),
                    official_source_probe=lambda value: True,
                )
            self.assertFalse((isolate / ".harness").exists())

    def test_snapshot_launcher_uses_verified_private_executable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            isolate = root / "isolate"
            isolate.mkdir()
            validator.initialize_authorized_o4_isolate_root(
                isolate, "codex-native-snapshot.public-v1:" + "1" * 32
            )
            source = root / "ambient-codex.exe"
            original = b"codex-native-fixture-v3\n" * 64
            source.write_bytes(original)
            bound_source = source_binding(
                native_sha256=hashlib.sha256(original).hexdigest(),
                native_bytes=len(original),
            )
            signature = lambda path: (  # noqa: E731
                bound_source["nativeAuthenticodeStatus"],
                bound_source["nativeAuthenticodeSigner"],
                bound_source["nativeAuthenticodeCertificateSha256"],
            )
            version = lambda executable, home: "codex-cli 0.148.0"  # noqa: E731
            snapshot = validator.materialize_task_scoped_native_snapshot(
                source,
                isolate,
                bound_source,
                "codex-native-snapshot.public-v1:" + "1" * 32,
                version_probe=version,
                signature_probe=signature,
                official_source_probe=lambda value: True,
            )
            captured: dict[str, object] = {}
            fake_process = Mock()
            fake_process.wait.return_value = 0

            def process_factory(arguments: list[str], **kwargs: object) -> Mock:
                captured["arguments"] = arguments
                captured["kwargs"] = kwargs
                return fake_process

            expected = isolate.joinpath(*validator.SNAPSHOT_RELATIVE_PARTS).resolve()
            with patch.object(
                validator,
                "_trusted_windows_powershell_executable",
                return_value=Path(
                    "/windows/System32/WindowsPowerShell/v1.0/powershell.exe"
                ),
            ):
                process, launch = validator.launch_task_scoped_snapshot_app_server(
                    isolate,
                    bound_source,
                    snapshot,
                    "codex-app-server-launch.public-v1:" + "2" * 32,
                    network_environment={},
                    version_probe=version,
                    signature_probe=signature,
                    process_factory=process_factory,
                    process_image_probe=lambda process: expected,
                )
            self.assertIs(process, fake_process)
            self.assertEqual(captured["arguments"], [str(expected), "app-server"])
            self.assertEqual(captured["kwargs"]["cwd"], isolate.resolve())
            self.assertEqual(captured["kwargs"]["env"]["CODEX_HOME"], str(isolate.resolve()))
            self.assertNotIn(str(root), json.dumps(launch, sort_keys=True))
            self.assertEqual(launch["processImageSha256"], snapshot["snapshotExecutableSha256"])
            terminal = validator.close_task_scoped_snapshot_app_server(
                fake_process, launch, bound_source, snapshot
            )
            fake_process.stdin.close.assert_called_once_with()
            fake_process.wait.assert_called_once_with(timeout=15.0)
            self.assertTrue(terminal["processExited"])

            mismatched_process = Mock()
            mismatched_process.wait.return_value = 0
            with (
                patch.object(
                    validator,
                    "_trusted_windows_powershell_executable",
                    return_value=Path(
                        "/windows/System32/WindowsPowerShell/v1.0/powershell.exe"
                    ),
                ),
                self.assertRaisesRegex(ValueError, "differs from the snapshot"),
            ):
                validator.launch_task_scoped_snapshot_app_server(
                    isolate,
                    bound_source,
                    snapshot,
                    "codex-app-server-launch.public-v1:" + "4" * 32,
                    network_environment={},
                    version_probe=version,
                    signature_probe=signature,
                    process_factory=lambda *args, **kwargs: mismatched_process,
                    process_image_probe=lambda process: source.resolve(),
                )
            mismatched_process.terminate.assert_called_once_with()

            locked_process = Mock()
            locked_process.wait.return_value = 0
            moved_snapshot = expected.with_name("codex-moved.exe")

            def rename_during_launch(*args: object, **kwargs: object) -> Mock:
                del args, kwargs
                with self.assertRaises(OSError):
                    expected.rename(moved_snapshot)
                return locked_process

            with patch.object(
                validator,
                "_trusted_windows_powershell_executable",
                return_value=Path(
                    "/windows/System32/WindowsPowerShell/v1.0/powershell.exe"
                ),
            ):
                validator.launch_task_scoped_snapshot_app_server(
                    isolate,
                    bound_source,
                    snapshot,
                    "codex-app-server-launch.public-v1:" + "5" * 32,
                    network_environment={},
                    version_probe=version,
                    signature_probe=signature,
                    process_factory=rename_during_launch,
                    process_image_probe=lambda process: expected,
                )
            self.assertTrue(expected.exists())
            self.assertFalse(moved_snapshot.exists())

    def test_app_server_io_is_captured_from_the_launched_process_streams(self) -> None:
        bound_source = source_binding()
        snapshot = snapshot_record(bound_source)
        launch = launch_record(bound_source, snapshot)
        process = Mock()
        process.stdin = Mock()
        process.stdout = Mock()
        process.stdout.readline.return_value = b'{"id":1,"result":{}}\n'
        validator.write_snapshot_app_server_message(
            process, {"id": 1, "method": "thread/list", "params": {}}
        )
        process.stdin.write.assert_called_once_with(
            b'{"id":1,"method":"thread/list","params":{}}\n'
        )
        process.stdin.flush.assert_called_once_with()
        observed = validator.read_snapshot_app_server_message(
            process, launch, bound_source, snapshot
        )
        self.assertEqual(observed["message"], {"id": 1, "result": {}})
        self.assertEqual(
            observed["launchPublicIdentity"], launch["launchPublicIdentity"]
        )

    def test_bounded_process_streams_drain_both_channels_and_reject_residue(self) -> None:
        process = Mock()
        process.stdout = io.BytesIO(b'{"id":1,"result":{}}\n')
        process.stderr = io.BytesIO(b"")
        capture = validator._BoundedAppServerStreams(process)
        self.assertEqual(capture.read(2), b'{"id":1,"result":{}}\n')
        capture.finish(2)

        noisy = Mock()
        noisy.stdout = io.BytesIO(b"")
        noisy.stderr = io.BytesIO(b"private diagnostic")
        capture = validator._BoundedAppServerStreams(noisy)
        capture.finish(2)

        overflow = Mock()
        overflow.stdout = io.BytesIO(b"")
        overflow.stderr = io.BytesIO(
            b"x" * (validator.MAX_APP_SERVER_STDERR_BYTES + 1)
        )
        capture = validator._BoundedAppServerStreams(overflow)
        with self.assertRaisesRegex(ValueError, "bounds"):
            capture.finish(2)

        surplus = Mock()
        surplus.stdout = io.BytesIO(b'{"id":1}\n{"id":2}\n')
        surplus.stderr = io.BytesIO(b"")
        capture = validator._BoundedAppServerStreams(surplus)
        self.assertEqual(capture.read(2), b'{"id":1}\n')
        with self.assertRaisesRegex(ValueError, "unconsumed"):
            capture.finish(2)

    @unittest.skipUnless(os.name == "nt", "native snapshot launcher is Windows-bound")
    def test_actual_popen_exit_nonzero_and_timeout_boundaries(self) -> None:
        bound_source = source_binding()
        snapshot = snapshot_record(bound_source)
        launch = launch_record(bound_source, snapshot)

        clean = subprocess.Popen(
            [
                sys.executable,
                "-c",
                "import sys;print('{\"id\":1,\"result\":{}}',flush=True);"
                "sys.stdin.buffer.read()",
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0,
        )
        clean._o4_bounded_streams = validator._BoundedAppServerStreams(clean)
        clean._o4_native_snapshot_launch = True
        observed = validator.read_snapshot_app_server_message(
            clean, launch, bound_source, snapshot, timeout=5
        )
        self.assertEqual(observed["message"], {"id": 1, "result": {}})
        terminal = validator.close_task_scoped_snapshot_app_server(
            clean, launch, bound_source, snapshot, timeout=5
        )
        self.assertTrue(terminal["processExited"])

        nonzero = subprocess.Popen(
            [sys.executable, "-c", "import sys;sys.stdin.buffer.read();raise SystemExit(7)"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0,
        )
        nonzero._o4_bounded_streams = validator._BoundedAppServerStreams(nonzero)
        nonzero._o4_native_snapshot_launch = True
        with self.assertRaisesRegex(ValueError, "terminal state"):
            validator.close_task_scoped_snapshot_app_server(
                nonzero, launch, bound_source, snapshot, timeout=5
            )

        delayed = subprocess.Popen(
            [sys.executable, "-c", "import time;time.sleep(5)"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0,
        )
        delayed._o4_bounded_streams = validator._BoundedAppServerStreams(delayed)
        delayed._o4_native_snapshot_launch = True
        with self.assertRaisesRegex(ValueError, "did not close cleanly"):
            validator.close_task_scoped_snapshot_app_server(
                delayed, launch, bound_source, snapshot, timeout=0.05
            )

    def test_raw_graph_limits_fail_before_copy(self) -> None:
        bound_source = source_binding()
        snapshot = snapshot_record(bound_source)
        cyclic: list[object] = [{}, {}, {}, {}]
        cyclic[0] = cyclic
        with self.assertRaisesRegex(ValueError, "raw third-generation"):
            validator.project_raw_carrier_observations(
                v1.CARRIER_SCENARIO_IDENTITIES[0],
                cyclic,  # type: ignore[arg-type]
                source_binding=bound_source,
                snapshot=snapshot,
                source_carrier_id=SOURCE_CARRIER_ID,
                expected_head=SOURCE_REVISION,
            )

    def test_snapshot_cleanup_proves_absence_for_every_terminal_reason(self) -> None:
        for reason in ("accepted", "stopped", "deterministic-failure"):
            with self.subTest(reason=reason), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                isolate = root / "isolate"
                isolate.mkdir()
                validator.initialize_authorized_o4_isolate_root(
                    isolate, "codex-native-snapshot.public-v1:" + "3" * 32
                )
                source = root / "ambient-codex.exe"
                original = b"codex-native-fixture-v3\n" * 64
                source.write_bytes(original)
                bound_source = source_binding(
                    native_sha256=hashlib.sha256(original).hexdigest(),
                    native_bytes=len(original),
                )
                signature = lambda path: (  # noqa: E731
                    bound_source["nativeAuthenticodeStatus"],
                    bound_source["nativeAuthenticodeSigner"],
                    bound_source["nativeAuthenticodeCertificateSha256"],
                )
                version = lambda executable, home: "codex-cli 0.148.0"  # noqa: E731
                snapshot = validator.materialize_task_scoped_native_snapshot(
                    source,
                    isolate,
                    bound_source,
                    "codex-native-snapshot.public-v1:" + "3" * 32,
                    version_probe=version,
                    signature_probe=signature,
                    official_source_probe=lambda value: True,
                )
                cleanup = validator.cleanup_task_scoped_native_snapshot(
                    isolate,
                    bound_source,
                    snapshot,
                    reason=reason,
                    version_probe=version,
                    signature_probe=signature,
                )
                self.assertTrue(cleanup["snapshotAbsentAfterCleanup"])
                self.assertTrue(cleanup["taskParentAbsentAfterCleanup"])
                self.assertFalse(
                    isolate.joinpath(*validator.SNAPSHOT_RELATIVE_PARTS).exists()
                )
                self.assertFalse((isolate / ".harness").exists())
                self.assertNotIn(str(root), json.dumps(cleanup, sort_keys=True))
                (isolate / "auth.json").write_text(
                    '{"private":"fixture"}\n', encoding="utf-8"
                )
                isolate_cleanup = validator.cleanup_authorized_o4_isolate_root(
                    isolate, snapshot, reason=reason
                )
                self.assertTrue(
                    isolate_cleanup["isolatedCodexHomeAbsentAfterCleanup"]
                )
                self.assertFalse(isolate.exists())
                self.assertNotIn(
                    str(root), json.dumps(isolate_cleanup, sort_keys=True)
                )

    def test_registration_is_generation_and_snapshot_isolated(self) -> None:
        bound_source = source_binding()
        snapshot = snapshot_record(bound_source)
        public_attestation = attestation_binding()
        source_attestation = attestation_record()
        increment = {
            "id": validator.INCREMENT_ID,
            "taskRegistration": {
                "locator": validator.REGISTRATION_LOCATOR,
                "sourceRevision": SOURCE_REVISION,
            },
        }
        registration = {
            "incrementId": validator.INCREMENT_ID,
            "criterionIds": ["O4"],
            "preRegistrationValues": registration_values(
                bound_source,
                snapshot,
                public_attestation,
                source_attestation,
            ),
            "preMeasurementValidator": {
                "kind": validator.VALIDATOR_KIND,
                "version": 1,
                "locator": validator.VALIDATOR_LOCATOR,
            },
        }
        errors: list[str] = []
        with (
            patch.object(
                validator,
                "_manifest_runtime_bindings",
                return_value=(bound_source, snapshot, public_attestation),
            ),
            patch.object(
                validator, "_git_revision_is_strict_ancestor", return_value=True
            ),
            patch.object(validator, "verify_task_attestation", return_value=True),
            patch.object(v1, "_goal_artifact_committed", return_value=True),
        ):
            self.assertTrue(
                validator.validate_registration(
                    registration, increment, ("O4",), Path("."), errors
                ),
                errors,
            )

        errors = []
        with (
            patch.object(
                validator,
                "_manifest_runtime_bindings",
                return_value=(bound_source, snapshot, public_attestation),
            ),
            patch.object(
                validator, "_git_revision_is_strict_ancestor", return_value=False
            ),
            patch.object(validator, "verify_task_attestation", return_value=True),
            patch.object(v1, "_goal_artifact_committed", return_value=True),
        ):
            self.assertFalse(
                validator.validate_registration(
                    registration, increment, ("O4",), Path("."), errors
                )
            )
        self.assertIn(
            "O4 third-generation source preparation must precede registration",
            errors,
        )

        crossed = deepcopy(registration)
        crossed["preMeasurementValidator"]["kind"] = v2.VALIDATOR_KIND
        errors = []
        with (
            patch.object(
                validator,
                "_manifest_runtime_bindings",
                return_value=(bound_source, snapshot, public_attestation),
            ),
            patch.object(
                validator, "_git_revision_is_strict_ancestor", return_value=True
            ),
            patch.object(validator, "verify_task_attestation", return_value=True),
            patch.object(v1, "_goal_artifact_committed", return_value=True),
        ):
            self.assertFalse(
                validator.validate_registration(
                    crossed, increment, ("O4",), Path("."), errors
                )
            )
        self.assertIn(
            "O4 third-generation pre-measurement validator is invalid", errors
        )

        changed_snapshot = deepcopy(registration)
        changed_snapshot["preRegistrationValues"]["scenarioValidator"][
            "taskScopedNativeSnapshot"
        ]["sha256"] = "f" * 64
        errors = []
        with (
            patch.object(
                validator,
                "_manifest_runtime_bindings",
                return_value=(bound_source, snapshot, public_attestation),
            ),
            patch.object(
                validator, "_git_revision_is_strict_ancestor", return_value=True
            ),
            patch.object(validator, "verify_task_attestation", return_value=True),
            patch.object(v1, "_goal_artifact_committed", return_value=True),
        ):
            self.assertFalse(
                validator.validate_registration(
                    changed_snapshot, increment, ("O4",), Path("."), errors
                )
            )
        self.assertIn("O4 third-generation validator binding is invalid", errors)

    def test_pre_registration_user_chronology_requires_real_thread_read(self) -> None:
        bound_source = source_binding()
        snapshot = snapshot_record(bound_source)
        with tempfile.TemporaryDirectory() as directory:
            isolate = Path(directory) / "isolate"
            isolate.mkdir()
            suite = validator._LiveO4CaptureSuite(isolate, snapshot, None)
            scenario = private_scenario(
                v1.CARRIER_SCENARIO_IDENTITIES[0],
                raw_compaction_observations(),
                bound_source,
                snapshot,
                "8",
            )
            raw = scenario["rawObservations"]
            assert isinstance(raw, list)
            capture = validator._LiveAppServerCapture(
                raw[0], raw[1], bound_source, snapshot, isolate, suite
            )
            process = Mock()
            process._o4_native_snapshot_launch = True
            process._o4_live_capture = capture
            with self.assertRaisesRegex(ValueError, "chronology is unavailable"):
                validator.capture_source_user_chronology_baseline(
                    REPO_ROOT, process, SOURCE_CARRIER_ID
                )
            capture_thread_read_chronology(
                process, capture, bound_source, snapshot, request_id=72
            )
            baseline = validator.capture_source_user_chronology_baseline(
                REPO_ROOT, process, SOURCE_CARRIER_ID
            )
            self.assertIsInstance(
                baseline, validator._SourceUserChronologyBaseline
            )
            self.assertEqual(baseline["userMessageCount"], 1)
            self.assertRegex(
                str(baseline["threadReadResponseRecordSha256"]), r"^[0-9a-f]{64}$"
            )
            late_suite = validator._LiveO4CaptureSuite(isolate, snapshot, None)
            late_capture = validator._LiveAppServerCapture(
                raw[0], raw[1], bound_source, snapshot, isolate, late_suite
            )
            late_process = Mock()
            late_process._o4_native_snapshot_launch = True
            late_process._o4_live_capture = late_capture
            capture_thread_read_chronology(
                late_process,
                late_capture,
                bound_source,
                snapshot,
                request_id=73,
                user_message_ids=("user-message-1", "user-handoff-request"),
            )
            with self.assertRaisesRegex(ValueError, "controlled goal start"):
                validator.capture_source_user_chronology_baseline(
                    REPO_ROOT, late_process, SOURCE_CARRIER_ID
                )

    def test_raw_projection_requires_snapshot_preflight_and_v3_state(self) -> None:
        bound_source = source_binding()
        snapshot = snapshot_record(bound_source)
        raw = raw_compaction_observations()
        raw[8]["report"]["activeIncrement"] = validator.INCREMENT_ID
        launch = launch_record(bound_source, snapshot)
        bound_raw = [
            validator.bind_snapshot_app_server_message(
                launch, bound_source, snapshot, item["message"]
            )
            if item.get("source") == "codex-app-server-json-rpc-v0.147.0"
            else item
            for item in raw
        ]
        terminal = validator.snapshot_app_server_terminal_observation(
            launch,
            bound_source,
            snapshot,
            return_code=0,
            termination_route="stdin-close-clean-exit-after-thread-archive",
        )
        preflight = {
            "source": "task-scoped-native-snapshot-preflight",
            "snapshotPublicIdentity": snapshot["publicIdentity"],
            "releaseVersion": bound_source["releaseVersion"],
            "registeredSha256": snapshot["snapshotExecutableSha256"],
            "observedExecutableSha256": snapshot["snapshotExecutableSha256"],
            "observedExecutableBytes": snapshot["snapshotExecutableBytes"],
            "versionOutput": snapshot["snapshotVersionOutput"],
            "ambientExecutableUsed": False,
        }
        projection = validator.project_raw_carrier_observations(
            v1.CARRIER_SCENARIO_IDENTITIES[0],
            [launch, preflight, *bound_raw, terminal],
            source_binding=bound_source,
            snapshot=snapshot,
            source_carrier_id=SOURCE_CARRIER_ID,
            expected_head=SOURCE_REVISION,
        )
        self.assertTrue(projection["nativeExecutionSnapshot"]["verifiedBeforeHostProcess"])
        self.assertFalse(projection["nativeExecutionSnapshot"]["ambientExecutableUsed"])
        self.assertEqual(
            projection["carrierProjection"]["codexSourceBinding"], bound_source
        )
        self.assertNotIn("0.147.0", json.dumps(projection, sort_keys=True))

        ambient = deepcopy(preflight)
        ambient["ambientExecutableUsed"] = True
        with self.assertRaisesRegex(ValueError, "preflight is invalid"):
            validator.project_raw_carrier_observations(
                v1.CARRIER_SCENARIO_IDENTITIES[0],
                [launch, ambient, *bound_raw, terminal],
                source_binding=bound_source,
                snapshot=snapshot,
                source_carrier_id=SOURCE_CARRIER_ID,
                expected_head=SOURCE_REVISION,
            )

    def test_raw_transition_projection_is_v3_bound_and_source_released(self) -> None:
        bound_source = source_binding()
        snapshot = snapshot_record(bound_source)
        raw = raw_transition_observations()
        for item in raw:
            report = item.get("report")
            if isinstance(report, dict) and "activeIncrement" in report:
                report["activeIncrement"] = validator.INCREMENT_ID
        launch = launch_record(
            bound_source,
            snapshot,
            "codex-app-server-launch.public-v1:" + "6" * 32,
        )
        bound_raw = [
            validator.bind_snapshot_app_server_message(
                launch, bound_source, snapshot, item["message"]
            )
            if item.get("source") == "codex-app-server-json-rpc-v0.147.0"
            else item
            for item in raw
        ]
        preflight = {
            "source": "task-scoped-native-snapshot-preflight",
            "snapshotPublicIdentity": snapshot["publicIdentity"],
            "releaseVersion": bound_source["releaseVersion"],
            "registeredSha256": snapshot["snapshotExecutableSha256"],
            "observedExecutableSha256": snapshot["snapshotExecutableSha256"],
            "observedExecutableBytes": snapshot["snapshotExecutableBytes"],
            "versionOutput": snapshot["snapshotVersionOutput"],
            "ambientExecutableUsed": False,
        }
        terminal = validator.snapshot_app_server_terminal_observation(
            launch,
            bound_source,
            snapshot,
            return_code=0,
            termination_route="stdin-close-clean-exit-after-thread-archive",
        )
        projection = validator.project_raw_carrier_observations(
            v1.CARRIER_SCENARIO_IDENTITIES[1],
            [launch, preflight, *bound_raw, terminal],
            source_binding=bound_source,
            snapshot=snapshot,
            source_carrier_id=SOURCE_CARRIER_ID,
            expected_head=SOURCE_REVISION,
            destination_carrier_id=DESTINATION_CARRIER_ID,
            expected_cwd=TEST_CWD,
        )
        self.assertEqual(
            projection["carrierProjection"]["eventSequence"][-1]["eventClass"],
            "source-carrier-released",
        )
        self.assertEqual(
            projection["nativeExecutionSnapshot"]["launchPublicIdentity"],
            launch["launchPublicIdentity"],
        )
        self.assertNotIn("0.147.0", json.dumps(projection, sort_keys=True))

    def test_unknown_capacity_signal_is_derived_from_live_suite_history(self) -> None:
        bound_source = source_binding()
        snapshot = snapshot_record(bound_source)
        with tempfile.TemporaryDirectory() as directory:
            isolate = Path(directory) / "isolate"
            isolate.mkdir()
            suite = validator._LiveO4CaptureSuite(
                isolate, snapshot, user_chronology_baseline()
            )
            first = private_scenario(
                v1.CARRIER_SCENARIO_IDENTITIES[0],
                raw_compaction_observations(),
                bound_source,
                snapshot,
                "3",
            )
            captured_scenario(first, bound_source, snapshot, isolate, suite)
            second = private_scenario(
                v1.CARRIER_SCENARIO_IDENTITIES[1],
                raw_transition_observations(),
                bound_source,
                snapshot,
                "4",
            )
            raw = second["rawObservations"]
            assert isinstance(raw, list)
            live = validator._LiveAppServerCapture(
                raw[0],
                raw[1],
                bound_source,
                snapshot,
                isolate,
                suite,
            )
            process = Mock()
            process._o4_native_snapshot_launch = True
            process._o4_live_capture = live
            capture_thread_read_chronology(
                process, live, bound_source, snapshot
            )
            validator.capture_unknown_capacity_transition_signal(
                process,
                SOURCE_CARRIER_ID,
            )
            capacity = next(
                item
                for item in live.messages
                if item.get("source")
                == "task-bound-effective-context-window-observer-v3"
            )
            fitness = next(
                item
                for item in live.messages
                if item.get("source") == "task-bound-carrier-fitness-observer-v1"
            )
            self.assertEqual(capacity["usageBand"], "unknown")
            self.assertIsNone(capacity["effectiveContextWindowTokens"])
            self.assertEqual(
                fitness["compactionCountsSinceVerifiedTransition"],
                {"automatic": 0, "manual": 1},
            )
            self.assertGreaterEqual(
                fitness["materialCheckpointCountSinceLastCompaction"],
                7,
            )
            self.assertGreaterEqual(
                fitness["materialCheckpointCountSinceVerifiedTransition"],
                fitness["materialCheckpointCountSinceLastCompaction"],
            )
            with self.assertRaises(TypeError):
                validator.capture_unknown_capacity_transition_signal(  # type: ignore[call-arg]
                    process,
                    SOURCE_CARRIER_ID,
                    automatic_compactions=0,
                    manual_compactions=1,
                    checkpoints_since_compaction=7,
                    checkpoints_since_transition=7,
                )

    def test_client_effective_window_drives_task_scoped_usage_band(self) -> None:
        bound_source = source_binding()
        snapshot = snapshot_record(bound_source)
        with tempfile.TemporaryDirectory() as directory:
            isolate = Path(directory) / "isolate"
            isolate.mkdir()
            suite = validator._LiveO4CaptureSuite(
                isolate, snapshot, user_chronology_baseline()
            )
            raw_first = raw_compaction_observations()
            raw_first.insert(
                8,
                {
                    "source": "codex-app-server-json-rpc-v0.147.0",
                    "message": {
                        "method": "thread/tokenUsage/updated",
                        "params": {
                            "threadId": SOURCE_CARRIER_ID,
                            "turnId": "turn_01000001",
                            "tokenUsage": {
                                "total": {"totalTokens": 300_000},
                                "last": {"totalTokens": 155_040},
                                "modelContextWindow": 258_400,
                            },
                        },
                    },
                },
            )
            first = private_scenario(
                v1.CARRIER_SCENARIO_IDENTITIES[0],
                raw_first,
                bound_source,
                snapshot,
                "b",
            )
            captured_scenario(first, bound_source, snapshot, isolate, suite)
            second = private_scenario(
                v1.CARRIER_SCENARIO_IDENTITIES[1],
                raw_transition_observations(),
                bound_source,
                snapshot,
                "c",
            )
            raw = second["rawObservations"]
            assert isinstance(raw, list)
            live = validator._LiveAppServerCapture(
                raw[0], raw[1], bound_source, snapshot, isolate, suite
            )
            process = Mock()
            process._o4_native_snapshot_launch = True
            process._o4_live_capture = live
            capture_thread_read_chronology(
                process, live, bound_source, snapshot
            )
            validator.capture_unknown_capacity_transition_signal(
                process, SOURCE_CARRIER_ID
            )
            capacity = next(
                item
                for item in live.messages
                if item.get("source")
                == "task-bound-effective-context-window-observer-v3"
            )
            self.assertEqual(capacity["effectiveContextWindowTokens"], 258_400)
            self.assertEqual(capacity["usedContextTokens"], 155_040)
            self.assertEqual(capacity["usedContextBasisPoints"], 6_000)
            self.assertEqual(capacity["usageBand"], "transition-ready")

    def test_known_window_remains_known_in_signed_carrier_projection(self) -> None:
        bound_source = source_binding()
        snapshot = snapshot_record(bound_source)
        with tempfile.TemporaryDirectory() as directory:
            isolate = Path(directory) / "isolate"
            isolate.mkdir()
            suite = validator._LiveO4CaptureSuite(
                isolate, snapshot, user_chronology_baseline()
            )
            raw_first = raw_compaction_observations()
            raw_first.insert(
                8,
                {
                    "source": "codex-app-server-json-rpc-v0.147.0",
                    "message": {
                        "method": "thread/tokenUsage/updated",
                        "params": {
                            "threadId": SOURCE_CARRIER_ID,
                            "tokenUsage": {
                                "last": {"totalTokens": 155_040},
                                "modelContextWindow": 258_400,
                            },
                        },
                    },
                },
            )
            first = private_scenario(
                v1.CARRIER_SCENARIO_IDENTITIES[0],
                raw_first,
                bound_source,
                snapshot,
                "6",
            )
            captured_scenario(first, bound_source, snapshot, isolate, suite)
            second = private_scenario(
                v1.CARRIER_SCENARIO_IDENTITIES[1],
                raw_transition_observations(),
                bound_source,
                snapshot,
                "7",
            )
            captured = captured_scenario(
                second, bound_source, snapshot, isolate, suite
            )
            value = captured._value
            projection = validator.project_raw_carrier_observations(
                str(value["scenarioIdentity"]),
                value["rawObservations"],
                source_binding=bound_source,
                snapshot=snapshot,
                source_carrier_id=SOURCE_CARRIER_ID,
                expected_head=SOURCE_REVISION,
                destination_carrier_id=DESTINATION_CARRIER_ID,
                expected_cwd=TEST_CWD,
            )
            carrier = projection["carrierProjection"]
            self.assertEqual(
                carrier["sourceFormat"],
                "public-safe-codex-app-server-goal-observation-v3",
            )
            self.assertEqual(
                carrier["eventSequence"][0]["eventClass"],
                "known-client-effective-context-band-triggered",
            )
            self.assertEqual(
                carrier["eventSequence"][0]["state"], "transition-ready"
            )
            self.assertTrue(
                validator._carrier_projection_valid(
                    projection, bound_source, snapshot
                )
            )
            carrier["eventShapeSha256"] = "0" * 64
            self.assertFalse(
                validator._carrier_projection_valid(
                    projection, bound_source, snapshot
                )
            )

    def test_client_write_cannot_spoof_effective_window_notification(self) -> None:
        bound_source = source_binding()
        snapshot = snapshot_record(bound_source)
        with tempfile.TemporaryDirectory() as directory:
            isolate = Path(directory) / "isolate"
            isolate.mkdir()
            suite = validator._LiveO4CaptureSuite(
                isolate, snapshot, user_chronology_baseline()
            )
            raw_first = raw_compaction_observations()
            raw_first.insert(
                8,
                {
                    "source": "codex-app-server-json-rpc-v0.147.0",
                    "message": {
                        "id": 77,
                        "method": "thread/tokenUsage/updated",
                        "params": {
                            "threadId": SOURCE_CARRIER_ID,
                            "tokenUsage": {
                                "last": {"totalTokens": 250_000},
                                "modelContextWindow": 258_400,
                            },
                        },
                    },
                },
            )
            first = private_scenario(
                v1.CARRIER_SCENARIO_IDENTITIES[0],
                raw_first,
                bound_source,
                snapshot,
                "d",
            )
            captured_scenario(first, bound_source, snapshot, isolate, suite)
            second = private_scenario(
                v1.CARRIER_SCENARIO_IDENTITIES[1],
                raw_transition_observations(),
                bound_source,
                snapshot,
                "e",
            )
            raw = second["rawObservations"]
            assert isinstance(raw, list)
            live = validator._LiveAppServerCapture(
                raw[0], raw[1], bound_source, snapshot, isolate, suite
            )
            process = Mock()
            process._o4_native_snapshot_launch = True
            process._o4_live_capture = live
            capture_thread_read_chronology(process, live, bound_source, snapshot)
            validator.capture_unknown_capacity_transition_signal(
                process, SOURCE_CARRIER_ID
            )
            capacity = next(
                item
                for item in live.messages
                if item.get("source")
                == "task-bound-effective-context-window-observer-v3"
            )
            self.assertEqual(capacity["usageBand"], "unknown")
            self.assertIsNone(capacity["tokenUsageRecordSha256"])

    def test_known_efficient_window_rejects_transition(self) -> None:
        bound_source = source_binding()
        snapshot = snapshot_record(bound_source)
        with tempfile.TemporaryDirectory() as directory:
            isolate = Path(directory) / "isolate"
            isolate.mkdir()
            suite = validator._LiveO4CaptureSuite(
                isolate, snapshot, user_chronology_baseline()
            )
            raw_first = raw_compaction_observations()
            raw_first.insert(
                8,
                {
                    "source": "codex-app-server-json-rpc-v0.147.0",
                    "message": {
                        "method": "thread/tokenUsage/updated",
                        "params": {
                            "threadId": SOURCE_CARRIER_ID,
                            "tokenUsage": {
                                "last": {"totalTokens": 127_000},
                                "modelContextWindow": 258_400,
                            },
                        },
                    },
                },
            )
            first = private_scenario(
                v1.CARRIER_SCENARIO_IDENTITIES[0],
                raw_first,
                bound_source,
                snapshot,
                "f",
            )
            captured_scenario(first, bound_source, snapshot, isolate, suite)
            second = private_scenario(
                v1.CARRIER_SCENARIO_IDENTITIES[1],
                raw_transition_observations(),
                bound_source,
                snapshot,
                "1",
            )
            raw = second["rawObservations"]
            assert isinstance(raw, list)
            live = validator._LiveAppServerCapture(
                raw[0], raw[1], bound_source, snapshot, isolate, suite
            )
            process = Mock()
            process._o4_native_snapshot_launch = True
            process._o4_live_capture = live
            capture_thread_read_chronology(process, live, bound_source, snapshot)
            with self.assertRaisesRegex(ValueError, "efficient carrier"):
                validator.capture_unknown_capacity_transition_signal(
                    process, SOURCE_CARRIER_ID
                )

    def test_new_user_message_before_transition_rejects_proactive_claim(self) -> None:
        bound_source = source_binding()
        snapshot = snapshot_record(bound_source)
        with tempfile.TemporaryDirectory() as directory:
            isolate = Path(directory) / "isolate"
            isolate.mkdir()
            suite = validator._LiveO4CaptureSuite(
                isolate, snapshot, user_chronology_baseline()
            )
            first = private_scenario(
                v1.CARRIER_SCENARIO_IDENTITIES[0],
                raw_compaction_observations(),
                bound_source,
                snapshot,
                "2",
            )
            captured_scenario(first, bound_source, snapshot, isolate, suite)
            second = private_scenario(
                v1.CARRIER_SCENARIO_IDENTITIES[1],
                raw_transition_observations(),
                bound_source,
                snapshot,
                "3",
            )
            raw = second["rawObservations"]
            assert isinstance(raw, list)
            live = validator._LiveAppServerCapture(
                raw[0], raw[1], bound_source, snapshot, isolate, suite
            )
            process = Mock()
            process._o4_native_snapshot_launch = True
            process._o4_live_capture = live
            capture_thread_read_chronology(
                process,
                live,
                bound_source,
                snapshot,
                user_message_ids=("user-message-1", "user-message-2"),
            )
            with self.assertRaisesRegex(ValueError, "user intervention"):
                validator.capture_unknown_capacity_transition_signal(
                    process, SOURCE_CARRIER_ID
                )

    def test_user_handoff_before_scenario_baseline_differs_from_registration(self) -> None:
        bound_source = source_binding()
        snapshot = snapshot_record(bound_source)
        with tempfile.TemporaryDirectory() as directory:
            isolate = Path(directory) / "isolate"
            isolate.mkdir()
            suite = validator._LiveO4CaptureSuite(
                isolate, snapshot, user_chronology_baseline()
            )
            first = private_scenario(
                v1.CARRIER_SCENARIO_IDENTITIES[0],
                raw_compaction_observations(),
                bound_source,
                snapshot,
                "4",
            )
            raw_first = first["rawObservations"]
            assert isinstance(raw_first, list)
            chronology_response = raw_first[3]
            assert isinstance(chronology_response, dict)
            turns = chronology_response["message"]["result"]["thread"]["turns"]
            turns[0]["items"].append(
                {
                    "type": "userMessage",
                    "id": "user-handoff-request",
                    "content": [
                        {"type": "text", "text": "Please hand off now."}
                    ],
                }
            )
            with self.assertRaisesRegex(ValueError, "measurement-start"):
                captured_scenario(
                    first, bound_source, snapshot, isolate, suite
                )
            self.assertFalse(suite.measurement_start_chronology_verified)
            self.assertEqual(suite.completed_scenarios, [])

    def test_compaction_cannot_complete_without_code_owned_checkpoints(self) -> None:
        bound_source = source_binding()
        snapshot = snapshot_record(bound_source)
        with tempfile.TemporaryDirectory() as directory:
            isolate = Path(directory) / "isolate"
            isolate.mkdir()
            suite = validator._LiveO4CaptureSuite(
                isolate, snapshot, user_chronology_baseline()
            )
            scenario = private_scenario(
                v1.CARRIER_SCENARIO_IDENTITIES[0],
                raw_compaction_observations(),
                bound_source,
                snapshot,
                "6",
            )
            raw = scenario["rawObservations"]
            assert isinstance(raw, list)
            capture = validator._LiveAppServerCapture(
                raw[0],
                raw[1],
                bound_source,
                snapshot,
                isolate,
                suite,
            )
            with self.assertRaisesRegex(ValueError, "seven code-owned"):
                suite.complete_capture(
                    v1.CARRIER_SCENARIO_IDENTITIES[0], capture
                )
            self.assertIsNone(suite.material_checkpoint_binding)
            self.assertEqual(suite.checkpoints_since_compaction, 0)

    def test_failed_compact_write_cannot_unlock_repository_checkpoint(self) -> None:
        bound_source = source_binding()
        snapshot = snapshot_record(bound_source)

        class FailingStdin(io.BytesIO):
            failed = False

            def flush(self) -> None:
                if not self.failed:
                    self.failed = True
                    raise OSError("fixture compact write failure")
                super().flush()

        with tempfile.TemporaryDirectory() as directory:
            isolate = Path(directory) / "isolate"
            isolate.mkdir()
            suite = validator._LiveO4CaptureSuite(
                isolate, snapshot, user_chronology_baseline()
            )
            scenario = private_scenario(
                v1.CARRIER_SCENARIO_IDENTITIES[0],
                raw_compaction_observations(),
                bound_source,
                snapshot,
                "6",
            )
            raw = scenario["rawObservations"]
            assert isinstance(raw, list)
            capture = validator._LiveAppServerCapture(
                raw[0], raw[1], bound_source, snapshot, isolate, suite
            )
            process = Mock()
            process._o4_native_snapshot_launch = True
            process._o4_live_capture = capture
            capture_thread_read_chronology(
                process, capture, bound_source, snapshot, request_id=190
            )
            process.stdin = FailingStdin()
            with self.assertRaisesRegex(ValueError, "request write failed"):
                validator.write_snapshot_app_server_message(
                    process,
                    {
                        "method": "thread/compact/start",
                        "id": 191,
                        "params": {"threadId": SOURCE_CARRIER_ID},
                    },
                )
            self.assertFalse(suite.measurement_start_chronology_verified)
            self.assertTrue(capture.poisoned)
            with self.assertRaisesRegex(ValueError, "capture is unavailable"):
                validator.write_snapshot_app_server_message(
                    process,
                    {
                        "method": "thread/compact/start",
                        "id": 191,
                        "params": {"threadId": SOURCE_CARRIER_ID},
                    },
                )
            with patch.object(validator, "run_fault_suite") as fault_suite:
                with self.assertRaisesRegex(ValueError, "capture is unavailable"):
                    validator.capture_repository_checkpoint(
                        process, Path("."), SOURCE_CARRIER_ID, SOURCE_REVISION
                    )
            fault_suite.assert_not_called()

    def test_post_compaction_handoff_blocks_fault_and_repository_checkpoint(
        self,
    ) -> None:
        bound_source = source_binding()
        snapshot = snapshot_record(bound_source)
        with tempfile.TemporaryDirectory() as directory:
            isolate = Path(directory) / "isolate"
            isolate.mkdir()
            suite = validator._LiveO4CaptureSuite(
                isolate, snapshot, user_chronology_baseline()
            )
            scenario = private_scenario(
                v1.CARRIER_SCENARIO_IDENTITIES[0],
                raw_compaction_observations(),
                bound_source,
                snapshot,
                "6",
            )
            raw = scenario["rawObservations"]
            assert isinstance(raw, list)
            capture = validator._LiveAppServerCapture(
                raw[0], raw[1], bound_source, snapshot, isolate, suite
            )
            process = Mock()
            process._o4_native_snapshot_launch = True
            process._o4_live_capture = capture
            capture_thread_read_chronology(
                process, capture, bound_source, snapshot, request_id=192
            )
            process.stdin = io.BytesIO()
            validator.write_snapshot_app_server_message(
                process,
                {
                    "method": "thread/compact/start",
                    "id": 193,
                    "params": {"threadId": SOURCE_CARRIER_ID},
                },
            )
            self.assertTrue(suite.measurement_start_chronology_verified)
            compact_lifecycle = [
                {"id": 193, "result": {}},
                {
                    "method": "item/started",
                    "params": {
                        "threadId": SOURCE_CARRIER_ID,
                        "turnId": "turn-late-handoff",
                        "item": {"type": "contextCompaction", "id": "item-late"},
                    },
                },
                {
                    "method": "item/completed",
                    "params": {
                        "threadId": SOURCE_CARRIER_ID,
                        "turnId": "turn-late-handoff",
                        "item": {"type": "contextCompaction", "id": "item-late"},
                    },
                },
            ]
            process.stdout = io.BytesIO(
                b"".join(
                    json.dumps(item, separators=(",", ":")).encode("utf-8")
                    + b"\n"
                    for item in compact_lifecycle
                )
            )
            for _ in compact_lifecycle:
                validator.read_snapshot_app_server_message(
                    process, capture.launch, bound_source, snapshot
                )
            capture_thread_read_chronology(
                process,
                capture,
                bound_source,
                snapshot,
                request_id=194,
                user_message_ids=("user-message-1", "user-message-2"),
            )
            with patch.object(validator, "run_fault_suite") as fault_suite:
                with self.assertRaisesRegex(ValueError, "checkpoint chronology"):
                    validator.capture_repository_checkpoint(
                        process, Path("."), SOURCE_CARRIER_ID, SOURCE_REVISION
                    )
            fault_suite.assert_not_called()

    def test_failed_compact_response_cannot_reuse_compaction_lifecycle(self) -> None:
        bound_source = source_binding()
        snapshot = snapshot_record(bound_source)
        with tempfile.TemporaryDirectory() as directory:
            isolate = Path(directory) / "isolate"
            isolate.mkdir()
            suite = validator._LiveO4CaptureSuite(
                isolate, snapshot, user_chronology_baseline()
            )
            scenario = private_scenario(
                v1.CARRIER_SCENARIO_IDENTITIES[0],
                raw_compaction_observations(),
                bound_source,
                snapshot,
                "6",
            )
            raw = scenario["rawObservations"]
            assert isinstance(raw, list)
            capture = validator._LiveAppServerCapture(
                raw[0], raw[1], bound_source, snapshot, isolate, suite
            )
            process = Mock()
            process._o4_native_snapshot_launch = True
            process._o4_live_capture = capture
            capture_thread_read_chronology(
                process, capture, bound_source, snapshot, request_id=195
            )
            process.stdin = io.BytesIO()
            validator.write_snapshot_app_server_message(
                process,
                {
                    "method": "thread/compact/start",
                    "id": 196,
                    "params": {"threadId": SOURCE_CARRIER_ID},
                },
            )
            misleading_lifecycle = [
                {"id": 196, "error": {"code": -32000, "message": "failed"}},
                {
                    "method": "item/started",
                    "params": {
                        "threadId": SOURCE_CARRIER_ID,
                        "turnId": "turn-unrelated",
                        "item": {
                            "type": "contextCompaction",
                            "id": "item-unrelated",
                        },
                    },
                },
                {
                    "method": "item/completed",
                    "params": {
                        "threadId": SOURCE_CARRIER_ID,
                        "turnId": "turn-unrelated",
                        "item": {
                            "type": "contextCompaction",
                            "id": "item-unrelated",
                        },
                    },
                },
            ]
            process.stdout = io.BytesIO(
                b"".join(
                    json.dumps(item, separators=(",", ":")).encode("utf-8")
                    + b"\n"
                    for item in misleading_lifecycle
                )
            )
            for _ in misleading_lifecycle:
                validator.read_snapshot_app_server_message(
                    process, capture.launch, bound_source, snapshot
                )
            capture_thread_read_chronology(
                process, capture, bound_source, snapshot, request_id=197
            )
            with patch.object(validator, "run_fault_suite") as fault_suite:
                with self.assertRaisesRegex(ValueError, "checkpoint chronology"):
                    validator.capture_repository_checkpoint(
                        process, Path("."), SOURCE_CARRIER_ID, SOURCE_REVISION
                    )
            fault_suite.assert_not_called()

    def test_compact_response_requires_type_exact_id_and_exact_shape(self) -> None:
        bound_source = source_binding()
        snapshot = snapshot_record(bound_source)
        cases = (
            ({"id": True, "result": {}}, "JSON-RPC id is invalid"),
            (
                {"id": 199, "result": {}, "unexpected": "alias"},
                "response is unpaired",
            ),
        )
        for response, diagnostic in cases:
            with self.subTest(response=response):
                with tempfile.TemporaryDirectory() as directory:
                    isolate = Path(directory) / "isolate"
                    isolate.mkdir()
                    suite = validator._LiveO4CaptureSuite(
                        isolate, snapshot, user_chronology_baseline()
                    )
                    scenario = private_scenario(
                        v1.CARRIER_SCENARIO_IDENTITIES[0],
                        raw_compaction_observations(),
                        bound_source,
                        snapshot,
                        "6",
                    )
                    raw = scenario["rawObservations"]
                    assert isinstance(raw, list)
                    capture = validator._LiveAppServerCapture(
                        raw[0], raw[1], bound_source, snapshot, isolate, suite
                    )
                    process = Mock()
                    process._o4_native_snapshot_launch = True
                    process._o4_live_capture = capture
                    capture_thread_read_chronology(
                        process, capture, bound_source, snapshot, request_id=198
                    )
                    process.stdin = io.BytesIO()
                    validator.write_snapshot_app_server_message(
                        process,
                        {
                            "method": "thread/compact/start",
                            "id": 199,
                            "params": {"threadId": SOURCE_CARRIER_ID},
                        },
                    )
                    process.stdout = io.BytesIO(
                        json.dumps(response, separators=(",", ":")).encode("utf-8")
                        + b"\n"
                    )
                    with self.assertRaisesRegex(ValueError, diagnostic):
                        validator.read_snapshot_app_server_message(
                            process, capture.launch, bound_source, snapshot
                        )
                    with patch.object(validator, "run_fault_suite") as fault_suite:
                        with self.assertRaisesRegex(
                            ValueError, "capture is unavailable"
                        ):
                            validator.capture_repository_checkpoint(
                                process,
                                Path("."),
                                SOURCE_CARRIER_ID,
                                SOURCE_REVISION,
                            )
                    fault_suite.assert_not_called()

    def test_duplicate_request_id_and_stale_read_response_cannot_alias(self) -> None:
        bound_source = source_binding()
        snapshot = snapshot_record(bound_source)
        with tempfile.TemporaryDirectory() as directory:
            isolate = Path(directory) / "isolate"
            isolate.mkdir()
            suite = validator._LiveO4CaptureSuite(
                isolate, snapshot, user_chronology_baseline()
            )
            scenario = private_scenario(
                v1.CARRIER_SCENARIO_IDENTITIES[0],
                raw_compaction_observations(),
                bound_source,
                snapshot,
                "6",
            )
            raw = scenario["rawObservations"]
            assert isinstance(raw, list)
            capture = validator._LiveAppServerCapture(
                raw[0], raw[1], bound_source, snapshot, isolate, suite
            )
            process = Mock()
            process._o4_native_snapshot_launch = True
            process._o4_live_capture = capture
            capture_thread_read_chronology(
                process, capture, bound_source, snapshot, request_id=210
            )
            process.stdin = io.BytesIO()
            stale_read = {
                "method": "thread/read",
                "id": 211,
                "params": {"threadId": SOURCE_CARRIER_ID, "includeTurns": True},
            }
            validator.write_snapshot_app_server_message(process, stale_read)
            validator.write_snapshot_app_server_message(
                process,
                {
                    "method": "thread/compact/start",
                    "id": 212,
                    "params": {"threadId": SOURCE_CARRIER_ID},
                },
            )
            with self.assertRaisesRegex(ValueError, "invalid or reused"):
                validator.write_snapshot_app_server_message(process, stale_read)
            lifecycle = [
                {"id": 212, "result": {}},
                {
                    "method": "item/started",
                    "params": {
                        "threadId": SOURCE_CARRIER_ID,
                        "turnId": "turn-stale-read",
                        "item": {"type": "contextCompaction", "id": "item-stale"},
                    },
                },
                {
                    "method": "item/completed",
                    "params": {
                        "threadId": SOURCE_CARRIER_ID,
                        "turnId": "turn-stale-read",
                        "item": {"type": "contextCompaction", "id": "item-stale"},
                    },
                },
                {
                    "id": 211,
                    "result": {
                        "thread": {
                            "id": SOURCE_CARRIER_ID,
                            "turns": [
                                {
                                    "id": "turn-user-chronology",
                                    "items": [
                                        {
                                            "type": "userMessage",
                                            "id": "user-message-1",
                                            "content": [
                                                {
                                                    "type": "text",
                                                    "text": v1.CARRIER_GOAL_TEXT,
                                                }
                                            ],
                                        }
                                    ],
                                }
                            ],
                        }
                    },
                },
            ]
            process.stdout = io.BytesIO(
                b"".join(
                    json.dumps(item, separators=(",", ":")).encode("utf-8")
                    + b"\n"
                    for item in lifecycle
                )
            )
            for _ in lifecycle:
                validator.read_snapshot_app_server_message(
                    process, capture.launch, bound_source, snapshot
                )
            with patch.object(validator, "run_fault_suite") as fault_suite:
                with self.assertRaisesRegex(ValueError, "checkpoint chronology"):
                    validator.capture_repository_checkpoint(
                        process, Path("."), SOURCE_CARRIER_ID, SOURCE_REVISION
                    )
            fault_suite.assert_not_called()

    def test_duplicate_observed_response_irreversibly_poisons_capture(self) -> None:
        bound_source = source_binding()
        snapshot = snapshot_record(bound_source)
        with tempfile.TemporaryDirectory() as directory:
            isolate = Path(directory) / "isolate"
            isolate.mkdir()
            suite = validator._LiveO4CaptureSuite(
                isolate, snapshot, user_chronology_baseline()
            )
            scenario = private_scenario(
                v1.CARRIER_SCENARIO_IDENTITIES[0],
                raw_compaction_observations(),
                bound_source,
                snapshot,
                "6",
            )
            raw = scenario["rawObservations"]
            assert isinstance(raw, list)
            capture = validator._LiveAppServerCapture(
                raw[0], raw[1], bound_source, snapshot, isolate, suite
            )
            process = Mock()
            process._o4_native_snapshot_launch = True
            process._o4_live_capture = capture
            capture_thread_read_chronology(
                process, capture, bound_source, snapshot, request_id=220
            )
            process.stdin = io.BytesIO()
            validator.write_snapshot_app_server_message(
                process,
                {
                    "method": "thread/compact/start",
                    "id": 221,
                    "params": {"threadId": SOURCE_CARRIER_ID},
                },
            )
            duplicate = {"id": 221, "result": {}}
            process.stdout = io.BytesIO(
                b"".join(
                    json.dumps(duplicate, separators=(",", ":")).encode("utf-8")
                    + b"\n"
                    for _ in range(2)
                )
            )
            validator.read_snapshot_app_server_message(
                process, capture.launch, bound_source, snapshot
            )
            with self.assertRaisesRegex(ValueError, "response is unpaired"):
                validator.read_snapshot_app_server_message(
                    process, capture.launch, bound_source, snapshot
                )
            self.assertTrue(capture.poisoned)
            with self.assertRaisesRegex(ValueError, "capture is unavailable"):
                validator.read_snapshot_app_server_message(
                    process, capture.launch, bound_source, snapshot
                )
            with patch.object(validator, "run_fault_suite") as fault_suite:
                with self.assertRaisesRegex(ValueError, "capture is unavailable"):
                    validator.capture_repository_checkpoint(
                        process, Path("."), SOURCE_CARRIER_ID, SOURCE_REVISION
                    )
            fault_suite.assert_not_called()

    def test_repeated_checkpoint_identity_cannot_inflate_material_count(self) -> None:
        bound_source = source_binding()
        snapshot = snapshot_record(bound_source)
        with tempfile.TemporaryDirectory() as directory:
            isolate = Path(directory) / "isolate"
            isolate.mkdir()
            suite = validator._LiveO4CaptureSuite(
                isolate, snapshot, user_chronology_baseline()
            )
            scenario = private_scenario(
                v1.CARRIER_SCENARIO_IDENTITIES[0],
                raw_compaction_observations(),
                bound_source,
                snapshot,
                "7",
            )
            captured = captured_scenario(
                scenario, bound_source, snapshot, isolate, suite
            )
            capture = captured._capture
            fault_suite = passing_fault_suite(SOURCE_REVISION)
            self.assertEqual(
                suite.material_checkpoint_binding["materialCheckpointCount"], 7
            )
            with self.assertRaisesRegex(ValueError, "checkpoint set"):
                suite.bind_compaction_checkpoint(
                    capture,
                    fault_suite,
                    {"eventShapeSha256": "a" * 64},
                )
            self.assertEqual(
                suite.material_checkpoint_binding["materialCheckpointCount"], 7
            )

    def test_measurement_baseline_requires_v3_program_only_activation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run_git(root, "init", "--quiet", "--initial-branch=main")
            run_git(root, "config", "user.name", "O4 V3 Fixture")
            run_git(root, "config", "user.email", "o4-v3@example.invalid")
            run_git(root, "config", "commit.gpgsign", "false")
            run_git(root, "config", "core.autocrlf", "false")
            write_json(root / "product/program.json", {"status": "ready"})
            write_json(root / validator.REGISTRATION_LOCATOR, {"schema": 1})
            run_git(
                root,
                "add",
                "product/program.json",
                validator.REGISTRATION_LOCATOR,
            )
            run_git(root, "commit", "--quiet", "--no-gpg-sign", "-m", "Register")
            registration_revision = run_git(root, "rev-parse", "HEAD")
            active = {
                "status": "active",
                "activeIncrementId": validator.INCREMENT_ID,
                "increments": [
                    {
                        "id": validator.INCREMENT_ID,
                        "state": "active",
                        "taskRegistration": {
                            "locator": validator.REGISTRATION_LOCATOR,
                            "sourceRevision": registration_revision,
                        },
                        "workItems": [{"id": "work.o4-v3", "state": "active"}],
                    }
                ],
            }
            write_json(root / "product/program.json", active)
            run_git(root, "add", "product/program.json")
            run_git(root, "commit", "--quiet", "--no-gpg-sign", "-m", "Activate")
            baseline = run_git(root, "rev-parse", "HEAD")
            self.assertTrue(validator._measurement_baseline_valid(root, baseline))

    def test_fault_suite_requires_every_v3_floor(self) -> None:
        def passing(
            root: Path,
            source_revision: str,
            scenario: v1.FaultScenario,
        ) -> dict[str, object]:
            del root, source_revision, scenario
            return {
                "baselineValid": True,
                "divergenceDetected": True,
                "expectedDiagnosticObserved": True,
                "recoveredValid": True,
                "recoveredHeadMatches": True,
                "probeCleanupVerified": True,
                "faultReportSha256": "d" * 64,
                "recoveryReportSha256": "e" * 64,
            }

        result = validator.run_fault_suite(
            Path("."), SOURCE_REVISION, executor=passing
        )
        self.assertEqual(result["suiteIdentity"], validator.SUITE_IDENTITY)
        self.assertTrue(result["allFaultControlsObserved"])


if __name__ == "__main__":
    unittest.main()
