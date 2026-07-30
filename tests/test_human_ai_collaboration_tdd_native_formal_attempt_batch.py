from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from scripts.validate_human_ai_collaboration_tdd_native_formal_attempt_batch import (
    EVIDENCE_PATH,
    validate_evidence,
)


ROOT = Path(__file__).resolve().parent.parent


class HumanAiCollaborationTddNativeFormalAttemptBatchTests(
    unittest.TestCase
):
    def test_current_batch_is_valid(self) -> None:
        document = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))
        validate_evidence(document, root=ROOT)

    def test_false_valid_baseline_is_rejected(self) -> None:
        document = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))
        mutated = copy.deepcopy(document)
        mutated["attemptPolicy"]["valid"] = 1
        mutated["decision"]["nativeValidComparisonBaselineAvailable"] = True
        with self.assertRaises(RuntimeError):
            validate_evidence(mutated, root=ROOT)


if __name__ == "__main__":
    unittest.main()
