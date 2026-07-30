import copy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from scripts.build_process_fidelity_chained_transform_trial_packet import (
    build_packet,
    validate_packet,
)
from scripts.validate_process_fidelity_chained_transform_packet_preflight import (
    EVIDENCE_PATH,
    validate_evidence,
)


ROOT = Path(__file__).resolve().parent.parent


class ProcessFidelityChainedTransformPacketPreflightTests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.evidence = json.loads(
            (ROOT / EVIDENCE_PATH).read_text(encoding="utf-8")
        )

    def test_current_evidence_is_valid(self) -> None:
        validate_evidence(self.evidence, root=ROOT)

    def test_packet_has_one_materialized_agent_stage(self) -> None:
        with TemporaryDirectory() as temporary:
            packet = Path(temporary) / "packet"
            build_packet(packet, root=ROOT)
            report = validate_packet(packet, root=ROOT)
            self.assertEqual(2, report["agentVisibleFileCount"])
            self.assertFalse(report["deferredAgentStagesMaterialized"])
            self.assertFalse(
                packet.joinpath("AGENT-RUNTIME", "hop-2-routing").exists()
            )

    def test_extra_agent_visible_file_fails_closed(self) -> None:
        with TemporaryDirectory() as temporary:
            packet = Path(temporary) / "packet"
            build_packet(packet, root=ROOT)
            extra = (
                packet
                / "AGENT-RUNTIME"
                / "hop-1-decomposition"
                / "PRIVATE.json"
            )
            extra.write_text("{}\n", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "runtime root"):
                validate_packet(packet, root=ROOT)

    def test_private_scoring_field_leak_fails_closed(self) -> None:
        with TemporaryDirectory() as temporary:
            packet = Path(temporary) / "packet"
            build_packet(packet, root=ROOT)
            stage_path = (
                packet
                / "AGENT-RUNTIME"
                / "hop-1-decomposition"
                / "STAGE-CONTRACT.json"
            )
            stage = json.loads(stage_path.read_text(encoding="utf-8"))
            stage["thresholds"] = {"authorityDriftCountMax": 0}
            stage_path.write_text(
                json.dumps(stage, indent=2) + "\n",
                encoding="utf-8",
            )
            manifest_path = packet / "MANIFEST.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            target = next(
                item
                for item in manifest["files"]
                if item["path"].endswith("STAGE-CONTRACT.json")
            )
            import hashlib

            target["sha256"] = hashlib.sha256(stage_path.read_bytes()).hexdigest()
            manifest_path.write_text(
                json.dumps(manifest, indent=2) + "\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(RuntimeError, "private scoring"):
                validate_packet(packet, root=ROOT)

    def test_route_observation_cannot_be_claimed_by_preflight(self) -> None:
        mutated = copy.deepcopy(self.evidence)
        mutated["preflightResult"]["actualRouteObserved"] = True
        with self.assertRaisesRegex(RuntimeError, "result drifted"):
            validate_evidence(mutated, root=ROOT)

    def test_live_dispatch_cannot_become_ready(self) -> None:
        mutated = copy.deepcopy(self.evidence)
        mutated["decision"]["liveDispatchReady"] = True
        with self.assertRaisesRegex(RuntimeError, "decision boundary"):
            validate_evidence(mutated, root=ROOT)

    def test_later_stage_isolation_is_not_claimed(self) -> None:
        mutated = copy.deepcopy(self.evidence)
        mutated["exposureBoundary"]["laterStageIsolationProved"] = True
        with self.assertRaisesRegex(RuntimeError, "exposure boundary"):
            validate_evidence(mutated, root=ROOT)

    def test_binding_hash_drift_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.evidence)
        mutated["bindings"]["traceSchema"]["fileSha256"] = "0" * 64
        with self.assertRaisesRegex(RuntimeError, "binding hash drifted"):
            validate_evidence(mutated, root=ROOT)

    def test_claim_promotion_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.evidence)
        mutated["claimBoundary"]["liveAgentBehaviorProved"] = True
        with self.assertRaisesRegex(RuntimeError, "claim boundary"):
            validate_evidence(mutated, root=ROOT)


if __name__ == "__main__":
    unittest.main()
