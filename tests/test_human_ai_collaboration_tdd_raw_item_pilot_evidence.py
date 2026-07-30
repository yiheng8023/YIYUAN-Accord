from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from scripts.validate_human_ai_collaboration_tdd_raw_item_pilot_evidence import (
    validate_evidence,
)


ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_PATH = (
    ROOT
    / "registry"
    / "human-ai-collaboration-tdd-raw-item-pilot-evidence-2026-07-26.json"
)


class HumanAiCollaborationTddRawItemPilotEvidenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.document = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))

    def test_current_evidence_validates(self) -> None:
        validate_evidence(self.document, root=ROOT)

    def test_agent_outcome_cannot_be_promoted(self) -> None:
        mutated = copy.deepcopy(self.document)
        mutated["decision"]["agentTddProcessPassed"] = True
        with self.assertRaisesRegex(
            RuntimeError,
            "decision boundary drifted",
        ):
            validate_evidence(mutated, root=ROOT)

    def test_fail_closed_case_cannot_be_erased(self) -> None:
        mutated = copy.deepcopy(self.document)
        mutated["runs"][1]["normalizationFailureCodes"] = []
        with self.assertRaisesRegex(
            RuntimeError,
            "fail-closed case drifted",
        ):
            validate_evidence(mutated, root=ROOT)


if __name__ == "__main__":
    unittest.main()
