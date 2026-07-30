from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.human_ai_collaboration_tdd_noncomparative_dispatch_authorization_adapter import (
    DispatchAuthorizationError,
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
    file_sha256,
)


def valid_handle(_: object) -> HandleValidationResult:
    return HandleValidationResult(
        valid=True,
        reason_code="synthetic-handle-valid",
    )


class HumanAiCollaborationTddNoncomparativeLedgerAuthorityAndReconciliationTests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.bundle = Bundle(self.root)

    def run_wrapper(
        self,
        factory: object,
        *,
        validator: object = valid_handle,
    ) -> dict:
        return construct_after_dispatch_reservation(
            protocol_path=self.bundle.protocol_path,
            source_governance_preflight_path=self.bundle.preflight_path,
            static_gap_audit_path=self.bundle.audit_path,
            diagnostic_admission_path=self.bundle.admission_path,
            candidate_id=CANDIDATE_ID,
            reservation_id="reservation-01",
            observed_at=OBSERVED_AT,
            app_server_factory=factory,
            app_server_handle_validator=validator,
        )

    def test_protocol_bound_authority_selects_the_only_ledger_path(self) -> None:
        result = self.run_wrapper(
            lambda _reservation, _register: object()
        )
        self.assertTrue(self.bundle.ledger_path.is_file())
        self.assertEqual(
            self.bundle.ledger_authority["authorityId"],
            result["reservation"]["ledgerAuthorityId"],
        )
        self.assertNotIn("ledgerPath", result["reservation"])

    def test_authority_document_digest_drift_rejects_before_ledger(self) -> None:
        self.bundle.ledger_authority["automaticRetryAllowed"] = True
        self.bundle.ledger_authority_path.write_text(
            json.dumps(self.bundle.ledger_authority, indent=2) + "\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(
            DispatchAuthorizationError,
            "ledger authority digest",
        ):
            self.run_wrapper(
                lambda _reservation, _register: object()
            )
        self.assertFalse(self.bundle.ledger_path.exists())

    def test_factory_exception_is_an_explicit_stranded_state(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "synthetic factory failure"):
            self.run_wrapper(
                lambda _reservation, _register: (_ for _ in ()).throw(
                    RuntimeError("synthetic factory failure")
                )
            )
        ledger = DispatchIdentityLedger(self.bundle.ledger_path)
        events = ledger.read_events()
        self.assertEqual(
            ["candidate-reserved", "construction-failed"],
            [event["eventType"] for event in events],
        )
        self.assertEqual("factory-raised", events[-1]["failureClass"])
        self.assertNotIn("errorMessage", events[-1])
        self.assertEqual(
            "construction-failed",
            ledger.read_reservation_status(
                reservation_id="reservation-01"
            )["status"],
        )

    def test_none_factory_handle_is_recorded_and_rejected(self) -> None:
        with self.assertRaisesRegex(
            DispatchGateError,
            "handle validation rejected",
        ):
            self.run_wrapper(
                lambda _reservation, _register: None,
                validator=lambda _handle: HandleValidationResult(
                    valid=False,
                    reason_code="none-handle",
                ),
            )
        events = DispatchIdentityLedger(
            self.bundle.ledger_path
        ).read_events()
        self.assertEqual(
            "handle-validation-rejected",
            events[-1]["failureClass"],
        )

    def test_manual_reconciliation_retains_consumed_cap(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "synthetic factory failure"):
            self.run_wrapper(
                lambda _reservation, _register: (_ for _ in ()).throw(
                    RuntimeError("synthetic factory failure")
                )
            )
        ledger = DispatchIdentityLedger(self.bundle.ledger_path)
        failure = ledger.read_events()[-1]
        reconciliation_path = self.root / "reconciliation.json"
        reconciliation = {
            "schema": 1,
            "kind": "manual-stranded-reservation-reconciliation",
            "reconciliationId": "reconciliation-01",
            "ledgerAuthorityId": self.bundle.ledger_authority["authorityId"],
            "candidateId": CANDIDATE_ID,
            "reservationId": "reservation-01",
            "failureEventSha256": failure["eventSha256"],
            "disposition": "retain-consumed-no-retry",
            "replacementDispatchAuthorized": False,
            "reservationReleaseAuthorized": False,
        }
        reconciliation_path.write_text(
            json.dumps(reconciliation, indent=2) + "\n",
            encoding="utf-8",
        )
        event = ledger.reconcile_failed_reservation(
            reconciliation_document_path=reconciliation_path,
            observed_at="2026-07-26T23:31:00+08:00",
        )
        self.assertEqual(
            file_sha256(reconciliation_path),
            event["reconciliationDocumentSha256"],
        )
        self.assertEqual(
            "reconciled-retained-consumed",
            ledger.read_reservation_status(
                reservation_id="reservation-01"
            )["status"],
        )
        calls = 0

        def factory(_: dict, _register: object) -> object:
            nonlocal calls
            calls += 1
            return object()

        with self.assertRaisesRegex(DispatchGateError, "candidate dispatch cap"):
            construct_after_dispatch_reservation(
                protocol_path=self.bundle.protocol_path,
                source_governance_preflight_path=self.bundle.preflight_path,
                static_gap_audit_path=self.bundle.audit_path,
                diagnostic_admission_path=self.bundle.admission_path,
                candidate_id=CANDIDATE_ID,
                reservation_id="reservation-02",
                observed_at=OBSERVED_AT,
                app_server_factory=factory,
                app_server_handle_validator=valid_handle,
            )
        self.assertEqual(0, calls)

    def test_reconciliation_cannot_authorize_release_or_retry(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "synthetic factory failure"):
            self.run_wrapper(
                lambda _reservation, _register: (_ for _ in ()).throw(
                    RuntimeError("synthetic factory failure")
                )
            )
        ledger = DispatchIdentityLedger(self.bundle.ledger_path)
        failure = ledger.read_events()[-1]
        reconciliation_path = self.root / "reconciliation.json"
        reconciliation_path.write_text(
            json.dumps(
                {
                    "schema": 1,
                    "kind": "manual-stranded-reservation-reconciliation",
                    "reconciliationId": "reconciliation-01",
                    "ledgerAuthorityId": self.bundle.ledger_authority[
                        "authorityId"
                    ],
                    "candidateId": CANDIDATE_ID,
                    "reservationId": "reservation-01",
                    "failureEventSha256": failure["eventSha256"],
                    "disposition": "retain-consumed-no-retry",
                    "replacementDispatchAuthorized": True,
                    "reservationReleaseAuthorized": False,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(
            DispatchGateError,
            "reconciliation boundary",
        ):
            ledger.reconcile_failed_reservation(
                reconciliation_document_path=reconciliation_path,
                observed_at="2026-07-26T23:31:00+08:00",
            )


if __name__ == "__main__":
    unittest.main()
