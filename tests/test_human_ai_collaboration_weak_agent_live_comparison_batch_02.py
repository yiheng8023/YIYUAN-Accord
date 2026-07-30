from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from scripts.validate_human_ai_collaboration_weak_agent_live_comparison_batch_02 import (
    EVIDENCE_PATH,
    PROTOCOL_PATH,
    validate_live_comparison_batch_02,
)


ROOT = Path(__file__).resolve().parent.parent


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class WeakAgentLiveComparisonBatch02Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.evidence = load(EVIDENCE_PATH)
        self.protocol = load(PROTOCOL_PATH)

    def validate(self, evidence: dict | None = None) -> None:
        validate_live_comparison_batch_02(
            evidence or self.evidence,
            root=ROOT,
            protocol=self.protocol,
        )

    def test_current_evidence_is_valid(self) -> None:
        self.validate()

    def test_rejects_native_boundary_failure_erasure(self) -> None:
        evidence = copy.deepcopy(self.evidence)
        native = next(
            item
            for item in evidence["runs"]
            if item["armId"] == "SE-OPS-NATIVE-SPARK"
        )
        native["strictProcessOutcome"] = "pass"
        with self.assertRaisesRegex(RuntimeError, "native boundary"):
            self.validate(evidence)

    def test_rejects_preference_promotion(self) -> None:
        evidence = copy.deepcopy(self.evidence)
        evidence["aggregateResult"][
            "associationSupportsPreferenceDecision"
        ] = True
        with self.assertRaisesRegex(RuntimeError, "overclaimed"):
            self.validate(evidence)

    def test_rejects_raw_report_rewrite_claim(self) -> None:
        evidence = copy.deepcopy(self.evidence)
        native = next(
            item
            for item in evidence["runs"]
            if item["armId"] == "SE-OPS-NATIVE-SPARK"
        )
        native["postHocClassifierBoundary"]["rawReportMutated"] = True
        with self.assertRaisesRegex(RuntimeError, "post-hoc"):
            self.validate(evidence)

    def test_rejects_current_matt_conflation(self) -> None:
        evidence = copy.deepcopy(self.evidence)
        evidence["candidate"]["equalsCurrentMattMain"] = True
        with self.assertRaisesRegex(RuntimeError, "candidate claim"):
            self.validate(evidence)

    def test_rejects_strict_process_count_promotion(self) -> None:
        evidence = copy.deepcopy(self.evidence)
        evidence["aggregateResult"]["strictProcessPassCount"]["native"] = 3
        with self.assertRaisesRegex(RuntimeError, "aggregate counts"):
            self.validate(evidence)

    def test_rejects_loader_causation_promotion(self) -> None:
        evidence = copy.deepcopy(self.evidence)
        evidence["aggregateResult"]["candidateEffectOrCausationProved"] = True
        with self.assertRaisesRegex(RuntimeError, "overclaimed"):
            self.validate(evidence)


if __name__ == "__main__":
    unittest.main()
