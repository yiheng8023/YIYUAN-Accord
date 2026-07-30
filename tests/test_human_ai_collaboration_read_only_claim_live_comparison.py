from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from scripts.validate_human_ai_collaboration_read_only_claim_live_comparison import (
    EVIDENCE_PATH,
    validate_live_comparison,
)


ROOT = Path(__file__).resolve().parent.parent


class HumanAiCollaborationReadOnlyClaimLiveComparisonTests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.document = json.loads(
            (ROOT / EVIDENCE_PATH).read_text(encoding="utf-8")
        )

    def test_current_live_evidence_is_valid(self) -> None:
        validate_live_comparison(self.document, root=ROOT)

    def test_rejects_oracle_pass_promotion(self) -> None:
        document = copy.deepcopy(self.document)
        document["aggregateObservation"]["hardOraclePassCount"] = 3
        with self.assertRaisesRegex(RuntimeError, "aggregate decision"):
            validate_live_comparison(document, root=ROOT)

    def test_rejects_general_weak_model_claim(self) -> None:
        document = copy.deepcopy(self.document)
        document["claimBoundary"]["provesGeneralWeakModelFailure"] = True
        with self.assertRaisesRegex(RuntimeError, "overpromoted"):
            validate_live_comparison(document, root=ROOT)

    def test_rejects_changed_c3_observation(self) -> None:
        document = copy.deepcopy(self.document)
        c3 = next(
            claim
            for claim in document["runs"][0]["submission"]["claims"]
            if claim["id"] == "C3"
        )
        c3["state"] = "unknown"
        with self.assertRaisesRegex(RuntimeError, "observed failure changed"):
            validate_live_comparison(document, root=ROOT)

    def test_rejects_tool_observation(self) -> None:
        document = copy.deepcopy(self.document)
        document["runs"][0]["hostBoundary"][
            "commandExecutionObserved"
        ] = True
        with self.assertRaisesRegex(RuntimeError, "host observation drifted"):
            validate_live_comparison(document, root=ROOT)


if __name__ == "__main__":
    unittest.main()
