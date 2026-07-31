from __future__ import annotations

import copy
import json
import unittest

from scripts.evaluate_human_ai_collaboration_engineering_management_zero_model_calibration import (
    FIXTURE_PATH,
    PROTOCOL_PATH,
    REQUIRED_FAULT_CLASSES,
    ROOT,
    evaluate_calibration,
    evaluate_repository_calibration,
)
from scripts.validate_human_ai_collaboration_engineering_management_zero_model_protocol import (
    validate_protocol,
)


class EngineeringManagementZeroModelCalibrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.protocol = json.loads(
            (ROOT / PROTOCOL_PATH).read_text(encoding="utf-8")
        )
        cls.fixture = json.loads(
            (ROOT / FIXTURE_PATH).read_text(encoding="utf-8")
        )

    def evaluate(self, *, protocol=None, fixture=None):
        return evaluate_calibration(
            copy.deepcopy(protocol or self.protocol),
            copy.deepcopy(fixture or self.fixture),
            root=ROOT,
        )

    def test_repository_protocol_is_bounded_and_valid(self) -> None:
        validate_protocol()
        report = evaluate_repository_calibration(ROOT)
        self.assertEqual("valid-zero-model-calibration", report["outcome"])
        self.assertEqual(18, report["caseCount"])
        self.assertEqual(17, report["faultCaseCount"])
        self.assertTrue(report["allCasesPassed"])

    def test_all_required_fault_classes_are_detected_exactly(self) -> None:
        report = self.evaluate()
        self.assertEqual(sorted(REQUIRED_FAULT_CLASSES), report["faultClassesCovered"])
        for case in report["cases"]:
            if case["faultClass"] == "control":
                self.assertEqual([], case["activeLossIds"])
            else:
                self.assertTrue(case["activeLossIds"])
                self.assertEqual(
                    "planning-draft",
                    case["cumulativeLoss"]["budgetExceededAtHop"],
                )

    def test_forecast_calibration_is_parent_recomputed(self) -> None:
        report = self.evaluate()
        self.assertEqual(
            {
                "sampleCount": 4,
                "intervalHitCount": 3,
                "absoluteMidpointErrorDoubleSum": 13,
            },
            report["forecastCalibration"],
        )

    def test_forecast_arithmetic_drift_fails_closed(self) -> None:
        fixture = copy.deepcopy(self.fixture)
        fixture["sourceAnchor"]["historicalForecastRecords"][1][
            "observedEffortDays"
        ] = 12
        with self.assertRaisesRegex(RuntimeError, "calibration arithmetic drifted"):
            self.evaluate(fixture=fixture)

    def test_forecast_cannot_become_binding_commitment(self) -> None:
        report = self.evaluate()
        case = next(
            item
            for item in report["cases"]
            if item["faultClass"] == "forecast-as-binding-commitment"
        )
        self.assertEqual(
            ["invariant-changed:noncoercive-forecast"],
            case["activeLossIds"],
        )

    def test_individual_metric_aggregation_is_rejected(self) -> None:
        report = self.evaluate()
        case = next(
            item
            for item in report["cases"]
            if item["faultClass"] == "individual-metric-aggregation"
        )
        self.assertEqual(
            ["invariant-changed:team-measurement-boundary"],
            case["activeLossIds"],
        )

    def test_professional_accountability_transfer_is_rejected(self) -> None:
        report = self.evaluate()
        case = next(
            item
            for item in report["cases"]
            if item["faultClass"] == "professional-accountability-transfer"
        )
        self.assertEqual(
            ["assumption:professional-accountability-transfer"],
            case["activeLossIds"],
        )

    def test_terminal_recovery_preserves_historical_loss(self) -> None:
        report = self.evaluate()
        for case in report["cases"]:
            if case["faultClass"] == "control":
                continue
            ledger = case["cumulativeLoss"]
            self.assertEqual([], ledger["hops"][-1]["activeLossIds"])
            self.assertTrue(ledger["cumulativeUniqueLossIds"])
            self.assertTrue(ledger["terminalRecoveryDoesNotEraseHistoricalUniqueLoss"])

    def test_fault_label_cannot_hide_a_different_mutation(self) -> None:
        fixture = copy.deepcopy(self.fixture)
        case = next(
            item
            for item in fixture["cases"]
            if item["faultClass"] == "quality-guardrail-omission"
        )
        case["overrides"] = {"qualityGuardrailIds": ["invented.guardrail"]}
        with self.assertRaisesRegex(RuntimeError, "Fault mutation shape drifted"):
            self.evaluate(fixture=fixture)

    def test_fixture_binding_drift_fails_closed(self) -> None:
        protocol = copy.deepcopy(self.protocol)
        protocol["fixtureBinding"]["fileSha256"] = "0" * 64
        with self.assertRaisesRegex(RuntimeError, "Fixture binding drifted"):
            self.evaluate(protocol=protocol)

    def test_source_scenario_evidence_cannot_be_promoted(self) -> None:
        protocol = copy.deepcopy(self.protocol)
        protocol["scenarioBinding"]["evidenceStateMustRemain"] = "verified"
        with self.assertRaisesRegex(RuntimeError, "Scenario evidence boundary drifted"):
            self.evaluate(protocol=protocol)

    def test_candidate_pin_cannot_be_rewritten(self) -> None:
        protocol = copy.deepcopy(self.protocol)
        protocol["candidateRouteBoundary"]["candidateSource"]["revision"] = "0" * 40
        with self.assertRaisesRegex(RuntimeError, "PM candidate source boundary drifted"):
            self.evaluate(protocol=protocol)

    def test_candidate_static_state_cannot_become_execution(self) -> None:
        protocol = copy.deepcopy(self.protocol)
        protocol["candidateRouteBoundary"]["candidateSource"]["components"][0][
            "executedByThisProtocol"
        ] = True
        with self.assertRaisesRegex(RuntimeError, "component identity or lifecycle"):
            self.evaluate(protocol=protocol)

    def test_official_route_cannot_gain_account_access(self) -> None:
        protocol = copy.deepcopy(self.protocol)
        protocol["officialRoute"]["connectedSourceOrAccountAccessAuthorized"] = True
        with self.assertRaisesRegex(RuntimeError, "Official route boundary drifted"):
            self.evaluate(protocol=protocol)

    def test_wayfinder_near_match_cannot_become_execution(self) -> None:
        protocol = copy.deepcopy(self.protocol)
        protocol["nearMatchBoundary"][0]["executed"] = True
        with self.assertRaisesRegex(RuntimeError, "Near-match boundary drifted"):
            self.evaluate(protocol=protocol)

    def test_execution_boundary_promotion_fails_closed(self) -> None:
        protocol = copy.deepcopy(self.protocol)
        protocol["executionBoundary"]["modelCallCount"] = 1
        with self.assertRaisesRegex(RuntimeError, "Execution boundary drifted"):
            self.evaluate(protocol=protocol)

    def test_claim_boundary_promotion_fails_closed(self) -> None:
        fixture = copy.deepcopy(self.fixture)
        fixture["claimBoundary"]["forecastAccuracyImproved"] = True
        with self.assertRaisesRegex(RuntimeError, "Fixture claim boundary drifted"):
            self.evaluate(fixture=fixture)

    def test_unknown_override_key_fails_before_scoring(self) -> None:
        fixture = copy.deepcopy(self.fixture)
        case = next(
            item
            for item in fixture["cases"]
            if item["faultClass"] == "control"
        )
        case["overrides"] = {"inventedField": []}
        with self.assertRaisesRegex(RuntimeError, "Fault mutation shape drifted"):
            self.evaluate(fixture=fixture)

    def test_passed_fixture_must_equal_hash_bound_repository_object(self) -> None:
        fixture = copy.deepcopy(self.fixture)
        fixture["unexpectedButOtherwiseValid"] = True
        with self.assertRaisesRegex(RuntimeError, "hash-bound repository object"):
            self.evaluate(fixture=fixture)

    def test_report_never_claims_live_or_residual_evidence(self) -> None:
        report = self.evaluate()
        self.assertFalse(report["formalLiveEvidenceEligible"])
        self.assertEqual(0, report["agentDispatchCount"])
        self.assertEqual(0, report["modelCallCount"])
        self.assertEqual(0, report["candidateExecutionCount"])
        self.assertTrue(all(value is False for value in report["claimBoundary"].values()))


if __name__ == "__main__":
    unittest.main()
