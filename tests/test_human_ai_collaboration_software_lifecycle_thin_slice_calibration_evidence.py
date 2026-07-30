from __future__ import annotations

import json
import unittest
from copy import deepcopy
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent

from scripts.validate_human_ai_collaboration_software_lifecycle_thin_slice_calibration_evidence import (
    EVIDENCE_PATH,
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
