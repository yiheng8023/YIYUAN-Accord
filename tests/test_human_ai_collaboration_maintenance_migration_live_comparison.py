from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from scripts.validate_human_ai_collaboration_maintenance_migration_live_comparison import (
    EVIDENCE_PATH,
    validate_live_comparison,
)


ROOT = Path(__file__).resolve().parent.parent


class MaintenanceMigrationLiveComparisonTests(unittest.TestCase):
    def setUp(self) -> None:
        self.document = json.loads((ROOT / EVIDENCE_PATH).read_text(encoding="utf-8"))

    def validate(self, document: dict | None = None) -> None:
        validate_live_comparison(document or self.document, root=ROOT)

    def test_current_evidence_is_valid(self) -> None:
        self.validate()

    def test_rejects_candidate_hidden_pass_promotion(self) -> None:
        document = copy.deepcopy(self.document)
        run = next(item for item in document["validRuns"] if item["id"] == "candidate:r1")
        run["hiddenTestsPassed"] = True
        with self.assertRaisesRegex(RuntimeError, "Hidden-contract"):
            self.validate(document)

    def test_rejects_loader_causation_promotion(self) -> None:
        document = copy.deepcopy(self.document)
        document["treatmentFidelityBoundary"]["independentLoaderEventProved"] = True
        with self.assertRaisesRegex(RuntimeError, "Treatment-fidelity"):
            self.validate(document)

    def test_rejects_invalid_measurement_counting(self) -> None:
        document = copy.deepcopy(self.document)
        document["invalidatedMeasurementRuns"][0]["countsInAggregate"] = True
        with self.assertRaisesRegex(RuntimeError, "Invalid measurement"):
            self.validate(document)

    def test_rejects_portfolio_action(self) -> None:
        document = copy.deepcopy(self.document)
        document["decision"]["candidateInstallUpdateOrRemovalJustified"] = True
        with self.assertRaisesRegex(RuntimeError, "decision drifted"):
            self.validate(document)


if __name__ == "__main__":
    unittest.main()
