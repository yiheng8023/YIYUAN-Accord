from __future__ import annotations

import json
import hashlib
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from scripts.human_ai_collaboration_tdd_noncomparative_dispatch_identity_ledger import (
    DispatchGateError,
    DispatchIdentityLedger,
)


CANDIDATE_ID = "tdd.matt.current"
CANDIDATE_SHA = "1" * 64
PROTOCOL_SHA = "2" * 64
OBSERVED_AT = "2026-07-26T20:00:00+08:00"


def authorization_evidence(
    *,
    candidate_id: str = CANDIDATE_ID,
    candidate_identity_sha256: str = CANDIDATE_SHA,
    protocol_sha256: str = PROTOCOL_SHA,
) -> dict:
    payload = {
        "schema": 1,
        "candidateId": candidate_id,
        "candidateIdentitySha256": candidate_identity_sha256,
        "protocolFileSha256": protocol_sha256,
        "sourceGovernancePreflightFileSha256": "3" * 64,
        "staticGapAuditFileSha256": "4" * 64,
        "diagnosticAdmissionFileSha256": "5" * 64,
        "diagnosticAdmissionId": "admission-test",
        "ledgerAuthorityDocument": "ledger-authority.json",
        "ledgerAuthorityDocumentSha256": "6" * 64,
        "ledgerAuthorityId": "ledger-authority-test",
        "ledgerRelativePath": "state/dispatch-ledger.jsonl",
        "observedAt": OBSERVED_AT,
        "exactCandidateExecutionAdmitted": True,
        "sourceAndToolchainReverifiedAtDispatch": True,
    }
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return {
        **payload,
        "authorizationSha256": hashlib.sha256(encoded).hexdigest(),
    }


class HumanAiCollaborationTddNoncomparativeDispatchIdentityLedgerTests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name) / "dispatch-ledger.jsonl"
        self.ledger = DispatchIdentityLedger(self.path)

    def reserve(self, reservation_id: str = "reservation-01") -> dict:
        return self.ledger._reserve_candidate(
            candidate_id=CANDIDATE_ID,
            candidate_identity_sha256=CANDIDATE_SHA,
            protocol_sha256=PROTOCOL_SHA,
            reservation_id=reservation_id,
            observed_at=OBSERVED_AT,
            exact_candidate_execution_admitted=True,
            source_and_toolchain_reverified_at_dispatch=True,
            authorization_evidence=authorization_evidence(),
        )

    def test_reservation_is_first_hash_chained_event(self) -> None:
        event = self.reserve()
        self.assertEqual("candidate-reserved", event["eventType"])
        self.assertEqual(1, event["sequence"])
        self.assertEqual("0" * 64, event["previousEventSha256"])
        self.assertEqual([event], self.ledger.read_events())

    def test_rejects_missing_exact_candidate_admission_without_writing(self) -> None:
        with self.assertRaisesRegex(DispatchGateError, "execution admission"):
            self.ledger._reserve_candidate(
                candidate_id=CANDIDATE_ID,
                candidate_identity_sha256=CANDIDATE_SHA,
                protocol_sha256=PROTOCOL_SHA,
                reservation_id="reservation-01",
                observed_at=OBSERVED_AT,
                exact_candidate_execution_admitted=False,
                source_and_toolchain_reverified_at_dispatch=True,
                authorization_evidence=authorization_evidence(),
            )
        self.assertFalse(self.path.exists())

    def test_rejects_stale_source_without_writing(self) -> None:
        with self.assertRaisesRegex(DispatchGateError, "reverified"):
            self.ledger._reserve_candidate(
                candidate_id=CANDIDATE_ID,
                candidate_identity_sha256=CANDIDATE_SHA,
                protocol_sha256=PROTOCOL_SHA,
                reservation_id="reservation-01",
                observed_at=OBSERVED_AT,
                exact_candidate_execution_admitted=True,
                source_and_toolchain_reverified_at_dispatch=False,
                authorization_evidence=authorization_evidence(),
            )
        self.assertFalse(self.path.exists())

    def test_rejects_second_or_replacement_candidate_reservation(self) -> None:
        self.reserve()
        with self.assertRaisesRegex(DispatchGateError, "candidate dispatch cap"):
            self.reserve("reservation-02")
        with self.assertRaisesRegex(DispatchGateError, "reservation identity"):
            self.ledger._reserve_candidate(
                candidate_id="tdd.superpowers.6.2.0",
                candidate_identity_sha256="3" * 64,
                protocol_sha256=PROTOCOL_SHA,
                reservation_id="reservation-01",
                observed_at=OBSERVED_AT,
                exact_candidate_execution_admitted=True,
                source_and_toolchain_reverified_at_dispatch=True,
                authorization_evidence=authorization_evidence(
                    candidate_id="tdd.superpowers.6.2.0",
                    candidate_identity_sha256="3" * 64,
                ),
            )

    def test_thread_and_turn_bindings_are_ordered_and_immutable(self) -> None:
        self.reserve()
        with self.assertRaisesRegex(DispatchGateError, "thread binding"):
            self.ledger.bind_turn(
                reservation_id="reservation-01",
                thread_id="thread-01",
                turn_id="turn-01",
                observed_at=OBSERVED_AT,
            )
        self.ledger.record_construction_success(
            reservation_id="reservation-01",
            construction_id="construction-01",
            observed_at=OBSERVED_AT,
        )
        thread = self.ledger.bind_thread(
            reservation_id="reservation-01",
            thread_id="thread-01",
            observed_at=OBSERVED_AT,
        )
        turn = self.ledger.bind_turn(
            reservation_id="reservation-01",
            thread_id="thread-01",
            turn_id="turn-01",
            observed_at=OBSERVED_AT,
        )
        self.assertEqual("thread-bound", thread["eventType"])
        self.assertEqual("turn-bound", turn["eventType"])
        with self.assertRaisesRegex(DispatchGateError, "thread already bound"):
            self.ledger.bind_thread(
                reservation_id="reservation-01",
                thread_id="thread-replacement",
                observed_at=OBSERVED_AT,
            )
        with self.assertRaisesRegex(DispatchGateError, "turn already bound"):
            self.ledger.bind_turn(
                reservation_id="reservation-01",
                thread_id="thread-01",
                turn_id="turn-replacement",
                observed_at=OBSERVED_AT,
            )

    def test_thread_binding_rejects_before_construction_success(self) -> None:
        self.reserve()
        with self.assertRaisesRegex(
            DispatchGateError,
            "construction has not succeeded",
        ):
            self.ledger.bind_thread(
                reservation_id="reservation-01",
                thread_id="thread-01",
                observed_at=OBSERVED_AT,
            )

    def test_rejects_hash_chain_tampering(self) -> None:
        self.reserve()
        event = json.loads(self.path.read_text(encoding="utf-8"))
        event["candidateId"] = "tampered"
        self.path.write_text(
            json.dumps(event, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(DispatchGateError, "event hash"):
            self.ledger.read_events()

    def test_rejects_torn_tail_instead_of_recovering_silently(self) -> None:
        self.reserve()
        with self.path.open("ab") as stream:
            stream.write(b'{"schema":1')
        with self.assertRaisesRegex(DispatchGateError, "invalid JSON"):
            self.ledger.read_events()

    def test_concurrent_duplicate_reservation_allows_exactly_one(self) -> None:
        def attempt(index: int) -> str:
            try:
                self.reserve(f"reservation-{index}")
                return "reserved"
            except DispatchGateError:
                return "rejected"

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(attempt, (1, 2)))
        self.assertEqual(["rejected", "reserved"], sorted(results))
        events = self.ledger.read_events()
        self.assertEqual(1, len(events))
        self.assertEqual(CANDIDATE_ID, events[0]["candidateId"])


if __name__ == "__main__":
    unittest.main()
