import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.build_handoff_loader_trial_packet import (
    build_preflight_packet,
    canonical_sha256,
    validate_capture_capability_registry,
    validate_packet_binding,
    validate_producer_loader_event,
)


ROOT = Path(__file__).resolve().parents[1]


class HandoffLoaderTrialPacketTests(unittest.TestCase):
    def _record(self, *, host_identity="codex-desktop", host_version="test"):
        return {
            "evidenceId": "synthetic-capture-capability-01",
            "evidenceClass": "host-adapter-capability-evidence",
            "adapterIdentity": "codex-host-loader-capture",
            "adapterVersion": "test-v1",
            "hostIdentity": host_identity,
            "hostVersion": host_version,
            "captureSurface": "synthetic-parent-observed-loader-event",
            "artifactRef": "synthetic://host/capture-capability",
            "artifactSha256": "a" * 64,
            "observedAt": "2026-07-24T00:00:00Z",
            "evidenceScope": "synthetic-unit-fixture-only",
            "claimBoundary": {
                "provesCaptureCapabilityOnly": True,
                "provesLoaderInvocation": False,
                "provesFreshSession": False,
                "provesReceiverOutcome": False,
                "provesAutomaticThreadCreation": False,
                "provesActualModelOrReasoning": False,
            },
        }

    def _registry(self, **record_overrides):
        record = self._record()
        record.update(record_overrides)
        return {
            "path": str(
                ROOT
                / "registry"
                / "handoff-loader-trial-preflight-contract-2026-07-24.json"
            ),
            "sha256": "d" * 64,
            "records": [record],
        }

    def _packet(self, capture="unknown"):
        kwargs = {}
        if capture == "available":
            kwargs = {
                "loader_capture_adapter_identity": "codex-host-loader-capture",
                "loader_capture_adapter_version": "test-v1",
                "capture_capability_evidence_id": (
                    "synthetic-capture-capability-01"
                ),
            }
        return build_preflight_packet(host_identity="codex-desktop", host_version="test", requested_model="gpt-5.3-codex-spark", requested_reasoning_effort="low", loader_evidence_capture=capture, **kwargs)

    def test_synthetic_admitted_available_is_only_ready_to_attempt(self):
        with patch(
            "scripts.build_handoff_loader_trial_packet.load_capture_capability_registry",
            return_value=self._registry(),
        ):
            packet = self._packet("available")
            self.assertEqual("ready-for-separately-authorized-handoff-loader-attempt", packet["status"])
            self.assertEqual([], validate_packet_binding(packet))
            self.assertTrue(packet["privateOracle"]["canonicalArmCEvaluator"].endswith("_verify_live_context_arm_c"))
            self.assertTrue(all(value is False for key, value in packet.items() if key.startswith("countsAs")))
            self.assertEqual(
                "synthetic-capture-capability-01",
                packet["publicPacket"]["captureCapabilityEvidence"]["evidenceId"],
            )

    def test_unavailable_and_unknown_are_blocked(self):
        for capture in ("unavailable", "unknown"):
            with self.subTest(capture=capture):
                packet = self._packet(capture)
                self.assertEqual("blocked-missing-handoff-loader-observability", packet["status"])
                self.assertEqual([], validate_packet_binding(packet))
                self.assertIsNone(packet["publicPacket"]["loaderCaptureAdapter"])
                self.assertIsNone(packet["publicPacket"]["captureCapabilityEvidence"])

    def test_loader_event_binds_identity_manifest_task_and_source(self):
        with patch(
            "scripts.build_handoff_loader_trial_packet.load_capture_capability_registry",
            return_value=self._registry(),
        ):
            packet = self._packet("available")
            binding = packet["publicPacket"]["payloadBinding"]
            event = {"identity": binding["identity"], "fileManifestSha256": binding["fileManifestSha256"], "taskId": "producer-1", "evidenceSource": "host-loader-event"}
            self.assertEqual([], validate_producer_loader_event(packet, producer_task_id="producer-1", loader_event=event))
            for key, value, code in (("identity", "other", "fail-loader-event-identity"), ("fileManifestSha256", "0" * 64, "fail-loader-event-manifest"), ("taskId", "other-task", "fail-loader-event-task-binding"), ("evidenceSource", "agent-self-report", "fail-loader-event-source")):
                variant = dict(event); variant[key] = value
                self.assertIn(code, validate_producer_loader_event(packet, producer_task_id="producer-1", loader_event=variant))

    def test_public_packet_tamper_is_rejected_after_digest_recompute_when_shape_collapses(self):
        packet = self._packet()
        packet["publicPacket"]["privateOracle"] = copy.deepcopy(packet["privateOracle"])
        packet["packetSha256"] = canonical_sha256(packet["publicPacket"])
        self.assertIn("fail-public-packet-shape", validate_packet_binding(packet))

    def test_private_binding_and_count_promotion_are_rejected(self):
        packet = self._packet()
        packet["privateOracle"]["selectedPayload"]["identity"] = "other"
        packet["oracleSha256"] = canonical_sha256(packet["privateOracle"])
        self.assertIn("fail-private-oracle-binding", validate_packet_binding(packet))
        packet = self._packet(); packet["countsAsFreshSessionProof"] = True
        self.assertIn("hard-fail-preflight-count-promotion", validate_packet_binding(packet))

    def test_canonical_protocol_rejects_custom_path_and_paired_payload_drift(self):
        with tempfile.TemporaryDirectory() as temporary:
            custom = Path(temporary) / "protocol.json"
            custom.write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "canonical repository protocol"):
                build_preflight_packet(host_identity="codex-desktop", host_version="test", requested_model="gpt-5.3-codex-spark", requested_reasoning_effort="low", loader_evidence_capture="unknown", protocol_path=custom)
        packet = self._packet()
        public = packet["publicPacket"]
        public["payloadBinding"]["identity"] = "other-payload"
        packet["privateOracle"]["selectedPayload"]["identity"] = "other-payload"
        packet["packetSha256"] = canonical_sha256(public)
        packet["oracleSha256"] = canonical_sha256(packet["privateOracle"])
        failures = validate_packet_binding(packet)
        self.assertIn("fail-canonical-payload-binding", failures)
        self.assertIn("fail-private-oracle-binding", failures)

    def test_protocol_digest_and_available_adapter_evidence_are_bound(self):
        packet = self._packet()
        packet["publicPacket"]["payloadBinding"]["protocolSha256"] = "b" * 64
        packet["privateOracle"]["protocolSha256"] = "b" * 64
        packet["packetSha256"] = canonical_sha256(packet["publicPacket"])
        packet["oracleSha256"] = canonical_sha256(packet["privateOracle"])
        failures = validate_packet_binding(packet)
        self.assertIn("fail-canonical-payload-binding", failures)
        self.assertIn("fail-private-oracle-binding", failures)
        with patch(
            "scripts.build_handoff_loader_trial_packet.load_capture_capability_registry",
            return_value=self._registry(),
        ):
            packet = self._packet("available")
            packet["publicPacket"]["captureCapabilityEvidence"][
                "artifactSha256"
            ] = "b" * 64
            packet["packetSha256"] = canonical_sha256(packet["publicPacket"])
            self.assertIn(
                "fail-canonical-capture-capability-binding",
                validate_packet_binding(packet),
            )

    def test_shape_only_and_unknown_evidence_id_fail_closed(self):
        with self.assertRaisesRegex(
            ValueError,
            "admitted canonical capability evidence",
        ):
            self._packet("available")
        with patch(
            "scripts.build_handoff_loader_trial_packet.load_capture_capability_registry",
            return_value=self._registry(),
        ):
            with self.assertRaisesRegex(
                ValueError,
                "admitted canonical capability evidence",
            ):
                build_preflight_packet(
                    host_identity="codex-desktop",
                    host_version="test",
                    requested_model="gpt-5.3-codex-spark",
                    requested_reasoning_effort="low",
                    loader_evidence_capture="available",
                    loader_capture_adapter_identity="codex-host-loader-capture",
                    loader_capture_adapter_version="test-v1",
                    capture_capability_evidence_id="unknown-evidence-id",
                )

    def test_canonical_record_must_match_host_and_adapter(self):
        with patch(
            "scripts.build_handoff_loader_trial_packet.load_capture_capability_registry",
            return_value=self._registry(hostIdentity="other-host"),
        ):
            with self.assertRaisesRegex(ValueError, "does not match host and adapter"):
                self._packet("available")

    def test_capture_registry_rejects_claim_promotion(self):
        record = self._record()
        record["claimBoundary"]["provesLoaderInvocation"] = True
        document = {
            "captureCapabilityEvidenceRegistry": {
                "schema": 1,
                "status": "admitted-capture-capability-evidence-present",
                "requiredRecordFields": sorted(record),
                "admittedRecords": [record],
                "emptyResult": "blocked-missing-handoff-loader-observability",
                "claimBoundary": {
                    "callerAssertionIsAdmissionEvidence": False,
                    "shapeValidReferenceIsAdmissionEvidence": False,
                    "registryPresenceProvesLoaderInvocation": False,
                    "registryPresenceProvesFreshSession": False,
                },
            }
        }
        self.assertIn(
            "hard-fail-capture-capability-claim-promotion",
            validate_capture_capability_registry(document),
        )

    def test_nonavailable_cannot_be_promoted_by_adapter_evidence(self):
        packet = self._packet("unknown")
        packet["publicPacket"]["loaderCaptureAdapter"] = {"identity": "claimed", "version": "v1"}
        packet["publicPacket"]["captureCapabilityEvidence"] = self._record()
        packet["packetSha256"] = canonical_sha256(packet["publicPacket"])
        self.assertIn("hard-fail-nonavailable-capture-promoted", validate_packet_binding(packet))

    def test_cli_never_prints_private_oracle(self):
        result = subprocess.run([sys.executable, "-B", "scripts/build_handoff_loader_trial_packet.py", "--host", "codex-desktop", "--host-version", "test", "--model", "gpt-5.3-codex-spark", "--reasoning", "low", "--loader-evidence-capture", "unknown"], cwd=ROOT, check=True, text=True, capture_output=True)
        rendered = json.loads(result.stdout)
        self.assertNotIn("privateOracle", rendered)
        self.assertNotIn("canonicalArmCEvaluator", result.stdout)
        self.assertIn("oracleSha256", rendered)


if __name__ == "__main__":
    unittest.main()
