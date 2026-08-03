from __future__ import annotations

import copy
import json
import unittest

from scripts.evaluate_skill_portfolio_decision_challenge_zero_model_calibration import (
    FIXTURE_PATH,
    PROTOCOL_PATH,
    REQUIRED_FAULT_CLASSES,
    ROOT,
    evaluate_calibration,
    evaluate_repository_calibration,
)
from scripts.validate_skill_portfolio_decision_challenge_zero_model_protocol import (
    validate_protocol,
)


class DecisionChallengeZeroModelCalibrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.protocol = json.loads((ROOT / PROTOCOL_PATH).read_text(encoding="utf-8"))
        cls.fixture = json.loads((ROOT / FIXTURE_PATH).read_text(encoding="utf-8"))

    def evaluate(self, *, protocol=None, fixture=None):
        return evaluate_calibration(
            copy.deepcopy(protocol or self.protocol),
            copy.deepcopy(fixture or self.fixture),
            root=ROOT,
        )

    def test_fixture_cannot_claim_a_new_full_scenario(self) -> None:
        fixture = copy.deepcopy(self.fixture)
        fixture["parentScenarioBinding"]["fullScenarioDuplicated"] = True

        with self.assertRaisesRegex(RuntimeError, "Fixture parent reuse boundary drifted"):
            self.evaluate(fixture=fixture)

    def test_composition_arm_cannot_be_enabled_by_protocol_drift(self) -> None:
        protocol = copy.deepcopy(self.protocol)
        protocol["comparisonBoundary"]["compositionArmEligible"] = True

        with self.assertRaisesRegex(RuntimeError, "Comparison boundary drifted"):
            self.evaluate(protocol=protocol)

    def test_acceptance_contract_cannot_drop_review_carry(self) -> None:
        protocol = copy.deepcopy(self.protocol)
        protocol["acceptance"]["allFaultsMustCarryAtReviewDetection"] = False

        with self.assertRaisesRegex(RuntimeError, "Acceptance boundary drifted"):
            self.evaluate(protocol=protocol)

    def test_repository_protocol_is_bounded_and_valid(self) -> None:
        report = validate_protocol(ROOT)

        self.assertEqual(
            "decision-challenge-effect-oracle-calibrated-no-candidate-behavior",
            report["status"],
        )
        self.assertTrue(report["allCasesPassed"])

    def test_repository_calibration_covers_only_incremental_effect_faults(self) -> None:
        report = evaluate_repository_calibration(ROOT)

        self.assertEqual("valid-zero-model-effect-calibration", report["outcome"])
        self.assertEqual(7, report["caseCount"])
        self.assertEqual(6, report["faultCaseCount"])
        self.assertEqual(
            sorted(REQUIRED_FAULT_CLASSES),
            report["faultClassesCovered"],
        )
        self.assertTrue(report["allCasesPassed"])
        self.assertTrue(report["parentOrgDecisionProtocolReused"])
        self.assertFalse(report["newFullScenarioFixtureCreated"])
        self.assertEqual(0, report["agentDispatchCount"])
        self.assertEqual(0, report["modelCallCount"])
        self.assertEqual(0, report["candidateExecutionCount"])
        self.assertFalse(report["formalLiveEvidenceEligible"])

        for case in report["cases"]:
            if case["faultClass"] == "control":
                self.assertEqual([], case["activeLossIds"])
                self.assertIsNone(case["cumulativeLoss"]["budgetExceededAtHop"])
                continue
            self.assertEqual(1, len(case["activeLossIds"]))
            self.assertEqual(
                "challenge-draft",
                case["cumulativeLoss"]["budgetExceededAtHop"],
            )
            self.assertEqual([], case["cumulativeLoss"]["hops"][-1]["activeLossIds"])
            self.assertTrue(
                case["cumulativeLoss"][
                    "terminalRecoveryDoesNotEraseHistoricalUniqueLoss"
                ]
            )

        self.assertTrue(all(value is False for value in report["claimBoundary"].values()))

    def test_fault_label_cannot_hide_a_different_mutation(self) -> None:
        fixture = copy.deepcopy(self.fixture)
        case = next(
            item for item in fixture["cases"] if item["faultClass"] == "steelman-omission"
        )
        case["overrides"] = {"failureAssumptionIds": []}

        with self.assertRaisesRegex(RuntimeError, "Fault mutation shape drifted"):
            self.evaluate(fixture=fixture)

    def test_candidate_lifecycle_cannot_be_promoted(self) -> None:
        protocol = copy.deepcopy(self.protocol)
        protocol["candidateBoundary"]["installed"] = True

        with self.assertRaisesRegex(
            RuntimeError,
            "Candidate identity or lifecycle boundary drifted",
        ):
            self.evaluate(protocol=protocol)

    def test_claim_boundary_cannot_be_promoted(self) -> None:
        protocol = copy.deepcopy(self.protocol)
        protocol["claimBoundary"]["candidateBehaviorProved"] = True

        with self.assertRaisesRegex(RuntimeError, "Claim boundary drifted"):
            self.evaluate(protocol=protocol)


if __name__ == "__main__":
    unittest.main()
