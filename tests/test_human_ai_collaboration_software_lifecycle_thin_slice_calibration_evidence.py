from __future__ import annotations

import json
import unittest
from copy import deepcopy
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent

from scripts.validate_human_ai_collaboration_software_lifecycle_thin_slice_calibration_evidence import (
    EVIDENCE_PATH,
    REPLAY_INPUT_PATH,
    _is_instruction_carrier_receipt_only_drift,
    _replays_exactly_with_instruction_carrier,
    validate_evidence,
)


class SoftwareLifecycleThinSliceCalibrationEvidenceTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls) -> None:
        cls.document = json.loads(
            (ROOT / EVIDENCE_PATH).read_text(encoding="utf-8")
        )

    def test_evidence_passes(self) -> None:
        validate_evidence(deepcopy(self.document), root=ROOT)

    def test_instruction_carrier_receipt_exception_is_fail_closed(self) -> None:
        capture_binding = self.document["bindings"]["capture"]
        capture_root = ROOT / capture_binding["captureRoot"]
        capture = json.loads(
            (ROOT / capture_binding["path"]).read_text(encoding="utf-8")
        )
        replay_input = json.loads(
            (ROOT / REPLAY_INPUT_PATH).read_text(encoding="utf-8")
        )
        instruction_carrier_path = (
            ROOT / replay_input["instructionCarrier"]["path"]
        )
        allowed_result = {
            "failureCodes": [
                "domain-suboracle-pack-drift",
                (
                    "stage-domain-suboracle-binding-drift:"
                    "observation-incident-handling"
                ),
                (
                    "stage-domain-suboracle-binding-drift:"
                    "maintenance-evolution"
                ),
            ]
        }
        self.assertTrue(
            _is_instruction_carrier_receipt_only_drift(
                result=allowed_result,
                capture=capture,
                capture_root=capture_root,
                root=ROOT,
                instruction_carrier_path=instruction_carrier_path,
            )
        )
        broader_result = deepcopy(allowed_result)
        broader_result["failureCodes"].append("protocol-binding-drift")
        self.assertFalse(
            _is_instruction_carrier_receipt_only_drift(
                result=broader_result,
                capture=capture,
                capture_root=capture_root,
                root=ROOT,
                instruction_carrier_path=instruction_carrier_path,
            )
        )

        pack_row = next(
            item
            for item in capture["rawArtifactIndex"]
            if item["artifactId"] == capture["domainSuboraclePackArtifactId"]
        )
        historical_pack = json.loads(
            (capture_root / pack_row["path"]).read_text(encoding="utf-8")
        )
        tampered_pack = deepcopy(historical_pack)
        tampered_pack["results"]["incident"][
            "disposableFixtureExecution"
        ]["stageReceipts"][0]["treeCanonicalSha256"] = "0" * 64
        self.assertFalse(
            _replays_exactly_with_instruction_carrier(
                tampered_pack,
                instruction_carrier_path=instruction_carrier_path,
                root=ROOT,
            )
        )

    def test_missing_claim_key_fails_closed(self) -> None:
        document = deepcopy(self.document)
        document["claimBoundary"].pop("provesProductionReadiness")
        with self.assertRaisesRegex(RuntimeError, "claim boundary"):
            validate_evidence(document, root=ROOT)

    def test_capture_hash_drift_fails_closed(self) -> None:
        document = deepcopy(self.document)
        document["bindings"]["capture"]["fileSha256"] = "0" * 64
        with self.assertRaisesRegex(RuntimeError, "binding hash"):
            validate_evidence(document, root=ROOT)

    def test_live_agent_or_candidate_decision_promotion_fails_closed(
        self,
    ) -> None:
        document = deepcopy(self.document)
        document["decision"]["weakAgentRunStarted"] = True
        document["decision"]["candidateSkillComparisonJustified"] = True
        with self.assertRaisesRegex(RuntimeError, "decision"):
            validate_evidence(document, root=ROOT)


if __name__ == "__main__":
    unittest.main()
