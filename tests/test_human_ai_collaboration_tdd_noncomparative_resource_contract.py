from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

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


class HostileFactoryError(RuntimeError):
    def add_note(self, note: str) -> None:
        raise RuntimeError(f"note rejected: {note}")


class HumanAiCollaborationTddNoncomparativeResourceContractTests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.bundle = Bundle(self.root)

    @staticmethod
    def valid_handle(_: object) -> HandleValidationResult:
        return HandleValidationResult(
            valid=True,
            reason_code="synthetic-handle-valid",
        )

    def run_wrapper(
        self,
        factory: object,
        *,
        validator: object | None = None,
        reservation_id: str = "reservation-01",
    ) -> dict:
        return construct_after_dispatch_reservation(
            protocol_path=self.bundle.protocol_path,
            source_governance_preflight_path=self.bundle.preflight_path,
            static_gap_audit_path=self.bundle.audit_path,
            diagnostic_admission_path=self.bundle.admission_path,
            candidate_id=CANDIDATE_ID,
            reservation_id=reservation_id,
            observed_at=OBSERVED_AT,
            app_server_factory=factory,
            app_server_handle_validator=validator or self.valid_handle,
        )

    def test_valid_handle_is_checked_once_and_resources_transfer(self) -> None:
        calls: list[str] = []

        def factory(_: dict, register_owned_resource: object) -> object:
            register_owned_resource(
                "resource-01",
                lambda: calls.append("cleanup"),
            )
            return object()

        def validator(_: object) -> HandleValidationResult:
            calls.append("validate")
            return self.valid_handle(object())

        result = self.run_wrapper(factory, validator=validator)

        self.assertEqual(["validate"], calls)
        self.assertEqual(
            "construction-succeeded",
            result["construction"]["eventType"],
        )

    def test_rejected_falsey_handle_is_cleaned_and_recorded(self) -> None:
        for handle in (None, False, []):
            with self.subTest(handle=repr(handle)):
                with tempfile.TemporaryDirectory() as temporary:
                    bundle = Bundle(Path(temporary))
                    calls: list[str] = []

                    def factory(
                        _: dict,
                        register_owned_resource: object,
                    ) -> object:
                        register_owned_resource(
                            "resource-01",
                            lambda: calls.append("cleanup"),
                        )
                        return handle

                    def reject(_: object) -> HandleValidationResult:
                        calls.append("validate")
                        return HandleValidationResult(
                            valid=False,
                            reason_code="synthetic-handle-rejected",
                        )

                    with self.assertRaisesRegex(
                        DispatchGateError,
                        "handle validation rejected",
                    ):
                        construct_after_dispatch_reservation(
                            protocol_path=bundle.protocol_path,
                            source_governance_preflight_path=(
                                bundle.preflight_path
                            ),
                            static_gap_audit_path=bundle.audit_path,
                            diagnostic_admission_path=bundle.admission_path,
                            candidate_id=CANDIDATE_ID,
                            reservation_id="reservation-01",
                            observed_at=OBSERVED_AT,
                            app_server_factory=factory,
                            app_server_handle_validator=reject,
                        )

                    self.assertEqual(["validate", "cleanup"], calls)
                    events = DispatchIdentityLedger(
                        bundle.ledger_path
                    ).read_events()
                    self.assertEqual(
                        "handle-validation-rejected",
                        events[-1]["failureClass"],
                    )

    def test_factory_failure_cleans_registered_resources_lifo(self) -> None:
        calls: list[str] = []
        primary = RuntimeError("synthetic factory failure")

        def factory(_: dict, register_owned_resource: object) -> object:
            register_owned_resource(
                "resource-01",
                lambda: calls.append("cleanup-01"),
            )
            register_owned_resource(
                "resource-02",
                lambda: calls.append("cleanup-02"),
            )
            raise primary

        with self.assertRaises(RuntimeError) as caught:
            self.run_wrapper(factory)

        self.assertIs(primary, caught.exception)
        self.assertEqual(["cleanup-02", "cleanup-01"], calls)
        self.assertEqual(
            "construction-failed",
            DispatchIdentityLedger(
                self.bundle.ledger_path
            ).read_events()[-1]["eventType"],
        )

    def test_validator_exception_cleans_and_records_failure(self) -> None:
        calls: list[str] = []
        validation_error = RuntimeError("validator failed")

        def factory(_: dict, register_owned_resource: object) -> object:
            register_owned_resource(
                "resource-01",
                lambda: calls.append("cleanup"),
            )
            return object()

        def validator(_: object) -> HandleValidationResult:
            raise validation_error

        with self.assertRaises(RuntimeError) as caught:
            self.run_wrapper(factory, validator=validator)

        self.assertIs(validation_error, caught.exception)
        self.assertEqual(["cleanup"], calls)
        self.assertEqual(
            "handle-validation-raised",
            DispatchIdentityLedger(
                self.bundle.ledger_path
            ).read_events()[-1]["failureClass"],
        )

    def test_invalid_validator_result_cleans_and_fails_closed(self) -> None:
        calls: list[str] = []

        def factory(_: dict, register_owned_resource: object) -> object:
            register_owned_resource(
                "resource-01",
                lambda: calls.append("cleanup"),
            )
            return object()

        with self.assertRaisesRegex(
            DispatchGateError,
            "validator returned an invalid result",
        ):
            self.run_wrapper(
                factory,
                validator=lambda _handle: True,
            )

        self.assertEqual(["cleanup"], calls)
        self.assertEqual(
            "handle-validation-result-invalid",
            DispatchIdentityLedger(
                self.bundle.ledger_path
            ).read_events()[-1]["failureClass"],
        )

    def test_hostile_primary_survives_failure_append_and_cleanup_errors(
        self,
    ) -> None:
        primary = HostileFactoryError("primary factory error")
        cleanup_error = RuntimeError("cleanup failed")
        append_error = DispatchGateError("failure append failed")

        def factory(_: dict, register_owned_resource: object) -> object:
            register_owned_resource(
                "resource-01",
                lambda: (_ for _ in ()).throw(cleanup_error),
            )
            raise primary

        with patch.object(
            DispatchIdentityLedger,
            "record_construction_failure",
            side_effect=append_error,
        ):
            with self.assertRaises(HostileFactoryError) as caught:
                self.run_wrapper(factory)

        self.assertIs(primary, caught.exception)
        self.assertEqual(
            ["candidate-reserved"],
            [
                event["eventType"]
                for event in DispatchIdentityLedger(
                    self.bundle.ledger_path
                ).read_events()
            ],
        )

    def test_success_append_failure_cleans_and_is_fresh_reader_visible(
        self,
    ) -> None:
        calls: list[str] = []
        append_error = DispatchGateError("success append failed")

        def factory(_: dict, register_owned_resource: object) -> object:
            register_owned_resource(
                "resource-01",
                lambda: calls.append("cleanup"),
            )
            return object()

        with patch.object(
            DispatchIdentityLedger,
            "record_construction_success",
            side_effect=append_error,
        ):
            with self.assertRaises(DispatchGateError) as caught:
                self.run_wrapper(factory)

        self.assertIs(append_error, caught.exception)
        self.assertEqual(["cleanup"], calls)
        status = DispatchIdentityLedger(
            self.bundle.ledger_path
        ).read_reservation_status(reservation_id="reservation-01")
        self.assertEqual(
            "reserved-without-construction-outcome",
            status["status"],
        )
        self.assertFalse(status["constructionOutcomeRecorded"])
        self.assertTrue(status["manualRecoveryRequired"])
        self.assertFalse(status["automaticRetryAuthorized"])
        self.assertFalse(status["automaticReleaseAuthorized"])

    def test_success_append_post_write_error_uses_durable_readback(
        self,
    ) -> None:
        calls: list[str] = []
        original = DispatchIdentityLedger.record_construction_success

        def factory(_: dict, register_owned_resource: object) -> object:
            register_owned_resource(
                "resource-01",
                lambda: calls.append("cleanup"),
            )
            return object()

        def persist_then_raise(
            ledger: DispatchIdentityLedger,
            **kwargs: object,
        ) -> dict:
            original(ledger, **kwargs)
            raise DispatchGateError("synthetic post-write transport error")

        with patch.object(
            DispatchIdentityLedger,
            "record_construction_success",
            new=persist_then_raise,
        ):
            result = self.run_wrapper(factory)

        self.assertEqual([], calls)
        self.assertEqual(
            "construction-succeeded",
            result["construction"]["eventType"],
        )
        status = DispatchIdentityLedger(
            self.bundle.ledger_path
        ).read_reservation_status(reservation_id="reservation-01")
        self.assertEqual("construction-succeeded", status["status"])
        self.assertTrue(status["constructionOutcomeRecorded"])
        self.assertFalse(status["manualRecoveryRequired"])

    def test_missing_outcome_manual_reconciliation_retains_consumed_cap(
        self,
    ) -> None:
        append_error = DispatchGateError("success append failed")

        def factory(_: dict, register_owned_resource: object) -> object:
            register_owned_resource("resource-01", lambda: None)
            return object()

        with patch.object(
            DispatchIdentityLedger,
            "record_construction_success",
            side_effect=append_error,
        ):
            with self.assertRaises(DispatchGateError):
                self.run_wrapper(factory)

        ledger = DispatchIdentityLedger(self.bundle.ledger_path)
        reservation = ledger.read_events()[0]
        reconciliation_path = self.root / "missing-outcome-reconciliation.json"
        reconciliation_path.write_text(
            json.dumps(
                {
                    "schema": 1,
                    "kind": (
                        "manual-missing-construction-outcome-reconciliation"
                    ),
                    "reconciliationId": "reconciliation-01",
                    "ledgerAuthorityId": self.bundle.ledger_authority[
                        "authorityId"
                    ],
                    "candidateId": CANDIDATE_ID,
                    "reservationId": "reservation-01",
                    "reservationEventSha256": reservation["eventSha256"],
                    "constructionOutcomeRecorded": False,
                    "disposition": "retain-consumed-no-retry",
                    "replacementDispatchAuthorized": False,
                    "reservationReleaseAuthorized": False,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        event = ledger.reconcile_missing_construction_outcome(
            reconciliation_document_path=reconciliation_path,
            observed_at="2026-07-27T01:00:00+08:00",
        )

        self.assertEqual(
            "missing-construction-outcome",
            event["reconciliationClass"],
        )
        self.assertEqual(
            "reconciled-retained-consumed",
            ledger.read_reservation_status(
                reservation_id="reservation-01"
            )["status"],
        )
        with self.assertRaisesRegex(DispatchGateError, "candidate dispatch cap"):
            self.run_wrapper(
                lambda _reservation, _register: object(),
                reservation_id="reservation-02",
            )

    def test_missing_outcome_reconciliation_rejects_wrong_reservation_hash(
        self,
    ) -> None:
        ledger, reservation = (
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
        reconciliation_path = self.root / "forged-reconciliation.json"
        reconciliation_path.write_text(
            json.dumps(
                {
                    "schema": 1,
                    "kind": (
                        "manual-missing-construction-outcome-reconciliation"
                    ),
                    "reconciliationId": "reconciliation-01",
                    "ledgerAuthorityId": self.bundle.ledger_authority[
                        "authorityId"
                    ],
                    "candidateId": CANDIDATE_ID,
                    "reservationId": "reservation-01",
                    "reservationEventSha256": "0" * 64,
                    "constructionOutcomeRecorded": False,
                    "disposition": "retain-consumed-no-retry",
                    "replacementDispatchAuthorized": False,
                    "reservationReleaseAuthorized": False,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        self.assertNotEqual(
            reservation["eventSha256"],
            "0" * 64,
        )
        with self.assertRaisesRegex(
            DispatchGateError,
            "evidence is mismatched",
        ):
            ledger.reconcile_missing_construction_outcome(
                reconciliation_document_path=reconciliation_path,
                observed_at="2026-07-27T01:00:00+08:00",
            )

    def test_two_authorities_allow_two_local_reservations(self) -> None:
        second_root = self.root / "second-authority"
        second_root.mkdir()
        second_bundle = Bundle(second_root)
        second_bundle.ledger_authority["authorityId"] = (
            "tdd-noncomparative-ledger-authority-02"
        )
        second_bundle.ledger_authority["ledgerRelativePath"] = (
            "state/dispatch-ledger-02.jsonl"
        )
        second_bundle.ledger_path = (
            second_root / "state" / "dispatch-ledger-02.jsonl"
        )
        second_bundle.write()

        first = self.run_wrapper(
            lambda _reservation, _register: object()
        )
        second = construct_after_dispatch_reservation(
            protocol_path=second_bundle.protocol_path,
            source_governance_preflight_path=second_bundle.preflight_path,
            static_gap_audit_path=second_bundle.audit_path,
            diagnostic_admission_path=second_bundle.admission_path,
            candidate_id=CANDIDATE_ID,
            reservation_id="reservation-02",
            observed_at=OBSERVED_AT,
            app_server_factory=lambda _reservation, _register: object(),
            app_server_handle_validator=self.valid_handle,
        )

        self.assertNotEqual(
            first["reservation"]["ledgerAuthorityId"],
            second["reservation"]["ledgerAuthorityId"],
        )
        self.assertEqual(
            first["reservation"]["candidateId"],
            second["reservation"]["candidateId"],
        )
        self.assertEqual(
            first["reservation"]["candidateIdentitySha256"],
            second["reservation"]["candidateIdentitySha256"],
        )
        self.assertTrue(self.bundle.ledger_path.is_file())
        self.assertTrue(second_bundle.ledger_path.is_file())
        for bundle, reservation_id in (
            (self.bundle, "reservation-03"),
            (second_bundle, "reservation-04"),
        ):
            with self.assertRaisesRegex(
                DispatchGateError,
                "candidate dispatch cap",
            ):
                construct_after_dispatch_reservation(
                    protocol_path=bundle.protocol_path,
                    source_governance_preflight_path=bundle.preflight_path,
                    static_gap_audit_path=bundle.audit_path,
                    diagnostic_admission_path=bundle.admission_path,
                    candidate_id=CANDIDATE_ID,
                    reservation_id=reservation_id,
                    observed_at=OBSERVED_AT,
                    app_server_factory=(
                        lambda _reservation, _register: object()
                    ),
                    app_server_handle_validator=self.valid_handle,
                )


if __name__ == "__main__":
    unittest.main()
