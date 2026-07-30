from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from scripts.evaluate_human_ai_collaboration_access_comms_zero_model_calibration import (
    REQUIRED_FAULT_CLASSES,
    evaluate_calibration,
    evaluate_repository_calibration,
)


ROOT = Path(__file__).resolve().parent.parent
PROTOCOL_PATH = ROOT / (
    "registry/human-ai-collaboration-access-comms-zero-model-protocol-"
    "2026-07-27.json"
)
FIXTURE_PATH = ROOT / (
    "tests/fixtures/human-ai-collaboration-access-comms-zero-model-"
    "calibration-2026-07-27.json"
)


class AccessCommsZeroModelCalibrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.protocol = json.loads(
            PROTOCOL_PATH.read_text(encoding="utf-8")
        )
        cls.fixture = json.loads(
            FIXTURE_PATH.read_text(encoding="utf-8")
        )

    def evaluate(self, fixture=None, protocol=None):
        return evaluate_calibration(
            copy.deepcopy(protocol or self.protocol),
            copy.deepcopy(fixture or self.fixture),
            root=ROOT,
        )

    def test_repository_calibration_is_bounded_and_valid(self) -> None:
        report = evaluate_repository_calibration(ROOT)
        self.assertEqual("valid-zero-model-calibration", report["outcome"])
        self.assertEqual(
            "zero-model-calibrated-no-live-agent-or-domain",
            report["status"],
        )
        self.assertEqual(9, report["caseCount"])
        self.assertEqual(8, report["faultCaseCount"])
        self.assertTrue(report["allCasesPassed"])

    def test_all_required_fault_classes_are_detected_exactly(self) -> None:
        report = self.evaluate()
        self.assertEqual(
            sorted(REQUIRED_FAULT_CLASSES),
            report["faultClassesCovered"],
        )
        cases = {item["faultClass"]: item for item in report["cases"]}
        for fault_class in REQUIRED_FAULT_CLASSES:
            with self.subTest(fault_class=fault_class):
                case = cases[fault_class]
                expected = case["expectedAdaptedActiveLossIds"]
                self.assertEqual(
                    expected,
                    case["stages"][1]["activeLossIds"],
                )
                self.assertTrue(expected)

    def test_per_hop_new_carried_and_recovered_sets_are_preserved(self) -> None:
        report = self.evaluate()
        case = next(
            item
            for item in report["cases"]
            if item["faultClass"] == "deadline-unit-drift"
        )
        hops = {
            item["stageId"]: item
            for item in case["cumulativeLoss"]["hops"]
        }
        losses = [
            "invariant-changed:deadline",
            "invariant-changed:unit",
        ]
        self.assertEqual(losses, hops["adapted-message"]["newLossIds"])
        self.assertEqual(
            losses,
            hops["review-detection"]["carriedLossIds"],
        )
        self.assertEqual(
            losses,
            hops["human-review-recovery"]["recoveredLossIds"],
        )

    def test_terminal_recovery_does_not_erase_unique_loss(self) -> None:
        report = self.evaluate()
        for case in report["cases"]:
            if case["faultClass"] == "control":
                continue
            with self.subTest(fault_class=case["faultClass"]):
                self.assertEqual(
                    [],
                    case["stages"][-1]["activeLossIds"],
                )
                ledger = case["cumulativeLoss"]
                self.assertEqual(
                    case["expectedCumulativeUniqueLossIds"],
                    ledger["cumulativeUniqueLossIds"],
                )
                self.assertTrue(
                    ledger[
                        "terminalRecoveryDoesNotEraseHistoricalUniqueLoss"
                    ]
                )

    def test_control_has_no_loss_or_budget_breach(self) -> None:
        report = self.evaluate()
        control = next(
            item
            for item in report["cases"]
            if item["faultClass"] == "control"
        )
        ledger = control["cumulativeLoss"]
        self.assertEqual([], ledger["cumulativeUniqueLossIds"])
        self.assertEqual(0, ledger["cumulativeUniqueLossWeight"])
        self.assertIsNone(ledger["budgetExceededAtHop"])
        self.assertTrue(
            all(not item["activeLossIds"] for item in control["stages"])
        )

    def test_fixture_hash_binding_drift_fails_closed(self) -> None:
        protocol = copy.deepcopy(self.protocol)
        protocol["fixtureBinding"]["fileSha256"] = "0" * 64
        with self.assertRaisesRegex(RuntimeError, "Fixture binding drifted"):
            self.evaluate(protocol=protocol)

    def test_duplicate_case_identity_fails_closed(self) -> None:
        fixture = copy.deepcopy(self.fixture)
        fixture["cases"][1]["id"] = fixture["cases"][0]["id"]
        with self.assertRaisesRegex(
            RuntimeError,
            "Fixture case identities drifted",
        ):
            self.evaluate(fixture=fixture)

    def test_acceptance_promotion_fails_closed(self) -> None:
        protocol = copy.deepcopy(self.protocol)
        protocol["acceptance"]["formalLiveEvidenceEligible"] = True
        with self.assertRaisesRegex(
            RuntimeError,
            "Acceptance contract drifted",
        ):
            self.evaluate(protocol=protocol)

    def test_execution_boundary_promotion_fails_closed(self) -> None:
        protocol = copy.deepcopy(self.protocol)
        protocol["executionBoundary"]["networkAccessUsed"] = True
        with self.assertRaisesRegex(
            RuntimeError,
            "Execution boundary drifted",
        ):
            self.evaluate(protocol=protocol)

    def test_source_scenario_contract_drift_fails_closed(self) -> None:
        protocol = copy.deepcopy(self.protocol)
        protocol["scenarioBinding"]["sourceScenarioContract"][
            "authorityBoundary"
        ] = "Synthetic calibration authorizes release."
        with self.assertRaisesRegex(
            RuntimeError,
            "Source scenario contract drifted",
        ):
            self.evaluate(protocol=protocol)

    def test_local_narrowing_cannot_promote_source_evidence(self) -> None:
        protocol = copy.deepcopy(self.protocol)
        protocol["scenarioBinding"]["localCalibrationNarrowing"][
            "sourceEvidenceStateRemains"
        ] = "verified"
        with self.assertRaisesRegex(
            RuntimeError,
            "Local calibration narrowing drifted",
        ):
            self.evaluate(protocol=protocol)

    def test_scenario_path_escape_fails_before_file_access(self) -> None:
        protocol = copy.deepcopy(self.protocol)
        protocol["scenarioBinding"]["sourcePath"] = (
            "../outside/private-source.json"
        )
        with self.assertRaisesRegex(
            RuntimeError,
            "escapes the repository root",
        ):
            self.evaluate(protocol=protocol)

    def test_reuse_absolute_path_fails_before_file_access(self) -> None:
        protocol = copy.deepcopy(self.protocol)
        protocol["processFidelityReuse"]["modulePath"] = str(
            (ROOT.parent / "outside.py").resolve()
        )
        with self.assertRaisesRegex(
            RuntimeError,
            "escapes the repository root",
        ):
            self.evaluate(protocol=protocol)

    def test_protocol_claim_key_deletion_fails_closed(self) -> None:
        protocol = copy.deepcopy(self.protocol)
        protocol["claimBoundary"].pop("accessibilityConformanceProved")
        with self.assertRaisesRegex(
            RuntimeError,
            "Protocol claim boundary drifted",
        ):
            self.evaluate(protocol=protocol)

    def test_fixture_claim_promotion_fails_closed(self) -> None:
        fixture = copy.deepcopy(self.fixture)
        fixture["claimBoundary"]["accessibilityConformanceProved"] = True
        with self.assertRaisesRegex(
            RuntimeError,
            "Fixture claim boundary drifted",
        ):
            self.evaluate(fixture=fixture)

    def test_protocol_status_promotion_fails_closed(self) -> None:
        protocol = copy.deepcopy(self.protocol)
        protocol["status"] = "live-domain-verified"
        with self.assertRaisesRegex(RuntimeError, "Protocol header drifted"):
            self.evaluate(protocol=protocol)

    def test_fixture_status_promotion_fails_closed(self) -> None:
        fixture = copy.deepcopy(self.fixture)
        fixture["status"] = "live-domain-verified"
        with self.assertRaisesRegex(RuntimeError, "Fixture header drifted"):
            self.evaluate(fixture=fixture)

    def test_failure_fallback_rewrite_fails_closed(self) -> None:
        protocol = copy.deepcopy(self.protocol)
        protocol["failureFallback"][-1] = (
            "Failure authorizes candidate implementation."
        )
        with self.assertRaisesRegex(RuntimeError, "Failure fallback drifted"):
            self.evaluate(protocol=protocol)

    def test_documentation_binding_drift_fails_closed(self) -> None:
        protocol = copy.deepcopy(self.protocol)
        protocol["documentation"] = "docs/strategy/other.md"
        with self.assertRaisesRegex(
            RuntimeError,
            "Documentation binding drifted",
        ):
            self.evaluate(protocol=protocol)

    def test_passed_fixture_must_equal_hash_bound_repository_object(self) -> None:
        fixture = copy.deepcopy(self.fixture)
        fixture["unexpectedButOtherwiseSemanticallyValid"] = True
        with self.assertRaisesRegex(
            RuntimeError,
            "hash-bound repository object",
        ):
            self.evaluate(fixture=fixture)

    def test_expected_fault_result_tampering_fails_closed(self) -> None:
        fixture = copy.deepcopy(self.fixture)
        fixture["cases"][1]["expectedAdaptedActiveLossIds"] = []
        with self.assertRaisesRegex(
            RuntimeError,
            "Expected adapted loss set drifted",
        ):
            self.evaluate(fixture=fixture)

    def test_unknown_assumption_fails_closed(self) -> None:
        fixture = copy.deepcopy(self.fixture)
        fixture["cases"][1]["assumptionIds"] = ["unknown-commitment"]
        with self.assertRaisesRegex(RuntimeError, "Unknown assumption id"):
            self.evaluate(fixture=fixture)

    def test_fault_label_cannot_hide_a_different_mutation(self) -> None:
        fixture = copy.deepcopy(self.fixture)
        case = fixture["cases"][1]
        case["changes"] = {
            "actor": "Neighborhood Volunteer Group",
        }
        case["expectedAdaptedActiveLossIds"] = [
            "invariant-changed:actor",
        ]
        case["expectedCumulativeUniqueLossIds"] = [
            "invariant-changed:actor",
        ]
        case["reviewDetectedLossIds"] = [
            "invariant-changed:actor",
        ]
        with self.assertRaisesRegex(
            RuntimeError,
            "Fault mutation shape drifted",
        ):
            self.evaluate(fixture=fixture)

    def test_claim_boundary_does_not_promote_live_or_domain_evidence(
        self,
    ) -> None:
        report = self.evaluate()
        self.assertFalse(report["formalLiveEvidenceEligible"])
        self.assertEqual(0, report["agentDispatchCount"])
        self.assertEqual(0, report["modelCallCount"])
        self.assertFalse(report["externalAccessUsed"])
        self.assertTrue(
            all(value is False for value in report["claimBoundary"].values())
        )
        self.assertIn(
            "structured semantic calibration",
            report["claimLimit"],
        )


if __name__ == "__main__":
    unittest.main()
