import copy
import json
from pathlib import Path
import unittest

from scripts.validate_human_ai_collaboration_high_impact_primary_source_claim_ledger import (
    INTAKE_PATH,
    LEDGER_PATH,
    MATRIX_PATH,
    validate_claim_ledger,
)


ROOT = Path(__file__).resolve().parent.parent


def _load(path: str) -> dict[str, object]:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class HighImpactPrimarySourceClaimLedgerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.ledger = _load(LEDGER_PATH)
        self.matrix = _load(MATRIX_PATH)
        self.intake = _load(INTAKE_PATH)

    def validate(
        self,
        ledger: dict[str, object] | None = None,
        matrix: dict[str, object] | None = None,
        intake: dict[str, object] | None = None,
    ) -> None:
        validate_claim_ledger(
            ledger or self.ledger,
            root=ROOT,
            matrix=matrix or self.matrix,
            intake=intake or self.intake,
        )

    def test_current_ledger_is_valid(self) -> None:
        self.validate()

    def test_live_harness_claim_cannot_be_promoted(self) -> None:
        mutated = copy.deepcopy(self.ledger)
        mutated["claimBoundary"]["liveHarnessOutcomeProved"] = True
        with self.assertRaisesRegex(RuntimeError, "claim boundary"):
            self.validate(ledger=mutated)

    def test_primary_source_url_drift_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.ledger)
        mutated["claims"][0]["source"]["canonicalUrl"] = (
            "https://example.invalid/secondary"
        )
        with self.assertRaisesRegex(RuntimeError, "source identity"):
            self.validate(ledger=mutated)

    def test_missing_method_qualifiers_are_rejected(self) -> None:
        mutated = copy.deepcopy(self.ledger)
        mutated["claims"][2]["methodLimits"] = ["small sample"]
        with self.assertRaisesRegex(RuntimeError, "Method qualifiers"):
            self.validate(ledger=mutated)

    def test_literature_cannot_promote_matrix_evidence_state(self) -> None:
        mutated = copy.deepcopy(self.matrix)
        scenario = next(
            item
            for item in mutated["scenarios"]
            if item["id"] == "SE-VERIFY-SECURE-01"
        )
        scenario["evidenceState"] = "verified-live-domain-evidence"
        with self.assertRaisesRegex(RuntimeError, "promoted scenario"):
            self.validate(matrix=mutated)

    def test_ambiguous_v1_research_measurement_cannot_be_repromoted(self) -> None:
        mutated = copy.deepcopy(self.matrix)
        scenario = next(
            item
            for item in mutated["scenarios"]
            if item["id"] == "GEN-RESEARCH-01"
        )
        scenario["evidenceState"] = (
            "bounded-synthetic-native-live-agent-failure-"
            "no-candidate-or-live-domain-evidence"
        )
        with self.assertRaisesRegex(RuntimeError, "promoted scenario"):
            self.validate(matrix=mutated)

    def test_matrix_claim_binding_drift_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.matrix)
        scenario = next(
            item
            for item in mutated["scenarios"]
            if item["id"] == "SE-MGMT-PRACTICE-01"
        )
        scenario["primarySourceDesignInputIds"] = []
        with self.assertRaisesRegex(RuntimeError, "design inputs drifted"):
            self.validate(matrix=mutated)

    def test_intake_cannot_accept_the_whole_report(self) -> None:
        mutated = copy.deepcopy(self.intake)
        mutated["primarySourceRepair"]["wholeReportAccepted"] = True
        with self.assertRaisesRegex(RuntimeError, "intake repair"):
            self.validate(intake=mutated)


if __name__ == "__main__":
    unittest.main()
