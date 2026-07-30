from __future__ import annotations

import json
import inspect
import tempfile
import unittest
from pathlib import Path

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
    ROOT,
    candidate_identity,
    canonical_sha256,
    file_sha256,
)


def valid_handle(_: object) -> HandleValidationResult:
    return HandleValidationResult(
        valid=True,
        reason_code="synthetic-handle-valid",
    )


class HumanAiCollaborationTddNoncomparativeRunnerPreflightTests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.bundle = Bundle(self.root)
        self.ledger_path = self.bundle.ledger_path

    def test_reservation_exists_before_injected_factory_is_called(self) -> None:
        observations: list[str] = []

        def factory(reservation: dict, _register: object) -> object:
            events = DispatchIdentityLedger(self.ledger_path).read_events()
            self.assertEqual([reservation], events)
            observations.append("factory-called-after-reservation")
            return object()

        result = construct_after_dispatch_reservation(
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
        self.assertEqual(
            ["factory-called-after-reservation"],
            observations,
        )
        self.assertEqual("candidate-reserved", result["reservation"]["eventType"])
        self.assertIsNotNone(result["appServerHandle"])

    def test_current_documents_fail_before_factory_construction(self) -> None:
        protocol_path = ROOT / (
            "registry/human-ai-collaboration-tdd-noncomparative-treatment-"
            "diagnostic-protocol-2026-07-26.json"
        )
        preflight_path = ROOT / (
            "registry/human-ai-collaboration-tdd-noncomparative-treatment-"
            "diagnostic-source-governance-preflight-2026-07-26.json"
        )
        audit_path = ROOT / (
            "registry/human-ai-collaboration-tdd-exact-candidate-admission-"
            "gap-audit-2026-07-26.json"
        )
        protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
        candidate = next(
            item
            for item in protocol["candidates"]
            if item["candidateId"] == CANDIDATE_ID
        )
        admission = self.bundle.admission
        admission.update(
            {
                "candidateIdentitySha256": canonical_sha256(
                    candidate_identity(candidate)
                ),
                "protocolFileSha256": file_sha256(protocol_path),
                "sourceGovernancePreflightFileSha256": file_sha256(
                    preflight_path
                ),
                "staticGapAuditFileSha256": file_sha256(audit_path),
            }
        )
        self.bundle.admission_path.write_text(
            json.dumps(admission, indent=2) + "\n",
            encoding="utf-8",
        )
        calls = 0

        def factory(_: dict, _register: object) -> object:
            nonlocal calls
            calls += 1
            return object()

        with self.assertRaisesRegex(
            RuntimeError,
            "protocol execution eligibility",
        ):
            construct_after_dispatch_reservation(
                protocol_path=protocol_path,
                source_governance_preflight_path=preflight_path,
                static_gap_audit_path=audit_path,
                diagnostic_admission_path=self.bundle.admission_path,
                candidate_id=CANDIDATE_ID,
                reservation_id="reservation-01",
                observed_at=OBSERVED_AT,
                app_server_factory=factory,
                app_server_handle_validator=valid_handle,
            )
        self.assertEqual(0, calls)
        self.assertFalse(self.ledger_path.exists())

    def test_factory_failure_consumes_reservation_and_blocks_retry(self) -> None:
        calls = 0

        def failing_factory(_: dict, _register: object) -> object:
            nonlocal calls
            calls += 1
            raise RuntimeError("synthetic factory failure")

        with self.assertRaisesRegex(RuntimeError, "synthetic factory failure"):
            construct_after_dispatch_reservation(
                protocol_path=self.bundle.protocol_path,
                source_governance_preflight_path=self.bundle.preflight_path,
                static_gap_audit_path=self.bundle.audit_path,
                diagnostic_admission_path=self.bundle.admission_path,
                candidate_id=CANDIDATE_ID,
                reservation_id="reservation-01",
                observed_at=OBSERVED_AT,
                app_server_factory=failing_factory,
                app_server_handle_validator=valid_handle,
            )
        self.assertEqual(1, calls)
        self.assertEqual(
            2,
            len(DispatchIdentityLedger(self.ledger_path).read_events()),
        )
        with self.assertRaisesRegex(
            DispatchGateError,
            "candidate dispatch cap",
        ):
            construct_after_dispatch_reservation(
                protocol_path=self.bundle.protocol_path,
                source_governance_preflight_path=self.bundle.preflight_path,
                static_gap_audit_path=self.bundle.audit_path,
                diagnostic_admission_path=self.bundle.admission_path,
                candidate_id=CANDIDATE_ID,
                reservation_id="reservation-02",
                observed_at=OBSERVED_AT,
                app_server_factory=failing_factory,
                app_server_handle_validator=valid_handle,
            )
        self.assertEqual(1, calls)

    def test_caller_cannot_supply_an_alternate_ledger_path(self) -> None:
        self.assertNotIn(
            "ledger_path",
            inspect.signature(
                construct_after_dispatch_reservation
            ).parameters,
        )

    def test_non_callable_factory_rejects_before_reservation(self) -> None:
        with self.assertRaisesRegex(TypeError, "factory must be callable"):
            construct_after_dispatch_reservation(
                protocol_path=self.bundle.protocol_path,
                source_governance_preflight_path=self.bundle.preflight_path,
                static_gap_audit_path=self.bundle.audit_path,
                diagnostic_admission_path=self.bundle.admission_path,
                candidate_id=CANDIDATE_ID,
                reservation_id="reservation-01",
                observed_at=OBSERVED_AT,
                app_server_factory=None,
                app_server_handle_validator=valid_handle,
            )
        self.assertFalse(self.ledger_path.exists())

    def test_non_callable_handle_validator_rejects_before_reservation(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "handle validator must be callable",
        ):
            construct_after_dispatch_reservation(
                protocol_path=self.bundle.protocol_path,
                source_governance_preflight_path=self.bundle.preflight_path,
                static_gap_audit_path=self.bundle.audit_path,
                diagnostic_admission_path=self.bundle.admission_path,
                candidate_id=CANDIDATE_ID,
                reservation_id="reservation-01",
                observed_at=OBSERVED_AT,
                app_server_factory=(
                    lambda _reservation, _register: object()
                ),
                app_server_handle_validator=None,
            )
        self.assertFalse(self.ledger_path.exists())


if __name__ == "__main__":
    unittest.main()
