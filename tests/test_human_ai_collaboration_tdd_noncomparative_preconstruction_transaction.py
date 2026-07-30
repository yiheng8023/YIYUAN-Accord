from __future__ import annotations

import hashlib
import tempfile
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path
from unittest.mock import patch

from scripts.human_ai_collaboration_tdd_noncomparative_dispatch_authorization_adapter import (
    build_dispatch_authorization_envelope,
)
from scripts.human_ai_collaboration_tdd_noncomparative_dispatch_identity_ledger import (
    DispatchGateError,
    DispatchIdentityLedger,
)
from scripts.human_ai_collaboration_tdd_noncomparative_runner_preflight import (
    HandleValidationResult,
    construct_after_dispatch_reservation,
)
from tests.test_human_ai_collaboration_tdd_noncomparative_dispatch_authorization_adapter import (
    Bundle,
    CANDIDATE_ID,
    OBSERVED_AT,
)


def valid_handle(_: object) -> HandleValidationResult:
    return HandleValidationResult(
        valid=True,
        reason_code="synthetic-handle-valid",
    )


class HumanAiCollaborationTddNoncomparativePreconstructionTransactionTests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.bundle = Bundle(self.root)

    def build_envelope(self):
        return build_dispatch_authorization_envelope(
            protocol_path=self.bundle.protocol_path,
            source_governance_preflight_path=self.bundle.preflight_path,
            static_gap_audit_path=self.bundle.audit_path,
            diagnostic_admission_path=self.bundle.admission_path,
            candidate_id=CANDIDATE_ID,
            observed_at=OBSERVED_AT,
        )

    def run_wrapper(self, factory: object) -> dict:
        return construct_after_dispatch_reservation(
            protocol_path=self.bundle.protocol_path,
            source_governance_preflight_path=self.bundle.preflight_path,
            static_gap_audit_path=self.bundle.audit_path,
            diagnostic_admission_path=self.bundle.admission_path,
            candidate_id=CANDIDATE_ID,
            reservation_id="reservation-01",
            observed_at=OBSERVED_AT,
            app_server_factory=factory,
            app_server_handle_validator=valid_handle,
        )

    def test_authorization_envelope_is_frozen_and_path_drift_cannot_change_it(
        self,
    ) -> None:
        envelope = self.build_envelope()
        authorization = envelope.reservation_input()
        self.bundle.preflight_path.write_text("{}\n", encoding="utf-8")

        self.assertEqual(authorization, envelope.reservation_input())
        self.assertNotEqual(
            authorization["sourceGovernancePreflightFileSha256"],
            hashlib.sha256(self.bundle.preflight_path.read_bytes()).hexdigest(),
        )
        with self.assertRaises(FrozenInstanceError):
            envelope.ledger_path = self.root / "alternate.jsonl"

    def test_reservation_consumes_the_same_envelope_after_path_drift(
        self,
    ) -> None:
        envelope = self.build_envelope()
        expected = envelope.reservation_input()
        self.bundle.preflight_path.write_text("{}\n", encoding="utf-8")
        patch_target = (
            "scripts.human_ai_collaboration_tdd_noncomparative_"
            "dispatch_authorization_adapter."
            "build_dispatch_authorization_envelope"
        )
        with patch(patch_target, return_value=envelope):
            ledger, event = (
                DispatchIdentityLedger.reserve_from_repository_documents(
                    protocol_path=self.bundle.protocol_path,
                    source_governance_preflight_path=self.bundle.preflight_path,
                    static_gap_audit_path=self.bundle.audit_path,
                    diagnostic_admission_path=self.bundle.admission_path,
                    candidate_id=CANDIDATE_ID,
                    reservation_id="reservation-01",
                    observed_at=OBSERVED_AT,
                )
            )

        self.assertEqual(
            expected["sourceGovernancePreflightFileSha256"],
            event["sourceGovernancePreflightFileSha256"],
        )
        self.assertEqual(self.bundle.ledger_path.resolve(), ledger.path)

    def test_thread_binding_requires_construction_success(self) -> None:
        ledger, _ = DispatchIdentityLedger.reserve_from_repository_documents(
            protocol_path=self.bundle.protocol_path,
            source_governance_preflight_path=self.bundle.preflight_path,
            static_gap_audit_path=self.bundle.audit_path,
            diagnostic_admission_path=self.bundle.admission_path,
            candidate_id=CANDIDATE_ID,
            reservation_id="reservation-01",
            observed_at=OBSERVED_AT,
        )
        with self.assertRaisesRegex(
            DispatchGateError,
            "construction has not succeeded",
        ):
            ledger.bind_thread(
                reservation_id="reservation-01",
                thread_id="thread-01",
                observed_at=OBSERVED_AT,
            )

        ledger.record_construction_success(
            reservation_id="reservation-01",
            construction_id="construction-01",
            observed_at=OBSERVED_AT,
        )
        event = ledger.bind_thread(
            reservation_id="reservation-01",
            thread_id="thread-01",
            observed_at=OBSERVED_AT,
        )
        self.assertEqual("thread-bound", event["eventType"])

    def test_wrapper_records_construction_success_before_returning_handle(
        self,
    ) -> None:
        result = self.run_wrapper(
            lambda _reservation, _register: object()
        )
        events = DispatchIdentityLedger(
            self.bundle.ledger_path
        ).read_events()
        self.assertEqual(
            ["candidate-reserved", "construction-succeeded"],
            [event["eventType"] for event in events],
        )
        self.assertEqual(
            events[-1]["eventSha256"],
            result["construction"]["eventSha256"],
        )

    def test_failure_recording_error_does_not_replace_factory_error(self) -> None:
        factory_error = ValueError("primary synthetic factory error")
        recording_error = DispatchGateError("synthetic ledger write failure")

        def factory(_: dict, _register: object) -> object:
            raise factory_error

        with patch.object(
            DispatchIdentityLedger,
            "record_construction_failure",
            side_effect=recording_error,
        ):
            with self.assertRaises(ValueError) as caught:
                self.run_wrapper(factory)

        self.assertIs(factory_error, caught.exception)
        self.assertIn(
            recording_error,
            caught.exception.dispatch_secondary_errors,
        )
        self.assertEqual(
            ["candidate-reserved"],
            [
                event["eventType"]
                for event in DispatchIdentityLedger(
                    self.bundle.ledger_path
                ).read_events()
            ],
        )

    def test_factory_cannot_bind_thread_before_construction_success(self) -> None:
        def factory(_: dict, _register: object) -> object:
            return DispatchIdentityLedger(
                self.bundle.ledger_path
            ).bind_thread(
                reservation_id="reservation-01",
                thread_id="thread-01",
                observed_at=OBSERVED_AT,
            )

        with self.assertRaisesRegex(
            DispatchGateError,
            "construction has not succeeded",
        ):
            self.run_wrapper(factory)
        self.assertEqual(
            ["candidate-reserved", "construction-failed"],
            [
                event["eventType"]
                for event in DispatchIdentityLedger(
                    self.bundle.ledger_path
                ).read_events()
            ],
        )


if __name__ == "__main__":
    unittest.main()
