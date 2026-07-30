from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from scripts.process_fidelity_chained_transform_dispatch_gate import (
    AMENDMENT_PATH,
    BASE_PROTOCOL_PATH,
    HOP_IDS,
    RAW_CAPTURE_SCHEMA_PATH,
    ROOT,
    TRACE_SCHEMA_PATH,
    build_dispatch_authorization_envelope,
    canonical_sha256,
    file_sha256,
)
from scripts.process_fidelity_chained_transform_dispatch_ledger import (
    ChainedTransformDispatchLedger,
    DispatchLedgerError,
)


SHA_A = "a" * 64
SHA_B = "b" * 64
SHA_C = "c" * 64


class ProcessFidelityChainedTransformDispatchLedgerTests(
    unittest.TestCase
):
    def copy_contracts(self, target: Path) -> None:
        for relative in (
            BASE_PROTOCOL_PATH,
            AMENDMENT_PATH,
            RAW_CAPTURE_SCHEMA_PATH,
            TRACE_SCHEMA_PATH,
        ):
            destination = target / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / relative, destination)

    def build_fixture(
        self,
        target: Path,
        *,
        run_id: str = "fixture-run-01",
        authority_id: str = "authority-fixture-01",
        authority_nonce: str = "nonce-fixture-01",
        raw_root: str = "audits/live-fixture-run-01",
    ) -> tuple[dict, str]:
        self.copy_contracts(target)
        now = datetime.now(timezone.utc).replace(microsecond=0)
        observed_at = now.isoformat()
        authority = {
            "schema": 1,
            "kind": "one-chained-transform-run-authority",
            "authorityId": authority_id,
            "authorityLocator": "fixture://explicit-user-scope",
            "nonce": authority_nonce,
            "runId": run_id,
            "blockIndex": 1,
            "positionInBlock": 1,
            "authorizedHopIds": list(HOP_IDS),
            "maximumAgentDispatchCount": 3,
            "model": "gpt-5.3-codex-spark",
            "reasoningEffort": "low",
            "providerFallbackAllowed": False,
            "dispatchAuthorized": True,
            "automaticRetryAllowed": False,
            "replacementDispatchAllowed": False,
            "strongDiagnosticAuthorized": False,
            "externalAccessAuthorized": False,
            "hostConfigurationMutationAuthorized": False,
            "globalSkillMutationAuthorized": False,
            "cleanupAuthorized": False,
            "notBefore": (now - timedelta(seconds=10)).isoformat(),
            "expiresAt": (now + timedelta(minutes=10)).isoformat(),
        }
        authority_path = target / f"{authority_id}.json"
        authority_path.write_text(
            json.dumps(authority, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        raw_response = {
            "id": 2,
            "result": {
                "thread": {
                    "id": f"thread-preflight-{run_id}",
                    "model": "gpt-5.3-codex-spark",
                    "reasoningEffort": "low",
                    "modelProvider": "openai",
                }
            },
        }
        raw_path = (
            target
            / "audits"
            / f"route-preflight-{run_id}"
            / "response.json"
        )
        raw_path.parent.mkdir(parents=True)
        raw_path.write_text(
            json.dumps(raw_response, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        observation = {
            "schema": 1,
            "kind": "codex-app-server-thread-route-observation",
            "hostId": "windows-fixture",
            "hostVersion": "codex-cli 0.145.0",
            "appServerTransport": "stdio",
            "observedAt": observed_at,
            "rawThreadStartResponsePath": raw_path.relative_to(
                target
            ).as_posix(),
            "rawThreadStartResponseSha256": file_sha256(raw_path),
            "turnStartRequestCount": 0,
            "providerFallbackRequested": False,
        }
        observation_path = target / f"route-observation-{run_id}.json"
        observation_path.write_text(
            json.dumps(observation, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        envelope = build_dispatch_authorization_envelope(
            root=target,
            authority_document_path=authority_path,
            route_observation_path=observation_path,
            run_id=run_id,
            block_index=1,
            position_in_block=1,
            raw_evidence_relative_path=raw_root,
            observed_at=observed_at,
        )
        return envelope, observed_at

    def reserve(
        self,
        ledger: ChainedTransformDispatchLedger,
        envelope: dict,
        observed_at: str,
        reservation_id: str = "reservation-01",
    ) -> dict:
        return ledger.reserve(
            envelope=envelope,
            reservation_id=reservation_id,
            observed_at=observed_at,
        )

    def start(
        self,
        ledger: ChainedTransformDispatchLedger,
        envelope: dict,
        observed_at: str,
        index: int,
        reservation_id: str = "reservation-01",
    ) -> dict:
        hop_id = HOP_IDS[index]
        return ledger.record_hop_started(
            reservation_id=reservation_id,
            hop_id=hop_id,
            dispatch_nonce=envelope["stageAuthorizations"][index][
                "dispatchNonce"
            ],
            start_id=f"start-{index + 1}",
            thread_id=f"thread-{index + 1}",
            turn_start_request_id=f"request-{index + 1}",
            observed_at=observed_at,
        )

    def terminal(
        self,
        ledger: ChainedTransformDispatchLedger,
        observed_at: str,
        index: int,
        *,
        status: str = "completed-valid",
        reservation_id: str = "reservation-01",
    ) -> dict:
        return ledger.record_hop_terminal(
            reservation_id=reservation_id,
            hop_id=HOP_IDS[index],
            terminal_id=f"terminal-{index + 1}",
            turn_id=f"turn-{index + 1}",
            terminal_status=status,
            receipt_sha256=SHA_A if status == "completed-valid" else None,
            error_evidence_sha256=(
                None if status == "completed-valid" else SHA_B
            ),
            observed_at=observed_at,
        )

    def test_zero_dispatch_preflight_does_not_mutate_or_promote(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            envelope, observed_at = self.build_fixture(root)
            ledger = ChainedTransformDispatchLedger(root / "ledger.jsonl")
            result = ledger.zero_dispatch_preflight(
                envelope=envelope,
                observed_at=observed_at,
            )
            self.assertTrue(result["reservationWouldBeAccepted"])
            self.assertFalse(result["modelCalled"])
            self.assertFalse(result["ledgerMutationPerformed"])
            self.assertFalse(result["liveDispatchReady"])
            self.assertEqual(result["modelDispatchCount"], 0)
            self.assertFalse(ledger.path.exists())

    def test_ordered_three_hop_run_has_valid_hash_chain(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            envelope, observed_at = self.build_fixture(root)
            ledger = ChainedTransformDispatchLedger(root / "ledger.jsonl")
            self.reserve(ledger, envelope, observed_at)
            for index in range(3):
                self.start(ledger, envelope, observed_at, index)
                self.terminal(ledger, observed_at, index)
            events = ledger.read_events()
            self.assertEqual(len(events), 7)
            self.assertEqual(
                [event["sequence"] for event in events],
                list(range(1, 8)),
            )
            status = ledger.read_reservation_status("reservation-01")
            self.assertEqual(status["modelDispatchCount"], 3)
            self.assertEqual(status["completedValidHopCount"], 3)
            self.assertIsNone(status["nextHopId"])
            self.assertFalse(status["formalCohortEligible"])
            self.assertFalse(status["liveDispatchReady"])

    def test_duplicate_authority_run_nonce_and_reservation_are_rejected(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            envelope, observed_at = self.build_fixture(root)
            ledger = ChainedTransformDispatchLedger(root / "ledger.jsonl")
            self.reserve(ledger, envelope, observed_at)
            result = ledger.zero_dispatch_preflight(
                envelope=envelope,
                observed_at=observed_at,
            )
            self.assertIn("duplicate-authorization", result["failures"])
            self.assertIn("duplicate-run-cell", result["failures"])
            self.assertIn("duplicate-authority-nonce", result["failures"])
            self.assertIn("duplicate-dispatch-nonce", result["failures"])
            with self.assertRaises(DispatchLedgerError):
                self.reserve(ledger, envelope, observed_at)

    def test_out_of_order_hop_and_duplicate_start_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            envelope, observed_at = self.build_fixture(root)
            ledger = ChainedTransformDispatchLedger(root / "ledger.jsonl")
            self.reserve(ledger, envelope, observed_at)
            with self.assertRaises(DispatchLedgerError):
                self.start(ledger, envelope, observed_at, 1)
            self.start(ledger, envelope, observed_at, 0)
            with self.assertRaises(DispatchLedgerError):
                self.start(ledger, envelope, observed_at, 0)
            with self.assertRaises(DispatchLedgerError):
                self.start(ledger, envelope, observed_at, 1)

    def test_failed_terminal_consumes_run_and_blocks_retry(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            envelope, observed_at = self.build_fixture(root)
            ledger = ChainedTransformDispatchLedger(root / "ledger.jsonl")
            self.reserve(ledger, envelope, observed_at)
            self.start(ledger, envelope, observed_at, 0)
            self.terminal(
                ledger,
                observed_at,
                0,
                status="failed",
            )
            status = ledger.read_reservation_status("reservation-01")
            self.assertTrue(status["blocked"])
            self.assertEqual(status["blockedTerminalStatus"], "failed")
            self.assertIsNone(status["nextHopId"])
            with self.assertRaises(DispatchLedgerError):
                self.start(ledger, envelope, observed_at, 0)
            with self.assertRaises(DispatchLedgerError):
                self.start(ledger, envelope, observed_at, 1)

    def test_ambiguous_terminal_requires_retain_consumed_reconciliation(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            envelope, observed_at = self.build_fixture(root)
            ledger = ChainedTransformDispatchLedger(root / "ledger.jsonl")
            self.reserve(ledger, envelope, observed_at)
            self.start(ledger, envelope, observed_at, 0)
            self.terminal(
                ledger,
                observed_at,
                0,
                status="ambiguous",
            )
            before = ledger.read_reservation_status("reservation-01")
            self.assertFalse(before["ambiguousReconciled"])
            event = ledger.reconcile_ambiguous(
                reservation_id="reservation-01",
                reconciliation_id="reconciliation-01",
                reconciliation_document_sha256=SHA_C,
                observed_at=observed_at,
            )
            self.assertEqual(
                event["disposition"],
                "retain-consumed-no-retry",
            )
            after = ledger.read_reservation_status("reservation-01")
            self.assertTrue(after["ambiguousReconciled"])
            with self.assertRaises(DispatchLedgerError):
                ledger.reconcile_ambiguous(
                    reservation_id="reservation-01",
                    reconciliation_id="reconciliation-02",
                    reconciliation_document_sha256=SHA_C,
                    observed_at=observed_at,
                )

    def test_corrupt_hash_and_partial_tail_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            envelope, observed_at = self.build_fixture(root)
            ledger = ChainedTransformDispatchLedger(root / "ledger.jsonl")
            self.reserve(ledger, envelope, observed_at)
            original = ledger.path.read_text(encoding="utf-8")
            event = json.loads(original)
            event["runId"] = "tampered-run"
            ledger.path.write_text(
                json.dumps(event, separators=(",", ":")) + "\n",
                encoding="utf-8",
            )
            with self.assertRaises(DispatchLedgerError):
                ledger.read_events()
            ledger.path.write_text(
                original + '{"schema":1',
                encoding="utf-8",
            )
            with self.assertRaises(DispatchLedgerError):
                ledger.read_events()

    def test_nonce_drift_and_expired_reservation_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            envelope, observed_at = self.build_fixture(root)
            ledger = ChainedTransformDispatchLedger(root / "ledger.jsonl")
            drifted = deepcopy(envelope)
            drifted["stageAuthorizations"][0]["dispatchNonce"] = SHA_A
            body = dict(drifted)
            body.pop("authorizationSha256")
            drifted["authorizationSha256"] = canonical_sha256(body)
            with self.assertRaises(DispatchLedgerError):
                self.reserve(ledger, drifted, observed_at)
            expired_time = (
                datetime.fromisoformat(observed_at) + timedelta(hours=1)
            ).isoformat()
            with self.assertRaises(DispatchLedgerError):
                self.reserve(ledger, envelope, expired_time)

    def test_terminal_status_and_evidence_shape_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            envelope, observed_at = self.build_fixture(root)
            ledger = ChainedTransformDispatchLedger(root / "ledger.jsonl")
            self.reserve(ledger, envelope, observed_at)
            self.start(ledger, envelope, observed_at, 0)
            with self.assertRaises(DispatchLedgerError):
                ledger.record_hop_terminal(
                    reservation_id="reservation-01",
                    hop_id=HOP_IDS[0],
                    terminal_id="terminal-invalid",
                    turn_id="turn-invalid",
                    terminal_status="completed-valid",
                    receipt_sha256=None,
                    error_evidence_sha256=None,
                    observed_at=observed_at,
                )
            with self.assertRaises(DispatchLedgerError):
                ledger.record_hop_terminal(
                    reservation_id="reservation-01",
                    hop_id=HOP_IDS[0],
                    terminal_id="terminal-invalid",
                    turn_id="turn-invalid",
                    terminal_status="unknown",
                    receipt_sha256=SHA_A,
                    error_evidence_sha256=None,
                    observed_at=observed_at,
                )

    def test_cross_process_contenders_consume_authorization_once(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            envelope, observed_at = self.build_fixture(root)
            envelope_path = root / "envelope.json"
            envelope_path.write_text(
                json.dumps(envelope, ensure_ascii=False),
                encoding="utf-8",
            )
            ledger_path = root / "ledger.jsonl"
            child = (
                "import json,sys;"
                "from pathlib import Path;"
                "from scripts.process_fidelity_chained_transform_dispatch_ledger "
                "import ChainedTransformDispatchLedger;"
                "e=json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'));"
                "ChainedTransformDispatchLedger(Path(sys.argv[2])).reserve("
                "envelope=e,reservation_id=sys.argv[3],"
                "observed_at=sys.argv[4])"
            )
            processes = [
                subprocess.Popen(
                    [
                        sys.executable,
                        "-c",
                        child,
                        str(envelope_path),
                        str(ledger_path),
                        f"reservation-process-{index}",
                        observed_at,
                    ],
                    cwd=ROOT,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                for index in range(2)
            ]
            results = [process.communicate(timeout=30) for process in processes]
            return_codes = [process.returncode for process in processes]
            self.assertEqual(sorted(return_codes), [0, 1], results)
            ledger = ChainedTransformDispatchLedger(ledger_path)
            events = ledger.read_events()
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0]["eventType"], "run-reserved")


if __name__ == "__main__":
    unittest.main()
