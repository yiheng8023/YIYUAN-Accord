from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from scripts.process_fidelity_chained_transform_dispatch_gate import (
    AMENDMENT_PATH,
    BASE_PROTOCOL_PATH,
    HOP_IDS,
    RAW_CAPTURE_SCHEMA_PATH,
    ROOT,
    TRACE_SCHEMA_PATH,
    DispatchGateError,
    build_dispatch_authorization_envelope,
    canonical_sha256,
    file_sha256,
    validate_dispatch_authorization_envelope,
    validate_native_hop_receipts,
)


class ProcessFidelityChainedTransformDispatchGateTests(unittest.TestCase):
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
        observed_model: str = "gpt-5.3-codex-spark",
        expires_delta_seconds: int = 300,
    ) -> dict:
        self.copy_contracts(target)
        now = datetime.now(timezone.utc).replace(microsecond=0)
        authority = {
            "schema": 1,
            "kind": "one-chained-transform-run-authority",
            "authorityId": "authority-fixture-01",
            "authorityLocator": "fixture://explicit-user-scope",
            "nonce": "nonce-fixture-01",
            "runId": "fixture-run-01",
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
            "expiresAt": (
                now + timedelta(seconds=expires_delta_seconds)
            ).isoformat(),
        }
        authority_path = target / "authority.json"
        authority_path.write_text(
            json.dumps(authority, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        raw_response = {
            "id": 2,
            "result": {
                "thread": {
                    "id": "thread-preflight",
                    "model": observed_model,
                    "reasoningEffort": "low",
                    "modelProvider": "openai",
                }
            },
        }
        raw_path = target / "audits" / "route-preflight" / "response.json"
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
            "observedAt": now.isoformat(),
            "rawThreadStartResponsePath": raw_path.relative_to(
                target
            ).as_posix(),
            "rawThreadStartResponseSha256": file_sha256(raw_path),
            "turnStartRequestCount": 0,
            "providerFallbackRequested": False,
        }
        observation_path = target / "route-observation.json"
        observation_path.write_text(
            json.dumps(observation, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return build_dispatch_authorization_envelope(
            root=target,
            authority_document_path=authority_path,
            route_observation_path=observation_path,
            run_id="fixture-run-01",
            block_index=1,
            position_in_block=1,
            raw_evidence_relative_path="audits/live-fixture-run-01",
            observed_at=now.isoformat(),
        )

    def write_artifact(
        self,
        root: Path,
        relative: str,
        artifact_id: str,
    ) -> dict:
        value = {
            "artifactId": artifact_id,
            "values": {"goal": f"value:{artifact_id}"},
            "provenanceIds": ["goal"],
            "assumptionIds": [],
            "detectedLossIds": [],
            "sections": {"fidelitySnapshot": {}},
        }
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(value, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return {
            "artifactId": artifact_id,
            "path": relative,
            "rawSha256": file_sha256(path),
            "canonicalSha256": canonical_sha256(value),
        }

    def receipt_fixture(
        self,
        envelope: dict,
        capture_root: Path,
    ) -> list[dict]:
        run_id = envelope["cell"]["runId"]
        inputs = [
            self.write_artifact(capture_root, "artifacts/S0.json", "S0"),
            self.write_artifact(
                capture_root,
                f"artifacts/{run_id}-M1.json",
                f"{run_id}-M1",
            ),
            self.write_artifact(
                capture_root,
                f"artifacts/{run_id}-R2.json",
                f"{run_id}-R2",
            ),
        ]
        outputs = [
            self.write_artifact(
                capture_root,
                f"artifacts/{run_id}-O1.json",
                f"{run_id}-O1",
            ),
            self.write_artifact(
                capture_root,
                f"artifacts/{run_id}-O2.json",
                f"{run_id}-O2",
            ),
            self.write_artifact(
                capture_root,
                f"artifacts/{run_id}-O3.json",
                f"{run_id}-O3",
            ),
        ]
        receipts: list[dict] = []
        previous_receipt_sha = None
        for index, hop_id in enumerate(HOP_IDS):
            thread_id = f"thread-{index + 1}"
            turn_id = f"turn-{index + 1}"
            thread_request_id = 10 + index * 2
            turn_request_id = thread_request_id + 1
            stage_contract_value = {
                "schema": 1,
                "stageId": hop_id,
                "inputArtifactId": inputs[index]["artifactId"],
                "outputArtifactId": outputs[index]["artifactId"],
                "toolsAllowed": [],
            }
            stage_contract_relative = f"contracts/{hop_id}.json"
            stage_contract_path = capture_root / stage_contract_relative
            stage_contract_path.parent.mkdir(parents=True, exist_ok=True)
            stage_contract_path.write_text(
                json.dumps(
                    stage_contract_value,
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            stage_contract = {
                "path": stage_contract_relative,
                "rawSha256": file_sha256(stage_contract_path),
                "canonicalSha256": canonical_sha256(stage_contract_value),
            }
            input_path = capture_root / inputs[index]["path"]
            input_value = json.loads(input_path.read_text(encoding="utf-8"))
            turn_payload = {
                "artifact": input_value,
                "stageContract": stage_contract_value,
            }
            turn_input = [
                {
                    "type": "text",
                    "text": json.dumps(
                        turn_payload,
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    ),
                }
            ]
            event_relative = f"events/{hop_id}.jsonl"
            event_path = capture_root / event_relative
            event_path.parent.mkdir(parents=True, exist_ok=True)
            events = [
                {
                    "captureSequence": 1,
                    "direction": "client-to-server",
                    "message": {
                        "id": thread_request_id,
                        "method": "thread/start",
                        "params": {
                            "model": "gpt-5.3-codex-spark",
                            "allowProviderModelFallback": False,
                        },
                    },
                },
                {
                    "captureSequence": 2,
                    "direction": "server-to-client",
                    "message": {
                        "id": thread_request_id,
                        "result": {
                            "thread": {
                                "id": thread_id,
                                "model": "gpt-5.3-codex-spark",
                                "reasoningEffort": "low",
                                "modelProvider": "openai",
                            }
                        },
                    },
                },
                {
                    "captureSequence": 3,
                    "direction": "client-to-server",
                    "message": {
                        "id": turn_request_id,
                        "method": "turn/start",
                        "params": {
                            "threadId": thread_id,
                            "model": "gpt-5.3-codex-spark",
                            "effort": "low",
                            "input": turn_input,
                        },
                    },
                },
                {
                    "captureSequence": 4,
                    "direction": "server-to-client",
                    "message": {
                        "id": turn_request_id,
                        "result": {
                            "turn": {
                                "id": turn_id,
                                "status": "inProgress",
                            }
                        },
                    },
                },
                {
                    "captureSequence": 5,
                    "direction": "server-to-client",
                    "message": {
                        "method": "item/completed",
                        "params": {
                            "threadId": thread_id,
                            "turnId": turn_id,
                            "item": {"type": "userMessage"},
                        },
                    },
                },
                {
                    "captureSequence": 6,
                    "direction": "server-to-client",
                    "message": {
                        "method": "item/completed",
                        "params": {
                            "threadId": thread_id,
                            "turnId": turn_id,
                            "item": {"type": "reasoning"},
                        },
                    },
                },
                {
                    "captureSequence": 7,
                    "direction": "server-to-client",
                    "message": {
                        "method": "item/completed",
                        "params": {
                            "threadId": thread_id,
                            "turnId": turn_id,
                            "item": {"type": "agentMessage"},
                        },
                    },
                },
                {
                    "captureSequence": 8,
                    "direction": "server-to-client",
                    "message": {
                        "method": "turn/completed",
                        "params": {
                            "threadId": thread_id,
                            "turn": {
                                "id": turn_id,
                                "status": "completed",
                            },
                        },
                    },
                },
            ]
            event_path.write_text(
                "".join(
                    json.dumps(event, ensure_ascii=False) + "\n"
                    for event in events
                ),
                encoding="utf-8",
            )
            parent_transform = None
            if index:
                parent_transform = {
                    "kind": (
                        "controlled-mutation"
                        if index == 1
                        else "recovery-envelope"
                    ),
                    "predecessorOutputCanonicalSha256": outputs[
                        index - 1
                    ]["canonicalSha256"],
                    "currentInputCanonicalSha256": inputs[index][
                        "canonicalSha256"
                    ],
                    "parentReceiptSha256": "1" * 64,
                    "contractSha256": "2" * 64,
                    "contractValid": True,
                }
            receipt = {
                "schema": 1,
                "kind": "parent-derived-native-hop-receipt",
                "authorizationSha256": envelope["authorizationSha256"],
                "runId": run_id,
                "hopId": hop_id,
                "sequence": index + 1,
                "predecessorReceiptSha256": previous_receipt_sha,
                "route": {
                    "requestedModel": "gpt-5.3-codex-spark",
                    "requestedReasoningEffort": "low",
                    "hostReportedModel": "gpt-5.3-codex-spark",
                    "hostReportedReasoningEffort": "low",
                    "hostReportedModelProvider": "openai",
                    "providerFallbackRequested": False,
                    "providerExecutionRouteTelemetry": "unknown",
                },
                "identity": {
                    "threadId": thread_id,
                    "turnId": turn_id,
                    "threadStartRequestId": thread_request_id,
                    "turnStartRequestId": turn_request_id,
                    "allNativeEventsMatchIdentity": True,
                },
                "artifacts": {
                    "input": inputs[index],
                    "stageContract": stage_contract,
                    "turnInputCanonicalSha256": canonical_sha256(turn_input),
                    "output": outputs[index],
                },
                "parentInputTransform": parent_transform,
                "activity": {
                    "itemTypes": ["userMessage", "reasoning", "agentMessage"],
                    "toolCallCount": 0,
                    "externalAccessUsedBeyondModelProvider": False,
                    "agentWritePerformed": False,
                },
                "terminal": {
                    "turnStartedObserved": True,
                    "turnCompletedObserved": True,
                    "status": "completed",
                    "error": None,
                    "outputPersisted": True,
                    "runnerTimeout": False,
                },
                "nativeEventLog": {
                    "path": event_relative,
                    "rawSha256": file_sha256(event_path),
                },
            }
            receipt["receiptSha256"] = canonical_sha256(receipt)
            previous_receipt_sha = receipt["receiptSha256"]
            receipts.append(receipt)
        return receipts

    def test_envelope_binds_host_route_but_keeps_live_stopped(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            envelope = self.build_fixture(Path(temporary))
            self.assertEqual(
                [],
                validate_dispatch_authorization_envelope(envelope),
            )
            self.assertEqual(
                "unknown",
                envelope["route"]["providerExecutionRouteTelemetry"],
            )
            self.assertFalse(envelope["boundaries"]["liveDispatchReady"])
            self.assertFalse(
                envelope["boundaries"]["atomicReservationLedgerBound"]
            )

    def test_requested_route_does_not_substitute_for_observed_route(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(
                DispatchGateError,
                "effective thread route",
            ):
                self.build_fixture(
                    Path(temporary),
                    observed_model="gpt-5.6-luna",
                )

    def test_expired_authority_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(
                DispatchGateError,
                "authority window",
            ):
                self.build_fixture(
                    Path(temporary),
                    expires_delta_seconds=-1,
                )

    def test_boundary_promotion_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            envelope = self.build_fixture(Path(temporary))
            envelope["boundaries"]["liveDispatchReady"] = True
            envelope["authorizationSha256"] = canonical_sha256(
                {
                    key: value
                    for key, value in envelope.items()
                    if key != "authorizationSha256"
                }
            )
            self.assertIn(
                "hard-fail-boundary-promotion",
                validate_dispatch_authorization_envelope(envelope),
            )

    def test_resealed_run_cell_drift_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            envelope = self.build_fixture(Path(temporary))
            envelope["cell"]["armId"] = "injected-authority-omission"
            envelope["authorizationSha256"] = canonical_sha256(
                {
                    key: value
                    for key, value in envelope.items()
                    if key != "authorizationSha256"
                }
            )
            self.assertIn(
                "fail-run-cell-binding",
                validate_dispatch_authorization_envelope(envelope),
            )

    def test_valid_receipts_still_do_not_count_as_formal_live_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            envelope = self.build_fixture(root)
            capture_root = root / "capture"
            receipts = self.receipt_fixture(envelope, capture_root)
            result = validate_native_hop_receipts(
                envelope=envelope,
                receipts=receipts,
                capture_root=capture_root,
            )
            self.assertEqual(
                "native-hop-receipts-valid-offline",
                result["status"],
            )
            self.assertEqual(3, result["validatedReceiptCount"])
            self.assertFalse(result["formalLiveEvidenceEligible"])
            self.assertFalse(result["atomicReservationLedgerVerified"])

    def test_route_drift_and_terminal_correctness_cannot_rescue_run(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            envelope = self.build_fixture(root)
            capture_root = root / "capture"
            receipts = self.receipt_fixture(envelope, capture_root)
            receipts[1]["route"]["hostReportedModel"] = "gpt-5.6-luna"
            receipts[1]["receiptSha256"] = canonical_sha256(
                {
                    key: value
                    for key, value in receipts[1].items()
                    if key != "receiptSha256"
                }
            )
            receipts[2]["predecessorReceiptSha256"] = receipts[1][
                "receiptSha256"
            ]
            receipts[2]["receiptSha256"] = canonical_sha256(
                {
                    key: value
                    for key, value in receipts[2].items()
                    if key != "receiptSha256"
                }
            )
            result = validate_native_hop_receipts(
                envelope=envelope,
                receipts=receipts,
                capture_root=capture_root,
            )
            self.assertIn(
                "route-drift:hop-2-routing",
                result["failureCodes"],
            )
            self.assertFalse(result["formalLiveEvidenceEligible"])
            self.assertEqual(0, result["validatedReceiptCount"])

    def test_cross_thread_reuse_and_parent_transform_drift_are_rejected(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            envelope = self.build_fixture(root)
            capture_root = root / "capture"
            receipts = self.receipt_fixture(envelope, capture_root)
            receipts[1]["identity"]["threadId"] = receipts[0]["identity"][
                "threadId"
            ]
            receipts[1]["parentInputTransform"][
                "predecessorOutputCanonicalSha256"
            ] = "f" * 64
            receipts[1]["receiptSha256"] = canonical_sha256(
                {
                    key: value
                    for key, value in receipts[1].items()
                    if key != "receiptSha256"
                }
            )
            receipts[2]["predecessorReceiptSha256"] = receipts[1][
                "receiptSha256"
            ]
            receipts[2]["receiptSha256"] = canonical_sha256(
                {
                    key: value
                    for key, value in receipts[2].items()
                    if key != "receiptSha256"
                }
            )
            result = validate_native_hop_receipts(
                envelope=envelope,
                receipts=receipts,
                capture_root=capture_root,
            )
            self.assertIn(
                "fresh-identity-drift:hop-2-routing",
                result["failureCodes"],
            )
            self.assertIn(
                "material-edge-input-mismatch:hop-2-routing",
                result["failureCodes"],
            )

    def test_artifact_substitution_and_missing_terminal_are_rejected(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            envelope = self.build_fixture(root)
            capture_root = root / "capture"
            receipts = self.receipt_fixture(envelope, capture_root)
            output_path = (
                capture_root
                / receipts[0]["artifacts"]["output"]["path"]
            )
            output_path.write_text("{}\n", encoding="utf-8")
            receipts[2]["terminal"]["turnCompletedObserved"] = False
            receipts[2]["receiptSha256"] = canonical_sha256(
                {
                    key: value
                    for key, value in receipts[2].items()
                    if key != "receiptSha256"
                }
            )
            result = validate_native_hop_receipts(
                envelope=envelope,
                receipts=receipts,
                capture_root=capture_root,
            )
            self.assertIn(
                "output-artifact-drift:hop-1-decomposition",
                result["failureCodes"],
            )
            self.assertIn(
                "terminal-evidence-missing:hop-3-acceptance-and-recovery",
                result["failureCodes"],
            )

    def test_unknown_receipt_field_and_private_oracle_leak_are_rejected(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            envelope = self.build_fixture(root)
            capture_root = root / "capture"
            receipts = self.receipt_fixture(envelope, capture_root)
            receipts[0]["selfReportedRoute"] = "untrusted"
            receipts[0]["receiptSha256"] = canonical_sha256(
                {
                    key: value
                    for key, value in receipts[0].items()
                    if key != "receiptSha256"
                }
            )
            receipts[1]["predecessorReceiptSha256"] = receipts[0][
                "receiptSha256"
            ]
            contract_path = (
                capture_root
                / receipts[1]["artifacts"]["stageContract"]["path"]
            )
            contract = json.loads(contract_path.read_text(encoding="utf-8"))
            contract["thresholds"] = {"private": True}
            contract_path.write_text(
                json.dumps(contract, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            receipts[1]["artifacts"]["stageContract"][
                "rawSha256"
            ] = file_sha256(contract_path)
            receipts[1]["artifacts"]["stageContract"][
                "canonicalSha256"
            ] = canonical_sha256(contract)
            receipts[1]["receiptSha256"] = canonical_sha256(
                {
                    key: value
                    for key, value in receipts[1].items()
                    if key != "receiptSha256"
                }
            )
            receipts[2]["predecessorReceiptSha256"] = receipts[1][
                "receiptSha256"
            ]
            receipts[2]["receiptSha256"] = canonical_sha256(
                {
                    key: value
                    for key, value in receipts[2].items()
                    if key != "receiptSha256"
                }
            )
            result = validate_native_hop_receipts(
                envelope=envelope,
                receipts=receipts,
                capture_root=capture_root,
            )
            self.assertIn(
                "unsupported-receipt-schema:hop-1-decomposition",
                result["failureCodes"],
            )
            self.assertIn(
                "private-oracle-leak:hop-2-routing",
                result["failureCodes"],
            )


if __name__ == "__main__":
    unittest.main()
