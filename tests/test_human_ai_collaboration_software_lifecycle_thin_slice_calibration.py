from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent

from scripts.evaluate_human_ai_collaboration_software_lifecycle_thin_slice_calibration import (
    evaluate_capture,
)
from scripts.run_human_ai_collaboration_software_lifecycle_thin_slice_calibration import (
    canonical_sha256,
    build_calibration_capture,
    self_hash,
)


def _raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class SoftwareLifecycleThinSliceCalibrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(
            prefix="aah-software-lifecycle-thin-slice-"
        )
        self.capture_root = Path(self.temporary.name)
        self.capture = build_calibration_capture(self.capture_root)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _row(self, artifact_id: str) -> dict:
        return next(
            item
            for item in self.capture["rawArtifactIndex"]
            if item["artifactId"] == artifact_id
        )

    def _load(self, artifact_id: str) -> dict:
        row = self._row(artifact_id)
        return json.loads(
            (self.capture_root / row["path"]).read_text(encoding="utf-8")
        )

    def _save(self, artifact_id: str, value: dict) -> None:
        row = self._row(artifact_id)
        path = self.capture_root / row["path"]
        path.write_text(
            json.dumps(value, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        row["bytes"] = len(path.read_bytes())
        row["rawSha256"] = _raw_sha256(path)
        row["canonicalSha256"] = canonical_sha256(value)

    def test_valid_zero_model_chain_is_calibration_only(self) -> None:
        result = evaluate_capture(
            deepcopy(self.capture),
            capture_root=self.capture_root,
            root=ROOT,
        )
        self.assertEqual("valid-calibration-only", result["status"])
        self.assertEqual([], result["failureCodes"])
        self.assertEqual(7, result["stageCount"])
        self.assertEqual(8, result["gateCount"])
        self.assertEqual(8, result["ledgerCount"])
        self.assertEqual(0, result["agentDispatchCount"])
        self.assertEqual(0, result["modelCallCount"])
        self.assertFalse(result["formalLiveEvidenceEligible"])
        self.assertTrue(
            all(value is False for value in result["claimBoundary"].values())
        )

    def test_raw_artifact_tamper_fails_before_semantic_credit(self) -> None:
        row = self.capture["rawArtifactIndex"][0]
        path = self.capture_root / row["path"]
        path.write_text("{}\n", encoding="utf-8")
        result = evaluate_capture(
            deepcopy(self.capture),
            capture_root=self.capture_root,
            root=ROOT,
        )
        self.assertEqual("invalid", result["status"])
        self.assertIn(
            "raw-artifact-byte-binding-mismatch",
            result["failureCodes"],
        )

    def test_rehashed_domain_suboracle_claim_drift_fails_closed(
        self,
    ) -> None:
        artifact_id = self.capture[
            "domainSuboraclePackArtifactId"
        ]
        pack = self._load(artifact_id)
        pack["positiveAcceptance"]["tdd"] = False
        pack["allPositiveAccepted"] = False
        self._save(artifact_id, pack)
        result = evaluate_capture(
            deepcopy(self.capture),
            capture_root=self.capture_root,
            root=ROOT,
        )
        self.assertEqual("invalid", result["status"])
        self.assertIn(
            "domain-suboracle-pack-drift",
            result["failureCodes"],
        )

    def test_missing_gate_receipt_fails_closed(self) -> None:
        self.capture["authorityReceiptIds"].pop()
        result = evaluate_capture(
            deepcopy(self.capture),
            capture_root=self.capture_root,
            root=ROOT,
        )
        self.assertEqual("invalid", result["status"])
        self.assertIn("capture-lifecycle-set-drift", result["failureCodes"])

    def test_same_identity_review_contract_drift_is_rejected(self) -> None:
        envelope_id = self.capture["stageEnvelopeIds"][3]
        envelope = self._load(envelope_id)
        envelope["role"] = "implementation-tdd-agent"
        envelope["envelopeSha256"] = self_hash(
            envelope,
            "envelopeSha256",
        )
        self._save(envelope_id, envelope)
        result = evaluate_capture(
            deepcopy(self.capture),
            capture_root=self.capture_root,
            root=ROOT,
        )
        self.assertEqual("invalid", result["status"])
        self.assertIn("stage-envelope-contract-drift", result["failureCodes"])

    def test_out_of_allowlist_change_is_rejected(self) -> None:
        envelope_id = self.capture["stageEnvelopeIds"][2]
        envelope = self._load(envelope_id)
        envelope["changedFiles"] = ["outside.txt"]
        envelope["envelopeSha256"] = self_hash(
            envelope,
            "envelopeSha256",
        )
        self._save(envelope_id, envelope)
        result = evaluate_capture(
            deepcopy(self.capture),
            capture_root=self.capture_root,
            root=ROOT,
        )
        self.assertEqual("invalid", result["status"])
        self.assertIn(
            "stage-changed-file-outside-allowlist",
            result["failureCodes"],
        )

    def test_unknown_telemetry_coercion_semantic_falsifier_is_rejected(
        self,
    ) -> None:
        envelope_id = self.capture["stageEnvelopeIds"][6]
        envelope = self._load(envelope_id)
        output_id = envelope["outputBindings"][0]["artifactId"]
        output = self._load(output_id)
        output["semanticAssertions"]["unknownTelemetryCoercedToZero"] = True
        self._save(output_id, output)
        output_row = self._row(output_id)
        descriptor = envelope["outputBindings"][0]
        descriptor["byteLength"] = output_row["bytes"]
        descriptor["byteSha256"] = output_row["rawSha256"]
        descriptor["canonicalJsonSha256"] = output_row["canonicalSha256"]
        envelope["outputSetCanonicalSha256"] = canonical_sha256(
            envelope["outputBindings"]
        )
        envelope["envelopeSha256"] = self_hash(
            envelope,
            "envelopeSha256",
        )
        self._save(envelope_id, envelope)
        result = evaluate_capture(
            deepcopy(self.capture),
            capture_root=self.capture_root,
            root=ROOT,
        )
        self.assertEqual("invalid", result["status"])
        self.assertIn(
            "stage-semantic-falsifier:maintenance-evolution",
            result["failureCodes"],
        )

    def test_agent_output_cannot_be_relabelled_as_truth_source(self) -> None:
        ledger_id = self.capture["acceptedInvariantLedgerIds"][-1]
        ledger = self._load(ledger_id)
        output_id = self.capture["stageEnvelopeIds"][-1]
        output_envelope = self._load(output_id)
        proposal_digest = output_envelope["outputBindings"][0][
            "canonicalJsonSha256"
        ]
        ledger["activeInvariants"][-1]["currentAcceptanceBasis"] = {
            "kind": "source",
            "bindingSha256": proposal_digest,
        }
        ledger["ledgerSha256"] = self_hash(ledger, "ledgerSha256")
        self._save(ledger_id, ledger)
        result = evaluate_capture(
            deepcopy(self.capture),
            capture_root=self.capture_root,
            root=ROOT,
        )
        self.assertEqual("invalid", result["status"])
        self.assertIn(
            "unregistered-source-promoted-truth",
            result["failureCodes"],
        )

    def test_receipt_replay_as_second_truth_change_is_rejected(self) -> None:
        ledger_id = self.capture["acceptedInvariantLedgerIds"][-1]
        ledger = self._load(ledger_id)
        receipt = self._load(self.capture["authorityReceiptIds"][1])
        replay = deepcopy(ledger["transitionHistory"][-1])
        replay["transitionId"] = "replayed-authority-change"
        replay["changes"][0]["changeId"] = "replayed-authority-change"
        replay["changes"][0]["basis"]["bindingSha256"] = receipt[
            "receiptSha256"
        ]
        replay["transitionCanonicalSha256"] = self_hash(
            replay,
            "transitionCanonicalSha256",
        )
        ledger["transitionHistory"].append(replay)
        ledger["summary"]["acceptedChangeCount"] += 1
        ledger["summary"]["humanReceiptBackedChangeCount"] += 1
        ledger["ledgerSha256"] = self_hash(ledger, "ledgerSha256")
        self._save(ledger_id, ledger)
        result = evaluate_capture(
            deepcopy(self.capture),
            capture_root=self.capture_root,
            root=ROOT,
        )
        self.assertEqual("invalid", result["status"])
        self.assertIn(
            "human-authority-receipt-replayed",
            result["failureCodes"],
        )

    def test_zero_model_capture_cannot_claim_route_or_dispatch(self) -> None:
        self.capture["execution"]["agentDispatchCount"] = 1
        self.capture["execution"]["actualRouteObserved"] = True
        result = evaluate_capture(
            deepcopy(self.capture),
            capture_root=self.capture_root,
            root=ROOT,
        )
        self.assertEqual("invalid", result["status"])
        self.assertIn(
            "zero-model-execution-boundary-drift",
            result["failureCodes"],
        )


if __name__ == "__main__":
    unittest.main()
