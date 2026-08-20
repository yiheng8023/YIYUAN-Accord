"""Third-generation task validator for the v1.2 O4 controlled suite.

The first two validators are frozen by immutable stopped registrations.  This
module keeps version selection task-time and dynamic, but requires the selected
official Codex native executable to be copied into the exact authorized
isolated resource before manifest capture and registration.  Outcome execution
may then use only that content-addressed snapshot.  The module is scoped to the
six current O4 scenarios; it is not a generic runtime or version manager.
"""

from __future__ import annotations

import base64
from copy import deepcopy
import ctypes
import hashlib
import json
import os
from pathlib import Path
import queue
import re
import secrets
import shutil
import stat
import subprocess
import tarfile
import tempfile
import threading
import time
from typing import Any, Callable, Mapping
import urllib.error
import urllib.parse
import urllib.request

from . import task_validator_o4_continuous_self_correction as v1
from . import task_validator_o4_continuous_self_correction_v2 as v2


INCREMENT_ID = "increment.v12-o4-continuous-self-correction-third-generation"
VALIDATOR_KIND = "o4-continuous-self-correction-validator-v3"
VALIDATOR_LOCATOR = "harness/task_validator_o4_continuous_self_correction_v3.py"
SUITE_IDENTITY = "o4-continuous-self-correction.controlled-v3"
REGISTRATION_LOCATOR = (
    "product/evidence/o4-continuous-self-correction-third-generation-registration.json"
)
OBSERVATION_LOCATOR = (
    "product/evidence/o4-continuous-self-correction-third-generation-observation.json"
)
CLAIM_CEILING = (
    "bounded-v1.2-controlled-Windows-Codex-exact-task-snapshot-"
    "self-correction-and-carrier-evidence-only"
)

SNAPSHOT_RELATIVE_PARTS = (".harness", "o4-v3-native", "codex.exe")
ISOLATE_MARKER_RELATIVE_PARTS = (".aah-o4-v3-isolate.json",)
PRIVATE_MEASUREMENT_RELATIVE_PARTS = (
    "o4-v3-private-measurement.json",
)
MAX_PRIVATE_MEASUREMENT_BYTES = 1_048_576
MAX_NATIVE_EXECUTABLE_BYTES = 536_870_912
MAX_NATIVE_PACKAGE_ARCHIVE_BYTES = 268_435_456
MAX_NATIVE_PACKAGE_EXPANDED_BYTES = 805_306_368
MAX_OFFICIAL_METADATA_BYTES = 2_097_152
MAX_OFFICIAL_SOURCE_BYTES = 2_097_152
SNAPSHOT_PUBLIC_ID_PATTERN = re.compile(
    r"codex-native-snapshot\.public-v1:[0-9a-f]{32}"
)
LAUNCH_PUBLIC_ID_PATTERN = re.compile(
    r"codex-app-server-launch\.public-v1:[0-9a-f]{32}"
)
SEMVER_PATTERN = re.compile(r"[0-9]+\.[0-9]+\.[0-9]+")
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
GIT_OBJECT_PATTERN = re.compile(r"[0-9a-f]{40}")
SOURCE_BLOB_PATHS = (
    "codex-rs/protocol/src/protocol.rs",
    "codex-rs/app-server/README.md",
    "codex-rs/app-server-protocol/src/protocol/v2/thread.rs",
    "codex-rs/app-server-protocol/src/protocol/common.rs",
    "codex-rs/app-server-protocol/src/protocol/v2/thread_data.rs",
    "codex-rs/app-server/src/request_processors/thread_goal_processor.rs",
)
OPENAI_SIGNER_COMPONENTS = (
    'CN="OpenAI OpCo, LLC"',
    'O="OpenAI OpCo, LLC"',
)
ALLOWED_NETWORK_ENVIRONMENT_KEYS = frozenset(
    {
        "ALL_PROXY",
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "NO_PROXY",
        "REQUESTS_CA_BUNDLE",
        "SSL_CERT_FILE",
    }
)
SNAPSHOT_TERMINAL_REASONS = frozenset(
    {"accepted", "stopped", "deterministic-failure"}
)
PRIVATE_SOURCE_TERMINAL_REASONS = frozenset(
    {"accepted", "claim-revoked", "stopped", "expiry", "deterministic-failure"}
)
OFFICIAL_HTTPS_HOSTS = frozenset(
    {"registry.npmjs.org", "raw.githubusercontent.com"}
)
APP_SERVER_SOURCE_TOKENS = (
    b"thread/start",
    b"thread/compact/start",
    b"thread/archive",
    b"thread/started",
    b"thread/goal/set",
    b"thread/goal/get",
    b"thread/goal/clear",
    b"thread/read",
    b"includeTurns",
    b"userMessage",
    b"content",
    b"forkedFromId",
    b"deferGoalContinuation",
    b"contextCompaction",
)
ATTESTATION_NAMESPACE = "agent-autonomy-harness-o4-v3"
ATTESTATION_PUBLIC_ID_PATTERN = re.compile(
    r"o4-capture-attestation\.public-v1:[0-9a-f]{32}"
)
ATTESTATION_KEY_RELATIVE_PARTS = ("o4-v3-capture-ed25519",)
MAX_ATTESTATION_PAYLOAD_BYTES = 1_048_576
MAX_ATTESTATION_SIGNATURE_BYTES = 16_384
MAX_APP_SERVER_MESSAGE_BYTES = 262_144
MAX_APP_SERVER_STDERR_BYTES = 65_536
MAX_ISOLATE_CLEANUP_NODES = 10_000
MAX_ISOLATE_CLEANUP_BYTES = 536_870_912


class _BoundedAppServerStreams:
    """Drain both child streams without deadlock; retain no private stderr text."""

    def __init__(self, process: Any) -> None:
        if getattr(process, "stdout", None) is None or getattr(
            process, "stderr", None
        ) is None:
            raise ValueError("App Server process streams are unavailable")
        self._stdout: queue.Queue[bytes | None] = queue.Queue(maxsize=256)
        self._stderr_bytes = 0
        self._error: str | None = None
        self._lock = threading.Lock()
        self._stdout_thread = threading.Thread(
            target=self._drain_stdout,
            args=(process.stdout,),
            name="aah-o4-v3-app-server-stdout",
            daemon=True,
        )
        self._stderr_thread = threading.Thread(
            target=self._drain_stderr,
            args=(process.stderr,),
            name="aah-o4-v3-app-server-stderr",
            daemon=True,
        )
        self._stdout_thread.start()
        self._stderr_thread.start()

    def _fail(self, message: str) -> None:
        with self._lock:
            if self._error is None:
                self._error = message

    def _drain_stdout(self, stream: Any) -> None:
        try:
            while True:
                raw = stream.readline(MAX_APP_SERVER_MESSAGE_BYTES + 1)
                if raw == b"":
                    self._stdout.put(None)
                    return
                if (
                    not isinstance(raw, bytes)
                    or len(raw) > MAX_APP_SERVER_MESSAGE_BYTES
                    or not raw.endswith(b"\n")
                ):
                    self._fail("App Server stdout framing exceeded the bound")
                    self._stdout.put(None)
                    return
                self._stdout.put(raw)
        except (AttributeError, OSError, TypeError, ValueError):
            self._fail("App Server stdout capture failed")
            try:
                self._stdout.put_nowait(None)
            except queue.Full:
                pass

    def _drain_stderr(self, stream: Any) -> None:
        try:
            while True:
                chunk = stream.read(4_096)
                if chunk == b"":
                    return
                if not isinstance(chunk, bytes):
                    self._fail("App Server stderr capture returned non-bytes")
                    return
                with self._lock:
                    self._stderr_bytes += len(chunk)
                    if self._stderr_bytes > MAX_APP_SERVER_STDERR_BYTES:
                        self._error = "App Server stderr exceeded the byte bound"
                        return
        except (AttributeError, OSError, TypeError, ValueError):
            self._fail("App Server stderr capture failed")

    def read(self, timeout: float) -> bytes:
        if not isinstance(timeout, (int, float)) or isinstance(timeout, bool) or not (
            0 < timeout <= 60
        ):
            raise ValueError("App Server response timeout is invalid")
        try:
            item = self._stdout.get(timeout=timeout)
        except queue.Empty as exc:
            raise ValueError("App Server response timed out") from exc
        if self._error is not None:
            raise ValueError(self._error)
        if item is None:
            raise ValueError("App Server stdout closed before a response")
        return item

    def finish(self, timeout: float) -> None:
        deadline = time.monotonic() + timeout
        for thread in (self._stdout_thread, self._stderr_thread):
            thread.join(max(0.0, deadline - time.monotonic()))
        if (
            self._stdout_thread.is_alive()
            or self._stderr_thread.is_alive()
            or self._error is not None
        ):
            raise ValueError("App Server streams did not close within their bounds")
        remaining = list(self._stdout.queue)
        if remaining not in ([], [None]):
            raise ValueError("App Server stdout retained unconsumed responses")


_LIVE_CAPTURE_ORIGIN = object()
_CAPTURE_EVENT_ORIGIN = object()


def _json_rpc_id_key(value: Any) -> tuple[type[int] | type[str], int | str] | None:
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        return None
    if isinstance(value, int) and value < 0:
        return None
    return (type(value), value)


class _CodeOwnedCaptureEvent:
    """One value emitted only after its bound production effect was observed."""

    def __init__(
        self,
        origin: object,
        capture: _LiveAppServerCapture,
        kind: str,
        value: dict[str, Any],
    ) -> None:
        if (
            origin is not _CAPTURE_EVENT_ORIGIN
            or not isinstance(capture, _LiveAppServerCapture)
            or capture.origin is not _LIVE_CAPTURE_ORIGIN
            or kind
            not in {
                "request-write",
                "response-read",
                "carrier-fitness-observation",
                "canonical-verifier-checkpoint",
                "git-clean-head-checkpoint",
                "source-release-preflight",
                "clean-process-terminal",
            }
            or not isinstance(value, dict)
            or not v1._json_within_limits(value)
        ):
            raise ValueError("O4 code-owned capture event is invalid")
        self._capture = capture
        self._kind = kind
        self._value = deepcopy(value)


def _code_owned_capture_event(
    capture: _LiveAppServerCapture,
    kind: str,
    value: dict[str, Any],
) -> _CodeOwnedCaptureEvent:
    return _CodeOwnedCaptureEvent(_CAPTURE_EVENT_ORIGIN, capture, kind, value)


class _LiveO4CaptureSuite:
    def __init__(
        self,
        isolate_root: Path,
        snapshot: dict[str, Any],
        registered_user_chronology_baseline: dict[str, Any] | None,
    ) -> None:
        self.origin = _LIVE_CAPTURE_ORIGIN
        self.isolate_root = isolate_root.resolve(strict=True)
        self.isolate_root_identity = _directory_object_identity(self.isolate_root)
        self.snapshot = deepcopy(snapshot)
        if registered_user_chronology_baseline is not None and not (
            _user_chronology_baseline_valid(registered_user_chronology_baseline)
        ):
            raise ValueError("O4 registered user chronology baseline is invalid")
        self.registered_user_chronology_baseline = (
            deepcopy(registered_user_chronology_baseline)
            if registered_user_chronology_baseline is not None
            else None
        )
        self.captures: list[_LiveAppServerCapture] = []
        self.completed_scenarios: list[str] = []
        self.automatic_compactions = 0
        self.manual_compactions = 0
        self.checkpoints_since_compaction = 0
        self.checkpoints_since_transition = 0
        self._material_checkpoint_binding: dict[str, Any] | None = None
        self._fault_suite: dict[str, Any] | None = None
        self.compaction_checkpoint_bound = False
        self._measurement_start_compact_token: (
            _MeasurementStartCompactToken | None
        ) = None

    @property
    def measurement_start_chronology_verified(self) -> bool:
        return isinstance(
            self._measurement_start_compact_token,
            _MeasurementStartCompactToken,
        )

    def _bind_measurement_start_compact_request(
        self,
        capture: _LiveAppServerCapture,
        source_carrier_id: str,
    ) -> None:
        if (
            self._measurement_start_compact_token is not None
            or capture is not self.captures[0]
            or capture.poisoned
            or self.completed_scenarios
            or self.compaction_checkpoint_bound
            or not capture.events
        ):
            raise ValueError("O4 measurement-start compact chronology is invalid")
        self._measurement_start_compact_token = _MeasurementStartCompactToken(
            _CAPTURE_EVENT_ORIGIN,
            capture,
            source_carrier_id,
            len(capture.events) - 1,
            v1._canonical_sha256(capture.events[-1][1]),
        )

    @property
    def material_checkpoint_binding(self) -> dict[str, Any] | None:
        return deepcopy(self._material_checkpoint_binding)

    @property
    def fault_suite(self) -> dict[str, Any] | None:
        return deepcopy(self._fault_suite)

    def register_capture(self, capture: _LiveAppServerCapture) -> None:
        if len(self.captures) >= 2 or self.completed_scenarios == list(
            v1.CARRIER_SCENARIO_IDENTITIES
        ):
            raise ValueError("O4 live capture suite is already complete")
        self.captures.append(capture)

    def complete_capture(
        self,
        scenario_identity: str,
        capture: _LiveAppServerCapture,
    ) -> None:
        expected_index = len(self.completed_scenarios)
        if (
            expected_index >= len(v1.CARRIER_SCENARIO_IDENTITIES)
            or scenario_identity != v1.CARRIER_SCENARIO_IDENTITIES[expected_index]
            or capture not in self.captures
            or capture.poisoned
        ):
            raise ValueError("O4 live capture suite chronology is invalid")
        if expected_index == 0:
            if (
                not self.measurement_start_chronology_verified
                or not self.compaction_checkpoint_bound
                or self._fault_suite is None
                or self._material_checkpoint_binding is None
                or self._material_checkpoint_binding.get("materialCheckpointCount")
                != 7
            ):
                raise ValueError(
                    "O4 live suite lacks seven code-owned material checkpoints"
                )
            self.manual_compactions = 1
            self.checkpoints_since_compaction = 7
            self.checkpoints_since_transition = 7
        self.completed_scenarios.append(scenario_identity)

    def bind_compaction_checkpoint(
        self,
        capture: _LiveAppServerCapture,
        fault_suite: dict[str, Any],
        reconciliation_projection: dict[str, Any],
    ) -> None:
        if (
            self.compaction_checkpoint_bound
            or self.completed_scenarios
            or not self.captures
            or capture is not self.captures[0]
            or capture.poisoned
            or fault_suite.get("allFaultControlsObserved") is not True
            or fault_suite.get("cleanupVerified") is not True
        ):
            raise ValueError("O4 compaction material checkpoint set is invalid")
        results = fault_suite.get("faultScenarioResults")
        if (
            not isinstance(results, list)
            or [
                item.get("scenarioIdentity")
                for item in results
                if isinstance(item, dict)
            ]
            != [item.scenario_identity for item in FAULT_SCENARIOS]
        ):
            raise ValueError("O4 compaction fault checkpoint set is invalid")
        fault_checkpoints = [
            "fault-recovery:"
            + str(item.get("scenarioIdentity"))
            + ":"
            + str(item.get("faultReportSha256"))
            + ":"
            + str(item.get("recoveryReportSha256"))
            for item in results
            if isinstance(item, dict)
        ]
        captured = capture.messages
        verifier_record = captured[-2] if len(captured) >= 2 else None
        git_record = captured[-1] if len(captured) >= 1 else None
        report = verifier_record.get("report") if isinstance(verifier_record, dict) else None
        git_head = git_record.get("head") if isinstance(git_record, dict) else None
        reconciliation_sha256 = reconciliation_projection.get(
            "eventShapeSha256"
        )
        verifier_report_sha256 = v1._canonical_sha256(report)
        checkpoint_identities = [
            *fault_checkpoints,
            "post-compaction-goal-authority-reconciliation-v1:"
            + reconciliation_sha256,
            "canonical-verifier:" + verifier_report_sha256,
            "git-clean-head:" + str(git_head),
        ]
        if (
            len(fault_checkpoints) != len(FAULT_SCENARIOS)
            or len(set(checkpoint_identities)) != 7
            or not isinstance(report, dict)
            or not isinstance(git_head, str)
            or GIT_OBJECT_PATTERN.fullmatch(git_head) is None
            or not isinstance(reconciliation_projection, dict)
            or not isinstance(reconciliation_sha256, str)
            or SHA256_PATTERN.fullmatch(reconciliation_sha256) is None
            or not isinstance(verifier_record, dict)
            or verifier_record.get("source")
            != "python--B--m-harness-verify-json"
            or not isinstance(git_record, dict)
            or git_record.get("source") != "git-rev-parse-and-status-v1"
        ):
            raise ValueError("O4 compaction checkpoint identity is invalid")
        self._material_checkpoint_binding = {
            "schema": 1,
            "checkpointIdentities": checkpoint_identities,
            "materialCheckpointCount": 7,
            "faultSuiteSha256": v1._canonical_sha256(fault_suite),
            "reconciliationEventShapeSha256": reconciliation_sha256,
            "verifierRecordSha256": v1._canonical_sha256(verifier_record),
            "verifierReportSha256": verifier_report_sha256,
            "gitRecordSha256": v1._canonical_sha256(git_record),
            "gitHead": git_head,
        }
        self._fault_suite = deepcopy(fault_suite)
        self.compaction_checkpoint_bound = True


class _LiveAppServerCapture:
    def __init__(
        self,
        launch: dict[str, Any],
        preflight: dict[str, Any],
        source_binding: dict[str, Any],
        snapshot: dict[str, Any],
        isolate_root: Path,
        suite: _LiveO4CaptureSuite,
    ) -> None:
        self.origin = _LIVE_CAPTURE_ORIGIN
        self.launch = deepcopy(launch)
        self.preflight = deepcopy(preflight)
        self.source_binding = deepcopy(source_binding)
        self.snapshot = deepcopy(snapshot)
        self.isolate_root = isolate_root.resolve(strict=True)
        if (
            not isinstance(suite, _LiveO4CaptureSuite)
            or suite.origin is not _LIVE_CAPTURE_ORIGIN
            or suite.isolate_root != self.isolate_root
            or suite.snapshot != snapshot
        ):
            raise ValueError("O4 live capture suite binding is invalid")
        self.suite = suite
        self._messages: list[dict[str, Any]] | tuple[dict[str, Any], ...] = []
        self._event_kinds: list[str] | tuple[str, ...] = []
        self._latest_verifier_report: dict[str, Any] | None = None
        self._terminal: dict[str, Any] | None = None
        self._sealed_digest: str | None = None
        self._seen_request_ids: set[
            tuple[type[int] | type[str], int | str]
        ] = set()
        self._pending_request_ids: set[
            tuple[type[int] | type[str], int | str]
        ] = set()
        self.poisoned = False
        self.finalized = False
        suite.register_capture(self)

    @property
    def messages(self) -> tuple[dict[str, Any], ...]:
        return tuple(deepcopy(self._messages))

    @property
    def events(self) -> tuple[tuple[str, dict[str, Any]], ...]:
        return tuple(
            (kind, deepcopy(value))
            for kind, value in zip(self._event_kinds, self._messages, strict=True)
        )

    @property
    def latest_verifier_report(self) -> dict[str, Any] | None:
        return deepcopy(self._latest_verifier_report)

    @property
    def terminal(self) -> dict[str, Any] | None:
        return deepcopy(self._terminal)

    @property
    def sealed_digest(self) -> str | None:
        return self._sealed_digest

    def _append_code_owned_event(self, event: _CodeOwnedCaptureEvent) -> None:
        request_id_key: tuple[type[int] | type[str], int | str] | None = None
        response_id_key: tuple[type[int] | type[str], int | str] | None = None
        if (
            self.origin is not _LIVE_CAPTURE_ORIGIN
            or self.poisoned
            or self.finalized
            or self._terminal is not None
            or not isinstance(self._messages, list)
            or not isinstance(self._event_kinds, list)
            or not isinstance(event, _CodeOwnedCaptureEvent)
            or event._capture is not self
            or event._kind == "clean-process-terminal"
        ):
            raise ValueError("O4 live capture message chronology is invalid")
        message = (
            event._value.get("message") if isinstance(event._value, dict) else None
        )
        if isinstance(message, dict) and "id" in message:
            rpc_id_key = _json_rpc_id_key(message.get("id"))
            if rpc_id_key is None:
                raise ValueError("O4 App Server JSON-RPC id is invalid")
            if event._kind == "request-write" and isinstance(
                message.get("method"), str
            ):
                if rpc_id_key in self._seen_request_ids:
                    raise ValueError("O4 App Server JSON-RPC request id was reused")
                request_id_key = rpc_id_key
            elif event._kind == "response-read" and "method" not in message:
                if (
                    rpc_id_key not in self._pending_request_ids
                    or not (
                        set(message) == {"id", "result"}
                        or set(message) == {"id", "error"}
                    )
                ):
                    raise ValueError("O4 App Server JSON-RPC response is unpaired")
                response_id_key = rpc_id_key
        self._messages.append(deepcopy(event._value))
        self._event_kinds.append(event._kind)
        if request_id_key is not None:
            self._seen_request_ids.add(request_id_key)
            self._pending_request_ids.add(request_id_key)
        if response_id_key is not None:
            self._pending_request_ids.remove(response_id_key)

    def _poison(self) -> None:
        self.poisoned = True

    def _bind_latest_verifier_report(self, report: dict[str, Any]) -> None:
        if self.poisoned or self._latest_verifier_report is not None or self.finalized:
            raise ValueError("O4 verifier checkpoint chronology is invalid")
        self._latest_verifier_report = deepcopy(report)

    def _bind_terminal_event(self, event: _CodeOwnedCaptureEvent) -> None:
        if (
            self._terminal is not None
            or self.poisoned
            or self.finalized
            or not isinstance(event, _CodeOwnedCaptureEvent)
            or event._capture is not self
            or event._kind != "clean-process-terminal"
        ):
            raise ValueError("O4 terminal capture chronology is invalid")
        self._terminal = deepcopy(event._value)

    def _seal(self, value: dict[str, Any]) -> None:
        if (
            self.finalized
            or self.poisoned
            or self._terminal is None
            or not isinstance(self._messages, list)
            or not isinstance(self._event_kinds, list)
            or len(self._event_kinds) != len(self._messages)
        ):
            raise ValueError("O4 live capture cannot be sealed")
        self._messages = tuple(deepcopy(self._messages))
        self._event_kinds = tuple(self._event_kinds)
        self._sealed_digest = v1._canonical_sha256(value)
        self.finalized = True


class _CapturedAppServerScenario:
    def __init__(self, capture: _LiveAppServerCapture, value: dict[str, Any]) -> None:
        if (
            capture.origin is not _LIVE_CAPTURE_ORIGIN
            or not capture.finalized
            or capture.sealed_digest != v1._canonical_sha256(value)
        ):
            raise ValueError("O4 live capture origin is invalid")
        self._capture = capture
        self._value = deepcopy(value)
        self._capture_digest = capture.sealed_digest
        self._consumed = False


class _TaskScopedSnapshotCleanup(dict[str, Any]):
    def __init__(self, value: dict[str, Any], isolate_root: Path) -> None:
        super().__init__(deepcopy(value))
        self._origin = _LIVE_CAPTURE_ORIGIN
        self._isolate_root = isolate_root.resolve(strict=True)


class _TaskAttestationPublicBinding(dict[str, Any]):
    def __init__(self, value: dict[str, Any], private_root: Path) -> None:
        super().__init__(deepcopy(value))
        self._origin = _LIVE_CAPTURE_ORIGIN
        self._private_root = private_root.resolve(strict=True)
        self._private_root_identity = _directory_object_identity(self._private_root)


class _SourceUserChronologyBaseline(dict[str, Any]):
    def __init__(
        self,
        origin: object,
        capture: _LiveAppServerCapture,
        source_carrier_id: str,
        value: dict[str, Any],
    ) -> None:
        if (
            origin is not _CAPTURE_EVENT_ORIGIN
            or not isinstance(capture, _LiveAppServerCapture)
            or capture.origin is not _LIVE_CAPTURE_ORIGIN
            or not isinstance(source_carrier_id, str)
            or not source_carrier_id
            or not _user_chronology_baseline_valid(value)
            or value.get("sourceCarrierIdentitySha256")
            != v1._canonical_sha256(source_carrier_id)
        ):
            raise ValueError("O4 source user chronology token is invalid")
        super().__init__(deepcopy(value))
        self._origin = _CAPTURE_EVENT_ORIGIN
        self._capture = capture
        self._suite = capture.suite
        self._source_carrier_id = source_carrier_id
        self._snapshot = deepcopy(capture.snapshot)
        self._source_binding = deepcopy(capture.source_binding)
        self._isolate_root = capture.isolate_root
        self._event_count = len(capture.events)
        self._response_record_sha256 = value["threadReadResponseRecordSha256"]
        self._consumed = False


class _MeasurementStartCompactToken:
    def __init__(
        self,
        origin: object,
        capture: _LiveAppServerCapture,
        source_carrier_id: str,
        request_ordinal: int,
        request_record_sha256: str,
    ) -> None:
        events = capture.events if isinstance(capture, _LiveAppServerCapture) else ()
        if (
            origin is not _CAPTURE_EVENT_ORIGIN
            or capture.origin is not _LIVE_CAPTURE_ORIGIN
            or capture.poisoned
            or not isinstance(source_carrier_id, str)
            or not source_carrier_id
            or type(request_ordinal) is not int
            or request_ordinal != len(events) - 1
            or request_ordinal < 0
            or SHA256_PATTERN.fullmatch(request_record_sha256) is None
        ):
            raise ValueError("O4 measurement-start compact token is invalid")
        kind, record = events[request_ordinal]
        message = record.get("message") if isinstance(record, dict) else None
        params = message.get("params") if isinstance(message, dict) else None
        if (
            kind != "request-write"
            or not isinstance(message, dict)
            or message.get("method") != "thread/compact/start"
            or not isinstance(params, dict)
            or params.get("threadId") != source_carrier_id
            or v1._canonical_sha256(record) != request_record_sha256
            or _json_rpc_id_key(message.get("id")) is None
        ):
            raise ValueError("O4 measurement-start compact token is invalid")
        self._origin = _CAPTURE_EVENT_ORIGIN
        self._capture = capture
        self._source_carrier_id = source_carrier_id
        self._request_ordinal = request_ordinal
        self._request_record_sha256 = request_record_sha256
        self._request_id = message["id"]
        self._request_id_key = _json_rpc_id_key(message["id"])


class _PendingMeasurementFinalization:
    def __init__(
        self,
        measurement_document: dict[str, Any],
        attestation_binding: dict[str, Any],
        private_raw_root: Path,
        isolate_root: Path,
        private_key_root: Path,
        root_identities: tuple[tuple[int, int], tuple[int, int], tuple[int, int]],
        tree_identities: tuple[
            tuple[tuple[str, str, int, int, int, str | None], ...],
            tuple[tuple[str, str, int, int, int, str | None], ...],
            tuple[tuple[str, str, int, int, int, str | None], ...],
        ],
        root_locks: tuple[
            _LockedPrivateResourceRoot,
            _LockedPrivateResourceRoot,
            _LockedPrivateResourceRoot,
        ],
    ) -> None:
        self._origin = _LIVE_CAPTURE_ORIGIN
        self._measurement_document = deepcopy(measurement_document)
        self._attestation_binding = deepcopy(dict(attestation_binding))
        self._private_raw_root = private_raw_root.resolve(strict=True)
        self._isolate_root = isolate_root.resolve(strict=True)
        self._private_key_root = private_key_root.resolve(strict=True)
        roots = (
            self._private_raw_root,
            self._isolate_root,
            self._private_key_root,
        )
        if len(set(roots)) != len(roots) or any(
            left.is_relative_to(right) or right.is_relative_to(left)
            for index, left in enumerate(roots)
            for right in roots[index + 1 :]
        ):
            raise ValueError("O4 private resource roots overlap")
        if (
            not isinstance(root_locks, tuple)
            or len(root_locks) != 3
            or any(
                not isinstance(lock, _LockedPrivateResourceRoot)
                or lock.path != path
                or lock.disposed
                for lock, path in zip(root_locks, roots)
            )
            or tuple(lock.identity for lock in root_locks) != root_identities
            or tuple(_private_resource_tree_identity(path) for path in roots)
            != tree_identities
        ):
            raise ValueError("O4 private resource identity drifted before finalization")
        for lock in root_locks:
            lock.verify()
        self._root_identities = root_identities
        self._tree_identities = tree_identities
        self._root_locks = root_locks
        self._consumed = False


def _trusted_windows_curl_executable() -> Path | None:
    if os.name != "nt" or not hasattr(ctypes, "WinDLL"):
        return None
    try:
        kernel32 = ctypes.WinDLL("Kernel32.dll", use_last_error=True)
        get_system_directory = kernel32.GetSystemDirectoryW
        get_system_directory.argtypes = [ctypes.c_wchar_p, ctypes.c_uint32]
        get_system_directory.restype = ctypes.c_uint32
        buffer = ctypes.create_unicode_buffer(32_768)
        length = get_system_directory(buffer, len(buffer))
        if length == 0 or length >= len(buffer):
            raise OSError("system directory unavailable")
        system_directory = Path(buffer.value).resolve(strict=True)
        executable = (system_directory / "curl.exe").resolve(strict=True)
        metadata = executable.lstat()
        if (
            executable.parent != system_directory
            or executable.name.casefold() != "curl.exe"
            or not stat.S_ISREG(metadata.st_mode)
            or _is_reparse_or_symlink(executable)
        ):
            raise OSError("untrusted Windows curl surface")
    except (OSError, RuntimeError, ValueError):
        return None
    return executable


def _trusted_curl_environment(curl: Path) -> dict[str, str]:
    system_directory = curl.parent
    system_root = system_directory.parent
    environment = {
        "SystemRoot": str(system_root),
        "WINDIR": str(system_root),
        "ComSpec": str(system_directory / "cmd.exe"),
        "PATH": str(system_directory),
        "PATHEXT": ".COM;.EXE;.BAT;.CMD",
    }
    for key, value in os.environ.items():
        if key.upper() in ALLOWED_NETWORK_ENVIRONMENT_KEYS:
            environment[key.upper()] = value
    return environment


def _trusted_ssh_keygen_executable() -> Path | None:
    try:
        if os.name == "nt":
            buffer = ctypes.create_unicode_buffer(32_768)
            length = ctypes.windll.kernel32.GetSystemDirectoryW(buffer, len(buffer))
            if length <= 0 or length >= len(buffer):
                return None
            system_directory = Path(buffer.value).resolve(strict=True)
            candidate = (system_directory / "OpenSSH" / "ssh-keygen.exe").resolve(
                strict=True
            )
            trusted_parent = (system_directory / "OpenSSH").resolve(strict=True)
            trusted = candidate.parent == trusted_parent
        else:
            executable = shutil.which("ssh-keygen")
            if executable is None:
                return None
            candidate = Path(executable).resolve(strict=True)
            trusted_roots = (
                Path("/usr/bin"),
                Path("/usr/local/bin"),
                Path("/opt/homebrew/bin"),
                Path("/opt/local/bin"),
            )
            trusted = candidate.parent in trusted_roots
        metadata = candidate.lstat()
        if (
            not trusted
            or candidate.name.casefold() not in {"ssh-keygen", "ssh-keygen.exe"}
            or not stat.S_ISREG(metadata.st_mode)
            or _is_reparse_or_symlink(candidate)
        ):
            return None
    except (OSError, RuntimeError, ValueError):
        return None
    return candidate


def _trusted_ssh_environment(
    executable: Path, private_temp_root: Path | None = None
) -> dict[str, str]:
    environment = {"PATH": str(executable.parent)}
    if os.name == "nt":
        system_directory = executable.parents[1]
        system_root = system_directory.parent
        environment.update(
            {
                "SystemRoot": str(system_root),
                "WINDIR": str(system_root),
                "ComSpec": str(system_directory / "cmd.exe"),
                "PATHEXT": ".COM;.EXE;.BAT;.CMD",
                "ProgramData": str(Path(system_root.drive + "\\") / "ProgramData"),
            }
        )
    else:
        environment.update({"HOME": os.devnull, "LANG": "C", "LC_ALL": "C"})
    if private_temp_root is not None:
        root = private_temp_root.resolve(strict=True)
        environment.update(
            {
                "TEMP": str(root),
                "TMP": str(root),
                "HOME": str(root),
                "USERPROFILE": str(root),
            }
        )
    return environment

REQUIRED_APP_SERVER_CONTRACT = {
    "freshThreadMethod": "thread/start",
    "freshThreadEvidence": [
        "thread-response-forkedFromId-null",
        "thread-response-turns-empty",
        "thread-started-notification",
    ],
    "goalMethods": [
        "thread/goal/set",
        "thread/goal/get",
        "thread/goal/clear",
    ],
    "compactionMethod": "thread/compact/start",
    "compactionLifecycle": [
        "item/started-contextCompaction",
        "item/completed-same-contextCompaction-id",
    ],
    "tokenUsageNotification": "thread/tokenUsage/updated",
    "effectiveContextWindowField": "tokenUsage.modelContextWindow",
    "currentContextUsageField": "tokenUsage.last.totalTokens",
    "userInterventionChronologyMethod": "thread/read",
    "userInterventionChronologyFields": [
        "includeTurns",
        "userMessage.id",
        "userMessage.content.text",
    ],
    "archiveMethod": "thread/archive",
    "resumeIdleLifecycleDependency": "none",
}

SOURCE_BINDING_FIELDS = {
    "repository",
    "releaseVersion",
    "tag",
    "tagObject",
    "peeledCommit",
    "npmPackage",
    "npmPackageVersion",
    "npmPackageIntegrity",
    "npmTarball",
    "nativePackageAlias",
    "nativePackageName",
    "nativePackageVersion",
    "nativePackageIntegrity",
    "nativePackageTarball",
    "platform",
    "license",
    "nativeExecutableSha256",
    "nativeExecutableBytes",
    "nativeAuthenticodeStatus",
    "nativeAuthenticodeSigner",
    "nativeAuthenticodeCertificateSha256",
    "nativeArchiveExecutableSha256",
    "nativeArchiveExecutableBytes",
    "sourceBlobSha256s",
    "protocolPath",
    "appServerPath",
    "goalProtocolPath",
    "notificationProtocolPath",
    "threadDataPath",
    "goalProcessorPath",
    "requiredAppServerContract",
}

SNAPSHOT_RECORD_FIELDS = {
    "schema",
    "captureKind",
    "publicIdentity",
    "state",
    "sourceReleaseVersion",
    "sourceExecutableSha256",
    "sourceExecutableBytes",
    "snapshotExecutableSha256",
    "snapshotExecutableBytes",
    "sourceAndSnapshotByteIdentity",
    "snapshotVersionOutput",
    "authenticodeStatus",
    "authenticodeSigner",
    "authenticodeCertificateSha256",
    "selectionRule",
    "materializationRule",
    "executionRule",
    "ambientDriftRule",
    "cleanupRule",
    "privateCleanupHostRule",
    "publicProjectionRule",
}

SNAPSHOT_POLICY = {
    "selectionRule": "resolve-current-suitable-official-codex-at-task-materialization",
    "materializationRule": (
        "copy-exact-source-native-executable-into-authorized-isolated-resource-"
        "before-environment-manifest-and-registration"
    ),
    "executionRule": (
        "after-registration-launch-only-the-private-task-scoped-snapshot-and-"
        "fail-closed-on-missing-version-signature-size-or-digest-drift"
    ),
    "ambientDriftRule": (
        "ambient-installation-after-snapshot-is-not-an-execution-dependency"
    ),
    "cleanupRule": (
        "delete-snapshot-with-exact-isolate-on-o4-accepted-stopped-or-"
        "deterministic-failure"
    ),
    "privateCleanupHostRule": (
        "preflight-exact-volume-root-handle-ntfs-fileid64-before-private-materialization-"
        "and-fail-closed-on-foreign-hardlinks-or-open-handles"
    ),
    "publicProjectionRule": (
        "publish-only-random-public-identity-official-source-identity-version-"
        "signature-size-and-digests-never-private-path"
    ),
}

CARRIER_GOAL_BINDING = {
    "locator": v1.CARRIER_GOAL_LOCATOR,
    "sha256": v1.CARRIER_GOAL_SHA256,
    "nativeStateSource": "codex-thread-goal-get-exact-task-scoped-native-snapshot",
    "requiredStatus": "active",
}

FAULT_SCENARIOS = v2.FAULT_SCENARIOS
SCENARIO_IDENTITIES = tuple(item.scenario_identity for item in FAULT_SCENARIOS) + (
    v1.CARRIER_SCENARIO_IDENTITIES
)
FAILURE_BINDINGS = deepcopy(v2.FAILURE_BINDINGS)
CORRECTION_BINDINGS = deepcopy(v2.CORRECTION_BINDINGS)
TRANSITION_AND_CLEANUP_BOUNDARY = {
    **deepcopy(v1.TRANSITION_AND_CLEANUP_BOUNDARY),
    "clientEffectiveContextWindowRule": (
        "bind-the-effective-window-and-current-usage-exposed-by-the-exact-"
        "client-app-server-never-substitute-the-provider-api-model-maximum"
    ),
    "taskScopedContextCalibrationBands": {
        "efficientBelowPercent": 60,
        "transitionReadyAtPercent": 60,
        "immediateTransitionAtPercent": 80,
        "authority": (
            "maintainer-observed-codex-calibration-hypothesis-requires-exact-"
            "task-evidence-not-portable-or-universal"
        ),
    },
    "compactionSummaryProxyRule": (
        "treat-native-compaction-count-and-latency-as-opaque-summary-load-"
        "proxies-never-parse-or-invent-summary-token-share"
    ),
    "turnCountFallbackRule": (
        "use-only-an-exact-source-bound-current-host-recommendation-when-one-"
        "exists-otherwise-record-unknown-never-hard-code-a-global-turn-count"
    ),
    "userInitiatedHandoffFailureRule": (
        "if-the-user-must-request-context-load-relief-before-the-agent-"
        "triggers-the-bound-transition-the-autonomy-scenario-fails"
    ),
    "nativeExecutionSnapshotRule": SNAPSHOT_POLICY["executionRule"],
    "ambientInstallationDriftRule": SNAPSHOT_POLICY["ambientDriftRule"],
    "nativeExecutionSnapshotCleanupRule": SNAPSHOT_POLICY["cleanupRule"],
    "privateRawSourceRetentionRule": (
        "retain-exact-private-raw-events-only-through-code-replay-signing-and-"
        "named-human-o4-judgment-under-separate-authorization-never-publish"
    ),
    "privateRawSourceCleanupRule": (
        "delete-with-attestation-key-on-accepted-claim-revocation-stop-expiry-or-"
        "deterministic-failure-while-public-signature-remains-replayable"
    ),
    "isolatedCodexHomeCleanupRule": (
        "delete-the-exact-marker-bound-codex-home-after-thread-archive-and-"
        "snapshot-cleanup-on-accepted-stopped-or-deterministic-failure"
    ),
    "terminalCleanupAttestationRule": (
        "sign-private-raw-and-isolate-absence-before-key-self-cleanup-then-"
        "require-all-three-public-safe-cleanup-records-before-evidence"
    ),
}


def _integrity_is_sha512(value: Any) -> bool:
    if not isinstance(value, str) or not value.startswith("sha512-"):
        return False
    try:
        decoded = base64.b64decode(value[7:], validate=True)
    except (ValueError, TypeError):
        return False
    return len(decoded) == 64


def _bounded_official_https_get(url: str, maximum_bytes: int) -> bytes:
    parsed = urllib.parse.urlsplit(url)
    if (
        parsed.scheme != "https"
        or parsed.hostname not in OFFICIAL_HTTPS_HOSTS
        or parsed.username is not None
        or parsed.password is not None
        or parsed.port not in {None, 443}
        or parsed.fragment
        or maximum_bytes <= 0
        or maximum_bytes > MAX_OFFICIAL_SOURCE_BYTES
    ):
        raise ValueError("official HTTPS source boundary is invalid")
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json, text/plain;q=0.9, */*;q=0.1",
            "User-Agent": "agent-autonomy-harness-v1.2-o4-source-probe",
        },
        method="GET",
    )
    curl = _trusted_windows_curl_executable()
    if curl is not None:
        try:
            completed = subprocess.run(
                [
                    str(curl),
                    "--disable",
                    "--fail",
                    "--silent",
                    "--show-error",
                    "--max-time",
                    "30",
                    "--retry",
                    "2",
                    "--retry-all-errors",
                    "--proto",
                    "=https",
                    "--max-filesize",
                    str(maximum_bytes),
                    url,
                ],
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=100,
                env=_trusted_curl_environment(curl),
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise ValueError("official HTTPS source is unavailable") from exc
        if (
            completed.returncode != 0
            or len(completed.stdout) > maximum_bytes
            or len(completed.stderr) > 4_096
        ):
            raise ValueError("official HTTPS source is unavailable")
        return completed.stdout
    last_error: Exception | None = None
    raw: bytes | None = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                final = urllib.parse.urlsplit(response.geturl())
                content_length = response.headers.get("Content-Length")
                if (
                    getattr(response, "status", None) != 200
                    or final.scheme != "https"
                    or final.hostname not in OFFICIAL_HTTPS_HOSTS
                    or final.username is not None
                    or final.password is not None
                    or final.port not in {None, 443}
                    or (
                        content_length is not None
                        and int(content_length) > maximum_bytes
                    )
                ):
                    raise ValueError("official HTTPS response boundary is invalid")
                raw = response.read(maximum_bytes + 1)
            break
        except (
            OSError,
            TimeoutError,
            urllib.error.URLError,
            ValueError,
        ) as exc:
            last_error = exc
            if attempt < 2:
                time.sleep(0.25 * (attempt + 1))
    if raw is None:
        raise ValueError("official HTTPS source is unavailable") from last_error
    if len(raw) > maximum_bytes:
        raise ValueError("official HTTPS source exceeds byte limit")
    return raw


def _official_json(url: str) -> dict[str, Any]:
    raw = _bounded_official_https_get(url, MAX_OFFICIAL_METADATA_BYTES)
    try:
        return v1._strict_json_object(raw)
    except (json.JSONDecodeError, RecursionError, TypeError, UnicodeError, ValueError):
        raise ValueError("official registry metadata is invalid") from None


def _trusted_git_executable() -> Path | None:
    executable = shutil.which("git")
    if executable is None:
        return None
    try:
        candidate = Path(executable).resolve(strict=True)
        metadata = candidate.lstat()
    except (OSError, RuntimeError, ValueError):
        return None
    if (
        candidate.name.casefold() not in {"git", "git.exe"}
        or not stat.S_ISREG(metadata.st_mode)
        or _is_reparse_or_symlink(candidate)
    ):
        return None
    if os.name == "nt":
        system_directory = ctypes.create_unicode_buffer(32_768)
        system_length = ctypes.windll.kernel32.GetSystemDirectoryW(
            system_directory, len(system_directory)
        )
        system_drive = (
            Path(system_directory.value).drive.casefold()
            if 0 < system_length < len(system_directory)
            else ""
        )
        folded = tuple(part.casefold() for part in candidate.parts)
        trusted = (
            bool(candidate.drive)
            and not candidate.drive.startswith("\\\\")
            and candidate.drive.casefold() == system_drive
            and len(folded) >= 4
            and folded[1:3]
            in {("program files", "git"), ("program files (x86)", "git")}
        )
    else:
        trusted_roots = (
            Path("/usr/bin"),
            Path("/usr/local/bin"),
            Path("/usr/local/Cellar"),
            Path("/opt/homebrew"),
            Path("/opt/local/bin"),
        )
        trusted = any(root == candidate or root in candidate.parents for root in trusted_roots)
    return candidate if trusted else None


def _trusted_git_environment(git: Path) -> dict[str, str]:
    environment = {
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_TERMINAL_PROMPT": "0",
        "PATH": str(git.parent),
    }
    if os.name == "nt":
        system_directory = ctypes.create_unicode_buffer(32_768)
        system_length = ctypes.windll.kernel32.GetSystemDirectoryW(
            system_directory, len(system_directory)
        )
        if system_length <= 0 or system_length >= len(system_directory):
            raise ValueError("trusted Git environment is unavailable")
        system_root = Path(system_directory.value).parent
        environment.update(
            {
                "SystemRoot": str(system_root),
                "WINDIR": str(system_root),
                "ComSpec": str(Path(system_directory.value) / "cmd.exe"),
                "PATHEXT": ".COM;.EXE;.BAT;.CMD",
            }
        )
    else:
        environment.update(
            {
                "HOME": os.devnull,
                "LANG": "C",
                "LC_ALL": "C",
            }
        )
    for key, value in os.environ.items():
        if key.upper() in ALLOWED_NETWORK_ENVIRONMENT_KEYS:
            environment[key.upper()] = value
    return environment


def _official_tag_identity(version: str) -> tuple[str, str]:
    git = _trusted_git_executable()
    if git is None:
        raise ValueError("trusted Git source probe is unavailable")
    tag_ref = f"refs/tags/rust-v{version}"
    peeled_ref = tag_ref + "^{}"
    environment = _trusted_git_environment(git)
    completed: subprocess.CompletedProcess[bytes] | None = None
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            candidate = subprocess.run(
                [
                    str(git),
                    "ls-remote",
                    "--tags",
                    "https://github.com/openai/codex.git",
                    tag_ref,
                    peeled_ref,
                ],
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=30,
                env=environment,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            last_error = exc
        else:
            completed = candidate
            if candidate.returncode == 0 and not candidate.stderr:
                break
        if attempt < 2:
            time.sleep(0.25 * (attempt + 1))
    if completed is None:
        raise ValueError("official Git tag source is unavailable") from last_error
    if (
        completed.returncode != 0
        or len(completed.stdout) > 512
        or bool(completed.stderr)
    ):
        raise ValueError("official Git tag source is invalid")
    lines = completed.stdout.decode("ascii").splitlines()
    expected_refs = {tag_ref, peeled_ref}
    parsed: dict[str, str] = {}
    for line in lines:
        fields = line.split("\t")
        if (
            len(fields) != 2
            or GIT_OBJECT_PATTERN.fullmatch(fields[0]) is None
            or fields[1] not in expected_refs
            or fields[1] in parsed
        ):
            raise ValueError("official Git tag response is invalid")
        parsed[fields[1]] = fields[0]
    if set(parsed) != expected_refs or parsed[tag_ref] == parsed[peeled_ref]:
        raise ValueError("official Git tag response is incomplete")
    return parsed[tag_ref], parsed[peeled_ref]


def _official_source_network_observation(
    version: str, *, require_current_latest: bool = True
) -> dict[str, Any]:
    if SEMVER_PATTERN.fullmatch(version) is None:
        raise ValueError("official Codex version is invalid")
    package = urllib.parse.quote("@openai/codex", safe="")
    latest = (
        _official_json(f"https://registry.npmjs.org/{package}/latest")
        if require_current_latest
        else None
    )
    exact = _official_json(f"https://registry.npmjs.org/{package}/{version}")
    native_version = f"{version}-win32-x64"
    native = _official_json(
        f"https://registry.npmjs.org/{package}/{native_version}"
    )
    tag_object, peeled_commit = _official_tag_identity(version)
    exact_dist = exact.get("dist")
    native_dist = native.get("dist")
    optional = exact.get("optionalDependencies")
    if (
        (require_current_latest and latest is not None and latest.get("version") != version)
        or exact.get("name") != "@openai/codex"
        or exact.get("version") != version
        or exact.get("license") != "Apache-2.0"
        or not isinstance(exact_dist, dict)
        or not isinstance(native_dist, dict)
        or not isinstance(optional, dict)
        or optional.get("@openai/codex-win32-x64")
        != f"npm:@openai/codex@{native_version}"
        or native.get("name") != "@openai/codex"
        or native.get("version") != native_version
        or native.get("license") != "Apache-2.0"
    ):
        raise ValueError("official npm release relationship is invalid")
    source_blobs: dict[str, str] = {}
    source_blob_bytes: dict[str, bytes] = {}
    app_server_readme: bytes | None = None
    for path in SOURCE_BLOB_PATHS:
        encoded_path = urllib.parse.quote(path, safe="/")
        raw = _bounded_official_https_get(
            "https://raw.githubusercontent.com/openai/codex/"
            f"{peeled_commit}/{encoded_path}",
            MAX_OFFICIAL_SOURCE_BYTES,
        )
        if not raw:
            raise ValueError("official Codex source blob is empty")
        source_blobs[path] = hashlib.sha256(raw).hexdigest()
        source_blob_bytes[path] = raw
        if path == "codex-rs/app-server/README.md":
            app_server_readme = raw
    if app_server_readme is None or any(
        token not in app_server_readme for token in APP_SERVER_SOURCE_TOKENS
    ):
        raise ValueError("required App Server contract is absent at official source")
    goal_processor_path = (
        "codex-rs/app-server/src/request_processors/thread_goal_processor.rs"
    )
    goal_protocol = source_blob_bytes[
        "codex-rs/app-server-protocol/src/protocol/v2/thread.rs"
    ]
    notification_protocol = source_blob_bytes[
        "codex-rs/app-server-protocol/src/protocol/common.rs"
    ]
    thread_data_protocol = source_blob_bytes[
        "codex-rs/app-server-protocol/src/protocol/v2/thread_data.rs"
    ]
    goal_processor = source_blob_bytes[goal_processor_path]
    if (
        b"pub struct ThreadTokenUsageUpdatedNotification" not in goal_protocol
        or b"pub model_context_window: Option<i64>" not in goal_protocol
        or b"pub last: TokenUsageBreakdown" not in goal_protocol
        or b'"thread/tokenUsage/updated"' not in notification_protocol
        or b"pub struct ThreadReadParams" not in goal_protocol
        or b"pub include_turns: bool" not in goal_protocol
        or b"pub turns: Vec<Turn>" not in thread_data_protocol
        or b"emit_resume_goal_snapshot(" not in goal_processor
        or b"emit_resume_goal_snapshot_and_continue(" in goal_processor
    ):
        raise ValueError("App Server goal-resume dependency is incompatible")
    return {
        "tagObject": tag_object,
        "peeledCommit": peeled_commit,
        "npmPackageIntegrity": exact_dist.get("integrity"),
        "npmTarball": exact_dist.get("tarball"),
        "nativePackageIntegrity": native_dist.get("integrity"),
        "nativePackageTarball": native_dist.get("tarball"),
        "sourceBlobSha256s": source_blobs,
    }


def _default_official_source_probe(source_binding: dict[str, Any]) -> bool:
    if not official_source_binding_valid(source_binding):
        return False
    try:
        observed = _official_source_network_observation(
            source_binding["releaseVersion"]
        )
    except ValueError:
        return False
    return all(source_binding.get(key) == value for key, value in observed.items())


def _verify_native_package_archive_executable(
    source_binding: dict[str, Any],
    isolate_root: Path,
) -> tuple[str, int]:
    """Verify npm SRI and hash the exact native member without extracting it."""

    root = isolate_root.resolve(strict=True)
    if not root.is_dir() or _is_reparse_or_symlink(root):
        raise ValueError("native package verification root is invalid")
    url = source_binding.get("nativePackageTarball")
    parsed = urllib.parse.urlsplit(url) if isinstance(url, str) else None
    if (
        parsed is None
        or parsed.scheme != "https"
        or parsed.hostname != "registry.npmjs.org"
        or parsed.username is not None
        or parsed.password is not None
        or parsed.port not in {None, 443}
    ):
        raise ValueError("native package tarball source is invalid")
    try:
        expected_archive_sha512 = base64.b64decode(
            source_binding["nativePackageIntegrity"][7:], validate=True
        )
    except (KeyError, TypeError, ValueError):
        raise ValueError("native package SRI is invalid") from None
    harness_parent = root / ".harness"
    harness_parent_preexisting = harness_parent.exists()
    download_parent = harness_parent / "o4-v3-source"
    archive = download_parent / "native-package.tgz"
    if download_parent.exists() or archive.exists():
        raise ValueError("native package verification residue already exists")
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/octet-stream",
            "User-Agent": "agent-autonomy-harness-v1.2-o4-source-probe",
        },
        method="GET",
    )
    try:
        download_parent.mkdir(parents=True, exist_ok=False)
        archive_sha512 = hashlib.sha512()
        archive_bytes = 0
        curl = _trusted_windows_curl_executable()
        if curl is not None:
            try:
                completed = subprocess.run(
                    [
                        str(curl),
                        "--disable",
                        "--fail",
                        "--silent",
                        "--show-error",
                        "--max-time",
                        "180",
                        "--retry",
                        "2",
                        "--retry-all-errors",
                        "--proto",
                        "=https",
                        "--max-filesize",
                        str(MAX_NATIVE_PACKAGE_ARCHIVE_BYTES),
                        "--output",
                        str(archive),
                        url,
                    ],
                    check=False,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=560,
                    env=_trusted_curl_environment(curl),
                )
            except (OSError, subprocess.SubprocessError) as exc:
                raise ValueError("native package archive is unavailable") from exc
            if (
                completed.returncode != 0
                or completed.stdout
                or len(completed.stderr) > 8_192
                or not archive.is_file()
                or _is_reparse_or_symlink(archive)
            ):
                raise ValueError("native package archive is unavailable")
        else:
            try:
                with urllib.request.urlopen(request, timeout=60) as response, archive.open(
                    "xb"
                ) as stream:
                    final = urllib.parse.urlsplit(response.geturl())
                    if (
                        getattr(response, "status", None) != 200
                        or final.scheme != "https"
                        or final.hostname != "registry.npmjs.org"
                        or final.username is not None
                        or final.password is not None
                        or final.port not in {None, 443}
                    ):
                        raise ValueError("native package response boundary is invalid")
                    while True:
                        chunk = response.read(1_048_576)
                        if not chunk:
                            break
                        archive_bytes += len(chunk)
                        if archive_bytes > MAX_NATIVE_PACKAGE_ARCHIVE_BYTES:
                            raise ValueError("native package archive exceeds byte limit")
                        archive_sha512.update(chunk)
                        stream.write(chunk)
            except (OSError, TimeoutError, urllib.error.URLError) as exc:
                raise ValueError("native package archive is unavailable") from exc
        if curl is not None:
            with archive.open("rb") as stream:
                while True:
                    chunk = stream.read(1_048_576)
                    if not chunk:
                        break
                    archive_bytes += len(chunk)
                    if archive_bytes > MAX_NATIVE_PACKAGE_ARCHIVE_BYTES:
                        raise ValueError("native package archive exceeds byte limit")
                    archive_sha512.update(chunk)
        if archive_bytes <= 0 or archive_sha512.digest() != expected_archive_sha512:
            raise ValueError("native package archive SRI does not match")
        executable_sha256: Any | None = None
        executable_bytes = 0
        executable_member_size = 0
        member_count = 0
        expanded_bytes = 0
        with tarfile.open(archive, mode="r|gz") as package:
            for member in package:
                member_count += 1
                if member_count > 64 or member.size < 0:
                    raise ValueError("native package archive exceeds entry limits")
                expanded_bytes += member.size
                if expanded_bytes > MAX_NATIVE_PACKAGE_EXPANDED_BYTES:
                    raise ValueError("native package archive exceeds expanded byte limit")
                normalized = member.name.replace("\\", "/")
                if not (
                    member.isfile()
                    and normalized.endswith(
                        "/vendor/x86_64-pc-windows-msvc/bin/codex.exe"
                    )
                    and ".." not in Path(normalized).parts
                ):
                    continue
                if executable_sha256 is not None:
                    raise ValueError("native package executable member is duplicated")
                if member.size <= 0 or member.size > MAX_NATIVE_EXECUTABLE_BYTES:
                    raise ValueError("native package executable member size is invalid")
                incoming = package.extractfile(member)
                if incoming is None:
                    raise ValueError("native package executable member is unavailable")
                executable_sha256 = hashlib.sha256()
                executable_member_size = member.size
                with incoming:
                    while True:
                        chunk = incoming.read(1_048_576)
                        if not chunk:
                            break
                        executable_bytes += len(chunk)
                        if executable_bytes > MAX_NATIVE_EXECUTABLE_BYTES:
                            raise ValueError("native package executable exceeds byte limit")
                        executable_sha256.update(chunk)
        if executable_sha256 is None:
            raise ValueError("native package executable member is absent")
        digest = executable_sha256.hexdigest()
        if executable_bytes != executable_member_size:
            raise ValueError("native package executable member is truncated")
    finally:
        if archive.exists():
            if _is_reparse_or_symlink(archive) or not archive.is_file():
                raise RuntimeError("native package archive cleanup became unsafe")
            archive.unlink()
        if download_parent.exists():
            if _is_reparse_or_symlink(download_parent):
                raise RuntimeError("native package archive parent became unsafe")
            download_parent.rmdir()
        if not harness_parent_preexisting and harness_parent.exists():
            try:
                harness_parent.rmdir()
            except OSError:
                pass
    return digest, executable_bytes


def resolve_current_official_source_binding(
    source_executable: Path,
    isolate_root: Path,
    *,
    version_probe: VersionProbe | None = None,
    signature_probe: SignatureProbe | None = None,
) -> dict[str, Any]:
    """Resolve one current official release at task time without a global pin."""

    source = source_executable.resolve(strict=True)
    root = isolate_root.resolve(strict=True)
    selected_version_probe = _default_version_probe if version_probe is None else version_probe
    version_output = selected_version_probe(source, root)
    match = re.fullmatch(r"codex-cli ([0-9]+\.[0-9]+\.[0-9]+)", version_output)
    if match is None:
        raise ValueError("current Codex version output is invalid")
    version = match.group(1)
    observed = _official_source_network_observation(version)
    executable_sha256, executable_bytes = _sha256_regular_file(source)
    selected_signature_probe = (
        _default_signature_probe if signature_probe is None else signature_probe
    )
    status, signer, certificate_sha256 = selected_signature_probe(source)
    provisional = {
        "repository": "https://github.com/openai/codex",
        "releaseVersion": version,
        "tag": f"rust-v{version}",
        "tagObject": observed["tagObject"],
        "peeledCommit": observed["peeledCommit"],
        "npmPackage": "@openai/codex",
        "npmPackageVersion": version,
        "npmPackageIntegrity": observed["npmPackageIntegrity"],
        "npmTarball": observed["npmTarball"],
        "nativePackageAlias": "@openai/codex-win32-x64",
        "nativePackageName": "@openai/codex",
        "nativePackageVersion": f"{version}-win32-x64",
        "nativePackageIntegrity": observed["nativePackageIntegrity"],
        "nativePackageTarball": observed["nativePackageTarball"],
        "platform": "win32-x64",
        "license": "Apache-2.0",
        "nativeExecutableSha256": executable_sha256,
        "nativeExecutableBytes": executable_bytes,
        "nativeAuthenticodeStatus": status,
        "nativeAuthenticodeSigner": signer,
        "nativeAuthenticodeCertificateSha256": certificate_sha256,
        "nativeArchiveExecutableSha256": executable_sha256,
        "nativeArchiveExecutableBytes": executable_bytes,
        "sourceBlobSha256s": observed["sourceBlobSha256s"],
        "protocolPath": SOURCE_BLOB_PATHS[0],
        "appServerPath": SOURCE_BLOB_PATHS[1],
        "goalProtocolPath": SOURCE_BLOB_PATHS[2],
        "notificationProtocolPath": SOURCE_BLOB_PATHS[3],
        "threadDataPath": SOURCE_BLOB_PATHS[4],
        "goalProcessorPath": SOURCE_BLOB_PATHS[5],
        "requiredAppServerContract": REQUIRED_APP_SERVER_CONTRACT,
    }
    archive_sha256, archive_bytes = _verify_native_package_archive_executable(
        provisional, root
    )
    if archive_sha256 != executable_sha256 or archive_bytes != executable_bytes:
        raise ValueError("installed native executable differs from official npm archive")
    binding = provisional
    if not official_source_binding_valid(binding):
        raise ValueError("current official Codex source binding is invalid")
    return binding


def official_source_binding_valid(value: Any) -> bool:
    """Validate one exact official source identity without making it global."""

    if not isinstance(value, dict) or set(value) != SOURCE_BINDING_FIELDS:
        return False
    version = value.get("releaseVersion")
    native_version = f"{version}-win32-x64" if isinstance(version, str) else None
    source_blob_sha256s = value.get("sourceBlobSha256s")
    return (
        isinstance(version, str)
        and SEMVER_PATTERN.fullmatch(version) is not None
        and value.get("repository") == "https://github.com/openai/codex"
        and value.get("tag") == f"rust-v{version}"
        and isinstance(value.get("tagObject"), str)
        and GIT_OBJECT_PATTERN.fullmatch(value["tagObject"]) is not None
        and isinstance(value.get("peeledCommit"), str)
        and GIT_OBJECT_PATTERN.fullmatch(value["peeledCommit"]) is not None
        and value["tagObject"] != value["peeledCommit"]
        and value.get("npmPackage") == "@openai/codex"
        and value.get("npmPackageVersion") == version
        and _integrity_is_sha512(value.get("npmPackageIntegrity"))
        and value.get("npmTarball")
        == f"https://registry.npmjs.org/@openai/codex/-/codex-{version}.tgz"
        and value.get("nativePackageAlias") == "@openai/codex-win32-x64"
        and value.get("nativePackageName") == "@openai/codex"
        and value.get("nativePackageVersion") == native_version
        and _integrity_is_sha512(value.get("nativePackageIntegrity"))
        and value.get("nativePackageTarball")
        == (
            "https://registry.npmjs.org/@openai/codex/-/"
            f"codex-{native_version}.tgz"
        )
        and value.get("platform") == "win32-x64"
        and value.get("license") == "Apache-2.0"
        and isinstance(value.get("nativeExecutableSha256"), str)
        and SHA256_PATTERN.fullmatch(value["nativeExecutableSha256"]) is not None
        and type(value.get("nativeExecutableBytes")) is int
        and 0 < value["nativeExecutableBytes"] <= MAX_NATIVE_EXECUTABLE_BYTES
        and value.get("nativeAuthenticodeStatus") == "Valid"
        and isinstance(value.get("nativeAuthenticodeSigner"), str)
        and all(
            component in value["nativeAuthenticodeSigner"]
            for component in OPENAI_SIGNER_COMPONENTS
        )
        and isinstance(value.get("nativeAuthenticodeCertificateSha256"), str)
        and SHA256_PATTERN.fullmatch(value["nativeAuthenticodeCertificateSha256"])
        is not None
        and value.get("nativeArchiveExecutableSha256")
        == value.get("nativeExecutableSha256")
        and value.get("nativeArchiveExecutableBytes")
        == value.get("nativeExecutableBytes")
        and isinstance(source_blob_sha256s, dict)
        and set(source_blob_sha256s) == set(SOURCE_BLOB_PATHS)
        and all(
            isinstance(digest, str) and SHA256_PATTERN.fullmatch(digest) is not None
            for digest in source_blob_sha256s.values()
        )
        and value.get("protocolPath") == "codex-rs/protocol/src/protocol.rs"
        and value.get("appServerPath") == "codex-rs/app-server/README.md"
        and value.get("goalProtocolPath")
        == "codex-rs/app-server-protocol/src/protocol/v2/thread.rs"
        and value.get("notificationProtocolPath")
        == "codex-rs/app-server-protocol/src/protocol/common.rs"
        and value.get("threadDataPath")
        == "codex-rs/app-server-protocol/src/protocol/v2/thread_data.rs"
        and value.get("goalProcessorPath")
        == "codex-rs/app-server/src/request_processors/thread_goal_processor.rs"
        and value.get("requiredAppServerContract") == REQUIRED_APP_SERVER_CONTRACT
    )


def snapshot_record_valid(value: Any, source_binding: Any) -> bool:
    if (
        not official_source_binding_valid(source_binding)
        or not isinstance(value, dict)
        or set(value) != SNAPSHOT_RECORD_FIELDS
    ):
        return False
    public_identity = value.get("publicIdentity")
    return (
        type(value.get("schema")) is int
        and value.get("schema") == 1
        and value.get("captureKind") == "o4-task-scoped-native-execution-snapshot"
        and isinstance(public_identity, str)
        and SNAPSHOT_PUBLIC_ID_PATTERN.fullmatch(public_identity) is not None
        and value.get("state") == "materialized-before-manifest-and-registration"
        and value.get("sourceReleaseVersion") == source_binding["releaseVersion"]
        and value.get("sourceExecutableSha256")
        == source_binding["nativeExecutableSha256"]
        and value.get("snapshotExecutableSha256")
        == source_binding["nativeExecutableSha256"]
        and type(value.get("sourceExecutableBytes")) is int
        and value.get("sourceExecutableBytes")
        == source_binding["nativeExecutableBytes"]
        and type(value.get("snapshotExecutableBytes")) is int
        and value.get("snapshotExecutableBytes")
        == source_binding["nativeExecutableBytes"]
        and value.get("sourceAndSnapshotByteIdentity") == "equal"
        and value.get("snapshotVersionOutput")
        == f"codex-cli {source_binding['releaseVersion']}"
        and value.get("authenticodeStatus")
        == source_binding["nativeAuthenticodeStatus"]
        and value.get("authenticodeSigner")
        == source_binding["nativeAuthenticodeSigner"]
        and value.get("authenticodeCertificateSha256")
        == source_binding["nativeAuthenticodeCertificateSha256"]
        and all(value.get(key) == expected for key, expected in SNAPSHOT_POLICY.items())
        and not v1._contains_private_value(value)
    )


def _snapshot_registration_binding(snapshot: dict[str, Any]) -> dict[str, Any]:
    return {
        "publicIdentity": snapshot["publicIdentity"],
        "releaseVersion": snapshot["sourceReleaseVersion"],
        "sha256": snapshot["snapshotExecutableSha256"],
        "bytes": snapshot["snapshotExecutableBytes"],
        "materializedBefore": "environment-manifest-and-registration",
        "executionSource": "exact-private-task-scoped-snapshot-only",
        "ambientInstallationAfterSnapshot": "not-an-execution-dependency",
        "privatePathPublished": False,
        "snapshotCleanup": "delete-executable-at-suite-terminal",
        "privateSourceRetention": (
            "retain-exact-raw-source-only-through-code-replay-signing-and-"
            "named-human-o4-judgment-under-separate-authorization"
        ),
        "privateSourceCleanup": (
            "delete-with-attestation-key-on-accepted-claim-revocation-stop-expiry-"
            "or-deterministic-failure-with-public-signature-replay-preserved"
        ),
        "isolatedCodexHomeCleanup": (
            "delete-exact-marker-bound-root-after-thread-archive-and-snapshot-"
            "cleanup-before-public-evidence"
        ),
    }


def counterexample_sources(source_binding: dict[str, Any]) -> list[dict[str, Any]]:
    sources = deepcopy(v2.COUNTEREXAMPLE_SOURCES[:4])
    sources.extend(
        [
            {
                "scenarioIdentity": v1.CARRIER_SCENARIO_IDENTITIES[0],
                "scenarioClass": "native-compaction-recovery",
                "evidenceClass": "controlled-codex-app-server-host-event-projection",
                "sourceBinding": deepcopy(source_binding),
            },
            {
                "scenarioIdentity": v1.CARRIER_SCENARIO_IDENTITIES[1],
                "scenarioClass": "proactive-same-goal-conversation-transition",
                "evidenceClass": "controlled-codex-app-server-host-event-projection",
                "sourceBinding": {
                    **deepcopy(source_binding),
                    "historicalCounterexampleIdentity": (
                        "source-carrier-autoresume-with-active-goal-after-verified-"
                        "destination-v1"
                    ),
                    "historicalCounterexampleRole": (
                        "private-source-control-regression-input-not-outcome-evidence"
                    ),
                },
            },
        ]
    )
    return sources


def _git_blob(root: Path, revision: Any, locator: Any) -> bytes | None:
    if (
        not isinstance(revision, str)
        or GIT_OBJECT_PATTERN.fullmatch(revision) is None
        or not isinstance(locator, str)
        or re.fullmatch(
            r"product/evidence/environment-manifests/[a-z0-9][a-z0-9._-]{0,127}\.json",
            locator,
        )
        is None
    ):
        return None
    git = _trusted_git_executable()
    if git is None:
        return None
    try:
        completed = subprocess.run(
            [str(git), "show", f"{revision}:{locator}"],
            cwd=root.resolve(strict=True),
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
            env=_trusted_git_environment(git),
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if (
        completed.returncode != 0
        or len(completed.stdout) > 1_048_576
        or len(completed.stderr) > 16_384
    ):
        return None
    return completed.stdout


def _git_revision_is_strict_ancestor(
    root: Path, ancestor: Any, descendant: Any
) -> bool:
    if (
        not isinstance(ancestor, str)
        or not isinstance(descendant, str)
        or ancestor == descendant
        or GIT_OBJECT_PATTERN.fullmatch(ancestor) is None
        or GIT_OBJECT_PATTERN.fullmatch(descendant) is None
    ):
        return False
    git = _trusted_git_executable()
    if git is None:
        return False
    try:
        completed = subprocess.run(
            [str(git), "merge-base", "--is-ancestor", ancestor, descendant],
            cwd=root.resolve(strict=True),
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
            env=_trusted_git_environment(git),
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return (
        completed.returncode == 0
        and not completed.stdout
        and len(completed.stderr) <= 16_384
    )


def _manifest_runtime_bindings(
    root: Path,
    environment_binding: Any,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]] | None:
    if not isinstance(environment_binding, dict):
        return None
    locator = environment_binding.get("manifestLocator")
    revision = environment_binding.get("manifestRevision")
    expected_sha256 = environment_binding.get("manifestSha256")
    raw = _git_blob(root, revision, locator)
    if (
        raw is None
        or not isinstance(expected_sha256, str)
        or SHA256_PATTERN.fullmatch(expected_sha256) is None
        or hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest()
        != expected_sha256
    ):
        return None
    try:
        manifest = v1._strict_json_object(raw)
    except (json.JSONDecodeError, RecursionError, TypeError, UnicodeError, ValueError):
        return None
    capture = manifest.get("capture-time-source-identities-fingerprint-and-drift-check")
    host = manifest.get("host-client-and-version")
    if not isinstance(capture, dict) or not isinstance(host, dict):
        return None
    source_binding = capture.get("codexSourceBinding")
    snapshot = capture.get("taskScopedNativeExecutionSnapshot")
    attestation_binding = capture.get("taskScopedCaptureAttestation")
    if (
        not official_source_binding_valid(source_binding)
        or not snapshot_record_valid(snapshot, source_binding)
        or not _attestation_public_key_valid(attestation_binding)
        or host.get("codexCli") != source_binding["releaseVersion"]
        or host.get("codexNativeBinarySha256")
        != source_binding["nativeExecutableSha256"]
        or host.get("codexTaskScopedSnapshotSha256")
        != snapshot["snapshotExecutableSha256"]
        or host.get("codexTaskScopedSnapshotPublicIdentity")
        != snapshot["publicIdentity"]
    ):
        return None
    return (
        deepcopy(source_binding),
        deepcopy(snapshot),
        deepcopy(attestation_binding),
    )


def _user_chronology_baseline_valid(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and set(value)
        == {
            "schema",
            "source",
            "sourceCarrierIdentitySha256",
            "userMessageCount",
            "userMessageIdentitySha256",
            "userMessageContentIdentitySha256",
            "controlledGoalMessageSha256",
            "threadReadResponseRecordSha256",
        }
        and value.get("schema") == 1
        and value.get("source")
        == "source-bound-pre-registration-user-chronology-v1"
        and type(value.get("userMessageCount")) is int
        and value["userMessageCount"] == 1
        and value.get("controlledGoalMessageSha256") == CARRIER_GOAL_BINDING["sha256"]
        and all(
            isinstance(value.get(field), str)
            and SHA256_PATTERN.fullmatch(value[field]) is not None
            for field in (
                "userMessageIdentitySha256",
                "userMessageContentIdentitySha256",
                "sourceCarrierIdentitySha256",
                "threadReadResponseRecordSha256",
            )
        )
        and not v1._contains_private_value(value)
    )


def _source_preparation_payload(
    environment_binding: dict[str, Any],
    source_binding: dict[str, Any],
    snapshot: dict[str, Any],
    attestation_binding: dict[str, Any],
    user_chronology_baseline: dict[str, Any],
) -> dict[str, Any]:
    preparation_revision = (
        environment_binding.get("manifestRevision")
        if isinstance(environment_binding, dict)
        else None
    )
    if (
        not isinstance(preparation_revision, str)
        or GIT_OBJECT_PATTERN.fullmatch(preparation_revision) is None
        or not isinstance(environment_binding, dict)
        or not official_source_binding_valid(source_binding)
        or not snapshot_record_valid(snapshot, source_binding)
        or not _attestation_public_key_valid(attestation_binding)
        or not _user_chronology_baseline_valid(user_chronology_baseline)
    ):
        raise ValueError("O4 source-preparation attestation input is invalid")
    return {
        "schema": 1,
        "kind": "o4-v3-source-preparation-before-measurement",
        "sourcePreparationRevision": preparation_revision,
        "environmentBindingSha256": v1._canonical_sha256(environment_binding),
        "officialSourceBinding": deepcopy(source_binding),
        "nativeSnapshotBinding": _snapshot_registration_binding(snapshot),
        "attestationPublicIdentity": attestation_binding["publicIdentity"],
        "attestationPublicKeyFingerprint": attestation_binding[
            "publicKeyFingerprint"
        ],
        "sourceUserChronologyBaseline": deepcopy(user_chronology_baseline),
        "chronologyRule": (
            "source-snapshot-and-public-key-materialized-before-registration-"
            "and-before-any-outcome-measurement"
        ),
    }


def seal_source_preparation_attestation(
    root: Path,
    isolate_root: Path,
    private_key_root: Path,
    environment_binding: dict[str, Any],
    source_binding: dict[str, Any],
    snapshot: dict[str, Any],
    attestation_binding: dict[str, Any],
    user_chronology_baseline: _SourceUserChronologyBaseline,
) -> dict[str, Any]:
    """Recheck the prepared source/snapshot and sign its public preregistration state."""

    if (
        not isinstance(user_chronology_baseline, _SourceUserChronologyBaseline)
        or user_chronology_baseline._origin is not _CAPTURE_EVENT_ORIGIN
        or user_chronology_baseline._source_binding != source_binding
        or user_chronology_baseline._snapshot != snapshot
        or user_chronology_baseline._isolate_root
        != isolate_root.resolve(strict=True)
        or user_chronology_baseline._suite.snapshot != snapshot
        or user_chronology_baseline._suite.isolate_root
        != isolate_root.resolve(strict=True)
        or user_chronology_baseline._capture.suite
        is not user_chronology_baseline._suite
        or user_chronology_baseline._capture.poisoned
        or user_chronology_baseline._consumed
        or len(user_chronology_baseline._capture.events)
        != user_chronology_baseline._event_count
        or not user_chronology_baseline._capture.events
        or user_chronology_baseline._capture.events[-1][0] != "response-read"
        or v1._canonical_sha256(
            user_chronology_baseline._capture.events[-1][1]
        )
        != user_chronology_baseline._response_record_sha256
        or user_chronology_baseline.get("threadReadResponseRecordSha256")
        not in {
            v1._canonical_sha256(record)
            for kind, record in user_chronology_baseline._capture.events
            if kind == "response-read"
        }
    ):
        raise ValueError("O4 pre-registration user chronology token is required")
    user_chronology_baseline._consumed = True
    manifest_bindings = _manifest_runtime_bindings(root, environment_binding)
    if manifest_bindings != (source_binding, snapshot, attestation_binding):
        raise ValueError("O4 committed environment manifest binding drifted")
    verified_task_scoped_snapshot_executable(
        isolate_root, source_binding, snapshot
    )
    if _default_official_source_probe(source_binding) is not True:
        raise ValueError("O4 official source replay failed before registration")
    return _sign_task_attestation(
        private_key_root,
        attestation_binding,
        _source_preparation_payload(
            environment_binding,
            source_binding,
            snapshot,
            attestation_binding,
            dict(user_chronology_baseline),
        ),
    )


def _starting_state_valid(
    value: Any,
    source_binding: dict[str, Any],
    snapshot: dict[str, Any],
    attestation_binding: dict[str, Any],
) -> bool:
    return value == {
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
        "controlledGoalArtifact": CARRIER_GOAL_BINDING,
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
        "officialCodexSource": source_binding,
        "taskScopedNativeExecution": _snapshot_registration_binding(snapshot),
        "taskScopedCaptureAttestation": attestation_binding,
    }


def _scenario_validator_binding_valid(
    value: Any,
    source_binding: dict[str, Any],
    snapshot: dict[str, Any],
    attestation_binding: dict[str, Any],
    source_preparation_attestation: dict[str, Any],
    user_chronology_baseline: dict[str, Any],
) -> bool:
    return value == {
        "suiteIdentity": SUITE_IDENTITY,
        "scenarioIdentities": list(SCENARIO_IDENTITIES),
        "validatorIdentity": VALIDATOR_KIND,
        "validatorLocator": VALIDATOR_LOCATOR,
        "hostProjectionBuilder": (
            f"{VALIDATOR_LOCATOR}:project_raw_carrier_observations"
        ),
        "captureSuiteBuilder": (
            f"{VALIDATOR_LOCATOR}:begin_task_scoped_capture_suite"
        ),
        "preRegistrationCaptureSuiteBuilder": (
            f"{VALIDATOR_LOCATOR}:begin_pre_registration_capture_suite"
        ),
        "sourceUserChronologyBaselineBuilder": (
            f"{VALIDATOR_LOCATOR}:capture_source_user_chronology_baseline"
        ),
        "snapshotLaunchBuilder": (
            f"{VALIDATOR_LOCATOR}:launch_task_scoped_snapshot_app_server"
        ),
        "snapshotRequestWriter": (
            f"{VALIDATOR_LOCATOR}:write_snapshot_app_server_message"
        ),
        "snapshotResponseReader": (
            f"{VALIDATOR_LOCATOR}:read_snapshot_app_server_message"
        ),
        "repositoryCheckpointRecorder": (
            f"{VALIDATOR_LOCATOR}:capture_repository_checkpoint"
        ),
        "carrierFitnessRecorder": (
            f"{VALIDATOR_LOCATOR}:capture_unknown_capacity_transition_signal"
        ),
        "sourceReleaseRecorder": (
            f"{VALIDATOR_LOCATOR}:capture_source_carrier_release_preflight"
        ),
        "sourcePreparationBuilder": (
            f"{VALIDATOR_LOCATOR}:seal_source_preparation_attestation"
        ),
        "privateMeasurementBuilder": (
            f"{VALIDATOR_LOCATOR}:persist_and_attest_private_measurement"
        ),
        "liveScenarioBuilder": (
            f"{VALIDATOR_LOCATOR}:finalize_live_app_server_scenario"
        ),
        "snapshotCleanupBuilder": (
            f"{VALIDATOR_LOCATOR}:cleanup_task_scoped_native_snapshot"
        ),
        "publicObservationBuilder": (
            f"{VALIDATOR_LOCATOR}:finalize_public_measurement_observation"
        ),
        "codexSourceBinding": source_binding,
        "taskScopedNativeSnapshot": _snapshot_registration_binding(snapshot),
        "taskScopedCaptureAttestation": attestation_binding,
        "sourcePreparationAttestation": source_preparation_attestation,
        "sourceUserChronologyBaseline": user_chronology_baseline,
        "controlledGoalArtifact": CARRIER_GOAL_BINDING,
        "receiptOnlyAccepted": False,
    }


def validate_registration(
    registration: dict[str, Any],
    increment: dict[str, Any],
    mapped_outcomes: tuple[str, ...],
    root: Path,
    errors: list[str],
) -> bool:
    """Validate the distinct third-generation suite before measurement."""

    before = len(errors)
    values = registration.get("preRegistrationValues")
    registration_binding = increment.get("taskRegistration")
    source_revision = (
        registration_binding.get("sourceRevision")
        if isinstance(registration_binding, dict)
        else None
    )
    if (
        increment.get("id") != INCREMENT_ID
        or registration.get("incrementId") != INCREMENT_ID
        or not isinstance(registration_binding, dict)
        or registration_binding.get("locator") != REGISTRATION_LOCATOR
        or mapped_outcomes != ("O4",)
        or registration.get("criterionIds") != ["O4"]
        or not isinstance(values, dict)
        or set(values) != v1.EXPECTED_PRE_REGISTRATION_FIELDS
    ):
        v1._error(errors, "O4 third-generation registration identity is invalid")
        return False
    runtime_bindings = _manifest_runtime_bindings(
        root, values.get("environmentAttributionBinding")
    )
    if runtime_bindings is None:
        v1._error(errors, "O4 third-generation native snapshot manifest is invalid")
        return False
    source_binding, snapshot, attestation_binding = runtime_bindings
    environment_binding = values.get("environmentAttributionBinding")
    manifest_revision = (
        environment_binding.get("manifestRevision")
        if isinstance(environment_binding, dict)
        else None
    )
    if not _git_revision_is_strict_ancestor(
        root, manifest_revision, source_revision
    ):
        v1._error(
            errors,
            "O4 third-generation source preparation must precede registration",
        )
    scenario_validator = values.get("scenarioValidator")
    source_preparation_attestation = (
        scenario_validator.get("sourcePreparationAttestation")
        if isinstance(scenario_validator, dict)
        else None
    )
    user_chronology_baseline = (
        scenario_validator.get("sourceUserChronologyBaseline")
        if isinstance(scenario_validator, dict)
        else None
    )
    try:
        preparation_payload = _source_preparation_payload(
            environment_binding,
            source_binding,
            snapshot,
            attestation_binding,
            user_chronology_baseline,
        )
    except (TypeError, ValueError):
        preparation_payload = {}
    if not verify_task_attestation(
        attestation_binding,
        preparation_payload,
        source_preparation_attestation,
    ):
        v1._error(
            errors,
            "O4 third-generation source preparation attestation is not verifiable",
        )
    if values.get("counterexampleIdentityAndSource") != counterexample_sources(
        source_binding
    ):
        v1._error(errors, "O4 third-generation suite must bind all six sources exactly once")
    if not v1._goal_artifact_committed(root, source_revision):
        v1._error(errors, "O4 controlled carrier goal artifact is not committed exactly")
    if not _starting_state_valid(
        values.get("startingAuthorityGoalAndCarrierState"),
        source_binding,
        snapshot,
        attestation_binding,
    ):
        v1._error(errors, "O4 third-generation starting state is invalid")
    if values.get("injectedOrObservedFailure") != FAILURE_BINDINGS:
        v1._error(errors, "O4 third-generation failure bindings are invalid")
    if values.get("expectedDetectionAndCorrection") != CORRECTION_BINDINGS:
        v1._error(errors, "O4 third-generation correction bindings are invalid")
    if values.get("transitionAndCleanupBoundary") != TRANSITION_AND_CLEANUP_BOUNDARY:
        v1._error(errors, "O4 third-generation cleanup boundary is invalid")
    if not _scenario_validator_binding_valid(
        scenario_validator,
        source_binding,
        snapshot,
        attestation_binding,
        source_preparation_attestation,
        user_chronology_baseline,
    ):
        v1._error(errors, "O4 third-generation validator binding is invalid")
    validator = registration.get("preMeasurementValidator")
    if not isinstance(validator, dict) or (
        validator.get("kind") != VALIDATOR_KIND
        or validator.get("version") != 1
        or validator.get("locator") != VALIDATOR_LOCATOR
    ):
        v1._error(errors, "O4 third-generation pre-measurement validator is invalid")
    return len(errors) == before


def _is_reparse_or_symlink(path: Path) -> bool:
    try:
        info = path.lstat()
    except OSError:
        return True
    attributes = getattr(info, "st_file_attributes", 0)
    reparse = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return path.is_symlink() or bool(attributes & reparse)


def _directory_object_identity(path: Path) -> tuple[int, int]:
    resolved = path.resolve(strict=True)
    metadata = resolved.lstat()
    if (
        not stat.S_ISDIR(metadata.st_mode)
        or _is_reparse_or_symlink(resolved)
        or type(metadata.st_dev) is not int
        or type(metadata.st_ino) is not int
        or metadata.st_ino <= 0
    ):
        raise ValueError("O4 private resource directory identity is invalid")
    return metadata.st_dev, metadata.st_ino


def _opened_windows_path(handle: int) -> Path:
    kernel32 = ctypes.WinDLL("Kernel32.dll", use_last_error=True)
    get_final_path = kernel32.GetFinalPathNameByHandleW
    get_final_path.argtypes = [
        ctypes.c_void_p,
        ctypes.c_wchar_p,
        ctypes.c_uint32,
        ctypes.c_uint32,
    ]
    get_final_path.restype = ctypes.c_uint32
    buffer = ctypes.create_unicode_buffer(32_768)
    length = get_final_path(ctypes.c_void_p(handle), buffer, len(buffer), 0)
    if length == 0 or length >= len(buffer):
        raise OSError("private resource final path is unavailable")
    value = buffer.value
    if value.startswith("\\\\?\\UNC\\"):
        value = "\\\\" + value[8:]
    elif value.startswith("\\\\?\\"):
        value = value[4:]
    return Path(value).resolve(strict=True)


class _LockedPrivateResourceRoot:
    """Hold a Windows directory without delete sharing until exact cleanup."""

    def __init__(self, path: Path) -> None:
        self.path = path.resolve(strict=True)
        self.identity = _directory_object_identity(self.path)
        self._handle: int | None = None
        self.disposed = False
        self.quarantined = False
        if os.name != "nt" or not hasattr(ctypes, "WinDLL"):
            return
        kernel32 = ctypes.WinDLL("Kernel32.dll", use_last_error=True)
        create_file = kernel32.CreateFileW
        create_file.argtypes = [
            ctypes.c_wchar_p,
            ctypes.c_uint32,
            ctypes.c_uint32,
            ctypes.c_void_p,
            ctypes.c_uint32,
            ctypes.c_uint32,
            ctypes.c_void_p,
        ]
        create_file.restype = ctypes.c_void_p
        handle = create_file(
            str(self.path),
            0x80000000 | 0x00010000,
            0x00000001 | 0x00000002,
            None,
            3,
            0x02000000 | 0x00200000,
            None,
        )
        invalid_handle = ctypes.c_void_p(-1).value
        if not handle or handle == invalid_handle:
            raise OSError("private resource directory lock is unavailable")
        self._handle = int(handle)
        try:
            self.verify()
        except Exception:
            self.release()
            raise

    def verify(self) -> None:
        if _directory_object_identity(self.path) != self.identity:
            raise RuntimeError("O4 locked private resource identity drifted")
        if self._handle is not None and _opened_windows_path(self._handle) != self.path:
            raise RuntimeError("O4 locked private resource path drifted")

    def release(self) -> None:
        if self._handle is None:
            return
        handle = self._handle
        self._handle = None
        kernel32 = ctypes.WinDLL("Kernel32.dll", use_last_error=True)
        close_handle = kernel32.CloseHandle
        close_handle.argtypes = [ctypes.c_void_p]
        close_handle.restype = ctypes.c_bool
        if not close_handle(ctypes.c_void_p(handle)):
            raise OSError("private resource directory lock could not be released")

    def quarantine(self) -> None:
        """Move the exact locked root to an unpredictable private cleanup namespace."""

        if self.quarantined:
            self.verify()
            return
        if self._handle is None:
            raise RuntimeError("private resource root quarantine is unavailable")

        class _RenameInfo(ctypes.Structure):
            _fields_ = [
                ("Flags", ctypes.c_uint32),
                ("RootDirectory", ctypes.c_void_p),
                ("FileNameLength", ctypes.c_uint32),
                ("FileName", ctypes.c_wchar * 32_768),
            ]

        destination = self.path.with_name(
            ".aah-o4-v3-dispose-" + secrets.token_hex(24)
        )
        if destination.exists():
            raise RuntimeError("private resource quarantine namespace collided")
        encoded_length = len(str(destination).encode("utf-16-le"))
        if encoded_length <= 0 or encoded_length > 65_534:
            raise ValueError("private resource quarantine path is invalid")
        information = _RenameInfo()
        information.Flags = 0x00000002
        information.RootDirectory = None
        information.FileNameLength = encoded_length
        information.FileName = str(destination)
        kernel32 = ctypes.WinDLL("Kernel32.dll", use_last_error=True)
        set_information = kernel32.SetFileInformationByHandle
        set_information.argtypes = [
            ctypes.c_void_p,
            ctypes.c_int,
            ctypes.c_void_p,
            ctypes.c_uint32,
        ]
        set_information.restype = ctypes.c_bool
        header_bytes = _RenameInfo.FileName.offset
        if not set_information(
            ctypes.c_void_p(self._handle),
            22,
            ctypes.byref(information),
            header_bytes + encoded_length,
        ):
            raise OSError("private resource root could not enter cleanup quarantine")
        self.path = destination.resolve(strict=True)
        self.quarantined = True
        self.verify()

    def dispose_empty(self) -> None:
        if self._handle is None or self.disposed:
            raise RuntimeError("private resource root disposition is invalid")
        self.verify()
        if any(self.path.iterdir()):
            raise RuntimeError("private resource root is not empty")
        handle = self._handle
        _mark_windows_handle_for_deletion(handle)
        self.disposed = True
        self.release()
        if self.path.exists():
            try:
                if _directory_object_identity(self.path) == self.identity:
                    raise RuntimeError("private resource root remained after disposition")
            except (OSError, ValueError):
                pass
            raise RuntimeError("private resource namespace was replaced during cleanup")


def _mark_windows_handle_for_deletion(handle: int) -> None:
    if os.name != "nt" or not hasattr(ctypes, "WinDLL") or handle <= 0:
        raise ValueError("Windows handle disposition is unavailable")

    class _DispositionEx(ctypes.Structure):
        _fields_ = [("Flags", ctypes.c_uint32)]

    class _Disposition(ctypes.Structure):
        _fields_ = [("DeleteFile", ctypes.c_ubyte)]

    kernel32 = ctypes.WinDLL("Kernel32.dll", use_last_error=True)
    set_information = kernel32.SetFileInformationByHandle
    set_information.argtypes = [
        ctypes.c_void_p,
        ctypes.c_int,
        ctypes.c_void_p,
        ctypes.c_uint32,
    ]
    set_information.restype = ctypes.c_bool
    extended = _DispositionEx(0x00000001 | 0x00000002 | 0x00000010)
    if set_information(
        ctypes.c_void_p(handle),
        21,
        ctypes.byref(extended),
        ctypes.sizeof(extended),
    ):
        return
    legacy = _Disposition(1)
    if not set_information(
        ctypes.c_void_p(handle),
        4,
        ctypes.byref(legacy),
        ctypes.sizeof(legacy),
    ):
        raise OSError(
            ctypes.get_last_error(),
            "private resource object could not be marked for deletion",
        )


def _sha256_windows_handle(handle: int) -> tuple[str, int]:
    if os.name != "nt" or not hasattr(ctypes, "WinDLL") or handle <= 0:
        raise ValueError("Windows file-handle hashing is unavailable")
    kernel32 = ctypes.WinDLL("Kernel32.dll", use_last_error=True)
    set_pointer = kernel32.SetFilePointerEx
    set_pointer.argtypes = [
        ctypes.c_void_p,
        ctypes.c_longlong,
        ctypes.POINTER(ctypes.c_longlong),
        ctypes.c_uint32,
    ]
    set_pointer.restype = ctypes.c_bool
    read_file = kernel32.ReadFile
    read_file.argtypes = [
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.POINTER(ctypes.c_uint32),
        ctypes.c_void_p,
    ]
    read_file.restype = ctypes.c_bool
    if not set_pointer(ctypes.c_void_p(handle), 0, None, 0):
        raise OSError("private resource file cursor could not be reset")
    digest = hashlib.sha256()
    size = 0
    buffer = ctypes.create_string_buffer(1_048_576)
    while True:
        received = ctypes.c_uint32(0)
        if not read_file(
            ctypes.c_void_p(handle),
            buffer,
            len(buffer),
            ctypes.byref(received),
            None,
        ):
            raise OSError("private resource file could not be read by handle")
        if received.value == 0:
            break
        size += received.value
        if size > MAX_ISOLATE_CLEANUP_BYTES:
            raise ValueError("private resource file exceeds its byte boundary")
        digest.update(buffer.raw[: received.value])
    return digest.hexdigest(), size


class _LockedPrivateResourceNode:
    def __init__(self, path: Path, expected_kind: str) -> None:
        if os.name != "nt" or not hasattr(ctypes, "WinDLL"):
            raise ValueError("Windows private node locking is unavailable")
        self.path = path.resolve(strict=True)
        metadata = self.path.lstat()
        is_directory = stat.S_ISDIR(metadata.st_mode)
        if (
            expected_kind not in {"file", "directory"}
            or is_directory != (expected_kind == "directory")
            or (not is_directory and not stat.S_ISREG(metadata.st_mode))
            or (not is_directory and metadata.st_nlink != 1)
            or _is_reparse_or_symlink(self.path)
        ):
            raise ValueError("private resource node type is invalid")
        self.kind = expected_kind
        self.identity = (metadata.st_dev, metadata.st_ino)
        kernel32 = ctypes.WinDLL("Kernel32.dll", use_last_error=True)
        create_file = kernel32.CreateFileW
        create_file.argtypes = [
            ctypes.c_wchar_p,
            ctypes.c_uint32,
            ctypes.c_uint32,
            ctypes.c_void_p,
            ctypes.c_uint32,
            ctypes.c_uint32,
            ctypes.c_void_p,
        ]
        create_file.restype = ctypes.c_void_p
        flags = 0x00200000 | (0x02000000 if is_directory else 0)
        handle = create_file(
            str(self.path),
            0x80000000 | 0x00010000,
            0,
            None,
            3,
            flags,
            None,
        )
        invalid_handle = ctypes.c_void_p(-1).value
        if not handle or handle == invalid_handle:
            raise OSError("private resource node lock is unavailable")
        self._handle: int | None = int(handle)
        try:
            if _opened_windows_path(self._handle) != self.path:
                raise RuntimeError("private resource node path drifted")
        except Exception:
            self.release()
            raise

    def verify(
        self,
        expected: tuple[str, str, int, int, int, str | None],
        *,
        require_empty_directory: bool = False,
    ) -> None:
        if self._handle is None:
            raise RuntimeError("private resource node lock is closed")
        relative, kind, device, inode, size, digest = expected
        del relative
        metadata = self.path.lstat()
        if (
            kind != self.kind
            or (metadata.st_dev, metadata.st_ino) != (device, inode)
            or (kind == "file" and metadata.st_nlink != 1)
        ):
            raise RuntimeError("private resource node identity drifted")
        if kind == "file":
            assert self._handle is not None
            observed_digest, observed_size = _sha256_windows_handle(self._handle)
            if (observed_size, observed_digest) != (size, digest):
                raise RuntimeError("private resource file bytes drifted")
        elif require_empty_directory and any(self.path.iterdir()):
            raise RuntimeError("private resource directory is not empty")

    def dispose(
        self,
        expected: tuple[str, str, int, int, int, str | None],
    ) -> None:
        self.verify(expected, require_empty_directory=True)
        assert self._handle is not None
        _mark_windows_handle_for_deletion(self._handle)
        identity = self.identity
        path = self.path
        self.release()
        if path.exists():
            metadata = path.lstat()
            if (metadata.st_dev, metadata.st_ino) == identity:
                raise RuntimeError("private resource node remained after disposition")
            raise RuntimeError("private resource node namespace was replaced")

    def release(self) -> None:
        if self._handle is None:
            return
        handle = self._handle
        self._handle = None
        kernel32 = ctypes.WinDLL("Kernel32.dll", use_last_error=True)
        close_handle = kernel32.CloseHandle
        close_handle.argtypes = [ctypes.c_void_p]
        close_handle.restype = ctypes.c_bool
        if not close_handle(ctypes.c_void_p(handle)):
            raise OSError("private resource node lock could not be released")


def _locked_private_node_by_file_id(
    root_lock: _LockedPrivateResourceRoot,
    expected: tuple[str, str, int, int, int, str | None],
) -> _LockedPrivateResourceNode:
    """Recover the exact NTFS object if a pathname was renamed during acquisition."""

    if os.name != "nt" or not hasattr(ctypes, "WinDLL"):
        raise ValueError("Windows file-id recovery is unavailable")
    relative, kind, device, inode, _size, _digest = expected
    del relative
    if root_lock._handle is None or device != root_lock.identity[0]:
        raise RuntimeError("private resource file-id volume binding is invalid")
    kernel32 = ctypes.WinDLL("Kernel32.dll", use_last_error=True)
    volume = root_lock._handle
    invalid_handle = ctypes.c_void_p(-1).value

    class _FileIdUnion(ctypes.Union):
        _fields_ = [("FileId", ctypes.c_longlong), ("ExtendedFileId", ctypes.c_ubyte * 16)]

    class _FileIdDescriptor(ctypes.Structure):
        _anonymous_ = ("Identifier",)
        _fields_ = [
            ("dwSize", ctypes.c_uint32),
            ("Type", ctypes.c_int),
            ("Identifier", _FileIdUnion),
        ]

    close_handle = kernel32.CloseHandle
    close_handle.argtypes = [ctypes.c_void_p]
    close_handle.restype = ctypes.c_bool
    try:
        descriptor = _FileIdDescriptor()
        descriptor.dwSize = ctypes.sizeof(_FileIdDescriptor)
        descriptor.Type = 0
        descriptor.FileId = ctypes.c_longlong(
            inode if inode < (1 << 63) else inode - (1 << 64)
        ).value
        open_by_id = kernel32.OpenFileById
        open_by_id.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(_FileIdDescriptor),
            ctypes.c_uint32,
            ctypes.c_uint32,
            ctypes.c_void_p,
            ctypes.c_uint32,
        ]
        open_by_id.restype = ctypes.c_void_p
        last_error: Exception | None = None
        for _attempt in range(16):
            handle = open_by_id(
                ctypes.c_void_p(volume),
                ctypes.byref(descriptor),
                0,
                0x00000001 | 0x00000002 | 0x00000004,
                None,
                0x02000000 if kind == "directory" else 0,
            )
            if not handle or handle == invalid_handle:
                raise OSError("private resource file-id recovery failed")
            locator_handle = int(handle)
            node: _LockedPrivateResourceNode | None = None
            try:
                recovered_path = _opened_windows_path(locator_handle)
                if kind == "file" and recovered_path.lstat().st_nlink != 1:
                    raise ValueError(
                        "private resource file-id object has an external hard link"
                    )
                node = _LockedPrivateResourceNode(recovered_path, kind)
                node.verify(expected)
                return node
            except (OSError, RuntimeError, ValueError) as exc:
                last_error = exc
                if node is not None:
                    node.release()
                if "external hard link" in str(exc):
                    raise
            finally:
                close_handle(ctypes.c_void_p(locator_handle))
        raise RuntimeError(
            "private resource file-id recovery was continuously raced"
        ) from last_error
    finally:
        root_lock.verify()


def _dispose_locked_private_tree(
    lock: _LockedPrivateResourceRoot,
    expected_tree: tuple[tuple[str, str, int, int, int, str | None], ...],
) -> None:
    lock.quarantine()
    lock.verify()
    nodes: dict[str, _LockedPrivateResourceNode] = {}
    try:
        for item in expected_tree:
            candidate = lock.path.joinpath(*item[0].split("/"))
            try:
                node = _LockedPrivateResourceNode(candidate, item[1])
                try:
                    node.verify(item)
                except Exception:
                    node.release()
                    raise
            except Exception:
                node = _locked_private_node_by_file_id(lock, item)
            nodes[item[0]] = node
    except Exception:
        for node in nodes.values():
            node.release()
        raise
    ordered = sorted(
        expected_tree,
        key=lambda item: (item[0].count("/"), item[1] == "directory"),
        reverse=True,
    )
    try:
        for item in ordered:
            nodes[item[0]].dispose(item)
    finally:
        for node in nodes.values():
            node.release()
    if any(lock.path.iterdir()):
        raise RuntimeError("private resource root gained unexpected residue")
    lock.dispose_empty()


class _LockedSnapshotExecutable:
    """Keep the verified snapshot pathname bound to one immutable file object."""

    def __init__(self, path: Path) -> None:
        if os.name != "nt" or not hasattr(ctypes, "WinDLL"):
            raise ValueError("Windows snapshot image locking is unavailable")
        self.path = path.resolve(strict=True)
        metadata = self.path.lstat()
        if (
            not stat.S_ISREG(metadata.st_mode)
            or _is_reparse_or_symlink(self.path)
            or type(metadata.st_dev) is not int
            or type(metadata.st_ino) is not int
            or metadata.st_ino <= 0
        ):
            raise ValueError("snapshot image object identity is invalid")
        self.identity = (metadata.st_dev, metadata.st_ino)
        self.digest_and_size = _sha256_regular_file(self.path)
        kernel32 = ctypes.WinDLL("Kernel32.dll", use_last_error=True)
        create_file = kernel32.CreateFileW
        create_file.argtypes = [
            ctypes.c_wchar_p,
            ctypes.c_uint32,
            ctypes.c_uint32,
            ctypes.c_void_p,
            ctypes.c_uint32,
            ctypes.c_uint32,
            ctypes.c_void_p,
        ]
        create_file.restype = ctypes.c_void_p
        handle = create_file(
            str(self.path),
            0x80000000,
            0x00000001,
            None,
            3,
            0x00200000,
            None,
        )
        invalid_handle = ctypes.c_void_p(-1).value
        if not handle or handle == invalid_handle:
            raise OSError("snapshot image object lock is unavailable")
        self._handle: int | None = int(handle)
        try:
            self.verify()
        except Exception:
            self.release()
            raise

    def verify(self) -> None:
        if self._handle is None:
            raise RuntimeError("snapshot image object lock is closed")
        metadata = self.path.lstat()
        if (
            (metadata.st_dev, metadata.st_ino) != self.identity
            or _opened_windows_path(self._handle) != self.path
            or _sha256_regular_file(self.path) != self.digest_and_size
        ):
            raise RuntimeError("snapshot image object identity drifted")

    def release(self) -> None:
        if self._handle is None:
            return
        handle = self._handle
        self._handle = None
        kernel32 = ctypes.WinDLL("Kernel32.dll", use_last_error=True)
        close_handle = kernel32.CloseHandle
        close_handle.argtypes = [ctypes.c_void_p]
        close_handle.restype = ctypes.c_bool
        if not close_handle(ctypes.c_void_p(handle)):
            raise OSError("snapshot image object lock could not be released")


def _private_resource_tree_identity(
    root: Path,
) -> tuple[tuple[str, str, int, int, int, str | None], ...]:
    resolved_root = root.resolve(strict=True)
    if _directory_object_identity(resolved_root) != (
        resolved_root.stat().st_dev,
        resolved_root.stat().st_ino,
    ):
        raise ValueError("O4 private resource root identity is unstable")
    entries: list[tuple[str, str, int, int, int, str | None]] = []
    nodes = 0
    total_bytes = 0
    for current, directories, files in os.walk(
        resolved_root,
        topdown=True,
        followlinks=False,
    ):
        directories.sort()
        files.sort()
        current_path = Path(current)
        if _is_reparse_or_symlink(current_path):
            raise ValueError("O4 private resource tree contains a reparse directory")
        for name in [*directories, *files]:
            candidate = current_path / name
            nodes += 1
            if nodes > MAX_ISOLATE_CLEANUP_NODES or _is_reparse_or_symlink(candidate):
                raise ValueError("O4 private resource tree exceeds its node boundary")
            metadata = candidate.lstat()
            relative = candidate.relative_to(resolved_root).as_posix()
            if stat.S_ISDIR(metadata.st_mode):
                entries.append(
                    (
                        relative,
                        "directory",
                        metadata.st_dev,
                        metadata.st_ino,
                        0,
                        None,
                    )
                )
            elif stat.S_ISREG(metadata.st_mode):
                if metadata.st_nlink != 1:
                    raise ValueError(
                        "O4 private resource file has an external hard link"
                    )
                digest, size = _sha256_regular_file(candidate)
                total_bytes += size
                if total_bytes > MAX_ISOLATE_CLEANUP_BYTES:
                    raise ValueError("O4 private resource tree exceeds its byte boundary")
                entries.append(
                    (
                        relative,
                        "file",
                        metadata.st_dev,
                        metadata.st_ino,
                        size,
                        digest,
                    )
                )
            else:
                raise ValueError("O4 private resource tree contains a special file")
    return tuple(entries)


def _windows_private_cleanup_capability(path: Path) -> bool:
    if os.name != "nt" or not hasattr(ctypes, "WinDLL"):
        return False
    try:
        resolved = path.resolve(strict=True)
        metadata = resolved.lstat()
    except (OSError, RuntimeError):
        return False
    if (
        not resolved.drive
        or not stat.S_ISDIR(metadata.st_mode)
        or metadata.st_ino <= 0
        or metadata.st_ino >= (1 << 64)
    ):
        return False
    kernel32 = ctypes.WinDLL("Kernel32.dll", use_last_error=True)
    get_volume_path = kernel32.GetVolumePathNameW
    get_volume_path.argtypes = [
        ctypes.c_wchar_p,
        ctypes.c_wchar_p,
        ctypes.c_uint32,
    ]
    get_volume_path.restype = ctypes.c_bool
    volume_path = ctypes.create_unicode_buffer(32_768)
    if not get_volume_path(str(resolved), volume_path, len(volume_path)):
        return False
    filesystem = ctypes.create_unicode_buffer(256)
    get_volume_information = kernel32.GetVolumeInformationW
    get_volume_information.argtypes = [
        ctypes.c_wchar_p,
        ctypes.c_wchar_p,
        ctypes.c_uint32,
        ctypes.POINTER(ctypes.c_uint32),
        ctypes.POINTER(ctypes.c_uint32),
        ctypes.POINTER(ctypes.c_uint32),
        ctypes.c_wchar_p,
        ctypes.c_uint32,
    ]
    get_volume_information.restype = ctypes.c_bool
    serial = ctypes.c_uint32(0)
    maximum_component = ctypes.c_uint32(0)
    flags = ctypes.c_uint32(0)
    if not get_volume_information(
        volume_path.value,
        None,
        0,
        ctypes.byref(serial),
        ctypes.byref(maximum_component),
        ctypes.byref(flags),
        filesystem,
        len(filesystem),
    ):
        return False
    if filesystem.value.upper() != "NTFS":
        return False

    class _FileIdUnion(ctypes.Union):
        _fields_ = [("FileId", ctypes.c_longlong), ("ExtendedFileId", ctypes.c_ubyte * 16)]

    class _FileIdDescriptor(ctypes.Structure):
        _anonymous_ = ("Identifier",)
        _fields_ = [
            ("dwSize", ctypes.c_uint32),
            ("Type", ctypes.c_int),
            ("Identifier", _FileIdUnion),
        ]

    create_file = kernel32.CreateFileW
    create_file.argtypes = [
        ctypes.c_wchar_p,
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.c_void_p,
    ]
    create_file.restype = ctypes.c_void_p
    root_handle = create_file(
        str(resolved),
        0x00000080,
        0x00000001 | 0x00000002 | 0x00000004,
        None,
        3,
        0x02000000 | 0x00200000,
        None,
    )
    invalid = ctypes.c_void_p(-1).value
    if not root_handle or root_handle == invalid:
        return False
    close_handle = kernel32.CloseHandle
    close_handle.argtypes = [ctypes.c_void_p]
    close_handle.restype = ctypes.c_bool
    recovered_handle: int | None = None
    try:
        descriptor = _FileIdDescriptor()
        descriptor.dwSize = ctypes.sizeof(_FileIdDescriptor)
        descriptor.Type = 0
        descriptor.FileId = ctypes.c_longlong(
            metadata.st_ino
            if metadata.st_ino < (1 << 63)
            else metadata.st_ino - (1 << 64)
        ).value
        open_by_id = kernel32.OpenFileById
        open_by_id.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(_FileIdDescriptor),
            ctypes.c_uint32,
            ctypes.c_uint32,
            ctypes.c_void_p,
            ctypes.c_uint32,
        ]
        open_by_id.restype = ctypes.c_void_p
        recovered = open_by_id(
            ctypes.c_void_p(root_handle),
            ctypes.byref(descriptor),
            0,
            0x00000001 | 0x00000002 | 0x00000004,
            None,
            0x02000000,
        )
        if not recovered or recovered == invalid:
            return False
        recovered_handle = int(recovered)
        recovered_path = _opened_windows_path(recovered_handle)
        return _directory_object_identity(recovered_path) == (
            metadata.st_dev,
            metadata.st_ino,
        )
    except (OSError, RuntimeError, ValueError):
        return False
    finally:
        if recovered_handle is not None:
            close_handle(ctypes.c_void_p(recovered_handle))
        close_handle(ctypes.c_void_p(root_handle))


def initialize_authorized_o4_isolate_root(
    isolate_root: Path, public_identity: str
) -> dict[str, Any]:
    """Mark one already-authorized empty CODEX_HOME before OAuth or snapshotting."""

    if SNAPSHOT_PUBLIC_ID_PATTERN.fullmatch(public_identity) is None:
        raise ValueError("O4 isolate public identity is invalid")
    root = isolate_root.resolve(strict=True)
    if (
        not root.is_dir()
        or _is_reparse_or_symlink(root)
        or any(root.iterdir())
        or (os.name == "nt" and not _windows_private_cleanup_capability(root))
    ):
        raise ValueError("O4 isolate root must be an exact empty directory")
    marker = {
        "schema": 1,
        "kind": "authorized-o4-v3-isolated-codex-home",
        "publicIdentity": public_identity,
        "privateCleanupCapability": "exact-volume-root-handle-ntfs-fileid64-exclusive-v1",
        "privatePathPublished": False,
    }
    path = root.joinpath(*ISOLATE_MARKER_RELATIVE_PARTS)
    raw = json.dumps(
        marker, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8") + b"\n"
    with path.open("xb") as stream:
        stream.write(raw)
    if not _isolate_marker_valid(root, public_identity):
        path.unlink(missing_ok=True)
        raise ValueError("O4 isolate marker could not be verified")
    return marker


def _isolate_marker_valid(isolate_root: Path, public_identity: str) -> bool:
    try:
        root = isolate_root.resolve(strict=True)
        path = root.joinpath(*ISOLATE_MARKER_RELATIVE_PARTS)
        if (
            not root.is_dir()
            or _is_reparse_or_symlink(root)
            or _is_reparse_or_symlink(path)
            or not path.is_file()
            or path.stat().st_size > 4_096
        ):
            return False
        value = v1._strict_json_object(path.read_bytes())
    except (OSError, RuntimeError, TypeError, ValueError):
        return False
    return value == {
        "schema": 1,
        "kind": "authorized-o4-v3-isolated-codex-home",
        "publicIdentity": public_identity,
        "privateCleanupCapability": "exact-volume-root-handle-ntfs-fileid64-exclusive-v1",
        "privatePathPublished": False,
    }


def begin_task_scoped_capture_suite(
    isolate_root: Path,
    source_binding: dict[str, Any],
    snapshot: dict[str, Any],
    registered_user_chronology_baseline: dict[str, Any],
) -> _LiveO4CaptureSuite:
    """Open the one in-memory capture suite for the exact marked O4 isolate."""

    root = isolate_root.resolve(strict=True)
    if not snapshot_record_valid(snapshot, source_binding):
        raise ValueError("O4 live capture suite snapshot is invalid")
    public_identity = snapshot.get("publicIdentity")
    if not isinstance(public_identity, str) or not _isolate_marker_valid(
        root,
        public_identity,
    ) or (os.name == "nt" and not _windows_private_cleanup_capability(root)):
        raise ValueError("O4 live capture suite isolate is invalid")
    if not _user_chronology_baseline_valid(registered_user_chronology_baseline):
        raise ValueError("O4 registered user chronology baseline is invalid")
    return _LiveO4CaptureSuite(
        root, snapshot, registered_user_chronology_baseline
    )


def begin_pre_registration_capture_suite(
    isolate_root: Path,
    source_binding: dict[str, Any],
    snapshot: dict[str, Any],
) -> _LiveO4CaptureSuite:
    """Open a source-preparation-only suite that cannot produce measurement evidence."""

    root = isolate_root.resolve(strict=True)
    if (
        not snapshot_record_valid(snapshot, source_binding)
        or not isinstance(snapshot.get("publicIdentity"), str)
        or not _isolate_marker_valid(root, snapshot["publicIdentity"])
        or (os.name == "nt" and not _windows_private_cleanup_capability(root))
    ):
        raise ValueError("O4 pre-registration capture suite is invalid")
    return _LiveO4CaptureSuite(root, snapshot, None)


def cleanup_authorized_o4_isolate_root(
    isolate_root: Path,
    snapshot: dict[str, Any],
    *,
    reason: str,
) -> dict[str, Any]:
    """Delete the exact marker-bound task CODEX_HOME after snapshot/thread close."""

    if (
        reason not in SNAPSHOT_TERMINAL_REASONS
        or not isinstance(snapshot, dict)
        or not isinstance(snapshot.get("publicIdentity"), str)
    ):
        raise ValueError("O4 isolate cleanup boundary is invalid")
    root = isolate_root.resolve(strict=True)
    public_identity = snapshot["publicIdentity"]
    if not _isolate_marker_valid(root, public_identity) or root.joinpath(
        *SNAPSHOT_RELATIVE_PARTS
    ).exists():
        raise ValueError("O4 isolate is unmarked or snapshot cleanup is incomplete")
    nodes = 0
    total_bytes = 0
    for current, directories, files in os.walk(root, topdown=True, followlinks=False):
        current_path = Path(current)
        if _is_reparse_or_symlink(current_path):
            raise ValueError("O4 isolate contains a reparse directory")
        for name in [*directories, *files]:
            candidate = current_path / name
            nodes += 1
            if nodes > MAX_ISOLATE_CLEANUP_NODES or _is_reparse_or_symlink(candidate):
                raise ValueError("O4 isolate cleanup inventory exceeded its boundary")
            if candidate.is_file():
                total_bytes += candidate.stat().st_size
                if total_bytes > MAX_ISOLATE_CLEANUP_BYTES:
                    raise ValueError("O4 isolate cleanup bytes exceeded their boundary")
    shutil.rmtree(root)
    if root.exists():
        raise RuntimeError("O4 isolated CODEX_HOME still exists after cleanup")
    return {
        "schema": 1,
        "source": "authorized-o4-v3-isolated-codex-home-terminal-cleanup",
        "snapshotPublicIdentity": public_identity,
        "reason": reason,
        "isolatedCodexHomeAbsentAfterCleanup": True,
        "privatePathPublished": False,
    }


def _trusted_windows_powershell_executable() -> Path | None:
    """Resolve the inbox Windows PowerShell without trusting ambient PATH."""

    if os.name != "nt" or not hasattr(ctypes, "WinDLL"):
        return None
    try:
        kernel32 = ctypes.WinDLL("Kernel32.dll", use_last_error=True)
        get_system_directory = kernel32.GetSystemDirectoryW
        get_system_directory.argtypes = [ctypes.c_wchar_p, ctypes.c_uint32]
        get_system_directory.restype = ctypes.c_uint32
        buffer = ctypes.create_unicode_buffer(32_768)
        length = get_system_directory(buffer, len(buffer))
        if length == 0 or length >= len(buffer):
            raise OSError("system directory unavailable")
        system_directory = Path(buffer.value).resolve(strict=True)
        expected_parent = (
            system_directory / "WindowsPowerShell" / "v1.0"
        ).resolve(strict=True)
        executable = (expected_parent / "powershell.exe").resolve(strict=True)
        metadata = executable.lstat()
        if (
            executable.parent != expected_parent
            or executable.name.casefold() != "powershell.exe"
            or not stat.S_ISREG(metadata.st_mode)
            or _is_reparse_or_symlink(expected_parent.parent)
            or _is_reparse_or_symlink(expected_parent)
            or _is_reparse_or_symlink(executable)
        ):
            raise OSError("untrusted Windows PowerShell surface")
    except (OSError, RuntimeError, ValueError):
        return None
    return executable


def _sha256_regular_file(path: Path) -> tuple[str, int]:
    if _is_reparse_or_symlink(path) or not path.is_file():
        raise ValueError("native executable must be a regular non-reparse file")
    size = path.stat().st_size
    if size <= 0 or size > MAX_NATIVE_EXECUTABLE_BYTES:
        raise ValueError("native executable size is outside the task boundary")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while True:
            chunk = stream.read(1_048_576)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest(), size


def _canonical_attestation_payload(value: Any) -> bytes:
    if (
        not isinstance(value, dict)
        or not v1._json_within_limits(value)
        or v1._contains_private_value(value)
    ):
        raise ValueError("O4 attestation payload is not public-safe")
    try:
        raw = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (RecursionError, TypeError, ValueError) as exc:
        raise ValueError("O4 attestation payload is invalid") from exc
    if not raw or len(raw) > MAX_ATTESTATION_PAYLOAD_BYTES:
        raise ValueError("O4 attestation payload exceeds byte limit")
    return raw


def _attestation_public_key_valid(value: Any) -> bool:
    if not isinstance(value, dict) or set(value) != {
        "schema",
        "scheme",
        "publicIdentity",
        "namespace",
        "publicKey",
        "publicKeyFingerprint",
        "keygenExecutableSha256",
        "implementation",
        "implementationVersion",
        "distribution",
        "sourceRepository",
        "license",
        "maturity",
        "reuseBoundary",
    }:
        return False
    public_identity = value.get("publicIdentity")
    public_key = value.get("publicKey")
    if (
        type(value.get("schema")) is not int
        or value.get("schema") != 1
        or value.get("scheme") != "openssh-sshsig-ed25519"
        or not isinstance(public_identity, str)
        or ATTESTATION_PUBLIC_ID_PATTERN.fullmatch(public_identity) is None
        or value.get("namespace") != ATTESTATION_NAMESPACE
        or not isinstance(public_key, str)
        or re.fullmatch(r"ssh-ed25519 [A-Za-z0-9+/]{60,100}={0,2}", public_key)
        is None
        or not isinstance(value.get("keygenExecutableSha256"), str)
        or SHA256_PATTERN.fullmatch(value["keygenExecutableSha256"]) is None
        or value.get("implementation") != "OpenSSH-sshsig"
        or not isinstance(value.get("implementationVersion"), str)
        or re.fullmatch(r"[ -~]{1,128}", value["implementationVersion"]) is None
        or (value.get("distribution"), value.get("sourceRepository"))
        not in {
            (
                "Windows-inbox-OpenSSH",
                "https://github.com/PowerShell/Win32-OpenSSH",
            ),
            (
                "operating-system-OpenSSH",
                "https://github.com/openssh/openssh-portable",
            ),
        }
        or value.get("license") != "OpenSSH-BSD-style"
        or value.get("maturity") != "operating-system-provided-established"
        or value.get("reuseBoundary")
        != "task-scoped-ed25519-sshsig-evidence-carrier-not-identity-or-authorization"
    ):
        return False
    try:
        encoded = public_key.split(" ", 1)[1]
        blob = base64.b64decode(encoded, validate=True)
        first_length = int.from_bytes(blob[:4], "big")
        first_end = 4 + first_length
        second_length = int.from_bytes(blob[first_end : first_end + 4], "big")
        key_bytes = blob[first_end + 4 :]
        expected_fingerprint = "SHA256:" + base64.b64encode(
            hashlib.sha256(blob).digest()
        ).decode("ascii").rstrip("=")
    except (IndexError, TypeError, ValueError):
        return False
    return (
        first_length == len(b"ssh-ed25519")
        and blob[4:first_end] == b"ssh-ed25519"
        and second_length == 32
        and len(key_bytes) == 32
        and value.get("publicKeyFingerprint") == expected_fingerprint
        and not v1._contains_private_value(value)
    )


def _ssh_keygen_implementation_version(executable: Path) -> str:
    if os.name == "nt":
        powershell = _trusted_windows_powershell_executable()
        if powershell is None:
            raise ValueError("trusted OpenSSH version surface is unavailable")
        system_directory = powershell.parents[2]
        system_root = system_directory.parent
        completed = subprocess.run(
            [
                str(powershell),
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                "$v=(Get-Item -LiteralPath $env:HARNESS_O4_SSH_KEYGEN).VersionInfo;"
                "$v.ProductVersion",
            ],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=15,
            env={
                "SystemRoot": str(system_root),
                "WINDIR": str(system_root),
                "ComSpec": str(system_directory / "cmd.exe"),
                "PATH": str(system_directory),
                "PATHEXT": ".COM;.EXE;.BAT;.CMD",
                "HARNESS_O4_SSH_KEYGEN": str(executable),
            },
        )
        raw = completed.stdout
        if completed.returncode != 0 or completed.stderr:
            raise ValueError("OpenSSH implementation version probe failed")
    else:
        ssh = (executable.parent / "ssh").resolve(strict=True)
        if (
            ssh.parent != executable.parent
            or _is_reparse_or_symlink(ssh)
            or not ssh.is_file()
        ):
            raise ValueError("trusted OpenSSH version surface is unavailable")
        completed = subprocess.run(
            [str(ssh), "-V"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=15,
            env=_trusted_ssh_environment(executable),
        )
        raw = completed.stderr or completed.stdout
        if completed.returncode != 0:
            raise ValueError("OpenSSH implementation version probe failed")
    try:
        version = raw.decode("utf-8").strip()
    except UnicodeError as exc:
        raise ValueError("OpenSSH implementation version is invalid") from exc
    if re.fullmatch(r"[ -~]{1,128}", version) is None:
        raise ValueError("OpenSSH implementation version is invalid")
    return version


def create_task_attestation_key(
    private_root: Path, public_identity: str
) -> dict[str, Any]:
    if ATTESTATION_PUBLIC_ID_PATTERN.fullmatch(public_identity) is None:
        raise ValueError("O4 attestation public identity is invalid")
    root = private_root.resolve(strict=True)
    if (
        not root.is_dir()
        or _is_reparse_or_symlink(root)
        or any(root.iterdir())
        or (os.name == "nt" and not _windows_private_cleanup_capability(root))
    ):
        raise ValueError("O4 attestation private root is invalid")
    executable = _trusted_ssh_keygen_executable()
    if executable is None:
        raise ValueError("trusted OpenSSH signature surface is unavailable")
    key_path = root.joinpath(*ATTESTATION_KEY_RELATIVE_PARTS)
    public_path = Path(str(key_path) + ".pub")
    if key_path.exists() or public_path.exists():
        raise ValueError("O4 attestation key already exists")
    completed = subprocess.run(
        [
            str(executable),
            "-q",
            "-t",
            "ed25519",
            "-N",
            "",
            "-C",
            "",
            "-f",
            str(key_path),
        ],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
        env=_trusted_ssh_environment(executable, root),
    )
    try:
        if completed.returncode != 0 or completed.stdout or completed.stderr:
            raise ValueError("O4 attestation key generation failed")
        if (
            _is_reparse_or_symlink(key_path)
            or _is_reparse_or_symlink(public_path)
            or not key_path.is_file()
            or not public_path.is_file()
        ):
            raise ValueError("O4 attestation key files are invalid")
        fields = public_path.read_text(encoding="ascii").strip().split()
        if len(fields) < 2:
            raise ValueError("O4 attestation public key is invalid")
        public_key = " ".join(fields[:2])
        blob = base64.b64decode(fields[1], validate=True)
        fingerprint = "SHA256:" + base64.b64encode(
            hashlib.sha256(blob).digest()
        ).decode("ascii").rstrip("=")
        public_path.write_text(public_key + "\n", encoding="ascii", newline="\n")
        os.chmod(key_path, stat.S_IRUSR | stat.S_IWUSR)
        keygen_sha256, _ = _sha256_regular_file(executable)
        binding = {
            "schema": 1,
            "scheme": "openssh-sshsig-ed25519",
            "publicIdentity": public_identity,
            "namespace": ATTESTATION_NAMESPACE,
            "publicKey": public_key,
            "publicKeyFingerprint": fingerprint,
            "keygenExecutableSha256": keygen_sha256,
            "implementation": "OpenSSH-sshsig",
            "implementationVersion": _ssh_keygen_implementation_version(executable),
            "distribution": (
                "Windows-inbox-OpenSSH"
                if os.name == "nt"
                else "operating-system-OpenSSH"
            ),
            "sourceRepository": (
                "https://github.com/PowerShell/Win32-OpenSSH"
                if os.name == "nt"
                else "https://github.com/openssh/openssh-portable"
            ),
            "license": "OpenSSH-BSD-style",
            "maturity": "operating-system-provided-established",
            "reuseBoundary": (
                "task-scoped-ed25519-sshsig-evidence-carrier-not-identity-or-"
                "authorization"
            ),
        }
        if not _attestation_public_key_valid(binding):
            raise ValueError("O4 attestation public binding is invalid")
        return _TaskAttestationPublicBinding(binding, root)
    except Exception as original_error:
        for candidate in (public_path, key_path):
            if candidate.exists() and not _is_reparse_or_symlink(candidate):
                candidate.unlink()
        if root.exists() and not any(root.iterdir()):
            root.rmdir()
        raise original_error


def _sign_task_attestation(
    private_root: Path,
    public_binding: dict[str, Any],
    payload: dict[str, Any],
) -> dict[str, Any]:
    if not _attestation_public_key_valid(public_binding):
        raise ValueError("O4 attestation public binding is invalid")
    root = private_root.resolve(strict=True)
    key_path = root.joinpath(*ATTESTATION_KEY_RELATIVE_PARTS)
    public_path = Path(str(key_path) + ".pub")
    if (
        _is_reparse_or_symlink(key_path)
        or _is_reparse_or_symlink(public_path)
        or public_path.read_text(encoding="ascii").strip()
        != public_binding["publicKey"]
    ):
        raise ValueError("O4 attestation private key binding is invalid")
    raw = _canonical_attestation_payload(payload)
    if payload.get("kind") not in {
        "o4-v3-source-preparation-before-measurement",
        "o4-v3-public-measurement-after-registration",
        "o4-v3-terminal-private-resource-cleanup",
    }:
        raise ValueError("unsupported O4 attestation payload kind")
    executable = _trusted_ssh_keygen_executable()
    if executable is None:
        raise ValueError("trusted OpenSSH signature surface is unavailable")
    executable_sha256, _ = _sha256_regular_file(executable)
    if executable_sha256 != public_binding["keygenExecutableSha256"]:
        raise ValueError("OpenSSH signing executable drifted after key creation")
    payload_path = root / "o4-v3-attestation-payload.json"
    signature_path = Path(str(payload_path) + ".sig")
    if payload_path.exists() or signature_path.exists():
        raise ValueError("O4 attestation signing residue already exists")
    try:
        with payload_path.open("xb") as stream:
            stream.write(raw)
        completed = subprocess.run(
            [
                str(executable),
                "-Y",
                "sign",
                "-f",
                str(key_path),
                "-n",
                ATTESTATION_NAMESPACE,
                str(payload_path),
            ],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
            env=_trusted_ssh_environment(executable, root),
        )
        if (
            completed.returncode != 0
            or completed.stdout
            or len(completed.stderr) > 4_096
            or not signature_path.is_file()
            or _is_reparse_or_symlink(signature_path)
        ):
            raise ValueError("O4 attestation signing failed")
        signature = signature_path.read_bytes()
        if not signature or len(signature) > MAX_ATTESTATION_SIGNATURE_BYTES:
            raise ValueError("O4 attestation signature is invalid")
        record = {
            "schema": 1,
            "publicIdentity": public_binding["publicIdentity"],
            "namespace": ATTESTATION_NAMESPACE,
            "payloadSha256": hashlib.sha256(raw).hexdigest(),
            "signatureBase64": base64.b64encode(signature).decode("ascii"),
        }
    finally:
        for candidate in (signature_path, payload_path):
            if candidate.exists():
                if _is_reparse_or_symlink(candidate) or not candidate.is_file():
                    raise RuntimeError("O4 attestation signing cleanup became unsafe")
                candidate.unlink()
    if not verify_task_attestation(public_binding, payload, record):
        raise ValueError("O4 attestation signature did not verify")
    return record


def verify_task_attestation(
    public_binding: dict[str, Any],
    payload: dict[str, Any],
    signature_record: Any,
) -> bool:
    if not _attestation_public_key_valid(public_binding) or not isinstance(
        signature_record, dict
    ):
        return False
    raw = _canonical_attestation_payload(payload)
    if (
        type(signature_record.get("schema")) is not int
        or not isinstance(signature_record.get("signatureBase64"), str)
        or set(signature_record) != {
        "schema",
        "publicIdentity",
        "namespace",
        "payloadSha256",
        "signatureBase64",
        }
        or signature_record
        != {
            **signature_record,
            "schema": 1,
            "publicIdentity": public_binding["publicIdentity"],
            "namespace": ATTESTATION_NAMESPACE,
            "payloadSha256": hashlib.sha256(raw).hexdigest(),
        }
    ):
        return False
    try:
        signature = base64.b64decode(
            signature_record["signatureBase64"], validate=True
        )
    except (KeyError, TypeError, ValueError):
        return False
    if not signature or len(signature) > MAX_ATTESTATION_SIGNATURE_BYTES:
        return False
    executable = _trusted_ssh_keygen_executable()
    if executable is None:
        return False
    try:
        executable_sha256, _ = _sha256_regular_file(executable)
        if executable_sha256 != public_binding["keygenExecutableSha256"]:
            return False
        with tempfile.TemporaryDirectory(prefix="aah-o4-v3-verify-") as directory:
            root = Path(directory)
            allowed = root / "allowed_signers"
            signature_path = root / "capture.sig"
            allowed.write_text(
                "o4-v3 " + public_binding["publicKey"] + "\n",
                encoding="ascii",
                newline="\n",
            )
            signature_path.write_bytes(signature)
            completed = subprocess.run(
                [
                    str(executable),
                    "-Y",
                    "verify",
                    "-f",
                    str(allowed),
                    "-I",
                    "o4-v3",
                    "-n",
                    ATTESTATION_NAMESPACE,
                    "-s",
                    str(signature_path),
                ],
                input=raw,
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=30,
                env=_trusted_ssh_environment(executable, root),
            )
    except (OSError, subprocess.SubprocessError, ValueError):
        return False
    return (
        completed.returncode == 0
        and len(completed.stdout) <= 4_096
        and len(completed.stderr) <= 4_096
    )


def cleanup_task_attestation_key(
    private_root: Path,
    public_binding: dict[str, Any],
    *,
    reason: str,
) -> dict[str, Any]:
    if reason not in PRIVATE_SOURCE_TERMINAL_REASONS or not (
        _attestation_public_key_valid(public_binding)
    ):
        raise ValueError("O4 attestation key cleanup boundary is invalid")
    root = private_root.resolve(strict=True)
    key_path = root.joinpath(*ATTESTATION_KEY_RELATIVE_PARTS)
    public_path = Path(str(key_path) + ".pub")
    if public_path.read_text(encoding="ascii").strip() != public_binding["publicKey"]:
        raise ValueError("O4 attestation key cleanup identity is invalid")
    for candidate in (public_path, key_path):
        if _is_reparse_or_symlink(candidate) or not candidate.is_file():
            raise ValueError("O4 attestation key cleanup target is invalid")
        candidate.unlink()
    if key_path.exists() or public_path.exists() or any(root.iterdir()):
        raise RuntimeError("O4 attestation key still exists after cleanup")
    root.rmdir()
    if root.exists():
        raise RuntimeError("O4 attestation private root still exists after cleanup")
    return {
        "schema": 1,
        "source": "o4-capture-attestation-key-terminal-cleanup",
        "publicIdentity": public_binding["publicIdentity"],
        "publicKeyFingerprint": public_binding["publicKeyFingerprint"],
        "reason": reason,
        "privateKeyAbsentAfterCleanup": True,
        "privateRootAbsentAfterCleanup": True,
        "privatePathPublished": False,
    }


VersionProbe = Callable[[Path, Path], str]
SignatureProbe = Callable[[Path], tuple[str, str, str]]
ProcessFactory = Callable[..., Any]
ProcessImageProbe = Callable[[Any], Path]
OfficialSourceProbe = Callable[[dict[str, Any]], bool]


def _default_version_probe(executable: Path, isolate_root: Path) -> str:
    powershell = _trusted_windows_powershell_executable()
    if powershell is None:
        raise ValueError("trusted Windows version-probe environment is unavailable")
    system_directory = powershell.parents[2]
    system_root = system_directory.parent
    environment = {
        "CODEX_HOME": str(isolate_root),
        "HOME": str(isolate_root),
        "USERPROFILE": str(isolate_root),
        "NO_COLOR": "1",
        "SystemRoot": str(system_root),
        "WINDIR": str(system_root),
        "ComSpec": str(system_directory / "cmd.exe"),
        "PATH": os.pathsep.join([str(executable.parent), str(system_directory)]),
        "PATHEXT": ".COM;.EXE;.BAT;.CMD",
        "TEMP": str(isolate_root),
        "TMP": str(isolate_root),
    }
    completed = subprocess.run(
        [str(executable), "--version"],
        cwd=isolate_root,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=15,
        env=environment,
    )
    if (
        completed.returncode != 0
        or len(completed.stdout) > 256
        or len(completed.stderr) > 4_096
    ):
        raise ValueError("task-scoped Codex version probe failed")
    return completed.stdout.decode("utf-8").strip()


def _default_signature_probe(executable: Path) -> tuple[str, str, str]:
    if os.name != "nt":
        raise ValueError("Authenticode observation is available only on Windows")
    powershell = _trusted_windows_powershell_executable()
    if powershell is None:
        raise ValueError("trusted PowerShell signature surface is unavailable")
    system_directory = powershell.parents[2]
    system_root = system_directory.parent
    script = (
        "$ErrorActionPreference='Stop';"
        "Import-Module Microsoft.PowerShell.Security -ErrorAction Stop;"
        "$s=Microsoft.PowerShell.Security\\Get-AuthenticodeSignature -LiteralPath "
        "$env:HARNESS_O4_SIGNATURE_TARGET;"
        "$h=[Security.Cryptography.SHA256]::Create();"
        "$certSha=([BitConverter]::ToString($h.ComputeHash("
        "$s.SignerCertificate.RawData))).Replace('-','').ToLowerInvariant();"
        "$h.Dispose();"
        "[pscustomobject]@{status=[string]$s.Status;"
        "signer=[string]$s.SignerCertificate.Subject;"
        "certificateSha256=$certSha}|ConvertTo-Json -Compress"
    )
    environment = {
        "SystemRoot": str(system_root),
        "WINDIR": str(system_root),
        "ComSpec": str(system_directory / "cmd.exe"),
        "PATH": str(system_directory),
        "PATHEXT": ".COM;.EXE;.BAT;.CMD",
        "POWERSHELL_TELEMETRY_OPTOUT": "1",
        "HARNESS_O4_SIGNATURE_TARGET": str(executable),
    }
    completed = subprocess.run(
        [powershell, "-NoProfile", "-NonInteractive", "-Command", script],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=20,
        env=environment,
    )
    if (
        completed.returncode != 0
        or len(completed.stdout) > 4_096
        or bool(completed.stderr)
    ):
        raise ValueError("task-scoped Codex signature probe failed")
    try:
        value = v1._strict_json_object(completed.stdout)
    except (json.JSONDecodeError, RecursionError, TypeError, UnicodeError, ValueError):
        raise ValueError("task-scoped Codex signature output is invalid") from None
    status = value.get("status")
    signer = value.get("signer")
    certificate_sha256 = value.get("certificateSha256")
    if (
        set(value) != {"status", "signer", "certificateSha256"}
        or not isinstance(status, str)
        or not status
        or status.strip() != status
        or not isinstance(signer, str)
        or not signer
        or signer.strip() != signer
        or not isinstance(certificate_sha256, str)
        or SHA256_PATTERN.fullmatch(certificate_sha256) is None
    ):
        raise ValueError("task-scoped Codex signature identity is invalid")
    return status, signer, certificate_sha256


def materialize_task_scoped_native_snapshot(
    source_executable: Path,
    isolate_root: Path,
    source_binding: dict[str, Any],
    public_identity: str,
    *,
    version_probe: VersionProbe | None = None,
    signature_probe: SignatureProbe | None = None,
    official_source_probe: OfficialSourceProbe | None = None,
) -> dict[str, Any]:
    """Copy and verify the exact native executable before registration."""

    if (
        not official_source_binding_valid(source_binding)
        or SNAPSHOT_PUBLIC_ID_PATTERN.fullmatch(public_identity) is None
    ):
        raise ValueError("official source or snapshot public identity is invalid")
    selected_official_source_probe = (
        _default_official_source_probe
        if official_source_probe is None
        else official_source_probe
    )
    if selected_official_source_probe(source_binding) is not True:
        raise ValueError("official Codex source observation is invalid")
    root = isolate_root.resolve(strict=True)
    source = source_executable.resolve(strict=True)
    if (
        not root.is_dir()
        or _is_reparse_or_symlink(root)
        or not _isolate_marker_valid(root, public_identity)
        or source.is_relative_to(root)
    ):
        raise ValueError("snapshot source or isolate root is invalid")
    source_sha256, source_bytes = _sha256_regular_file(source)
    if (
        source_sha256 != source_binding["nativeExecutableSha256"]
        or source_bytes != source_binding["nativeExecutableBytes"]
    ):
        raise ValueError("ambient native executable does not match the bound source")
    selected_signature_probe = (
        _default_signature_probe if signature_probe is None else signature_probe
    )
    source_status, source_signer, source_certificate_sha256 = (
        selected_signature_probe(source)
    )
    if (
        source_status != source_binding["nativeAuthenticodeStatus"]
        or source_signer != source_binding["nativeAuthenticodeSigner"]
        or source_certificate_sha256
        != source_binding["nativeAuthenticodeCertificateSha256"]
    ):
        raise ValueError("ambient native executable signature does not match")

    snapshot_parent = root.joinpath(*SNAPSHOT_RELATIVE_PARTS[:-1])
    target = root.joinpath(*SNAPSHOT_RELATIVE_PARTS)
    harness_parent = snapshot_parent.parent
    harness_parent_preexisting = harness_parent.exists()
    if (
        target.exists()
        or snapshot_parent.exists()
        or (harness_parent_preexisting and _is_reparse_or_symlink(harness_parent))
    ):
        raise ValueError("task-scoped native snapshot already exists")
    try:
        snapshot_parent.mkdir(parents=True, exist_ok=False)
        with source.open("rb") as incoming, target.open("xb") as outgoing:
            shutil.copyfileobj(incoming, outgoing, length=1_048_576)
        snapshot_sha256, snapshot_bytes = _sha256_regular_file(target)
        snapshot_status, snapshot_signer, snapshot_certificate_sha256 = (
            selected_signature_probe(target)
        )
        selected_version_probe = (
            _default_version_probe if version_probe is None else version_probe
        )
        version_output = selected_version_probe(target, root)
        if (
            snapshot_sha256 != source_sha256
            or snapshot_bytes != source_bytes
            or snapshot_status != source_status
            or snapshot_signer != source_signer
            or snapshot_certificate_sha256 != source_certificate_sha256
            or version_output != f"codex-cli {source_binding['releaseVersion']}"
        ):
            raise ValueError("task-scoped native snapshot verification failed")
        record = {
            "schema": 1,
            "captureKind": "o4-task-scoped-native-execution-snapshot",
            "publicIdentity": public_identity,
            "state": "materialized-before-manifest-and-registration",
            "sourceReleaseVersion": source_binding["releaseVersion"],
            "sourceExecutableSha256": source_sha256,
            "sourceExecutableBytes": source_bytes,
            "snapshotExecutableSha256": snapshot_sha256,
            "snapshotExecutableBytes": snapshot_bytes,
            "sourceAndSnapshotByteIdentity": "equal",
            "snapshotVersionOutput": version_output,
            "authenticodeStatus": snapshot_status,
            "authenticodeSigner": snapshot_signer,
            "authenticodeCertificateSha256": snapshot_certificate_sha256,
            **SNAPSHOT_POLICY,
        }
        if not snapshot_record_valid(record, source_binding):
            raise ValueError("task-scoped native snapshot record is invalid")
        return record
    except Exception as original_error:
        try:
            if target.exists():
                if _is_reparse_or_symlink(target) or not target.is_file():
                    raise OSError("unsafe snapshot failure residue")
                target.unlink()
            if snapshot_parent.exists():
                if _is_reparse_or_symlink(snapshot_parent):
                    raise OSError("unsafe snapshot failure parent")
                snapshot_parent.rmdir()
        except OSError as cleanup_error:
            raise RuntimeError(
                "task-scoped native snapshot failure cleanup did not close"
            ) from cleanup_error
        if not harness_parent_preexisting and harness_parent.exists():
            try:
                harness_parent.rmdir()
            except OSError:
                pass
        raise original_error


def prepare_task_scoped_native_snapshot(
    source_executable: Path,
    isolate_root: Path,
    public_identity: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Resolve the current official release once, then snapshot that exact byte set."""

    source_binding = resolve_current_official_source_binding(
        source_executable, isolate_root
    )
    snapshot = materialize_task_scoped_native_snapshot(
        source_executable,
        isolate_root,
        source_binding,
        public_identity,
        official_source_probe=lambda candidate: candidate == source_binding,
    )
    return source_binding, snapshot


def verified_task_scoped_snapshot_executable(
    isolate_root: Path,
    source_binding: dict[str, Any],
    snapshot: dict[str, Any],
    *,
    version_probe: VersionProbe | None = None,
    signature_probe: SignatureProbe | None = None,
) -> Path:
    """Return only the registered private executable after a fresh preflight."""

    if not snapshot_record_valid(snapshot, source_binding):
        raise ValueError("task-scoped native snapshot binding is invalid")
    root = isolate_root.resolve(strict=True)
    if not _isolate_marker_valid(root, snapshot["publicIdentity"]):
        raise ValueError("task-scoped native snapshot isolate marker is invalid")
    target = root.joinpath(*SNAPSHOT_RELATIVE_PARTS)
    resolved = target.resolve(strict=True)
    if not resolved.is_relative_to(root) or resolved != target:
        raise ValueError("task-scoped native snapshot escaped its isolate")
    observed_sha256, observed_bytes = _sha256_regular_file(resolved)
    selected_signature_probe = (
        _default_signature_probe if signature_probe is None else signature_probe
    )
    status, signer, certificate_sha256 = selected_signature_probe(resolved)
    selected_version_probe = _default_version_probe if version_probe is None else version_probe
    version_output = selected_version_probe(resolved, root)
    if (
        observed_sha256 != snapshot["snapshotExecutableSha256"]
        or observed_bytes != snapshot["snapshotExecutableBytes"]
        or status != snapshot["authenticodeStatus"]
        or signer != snapshot["authenticodeSigner"]
        or certificate_sha256 != snapshot["authenticodeCertificateSha256"]
        or version_output != snapshot["snapshotVersionOutput"]
    ):
        raise ValueError("task-scoped native snapshot preflight failed")
    return resolved


def snapshot_preflight_observation(
    isolate_root: Path,
    source_binding: dict[str, Any],
    snapshot: dict[str, Any],
    *,
    version_probe: VersionProbe | None = None,
    signature_probe: SignatureProbe | None = None,
) -> dict[str, Any]:
    executable = verified_task_scoped_snapshot_executable(
        isolate_root,
        source_binding,
        snapshot,
        version_probe=version_probe,
        signature_probe=signature_probe,
    )
    observed_sha256, observed_bytes = _sha256_regular_file(executable)
    return {
        "source": "task-scoped-native-snapshot-preflight",
        "snapshotPublicIdentity": snapshot["publicIdentity"],
        "releaseVersion": source_binding["releaseVersion"],
        "registeredSha256": snapshot["snapshotExecutableSha256"],
        "observedExecutableSha256": observed_sha256,
        "observedExecutableBytes": observed_bytes,
        "versionOutput": snapshot["snapshotVersionOutput"],
        "ambientExecutableUsed": False,
    }


def _network_environment_valid(value: Mapping[str, str]) -> bool:
    return (
        set(value).issubset(ALLOWED_NETWORK_ENVIRONMENT_KEYS)
        and all(
            isinstance(item, str)
            and item
            and len(item) <= 4_096
            and "\x00" not in item
            for item in value.values()
        )
    )


def _launch_record_valid(
    value: Any,
    source_binding: dict[str, Any],
    snapshot: dict[str, Any],
) -> bool:
    if not isinstance(value, dict):
        return False
    launch_identity = value.get("launchPublicIdentity")
    return value == {
        "schema": 1,
        "source": "task-scoped-native-snapshot-app-server-launch",
        "launchPublicIdentity": launch_identity,
        "snapshotPublicIdentity": snapshot["publicIdentity"],
        "releaseVersion": source_binding["releaseVersion"],
        "processImageSha256": snapshot["snapshotExecutableSha256"],
        "processImageBytes": snapshot["snapshotExecutableBytes"],
        "processImageObservedFromHost": True,
        "command": "app-server",
        "cwdClass": "exact-authorized-isolate-root",
        "environmentClass": (
            "isolated-codex-home-plus-explicit-source-bound-network-environment"
        ),
        "ambientExecutableUsed": False,
    } and isinstance(launch_identity, str) and (
        LAUNCH_PUBLIC_ID_PATTERN.fullmatch(launch_identity) is not None
    ) and not v1._contains_private_value(value)


def _default_process_image_probe(process: Any) -> Path:
    if os.name != "nt" or not hasattr(ctypes, "WinDLL"):
        raise ValueError("Windows process-image observation is unavailable")
    pid = getattr(process, "pid", None)
    if type(pid) is not int or pid <= 0:
        raise ValueError("App Server process identity is unavailable")
    kernel32 = ctypes.WinDLL("Kernel32.dll", use_last_error=True)
    open_process = kernel32.OpenProcess
    open_process.argtypes = [ctypes.c_uint32, ctypes.c_bool, ctypes.c_uint32]
    open_process.restype = ctypes.c_void_p
    query_image = kernel32.QueryFullProcessImageNameW
    query_image.argtypes = [
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.c_wchar_p,
        ctypes.POINTER(ctypes.c_uint32),
    ]
    query_image.restype = ctypes.c_bool
    close_handle = kernel32.CloseHandle
    close_handle.argtypes = [ctypes.c_void_p]
    close_handle.restype = ctypes.c_bool
    handle = open_process(0x1000, False, pid)
    if not handle:
        raise ValueError("App Server process cannot be inspected")
    try:
        buffer = ctypes.create_unicode_buffer(32_768)
        length = ctypes.c_uint32(len(buffer))
        if not query_image(handle, 0, buffer, ctypes.byref(length)):
            raise ValueError("App Server process image is unavailable")
        observed = Path(buffer.value[: length.value]).resolve(strict=True)
    finally:
        close_handle(handle)
    return observed


def _terminate_task_scoped_process(process: Any) -> None:
    """Require the task-owned child to reach a terminal state or surface residue."""

    try:
        process.terminate()
        process.wait(timeout=5)
        return
    except (AttributeError, OSError, subprocess.TimeoutExpired):
        pass
    try:
        process.kill()
        process.wait(timeout=5)
    except (AttributeError, OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError("task-scoped App Server process could not be terminated") from exc


def _finish_and_close_task_scoped_streams(
    process: Any,
    *,
    timeout: float,
    require_bounded_capture: bool,
) -> None:
    errors: list[Exception] = []
    capture = getattr(process, "_o4_bounded_streams", None)
    if isinstance(capture, _BoundedAppServerStreams):
        try:
            capture.finish(timeout)
        except ValueError as exc:
            errors.append(exc)
    elif require_bounded_capture:
        errors.append(ValueError("task-scoped App Server capture state is missing"))
    for stream_name in ("stdin", "stdout", "stderr"):
        stream = getattr(process, stream_name, None)
        try:
            if stream is not None and not getattr(stream, "closed", False):
                stream.close()
        except OSError as exc:
            errors.append(exc)
    if errors:
        raise RuntimeError("task-scoped App Server streams did not close cleanly") from errors[0]


def _terminate_and_close_task_scoped_process_streams(
    process: Any,
    *,
    require_bounded_capture: bool,
) -> None:
    """Attempt both child termination and stream cleanup, surfacing either residue."""

    errors: list[Exception] = []
    try:
        _terminate_task_scoped_process(process)
    except Exception as exc:
        errors.append(exc)
    try:
        _finish_and_close_task_scoped_streams(
            process,
            timeout=5.0,
            require_bounded_capture=require_bounded_capture,
        )
    except Exception as exc:
        errors.append(exc)
    if errors:
        raise RuntimeError(
            "task-scoped App Server process or stream residue remains"
        ) from errors[0]


def launch_task_scoped_snapshot_app_server(
    isolate_root: Path,
    source_binding: dict[str, Any],
    snapshot: dict[str, Any],
    launch_public_identity: str,
    *,
    network_environment: Mapping[str, str],
    capture_suite: _LiveO4CaptureSuite | None = None,
    version_probe: VersionProbe | None = None,
    signature_probe: SignatureProbe | None = None,
    process_factory: ProcessFactory | None = None,
    process_image_probe: ProcessImageProbe | None = None,
) -> tuple[Any, dict[str, Any]]:
    """Launch only the verified task snapshot; return no private path evidence."""

    if (
        LAUNCH_PUBLIC_ID_PATTERN.fullmatch(launch_public_identity) is None
        or not _network_environment_valid(network_environment)
    ):
        raise ValueError("task-scoped App Server launch boundary is invalid")
    root = isolate_root.resolve(strict=True)
    if process_factory is None and (
        not isinstance(capture_suite, _LiveO4CaptureSuite)
        or capture_suite.origin is not _LIVE_CAPTURE_ORIGIN
        or capture_suite.isolate_root != root
        or capture_suite.snapshot != snapshot
    ):
        raise ValueError("task-scoped App Server capture suite is invalid")
    executable = verified_task_scoped_snapshot_executable(
        root,
        source_binding,
        snapshot,
        version_probe=version_probe,
        signature_probe=signature_probe,
    )
    powershell = _trusted_windows_powershell_executable()
    if powershell is None:
        raise ValueError("trusted Windows runtime environment is unavailable")
    system_directory = powershell.parents[2]
    system_root = system_directory.parent
    environment = {
        "CODEX_HOME": str(root),
        "HOME": str(root),
        "USERPROFILE": str(root),
        "NO_COLOR": "1",
        "SystemRoot": str(system_root),
        "WINDIR": str(system_root),
        "ComSpec": str(system_directory / "cmd.exe"),
        "PATH": os.pathsep.join([str(executable.parent), str(system_directory)]),
        "PATHEXT": ".COM;.EXE;.BAT;.CMD",
        "TEMP": str(root),
        "TMP": str(root),
        **dict(network_environment),
    }
    record = {
        "schema": 1,
        "source": "task-scoped-native-snapshot-app-server-launch",
        "launchPublicIdentity": launch_public_identity,
        "snapshotPublicIdentity": snapshot["publicIdentity"],
        "releaseVersion": source_binding["releaseVersion"],
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
    if not _launch_record_valid(record, source_binding, snapshot):
        raise ValueError("task-scoped App Server launch record is invalid")
    image_lock = _LockedSnapshotExecutable(executable)
    selected_factory = subprocess.Popen if process_factory is None else process_factory
    process: Any | None = None
    try:
        if image_lock.digest_and_size != (
            snapshot["snapshotExecutableSha256"],
            snapshot["snapshotExecutableBytes"],
        ):
            raise ValueError("snapshot image drifted before process creation")
        locked_executable = verified_task_scoped_snapshot_executable(
            root,
            source_binding,
            snapshot,
            version_probe=version_probe,
            signature_probe=signature_probe,
        )
        image_lock.verify()
        if locked_executable != executable:
            raise ValueError("snapshot image path drifted before process creation")
        process = selected_factory(
            [str(executable), "app-server"],
            cwd=root,
            env=environment,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0,
        )
        if process_factory is None:
            try:
                process._o4_bounded_streams = _BoundedAppServerStreams(process)
                process._o4_native_snapshot_launch = True
            except Exception as original_error:
                raise ValueError(
                    "App Server bounded stream capture failed"
                ) from original_error
        selected_process_image_probe = (
            _default_process_image_probe
            if process_image_probe is None
            else process_image_probe
        )
        observed_image = selected_process_image_probe(process).resolve(strict=True)
        if observed_image != executable:
            raise ValueError("App Server process image differs from the snapshot")
        image_lock.verify()
        observed_sha256, observed_bytes = _sha256_regular_file(observed_image)
        if (
            observed_sha256 != snapshot["snapshotExecutableSha256"]
            or observed_bytes != snapshot["snapshotExecutableBytes"]
        ):
            raise ValueError("App Server process image identity drifted")
        if process_factory is None:
            preflight = snapshot_preflight_observation(
                root,
                source_binding,
                snapshot,
                version_probe=version_probe,
                signature_probe=signature_probe,
            )
            process._o4_live_capture = _LiveAppServerCapture(
                record,
                preflight,
                source_binding,
                snapshot,
                root,
                capture_suite,
            )
    except Exception as original_error:
        if process is not None:
            _terminate_and_close_task_scoped_process_streams(
                process,
                require_bounded_capture=process_factory is None,
            )
        raise original_error
    finally:
        image_lock.release()
    assert process is not None
    return process, record


def write_snapshot_app_server_message(process: Any, message: dict[str, Any]) -> None:
    if getattr(process, "stdin", None) is None or not v1._json_within_limits(message):
        raise ValueError("App Server request boundary is invalid")
    try:
        raw = json.dumps(
            message,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8") + b"\n"
    except (RecursionError, TypeError, ValueError) as exc:
        raise ValueError("App Server request is invalid") from exc
    if len(raw) > 262_144:
        raise ValueError("App Server request exceeds byte limit")
    live_capture = getattr(process, "__dict__", {}).get("_o4_live_capture")
    bound: dict[str, Any] | None = None
    compact_source_carrier_id: str | None = None
    if live_capture is not None:
        checked_capture = _open_live_capture(process)
        request_id_key = (
            _json_rpc_id_key(message.get("id")) if "id" in message else None
        )
        if "id" in message and (
            request_id_key is None
            or request_id_key in checked_capture._seen_request_ids
        ):
            raise ValueError("O4 App Server JSON-RPC request id is invalid or reused")
        params = message.get("params") if isinstance(message, dict) else None
        if message.get("method") == "thread/compact/start":
            source_carrier_id = (
                params.get("threadId") if isinstance(params, dict) else None
            )
            if request_id_key is None or not isinstance(source_carrier_id, str) or not (
                _measurement_start_user_chronology_valid(
                    checked_capture, source_carrier_id
                )
            ):
                raise ValueError(
                    "O4 measurement-start user chronology differs from registration"
                )
            compact_source_carrier_id = source_carrier_id
        bound = bind_snapshot_app_server_message(
            checked_capture.launch,
            checked_capture.source_binding,
            checked_capture.snapshot,
            message,
        )
    try:
        process.stdin.write(raw)
        process.stdin.flush()
    except (AttributeError, OSError) as exc:
        if isinstance(live_capture, _LiveAppServerCapture):
            live_capture._poison()
        raise ValueError("App Server request write failed") from exc
    if isinstance(live_capture, _LiveAppServerCapture) and bound is not None:
        try:
            live_capture._append_code_owned_event(
                _code_owned_capture_event(live_capture, "request-write", bound)
            )
            if compact_source_carrier_id is not None:
                live_capture.suite._bind_measurement_start_compact_request(
                    live_capture,
                    compact_source_carrier_id,
                )
        except Exception:
            live_capture._poison()
            raise


def read_snapshot_app_server_message(
    process: Any,
    launch_record: dict[str, Any],
    source_binding: dict[str, Any],
    snapshot: dict[str, Any],
    *,
    timeout: float = 30.0,
) -> dict[str, Any]:
    if (
        getattr(process, "stdout", None) is None
        or not _launch_record_valid(launch_record, source_binding, snapshot)
    ):
        raise ValueError("App Server response boundary is invalid")
    live_capture = getattr(process, "__dict__", {}).get("_o4_live_capture")
    if live_capture is not None:
        checked_capture = _open_live_capture(process)
        if (
            checked_capture.launch != launch_record
            or checked_capture.source_binding != source_binding
            or checked_capture.snapshot != snapshot
        ):
            raise ValueError("App Server response capture identity is invalid")
    capture = getattr(process, "_o4_bounded_streams", None)
    try:
        raw = (
            capture.read(timeout)
            if isinstance(capture, _BoundedAppServerStreams)
            else process.stdout.readline(MAX_APP_SERVER_MESSAGE_BYTES + 1)
        )
    except (AttributeError, OSError, ValueError) as exc:
        if isinstance(live_capture, _LiveAppServerCapture):
            live_capture._poison()
        raise ValueError("App Server response read failed") from exc
    if (
        not isinstance(raw, bytes)
        or not raw
        or len(raw) > MAX_APP_SERVER_MESSAGE_BYTES
        or not raw.endswith(b"\n")
    ):
        if isinstance(live_capture, _LiveAppServerCapture):
            live_capture._poison()
        raise ValueError("App Server response framing is invalid")
    try:
        message = v1._strict_json_object(raw[:-1])
    except (json.JSONDecodeError, RecursionError, TypeError, UnicodeError, ValueError):
        if isinstance(live_capture, _LiveAppServerCapture):
            live_capture._poison()
        raise ValueError("App Server response JSON is invalid") from None
    try:
        bound = bind_snapshot_app_server_message(
            launch_record, source_binding, snapshot, message
        )
        if live_capture is not None:
            if not isinstance(live_capture, _LiveAppServerCapture):
                raise ValueError("App Server live capture state is invalid")
            live_capture._append_code_owned_event(
                _code_owned_capture_event(live_capture, "response-read", bound)
            )
    except Exception:
        if isinstance(live_capture, _LiveAppServerCapture):
            live_capture._poison()
        raise
    return bound


def bind_snapshot_app_server_message(
    launch_record: dict[str, Any],
    source_binding: dict[str, Any],
    snapshot: dict[str, Any],
    message: dict[str, Any],
) -> dict[str, Any]:
    if (
        not _launch_record_valid(launch_record, source_binding, snapshot)
        or not isinstance(message, dict)
        or not v1._json_within_limits(message)
    ):
        raise ValueError("task-scoped App Server message boundary is invalid")
    try:
        raw = json.dumps(
            message,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (RecursionError, TypeError, ValueError) as exc:
        raise ValueError("task-scoped App Server message is invalid") from exc
    if len(raw) > 262_144:
        raise ValueError("task-scoped App Server message exceeds byte limit")
    return {
        "source": f"codex-app-server-json-rpc-v{source_binding['releaseVersion']}",
        "launchPublicIdentity": launch_record["launchPublicIdentity"],
        "message": deepcopy(message),
    }


def _open_live_capture(process: Any) -> _LiveAppServerCapture:
    state = getattr(process, "__dict__", {})
    capture = state.get("_o4_live_capture")
    if (
        state.get("_o4_native_snapshot_launch") is not True
        or not isinstance(capture, _LiveAppServerCapture)
        or capture.origin is not _LIVE_CAPTURE_ORIGIN
        or capture.poisoned
        or capture.finalized
        or capture.terminal is not None
    ):
        raise ValueError("O4 live App Server capture is unavailable")
    return capture


def _thread_read_user_message_snapshot(
    capture: _LiveAppServerCapture,
    source_carrier_id: str,
    *,
    before_compaction: bool,
    after_event_ordinal: int | None = None,
) -> dict[str, Any]:
    """Derive a private user-input chronology only from paired App Server IO."""

    if before_compaction and after_event_ordinal is not None:
        raise ValueError("O4 user chronology scope is invalid")
    requests: dict[tuple[type[int] | type[str], int | str], int] = {}
    compaction_ordinal: int | None = None
    snapshots: list[dict[str, Any]] = []
    for ordinal, (kind, record) in enumerate(capture.events):
        message = record.get("message") if isinstance(record, dict) else None
        if not isinstance(message, dict):
            continue
        if (
            kind == "request-write"
            and message.get("method") == "thread/compact/start"
            and isinstance(message.get("params"), dict)
            and message["params"].get("threadId") == source_carrier_id
        ):
            compaction_ordinal = ordinal
        if (
            kind == "request-write"
            and message.get("method") == "thread/read"
            and isinstance(message.get("params"), dict)
            and message["params"]
            == {"threadId": source_carrier_id, "includeTurns": True}
            and "id" in message
        ):
            request_id_key = _json_rpc_id_key(message["id"])
            if request_id_key is None or request_id_key in requests:
                raise ValueError("O4 thread/read JSON-RPC id is ambiguous")
            requests[request_id_key] = ordinal
            continue
        response_id_key = _json_rpc_id_key(message.get("id"))
        request_ordinal = (
            requests.pop(response_id_key, None)
            if response_id_key is not None
            else None
        )
        if kind != "response-read" or request_ordinal is None:
            continue
        result = message.get("result")
        thread = result.get("thread") if isinstance(result, dict) else None
        turns = thread.get("turns") if isinstance(thread, dict) else None
        if (
            not isinstance(thread, dict)
            or thread.get("id") != source_carrier_id
            or not isinstance(turns, list)
        ):
            raise ValueError("O4 thread/read user chronology response is invalid")
        user_message_ids: list[str] = []
        user_message_contents: list[list[dict[str, Any]]] = []
        user_message_texts: list[str] = []
        for turn in turns:
            items = turn.get("items") if isinstance(turn, dict) else None
            if not isinstance(items, list):
                raise ValueError("O4 thread/read user chronology is incomplete")
            for item in items:
                if not isinstance(item, dict) or item.get("type") != "userMessage":
                    continue
                item_id = item.get("id")
                if not isinstance(item_id, str) or not item_id:
                    raise ValueError("O4 thread/read user message identity is invalid")
                content = item.get("content")
                if not isinstance(content, list) or not content:
                    raise ValueError("O4 thread/read user message content is invalid")
                text_parts: list[str] = []
                for part in content:
                    if (
                        not isinstance(part, dict)
                        or part.get("type") != "text"
                        or not isinstance(part.get("text"), str)
                    ):
                        raise ValueError("O4 thread/read user message is not text-only")
                    text_parts.append(part["text"])
                user_message_ids.append(item_id)
                user_message_contents.append(deepcopy(content))
                user_message_texts.append("".join(text_parts))
        if len(user_message_ids) != len(set(user_message_ids)):
            raise ValueError("O4 thread/read user message chronology is ambiguous")
        snapshots.append(
            {
                "requestOrdinal": request_ordinal,
                "responseOrdinal": ordinal,
                "responseRecordSha256": v1._canonical_sha256(record),
                "userMessageIds": user_message_ids,
                "userMessageIdentitySha256": v1._canonical_sha256(user_message_ids),
                "userMessageContentIdentitySha256": v1._canonical_sha256(
                    user_message_contents
                ),
                "userMessageTexts": user_message_texts,
            }
        )
    if before_compaction:
        eligible = [
            item
            for item in snapshots
            if compaction_ordinal is not None
            and item["responseOrdinal"] < compaction_ordinal
        ]
    elif after_event_ordinal is not None:
        eligible = [
            item
            for item in snapshots
            if item["requestOrdinal"] > after_event_ordinal
            and item["responseOrdinal"] > item["requestOrdinal"]
        ]
    else:
        eligible = snapshots
    if len(eligible) != 1:
        raise ValueError("O4 source user-input chronology is unavailable or non-exact")
    return eligible[0]


def capture_source_user_chronology_baseline(
    root: Path,
    process: Any,
    source_carrier_id: str,
) -> _SourceUserChronologyBaseline:
    """Seal the source user-message history before registration and measurement."""

    capture = _open_live_capture(process)
    suite = capture.suite
    if (
        suite.registered_user_chronology_baseline is not None
        or suite.completed_scenarios
        or suite.captures != [capture]
        or any(
            isinstance(record.get("message"), dict)
            and record["message"].get("method") == "thread/compact/start"
            for record in capture.messages
        )
    ):
        raise ValueError("O4 pre-registration user chronology phase is invalid")
    snapshot = _thread_read_user_message_snapshot(
        capture, source_carrier_id, before_compaction=False
    )
    try:
        goal_bytes = root.resolve(strict=True).joinpath(
            CARRIER_GOAL_BINDING["locator"]
        ).read_bytes()
    except OSError as exc:
        raise ValueError("O4 controlled goal artifact is unavailable") from exc
    if (
        goal_bytes != v1.CARRIER_GOAL_TEXT.encode("utf-8")
        or hashlib.sha256(goal_bytes).hexdigest() != CARRIER_GOAL_BINDING["sha256"]
        or snapshot["userMessageTexts"] != [v1.CARRIER_GOAL_TEXT]
    ):
        raise ValueError("O4 pre-registration chronology is not the controlled goal start")
    value = {
        "schema": 1,
        "source": "source-bound-pre-registration-user-chronology-v1",
        "sourceCarrierIdentitySha256": v1._canonical_sha256(source_carrier_id),
        "userMessageCount": len(snapshot["userMessageIds"]),
        "userMessageIdentitySha256": snapshot["userMessageIdentitySha256"],
        "userMessageContentIdentitySha256": snapshot[
            "userMessageContentIdentitySha256"
        ],
        "controlledGoalMessageSha256": hashlib.sha256(goal_bytes).hexdigest(),
        "threadReadResponseRecordSha256": snapshot["responseRecordSha256"],
    }
    return _SourceUserChronologyBaseline(
        _CAPTURE_EVENT_ORIGIN, capture, source_carrier_id, value
    )


def _measurement_start_user_chronology_valid(
    capture: _LiveAppServerCapture,
    source_carrier_id: str,
) -> bool:
    suite = capture.suite
    if (
        capture is not suite.captures[0]
        or suite.completed_scenarios
        or suite.compaction_checkpoint_bound
        or suite._measurement_start_compact_token is not None
        or suite.registered_user_chronology_baseline is None
    ):
        return False
    try:
        current = _thread_read_user_message_snapshot(
            capture, source_carrier_id, before_compaction=False
        )
    except ValueError:
        return False
    registered = suite.registered_user_chronology_baseline
    return (
        registered.get("userMessageCount") == len(current["userMessageIds"])
        and registered.get("userMessageIdentitySha256")
        == current["userMessageIdentitySha256"]
        and registered.get("userMessageContentIdentitySha256")
        == current["userMessageContentIdentitySha256"]
        and registered.get("sourceCarrierIdentitySha256")
        == v1._canonical_sha256(source_carrier_id)
    )


def _measurement_checkpoint_user_chronology_valid(
    capture: _LiveAppServerCapture,
    source_carrier_id: str,
) -> bool:
    suite = capture.suite
    token = suite._measurement_start_compact_token
    if (
        capture is not suite.captures[0]
        or suite.completed_scenarios
        or suite.compaction_checkpoint_bound
        or not isinstance(token, _MeasurementStartCompactToken)
        or token._origin is not _CAPTURE_EVENT_ORIGIN
        or token._capture is not capture
        or token._source_carrier_id != source_carrier_id
        or suite.registered_user_chronology_baseline is None
    ):
        return False
    events = capture.events
    if token._request_ordinal >= len(events):
        return False
    kind, record = events[token._request_ordinal]
    message = record.get("message") if isinstance(record, dict) else None
    params = message.get("params") if isinstance(message, dict) else None
    if (
        kind != "request-write"
        or not isinstance(message, dict)
        or message.get("method") != "thread/compact/start"
        or not isinstance(params, dict)
        or params.get("threadId") != source_carrier_id
        or v1._canonical_sha256(record) != token._request_record_sha256
        or _json_rpc_id_key(message.get("id")) != token._request_id_key
    ):
        return False
    compact_responses: list[tuple[int, dict[str, Any]]] = []
    lifecycle_events: list[tuple[str, int, str, str, str]] = []
    for ordinal, (event_kind, event_record) in enumerate(events):
        if ordinal <= token._request_ordinal or event_kind != "response-read":
            continue
        event_message = (
            event_record.get("message") if isinstance(event_record, dict) else None
        )
        if not isinstance(event_message, dict):
            continue
        if _json_rpc_id_key(event_message.get("id")) == token._request_id_key:
            compact_responses.append((ordinal, event_message))
        method = event_message.get("method")
        event_params = event_message.get("params")
        item = event_params.get("item") if isinstance(event_params, dict) else None
        if (
            method not in {"item/started", "item/completed"}
            or not isinstance(event_params, dict)
            or event_params.get("threadId") != source_carrier_id
            or not isinstance(item, dict)
            or item.get("type") != "contextCompaction"
        ):
            continue
        turn_id = event_params.get("turnId")
        item_id = item.get("id")
        if (
            not isinstance(turn_id, str)
            or not turn_id
            or not isinstance(item_id, str)
            or not item_id
        ):
            return False
        lifecycle_events.append(
            (method, ordinal, source_carrier_id, turn_id, item_id)
        )
    if len(compact_responses) != 1:
        return False
    response_ordinal, response_message = compact_responses[0]
    if (
        response_ordinal <= token._request_ordinal
        or set(response_message) != {"id", "result"}
        or response_message.get("result") != {}
        or _json_rpc_id_key(response_message.get("id"))
        != token._request_id_key
    ):
        return False
    started = [item for item in lifecycle_events if item[0] == "item/started"]
    completed = [item for item in lifecycle_events if item[0] == "item/completed"]
    if (
        len(started) != 1
        or len(completed) != 1
        or started[0][1] <= response_ordinal
        or completed[0][1] <= started[0][1]
        or started[0][2:] != completed[0][2:]
    ):
        return False
    completed_ordinal = completed[0][1]
    try:
        current = _thread_read_user_message_snapshot(
            capture,
            source_carrier_id,
            before_compaction=False,
            after_event_ordinal=completed_ordinal,
        )
    except ValueError:
        return False
    registered = suite.registered_user_chronology_baseline
    return (
        registered.get("userMessageCount") == len(current["userMessageIds"])
        and registered.get("userMessageIdentitySha256")
        == current["userMessageIdentitySha256"]
        and registered.get("userMessageContentIdentitySha256")
        == current["userMessageContentIdentitySha256"]
        and registered.get("sourceCarrierIdentitySha256")
        == v1._canonical_sha256(source_carrier_id)
    )


def _post_reconciliation_token_usage_snapshot(
    capture: _LiveAppServerCapture,
    source_carrier_id: str,
) -> dict[str, Any] | None:
    """Return only a server-read usage notification after compaction reconciliation."""

    completed_ordinal: int | None = None
    goal_requests: dict[Any, int] = {}
    reconciliation_ordinal: int | None = None
    candidates: list[dict[str, Any]] = []
    for ordinal, (kind, record) in enumerate(capture.events):
        message = record.get("message") if isinstance(record, dict) else None
        if not isinstance(message, dict):
            continue
        params = message.get("params")
        item = params.get("item") if isinstance(params, dict) else None
        if (
            kind == "response-read"
            and message.get("method") == "item/completed"
            and isinstance(params, dict)
            and params.get("threadId") == source_carrier_id
            and isinstance(item, dict)
            and item.get("type") == "contextCompaction"
        ):
            completed_ordinal = ordinal
            continue
        if (
            kind == "request-write"
            and completed_ordinal is not None
            and ordinal > completed_ordinal
            and message.get("method") == "thread/goal/get"
            and isinstance(params, dict)
            and params.get("threadId") == source_carrier_id
            and "id" in message
        ):
            goal_requests[message["id"]] = ordinal
            continue
        if (
            kind == "response-read"
            and message.get("id") in goal_requests
            and ordinal > goal_requests[message.get("id")]
        ):
            reconciliation_ordinal = ordinal
            continue
        if (
            kind != "response-read"
            or reconciliation_ordinal is None
            or ordinal <= reconciliation_ordinal
            or message.get("method") != "thread/tokenUsage/updated"
            or not isinstance(params, dict)
            or params.get("threadId") != source_carrier_id
        ):
            continue
        token_usage = params.get("tokenUsage")
        last_usage = token_usage.get("last") if isinstance(token_usage, dict) else None
        window = (
            token_usage.get("modelContextWindow")
            if isinstance(token_usage, dict)
            else None
        )
        used = last_usage.get("totalTokens") if isinstance(last_usage, dict) else None
        if type(window) is int and type(used) is int and 0 < window and 0 <= used <= window:
            candidates.append(
                {
                    "recordOrdinal": ordinal,
                    "recordSha256": v1._canonical_sha256(record),
                    "effectiveContextWindowTokens": window,
                    "usedContextTokens": used,
                }
            )
    return candidates[-1] if candidates else None


def capture_unknown_capacity_transition_signal(
    process: Any,
    source_carrier_id: str,
) -> None:
    """Record the bound conservative transition rule before its App Server calls."""

    capture = _open_live_capture(process)
    suite = capture.suite
    if (
        suite.completed_scenarios
        != [v1.CARRIER_SCENARIO_IDENTITIES[0]]
        or capture is not suite.captures[-1]
    ):
        raise ValueError("O4 carrier-fitness source chronology is invalid")
    baseline = _thread_read_user_message_snapshot(
        suite.captures[0], source_carrier_id, before_compaction=True
    )
    current = _thread_read_user_message_snapshot(
        capture, source_carrier_id, before_compaction=False
    )
    registered_baseline = suite.registered_user_chronology_baseline
    if (
        not isinstance(registered_baseline, dict)
        or registered_baseline.get("userMessageCount")
        != len(baseline["userMessageIds"])
        or registered_baseline.get("userMessageIdentitySha256")
        != baseline["userMessageIdentitySha256"]
        or registered_baseline.get("userMessageContentIdentitySha256")
        != baseline["userMessageContentIdentitySha256"]
        or registered_baseline.get("sourceCarrierIdentitySha256")
        != v1._canonical_sha256(source_carrier_id)
    ):
        raise ValueError("O4 source user chronology differs from registration")
    user_initiated = baseline["userMessageIds"] != current["userMessageIds"]
    if user_initiated:
        raise ValueError("O4 transition followed user intervention")
    usage = _post_reconciliation_token_usage_snapshot(
        suite.captures[0], source_carrier_id
    )
    context_window = (
        usage["effectiveContextWindowTokens"] if usage is not None else None
    )
    used_context = usage["usedContextTokens"] if usage is not None else None
    used_basis_points = (
        (used_context * 10_000) // context_window
        if context_window is not None and used_context is not None
        else None
    )
    if used_basis_points is None:
        usage_band = "unknown"
    elif used_basis_points >= 8_000:
        usage_band = "immediate-transition"
    elif used_basis_points >= 6_000:
        usage_band = "transition-ready"
    else:
        usage_band = "efficient"
    capacity_observation = {
        "source": "task-bound-effective-context-window-observer-v3",
        "carrierId": source_carrier_id,
        "effectiveContextWindowTokens": context_window,
        "usedContextTokens": used_context,
        "usedContextBasisPoints": used_basis_points,
        "usageBand": usage_band,
        "tokenUsageRecordOrdinal": (
            usage["recordOrdinal"] if usage is not None else None
        ),
        "tokenUsageRecordSha256": (
            usage["recordSha256"] if usage is not None else None
        ),
        "calibrationBands": deepcopy(
            TRANSITION_AND_CLEANUP_BOUNDARY["taskScopedContextCalibrationBands"]
        ),
        "turnCountRecommendationState": "not-established-by-bound-official-source",
        "turnCountRecommendation": None,
        "automaticCompactionCount": suite.automatic_compactions,
        "manualCompactionCount": suite.manual_compactions,
        "opaqueCompactionSummaryCountProxy": (
            suite.automatic_compactions + suite.manual_compactions
        ),
        "userChronologyBaselineCount": len(baseline["userMessageIds"]),
        "userChronologyCurrentCount": len(current["userMessageIds"]),
        "userChronologyBaselineSha256": baseline["userMessageIdentitySha256"],
        "userChronologyCurrentSha256": current["userMessageIdentitySha256"],
        "userChronologyBaselineContentSha256": baseline[
            "userMessageContentIdentitySha256"
        ],
        "userChronologyCurrentContentSha256": current[
            "userMessageContentIdentitySha256"
        ],
        "sourceCarrierIdentitySha256": v1._canonical_sha256(source_carrier_id),
        "userInitiatedHandoffObserved": user_initiated,
        "agentTransitionTriggeredBeforeUserIntervention": not user_initiated,
    }
    if usage_band == "efficient":
        raise ValueError("O4 known efficient carrier does not authorize transition")
    capture._append_code_owned_event(
        _code_owned_capture_event(
            capture, "carrier-fitness-observation", capacity_observation
        )
    )
    if usage_band != "unknown":
        return
    value = {
        "source": "task-bound-carrier-fitness-observer-v1",
        "carrierId": source_carrier_id,
        "remainingCapacityState": "unknown",
        "ruleIdentity": TRANSITION_AND_CLEANUP_BOUNDARY["unknownCapacityRule"],
        "signalScope": TRANSITION_AND_CLEANUP_BOUNDARY["carrierSignalScope"],
        "compactionCountsSinceVerifiedTransition": {
            "automatic": suite.automatic_compactions,
            "manual": suite.manual_compactions,
        },
        "materialCheckpointCountSinceLastCompaction": (
            suite.checkpoints_since_compaction
        ),
        "materialCheckpointCountSinceVerifiedTransition": (
            suite.checkpoints_since_transition
        ),
        "transitionTriggered": True,
    }
    try:
        v1._carrier_fitness_observed(value, source_carrier_id=source_carrier_id)
    except (TypeError, ValueError) as exc:
        raise ValueError("O4 carrier-fitness capture is invalid") from exc
    capture._append_code_owned_event(
        _code_owned_capture_event(capture, "carrier-fitness-observation", value)
    )


def capture_repository_checkpoint(
    process: Any,
    root: Path,
    carrier_id: str,
    expected_head: str,
) -> None:
    """Execute and retain the canonical verifier and clean Git checkpoint."""

    capture = _open_live_capture(process)
    if GIT_OBJECT_PATTERN.fullmatch(expected_head) is None:
        raise ValueError("O4 checkpoint head is invalid")
    suite = capture.suite
    first_checkpoint = (
        capture is suite.captures[0]
        and not suite.compaction_checkpoint_bound
        and not suite.completed_scenarios
        and _measurement_checkpoint_user_chronology_valid(capture, carrier_id)
    )
    transition_checkpoint = (
        len(suite.captures) == 2
        and capture is suite.captures[1]
        and suite.compaction_checkpoint_bound
        and suite.completed_scenarios == [v1.CARRIER_SCENARIO_IDENTITIES[0]]
        and capture.latest_verifier_report is None
    )
    if not (first_checkpoint or transition_checkpoint):
        raise ValueError("O4 repository checkpoint chronology is invalid")
    from .control import _evidence_git, verify_product

    resolved_root = root.resolve(strict=True)
    fault_suite = run_fault_suite(resolved_root, expected_head) if first_checkpoint else None
    if first_checkpoint and (
        not isinstance(fault_suite, dict)
        or fault_suite.get("allFaultControlsObserved") is not True
        or fault_suite.get("cleanupVerified") is not True
    ):
        raise ValueError("O4 repository fault checkpoints are invalid")
    report = verify_product(resolved_root)
    states = report.get("criterionStates") if isinstance(report, dict) else None
    if (
        not isinstance(report, dict)
        or report.get("valid") is not True
        or report.get("programStatus") != "active"
        or report.get("completionState") != "in-progress"
        or report.get("activeIncrement") != INCREMENT_ID
        or report.get("errors") != []
        or not isinstance(states, dict)
        or any(states.get(item) is not True for item in ("G1", "G2", "G3", "G4"))
        or states.get("O4") is not False
    ):
        raise ValueError("O4 canonical verifier checkpoint is invalid")
    head_raw = _evidence_git(resolved_root, "rev-parse", "HEAD", max_output_bytes=128)
    status_raw = _evidence_git(
        resolved_root,
        "status",
        "--porcelain=v1",
        "--untracked-files=all",
        max_output_bytes=65_536,
    )
    try:
        head = head_raw.decode("ascii").strip() if head_raw is not None else ""
        status = status_raw.decode("utf-8") if status_raw is not None else None
    except UnicodeError as exc:
        raise ValueError("O4 Git checkpoint encoding is invalid") from exc
    git_record = {
        "source": "git-rev-parse-and-status-v1",
        "carrierId": carrier_id,
        "head": head,
        "expectedHead": expected_head,
        "statusPorcelainV1": status,
    }
    try:
        v1._git_observed(
            git_record,
            carrier_id=carrier_id,
            expected_head=expected_head,
        )
    except (TypeError, ValueError) as exc:
        raise ValueError("O4 Git checkpoint is invalid") from exc
    verifier_record = {
        "source": "python--B--m-harness-verify-json",
        "carrierId": carrier_id,
        "report": deepcopy(report),
    }
    proposed_records = [
        *capture.messages,
        verifier_record,
        git_record,
    ]
    frozen_records = _frozen_projector_records(
        proposed_records,
        capture.source_binding,
        capture.launch,
    )
    if first_checkpoint:
        reconciliation_projection = v2.project_raw_carrier_observations(
            v1.CARRIER_SCENARIO_IDENTITIES[0],
            frozen_records,
            source_carrier_id=carrier_id,
            expected_head=expected_head,
        )
    capture._append_code_owned_event(
        _code_owned_capture_event(
            capture, "canonical-verifier-checkpoint", verifier_record
        )
    )
    capture._append_code_owned_event(
        _code_owned_capture_event(capture, "git-clean-head-checkpoint", git_record)
    )
    if first_checkpoint:
        assert isinstance(fault_suite, dict)
        capture.suite.bind_compaction_checkpoint(
            capture,
            fault_suite,
            reconciliation_projection,
        )
    capture._bind_latest_verifier_report(report)


def capture_source_carrier_release_preflight(
    process: Any,
    source_carrier_id: str,
) -> None:
    """Bind source release to the immediately preceding canonical checkpoint."""

    capture = _open_live_capture(process)
    report = capture.latest_verifier_report
    release = report.get("sourceCarrierRelease") if isinstance(report, dict) else None
    if not isinstance(release, dict):
        raise ValueError("O4 source-release preflight is unavailable")
    value = {
        "source": "harness-source-carrier-release-preflight-v1",
        "carrierId": source_carrier_id,
        "report": {
            "allowed": release.get("allowed"),
            "state": release.get("state"),
        },
    }
    try:
        v1._source_release_preflight_observed(
            value,
            source_carrier_id=source_carrier_id,
        )
    except (TypeError, ValueError) as exc:
        raise ValueError("O4 source-release preflight is invalid") from exc
    capture._append_code_owned_event(
        _code_owned_capture_event(capture, "source-release-preflight", value)
    )


def snapshot_app_server_terminal_observation(
    launch_record: dict[str, Any],
    source_binding: dict[str, Any],
    snapshot: dict[str, Any],
    *,
    return_code: int,
    termination_route: str,
) -> dict[str, Any]:
    if (
        not _launch_record_valid(launch_record, source_binding, snapshot)
        or type(return_code) is not int
        or return_code != 0
        or termination_route != "stdin-close-clean-exit-after-thread-archive"
    ):
        raise ValueError("task-scoped App Server terminal state is invalid")
    return {
        "schema": 1,
        "source": "task-scoped-native-snapshot-app-server-terminal",
        "launchPublicIdentity": launch_record["launchPublicIdentity"],
        "snapshotPublicIdentity": snapshot["publicIdentity"],
        "processImageSha256": snapshot["snapshotExecutableSha256"],
        "returnCode": return_code,
        "terminationRoute": termination_route,
        "processExited": True,
    }


def close_task_scoped_snapshot_app_server(
    process: Any,
    launch_record: dict[str, Any],
    source_binding: dict[str, Any],
    snapshot: dict[str, Any],
    *,
    timeout: float = 15.0,
) -> dict[str, Any]:
    """Close stdin and require one clean exit after the caller archived the thread."""

    if (
        not _launch_record_valid(launch_record, source_binding, snapshot)
        or not isinstance(timeout, (int, float))
        or isinstance(timeout, bool)
        or timeout <= 0
        or timeout > 30
        or getattr(process, "stdin", None) is None
    ):
        raise ValueError("task-scoped App Server close boundary is invalid")
    try:
        process.stdin.close()
        return_code = process.wait(timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as exc:
        _terminate_and_close_task_scoped_process_streams(
            process,
            require_bounded_capture=getattr(
                process, "_o4_native_snapshot_launch", False
            )
            is True,
        )
        raise ValueError("task-scoped App Server did not close cleanly") from exc
    if getattr(process, "_o4_native_snapshot_launch", False) is True:
        capture = getattr(process, "_o4_bounded_streams", None)
        if not isinstance(capture, _BoundedAppServerStreams):
            raise ValueError("task-scoped App Server capture state is missing")
        try:
            poll = process.poll()
            handle = getattr(process, "_handle", None)
            try:
                handle_value = int(handle)
            except (TypeError, ValueError):
                handle_value = 0
            if poll != return_code or handle_value <= 0:
                raise ValueError("task-scoped App Server exit identity is invalid")
            if os.name == "nt" and hasattr(ctypes, "WinDLL"):
                kernel32 = ctypes.WinDLL("Kernel32.dll", use_last_error=True)
                wait_for_single = kernel32.WaitForSingleObject
                wait_for_single.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
                wait_for_single.restype = ctypes.c_uint32
                if wait_for_single(handle_value, 0) != 0:
                    raise ValueError("task-scoped App Server process is still live")
        finally:
            _finish_and_close_task_scoped_streams(
                process,
                timeout=min(timeout, 10.0),
                require_bounded_capture=True,
            )
    terminal = snapshot_app_server_terminal_observation(
        launch_record,
        source_binding,
        snapshot,
        return_code=return_code,
        termination_route="stdin-close-clean-exit-after-thread-archive",
    )
    live_capture = getattr(process, "__dict__", {}).get("_o4_live_capture")
    if live_capture is not None:
        if (
            not isinstance(live_capture, _LiveAppServerCapture)
            or live_capture.origin is not _LIVE_CAPTURE_ORIGIN
            or live_capture.poisoned
            or live_capture.finalized
            or live_capture.terminal is not None
            or live_capture.launch != launch_record
            or live_capture.source_binding != source_binding
            or live_capture.snapshot != snapshot
        ):
            raise ValueError("App Server terminal capture state is invalid")
        live_capture._bind_terminal_event(
            _code_owned_capture_event(
                live_capture, "clean-process-terminal", terminal
            )
        )
    return terminal


def finalize_live_app_server_scenario(
    process: Any,
    scenario_identity: str,
    source_binding: dict[str, Any],
    snapshot: dict[str, Any],
    source_carrier_id: str,
    expected_head: str,
    *,
    destination_carrier_id: str | None = None,
    expected_cwd: str | None = None,
) -> _CapturedAppServerScenario:
    """Close one real capture into the only outcome-bearing scenario operand."""

    state = getattr(process, "__dict__", {})
    capture = state.get("_o4_live_capture")
    if (
        state.get("_o4_native_snapshot_launch") is not True
        or not isinstance(capture, _LiveAppServerCapture)
        or capture.origin is not _LIVE_CAPTURE_ORIGIN
        or capture.poisoned
        or capture.finalized
        or capture.terminal is None
        or capture.source_binding != source_binding
        or capture.snapshot != snapshot
    ):
        raise ValueError("O4 completed live App Server capture is invalid")
    raw_observations = [
        deepcopy(capture.launch),
        deepcopy(capture.preflight),
        *deepcopy(capture.messages),
        deepcopy(capture.terminal),
    ]
    project_raw_carrier_observations(
        scenario_identity,
        raw_observations,
        source_binding=source_binding,
        snapshot=snapshot,
        source_carrier_id=source_carrier_id,
        expected_head=expected_head,
        destination_carrier_id=destination_carrier_id,
        expected_cwd=expected_cwd,
    )
    value = {
        "scenarioIdentity": scenario_identity,
        "sourceCarrierId": source_carrier_id,
        "expectedHead": expected_head,
        "destinationCarrierId": destination_carrier_id,
        "expectedCwd": expected_cwd,
        "rawObservations": raw_observations,
    }
    if not v1._json_within_limits(value):
        raise ValueError("O4 completed live App Server scenario exceeds limits")
    capture.suite.complete_capture(scenario_identity, capture)
    capture._seal(value)
    return _CapturedAppServerScenario(capture, value)


def _terminal_record_valid(
    value: Any,
    launch_record: dict[str, Any],
    source_binding: dict[str, Any],
    snapshot: dict[str, Any],
) -> bool:
    try:
        expected = snapshot_app_server_terminal_observation(
            launch_record,
            source_binding,
            snapshot,
            return_code=0,
            termination_route="stdin-close-clean-exit-after-thread-archive",
        )
    except ValueError:
        return False
    return value == expected and not v1._contains_private_value(value)


def cleanup_task_scoped_native_snapshot(
    isolate_root: Path,
    source_binding: dict[str, Any],
    snapshot: dict[str, Any],
    *,
    reason: str,
    version_probe: VersionProbe | None = None,
    signature_probe: SignatureProbe | None = None,
) -> _TaskScopedSnapshotCleanup:
    """Verify, delete and prove absence of the one exact snapshot path."""

    if reason not in SNAPSHOT_TERMINAL_REASONS:
        raise ValueError("task-scoped native snapshot cleanup reason is invalid")
    root = isolate_root.resolve(strict=True)
    target = verified_task_scoped_snapshot_executable(
        root,
        source_binding,
        snapshot,
        version_probe=version_probe,
        signature_probe=signature_probe,
    )
    snapshot_parent = target.parent
    target.unlink()
    try:
        target.lstat()
    except FileNotFoundError:
        pass
    else:
        raise RuntimeError("task-scoped native snapshot still exists after cleanup")
    if _is_reparse_or_symlink(snapshot_parent):
        raise RuntimeError("task-scoped native snapshot parent became unsafe")
    snapshot_parent.rmdir()
    if snapshot_parent.exists():
        raise RuntimeError("task-scoped native snapshot parent still exists")
    harness_parent = snapshot_parent.parent
    if harness_parent == root / ".harness" and harness_parent.exists():
        if _is_reparse_or_symlink(harness_parent):
            raise RuntimeError("task-scoped native snapshot container became unsafe")
        try:
            harness_parent.rmdir()
        except OSError:
            # The exact O4 snapshot is gone; another authorized task-owned
            # resource may still share the private container.
            pass
    record = {
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
    if not _snapshot_cleanup_record_valid(record, snapshot):
        raise RuntimeError("task-scoped native snapshot cleanup record is invalid")
    return _TaskScopedSnapshotCleanup(record, root)


def _snapshot_cleanup_record_valid(value: Any, snapshot: dict[str, Any]) -> bool:
    if not isinstance(value, dict):
        return False
    reason = value.get("reason")
    return value == {
        "schema": 1,
        "source": "task-scoped-native-snapshot-terminal-cleanup",
        "snapshotPublicIdentity": snapshot["publicIdentity"],
        "snapshotSha256": snapshot["snapshotExecutableSha256"],
        "reason": reason,
        "snapshotPresentBeforeCleanup": True,
        "snapshotAbsentAfterCleanup": True,
        "taskParentAbsentAfterCleanup": True,
        "privatePathPublished": False,
    } and reason in SNAPSHOT_TERMINAL_REASONS and not v1._contains_private_value(value)


def _snapshot_preflight_observed(
    value: Any,
    source_binding: dict[str, Any],
    snapshot: dict[str, Any],
) -> dict[str, Any]:
    expected = {
        "source": "task-scoped-native-snapshot-preflight",
        "snapshotPublicIdentity": snapshot["publicIdentity"],
        "releaseVersion": source_binding["releaseVersion"],
        "registeredSha256": snapshot["snapshotExecutableSha256"],
        "observedExecutableSha256": snapshot["snapshotExecutableSha256"],
        "observedExecutableBytes": snapshot["snapshotExecutableBytes"],
        "versionOutput": snapshot["snapshotVersionOutput"],
        "ambientExecutableUsed": False,
    }
    if value != expected or v1._contains_private_value(value):
        raise ValueError("task-scoped native snapshot preflight is invalid")
    return {
        "publicIdentity": snapshot["publicIdentity"],
        "releaseVersion": source_binding["releaseVersion"],
        "sha256": snapshot["snapshotExecutableSha256"],
        "bytes": snapshot["snapshotExecutableBytes"],
        "verifiedBeforeHostProcess": True,
        "ambientExecutableUsed": False,
    }


def _frozen_projector_records(
    records: list[dict[str, Any]],
    source_binding: dict[str, Any],
    launch_record: dict[str, Any],
) -> list[dict[str, Any]]:
    dynamic_source = f"codex-app-server-json-rpc-v{source_binding['releaseVersion']}"
    copied: list[dict[str, Any]] = []
    app_server_records = 0
    thread_read_ids = {
        item.get("message", {}).get("id")
        for item in records
        if isinstance(item, dict)
        and isinstance(item.get("message"), dict)
        and item["message"].get("method") == "thread/read"
        and "id" in item["message"]
    }
    for item in deepcopy(records):
        if (
            isinstance(item, dict)
            and item.get("source")
            == "task-bound-effective-context-window-observer-v3"
        ):
            if item.get("usageBand") in {
                "transition-ready",
                "immediate-transition",
            }:
                copied.append(
                    {
                        "source": "task-bound-carrier-fitness-observer-v1",
                        "carrierId": item.get("carrierId"),
                        "remainingCapacityState": "unknown",
                        "ruleIdentity": TRANSITION_AND_CLEANUP_BOUNDARY[
                            "unknownCapacityRule"
                        ],
                        "signalScope": TRANSITION_AND_CLEANUP_BOUNDARY[
                            "carrierSignalScope"
                        ],
                        "compactionCountsSinceVerifiedTransition": {
                            "automatic": item.get("automaticCompactionCount"),
                            "manual": item.get("manualCompactionCount"),
                        },
                        "materialCheckpointCountSinceLastCompaction": 7,
                        "materialCheckpointCountSinceVerifiedTransition": 7,
                        "transitionTriggered": True,
                    }
                )
            continue
        if isinstance(item, dict) and isinstance(item.get("source"), str) and (
            item["source"].startswith("codex-app-server-json-rpc-v")
        ):
            if (
                set(item) != {"source", "launchPublicIdentity", "message"}
                or item.get("source") != dynamic_source
                or item.get("launchPublicIdentity")
                != launch_record["launchPublicIdentity"]
            ):
                raise ValueError("raw App Server process binding is invalid")
            if (
                isinstance(item.get("message"), dict)
                and (
                    item["message"].get("method") == "thread/read"
                    or (
                        item["message"].get("id") in thread_read_ids
                        and "method" not in item["message"]
                    )
                )
            ):
                continue
            if (
                isinstance(item.get("message"), dict)
                and item["message"].get("method")
                == "thread/tokenUsage/updated"
            ):
                continue
            copied.append(
                {
                    "source": "codex-app-server-json-rpc-v0.147.0",
                    "message": item.get("message"),
                }
            )
            app_server_records += 1
        else:
            copied.append(item)
    if app_server_records == 0:
        raise ValueError("raw App Server process binding is absent")
    verifier_reports = [
        item.get("report")
        for item in copied
        if isinstance(item, dict)
        and item.get("source") == "python--B--m-harness-verify-json"
    ]
    if (
        len(verifier_reports) != 1
        or not isinstance(verifier_reports[0], dict)
        or verifier_reports[0].get("activeIncrement") != INCREMENT_ID
    ):
        raise ValueError("raw canonical verifier observation has wrong O4 generation")
    verifier_reports[0]["activeIncrement"] = v2.INCREMENT_ID
    return copied


def project_raw_carrier_observations(
    scenario_identity: str,
    raw_observations: list[dict[str, Any]],
    *,
    source_binding: dict[str, Any],
    snapshot: dict[str, Any],
    source_carrier_id: str,
    expected_head: str,
    destination_carrier_id: str | None = None,
    expected_cwd: str | None = None,
) -> dict[str, Any]:
    """Project one snapshot-owned process lifecycle plus a frozen chronology."""

    if (
        not official_source_binding_valid(source_binding)
        or not snapshot_record_valid(snapshot, source_binding)
        or not isinstance(raw_observations, list)
        or len(raw_observations) < 4
        or not v1._json_within_limits(raw_observations)
    ):
        raise ValueError("raw third-generation carrier binding is invalid")
    launch_record = raw_observations[0]
    terminal_record = raw_observations[-1]
    if (
        not _launch_record_valid(launch_record, source_binding, snapshot)
        or not _terminal_record_valid(
            terminal_record, launch_record, source_binding, snapshot
        )
    ):
        raise ValueError("raw task-scoped App Server lifecycle is invalid")
    native_projection = _snapshot_preflight_observed(
        raw_observations[1], source_binding, snapshot
    )
    native_projection.update(
        {
            "launchPublicIdentity": launch_record["launchPublicIdentity"],
            "processImageSha256": launch_record["processImageSha256"],
            "snapshotOwnedAppServerLaunch": True,
        }
    )
    captured_records = raw_observations[2:-1]
    copied = _frozen_projector_records(
        captured_records,
        source_binding,
        launch_record,
    )
    carrier_projection = v2.project_raw_carrier_observations(
        scenario_identity,
        copied,
        source_carrier_id=source_carrier_id,
        expected_head=expected_head,
        destination_carrier_id=destination_carrier_id,
        expected_cwd=expected_cwd,
    )
    if carrier_projection.get("codexSourceBinding") != v1.CODEX_SOURCE_BINDING:
        raise ValueError("frozen carrier projector source binding drifted")
    material_checkpoint_evidence: dict[str, Any] | None = None
    context_usage_evidence: dict[str, Any] | None = None
    carrier_decision_evidence: dict[str, Any] | None = None
    if scenario_identity == v1.CARRIER_SCENARIO_IDENTITIES[0]:
        verifier_records = [
            item
            for item in captured_records
            if item.get("source") == "python--B--m-harness-verify-json"
        ]
        git_records = [
            item
            for item in captured_records
            if item.get("source") == "git-rev-parse-and-status-v1"
        ]
        if len(verifier_records) != 1 or len(git_records) != 1:
            raise ValueError("compaction checkpoint records are not exact")
        report = verifier_records[0].get("report")
        git_head = git_records[0].get("head")
        if not isinstance(report, dict) or not isinstance(git_head, str):
            raise ValueError("compaction checkpoint record identity is invalid")
        material_checkpoint_evidence = {
            "schema": 1,
            "reconciliationEventShapeSha256": carrier_projection.get(
                "eventShapeSha256"
            ),
            "verifierRecordSha256": v1._canonical_sha256(verifier_records[0]),
            "verifierReportSha256": v1._canonical_sha256(report),
            "gitRecordSha256": v1._canonical_sha256(git_records[0]),
            "gitHead": git_head,
        }
        compaction_index: int | None = None
        reconciliation_index: int | None = None
        goal_request_ids: set[Any] = set()
        usage_candidates: list[dict[str, Any]] = []
        for index, record in enumerate(captured_records):
            message = record.get("message") if isinstance(record, dict) else None
            params = message.get("params") if isinstance(message, dict) else None
            item = params.get("item") if isinstance(params, dict) else None
            if (
                isinstance(message, dict)
                and message.get("method") == "item/completed"
                and isinstance(params, dict)
                and params.get("threadId") == source_carrier_id
                and isinstance(item, dict)
                and item.get("type") == "contextCompaction"
            ):
                compaction_index = index
            elif (
                isinstance(message, dict)
                and compaction_index is not None
                and index > compaction_index
                and message.get("method") == "thread/goal/get"
                and isinstance(params, dict)
                and params.get("threadId") == source_carrier_id
                and "id" in message
            ):
                goal_request_ids.add(message["id"])
            elif (
                isinstance(message, dict)
                and message.get("id") in goal_request_ids
                and isinstance(message.get("result"), dict)
            ):
                reconciliation_index = index
            elif (
                isinstance(message, dict)
                and reconciliation_index is not None
                and index > reconciliation_index
                and message.get("method") == "thread/tokenUsage/updated"
                and isinstance(params, dict)
                and params.get("threadId") == source_carrier_id
            ):
                token_usage = params.get("tokenUsage")
                last_usage = (
                    token_usage.get("last") if isinstance(token_usage, dict) else None
                )
                window = (
                    token_usage.get("modelContextWindow")
                    if isinstance(token_usage, dict)
                    else None
                )
                used = (
                    last_usage.get("totalTokens")
                    if isinstance(last_usage, dict)
                    else None
                )
                if (
                    type(window) is int
                    and type(used) is int
                    and 0 < window
                    and 0 <= used <= window
                ):
                    usage_candidates.append(
                        {
                            "schema": 1,
                            "recordOrdinal": index,
                            "recordSha256": v1._canonical_sha256(record),
                            "effectiveContextWindowTokens": window,
                            "usedContextTokens": used,
                        }
                    )
        context_usage_evidence = usage_candidates[-1] if usage_candidates else None
    else:
        decision_records = [
            item
            for item in captured_records
            if item.get("source")
            == "task-bound-effective-context-window-observer-v3"
        ]
        if len(decision_records) > 1:
            raise ValueError("carrier decision observation is not exact")
        if decision_records:
            carrier_decision_evidence = {
                key: deepcopy(item)
                for key, item in decision_records[0].items()
                if key != "carrierId"
            }
            usage_band = carrier_decision_evidence.get("usageBand")
            if usage_band in {"transition-ready", "immediate-transition"}:
                sequence = carrier_projection.get("eventSequence")
                if (
                    not isinstance(sequence, list)
                    or not sequence
                    or sequence[0].get("eventClass")
                    != "capacity-risk-or-unknown-rule-triggered"
                ):
                    raise ValueError("known carrier transition base projection is invalid")
                sequence[0]["eventClass"] = "known-client-effective-context-band-triggered"
                sequence[0]["state"] = usage_band
                carrier_projection["sourceFormat"] = (
                    "public-safe-codex-app-server-goal-observation-v3"
                )
                carrier_projection["eventShapeSha256"] = v1._canonical_sha256(
                    sequence
                )
    carrier_projection["codexSourceBinding"] = deepcopy(source_binding)
    return {
        "schema": 1,
        "scenarioIdentity": scenario_identity,
        "nativeExecutionSnapshot": native_projection,
        "processLifecycle": {
            "launch": deepcopy(launch_record),
            "terminal": deepcopy(terminal_record),
        },
        "materialCheckpointEvidence": material_checkpoint_evidence,
        "contextUsageEvidence": context_usage_evidence,
        "carrierDecisionEvidence": carrier_decision_evidence,
        "carrierProjection": carrier_projection,
    }


def _replay_private_measurement_value(
    value: Any,
    source_binding: dict[str, Any],
    snapshot: dict[str, Any],
    source_revision: str,
    baseline_revision: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]] | None:
    if (
        not isinstance(value, dict)
        or set(value)
        != {
            "schema",
            "suiteIdentity",
            "state",
            "sourceBinding",
            "snapshotBinding",
            "registrationSourceRevision",
            "measurementBaselineRevision",
            "scenarios",
            "snapshotCleanup",
        }
        or type(value.get("schema")) is not int
        or value.get("schema") != 1
        or value.get("suiteIdentity") != SUITE_IDENTITY
        or value.get("state") != "measurement-complete-live-private-source"
        or value.get("sourceBinding") != source_binding
        or value.get("snapshotBinding") != snapshot
        or value.get("registrationSourceRevision") != source_revision
        or value.get("measurementBaselineRevision") != baseline_revision
        or GIT_OBJECT_PATTERN.fullmatch(source_revision) is None
        or GIT_OBJECT_PATTERN.fullmatch(baseline_revision) is None
        or not v1._json_within_limits(value)
    ):
        return None
    scenarios = value.get("scenarios")
    cleanup = value.get("snapshotCleanup")
    if (
        not isinstance(scenarios, list)
        or len(scenarios) != 2
        or not _snapshot_cleanup_record_valid(cleanup, snapshot)
        or cleanup.get("reason") != "accepted"
    ):
        return None
    projections: list[dict[str, Any]] = []
    for index, item in enumerate(scenarios):
        expected_scenario = v1.CARRIER_SCENARIO_IDENTITIES[index]
        if (
            not isinstance(item, dict)
            or set(item)
            != {
                "scenarioIdentity",
                "sourceCarrierId",
                "expectedHead",
                "destinationCarrierId",
                "expectedCwd",
                "rawObservations",
            }
            or item.get("scenarioIdentity") != expected_scenario
            or not isinstance(item.get("sourceCarrierId"), str)
            or not isinstance(item.get("expectedHead"), str)
            or item.get("expectedHead") != baseline_revision
            or not isinstance(item.get("rawObservations"), list)
            or not v1._json_within_limits(item["rawObservations"])
        ):
            return None
        is_transition = index == 1
        destination = item.get("destinationCarrierId")
        expected_cwd = item.get("expectedCwd")
        if is_transition:
            if not isinstance(destination, str) or not isinstance(expected_cwd, str):
                return None
        elif destination is not None or expected_cwd is not None:
            return None
        try:
            projection = project_raw_carrier_observations(
                expected_scenario,
                item["rawObservations"],
                source_binding=source_binding,
                snapshot=snapshot,
                source_carrier_id=item["sourceCarrierId"],
                expected_head=item["expectedHead"],
                destination_carrier_id=destination,
                expected_cwd=expected_cwd,
            )
        except (RecursionError, TypeError, ValueError):
            return None
        projections.append(projection)
    if len(
        {
            item["processLifecycle"]["launch"]["launchPublicIdentity"]
            for item in projections
        }
    ) != 2:
        return None
    return projections, cleanup


def _load_private_measurement(
    private_root: Path,
    source_binding: dict[str, Any],
    snapshot: dict[str, Any],
    source_revision: str,
    baseline_revision: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]] | None:
    try:
        root = private_root.resolve(strict=True)
        if not root.is_dir() or _is_reparse_or_symlink(root):
            return None
        path = root.joinpath(*PRIVATE_MEASUREMENT_RELATIVE_PARTS)
        resolved = path.resolve(strict=True)
        if (
            resolved != path
            or not resolved.is_relative_to(root)
            or _is_reparse_or_symlink(resolved)
            or not resolved.is_file()
            or resolved.stat().st_size > MAX_PRIVATE_MEASUREMENT_BYTES
        ):
            return None
        value = v1._strict_json_object(resolved.read_bytes())
    except (
        json.JSONDecodeError,
        OSError,
        RecursionError,
        RuntimeError,
        TypeError,
        UnicodeError,
        ValueError,
    ):
        return None
    return _replay_private_measurement_value(
        value,
        source_binding,
        snapshot,
        source_revision,
        baseline_revision,
    )


def persist_private_measurement(
    private_root: Path,
    source_binding: dict[str, Any],
    snapshot: dict[str, Any],
    source_revision: str,
    baseline_revision: str,
    scenarios: list[dict[str, Any]],
    snapshot_cleanup: dict[str, Any],
) -> None:
    root = private_root.resolve(strict=True)
    if (
        not root.is_dir()
        or _is_reparse_or_symlink(root)
        or any(root.iterdir())
    ):
        raise ValueError("private O4 measurement root is invalid")
    value = {
        "schema": 1,
        "suiteIdentity": SUITE_IDENTITY,
        "state": "measurement-complete-live-private-source",
        "sourceBinding": deepcopy(source_binding),
        "snapshotBinding": deepcopy(snapshot),
        "registrationSourceRevision": source_revision,
        "measurementBaselineRevision": baseline_revision,
        "scenarios": deepcopy(scenarios),
        "snapshotCleanup": deepcopy(snapshot_cleanup),
    }
    if (
        _replay_private_measurement_value(
            value,
            source_binding,
            snapshot,
            source_revision,
            baseline_revision,
        )
        is None
    ):
        raise ValueError("private O4 measurement replay is invalid")
    raw = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8") + b"\n"
    if len(raw) > MAX_PRIVATE_MEASUREMENT_BYTES:
        raise ValueError("private O4 measurement exceeds byte limit")
    path = root.joinpath(*PRIVATE_MEASUREMENT_RELATIVE_PARTS)
    if path.exists():
        raise ValueError("private O4 measurement already exists")
    try:
        with path.open("xb") as stream:
            stream.write(raw)
        if (
            _load_private_measurement(
                root,
                source_binding,
                snapshot,
                source_revision,
                baseline_revision,
            )
            is None
        ):
            raise ValueError("private O4 measurement persistence replay failed")
    except Exception as original_error:
        try:
            if path.exists():
                if _is_reparse_or_symlink(path) or not path.is_file():
                    raise OSError("unsafe private O4 measurement residue")
                path.unlink()
            if root.exists() and not any(root.iterdir()):
                root.rmdir()
        except OSError as cleanup_error:
            raise RuntimeError(
                "private O4 measurement failure cleanup did not close"
            ) from cleanup_error
        raise original_error


def cleanup_private_measurement(
    private_root: Path,
    snapshot: dict[str, Any],
    *,
    reason: str,
) -> dict[str, Any]:
    if reason not in PRIVATE_SOURCE_TERMINAL_REASONS:
        raise ValueError("private O4 measurement cleanup reason is invalid")
    root = private_root.resolve(strict=True)
    if not root.is_dir() or _is_reparse_or_symlink(root):
        raise ValueError("private O4 measurement root is invalid")
    path = root.joinpath(*PRIVATE_MEASUREMENT_RELATIVE_PARTS)
    resolved = path.resolve(strict=True)
    if (
        resolved != path
        or not resolved.is_relative_to(root)
        or _is_reparse_or_symlink(resolved)
        or not resolved.is_file()
    ):
        raise ValueError("private O4 measurement resource is invalid")
    resolved.unlink()
    try:
        resolved.lstat()
    except FileNotFoundError:
        pass
    else:
        raise RuntimeError("private O4 measurement still exists after cleanup")
    if any(root.iterdir()):
        raise RuntimeError("private O4 measurement root contains unexpected residue")
    root.rmdir()
    if root.exists():
        raise RuntimeError("private O4 measurement root still exists after cleanup")
    return {
        "schema": 1,
        "source": "private-o4-measurement-terminal-cleanup",
        "snapshotPublicIdentity": snapshot["publicIdentity"],
        "reason": reason,
        "privateMeasurementAbsentAfterCleanup": True,
        "privateRootAbsentAfterCleanup": True,
        "privatePathPublished": False,
    }


def _private_measurement_cleanup_record_valid(
    value: Any, snapshot: dict[str, Any]
) -> bool:
    return value == {
        "schema": 1,
        "source": "private-o4-measurement-terminal-cleanup",
        "snapshotPublicIdentity": snapshot.get("publicIdentity"),
        "reason": "accepted",
        "privateMeasurementAbsentAfterCleanup": True,
        "privateRootAbsentAfterCleanup": True,
        "privatePathPublished": False,
    }


def _isolate_cleanup_record_valid(value: Any, snapshot: dict[str, Any]) -> bool:
    return value == {
        "schema": 1,
        "source": "authorized-o4-v3-isolated-codex-home-terminal-cleanup",
        "snapshotPublicIdentity": snapshot.get("publicIdentity"),
        "reason": "accepted",
        "isolatedCodexHomeAbsentAfterCleanup": True,
        "privatePathPublished": False,
    }


def _attestation_key_cleanup_record_valid(
    value: Any, attestation_binding: dict[str, Any]
) -> bool:
    return value == {
        "schema": 1,
        "source": "o4-capture-attestation-key-terminal-cleanup",
        "publicIdentity": attestation_binding.get("publicIdentity"),
        "publicKeyFingerprint": attestation_binding.get("publicKeyFingerprint"),
        "reason": "accepted",
        "privateKeyAbsentAfterCleanup": True,
        "privateRootAbsentAfterCleanup": True,
        "privatePathPublished": False,
    }


def _material_checkpoint_binding_valid(
    value: Any,
    fault_suite: Any,
    baseline_revision: str,
    projections: Any,
) -> bool:
    if (
        not isinstance(value, dict)
        or set(value)
        != {
            "schema",
            "checkpointIdentities",
            "materialCheckpointCount",
            "faultSuiteSha256",
            "reconciliationEventShapeSha256",
            "verifierRecordSha256",
            "verifierReportSha256",
            "gitRecordSha256",
            "gitHead",
        }
        or value.get("schema") != 1
        or value.get("materialCheckpointCount") != 7
        or value.get("gitHead") != baseline_revision
        or GIT_OBJECT_PATTERN.fullmatch(baseline_revision) is None
        or not isinstance(fault_suite, dict)
        or value.get("faultSuiteSha256") != v1._canonical_sha256(fault_suite)
        or not isinstance(projections, list)
        or len(projections) != 2
    ):
        return False
    for field in (
        "faultSuiteSha256",
        "reconciliationEventShapeSha256",
        "verifierRecordSha256",
        "verifierReportSha256",
        "gitRecordSha256",
    ):
        item = value.get(field)
        if not isinstance(item, str) or SHA256_PATTERN.fullmatch(item) is None:
            return False
    results = fault_suite.get("faultScenarioResults")
    if not isinstance(results, list):
        return False
    fault_checkpoints = [
        "fault-recovery:"
        + str(item.get("scenarioIdentity"))
        + ":"
        + str(item.get("faultReportSha256"))
        + ":"
        + str(item.get("recoveryReportSha256"))
        for item in results
        if isinstance(item, dict)
    ]
    identities = value.get("checkpointIdentities")
    expected = [
        *fault_checkpoints,
        "post-compaction-goal-authority-reconciliation-v1:"
        + value["reconciliationEventShapeSha256"],
        "canonical-verifier:" + value["verifierReportSha256"],
        "git-clean-head:" + baseline_revision,
    ]
    compaction_evidence = (
        projections[0].get("materialCheckpointEvidence")
        if isinstance(projections[0], dict)
        else None
    )
    transition_evidence = (
        projections[1].get("materialCheckpointEvidence")
        if isinstance(projections[1], dict)
        else None
    )
    expected_evidence = {
        "schema": 1,
        "reconciliationEventShapeSha256": value.get(
            "reconciliationEventShapeSha256"
        ),
        "verifierRecordSha256": value.get("verifierRecordSha256"),
        "verifierReportSha256": value.get("verifierReportSha256"),
        "gitRecordSha256": value.get("gitRecordSha256"),
        "gitHead": baseline_revision,
    }
    context_evidence = (
        projections[0].get("contextUsageEvidence")
        if isinstance(projections[0], dict)
        else None
    )
    decision_evidence = (
        projections[1].get("carrierDecisionEvidence")
        if isinstance(projections[1], dict)
        else None
    )
    usage_binding_matches = isinstance(decision_evidence, dict) and (
        (
            context_evidence is None
            and decision_evidence.get("effectiveContextWindowTokens") is None
            and decision_evidence.get("usedContextTokens") is None
            and decision_evidence.get("tokenUsageRecordOrdinal") is None
            and decision_evidence.get("tokenUsageRecordSha256") is None
        )
        or (
            isinstance(context_evidence, dict)
            and decision_evidence.get("effectiveContextWindowTokens")
            == context_evidence.get("effectiveContextWindowTokens")
            and decision_evidence.get("usedContextTokens")
            == context_evidence.get("usedContextTokens")
            and decision_evidence.get("tokenUsageRecordOrdinal")
            == context_evidence.get("recordOrdinal")
            and decision_evidence.get("tokenUsageRecordSha256")
            == context_evidence.get("recordSha256")
        )
    )
    return (
        len(fault_checkpoints) == len(FAULT_SCENARIOS)
        and identities == expected
        and len(set(expected)) == 7
        and compaction_evidence == expected_evidence
        and transition_evidence is None
        and usage_binding_matches
        and not v1._contains_private_value(value)
    )


def _measurement_attestation_payload(
    source_revision: str,
    baseline_revision: str,
    source_binding: dict[str, Any],
    snapshot: dict[str, Any],
    projections: list[dict[str, Any]],
    fault_suite: dict[str, Any],
    material_checkpoint_binding: dict[str, Any],
    snapshot_cleanup: dict[str, Any],
) -> dict[str, Any]:
    value = {
        "schema": 1,
        "kind": "o4-v3-public-measurement-after-registration",
        "suiteIdentity": SUITE_IDENTITY,
        "registrationSourceRevision": source_revision,
        "measurementBaselineRevision": baseline_revision,
        "sourceBinding": deepcopy(source_binding),
        "snapshotBinding": deepcopy(snapshot),
        "faultSuite": deepcopy(fault_suite),
        "materialCheckpointBinding": deepcopy(material_checkpoint_binding),
        "carrierProjections": deepcopy(projections),
        "claimCeiling": CLAIM_CEILING,
        "cleanupVerified": True,
        "snapshotCleanup": deepcopy(snapshot_cleanup),
    }
    if (
        GIT_OBJECT_PATTERN.fullmatch(source_revision) is None
        or GIT_OBJECT_PATTERN.fullmatch(baseline_revision) is None
        or not official_source_binding_valid(source_binding)
        or not snapshot_record_valid(snapshot, source_binding)
        or not isinstance(projections, list)
        or not isinstance(fault_suite, dict)
        or not _material_checkpoint_binding_valid(
            material_checkpoint_binding,
            fault_suite,
            baseline_revision,
            projections,
        )
        or not _snapshot_cleanup_record_valid(snapshot_cleanup, snapshot)
        or snapshot_cleanup.get("reason") != "accepted"
        or not v1._json_within_limits(value)
        or v1._contains_private_value(value)
    ):
        raise ValueError("O4 public measurement attestation payload is invalid")
    return value


def _terminal_cleanup_attestation_payload(
    attestation_binding: dict[str, Any],
    measurement_attestation: dict[str, Any],
    private_measurement_cleanup: dict[str, Any],
    isolate_cleanup: dict[str, Any],
    snapshot: dict[str, Any],
) -> dict[str, Any]:
    if (
        not _attestation_public_key_valid(attestation_binding)
        or not isinstance(measurement_attestation, dict)
        or not _private_measurement_cleanup_record_valid(
            private_measurement_cleanup, snapshot
        )
        or not _isolate_cleanup_record_valid(isolate_cleanup, snapshot)
    ):
        raise ValueError("O4 terminal cleanup attestation input is invalid")
    return {
        "schema": 1,
        "kind": "o4-v3-terminal-private-resource-cleanup",
        "suiteIdentity": SUITE_IDENTITY,
        "measurementAttestation": deepcopy(measurement_attestation),
        "privateMeasurementCleanup": deepcopy(private_measurement_cleanup),
        "isolatedCodexHomeCleanup": deepcopy(isolate_cleanup),
        "attestationKeyCleanupCommitment": {
            "publicIdentity": attestation_binding["publicIdentity"],
            "publicKeyFingerprint": attestation_binding["publicKeyFingerprint"],
            "reason": "accepted",
            "privateKeyAndRootMustBeAbsentBeforeEvidenceCommit": True,
        },
    }


def finalize_public_measurement_observation(
    pending: _PendingMeasurementFinalization,
) -> dict[str, Any]:
    """Delete all exact private resources, then emit the portable signed result."""

    if (
        not isinstance(pending, _PendingMeasurementFinalization)
        or pending._origin is not _LIVE_CAPTURE_ORIGIN
        or pending._consumed
    ):
        raise ValueError("O4 pending finalization identity is invalid")
    pending._consumed = True
    measurement_document = deepcopy(pending._measurement_document)
    attestation_binding = deepcopy(pending._attestation_binding)
    raw_path = pending._private_raw_root
    isolate_path = pending._isolate_root
    key_path = pending._private_key_root
    snapshot = measurement_document.get("snapshotBinding")
    root_paths = (raw_path, isolate_path, key_path)
    root_locks = list(pending._root_locks)
    try:
        if not isinstance(snapshot, dict):
            raise ValueError("O4 terminal snapshot binding is invalid")
        for lock in root_locks:
            lock.verify()
        if (
            tuple(lock.identity for lock in root_locks)
            != pending._root_identities
            or tuple(
                _private_resource_tree_identity(path) for path in root_paths
            )
            != pending._tree_identities
        ):
            raise RuntimeError("O4 terminal private resource identity drifted")
        measurement_payload = _measurement_attestation_payload(
            measurement_document.get("registrationSourceRevision"),
            measurement_document.get("measurementBaselineRevision"),
            measurement_document.get("sourceBinding"),
            snapshot,
            measurement_document.get("carrierProjections"),
            measurement_document.get("faultSuite"),
            measurement_document.get("materialCheckpointBinding"),
            measurement_document.get("snapshotCleanup"),
        )
        measurement_attestation = measurement_document.get("captureAttestation")
        if not verify_task_attestation(
            attestation_binding,
            measurement_payload,
            measurement_attestation,
        ):
            raise ValueError("O4 measurement attestation is invalid before cleanup")
        _dispose_locked_private_tree(root_locks[0], pending._tree_identities[0])
        _dispose_locked_private_tree(root_locks[1], pending._tree_identities[1])
        private_measurement_cleanup = {
            "schema": 1,
            "source": "private-o4-measurement-terminal-cleanup",
            "snapshotPublicIdentity": snapshot["publicIdentity"],
            "reason": "accepted",
            "privateMeasurementAbsentAfterCleanup": True,
            "privateRootAbsentAfterCleanup": True,
            "privatePathPublished": False,
        }
        isolate_cleanup = {
            "schema": 1,
            "source": "authorized-o4-v3-isolated-codex-home-terminal-cleanup",
            "snapshotPublicIdentity": snapshot["publicIdentity"],
            "reason": "accepted",
            "isolatedCodexHomeAbsentAfterCleanup": True,
            "privatePathPublished": False,
        }
        terminal_payload = _terminal_cleanup_attestation_payload(
            attestation_binding,
            measurement_attestation,
            private_measurement_cleanup,
            isolate_cleanup,
            snapshot,
        )
        terminal_cleanup_attestation = _sign_task_attestation(
            key_path,
            attestation_binding,
            terminal_payload,
        )
        if _private_resource_tree_identity(key_path) != pending._tree_identities[2]:
            raise RuntimeError("O4 attestation key tree drifted during finalization")
        _dispose_locked_private_tree(root_locks[2], pending._tree_identities[2])
        key_cleanup = {
            "schema": 1,
            "source": "o4-capture-attestation-key-terminal-cleanup",
            "publicIdentity": attestation_binding["publicIdentity"],
            "publicKeyFingerprint": attestation_binding["publicKeyFingerprint"],
            "reason": "accepted",
            "privateKeyAbsentAfterCleanup": True,
            "privateRootAbsentAfterCleanup": True,
            "privatePathPublished": False,
        }
        if (
            not verify_task_attestation(
                attestation_binding,
                terminal_payload,
                terminal_cleanup_attestation,
            )
            or not _attestation_key_cleanup_record_valid(
                key_cleanup,
                attestation_binding,
            )
        ):
            raise ValueError("O4 terminal private-resource cleanup is not verifiable")
        result = {
            **deepcopy(measurement_document),
            "privateMeasurementCleanup": deepcopy(private_measurement_cleanup),
            "isolatedCodexHomeCleanup": deepcopy(isolate_cleanup),
            "terminalCleanupAttestation": deepcopy(terminal_cleanup_attestation),
            "attestationKeyCleanup": deepcopy(key_cleanup),
        }
        if v1._contains_private_value(result) or not v1._json_within_limits(result):
            raise ValueError("O4 public observation retained private material")
        if raw_path.exists() or isolate_path.exists() or key_path.exists():
            raise RuntimeError("O4 terminal private resource remained after cleanup")
        return result
    except Exception as original_error:
        cleanup_errors: list[Exception] = []
        for lock, expected_tree in zip(
            root_locks, pending._tree_identities, strict=True
        ):
            if lock.disposed:
                continue
            try:
                _dispose_locked_private_tree(lock, expected_tree)
            except Exception as cleanup_error:
                cleanup_errors.append(cleanup_error)
        for lock in root_locks:
            if lock._handle is None:
                continue
            try:
                lock.release()
            except Exception as cleanup_error:
                cleanup_errors.append(cleanup_error)
        if cleanup_errors:
            raise RuntimeError(
                "O4 terminal finalization failed with task-owned residue"
            ) from cleanup_errors[0]
        raise original_error


def persist_and_attest_private_measurement(
    root: Path,
    private_raw_root: Path,
    private_key_root: Path,
    source_binding: dict[str, Any],
    snapshot: dict[str, Any],
    attestation_binding: dict[str, Any],
    baseline_revision: str,
    scenarios: list[_CapturedAppServerScenario],
    snapshot_cleanup: _TaskScopedSnapshotCleanup,
) -> _PendingMeasurementFinalization:
    """Persist only code-captured host events and sign their public-safe replay."""

    context = _measurement_context(root, baseline_revision)
    if context is None:
        raise ValueError("O4 measurement baseline is not registered and active")
    source_revision, _ = context
    registered = _registered_runtime_bindings(root, baseline_revision)
    if registered is None or registered[:3] != (
        source_binding,
        snapshot,
        attestation_binding,
    ):
        raise ValueError("O4 measurement runtime differs from the registration")
    if (
        not isinstance(scenarios, list)
        or len(scenarios) != 2
        or not isinstance(snapshot_cleanup, _TaskScopedSnapshotCleanup)
        or getattr(snapshot_cleanup, "_origin", None) is not _LIVE_CAPTURE_ORIGIN
        or snapshot_cleanup.get("reason") != "accepted"
    ):
        raise ValueError("O4 measurement requires live task-owned operands")
    scenario_values: list[dict[str, Any]] = []
    captures: list[_LiveAppServerCapture] = []
    for index, item in enumerate(scenarios):
        if (
            not isinstance(item, _CapturedAppServerScenario)
            or item._consumed
            or item._capture.origin is not _LIVE_CAPTURE_ORIGIN
            or not item._capture.finalized
            or item._capture_digest != item._capture.sealed_digest
            or item._capture_digest != v1._canonical_sha256(item._value)
            or item._capture.source_binding != source_binding
            or item._capture.snapshot != snapshot
            or item._value.get("scenarioIdentity")
            != v1.CARRIER_SCENARIO_IDENTITIES[index]
            or item._value.get("expectedHead") != baseline_revision
        ):
            raise ValueError("O4 measurement live scenario identity is invalid")
        scenario_values.append(deepcopy(item._value))
        captures.append(item._capture)
    if (
        captures[0] is captures[1]
        or captures[0].suite is not captures[1].suite
        or captures[0].isolate_root != captures[1].isolate_root
        or snapshot_cleanup._isolate_root != captures[0].isolate_root
        or captures[0].suite.completed_scenarios
        != list(v1.CARRIER_SCENARIO_IDENTITIES)
        or registered[3] != captures[0].suite.registered_user_chronology_baseline
    ):
        raise ValueError("O4 measurement live process or isolate identity is invalid")
    raw_path = private_raw_root.resolve(strict=True)
    key_path = private_key_root.resolve(strict=True)
    isolate_path = captures[0].isolate_root
    roots = (raw_path, isolate_path, key_path)
    if len(set(roots)) != len(roots) or any(
        left.is_relative_to(right) or right.is_relative_to(left)
        for index, left in enumerate(roots)
        for right in roots[index + 1 :]
    ):
        raise ValueError("O4 private resource roots overlap")
    if os.name == "nt" and any(
        not _windows_private_cleanup_capability(path) for path in roots
    ):
        raise ValueError("O4 private resource cleanup capability is unavailable")
    if (
        not isinstance(attestation_binding, _TaskAttestationPublicBinding)
        or attestation_binding._origin is not _LIVE_CAPTURE_ORIGIN
        or attestation_binding._private_root != key_path
    ):
        raise ValueError("O4 attestation private-root token is invalid")
    expected_root_identities = tuple(
        _directory_object_identity(path) for path in roots
    )
    if (
        expected_root_identities[1] != captures[0].suite.isolate_root_identity
        or expected_root_identities[2]
        != attestation_binding._private_root_identity
    ):
        raise ValueError("O4 private resource origin identity drifted")
    acquired_locks: list[_LockedPrivateResourceRoot] = []
    try:
        for path in roots:
            acquired_locks.append(_LockedPrivateResourceRoot(path))
    except Exception:
        for lock in acquired_locks:
            lock.release()
        raise
    root_locks = tuple(acquired_locks)
    root_identities = tuple(lock.identity for lock in root_locks)
    if root_identities != expected_root_identities:
        for lock in root_locks:
            lock.release()
        raise ValueError("O4 private resource changed during lock acquisition")
    for item in scenarios:
        item._consumed = True
    cleanup_trees = tuple(_private_resource_tree_identity(path) for path in roots)
    try:
        persist_private_measurement(
            raw_path,
            source_binding,
            snapshot,
            source_revision,
            baseline_revision,
            scenario_values,
            dict(snapshot_cleanup),
        )
        cleanup_trees = tuple(_private_resource_tree_identity(path) for path in roots)
        replay = _load_private_measurement(
            raw_path,
            source_binding,
            snapshot,
            source_revision,
            baseline_revision,
        )
        if replay is None:
            raise ValueError("O4 private measurement replay failed")
        projections, cleanup = replay
        fault_suite = deepcopy(captures[0].suite.fault_suite)
        material_checkpoint_binding = deepcopy(
            captures[0].suite.material_checkpoint_binding
        )
        replayed_fault_suite = run_fault_suite(root, baseline_revision)
        if (
            not isinstance(fault_suite, dict)
            or
            fault_suite.get("allFaultControlsObserved") is not True
            or fault_suite.get("cleanupVerified") is not True
            or replayed_fault_suite != fault_suite
        ):
            raise ValueError("O4 deterministic fault replay failed")
        payload = _measurement_attestation_payload(
            source_revision,
            baseline_revision,
            source_binding,
            snapshot,
            projections,
            fault_suite,
            material_checkpoint_binding,
            cleanup,
        )
        signature = _sign_task_attestation(
            key_path, attestation_binding, payload
        )
        cleanup_trees = tuple(_private_resource_tree_identity(path) for path in roots)
        measurement_document = {**payload, "captureAttestation": signature}
        tree_identities = tuple(
            _private_resource_tree_identity(path) for path in roots
        )
        return _PendingMeasurementFinalization(
            measurement_document,
            attestation_binding,
            raw_path,
            isolate_path,
            key_path,
            root_identities,
            tree_identities,
            root_locks,
        )
    except Exception as original_error:
        cleanup_errors: list[Exception] = []
        for lock, expected_tree in zip(root_locks, cleanup_trees, strict=True):
            if lock.disposed:
                continue
            try:
                _dispose_locked_private_tree(lock, expected_tree)
            except Exception as cleanup_error:
                cleanup_errors.append(cleanup_error)
        for lock in root_locks:
            if lock._handle is None:
                continue
            try:
                lock.release()
            except Exception as cleanup_error:
                cleanup_errors.append(cleanup_error)
        if cleanup_errors:
            raise RuntimeError(
                "O4 measurement attestation failed with private residue"
            ) from cleanup_errors[0]
        raise original_error


def _carrier_projection_valid(
    value: Any,
    source_binding: dict[str, Any],
    snapshot: dict[str, Any],
) -> bool:
    if not isinstance(value, dict) or set(value) != {
        "schema",
        "scenarioIdentity",
        "nativeExecutionSnapshot",
        "processLifecycle",
        "materialCheckpointEvidence",
        "contextUsageEvidence",
        "carrierDecisionEvidence",
        "carrierProjection",
    }:
        return False
    process_lifecycle = value.get("processLifecycle")
    if not isinstance(process_lifecycle, dict) or set(process_lifecycle) != {
        "launch",
        "terminal",
    }:
        return False
    launch_record = process_lifecycle.get("launch")
    terminal_record = process_lifecycle.get("terminal")
    if not _launch_record_valid(launch_record, source_binding, snapshot) or not (
        _terminal_record_valid(
            terminal_record, launch_record, source_binding, snapshot
        )
    ):
        return False
    expected_native = {
        "publicIdentity": snapshot["publicIdentity"],
        "releaseVersion": source_binding["releaseVersion"],
        "sha256": snapshot["snapshotExecutableSha256"],
        "bytes": snapshot["snapshotExecutableBytes"],
        "verifiedBeforeHostProcess": True,
        "ambientExecutableUsed": False,
        "launchPublicIdentity": launch_record["launchPublicIdentity"],
        "processImageSha256": snapshot["snapshotExecutableSha256"],
        "snapshotOwnedAppServerLaunch": True,
    }
    carrier_projection = value.get("carrierProjection")
    material_checkpoint_evidence = value.get("materialCheckpointEvidence")
    context_usage_evidence = value.get("contextUsageEvidence")
    carrier_decision_evidence = value.get("carrierDecisionEvidence")
    scenario_identity = value.get("scenarioIdentity")
    if scenario_identity == v1.CARRIER_SCENARIO_IDENTITIES[0]:
        if (
            not isinstance(material_checkpoint_evidence, dict)
            or set(material_checkpoint_evidence)
            != {
                "schema",
                "reconciliationEventShapeSha256",
                "verifierRecordSha256",
                "verifierReportSha256",
                "gitRecordSha256",
                "gitHead",
            }
            or material_checkpoint_evidence.get("schema") != 1
            or material_checkpoint_evidence.get(
                "reconciliationEventShapeSha256"
            )
            != (
                carrier_projection.get("eventShapeSha256")
                if isinstance(carrier_projection, dict)
                else None
            )
            or any(
                not isinstance(material_checkpoint_evidence.get(field), str)
                or SHA256_PATTERN.fullmatch(
                    material_checkpoint_evidence[field]
                )
                is None
                for field in (
                    "reconciliationEventShapeSha256",
                    "verifierRecordSha256",
                    "verifierReportSha256",
                    "gitRecordSha256",
                )
            )
            or not isinstance(material_checkpoint_evidence.get("gitHead"), str)
            or GIT_OBJECT_PATTERN.fullmatch(
                material_checkpoint_evidence["gitHead"]
            )
            is None
        ):
            return False
        if context_usage_evidence is not None:
            if (
                not isinstance(context_usage_evidence, dict)
                or set(context_usage_evidence)
                != {
                    "schema",
                    "recordOrdinal",
                    "recordSha256",
                    "effectiveContextWindowTokens",
                    "usedContextTokens",
                }
                or context_usage_evidence.get("schema") != 1
                or type(context_usage_evidence.get("recordOrdinal")) is not int
                or context_usage_evidence["recordOrdinal"] < 0
                or not isinstance(context_usage_evidence.get("recordSha256"), str)
                or SHA256_PATTERN.fullmatch(context_usage_evidence["recordSha256"])
                is None
                or type(context_usage_evidence.get("effectiveContextWindowTokens"))
                is not int
                or context_usage_evidence["effectiveContextWindowTokens"] <= 0
                or type(context_usage_evidence.get("usedContextTokens")) is not int
                or not (
                    0
                    <= context_usage_evidence["usedContextTokens"]
                    <= context_usage_evidence["effectiveContextWindowTokens"]
                )
            ):
                return False
        if carrier_decision_evidence is not None:
            return False
    else:
        if (
            material_checkpoint_evidence is not None
            or context_usage_evidence is not None
            or not isinstance(
            carrier_decision_evidence, dict
            )
        ):
            return False
        expected_fields = {
            "source",
            "effectiveContextWindowTokens",
            "usedContextTokens",
            "usedContextBasisPoints",
            "usageBand",
            "tokenUsageRecordOrdinal",
            "tokenUsageRecordSha256",
            "calibrationBands",
            "turnCountRecommendationState",
            "turnCountRecommendation",
            "automaticCompactionCount",
            "manualCompactionCount",
            "opaqueCompactionSummaryCountProxy",
            "userChronologyBaselineCount",
            "userChronologyCurrentCount",
            "userChronologyBaselineSha256",
            "userChronologyCurrentSha256",
            "userChronologyBaselineContentSha256",
            "userChronologyCurrentContentSha256",
            "sourceCarrierIdentitySha256",
            "userInitiatedHandoffObserved",
            "agentTransitionTriggeredBeforeUserIntervention",
        }
        automatic = carrier_decision_evidence.get("automaticCompactionCount")
        manual = carrier_decision_evidence.get("manualCompactionCount")
        window = carrier_decision_evidence.get("effectiveContextWindowTokens")
        used = carrier_decision_evidence.get("usedContextTokens")
        basis_points = carrier_decision_evidence.get("usedContextBasisPoints")
        token_ordinal = carrier_decision_evidence.get("tokenUsageRecordOrdinal")
        token_sha256 = carrier_decision_evidence.get("tokenUsageRecordSha256")
        baseline_count = carrier_decision_evidence.get("userChronologyBaselineCount")
        current_count = carrier_decision_evidence.get("userChronologyCurrentCount")
        baseline_sha256 = carrier_decision_evidence.get(
            "userChronologyBaselineSha256"
        )
        current_sha256 = carrier_decision_evidence.get("userChronologyCurrentSha256")
        baseline_content_sha256 = carrier_decision_evidence.get(
            "userChronologyBaselineContentSha256"
        )
        current_content_sha256 = carrier_decision_evidence.get(
            "userChronologyCurrentContentSha256"
        )
        if (
            set(carrier_decision_evidence) != expected_fields
            or carrier_decision_evidence.get("source")
            != "task-bound-effective-context-window-observer-v3"
            or carrier_decision_evidence.get("calibrationBands")
            != TRANSITION_AND_CLEANUP_BOUNDARY[
                "taskScopedContextCalibrationBands"
            ]
            or carrier_decision_evidence.get("turnCountRecommendationState")
            != "not-established-by-bound-official-source"
            or carrier_decision_evidence.get("turnCountRecommendation") is not None
            or type(automatic) is not int
            or automatic < 0
            or type(manual) is not int
            or manual < 0
            or automatic + manual < 1
            or carrier_decision_evidence.get(
                "opaqueCompactionSummaryCountProxy"
            )
            != automatic + manual
            or type(baseline_count) is not int
            or baseline_count < 1
            or current_count != baseline_count
            or not isinstance(baseline_sha256, str)
            or SHA256_PATTERN.fullmatch(baseline_sha256) is None
            or current_sha256 != baseline_sha256
            or not isinstance(baseline_content_sha256, str)
            or SHA256_PATTERN.fullmatch(baseline_content_sha256) is None
            or current_content_sha256 != baseline_content_sha256
            or not isinstance(
                carrier_decision_evidence.get("sourceCarrierIdentitySha256"), str
            )
            or SHA256_PATTERN.fullmatch(
                carrier_decision_evidence["sourceCarrierIdentitySha256"]
            )
            is None
            or carrier_decision_evidence.get("userInitiatedHandoffObserved")
            is not False
            or carrier_decision_evidence.get(
                "agentTransitionTriggeredBeforeUserIntervention"
            )
            is not True
        ):
            return False
        if window is None or used is None:
            if not (
                window is None
                and used is None
                and basis_points is None
                and carrier_decision_evidence.get("usageBand") == "unknown"
                and token_ordinal is None
                and token_sha256 is None
            ):
                return False
        else:
            if (
                type(window) is not int
                or type(used) is not int
                or not (0 <= used <= window)
                or window <= 0
                or basis_points != (used * 10_000) // window
                or type(token_ordinal) is not int
                or token_ordinal < 0
                or not isinstance(token_sha256, str)
                or SHA256_PATTERN.fullmatch(token_sha256) is None
            ):
                return False
            expected_band = (
                "immediate-transition"
                if basis_points >= 8_000
                else "transition-ready"
                if basis_points >= 6_000
                else "efficient"
            )
            if (
                carrier_decision_evidence.get("usageBand") != expected_band
                or expected_band == "efficient"
            ):
                return False
    frozen_projection = deepcopy(carrier_projection)
    if isinstance(frozen_projection, dict):
        frozen_projection["codexSourceBinding"] = v1.CODEX_SOURCE_BINDING
        if (
            isinstance(carrier_decision_evidence, dict)
            and carrier_decision_evidence.get("usageBand")
            in {"transition-ready", "immediate-transition"}
        ):
            sequence = frozen_projection.get("eventSequence")
            if (
                frozen_projection.get("sourceFormat")
                != "public-safe-codex-app-server-goal-observation-v3"
                or not isinstance(sequence, list)
                or not sequence
                or sequence[0]
                != {
                    "ordinal": 0,
                    "sourceClass": "carrier-fitness-observation",
                    "eventClass": "known-client-effective-context-band-triggered",
                    "carrierRole": "source",
                    "state": carrier_decision_evidence.get("usageBand"),
                }
            ):
                return False
            if carrier_projection.get("eventShapeSha256") != v1._canonical_sha256(
                sequence
            ):
                return False
            sequence[0]["eventClass"] = "capacity-risk-or-unknown-rule-triggered"
            sequence[0]["state"] = "transition-required"
            frozen_projection["sourceFormat"] = (
                "public-safe-codex-app-server-goal-observation-v2"
            )
            frozen_projection["eventShapeSha256"] = v1._canonical_sha256(sequence)
    return (
        value.get("schema") == 1
        and scenario_identity in v1.CARRIER_SCENARIO_IDENTITIES
        and value.get("nativeExecutionSnapshot") == expected_native
        and isinstance(carrier_projection, dict)
        and carrier_projection.get("scenarioIdentity") == value.get("scenarioIdentity")
        and carrier_projection.get("codexSourceBinding") == source_binding
        and v1._carrier_projection_valid(frozen_projection)
        and not v1._contains_private_value(value)
    )


FaultExecutor = Callable[[Path, str, v1.FaultScenario], dict[str, Any]]


def run_fault_suite(
    root: Path,
    source_revision: str,
    *,
    executor: FaultExecutor | None = None,
) -> dict[str, Any]:
    replay = v2.run_fault_suite(root, source_revision, executor=executor)
    replay["suiteIdentity"] = SUITE_IDENTITY
    return replay


def _measurement_context(
    root: Path, baseline_revision: Any
) -> tuple[str, dict[str, Any]] | None:
    if (
        not isinstance(baseline_revision, str)
        or GIT_OBJECT_PATTERN.fullmatch(baseline_revision) is None
    ):
        return None
    git = _trusted_git_executable()
    if git is None:
        return None
    common = {
        "cwd": root.resolve(strict=True),
        "check": False,
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "timeout": 30,
        "env": _trusted_git_environment(git),
    }
    try:
        ancestry = subprocess.run(
            [str(git), "rev-list", "--parents", "-n", "1", baseline_revision],
            **common,
        )
        if (
            ancestry.returncode != 0
            or len(ancestry.stdout) > 256
            or len(ancestry.stderr) > 16_384
        ):
            return None
        parts = ancestry.stdout.decode("ascii").strip().split()
        if len(parts) != 2 or parts[0] != baseline_revision:
            return None
        registration_revision = parts[1]
        head_ancestry = subprocess.run(
            [str(git), "merge-base", "--is-ancestor", baseline_revision, "HEAD"],
            **common,
        )
        changed = subprocess.run(
            [
                str(git),
                "diff-tree",
                "--no-commit-id",
                "--name-only",
                "-r",
                baseline_revision,
            ],
            **common,
        )
        if (
            head_ancestry.returncode != 0
            or head_ancestry.stdout
            or len(head_ancestry.stderr) > 16_384
            or changed.returncode != 0
            or len(changed.stdout) > 4_096
            or len(changed.stderr) > 16_384
            or changed.stdout.decode("utf-8").splitlines()
            != ["product/program.json"]
        ):
            return None
        raw_program = subprocess.run(
            [str(git), "show", f"{baseline_revision}:product/program.json"],
            **common,
        )
        if (
            raw_program.returncode != 0
            or len(raw_program.stdout) > 1_048_576
            or len(raw_program.stderr) > 16_384
        ):
            return None
        program = v1._strict_json_object(raw_program.stdout)
    except (OSError, subprocess.SubprocessError, UnicodeError, ValueError):
        return None
    increments = program.get("increments")
    if not isinstance(increments, list):
        return None
    active = [
        item
        for item in increments
        if isinstance(item, dict) and item.get("state") == "active"
    ]
    if len(active) != 1 or active[0].get("id") != INCREMENT_ID:
        return None
    increment = active[0]
    registration = increment.get("taskRegistration")
    work_items = increment.get("workItems")
    active_work = (
        [
            item
            for item in work_items
            if isinstance(item, dict) and item.get("state") == "active"
        ]
        if isinstance(work_items, list)
        else []
    )
    if not (
        program.get("status") == "active"
        and program.get("activeIncrementId") == INCREMENT_ID
        and isinstance(registration, dict)
        and registration.get("locator") == REGISTRATION_LOCATOR
        and registration.get("sourceRevision") == registration_revision
        and len(active_work) == 1
    ):
        return None
    return registration_revision, increment


def _measurement_baseline_valid(root: Path, baseline_revision: Any) -> bool:
    return _measurement_context(root, baseline_revision) is not None


def _registered_runtime_bindings(
    root: Path, baseline_revision: str
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]] | None:
    context = _measurement_context(root, baseline_revision)
    if context is None:
        return None
    registration_revision, increment = context
    # Registration artifacts are outside the environment-manifest namespace, so
    # read them through a bounded direct Git command rather than widening _git_blob.
    git = _trusted_git_executable()
    if git is None:
        return None
    try:
        completed = subprocess.run(
            [str(git), "show", f"{registration_revision}:{REGISTRATION_LOCATOR}"],
            cwd=root.resolve(strict=True),
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
            env=_trusted_git_environment(git),
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if (
        completed.returncode != 0
        or len(completed.stdout) > 1_048_576
        or len(completed.stderr) > 16_384
    ):
        return None
    try:
        registration = v1._strict_json_object(completed.stdout)
    except (json.JSONDecodeError, RecursionError, TypeError, UnicodeError, ValueError):
        return None
    errors: list[str] = []
    if not validate_registration(registration, increment, ("O4",), root, errors):
        return None
    values = registration.get("preRegistrationValues")
    runtime = _manifest_runtime_bindings(
        root, values.get("environmentAttributionBinding")
    )
    scenario_validator = values.get("scenarioValidator")
    baseline = (
        scenario_validator.get("sourceUserChronologyBaseline")
        if isinstance(scenario_validator, dict)
        else None
    )
    if runtime is None or not _user_chronology_baseline_valid(baseline):
        return None
    return (*runtime, deepcopy(baseline))


def _observation_valid(
    root: Path,
    observation: dict[str, Any],
    source_revision: str,
) -> bool:
    if set(observation) != {
        "schema",
        "kind",
        "suiteIdentity",
        "registrationSourceRevision",
        "measurementBaselineRevision",
        "sourceBinding",
        "snapshotBinding",
        "faultSuite",
        "materialCheckpointBinding",
        "carrierProjections",
        "claimCeiling",
        "cleanupVerified",
        "snapshotCleanup",
        "captureAttestation",
        "privateMeasurementCleanup",
        "isolatedCodexHomeCleanup",
        "terminalCleanupAttestation",
        "attestationKeyCleanup",
    }:
        return False
    source_binding = observation.get("sourceBinding")
    snapshot = observation.get("snapshotBinding")
    projections = observation.get("carrierProjections")
    cleanup = observation.get("snapshotCleanup")
    registered = _registered_runtime_bindings(root, source_revision)
    measurement_context = _measurement_context(root, source_revision)
    registration_revision = (
        measurement_context[0] if measurement_context is not None else None
    )
    if registered is None:
        return False
    (
        registered_source,
        registered_snapshot,
        attestation_binding,
        registered_user_baseline,
    ) = registered
    decision_evidence = (
        projections[1].get("carrierDecisionEvidence")
        if isinstance(projections, list)
        and len(projections) == 2
        and isinstance(projections[1], dict)
        else None
    )
    try:
        payload = _measurement_attestation_payload(
            registration_revision,
            source_revision,
            source_binding,
            snapshot,
            projections,
            observation.get("faultSuite"),
            observation.get("materialCheckpointBinding"),
            cleanup,
        )
    except (TypeError, ValueError):
        return False
    private_measurement_cleanup = observation.get("privateMeasurementCleanup")
    isolate_cleanup = observation.get("isolatedCodexHomeCleanup")
    try:
        terminal_payload = _terminal_cleanup_attestation_payload(
            attestation_binding,
            observation.get("captureAttestation"),
            private_measurement_cleanup,
            isolate_cleanup,
            snapshot,
        )
    except (TypeError, ValueError):
        return False
    if (
        observation.get("schema") != 1
        or observation.get("kind") != "o4-v3-public-measurement-after-registration"
        or observation.get("suiteIdentity") != SUITE_IDENTITY
        or observation.get("registrationSourceRevision") != registration_revision
        or observation.get("measurementBaselineRevision") != source_revision
        or not official_source_binding_valid(source_binding)
        or not snapshot_record_valid(snapshot, source_binding)
        or (registered_source, registered_snapshot) != (source_binding, snapshot)
        or not isinstance(projections, list)
        or len(projections) != 2
        or not isinstance(decision_evidence, dict)
        or decision_evidence.get("userChronologyBaselineCount")
        != registered_user_baseline.get("userMessageCount")
        or decision_evidence.get("userChronologyBaselineSha256")
        != registered_user_baseline.get("userMessageIdentitySha256")
        or decision_evidence.get("userChronologyBaselineContentSha256")
        != registered_user_baseline.get("userMessageContentIdentitySha256")
        or decision_evidence.get("sourceCarrierIdentitySha256")
        != registered_user_baseline.get("sourceCarrierIdentitySha256")
        or not verify_task_attestation(
            attestation_binding,
            payload,
            observation.get("captureAttestation"),
        )
        or not verify_task_attestation(
            attestation_binding,
            terminal_payload,
            observation.get("terminalCleanupAttestation"),
        )
        or not _attestation_key_cleanup_record_valid(
            observation.get("attestationKeyCleanup"), attestation_binding
        )
        or [
            item.get("scenarioIdentity")
            for item in projections
            if isinstance(item, dict)
        ]
        != list(v1.CARRIER_SCENARIO_IDENTITIES)
        or not all(
            _carrier_projection_valid(item, source_binding, snapshot)
            for item in projections
        )
        or len(
            {
                item["processLifecycle"]["launch"]["launchPublicIdentity"]
                for item in projections
            }
        )
        != 2
        or observation.get("claimCeiling") != CLAIM_CEILING
        or observation.get("cleanupVerified") is not True
        or not _snapshot_cleanup_record_valid(cleanup, snapshot)
        or cleanup.get("reason") != "accepted"
        or not _measurement_baseline_valid(root, source_revision)
    ):
        return False
    replay = run_fault_suite(root, source_revision)
    return (
        observation.get("faultSuite") == replay
        and replay.get("allFaultControlsObserved") is True
        and replay.get("cleanupVerified") is True
    )


def validate_evidence(
    document: dict[str, Any],
    criterion_id: str,
    root: Path,
    errors: list[str],
) -> bool:
    """Replay v3 faults and validate snapshot-bound carrier projections."""

    before = len(errors)
    source = document.get("source")
    result = document.get("result")
    if (
        criterion_id != "O4"
        or document.get("criterionIds") != ["O4"]
        or document.get("incrementId") != INCREMENT_ID
        or not isinstance(source, dict)
        or source.get("kind") != "controlled-o4-self-correction-suite-observation"
        or source.get("locator") != OBSERVATION_LOCATOR
        or not isinstance(source.get("identity"), str)
        or re.fullmatch(r"sha256:[0-9a-f]{64}", source["identity"]) is None
        or not isinstance(result, dict)
        or set(result)
        != {
            "accepted",
            "suiteIdentity",
            "sourceRevision",
            "observationSha256",
            "independentReplayVerified",
            "destinationBeforeSourceReleaseVerified",
            "snapshotExecutionAndCleanupVerified",
            "cleanupVerified",
            "claimCeiling",
        }
        or result.get("accepted") is not True
        or result.get("suiteIdentity") != SUITE_IDENTITY
        or not isinstance(result.get("sourceRevision"), str)
        or GIT_OBJECT_PATTERN.fullmatch(result["sourceRevision"]) is None
        or not isinstance(result.get("observationSha256"), str)
        or SHA256_PATTERN.fullmatch(result["observationSha256"]) is None
        or source.get("identity") != "sha256:" + result.get("observationSha256", "")
        or result.get("independentReplayVerified") is not True
        or result.get("destinationBeforeSourceReleaseVerified") is not True
        or result.get("snapshotExecutionAndCleanupVerified") is not True
        or result.get("cleanupVerified") is not True
        or result.get("claimCeiling") != CLAIM_CEILING
    ):
        v1._error(errors, "O4 third-generation evidence is incomplete")
        return False
    try:
        raw = (root / OBSERVATION_LOCATOR).read_bytes()
        if hashlib.sha256(raw).hexdigest() != result["observationSha256"]:
            raise ValueError("O4 third-generation observation digest mismatch")
        observation = v1._strict_json_object(raw)
        if not _observation_valid(root, observation, result["sourceRevision"]):
            raise ValueError("O4 third-generation observation replay failed")
    except (
        json.JSONDecodeError,
        OSError,
        RecursionError,
        TypeError,
        UnicodeError,
        ValueError,
    ):
        v1._error(errors, "O4 third-generation evidence replay failed closed")
    return len(errors) == before


__all__ = [
    "CARRIER_GOAL_BINDING",
    "CLAIM_CEILING",
    "CORRECTION_BINDINGS",
    "FAILURE_BINDINGS",
    "FAULT_SCENARIOS",
    "INCREMENT_ID",
    "ISOLATE_MARKER_RELATIVE_PARTS",
    "OBSERVATION_LOCATOR",
    "REGISTRATION_LOCATOR",
    "REQUIRED_APP_SERVER_CONTRACT",
    "SCENARIO_IDENTITIES",
    "SNAPSHOT_RELATIVE_PARTS",
    "SNAPSHOT_POLICY",
    "SOURCE_BLOB_PATHS",
    "SUITE_IDENTITY",
    "TRANSITION_AND_CLEANUP_BOUNDARY",
    "VALIDATOR_KIND",
    "VALIDATOR_LOCATOR",
    "begin_pre_registration_capture_suite",
    "begin_task_scoped_capture_suite",
    "bind_snapshot_app_server_message",
    "capture_repository_checkpoint",
    "capture_source_carrier_release_preflight",
    "capture_source_user_chronology_baseline",
    "capture_unknown_capacity_transition_signal",
    "cleanup_authorized_o4_isolate_root",
    "cleanup_private_measurement",
    "cleanup_task_attestation_key",
    "cleanup_task_scoped_native_snapshot",
    "close_task_scoped_snapshot_app_server",
    "counterexample_sources",
    "initialize_authorized_o4_isolate_root",
    "finalize_live_app_server_scenario",
    "finalize_public_measurement_observation",
    "launch_task_scoped_snapshot_app_server",
    "materialize_task_scoped_native_snapshot",
    "official_source_binding_valid",
    "create_task_attestation_key",
    "persist_and_attest_private_measurement",
    "prepare_task_scoped_native_snapshot",
    "project_raw_carrier_observations",
    "resolve_current_official_source_binding",
    "seal_source_preparation_attestation",
    "read_snapshot_app_server_message",
    "run_fault_suite",
    "snapshot_app_server_terminal_observation",
    "snapshot_preflight_observation",
    "snapshot_record_valid",
    "validate_evidence",
    "validate_registration",
    "verified_task_scoped_snapshot_executable",
    "verify_task_attestation",
    "write_snapshot_app_server_message",
]
