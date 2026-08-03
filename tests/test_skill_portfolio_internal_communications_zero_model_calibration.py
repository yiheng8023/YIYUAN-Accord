from __future__ import annotations

import copy
import json
import unittest

from scripts.evaluate_skill_portfolio_internal_communications_zero_model_calibration import (
    FIXTURE_PATH,
    PROTOCOL_PATH,
    REQUIRED_FAULT_CLASSES,
    ROOT,
    evaluate_calibration,
    evaluate_repository_calibration,
)
from scripts.validate_skill_portfolio_internal_communications_zero_model_protocol import (
    validate_protocol,
)


class InternalCommunicationsZeroModelCalibrationTests(unittest.TestCase):
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

    def test_account_data_gate_cannot_be_promoted(self) -> None:
        protocol = copy.deepcopy(self.protocol)
        protocol["claimBoundary"]["accountOrOrganizationalDataAccessAuthorized"] = True
        with self.assertRaisesRegex(RuntimeError, "Claim boundary drifted"):
            self.evaluate(protocol=protocol)

    def test_candidate_dimension_eligibility_cannot_drift(self) -> None:
        protocol = copy.deepcopy(self.protocol)
        protocol["candidateBoundary"]["candidates"][0]["eligibleDimensionIds"].remove(
            "send-and-publication-authority"
        )
        with self.assertRaisesRegex(
            RuntimeError,
            "Candidate identity, eligibility, or lifecycle boundary drifted",
        ):
            self.evaluate(protocol=protocol)

    def test_parent_reuse_cannot_be_rewritten_as_reexecution(self) -> None:
        protocol = copy.deepcopy(self.protocol)
        protocol["parentReuse"]["parentProtocolOrFixtureReexecutedByThisEvaluator"] = True
        with self.assertRaisesRegex(RuntimeError, "Parent evidence reuse boundary drifted"):
            self.evaluate(protocol=protocol)

    def test_repository_calibration_preserves_carrier_and_send_boundaries(self) -> None:
        report = evaluate_repository_calibration(ROOT)

        self.assertEqual("valid-zero-model-effect-calibration", report["outcome"])
        self.assertEqual(
            "internal-communications-effect-oracle-calibrated-no-candidate-behavior",
            report["status"],
        )
        self.assertEqual("effect.internal-communications", report["effectGroupId"])
        self.assertEqual(1, report["candidateCount"])
        self.assertEqual(1, report["scenarioCount"])
        self.assertEqual(6, report["caseCount"])
        self.assertEqual(5, report["faultCaseCount"])
        self.assertEqual(sorted(REQUIRED_FAULT_CLASSES), report["faultClassesCovered"])
        self.assertTrue(report["accessCommsOracleReused"])
        self.assertFalse(report["fullScenarioFixtureCreated"])
        self.assertEqual(0, report["agentDispatchCount"])
        self.assertEqual(0, report["modelCallCount"])
        self.assertEqual(0, report["candidateExecutionCount"])
        self.assertFalse(report["formalLiveEvidenceEligible"])

        for case in report["cases"]:
            if case["faultClass"] == "control":
                self.assertEqual([], case["activeLossIds"])
                continue
            self.assertEqual(1, len(case["activeLossIds"]))
            self.assertEqual(
                "communication-draft",
                case["cumulativeLoss"]["budgetExceededAtHop"],
            )
            self.assertEqual([], case["cumulativeLoss"]["hops"][-1]["activeLossIds"])

        self.assertTrue(all(value is False for value in report["claimBoundary"].values()))

    def test_protocol_validator_accepts_repository_state(self) -> None:
        report = validate_protocol(ROOT)
        self.assertEqual(
            "internal-communications-effect-oracle-calibrated-no-candidate-behavior",
            report["status"],
        )


if __name__ == "__main__":
    unittest.main()
