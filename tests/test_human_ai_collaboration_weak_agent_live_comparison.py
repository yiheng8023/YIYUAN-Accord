from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from scripts.validate_human_ai_collaboration_weak_agent_live_comparison import (
    EVIDENCE_PATH,
    validate_live_comparison,
)


ROOT = Path(__file__).resolve().parent.parent


class HumanAiCollaborationWeakAgentLiveComparisonTests(unittest.TestCase):
    def setUp(self) -> None:
        self.document = json.loads(
            (ROOT / EVIDENCE_PATH).read_text(encoding="utf-8")
        )

    def test_current_live_comparison_is_valid(self) -> None:
        validate_live_comparison(self.document, root=ROOT)

    def test_rejects_superiority_promotion(self) -> None:
        document = copy.deepcopy(self.document)
        document["claimBoundary"]["provesMattSuperiority"] = True

        with self.assertRaisesRegex(RuntimeError, "overclaimed"):
            validate_live_comparison(document, root=ROOT)

    def test_rejects_hidden_test_failure(self) -> None:
        document = copy.deepcopy(self.document)
        document["runs"][0]["outcome"]["hiddenTestsPassed"] = False

        with self.assertRaisesRegex(RuntimeError, "run boundary failed"):
            validate_live_comparison(document, root=ROOT)

    def test_rejects_loader_causation_promotion(self) -> None:
        document = copy.deepcopy(self.document)
        document["runs"][1]["exposure"]["loaderInvocationProved"] = True

        with self.assertRaisesRegex(RuntimeError, "exposure boundary drifted"):
            validate_live_comparison(document, root=ROOT)

    def test_rejects_preference_before_repetition(self) -> None:
        document = copy.deepcopy(self.document)
        document["pairedObservation"]["decision"] = "prefer-matt"

        with self.assertRaisesRegex(RuntimeError, "paired decision"):
            validate_live_comparison(document, root=ROOT)


if __name__ == "__main__":
    unittest.main()
