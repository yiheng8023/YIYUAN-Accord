#!/usr/bin/env python3
"""Fail-closed append-only identity ledger for a future TDD diagnostic runner."""

from __future__ import annotations

import hashlib
import json
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


ZERO_SHA256 = "0" * 64
ALLOWED_EVENT_TYPES = {
    "candidate-reserved",
    "construction-succeeded",
    "construction-failed",
    "reservation-reconciled",
    "thread-bound",
    "turn-bound",
}


class DispatchGateError(RuntimeError):
    """Raised when a dispatch identity transition cannot be recorded safely."""


def _is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _event_sha256(event: dict[str, Any]) -> str:
    payload = {
        key: value
        for key, value in event.items()
        if key != "eventSha256"
    }
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _canonical_sha256(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@contextmanager
def _exclusive_lock(path: Path) -> Iterator[None]:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as stream:
        stream.seek(0, os.SEEK_END)
        if stream.tell() == 0:
            stream.write(b"\0")
            stream.flush()
            os.fsync(stream.fileno())
        stream.seek(0)
        if os.name == "nt":
            import msvcrt

            msvcrt.locking(stream.fileno(), msvcrt.LK_LOCK, 1)
            try:
                yield
            finally:
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


class DispatchIdentityLedger:
    """Append candidate, thread, and turn identity transitions under one lock."""

    def __init__(self, path: Path) -> None:
        self.path = path.resolve()
        self.lock_path = self.path.with_name(self.path.name + ".lock")

    def read_events(self) -> list[dict[str, Any]]:
        with _exclusive_lock(self.lock_path):
            return self._read_unlocked()

    @classmethod
    def reserve_from_repository_documents(
        cls,
        *,
        protocol_path: Path,
        source_governance_preflight_path: Path,
        static_gap_audit_path: Path,
        diagnostic_admission_path: Path,
        candidate_id: str,
        reservation_id: str,
        observed_at: str,
    ) -> tuple["DispatchIdentityLedger", dict[str, Any]]:
        try:
            from .human_ai_collaboration_tdd_noncomparative_dispatch_authorization_adapter import (
                build_dispatch_authorization_envelope,
            )
        except ImportError:
            from human_ai_collaboration_tdd_noncomparative_dispatch_authorization_adapter import (
                build_dispatch_authorization_envelope,
            )

        envelope = build_dispatch_authorization_envelope(
            protocol_path=protocol_path,
            source_governance_preflight_path=source_governance_preflight_path,
            static_gap_audit_path=static_gap_audit_path,
            diagnostic_admission_path=diagnostic_admission_path,
            candidate_id=candidate_id,
            observed_at=observed_at,
        )
        authorization = envelope.reservation_input()
        ledger = cls(envelope.ledger_path)
        event = ledger._reserve_candidate(
            candidate_id=authorization["candidateId"],
            candidate_identity_sha256=authorization[
                "candidateIdentitySha256"
            ],
            protocol_sha256=authorization["protocolFileSha256"],
            reservation_id=reservation_id,
            observed_at=authorization["observedAt"],
            exact_candidate_execution_admitted=authorization[
                "exactCandidateExecutionAdmitted"
            ],
            source_and_toolchain_reverified_at_dispatch=authorization[
                "sourceAndToolchainReverifiedAtDispatch"
            ],
            authorization_evidence=authorization,
        )
        return ledger, event

    def _reserve_candidate(
        self,
        *,
        candidate_id: str,
        candidate_identity_sha256: str,
        protocol_sha256: str,
        reservation_id: str,
        observed_at: str,
        exact_candidate_execution_admitted: bool,
        source_and_toolchain_reverified_at_dispatch: bool,
        authorization_evidence: dict[str, Any],
    ) -> dict[str, Any]:
        if exact_candidate_execution_admitted is not True:
            raise DispatchGateError(
                "exact-candidate execution admission is required"
            )
        if source_and_toolchain_reverified_at_dispatch is not True:
            raise DispatchGateError(
                "source and toolchain must be reverified at dispatch"
            )
        self._require_identity(candidate_id, "candidate identity")
        self._require_identity(reservation_id, "reservation identity")
        self._require_identity(observed_at, "observation time")
        if not _is_sha256(candidate_identity_sha256):
            raise DispatchGateError("candidate identity SHA-256 is invalid")
        if not _is_sha256(protocol_sha256):
            raise DispatchGateError("protocol SHA-256 is invalid")
        authorization_payload = {
            key: value
            for key, value in authorization_evidence.items()
            if key != "authorizationSha256"
        }
        if not (
            authorization_payload
            == {
                "schema": 1,
                "candidateId": candidate_id,
                "candidateIdentitySha256": candidate_identity_sha256,
                "protocolFileSha256": protocol_sha256,
                "sourceGovernancePreflightFileSha256": authorization_evidence.get(
                    "sourceGovernancePreflightFileSha256"
                ),
                "staticGapAuditFileSha256": authorization_evidence.get(
                    "staticGapAuditFileSha256"
                ),
                "diagnosticAdmissionFileSha256": authorization_evidence.get(
                    "diagnosticAdmissionFileSha256"
                ),
                "diagnosticAdmissionId": authorization_evidence.get(
                    "diagnosticAdmissionId"
                ),
                "ledgerAuthorityDocument": authorization_evidence.get(
                    "ledgerAuthorityDocument"
                ),
                "ledgerAuthorityDocumentSha256": authorization_evidence.get(
                    "ledgerAuthorityDocumentSha256"
                ),
                "ledgerAuthorityId": authorization_evidence.get(
                    "ledgerAuthorityId"
                ),
                "ledgerRelativePath": authorization_evidence.get(
                    "ledgerRelativePath"
                ),
                "observedAt": observed_at,
                "exactCandidateExecutionAdmitted": True,
                "sourceAndToolchainReverifiedAtDispatch": True,
            }
            and all(
                _is_sha256(authorization_evidence.get(key))
                for key in (
                    "sourceGovernancePreflightFileSha256",
                    "staticGapAuditFileSha256",
                    "diagnosticAdmissionFileSha256",
                    "ledgerAuthorityDocumentSha256",
                )
            )
            and isinstance(
                authorization_evidence.get("diagnosticAdmissionId"),
                str,
            )
            and bool(
                authorization_evidence["diagnosticAdmissionId"].strip()
            )
            and all(
                isinstance(authorization_evidence.get(key), str)
                and bool(authorization_evidence[key].strip())
                for key in (
                    "ledgerAuthorityDocument",
                    "ledgerAuthorityId",
                    "ledgerRelativePath",
                )
            )
            and authorization_evidence.get("authorizationSha256")
            == _canonical_sha256(authorization_payload)
        ):
            raise DispatchGateError(
                "dispatch authorization evidence is invalid"
            )

        with _exclusive_lock(self.lock_path):
            events = self._read_unlocked()
            if any(
                event["candidateId"] == candidate_id
                for event in events
            ):
                raise DispatchGateError(
                    "candidate dispatch cap has already been consumed"
                )
            if any(
                event["reservationId"] == reservation_id
                for event in events
            ):
                raise DispatchGateError(
                    "reservation identity has already been used"
                )
            return self._append_unlocked(
                events,
                {
                    "schema": 1,
                    "eventType": "candidate-reserved",
                    "candidateId": candidate_id,
                    "candidateIdentitySha256": candidate_identity_sha256,
                    "protocolSha256": protocol_sha256,
                    "reservationId": reservation_id,
                    "observedAt": observed_at,
                    "exactCandidateExecutionAdmitted": True,
                    "sourceAndToolchainReverifiedAtDispatch": True,
                    "sourceGovernancePreflightFileSha256": (
                        authorization_evidence[
                            "sourceGovernancePreflightFileSha256"
                        ]
                    ),
                    "staticGapAuditFileSha256": authorization_evidence[
                        "staticGapAuditFileSha256"
                    ],
                    "diagnosticAdmissionFileSha256": (
                        authorization_evidence[
                            "diagnosticAdmissionFileSha256"
                        ]
                    ),
                    "diagnosticAdmissionId": authorization_evidence[
                        "diagnosticAdmissionId"
                    ],
                    "ledgerAuthorityDocument": authorization_evidence[
                        "ledgerAuthorityDocument"
                    ],
                    "ledgerAuthorityDocumentSha256": authorization_evidence[
                        "ledgerAuthorityDocumentSha256"
                    ],
                    "ledgerAuthorityId": authorization_evidence[
                        "ledgerAuthorityId"
                    ],
                    "ledgerRelativePath": authorization_evidence[
                        "ledgerRelativePath"
                    ],
                    "authorizationSha256": authorization_evidence[
                        "authorizationSha256"
                    ],
                },
            )

    def record_construction_success(
        self,
        *,
        reservation_id: str,
        construction_id: str,
        observed_at: str,
    ) -> dict[str, Any]:
        self._require_identity(reservation_id, "reservation identity")
        self._require_identity(construction_id, "construction identity")
        self._require_identity(observed_at, "observation time")
        with _exclusive_lock(self.lock_path):
            events = self._read_unlocked()
            reservation = self._reservation(events, reservation_id)
            if any(
                event["reservationId"] == reservation_id
                and event["eventType"]
                in {
                    "construction-succeeded",
                    "construction-failed",
                    "reservation-reconciled",
                    "thread-bound",
                    "turn-bound",
                }
                for event in events
            ):
                raise DispatchGateError(
                    "reservation already has a later lifecycle event"
                )
            if any(
                event.get("constructionId") == construction_id
                for event in events
            ):
                raise DispatchGateError(
                    "construction identity already used"
                )
            return self._append_unlocked(
                events,
                {
                    "schema": 1,
                    "eventType": "construction-succeeded",
                    "candidateId": reservation["candidateId"],
                    "candidateIdentitySha256": reservation[
                        "candidateIdentitySha256"
                    ],
                    "protocolSha256": reservation["protocolSha256"],
                    "reservationId": reservation_id,
                    "ledgerAuthorityId": reservation["ledgerAuthorityId"],
                    "constructionId": construction_id,
                    "observedAt": observed_at,
                },
            )

    def record_construction_failure(
        self,
        *,
        reservation_id: str,
        failure_id: str,
        observed_at: str,
        failure_class: str,
    ) -> dict[str, Any]:
        self._require_identity(reservation_id, "reservation identity")
        self._require_identity(failure_id, "failure identity")
        self._require_identity(observed_at, "observation time")
        if failure_class not in {
            "factory-raised",
            "factory-returned-invalid-handle",
            "handle-validation-raised",
            "handle-validation-rejected",
            "handle-validation-result-invalid",
        }:
            raise DispatchGateError("construction failure class is invalid")
        with _exclusive_lock(self.lock_path):
            events = self._read_unlocked()
            reservation = self._reservation(events, reservation_id)
            if any(
                event["reservationId"] == reservation_id
                and event["eventType"]
                in {
                    "construction-succeeded",
                    "construction-failed",
                    "reservation-reconciled",
                    "thread-bound",
                    "turn-bound",
                }
                for event in events
            ):
                raise DispatchGateError(
                    "reservation already has a later lifecycle event"
                )
            if any(event.get("failureId") == failure_id for event in events):
                raise DispatchGateError("failure identity already used")
            return self._append_unlocked(
                events,
                {
                    "schema": 1,
                    "eventType": "construction-failed",
                    "candidateId": reservation["candidateId"],
                    "candidateIdentitySha256": reservation[
                        "candidateIdentitySha256"
                    ],
                    "protocolSha256": reservation["protocolSha256"],
                    "reservationId": reservation_id,
                    "ledgerAuthorityId": reservation["ledgerAuthorityId"],
                    "failureId": failure_id,
                    "failureClass": failure_class,
                    "observedAt": observed_at,
                },
            )

    def read_reservation_status(
        self,
        *,
        reservation_id: str,
    ) -> dict[str, Any]:
        self._require_identity(reservation_id, "reservation identity")
        with _exclusive_lock(self.lock_path):
            events = self._read_unlocked()
            reservation = self._reservation(events, reservation_id)
            failure = next(
                (
                    event
                    for event in events
                    if event["eventType"] == "construction-failed"
                    and event["reservationId"] == reservation_id
                ),
                None,
            )
            reconciliation = next(
                (
                    event
                    for event in events
                    if event["eventType"] == "reservation-reconciled"
                    and event["reservationId"] == reservation_id
                ),
                None,
            )
            success = next(
                (
                    event
                    for event in events
                    if event["eventType"] == "construction-succeeded"
                    and event["reservationId"] == reservation_id
                ),
                None,
            )
            status = "reserved-without-construction-outcome"
            if success is not None:
                status = "construction-succeeded"
            if failure is not None:
                status = "construction-failed"
            if reconciliation is not None:
                status = "reconciled-retained-consumed"
            return {
                "reservationId": reservation_id,
                "candidateId": reservation["candidateId"],
                "ledgerAuthorityId": reservation["ledgerAuthorityId"],
                "status": status,
                "reservationEventSha256": reservation["eventSha256"],
                "constructionOutcomeRecorded": (
                    success is not None or failure is not None
                ),
                "manualRecoveryRequired": (
                    success is None
                    and failure is None
                    and reconciliation is None
                ),
                "failureEventSha256": (
                    failure["eventSha256"] if failure is not None else None
                ),
                "constructionEventSha256": (
                    success["eventSha256"] if success is not None else None
                ),
                "reconciliationEventSha256": (
                    reconciliation["eventSha256"]
                    if reconciliation is not None
                    else None
                ),
                "dispatchCapConsumed": True,
                "replacementAuthorized": False,
                "automaticReleaseAuthorized": False,
                "automaticRetryAuthorized": False,
            }

    def reconcile_failed_reservation(
        self,
        *,
        reconciliation_document_path: Path,
        observed_at: str,
    ) -> dict[str, Any]:
        self._require_identity(observed_at, "observation time")
        path = reconciliation_document_path.resolve()
        try:
            raw = path.read_bytes()
            document = json.loads(raw.decode("utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise DispatchGateError(
                "reconciliation document is not readable valid JSON"
            ) from error
        if not isinstance(document, dict):
            raise DispatchGateError(
                "reconciliation document must be an object"
            )
        if not (
            document.get("schema") == 1
            and document.get("kind")
            == "manual-stranded-reservation-reconciliation"
            and isinstance(document.get("reconciliationId"), str)
            and bool(document["reconciliationId"].strip())
            and isinstance(document.get("ledgerAuthorityId"), str)
            and bool(document["ledgerAuthorityId"].strip())
            and isinstance(document.get("candidateId"), str)
            and bool(document["candidateId"].strip())
            and isinstance(document.get("reservationId"), str)
            and bool(document["reservationId"].strip())
            and _is_sha256(document.get("failureEventSha256"))
            and document.get("disposition") == "retain-consumed-no-retry"
            and document.get("replacementDispatchAuthorized") is False
            and document.get("reservationReleaseAuthorized") is False
        ):
            raise DispatchGateError(
                "manual reconciliation boundary is not satisfied"
            )
        with _exclusive_lock(self.lock_path):
            events = self._read_unlocked()
            reservation = self._reservation(
                events,
                document["reservationId"],
            )
            failure = next(
                (
                    event
                    for event in events
                    if event["eventType"] == "construction-failed"
                    and event["reservationId"]
                    == document["reservationId"]
                ),
                None,
            )
            if not (
                failure is not None
                and failure["eventSha256"]
                == document["failureEventSha256"]
                and reservation["candidateId"] == document["candidateId"]
                and reservation["ledgerAuthorityId"]
                == document["ledgerAuthorityId"]
                and not any(
                    event["eventType"] == "reservation-reconciled"
                    and event["reservationId"] == document["reservationId"]
                    for event in events
                )
                and not any(
                    event.get("reconciliationId")
                    == document["reconciliationId"]
                    for event in events
                )
            ):
                raise DispatchGateError(
                    "manual reconciliation evidence is mismatched or reused"
                )
            return self._append_unlocked(
                events,
                {
                    "schema": 1,
                    "eventType": "reservation-reconciled",
                    "candidateId": reservation["candidateId"],
                    "candidateIdentitySha256": reservation[
                        "candidateIdentitySha256"
                    ],
                    "protocolSha256": reservation["protocolSha256"],
                    "reservationId": reservation["reservationId"],
                    "ledgerAuthorityId": reservation["ledgerAuthorityId"],
                    "failureEventSha256": failure["eventSha256"],
                    "reconciliationId": document["reconciliationId"],
                    "reconciliationDocumentSha256": hashlib.sha256(
                        raw
                    ).hexdigest(),
                    "disposition": "retain-consumed-no-retry",
                    "observedAt": observed_at,
                },
            )

    def reconcile_missing_construction_outcome(
        self,
        *,
        reconciliation_document_path: Path,
        observed_at: str,
    ) -> dict[str, Any]:
        self._require_identity(observed_at, "observation time")
        path = reconciliation_document_path.resolve()
        try:
            raw = path.read_bytes()
            document = json.loads(raw.decode("utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise DispatchGateError(
                "reconciliation document is not readable valid JSON"
            ) from error
        if not isinstance(document, dict):
            raise DispatchGateError(
                "reconciliation document must be an object"
            )
        if not (
            document.get("schema") == 1
            and document.get("kind")
            == "manual-missing-construction-outcome-reconciliation"
            and isinstance(document.get("reconciliationId"), str)
            and bool(document["reconciliationId"].strip())
            and isinstance(document.get("ledgerAuthorityId"), str)
            and bool(document["ledgerAuthorityId"].strip())
            and isinstance(document.get("candidateId"), str)
            and bool(document["candidateId"].strip())
            and isinstance(document.get("reservationId"), str)
            and bool(document["reservationId"].strip())
            and _is_sha256(document.get("reservationEventSha256"))
            and document.get("constructionOutcomeRecorded") is False
            and document.get("disposition") == "retain-consumed-no-retry"
            and document.get("replacementDispatchAuthorized") is False
            and document.get("reservationReleaseAuthorized") is False
        ):
            raise DispatchGateError(
                "manual missing-outcome reconciliation boundary is not satisfied"
            )
        with _exclusive_lock(self.lock_path):
            events = self._read_unlocked()
            reservation = self._reservation(
                events,
                document["reservationId"],
            )
            if not (
                reservation["eventSha256"]
                == document["reservationEventSha256"]
                and reservation["candidateId"] == document["candidateId"]
                and reservation["ledgerAuthorityId"]
                == document["ledgerAuthorityId"]
                and not any(
                    event["reservationId"] == document["reservationId"]
                    and event["eventType"]
                    in {
                        "construction-succeeded",
                        "construction-failed",
                        "reservation-reconciled",
                        "thread-bound",
                        "turn-bound",
                    }
                    for event in events
                )
                and not any(
                    event.get("reconciliationId")
                    == document["reconciliationId"]
                    for event in events
                )
            ):
                raise DispatchGateError(
                    "manual missing-outcome reconciliation evidence is mismatched or reused"
                )
            return self._append_unlocked(
                events,
                {
                    "schema": 1,
                    "eventType": "reservation-reconciled",
                    "candidateId": reservation["candidateId"],
                    "candidateIdentitySha256": reservation[
                        "candidateIdentitySha256"
                    ],
                    "protocolSha256": reservation["protocolSha256"],
                    "reservationId": reservation["reservationId"],
                    "ledgerAuthorityId": reservation["ledgerAuthorityId"],
                    "reservationEventSha256": reservation["eventSha256"],
                    "reconciliationClass": (
                        "missing-construction-outcome"
                    ),
                    "reconciliationId": document["reconciliationId"],
                    "reconciliationDocumentSha256": hashlib.sha256(
                        raw
                    ).hexdigest(),
                    "disposition": "retain-consumed-no-retry",
                    "observedAt": observed_at,
                },
            )

    def bind_thread(
        self,
        *,
        reservation_id: str,
        thread_id: str,
        observed_at: str,
    ) -> dict[str, Any]:
        self._require_identity(reservation_id, "reservation identity")
        self._require_identity(thread_id, "thread identity")
        self._require_identity(observed_at, "observation time")
        with _exclusive_lock(self.lock_path):
            events = self._read_unlocked()
            reservation = self._reservation(events, reservation_id)
            if any(
                event["eventType"] == "thread-bound"
                and event["reservationId"] == reservation_id
                for event in events
            ):
                raise DispatchGateError("thread already bound")
            if any(
                event["eventType"]
                in {"construction-failed", "reservation-reconciled"}
                and event["reservationId"] == reservation_id
                for event in events
            ):
                raise DispatchGateError(
                    "failed reservation cannot bind a thread"
                )
            if not any(
                event["eventType"] == "construction-succeeded"
                and event["reservationId"] == reservation_id
                for event in events
            ):
                raise DispatchGateError(
                    "construction has not succeeded"
                )
            if any(
                event.get("threadId") == thread_id
                for event in events
            ):
                raise DispatchGateError("thread identity already used")
            return self._append_unlocked(
                events,
                {
                    "schema": 1,
                    "eventType": "thread-bound",
                    "candidateId": reservation["candidateId"],
                    "candidateIdentitySha256": reservation[
                        "candidateIdentitySha256"
                    ],
                    "protocolSha256": reservation["protocolSha256"],
                    "reservationId": reservation_id,
                    "threadId": thread_id,
                    "observedAt": observed_at,
                },
            )

    def bind_turn(
        self,
        *,
        reservation_id: str,
        thread_id: str,
        turn_id: str,
        observed_at: str,
    ) -> dict[str, Any]:
        self._require_identity(reservation_id, "reservation identity")
        self._require_identity(thread_id, "thread identity")
        self._require_identity(turn_id, "turn identity")
        self._require_identity(observed_at, "observation time")
        with _exclusive_lock(self.lock_path):
            events = self._read_unlocked()
            reservation = self._reservation(events, reservation_id)
            if any(
                event["eventType"] == "turn-bound"
                and event["reservationId"] == reservation_id
                for event in events
            ):
                raise DispatchGateError("turn already bound")
            thread = next(
                (
                    event
                    for event in events
                    if event["eventType"] == "thread-bound"
                    and event["reservationId"] == reservation_id
                ),
                None,
            )
            if thread is None or thread.get("threadId") != thread_id:
                raise DispatchGateError(
                    "thread binding is missing or mismatched"
                )
            if any(event.get("turnId") == turn_id for event in events):
                raise DispatchGateError("turn identity already used")
            return self._append_unlocked(
                events,
                {
                    "schema": 1,
                    "eventType": "turn-bound",
                    "candidateId": reservation["candidateId"],
                    "candidateIdentitySha256": reservation[
                        "candidateIdentitySha256"
                    ],
                    "protocolSha256": reservation["protocolSha256"],
                    "reservationId": reservation_id,
                    "threadId": thread_id,
                    "turnId": turn_id,
                    "observedAt": observed_at,
                },
            )

    def _read_unlocked(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        events: list[dict[str, Any]] = []
        for line_number, raw_line in enumerate(
            self.path.read_bytes().splitlines(),
            start=1,
        ):
            try:
                event = json.loads(raw_line.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as error:
                raise DispatchGateError(
                    f"invalid JSON at ledger line {line_number}"
                ) from error
            if not isinstance(event, dict):
                raise DispatchGateError(
                    f"ledger line {line_number} is not an object"
                )
            events.append(event)
        self._validate_events(events)
        return events

    def _validate_events(self, events: list[dict[str, Any]]) -> None:
        reservations: dict[str, dict[str, Any]] = {}
        candidate_ids: set[str] = set()
        construction_ids: set[str] = set()
        failure_ids: set[str] = set()
        reconciliation_ids: set[str] = set()
        thread_ids: set[str] = set()
        turn_ids: set[str] = set()
        previous_sha256 = ZERO_SHA256
        for sequence, event in enumerate(events, start=1):
            if event.get("schema") != 1:
                raise DispatchGateError("ledger event schema drifted")
            if event.get("sequence") != sequence:
                raise DispatchGateError("ledger event sequence drifted")
            if event.get("previousEventSha256") != previous_sha256:
                raise DispatchGateError("ledger hash chain drifted")
            if event.get("eventType") not in ALLOWED_EVENT_TYPES:
                raise DispatchGateError("ledger event type is invalid")
            if event.get("eventSha256") != _event_sha256(event):
                raise DispatchGateError("ledger event hash drifted")
            reservation_id = event.get("reservationId")
            candidate_id = event.get("candidateId")
            self._require_identity(
                reservation_id,
                "reservation identity",
            )
            self._require_identity(candidate_id, "candidate identity")
            if not _is_sha256(event.get("candidateIdentitySha256")):
                raise DispatchGateError(
                    "ledger candidate identity SHA-256 is invalid"
                )
            if not _is_sha256(event.get("protocolSha256")):
                raise DispatchGateError(
                    "ledger protocol SHA-256 is invalid"
                )

            if event["eventType"] == "candidate-reserved":
                if (
                    reservation_id in reservations
                    or candidate_id in candidate_ids
                ):
                    raise DispatchGateError(
                        "ledger contains a duplicate candidate reservation"
                    )
                if (
                    event.get("exactCandidateExecutionAdmitted") is not True
                    or event.get(
                        "sourceAndToolchainReverifiedAtDispatch"
                    )
                    is not True
                ):
                    raise DispatchGateError(
                        "ledger reservation lacks dispatch preconditions"
                    )
                authorization_payload = {
                    "schema": 1,
                    "candidateId": candidate_id,
                    "candidateIdentitySha256": event[
                        "candidateIdentitySha256"
                    ],
                    "protocolFileSha256": event["protocolSha256"],
                    "sourceGovernancePreflightFileSha256": event.get(
                        "sourceGovernancePreflightFileSha256"
                    ),
                    "staticGapAuditFileSha256": event.get(
                        "staticGapAuditFileSha256"
                    ),
                    "diagnosticAdmissionFileSha256": event.get(
                        "diagnosticAdmissionFileSha256"
                    ),
                    "diagnosticAdmissionId": event.get(
                        "diagnosticAdmissionId"
                    ),
                    "ledgerAuthorityDocument": event.get(
                        "ledgerAuthorityDocument"
                    ),
                    "ledgerAuthorityDocumentSha256": event.get(
                        "ledgerAuthorityDocumentSha256"
                    ),
                    "ledgerAuthorityId": event.get("ledgerAuthorityId"),
                    "ledgerRelativePath": event.get("ledgerRelativePath"),
                    "observedAt": event.get("observedAt"),
                    "exactCandidateExecutionAdmitted": True,
                    "sourceAndToolchainReverifiedAtDispatch": True,
                }
                if not (
                    all(
                        _is_sha256(authorization_payload.get(key))
                        for key in (
                            "sourceGovernancePreflightFileSha256",
                            "staticGapAuditFileSha256",
                            "diagnosticAdmissionFileSha256",
                            "ledgerAuthorityDocumentSha256",
                        )
                    )
                    and isinstance(
                        authorization_payload["diagnosticAdmissionId"],
                        str,
                    )
                    and bool(
                        authorization_payload[
                            "diagnosticAdmissionId"
                        ].strip()
                    )
                    and all(
                        isinstance(authorization_payload.get(key), str)
                        and bool(authorization_payload[key].strip())
                        for key in (
                            "ledgerAuthorityDocument",
                            "ledgerAuthorityId",
                            "ledgerRelativePath",
                        )
                    )
                    and event.get("authorizationSha256")
                    == _canonical_sha256(authorization_payload)
                ):
                    raise DispatchGateError(
                        "ledger reservation authorization binding is invalid"
                    )
                reservations[reservation_id] = event
                candidate_ids.add(candidate_id)
            elif event["eventType"] == "construction-succeeded":
                reservation = reservations.get(reservation_id)
                construction_id = event.get("constructionId")
                if (
                    reservation is None
                    or candidate_id != reservation["candidateId"]
                    or event.get("ledgerAuthorityId")
                    != reservation.get("ledgerAuthorityId")
                    or not isinstance(construction_id, str)
                    or not construction_id
                    or construction_id in construction_ids
                    or any(
                        prior["reservationId"] == reservation_id
                        and prior["eventType"]
                        in {
                            "construction-succeeded",
                            "construction-failed",
                            "reservation-reconciled",
                            "thread-bound",
                            "turn-bound",
                        }
                        for prior in events[: sequence - 1]
                    )
                ):
                    raise DispatchGateError(
                        "ledger construction success is invalid"
                    )
                construction_ids.add(construction_id)
            elif event["eventType"] == "construction-failed":
                reservation = reservations.get(reservation_id)
                failure_id = event.get("failureId")
                if (
                    reservation is None
                    or candidate_id != reservation["candidateId"]
                    or event.get("ledgerAuthorityId")
                    != reservation.get("ledgerAuthorityId")
                    or not isinstance(failure_id, str)
                    or not failure_id
                    or failure_id in failure_ids
                    or event.get("failureClass")
                    not in {
                        "factory-raised",
                        "factory-returned-invalid-handle",
                        "handle-validation-raised",
                        "handle-validation-rejected",
                        "handle-validation-result-invalid",
                    }
                    or any(
                        prior["reservationId"] == reservation_id
                        and prior["eventType"]
                        in {
                            "construction-succeeded",
                            "construction-failed",
                            "reservation-reconciled",
                            "thread-bound",
                            "turn-bound",
                        }
                        for prior in events[: sequence - 1]
                    )
                ):
                    raise DispatchGateError(
                        "ledger construction failure is invalid"
                    )
                failure_ids.add(failure_id)
            elif event["eventType"] == "reservation-reconciled":
                reservation = reservations.get(reservation_id)
                reconciliation_id = event.get("reconciliationId")
                reconciliation_class = event.get(
                    "reconciliationClass",
                    "recorded-construction-failure",
                )
                failure = next(
                    (
                        prior
                        for prior in events[: sequence - 1]
                        if prior["eventType"] == "construction-failed"
                        and prior["reservationId"] == reservation_id
                    ),
                    None,
                )
                if (
                    reservation is None
                    or candidate_id != reservation["candidateId"]
                    or event.get("ledgerAuthorityId")
                    != reservation.get("ledgerAuthorityId")
                    or not isinstance(reconciliation_id, str)
                    or not reconciliation_id
                    or reconciliation_id in reconciliation_ids
                    or not _is_sha256(
                        event.get("reconciliationDocumentSha256")
                    )
                    or event.get("disposition")
                    != "retain-consumed-no-retry"
                    or any(
                        prior["eventType"] == "reservation-reconciled"
                        and prior["reservationId"] == reservation_id
                        for prior in events[: sequence - 1]
                    )
                ):
                    raise DispatchGateError(
                        "ledger reconciliation event is invalid"
                    )
                if reconciliation_class == "recorded-construction-failure":
                    if (
                        failure is None
                        or event.get("failureEventSha256")
                        != failure["eventSha256"]
                        or event.get("reservationEventSha256") is not None
                    ):
                        raise DispatchGateError(
                            "ledger failure reconciliation is invalid"
                        )
                elif reconciliation_class == "missing-construction-outcome":
                    if (
                        failure is not None
                        or event.get("failureEventSha256") is not None
                        or event.get("reservationEventSha256")
                        != reservation["eventSha256"]
                        or any(
                            prior["reservationId"] == reservation_id
                            and prior["eventType"]
                            in {
                                "construction-succeeded",
                                "construction-failed",
                                "reservation-reconciled",
                                "thread-bound",
                                "turn-bound",
                            }
                            for prior in events[: sequence - 1]
                        )
                    ):
                        raise DispatchGateError(
                            "ledger missing-outcome reconciliation is invalid"
                        )
                else:
                    raise DispatchGateError(
                        "ledger reconciliation class is invalid"
                    )
                reconciliation_ids.add(reconciliation_id)
            elif event["eventType"] == "thread-bound":
                reservation = reservations.get(reservation_id)
                thread_id = event.get("threadId")
                construction = next(
                    (
                        prior
                        for prior in events[: sequence - 1]
                        if prior["eventType"] == "construction-succeeded"
                        and prior["reservationId"] == reservation_id
                    ),
                    None,
                )
                if (
                    reservation is None
                    or construction is None
                    or candidate_id != reservation["candidateId"]
                    or thread_id in thread_ids
                    or not isinstance(thread_id, str)
                    or not thread_id
                    or any(
                        prior["eventType"] == "thread-bound"
                        and prior["reservationId"] == reservation_id
                        for prior in events[: sequence - 1]
                    )
                    or any(
                        prior["eventType"]
                        in {"construction-failed", "reservation-reconciled"}
                        and prior["reservationId"] == reservation_id
                        for prior in events[: sequence - 1]
                    )
                ):
                    raise DispatchGateError(
                        "ledger thread binding is invalid"
                    )
                thread_ids.add(thread_id)
            elif event["eventType"] == "turn-bound":
                reservation = reservations.get(reservation_id)
                thread_id = event.get("threadId")
                turn_id = event.get("turnId")
                bound_thread = next(
                    (
                        prior
                        for prior in events[: sequence - 1]
                        if prior["eventType"] == "thread-bound"
                        and prior["reservationId"] == reservation_id
                    ),
                    None,
                )
                if (
                    reservation is None
                    or bound_thread is None
                    or thread_id != bound_thread.get("threadId")
                    or turn_id in turn_ids
                    or not isinstance(turn_id, str)
                    or not turn_id
                    or any(
                        prior["eventType"] == "turn-bound"
                        and prior["reservationId"] == reservation_id
                        for prior in events[: sequence - 1]
                    )
                ):
                    raise DispatchGateError(
                        "ledger turn binding is invalid"
                    )
                turn_ids.add(turn_id)
            else:
                raise DispatchGateError("ledger event type is invalid")
            previous_sha256 = event["eventSha256"]

    def _append_unlocked(
        self,
        events: list[dict[str, Any]],
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        event = {
            **payload,
            "sequence": len(events) + 1,
            "previousEventSha256": (
                events[-1]["eventSha256"]
                if events
                else ZERO_SHA256
            ),
        }
        event["eventSha256"] = _event_sha256(event)
        self._validate_events([*events, event])
        self.path.parent.mkdir(parents=True, exist_ok=True)
        encoded = (
            json.dumps(
                event,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n"
        ).encode("utf-8")
        with self.path.open("ab") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        return event

    @staticmethod
    def _reservation(
        events: list[dict[str, Any]],
        reservation_id: str,
    ) -> dict[str, Any]:
        reservation = next(
            (
                event
                for event in events
                if event["eventType"] == "candidate-reserved"
                and event["reservationId"] == reservation_id
            ),
            None,
        )
        if reservation is None:
            raise DispatchGateError("candidate reservation is missing")
        return reservation

    @staticmethod
    def _require_identity(value: Any, label: str) -> None:
        if not isinstance(value, str) or not value.strip():
            raise DispatchGateError(f"{label} is required")
