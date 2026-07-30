#!/usr/bin/env python3
"""One-shot dispatch ledger for the chained-transform fidelity calibration.

The ledger is intentionally narrower than a general job manager.  It records
one immutable authorization reservation and at most one dispatch attempt for
each of the three protocol hops.  A failed, ambiguous, or interrupted attempt
remains consumed and cannot be retried or replaced automatically.
"""

from __future__ import annotations

from datetime import datetime
import json
import os
from pathlib import Path
from typing import Any

try:
    from .human_ai_collaboration_tdd_noncomparative_dispatch_identity_ledger import (
        ZERO_SHA256,
        _canonical_sha256,
        _event_sha256,
        _exclusive_lock,
    )
    from .process_fidelity_chained_transform_dispatch_gate import (
        HOP_IDS,
        validate_dispatch_authorization_envelope,
    )
except ImportError:
    from human_ai_collaboration_tdd_noncomparative_dispatch_identity_ledger import (
        ZERO_SHA256,
        _canonical_sha256,
        _event_sha256,
        _exclusive_lock,
    )
    from process_fidelity_chained_transform_dispatch_gate import (
        HOP_IDS,
        validate_dispatch_authorization_envelope,
    )


ALLOWED_EVENT_TYPES = {
    "run-reserved",
    "hop-dispatch-started",
    "hop-terminal-recorded",
    "reservation-reconciled",
}
ALLOWED_TERMINAL_STATUSES = {
    "completed-valid",
    "failed",
    "ambiguous",
}
COMMON_EVENT_KEYS = {
    "schema",
    "sequence",
    "eventType",
    "reservationId",
    "authorizationSha256",
    "runId",
    "authorityId",
    "authorityNonce",
    "observedAt",
    "previousEventSha256",
    "eventSha256",
}
EVENT_SPECIFIC_KEYS = {
    "run-reserved": {
        "rawEvidenceRoot",
        "sourceBindingSha256",
        "runCellSha256",
        "routeBindingSha256",
        "dispatchNonces",
        "automaticRetryAllowed",
        "replacementDispatchAllowed",
        "reservationDisposition",
    },
    "hop-dispatch-started": {
        "hopId",
        "hopSequence",
        "dispatchNonce",
        "startId",
        "threadId",
        "turnStartRequestId",
        "modelDispatchCount",
    },
    "hop-terminal-recorded": {
        "hopId",
        "hopSequence",
        "startEventSha256",
        "terminalId",
        "threadId",
        "turnId",
        "terminalStatus",
        "receiptSha256",
        "errorEvidenceSha256",
    },
    "reservation-reconciled": {
        "hopId",
        "hopSequence",
        "terminalEventSha256",
        "reconciliationId",
        "reconciliationDocumentSha256",
        "disposition",
    },
}


class DispatchLedgerError(RuntimeError):
    """Raised when a one-shot transition cannot be proved or recorded."""


def _is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _require_identity(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DispatchLedgerError(f"{label} is required")
    return value


def _parse_time(value: Any, label: str) -> datetime:
    if not isinstance(value, str):
        raise DispatchLedgerError(f"{label} is missing")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise DispatchLedgerError(f"{label} is invalid") from error
    if parsed.tzinfo is None:
        raise DispatchLedgerError(f"{label} must include an offset")
    return parsed


def _reservation_fields(envelope: dict[str, Any]) -> dict[str, Any]:
    authorization = envelope.get("authorizationDocument", {})
    return {
        "authorizationSha256": envelope.get("authorizationSha256"),
        "runId": envelope.get("cell", {}).get("runId"),
        "authorityId": authorization.get("authorityId"),
        "authorityNonce": authorization.get("nonce"),
    }


class ChainedTransformDispatchLedger:
    """Append and validate one-run dispatch transitions under one file lock."""

    def __init__(self, path: Path) -> None:
        self.path = path.resolve()
        self.lock_path = self.path.with_name(self.path.name + ".lock")

    def read_events(self) -> list[dict[str, Any]]:
        with _exclusive_lock(self.lock_path):
            return self._read_unlocked()

    def zero_dispatch_preflight(
        self,
        *,
        envelope: dict[str, Any],
        observed_at: str,
    ) -> dict[str, Any]:
        """Return a race-prone advisory snapshot without reserving or dispatching."""

        failures = self._validate_reservation_input(
            envelope=envelope,
            observed_at=observed_at,
        )
        with _exclusive_lock(self.lock_path):
            events = self._read_unlocked()
            failures.extend(self._reservation_collisions(events, envelope))
        unique_failures = list(dict.fromkeys(failures))
        return {
            "schema": 1,
            "kind": "chained-transform-zero-dispatch-preflight",
            "authorizationSha256": envelope.get("authorizationSha256"),
            "runId": envelope.get("cell", {}).get("runId"),
            "observedAt": observed_at,
            "modelDispatchCount": 0,
            "modelCalled": False,
            "ledgerMutationPerformed": False,
            "advisoryOnly": True,
            "reservationWouldBeAccepted": not unique_failures,
            "failures": unique_failures,
            "liveDispatchReady": False,
        }

    def reserve(
        self,
        *,
        envelope: dict[str, Any],
        reservation_id: str,
        observed_at: str,
    ) -> dict[str, Any]:
        """Atomically consume one authorization, run cell, and nonce set."""

        _require_identity(reservation_id, "reservation identity")
        failures = self._validate_reservation_input(
            envelope=envelope,
            observed_at=observed_at,
        )
        if failures:
            raise DispatchLedgerError(
                "dispatch envelope is not reservable: " + ",".join(failures)
            )
        fields = _reservation_fields(envelope)
        with _exclusive_lock(self.lock_path):
            events = self._read_unlocked()
            collisions = self._reservation_collisions(events, envelope)
            if any(
                event["reservationId"] == reservation_id
                for event in events
            ):
                collisions.append("duplicate-reservation-id")
            if collisions:
                raise DispatchLedgerError(
                    "dispatch reservation collision: "
                    + ",".join(dict.fromkeys(collisions))
                )
            payload = {
                "schema": 1,
                "eventType": "run-reserved",
                "reservationId": reservation_id,
                **fields,
                "observedAt": observed_at,
                "rawEvidenceRoot": envelope["rawEvidenceRoot"],
                "sourceBindingSha256": _canonical_sha256(
                    envelope["bindings"]
                ),
                "runCellSha256": _canonical_sha256(envelope["cell"]),
                "routeBindingSha256": _canonical_sha256(
                    envelope["route"]
                ),
                "dispatchNonces": {
                    item["hopId"]: item["dispatchNonce"]
                    for item in envelope["stageAuthorizations"]
                },
                "automaticRetryAllowed": False,
                "replacementDispatchAllowed": False,
                "reservationDisposition": (
                    "consumed-on-reservation-no-automatic-release"
                ),
            }
            return self._append_unlocked(events, payload)

    def record_hop_started(
        self,
        *,
        reservation_id: str,
        hop_id: str,
        dispatch_nonce: str,
        start_id: str,
        thread_id: str,
        turn_start_request_id: str,
        observed_at: str,
    ) -> dict[str, Any]:
        """Atomically consume the next hop's sole dispatch nonce."""

        for value, label in (
            (reservation_id, "reservation identity"),
            (start_id, "start identity"),
            (thread_id, "thread identity"),
            (turn_start_request_id, "turn-start request identity"),
        ):
            _require_identity(value, label)
        _parse_time(observed_at, "observedAt")
        if hop_id not in HOP_IDS:
            raise DispatchLedgerError("hop identity is invalid")
        with _exclusive_lock(self.lock_path):
            events = self._read_unlocked()
            reservation = self._reservation(events, reservation_id)
            reservation_events = self._events_for(events, reservation_id)
            expected_hop = self._next_hop(reservation_events)
            if expected_hop != hop_id:
                raise DispatchLedgerError(
                    "hop is not the next one-shot dispatch"
                )
            if reservation["dispatchNonces"].get(hop_id) != dispatch_nonce:
                raise DispatchLedgerError("dispatch nonce is invalid")
            if any(
                event.get("startId") == start_id
                or event.get("threadId") == thread_id
                or event.get("turnStartRequestId")
                == turn_start_request_id
                for event in events
                if event["eventType"] == "hop-dispatch-started"
            ):
                raise DispatchLedgerError(
                    "dispatch identity has already been consumed"
                )
            return self._append_unlocked(
                events,
                {
                    "schema": 1,
                    "eventType": "hop-dispatch-started",
                    "reservationId": reservation_id,
                    **self._lineage_fields(reservation),
                    "observedAt": observed_at,
                    "hopId": hop_id,
                    "hopSequence": HOP_IDS.index(hop_id) + 1,
                    "dispatchNonce": dispatch_nonce,
                    "startId": start_id,
                    "threadId": thread_id,
                    "turnStartRequestId": turn_start_request_id,
                    "modelDispatchCount": 1,
                },
            )

    def record_hop_terminal(
        self,
        *,
        reservation_id: str,
        hop_id: str,
        terminal_id: str,
        turn_id: str,
        terminal_status: str,
        receipt_sha256: str | None,
        error_evidence_sha256: str | None,
        observed_at: str,
    ) -> dict[str, Any]:
        """Record exactly one terminal classification for a started hop."""

        for value, label in (
            (reservation_id, "reservation identity"),
            (terminal_id, "terminal identity"),
            (turn_id, "turn identity"),
        ):
            _require_identity(value, label)
        _parse_time(observed_at, "observedAt")
        if hop_id not in HOP_IDS:
            raise DispatchLedgerError("hop identity is invalid")
        if terminal_status not in ALLOWED_TERMINAL_STATUSES:
            raise DispatchLedgerError("terminal status is invalid")
        if terminal_status == "completed-valid":
            if not _is_sha256(receipt_sha256) or error_evidence_sha256 is not None:
                raise DispatchLedgerError(
                    "completed terminal requires only a receipt SHA-256"
                )
        elif not (
            receipt_sha256 is None and _is_sha256(error_evidence_sha256)
        ):
            raise DispatchLedgerError(
                "non-completed terminal requires only an error evidence SHA-256"
            )
        with _exclusive_lock(self.lock_path):
            events = self._read_unlocked()
            reservation = self._reservation(events, reservation_id)
            reservation_events = self._events_for(events, reservation_id)
            start = next(
                (
                    event
                    for event in reservation_events
                    if event["eventType"] == "hop-dispatch-started"
                    and event["hopId"] == hop_id
                ),
                None,
            )
            if start is None:
                raise DispatchLedgerError("hop start is missing")
            if any(
                event["eventType"] == "hop-terminal-recorded"
                and event["hopId"] == hop_id
                for event in reservation_events
            ):
                raise DispatchLedgerError("hop terminal already exists")
            if any(
                event.get("terminalId") == terminal_id
                for event in events
                if event["eventType"] == "hop-terminal-recorded"
            ):
                raise DispatchLedgerError(
                    "terminal identity has already been consumed"
                )
            if any(
                event.get("turnId") == turn_id
                for event in events
                if event["eventType"] == "hop-terminal-recorded"
            ):
                raise DispatchLedgerError(
                    "turn identity has already been consumed"
                )
            return self._append_unlocked(
                events,
                {
                    "schema": 1,
                    "eventType": "hop-terminal-recorded",
                    "reservationId": reservation_id,
                    **self._lineage_fields(reservation),
                    "observedAt": observed_at,
                    "hopId": hop_id,
                    "hopSequence": HOP_IDS.index(hop_id) + 1,
                    "startEventSha256": start["eventSha256"],
                    "terminalId": terminal_id,
                    "threadId": start["threadId"],
                    "turnId": turn_id,
                    "terminalStatus": terminal_status,
                    "receiptSha256": receipt_sha256,
                    "errorEvidenceSha256": error_evidence_sha256,
                },
            )

    def reconcile_ambiguous(
        self,
        *,
        reservation_id: str,
        reconciliation_id: str,
        reconciliation_document_sha256: str,
        observed_at: str,
    ) -> dict[str, Any]:
        """Retain an ambiguous attempt as consumed; never release it."""

        _require_identity(reservation_id, "reservation identity")
        _require_identity(reconciliation_id, "reconciliation identity")
        _parse_time(observed_at, "observedAt")
        if not _is_sha256(reconciliation_document_sha256):
            raise DispatchLedgerError(
                "reconciliation document SHA-256 is invalid"
            )
        with _exclusive_lock(self.lock_path):
            events = self._read_unlocked()
            reservation = self._reservation(events, reservation_id)
            reservation_events = self._events_for(events, reservation_id)
            ambiguous = next(
                (
                    event
                    for event in reservation_events
                    if event["eventType"] == "hop-terminal-recorded"
                    and event["terminalStatus"] == "ambiguous"
                ),
                None,
            )
            if ambiguous is None:
                raise DispatchLedgerError(
                    "ambiguous terminal is required for reconciliation"
                )
            if any(
                event["eventType"] == "reservation-reconciled"
                for event in reservation_events
            ):
                raise DispatchLedgerError(
                    "reservation reconciliation already exists"
                )
            if any(
                event.get("reconciliationId") == reconciliation_id
                for event in events
                if event["eventType"] == "reservation-reconciled"
            ):
                raise DispatchLedgerError(
                    "reconciliation identity has already been consumed"
                )
            return self._append_unlocked(
                events,
                {
                    "schema": 1,
                    "eventType": "reservation-reconciled",
                    "reservationId": reservation_id,
                    **self._lineage_fields(reservation),
                    "observedAt": observed_at,
                    "hopId": ambiguous["hopId"],
                    "hopSequence": ambiguous["hopSequence"],
                    "terminalEventSha256": ambiguous["eventSha256"],
                    "reconciliationId": reconciliation_id,
                    "reconciliationDocumentSha256": (
                        reconciliation_document_sha256
                    ),
                    "disposition": "retain-consumed-no-retry",
                },
            )

    def read_reservation_status(
        self,
        reservation_id: str,
    ) -> dict[str, Any]:
        _require_identity(reservation_id, "reservation identity")
        with _exclusive_lock(self.lock_path):
            events = self._read_unlocked()
            reservation = self._reservation(events, reservation_id)
            reservation_events = self._events_for(events, reservation_id)
            terminals = [
                event
                for event in reservation_events
                if event["eventType"] == "hop-terminal-recorded"
            ]
            reconciliation = next(
                (
                    event
                    for event in reservation_events
                    if event["eventType"] == "reservation-reconciled"
                ),
                None,
            )
            blocked = next(
                (
                    event
                    for event in terminals
                    if event["terminalStatus"] in {"failed", "ambiguous"}
                ),
                None,
            )
            next_hop = self._next_hop(reservation_events)
            return {
                "schema": 1,
                "kind": "chained-transform-dispatch-reservation-status",
                "reservationId": reservation_id,
                "authorizationSha256": reservation["authorizationSha256"],
                "runId": reservation["runId"],
                "modelDispatchCount": sum(
                    event["modelDispatchCount"]
                    for event in reservation_events
                    if event["eventType"] == "hop-dispatch-started"
                ),
                "completedValidHopCount": sum(
                    event["terminalStatus"] == "completed-valid"
                    for event in terminals
                ),
                "nextHopId": next_hop,
                "blocked": blocked is not None,
                "blockedTerminalStatus": (
                    blocked["terminalStatus"] if blocked else None
                ),
                "ambiguousReconciled": bool(
                    blocked
                    and blocked["terminalStatus"] == "ambiguous"
                    and reconciliation
                ),
                "automaticRetryAllowed": False,
                "replacementDispatchAllowed": False,
                "formalCohortEligible": False,
                "liveDispatchReady": next_hop is not None,
                "ledgerTailSha256": events[-1]["eventSha256"],
            }

    def _validate_reservation_input(
        self,
        *,
        envelope: dict[str, Any],
        observed_at: str,
    ) -> list[str]:
        failures = list(validate_dispatch_authorization_envelope(envelope))
        try:
            reservation_time = _parse_time(observed_at, "observedAt")
            envelope_time = _parse_time(
                envelope.get("observedAt"),
                "envelope observedAt",
            )
            authority_path = Path(
                envelope.get("authorizationDocument", {}).get("path", "")
            )
            authority = json.loads(authority_path.read_text(encoding="utf-8"))
            not_before = _parse_time(authority.get("notBefore"), "notBefore")
            expires_at = _parse_time(authority.get("expiresAt"), "expiresAt")
            route_time = _parse_time(
                envelope.get("route", {})
                .get("hostReportedEffectiveRoute", {})
                .get("observedAt"),
                "route observedAt",
            )
            if not (
                envelope_time <= reservation_time
                and not_before <= reservation_time <= expires_at
            ):
                failures.append("fail-reservation-authority-window")
            route_age = (reservation_time - route_time).total_seconds()
            if not 0 <= route_age <= 120:
                failures.append("fail-reservation-route-freshness")
        except (
            DispatchLedgerError,
            OSError,
            UnicodeDecodeError,
            json.JSONDecodeError,
            TypeError,
        ):
            failures.append("fail-reservation-time-revalidation")
        fields = _reservation_fields(envelope)
        if not (
            _is_sha256(fields["authorizationSha256"])
            and all(
                isinstance(fields[key], str) and bool(fields[key].strip())
                for key in ("runId", "authorityId", "authorityNonce")
            )
        ):
            failures.append("fail-reservation-identity")
        return list(dict.fromkeys(failures))

    @staticmethod
    def _reservation_collisions(
        events: list[dict[str, Any]],
        envelope: dict[str, Any],
    ) -> list[str]:
        fields = _reservation_fields(envelope)
        stage_nonces = {
            item.get("dispatchNonce")
            for item in envelope.get("stageAuthorizations", [])
        }
        failures: list[str] = []
        for event in events:
            if event["eventType"] != "run-reserved":
                continue
            if event["authorizationSha256"] == fields["authorizationSha256"]:
                failures.append("duplicate-authorization")
            if event["runId"] == fields["runId"]:
                failures.append("duplicate-run-cell")
            if event["authorityNonce"] == fields["authorityNonce"]:
                failures.append("duplicate-authority-nonce")
            if stage_nonces & set(event["dispatchNonces"].values()):
                failures.append("duplicate-dispatch-nonce")
            if event["rawEvidenceRoot"] == envelope.get("rawEvidenceRoot"):
                failures.append("duplicate-raw-evidence-root")
        return failures

    def _read_unlocked(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        raw = self.path.read_bytes()
        if raw and not raw.endswith(b"\n"):
            raise DispatchLedgerError("ledger has an incomplete tail")
        events: list[dict[str, Any]] = []
        for line_number, raw_line in enumerate(raw.splitlines(), start=1):
            try:
                event = json.loads(raw_line.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as error:
                raise DispatchLedgerError(
                    f"invalid JSON at ledger line {line_number}"
                ) from error
            if not isinstance(event, dict):
                raise DispatchLedgerError(
                    f"ledger line {line_number} is not an object"
                )
            events.append(event)
        self._validate_events(events)
        return events

    def _validate_events(self, events: list[dict[str, Any]]) -> None:
        reservations: dict[str, dict[str, Any]] = {}
        previous_sha256 = ZERO_SHA256
        previous_time: datetime | None = None
        for sequence, event in enumerate(events, start=1):
            event_type = event.get("eventType")
            expected_keys = COMMON_EVENT_KEYS | EVENT_SPECIFIC_KEYS.get(
                event_type,
                set(),
            )
            if set(event) != expected_keys:
                raise DispatchLedgerError("ledger event shape drifted")
            if (
                event.get("schema") != 1
                or event.get("sequence") != sequence
                or event_type not in ALLOWED_EVENT_TYPES
                or event.get("previousEventSha256") != previous_sha256
                or event.get("eventSha256") != _event_sha256(event)
            ):
                raise DispatchLedgerError(
                    "ledger sequence, type, or hash chain drifted"
                )
            event_time = _parse_time(event.get("observedAt"), "observedAt")
            if previous_time is not None and event_time < previous_time:
                raise DispatchLedgerError("ledger event time moved backwards")
            previous_time = event_time
            for key, label in (
                ("reservationId", "reservation identity"),
                ("runId", "run identity"),
                ("authorityId", "authority identity"),
                ("authorityNonce", "authority nonce"),
            ):
                _require_identity(event.get(key), label)
            if not _is_sha256(event.get("authorizationSha256")):
                raise DispatchLedgerError(
                    "ledger authorization SHA-256 is invalid"
                )
            reservation_id = event["reservationId"]
            if event_type == "run-reserved":
                if (
                    reservation_id in reservations
                    or any(
                        prior["eventType"] == "run-reserved"
                        and (
                            prior["authorizationSha256"]
                            == event["authorizationSha256"]
                            or prior["runId"] == event["runId"]
                            or prior["authorityNonce"]
                            == event["authorityNonce"]
                            or prior["rawEvidenceRoot"]
                            == event["rawEvidenceRoot"]
                            or set(prior["dispatchNonces"].values())
                            & set(event["dispatchNonces"].values())
                        )
                        for prior in events[: sequence - 1]
                    )
                    or set(event["dispatchNonces"]) != set(HOP_IDS)
                    or not all(
                        _is_sha256(value)
                        for value in event["dispatchNonces"].values()
                    )
                    or not all(
                        _is_sha256(event.get(key))
                        for key in (
                            "sourceBindingSha256",
                            "runCellSha256",
                            "routeBindingSha256",
                        )
                    )
                    or event.get("automaticRetryAllowed") is not False
                    or event.get("replacementDispatchAllowed") is not False
                    or event.get("reservationDisposition")
                    != "consumed-on-reservation-no-automatic-release"
                ):
                    raise DispatchLedgerError(
                        "ledger reservation event is invalid"
                    )
                reservations[reservation_id] = event
            else:
                reservation = reservations.get(reservation_id)
                if reservation is None or self._lineage_fields(
                    reservation
                ) != {
                    key: event.get(key)
                    for key in (
                        "authorizationSha256",
                        "runId",
                        "authorityId",
                        "authorityNonce",
                    )
                }:
                    raise DispatchLedgerError(
                        "ledger event reservation lineage drifted"
                    )
                reservation_events = [
                    prior
                    for prior in events[: sequence - 1]
                    if prior["reservationId"] == reservation_id
                ]
                if event_type == "hop-dispatch-started":
                    expected_hop = self._next_hop(reservation_events)
                    if not (
                        event["hopId"] == expected_hop
                        and event["hopSequence"]
                        == HOP_IDS.index(event["hopId"]) + 1
                        and event["dispatchNonce"]
                        == reservation["dispatchNonces"][event["hopId"]]
                        and event["modelDispatchCount"] == 1
                        and all(
                            isinstance(event[key], str)
                            and bool(event[key].strip())
                            for key in (
                                "startId",
                                "threadId",
                                "turnStartRequestId",
                            )
                        )
                        and not any(
                            prior.get("startId") == event["startId"]
                            or prior.get("threadId") == event["threadId"]
                            or prior.get("turnStartRequestId")
                            == event["turnStartRequestId"]
                            for prior in events[: sequence - 1]
                            if prior["eventType"]
                            == "hop-dispatch-started"
                        )
                    ):
                        raise DispatchLedgerError(
                            "ledger hop start event is invalid"
                        )
                elif event_type == "hop-terminal-recorded":
                    start = next(
                        (
                            prior
                            for prior in reservation_events
                            if prior["eventType"]
                            == "hop-dispatch-started"
                            and prior["hopId"] == event["hopId"]
                        ),
                        None,
                    )
                    status = event.get("terminalStatus")
                    if not (
                        start is not None
                        and event["hopSequence"]
                        == HOP_IDS.index(event["hopId"]) + 1
                        and event["startEventSha256"]
                        == start["eventSha256"]
                        and event["threadId"] == start["threadId"]
                        and status in ALLOWED_TERMINAL_STATUSES
                        and all(
                            isinstance(event[key], str)
                            and bool(event[key].strip())
                            for key in ("terminalId", "threadId", "turnId")
                        )
                        and not any(
                            prior["eventType"]
                            == "hop-terminal-recorded"
                            and (
                                prior["hopId"] == event["hopId"]
                                or prior["terminalId"]
                                == event["terminalId"]
                                or prior["turnId"] == event["turnId"]
                            )
                            for prior in events[: sequence - 1]
                        )
                        and (
                            (
                                status == "completed-valid"
                                and _is_sha256(
                                    event.get("receiptSha256")
                                )
                                and event.get("errorEvidenceSha256")
                                is None
                            )
                            or (
                                status in {"failed", "ambiguous"}
                                and event.get("receiptSha256") is None
                                and _is_sha256(
                                    event.get("errorEvidenceSha256")
                                )
                            )
                        )
                    ):
                        raise DispatchLedgerError(
                            "ledger hop terminal event is invalid"
                        )
                elif event_type == "reservation-reconciled":
                    ambiguous = next(
                        (
                            prior
                            for prior in reservation_events
                            if prior["eventType"]
                            == "hop-terminal-recorded"
                            and prior["terminalStatus"] == "ambiguous"
                        ),
                        None,
                    )
                    if not (
                        ambiguous is not None
                        and event["hopId"] == ambiguous["hopId"]
                        and event["hopSequence"]
                        == ambiguous["hopSequence"]
                        and event["terminalEventSha256"]
                        == ambiguous["eventSha256"]
                        and isinstance(event["reconciliationId"], str)
                        and bool(event["reconciliationId"].strip())
                        and _is_sha256(
                            event["reconciliationDocumentSha256"]
                        )
                        and event["disposition"]
                        == "retain-consumed-no-retry"
                        and not any(
                            prior["eventType"]
                            == "reservation-reconciled"
                            for prior in reservation_events
                        )
                    ):
                        raise DispatchLedgerError(
                            "ledger reconciliation event is invalid"
                        )
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
                events[-1]["eventSha256"] if events else ZERO_SHA256
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
                if event["eventType"] == "run-reserved"
                and event["reservationId"] == reservation_id
            ),
            None,
        )
        if reservation is None:
            raise DispatchLedgerError("run reservation is missing")
        return reservation

    @staticmethod
    def _events_for(
        events: list[dict[str, Any]],
        reservation_id: str,
    ) -> list[dict[str, Any]]:
        return [
            event
            for event in events
            if event["reservationId"] == reservation_id
        ]

    @staticmethod
    def _lineage_fields(
        reservation: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            key: reservation[key]
            for key in (
                "authorizationSha256",
                "runId",
                "authorityId",
                "authorityNonce",
            )
        }

    @staticmethod
    def _next_hop(
        reservation_events: list[dict[str, Any]],
    ) -> str | None:
        terminals = {
            event["hopId"]: event
            for event in reservation_events
            if event["eventType"] == "hop-terminal-recorded"
        }
        if any(
            event["terminalStatus"] in {"failed", "ambiguous"}
            for event in terminals.values()
        ):
            return None
        starts = {
            event["hopId"]
            for event in reservation_events
            if event["eventType"] == "hop-dispatch-started"
        }
        for hop_id in HOP_IDS:
            if hop_id not in starts:
                previous = HOP_IDS[: HOP_IDS.index(hop_id)]
                if all(
                    terminals.get(prior, {}).get("terminalStatus")
                    == "completed-valid"
                    for prior in previous
                ):
                    return hop_id
                return None
            if hop_id not in terminals:
                return None
        return None
