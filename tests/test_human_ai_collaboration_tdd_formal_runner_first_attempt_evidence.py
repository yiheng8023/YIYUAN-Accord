from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from scripts.validate_human_ai_collaboration_tdd_formal_runner_first_attempt_evidence import (
    validate_evidence,
)


ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_PATH = (
    ROOT
    / "registry"
    / "human-ai-collaboration-tdd-formal-runner-first-attempt-evidence-2026-07-26.json"
)


class TddFormalRunnerFirstAttemptEvidenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.document = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))

    def test_current_evidence_validates(self) -> None:
        validate_evidence(self.document, root=ROOT)

    def test_invalid_attempt_cannot_be_counted(self) -> None:
        mutated = copy.deepcopy(self.document)
        mutated["classification"]["formalRunCounted"] = True
        with self.assertRaisesRegex(RuntimeError, "classification drifted"):
            validate_evidence(mutated, root=ROOT)

    def test_mutant_survivors_cannot_be_hidden(self) -> None:
        mutated = copy.deepcopy(self.document)
        mutated["parentOutcome"]["survivingMutantIds"] = []
        with self.assertRaisesRegex(RuntimeError, "parent outcome drifted"):
            validate_evidence(mutated, root=ROOT)


if __name__ == "__main__":
    unittest.main()
