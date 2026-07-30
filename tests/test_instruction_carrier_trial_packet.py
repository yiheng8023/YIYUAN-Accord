import copy
import unittest
import json
import subprocess
import sys
from pathlib import Path

from scripts.build_instruction_carrier_trial_packet import (
    build_trial_packet,
    canonical_sha256,
    validate_loader_event_for_packet,
    validate_packet_binding,
)
from scripts.evaluate_instruction_carrier_adherence import evaluate_observation


ROOT = Path(__file__).resolve().parents[1]
CARRIER = ROOT / "AGENTS.md"


class InstructionCarrierTrialPacketTests(unittest.TestCase):
    def _packet(self, capture: str = "available") -> dict:
        return build_trial_packet(
            carrier_path=CARRIER,
            carrier_identity="agents-project-rules",
            host_identity="codex-desktop",
            host_version="test-host-version",
            requested_model="gpt-5.3-codex-spark",
            requested_reasoning_effort="low",
            loader_evidence_capture=capture,
        )

    def test_available_preflight_is_only_ready_to_attempt(self) -> None:
        packet = self._packet()
        self.assertEqual("ready-for-separately-authorized-live-attempt", packet["status"])
        self.assertEqual([], validate_packet_binding(packet))
        self.assertFalse(packet["countsAsLiveHostProof"])
        self.assertFalse(packet["countsAsWeakAgentAcceptance"])
        self.assertFalse(packet["countsAsCrossHostParity"])

    def test_unavailable_loader_capture_is_blocked(self) -> None:
        packet = self._packet("unavailable")
        self.assertEqual("blocked-missing-host-loader-observability", packet["status"])
        self.assertEqual([], validate_packet_binding(packet))

    def test_unknown_loader_capture_is_blocked(self) -> None:
        packet = self._packet("unknown")
        self.assertEqual("blocked-missing-host-loader-observability", packet["status"])
        self.assertEqual([], validate_packet_binding(packet))

    def test_wrong_public_packet_digest_is_rejected(self) -> None:
        packet = self._packet()
        packet["publicPacket"]["targetHost"]["version"] = "different"
        self.assertIn("fail-public-packet-digest", validate_packet_binding(packet))

    def test_wrong_private_carrier_identity_binding_is_rejected(self) -> None:
        packet = self._packet()
        packet["privateOracle"]["expectedResponse"]["carrierId"] = "other-carrier"
        packet["oracleSha256"] = canonical_sha256(packet["privateOracle"])
        self.assertIn("fail-carrier-identity-binding", validate_packet_binding(packet))

    def test_wrong_loader_carrier_digest_is_rejected(self) -> None:
        packet = self._packet()
        failures = validate_loader_event_for_packet(
            packet,
            instantiated_task_id="ctx07-task-01",
            loader_event={
                "carrierId": "agents-project-rules",
                "carrierSha256": "0" * 64,
                "taskId": "ctx07-task-01",
                "evidenceSource": "host-instruction-loader-event",
            },
        )
        self.assertIn("fail-loader-event-carrier-digest", failures)

    def test_wrong_loader_task_id_is_rejected(self) -> None:
        packet = self._packet()
        carrier_sha256 = packet["publicPacket"]["carrier"]["sha256"]
        failures = validate_loader_event_for_packet(
            packet,
            instantiated_task_id="ctx07-task-01",
            loader_event={
                "carrierId": "agents-project-rules",
                "carrierSha256": carrier_sha256,
                "taskId": "ctx07-task-02",
                "evidenceSource": "host-instruction-loader-event",
            },
        )
        self.assertIn("fail-loader-event-task-binding", failures)

    def test_private_oracle_exposure_is_rejected(self) -> None:
        packet = self._packet()
        packet["publicPacket"]["privateOracle"] = copy.deepcopy(packet["privateOracle"])
        self.assertIn("fail-private-oracle-exposed", validate_packet_binding(packet))

    def test_nonavailable_capture_cannot_be_promoted(self) -> None:
        packet = self._packet("unknown")
        packet["status"] = "ready-for-separately-authorized-live-attempt"
        self.assertIn("fail-preflight-status", validate_packet_binding(packet))
        self.assertIn(
            "hard-fail-nonavailable-loader-capture-promoted",
            validate_packet_binding(packet),
        )

    def test_preflight_count_promotion_is_rejected(self) -> None:
        packet = self._packet()
        packet["countsAsLiveHostProof"] = True
        self.assertIn("hard-fail-preflight-count-promotion", validate_packet_binding(packet))

    def test_cli_stdout_never_contains_private_oracle_body(self) -> None:
        result = subprocess.run(
            [sys.executable, "-B", "scripts/build_instruction_carrier_trial_packet.py", "--carrier", "AGENTS.md", "--carrier-id", "agents-project-rules", "--host", "codex-desktop", "--host-version", "test", "--model", "gpt-5.3-codex-spark", "--reasoning", "low", "--loader-evidence-capture", "unknown"],
            cwd=ROOT, check=True, capture_output=True, text=True,
        )
        public = json.loads(result.stdout)
        self.assertNotIn("privateOracle", public)
        self.assertNotIn("requiredRuleResults", result.stdout)
        self.assertIn("oracleSha256", public)

    def test_private_oracle_is_directly_consumable_by_canonical_scorer(self) -> None:
        packet = self._packet()
        expected = packet["privateOracle"]["expectedResponse"]
        raw = json.dumps(expected, separators=(",", ":")).encode()
        evidence = {
            "scenarioId": "CTX-07", "synthetic": True, "liveExecutionObserved": False,
            "runId": "run", "hostRunId": "host-run", "hostThreadId": "thread", "taskId": "task",
            "hostIdentity": "synthetic-host", "hostVersion": "1", "hostRunEvidenceSource": "synthetic-fixture",
            "carrierId": "agents-project-rules", "carrierPath": str(CARRIER.resolve()),
            "carrierSha256": packet["publicPacket"]["carrier"]["sha256"], "filesystemPresence": True,
            "discoveryState": "observed", "discoveryEvidenceSource": "synthetic-fixture",
            "loadingState": "observed", "loadingEvidenceSource": "synthetic-fixture",
            "loaderEvent": {"carrierId": "agents-project-rules", "carrierSha256": packet["publicPacket"]["carrier"]["sha256"], "taskId": "task", "evidenceSource": "synthetic-fixture"},
            "effectiveInstructionSurface": {"precedence": "synthetic", "evidenceSource": "synthetic-fixture"},
            "rawResponseSha256": __import__("hashlib").sha256(raw).hexdigest(), "oraclePrivate": packet["privateOracle"], "oracleSha256": packet["oracleSha256"],
            "hostApprovalState": "absent", "hostApprovalEvidenceSource": "synthetic-fixture", "hostApprovalCreditedToCarrier": False,
            "hardStandardOutcome": "pass", "hardStandardEvidenceSource": "synthetic-fixture", "hardStandardCreditedToCarrier": False,
            "repositoryTruthBefore": {"head": "x"}, "repositoryTruthAfter": {"head": "x"},
            "requestedModel": "gpt-5.3-codex-spark", "requestedReasoningEffort": "low", "actualModel": "gpt-5.3-codex-spark", "actualReasoningEffort": "low", "actualModelEvidenceSource": "synthetic-fixture", "actualReasoningEvidenceSource": "synthetic-fixture", "universalAdherenceClaimed": False,
        }
        self.assertEqual("evidence-contract-ready-not-live-host-proved", evaluate_observation(raw, evidence)["status"])

    def test_missing_carrier_id_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            build_trial_packet(carrier_path=CARRIER, carrier_identity="", host_identity="host", host_version="1", requested_model="model", requested_reasoning_effort="low", loader_evidence_capture="available")

    def test_recomputed_collapsed_public_packet_is_rejected(self) -> None:
        packet = self._packet()
        packet["publicPacket"]["privateOracle"] = copy.deepcopy(packet["privateOracle"])
        packet["packetSha256"] = canonical_sha256(packet["publicPacket"])
        self.assertIn("fail-public-packet-shape", validate_packet_binding(packet))

    def test_fake_actual_fields_are_rejected_even_with_recomputed_digest(self) -> None:
        packet = self._packet()
        packet["publicPacket"]["targetHost"]["actualModel"] = "forged"
        packet["packetSha256"] = canonical_sha256(packet["publicPacket"])
        self.assertEqual(["hard-fail-unobserved-actual-condition-field"], validate_packet_binding(packet))


if __name__ == "__main__":
    unittest.main()
