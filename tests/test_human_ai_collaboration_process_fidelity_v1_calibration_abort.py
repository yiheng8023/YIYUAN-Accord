from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from scripts.validate_human_ai_collaboration_process_fidelity_v1_calibration_abort import (
    EVIDENCE_PATH,
    ROOT,
    validate_evidence,
)


class ProcessFidelityV1CalibrationAbortTests(unittest.TestCase):
    def setUp(self) -> None:
        self.evidence = json.loads(
            (ROOT / EVIDENCE_PATH).read_text(encoding="utf-8")
        )

    def test_current_evidence_is_valid(self) -> None:
        validate_evidence(self.evidence)

    def test_agent_failure_promotion_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.evidence)
        mutated["designValidity"]["countsAsWeakAgentCapabilityFailure"] = True
        with self.assertRaisesRegex(
            RuntimeError,
            "design invalidity was weakened",
        ):
            validate_evidence(mutated)

    def test_remaining_dispatch_claim_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.evidence)
        mutated["authorityBoundary"]["remainingTasksDispatched"] = True
        with self.assertRaisesRegex(RuntimeError, "authority boundary drifted"):
            validate_evidence(mutated)


if __name__ == "__main__":
    unittest.main()
