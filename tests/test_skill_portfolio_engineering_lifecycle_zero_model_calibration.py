from __future__ import annotations

import copy
import json
import unittest

from scripts.evaluate_skill_portfolio_engineering_lifecycle_zero_model_calibration import (
    FIXTURE_PATH,
    PROTOCOL_PATH,
    REQUIRED_FAULT_CLASSES,
    ROOT,
    evaluate_calibration,
    evaluate_repository_calibration,
)
from scripts.validate_skill_portfolio_engineering_lifecycle_zero_model_protocol import (
    validate_protocol,
)


class EngineeringLifecycleZeroModelCalibrationTests(unittest.TestCase):
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

    def test_historical_evidence_cannot_be_promoted_to_current_candidate_proof(self) -> None:
        protocol = copy.deepcopy(self.protocol)
        protocol["historicalEvidenceBoundary"][
            "historicalAdaptedPayloadEvidencePromotedToCurrentExactCandidateProof"
        ] = True

        with self.assertRaisesRegex(RuntimeError, "Historical evidence boundary drifted"):
            self.evaluate(protocol=protocol)

    def test_candidate_dimension_eligibility_cannot_drift(self) -> None:
        protocol = copy.deepcopy(self.protocol)
        protocol["candidateBoundary"]["candidates"][0]["eligibleDimensionIds"].append(
            "source-freshness"
        )

        with self.assertRaisesRegex(
            RuntimeError,
            "Candidate identity, eligibility, or lifecycle boundary drifted",
        ):
            self.evaluate(protocol=protocol)

    def test_claim_boundary_cannot_be_promoted(self) -> None:
        protocol = copy.deepcopy(self.protocol)
        protocol["claimBoundary"]["currentCandidateBehaviorProved"] = True

        with self.assertRaisesRegex(RuntimeError, "Claim boundary drifted"):
            self.evaluate(protocol=protocol)

    def test_source_snapshot_repository_identity_is_required(self) -> None:
        protocol = copy.deepcopy(self.protocol)
        binding = next(
            item
            for item in protocol["sourceBindings"]
            if item["path"].endswith("software-engineering-source-snapshot-2026-07-31.json")
        )
        binding["repositorySha256"] = "0" * 64
        with self.assertRaisesRegex(RuntimeError, "repository digest drifted"):
            self.evaluate(protocol=protocol)

    def test_source_snapshot_capture_identity_is_still_required(self) -> None:
        protocol = copy.deepcopy(self.protocol)
        binding = next(
            item
            for item in protocol["sourceBindings"]
            if item["path"].endswith("software-engineering-source-snapshot-2026-07-31.json")
        )
        binding["sha256"] = "0" * 64
        with self.assertRaisesRegex(RuntimeError, "capture digest drifted"):
            self.evaluate(protocol=protocol)

    def test_repository_protocol_is_bounded_and_valid(self) -> None:
        report = validate_protocol(ROOT)

        self.assertEqual(4, report["candidateCount"])
        self.assertTrue(report["allCasesPassed"])

    def test_repository_calibration_is_shared_structure_not_candidate_proof(self) -> None:
        report = evaluate_repository_calibration(ROOT)

        self.assertEqual("valid-zero-model-effect-calibration", report["outcome"])
        self.assertEqual(
            "engineering-lifecycle-effect-oracle-calibrated-no-candidate-behavior",
            report["status"],
        )
        self.assertEqual("effect.engineering-lifecycle", report["effectGroupId"])
        self.assertEqual(4, report["candidateCount"])
        self.assertEqual(7, report["caseCount"])
        self.assertEqual(6, report["faultCaseCount"])
        self.assertEqual(
            sorted(REQUIRED_FAULT_CLASSES),
            report["faultClassesCovered"],
        )
        self.assertTrue(report["sharedStructureOnly"])
        self.assertFalse(report["fullScenarioFixtureCreated"])
        self.assertFalse(report["historicalEvidencePromotedToCurrentCandidateProof"])
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
                "lifecycle-draft",
                case["cumulativeLoss"]["budgetExceededAtHop"],
            )
            self.assertEqual([], case["cumulativeLoss"]["hops"][-1]["activeLossIds"])

        self.assertTrue(all(value is False for value in report["claimBoundary"].values()))


if __name__ == "__main__":
    unittest.main()
