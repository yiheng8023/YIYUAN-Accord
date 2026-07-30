from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from scripts.validate_human_ai_collaboration_weak_agent_live_comparison_batch_03 import (
    EVIDENCE_PATH,
    PROTOCOL_PATH,
    validate_live_comparison_batch_03,
)


ROOT = Path(__file__).resolve().parent.parent


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class WeakAgentLiveComparisonBatch03Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.evidence = load(EVIDENCE_PATH)
        self.protocol = load(PROTOCOL_PATH)

    def validate(self, evidence: dict | None = None) -> None:
        validate_live_comparison_batch_03(
            evidence or self.evidence,
            root=ROOT,
            protocol=self.protocol,
        )

    def test_current_evidence_is_valid(self) -> None:
        self.validate()

    def test_rejects_invalid_guard_run_promotion(self) -> None:
        evidence = copy.deepcopy(self.evidence)
        evidence["invalidatedGuardRuns"][0]["countsInAggregate"] = True
        with self.assertRaisesRegex(RuntimeError, "invalid guard-run"):
            self.validate(evidence)

    def test_rejects_preference_promotion(self) -> None:
        evidence = copy.deepcopy(self.evidence)
        evidence["aggregateResult"][
            "associationSupportsPreferenceDecision"
        ] = True
        with self.assertRaisesRegex(RuntimeError, "overclaimed"):
            self.validate(evidence)

    def test_rejects_matt_hypothesis_failure_erasure(self) -> None:
        evidence = copy.deepcopy(self.evidence)
        run = next(item for item in evidence["runs"] if item["id"] == "matt:r1")
        run["hypothesisCountRecorded"] = 3
        with self.assertRaisesRegex(RuntimeError, "observed outcome"):
            self.validate(evidence)

    def test_rejects_superpowers_schema_failure_erasure(self) -> None:
        evidence = copy.deepcopy(self.evidence)
        run = next(
            item for item in evidence["runs"] if item["id"] == "superpowers:r1"
        )
        run["exactSymptomBoolean"] = True
        with self.assertRaisesRegex(RuntimeError, "observed outcome"):
            self.validate(evidence)

    def test_rejects_superpowers_red_green_promotion(self) -> None:
        evidence = copy.deepcopy(self.evidence)
        run = next(
            item for item in evidence["runs"] if item["id"] == "superpowers:r3"
        )
        run["redBeforeGreenObserved"] = True
        with self.assertRaisesRegex(RuntimeError, "observed outcome"):
            self.validate(evidence)

    def test_rejects_full_suite_conflation(self) -> None:
        evidence = copy.deepcopy(self.evidence)
        evidence["treatmentFidelityBoundary"][
            "provesFullSuperpowersSuiteBehavior"
        ] = True
        with self.assertRaisesRegex(RuntimeError, "treatment-fidelity"):
            self.validate(evidence)


if __name__ == "__main__":
    unittest.main()
